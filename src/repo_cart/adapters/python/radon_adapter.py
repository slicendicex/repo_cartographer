"""
Radon adapter — Python cyclomatic complexity via radon cc.

Requires: pip install radon
Command:  radon cc -j <path>
Layer:    complexity
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext


class RadonAdapter(AdapterBase):

    @property
    def name(self) -> str:
        return "radon"

    @property
    def language(self) -> str:
        return "python"

    @property
    def layer(self) -> str:
        return "complexity"

    def check(self) -> bool:
        return shutil.which("radon") is not None

    def run(self, path: Path) -> str:
        return self._run_subprocess(["radon", "cc", "-j", str(path)], cwd=path)

    def parse(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"radon output is not valid JSON: {exc}", "parse_error")

        hotspots: list[dict] = []
        total_complexity = 0.0
        function_count = 0

        for filepath, blocks in data.items():
            for block in blocks:
                cc = block.get("complexity", 0)
                total_complexity += cc
                function_count += 1
                hotspots.append({
                    "file": filepath,
                    "name": block.get("name", "?"),
                    "complexity": cc,
                    "grade": _grade(cc),
                    "type": block.get("type", "?"),
                    "line": block.get("lineno", 0),
                })

        hotspots.sort(key=lambda h: h["complexity"], reverse=True)
        avg = round(total_complexity / function_count, 2) if function_count > 0 else 0.0

        return {
            "avg_complexity": avg,
            "function_count": function_count,
            "hotspots": hotspots[:20],  # cap at 20 for snapshot size
        }

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        total = ctx.files_by_language.get("python", 0)
        if total == 0:
            return 0.0
        analyzed = len({h["file"] for h in parsed.get("hotspots", [])})
        return min(analyzed / total, 1.0)


def _grade(cc: int) -> str:
    if cc <= 5:
        return "A"
    if cc <= 10:
        return "B"
    if cc <= 15:
        return "C"
    if cc <= 20:
        return "D"
    if cc <= 25:
        return "E"
    return "F"
