"""Tests for EntryPointsAdapter."""

import json

import pytest

from repo_cart.adapters.base import WalkerContext
from repo_cart.adapters.common.entry_points_adapter import EntryPointsAdapter


class TestEntryPointsAdapterCheck:
    def test_check_always_true(self):
        assert EntryPointsAdapter().check() is True


class TestEntryPointsAdapterPyproject:
    def setup_method(self):
        self.adapter = EntryPointsAdapter()

    def test_cli_from_pyproject_scripts(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project.scripts]\nrepo-cart = "repo_cart.cli:app"\n'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["cli"] == ["repo-cart"]

    def test_no_scripts_section_yields_empty_cli(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["cli"] == []


class TestEntryPointsAdapterPackageJson:
    def setup_method(self):
        self.adapter = EntryPointsAdapter()

    def test_package_main_field(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"main": "./dist/index.js"}))
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["package_main"] == "./dist/index.js"

    def test_package_bin_string(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"bin": "./cli.js"}))
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["package_main"] == "./cli.js"
        assert result["cli"] == []

    def test_package_bin_dict(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"bin": {"mycli": "./cli.js", "myutil": "./util.js"}})
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert "mycli" in result["cli"]
        assert "myutil" in result["cli"]

    def test_main_takes_priority_over_bin_string(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"main": "./index.js", "bin": "./cli.js"})
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["package_main"] == "./index.js"


class TestEntryPointsAdapterMainModule:
    def setup_method(self):
        self.adapter = EntryPointsAdapter()

    def test_main_module_detected(self, tmp_path):
        src = tmp_path / "src" / "mypkg"
        src.mkdir(parents=True)
        (src / "__main__.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert any("__main__.py" in m for m in result["main_modules"])

    def test_no_src_dir_yields_empty_main_modules(self, tmp_path):
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["main_modules"] == []


class TestEntryPointsAdapterEmpty:
    def test_no_entry_points_returns_empty_with_zero_confidence(self, tmp_path):
        adapter = EntryPointsAdapter()
        result = adapter.parse(adapter.run(tmp_path))
        assert result["cli"] == []
        assert result["main_modules"] == []
        assert result["package_main"] is None
        ctx = WalkerContext(total_files=5, files_by_language={})
        assert adapter.confidence(result, ctx) == 0.0


class TestEntryPointsAdapterConfidence:
    def setup_method(self):
        self.adapter = EntryPointsAdapter()
        self.ctx = WalkerContext(total_files=10, files_by_language={})

    def test_confidence_full_when_cli_found(self):
        parsed = {"cli": ["mytool"], "main_modules": [], "package_main": None}
        assert self.adapter.confidence(parsed, self.ctx) == 1.0

    def test_confidence_full_when_main_module_found(self):
        parsed = {"cli": [], "main_modules": ["src/pkg/__main__.py"], "package_main": None}
        assert self.adapter.confidence(parsed, self.ctx) == 1.0

    def test_confidence_full_when_package_main_found(self):
        parsed = {"cli": [], "main_modules": [], "package_main": "./index.js"}
        assert self.adapter.confidence(parsed, self.ctx) == 1.0

    def test_confidence_zero_when_no_entry_points(self):
        parsed = {"cli": [], "main_modules": [], "package_main": None}
        assert self.adapter.confidence(parsed, self.ctx) == 0.0
