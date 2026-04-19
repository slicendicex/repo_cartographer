"""TestCoverageAdapter — heuristic structural test coverage via file stem matching."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext


_EXCLUDED_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".eggs", ".mypy_cache", ".pytest_cache",
    ".next", ".nuxt", "coverage",
})

_TEST_FILE_RE = re.compile(
    r"^(test_.+\.py|.+_test\.py|.+\.test\.ts|.+\.spec\.ts)$"
)


def _is_test_file(name: str) -> bool:
    return bool(_TEST_FILE_RE.match(name))


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
        tests_dir = path / "tests"
        if not tests_dir.is_dir():
            raise AdapterError("no test directory found", "no_config")

        source_files = self._collect_source_files(path)
        test_count, test_stems = self._collect_test_info(tests_dir)

        if len(source_files) == 0:
            coverage_ratio = 0.0
        else:
            coverage_ratio = min(test_count / len(source_files), 1.0)

        untested = [
            str(f.relative_to(path))
            for f in source_files
            if not _has_test(f, test_stems)
        ]

        return json.dumps({
            "test_files": test_count,
            "source_files": len(source_files),
            "coverage_ratio": round(coverage_ratio, 2),
            "untested_modules": untested,
        })

    def parse(self, raw: str) -> dict:
        return json.loads(raw)

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        if ctx.total_files == 0:
            return 0.0
        return min(parsed.get("test_files", 0) / ctx.total_files, 1.0)

    def _collect_source_files(self, root: Path) -> list[Path]:
        base = root / "src" if (root / "src").is_dir() else root
        files = []
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                if name.endswith(".py") and name != "__init__.py" and not _is_test_file(name):
                    files.append(Path(dirpath) / name)
        return files

    def _collect_test_info(self, tests_dir: Path) -> tuple[int, set[str]]:
        count = 0
        stems: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(tests_dir, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                if _is_test_file(name):
                    count += 1
                    stems.add(Path(name).stem.lower())
        return count, stems


def _has_test(source_file: Path, test_stems: set[str]) -> bool:
    stem = source_file.stem.lower()
    return f"test_{stem}" in test_stems or f"{stem}_test" in test_stems
