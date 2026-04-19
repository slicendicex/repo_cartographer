"""EntryPointsAdapter — finds CLI commands, __main__.py modules, and package main fields."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, WalkerContext


class EntryPointsAdapter(AdapterBase):
    @property
    def name(self) -> str:
        return "entry_points_adapter"

    @property
    def language(self) -> str:
        return "any"

    @property
    def layer(self) -> str:
        return "entry_points"

    def check(self) -> bool:
        return True

    def run(self, path: Path) -> str:
        result = self._collect(path)
        return json.dumps(result)

    def parse(self, raw: str) -> dict:
        return json.loads(raw)

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        if parsed.get("cli") or parsed.get("main_modules") or parsed.get("package_main"):
            return 1.0
        return 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect(self, path: Path) -> dict:
        cli: list[str] = []
        main_modules: list[str] = []
        package_main: str | None = None

        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            scripts = self._pyproject_scripts(pyproject)
            cli.extend(scripts)

        pkg_json = path / "package.json"
        if pkg_json.exists():
            pkg_cli, pkg_main = self._package_json_entries(pkg_json)
            cli.extend(pkg_cli)
            if pkg_main and package_main is None:
                package_main = pkg_main

        src = path / "src"
        if src.is_dir():
            for f in src.rglob("__main__.py"):
                main_modules.append(str(f.relative_to(path)))

        return {
            "cli": cli,
            "main_modules": main_modules,
            "package_main": package_main,
        }

    def _pyproject_scripts(self, path: Path) -> list[str]:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return list(data.get("project", {}).get("scripts", {}).keys())

    def _package_json_entries(self, path: Path) -> tuple[list[str], str | None]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return [], None

        cli: list[str] = []
        package_main: str | None = data.get("main") or None

        bin_field = data.get("bin")
        if isinstance(bin_field, dict):
            cli.extend(bin_field.keys())
        elif isinstance(bin_field, str) and package_main is None:
            package_main = bin_field

        return cli, package_main
