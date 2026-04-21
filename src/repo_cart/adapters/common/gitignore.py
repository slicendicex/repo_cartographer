"""Shared .gitignore parser — called by the walker and file-walking adapters."""

from __future__ import annotations

from pathlib import Path

import pathspec


def load_gitignore(repo_root: Path) -> pathspec.PathSpec | None:
    """
    Parse the root-level .gitignore and return a PathSpec matcher.
    Returns None if no .gitignore exists or if parsing fails.
    Nested .gitignore files are not supported.
    """
    gitignore = repo_root / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        return pathspec.PathSpec.from_lines("gitignore", lines)
    except Exception:
        return None
