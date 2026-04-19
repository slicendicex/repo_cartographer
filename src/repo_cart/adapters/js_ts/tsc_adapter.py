"""
TypeScript compiler adapter — type errors via tsc --noEmit.

Requires: tsc in node_modules/.bin or on PATH
Command:  tsc --noEmit --pretty false
Layer:    types

Skipped with reason_code=no_config if tsconfig.json is absent.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext


def _find_tsc(path: Path) -> str | None:
    """Return the tsc binary path: local node_modules/.bin first, then PATH."""
    local = path / "node_modules" / ".bin" / "tsc"
    if local.is_file():
        return str(local)
    return shutil.which("tsc")


# tsc error line format: path/to/file.ts(line,col): error TS####: message
_ERROR_RE = re.compile(r"^(.+?)\((\d+),(\d+)\): (error|warning) (TS\d+): (.+)$")


class TscAdapter(AdapterBase):

    @property
    def name(self) -> str:
        return "tsc"

    @property
    def language(self) -> str:
        return "typescript"

    @property
    def layer(self) -> str:
        return "types"

    def check(self) -> bool:
        return shutil.which("tsc") is not None

    def run(self, path: Path) -> str:
        if not (path / "tsconfig.json").exists():
            raise AdapterError("tsconfig.json not found", "no_config")
        binary = _find_tsc(path)
        if binary is None:
            raise AdapterError("tsc not found", "not_installed")
        try:
            return self._run_subprocess(
                [binary, "--noEmit", "--pretty", "false"],
                cwd=path,
            )
        except AdapterError as exc:
            # tsc exits non-zero when there are type errors — that is the expected
            # success case. Re-raise only genuine failures (not_installed, timeout).
            if exc.reason_code in ("not_installed", "timeout"):
                raise
            # Return the raw output (stdout+stderr) so parse() can process it.
            return str(exc)

    def parse(self, raw: str) -> dict:
        errors: list[dict] = []
        warnings: list[dict] = []

        for line in raw.splitlines():
            m = _ERROR_RE.match(line.strip())
            if not m:
                continue
            entry = {
                "file": m.group(1),
                "line": int(m.group(2)),
                "col": int(m.group(3)),
                "code": m.group(5),
                "message": m.group(6),
            }
            if m.group(4) == "error":
                errors.append(entry)
            else:
                warnings.append(entry)

        return {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:20],
        }

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        total = ctx.files_by_language.get("typescript", 0)
        if total == 0:
            return 0.0
        analyzed = len({e["file"] for e in parsed.get("errors", [])})
        return min(analyzed / total, 1.0) if analyzed > 0 else 0.5
