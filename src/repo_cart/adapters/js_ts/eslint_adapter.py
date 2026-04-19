"""
ESLint adapter — JS/TS lint errors via eslint.

Requires: eslint in node_modules/.bin or on PATH
Command:  eslint --format json <path>
Layer:    lint

Config detection:
  v9+: eslint.config.{js,mjs,cjs}
  v7/v8: .eslintrc, .eslintrc.{js,cjs,json,yml,yaml}
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext


_V9_CONFIGS = ("eslint.config.js", "eslint.config.mjs", "eslint.config.cjs")
_LEGACY_CONFIGS = (
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".eslintrc.yaml",
)


def _find_eslint(path: Path) -> str | None:
    """Return the eslint binary path: local node_modules/.bin first, then PATH."""
    local = path / "node_modules" / ".bin" / "eslint"
    if local.is_file():
        return str(local)
    return shutil.which("eslint")


def _has_config(path: Path) -> bool:
    for name in _V9_CONFIGS + _LEGACY_CONFIGS:
        if (path / name).exists():
            return True
    return False


class ESLintAdapter(AdapterBase):

    @property
    def name(self) -> str:
        return "eslint"

    @property
    def language(self) -> str:
        return "javascript"

    @property
    def layer(self) -> str:
        return "lint"

    def check(self) -> bool:
        return shutil.which("eslint") is not None

    def run(self, path: Path) -> str:
        binary = _find_eslint(path)
        if binary is None:
            raise AdapterError("eslint not found", "not_installed")
        if not _has_config(path):
            raise AdapterError("no eslint config found", "no_config")

        # eslint exit codes:
        #   0 — no lint errors
        #   1 — lint errors found (stdout contains valid JSON — the normal result)
        #   2 — fatal error (bad config, internal crash — not parseable)
        # _run_subprocess raises on any non-zero exit, so we invoke subprocess
        # directly here to distinguish 1 from 2.
        try:
            result = subprocess.run(
                [binary, "--format", "json", str(path)],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise AdapterError(f"eslint timed out after {self.timeout}s", "timeout")

        if result.returncode == 2:
            raise AdapterError(
                result.stderr or "eslint fatal error (exit 2)",
                "parse_error",
            )

        return result.stdout

    def parse(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"eslint output is not valid JSON: {exc}", "parse_error")

        error_count = 0
        warning_count = 0
        files_with_issues: list[dict] = []

        for entry in data:
            e = entry.get("errorCount", 0)
            w = entry.get("warningCount", 0)
            error_count += e
            warning_count += w
            if e + w > 0:
                files_with_issues.append({
                    "file": entry.get("filePath", "?"),
                    "errors": e,
                    "warnings": w,
                    "messages": [
                        {
                            "rule": m.get("ruleId", "?"),
                            "severity": m.get("severity", 1),
                            "line": m.get("line", 0),
                            "message": m.get("message", ""),
                        }
                        for m in entry.get("messages", [])[:5]
                    ],
                })

        files_with_issues.sort(key=lambda f: f["errors"], reverse=True)

        return {
            "error_count": error_count,
            "warning_count": warning_count,
            "files_with_issues": files_with_issues[:20],
        }

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        total = ctx.files_by_language.get("javascript", 0) + ctx.files_by_language.get("typescript", 0)
        if total == 0:
            return 0.0
        analyzed = len({f["file"] for f in parsed.get("files_with_issues", [])})
        return min(analyzed / total, 1.0) if analyzed > 0 else 0.5
