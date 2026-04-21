"""GitActivityAdapter — git log based activity layer (Layer 07)."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext
from repo_cart.core.walker import EXCLUDED_DIRS

_VALID_WINDOWS: frozenset[str] = frozenset({"30d", "90d", "365d", "all"})
_WINDOW_DAYS: dict[str, int] = {"30d": 30, "90d": 90, "365d": 365}
_TOP_N = 10


def _is_excluded(fpath: str) -> bool:
    return any(part in EXCLUDED_DIRS for part in Path(fpath).parts)


def _parse_sentinel(log_output: str) -> list[dict]:
    """Parse `git log --format='COMMIT %H|%ae|%as' --numstat` output.

    Sentinel lines mark commit boundaries; numstat tab-delimited lines follow.
    Binary files (numstat shows '-') and excluded dirs are silently skipped.
    """
    commits: list[dict] = []
    current: dict | None = None
    for line in log_output.splitlines():
        if line.startswith("COMMIT "):
            if current is not None:
                commits.append(current)
            _, rest = line.split(" ", 1)
            sha, email, date = rest.split("|", 2)
            current = {"sha": sha, "email": email, "date": date, "files": []}
        elif "\t" in line and current is not None:
            parts = line.split("\t")
            if len(parts) == 3 and parts[0] != "-":  # skip binary files ("-")
                fpath = parts[2]
                if not _is_excluded(fpath):
                    current["files"].append(fpath)
        # blank lines between commits are ignored naturally
    if current is not None:
        commits.append(current)
    return commits


class GitActivityAdapter(AdapterBase):
    timeout: int = 120  # full-history scans on large repos need headroom

    def __init__(self, window: str = "90d") -> None:
        if window not in _VALID_WINDOWS:
            raise ValueError(
                f"invalid window {window!r}; must be one of {sorted(_VALID_WINDOWS)}"
            )
        self._window = window

    @property
    def name(self) -> str:
        return "git_activity_adapter"

    @property
    def language(self) -> str:
        return "any"

    @property
    def layer(self) -> str:
        return "git_activity"

    def check(self) -> bool:
        return shutil.which("git") is not None

    def run(self, path: Path) -> str:
        # Verify we're inside a git repo — handles worktrees, not just .git/ presence
        wt = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if wt.returncode != 0 or wt.stdout.strip() != "true":
            raise AdapterError("not a git repository", "unsupported_repo")

        # Shallow clone detection — falls back to False on git < 2.15
        shallow_proc = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        is_shallow = shallow_proc.returncode == 0 and shallow_proc.stdout.strip() == "true"

        # Main git log call using sentinel format (one call for all signals)
        cmd = ["git", "log", "--format=COMMIT %H|%ae|%as", "--numstat"]
        if self._window != "all":
            days = _WINDOW_DAYS[self._window]
            cmd += [f"--since={days} days ago"]

        log_output = self._run_subprocess(cmd, cwd=path)
        commits = _parse_sentinel(log_output)

        # Aggregate signals
        file_counts: Counter[str] = Counter()
        dir_counts: Counter[str] = Counter()
        authors: set[str] = set()
        for c in commits:
            authors.add(c["email"])
            for f in c["files"]:
                file_counts[f] += 1
                p = Path(f)
                if len(p.parts) > 1:  # skip root-level files (Makefile, README, etc.)
                    dir_counts[p.parts[0]] += 1

        # Coverage: fraction of git-tracked files touched in the window
        ls_output = self._run_subprocess(["git", "ls-files"], cwd=path)
        tracked = {line for line in ls_output.splitlines() if line}
        touched = set(file_counts.keys())
        coverage = len(touched & tracked) / len(tracked) if tracked else 0.0

        return json.dumps({
            "window": self._window,
            "shallow_clone": is_shallow,
            "commits_in_window": len(commits),
            "active_contributors": len(authors),
            "coverage": round(coverage, 3),
            "hot_files": [
                {"path": p, "changes": n}
                for p, n in file_counts.most_common(_TOP_N)
            ],
            "hot_dirs": [
                {"path": d, "changes": n}
                for d, n in dir_counts.most_common(_TOP_N)
            ],
        })

    def parse(self, raw: str) -> dict:
        return json.loads(raw)

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        # ctx unused — confidence is derived from git signals in parsed data
        commit_count = parsed.get("commits_in_window", 0)
        if commit_count == 0:
            return 0.0
        score = 1.0
        if parsed.get("shallow_clone"):
            score = min(score, 0.6)
        if commit_count < 5:
            score -= 0.2
        return round(max(score, 0.0), 2)
