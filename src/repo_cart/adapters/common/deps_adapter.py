"""DepsAdapter — parses dependency manifests without any external binaries."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext


def _strip_version(spec: str) -> str:
    """Return the bare package name from a dependency specifier."""
    return re.split(r"[>=<!~\[\s]", spec)[0].strip()


class DepsAdapter(AdapterBase):
    @property
    def name(self) -> str:
        return "deps_adapter"

    @property
    def language(self) -> str:
        return "any"

    @property
    def layer(self) -> str:
        return "dependencies"

    def check(self) -> bool:
        return True

    def run(self, path: Path) -> str:
        result = self._collect(path)
        if not result:
            raise AdapterError("no dependency file found", "no_config")
        return json.dumps(result)

    def parse(self, raw: str) -> dict:
        return json.loads(raw)

    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        return 1.0 if parsed else 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect(self, path: Path) -> dict:
        result: dict = {}

        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            python_info = self._parse_pyproject(pyproject)
            if python_info:
                result["python"] = python_info

        if "python" not in result:
            req = path / "requirements.txt"
            req_dev = path / "requirements-dev.txt"
            if req.exists() or req_dev.exists():
                runtime = self._parse_requirements(req) if req.exists() else []
                dev = self._parse_requirements(req_dev) if req_dev.exists() else []
                result["python"] = {
                    "runtime": runtime,
                    "dev": dev,
                    "total": len(runtime) + len(dev),
                    "source_file": "requirements.txt",
                }

        pkg_json = path / "package.json"
        if pkg_json.exists():
            js_info = self._parse_package_json(pkg_json)
            if js_info:
                result["js"] = js_info

        return result

    def _parse_pyproject(self, path: Path) -> dict | None:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        project = data.get("project", {})
        runtime = list(project.get("dependencies", []))
        dev = list(project.get("optional-dependencies", {}).get("dev", []))

        if not runtime and not dev:
            return None

        return {
            "runtime": runtime,
            "dev": dev,
            "total": len(runtime) + len(dev),
            "source_file": "pyproject.toml",
        }

    def _parse_requirements(self, path: Path) -> list[str]:
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                lines.append(line)
        return lines

    def _parse_package_json(self, path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        runtime = list(data.get("dependencies", {}).keys())
        dev = list(data.get("devDependencies", {}).keys())

        if not runtime and not dev:
            return None

        return {
            "runtime": runtime,
            "dev": dev,
            "total": len(runtime) + len(dev),
            "source_file": "package.json",
        }
