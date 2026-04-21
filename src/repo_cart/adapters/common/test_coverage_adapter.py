"""TestCoverageAdapter — per-language test coverage via file discovery and coverage.xml."""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, WalkerContext
from repo_cart.adapters.common.gitignore import load_gitignore
from repo_cart.core.walker import EXCLUDED_DIRS


_PYTHON_TEST_RE = re.compile(r"^(test_.+|.+_test)\.py$")
_JS_TEST_RE = re.compile(r"^.+\.(test|spec)\.(js|jsx|mjs|cjs)$")
_TS_TEST_RE = re.compile(r"^.+\.(test|spec)\.(ts|tsx|mts|cts)$")

_PYTHON_SRC_EXTS = frozenset({".py"})
_TS_SRC_EXTS = frozenset({".ts", ".tsx", ".mts", ".cts"})
_JS_SRC_EXTS = frozenset({".js", ".jsx", ".mjs", ".cjs"})


def _classify_file(name: str) -> tuple[str | None, bool]:
    """Return (language, is_test). Returns (None, False) for unrecognized files."""
    if _PYTHON_TEST_RE.match(name):
        return "python", True
    if _JS_TEST_RE.match(name):
        return "javascript", True
    if _TS_TEST_RE.match(name):
        return "typescript", True

    if name == "__init__.py" or name.endswith(".d.ts"):
        return None, False

    ext = Path(name).suffix.lower()
    if ext in _PYTHON_SRC_EXTS:
        return "python", False
    if ext in _TS_SRC_EXTS:
        return "typescript", False
    if ext in _JS_SRC_EXTS:
        return "javascript", False
    return None, False


def _try_coverage_xml(path: Path) -> tuple[float | None, float | None, str | None]:
    """Parse coverage.xml if present. Returns (line_rate, branch_rate, iso_timestamp)."""
    xml_path = path / "coverage.xml"
    if not xml_path.is_file():
        return None, None, None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        line_rate_str = root.get("line-rate")
        if line_rate_str is None:
            return None, None, None
        line_rate = round(float(line_rate_str), 3)
        branch_rate_str = root.get("branch-rate")
        branch_rate = round(float(branch_rate_str), 3) if branch_rate_str else None
        mtime = xml_path.stat().st_mtime
        ts = datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
        return line_rate, branch_rate, ts
    except Exception:
        return None, None, None


class TestCoverageAdapter(AdapterBase):
    @property
    def name(self) -> str:
        return "test_coverage_adapter"

    @property
    def language(self) -> str:
        return "any"

    @property
    def layer(self) -> str:
        return "test_coverage"

    def check(self) -> bool:
        return True

    def run(self, path: Path) -> str:
        spec = load_gitignore(path)

        # Walk the whole tree once, classifying each file.
        source_files: dict[str, list[Path]] = defaultdict(list)
        test_files: dict[str, list[str]] = defaultdict(list)

        def _skip_dir(root_path: Path, d: str) -> bool:
            if d in EXCLUDED_DIRS:
                return True
            if spec is not None:
                rel = str((root_path / d).relative_to(path))
                return spec.match_file(rel + "/") or spec.match_file(rel)
            return False

        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            dir_path = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not _skip_dir(dir_path, d)]
            for name in filenames:
                lang, is_test = _classify_file(name)
                if lang is None:
                    continue
                if is_test:
                    test_files[lang].append(Path(name).stem.lower())
                else:
                    source_files[lang].append(dir_path / name)

        # Build per-language breakdown.
        all_langs = set(source_files) | set(test_files)
        by_language: dict[str, dict] = {}
        for lang in sorted(all_langs):
            src = source_files[lang]
            test_stems = set(test_files[lang])
            n_src = len(src)
            n_test = sum(len(v) for v in test_files.items() if v[0] == lang)
            n_test = len(test_files[lang])
            ratio = min(n_test / n_src, 1.0) if n_src > 0 else 0.0

            untested: list[str] = []
            if lang == "python":
                untested = [
                    str(f.relative_to(path))
                    for f in src
                    if not _has_python_test(f, test_stems)
                ]

            by_language[lang] = {
                "source_files": n_src,
                "test_files": n_test,
                "heuristic_ratio": round(ratio, 2),
                "untested_modules": untested,
            }

        # Try coverage.xml for exact line coverage.
        line_rate, branch_rate, xml_ts = _try_coverage_xml(path)

        return json.dumps({
            "by_language": by_language,
            "coverage_xml_present": line_rate is not None,
            "line_rate": line_rate,
            "branch_rate": branch_rate,
            "coverage_xml_timestamp": xml_ts,
        })

    def parse(self, raw: str) -> dict:
        return json.loads(raw)

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        if ctx.total_files == 0:
            return 0.0
        if parsed.get("coverage_xml_present"):
            return 1.0
        total_tests = sum(
            lang.get("test_files", 0)
            for lang in parsed.get("by_language", {}).values()
        )
        return min(total_tests / ctx.total_files, 1.0)


def _has_python_test(source_file: Path, test_stems: set[str]) -> bool:
    stem = source_file.stem.lower()
    return f"test_{stem}" in test_stems or f"{stem}_test" in test_stems
