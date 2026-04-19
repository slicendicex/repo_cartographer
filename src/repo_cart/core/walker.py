"""
File tree walker — produces WalkerResult from a repo path.

Always the first step in a scan. The structure layer is derived from its output
and is the only layer guaranteed to be present in every snapshot.

Excluded directories (hardcoded; .gitignore parsing is deferred to Phase 2):

    node_modules  .git  __pycache__  .venv  venv  dist  build
    .mypy_cache   .pytest_cache  .tox  .nox  coverage  .eggs

Uses os.walk(followlinks=False) to avoid symlink loops.
Unreadable directories are skipped silently; the count is recorded in
WalkerResult.unreadable_dirs for confidence scoring.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from repo_cart.adapters.base import WalkerContext


# Directories skipped unconditionally during traversal.
# .gitignore parsing is deferred from MVP — see docs/layer-00.md.
EXCLUDED_DIRS: frozenset[str] = frozenset({
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".nox",
    "coverage",
    ".eggs",
})

# File extension → language label used in WalkerContext.files_by_language.
LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".mts": "typescript",
    ".cts": "typescript",
}


@dataclass
class WalkerResult:
    """
    Return value of walk(). Named fields replace the anonymous tuple so callers
    don't need to guess which element is which.
    """

    ctx: WalkerContext
    top_dirs: list[str]
    unreadable_dirs: list[str] = field(default_factory=list)

    @property
    def had_warnings(self) -> bool:
        return len(self.unreadable_dirs) > 0


def walk(path: Path) -> WalkerResult:
    """
    Traverse the repo at ``path`` and return a WalkerResult.

    The scan is always attempted regardless of repo size or content — it has no
    external dependencies. However, it may be partial: unreadable directories
    are skipped silently and recorded in WalkerResult.unreadable_dirs.

    Raises ValueError if ``path`` does not exist or is not a directory.
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    files_by_language: dict[str, int] = {}
    total_files = 0
    top_dirs: list[str] = []
    unreadable_dirs: list[str] = []

    def _on_error(exc: OSError) -> None:
        unreadable_dirs.append(str(exc.filename))

    for root, dirs, files in os.walk(path, followlinks=False, onerror=_on_error):
        root_path = Path(root)

        # Collect top-level directories (depth 1 only).
        if root_path == path:
            top_dirs = sorted(d for d in dirs if d not in EXCLUDED_DIRS)

        # Prune excluded directories in-place so os.walk skips their subtrees.
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for filename in files:
            total_files += 1
            ext = Path(filename).suffix.lower()
            lang = LANGUAGE_BY_EXT.get(ext)
            if lang:
                files_by_language[lang] = files_by_language.get(lang, 0) + 1

    ctx = WalkerContext(
        total_files=total_files,
        files_by_language=files_by_language,
    )
    return WalkerResult(ctx=ctx, top_dirs=top_dirs, unreadable_dirs=unreadable_dirs)
