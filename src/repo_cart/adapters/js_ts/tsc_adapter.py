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
import subprocess
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

        # tsc exit codes:
        #   0 — no type errors
        #   1 — type errors found (stdout has error lines — the normal result)
        #   2 — fatal error (bad config, missing files — not parseable)
        try:
            result = subprocess.run(
                [binary, "--noEmit", "--pretty", "false"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise AdapterError(f"tsc timed out after {self.timeout}s", "timeout")

        if result.returncode == 2:
            raise AdapterError(
                result.stderr or result.stdout or "tsc fatal error (exit 2)",
                "parse_error",
            )

        return result.stdout + result.stderr

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
