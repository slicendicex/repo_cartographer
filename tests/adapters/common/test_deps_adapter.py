"""Tests for DepsAdapter."""

import json
from pathlib import Path

import pytest

from repo_cart.adapters.base import AdapterError, WalkerContext
from repo_cart.adapters.common.deps_adapter import DepsAdapter


class TestDepsAdapterCheck:
    def test_check_always_true(self):
        assert DepsAdapter().check() is True


class TestDepsAdapterPyproject:
    def setup_method(self):
        self.adapter = DepsAdapter()

    def test_parse_pyproject_runtime_and_dev(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["typer>=0.12"]\n'
            '[project.optional-dependencies]\ndev = ["pytest>=8.0", "radon>=6.0"]\n'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["python"]["runtime"] == ["typer>=0.12"]
        assert result["python"]["dev"] == ["pytest>=8.0", "radon>=6.0"]
        assert result["python"]["total"] == 3
        assert result["python"]["source_file"] == "pyproject.toml"

    def test_parse_pyproject_runtime_only(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["typer>=0.12"]\n'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["python"]["runtime"] == ["typer>=0.12"]
        assert result["python"]["dev"] == []

    def test_pyproject_takes_priority_over_requirements(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["typer>=0.12"]\n'
        )
        (tmp_path / "requirements.txt").write_text("flask>=3.0\n")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["python"]["source_file"] == "pyproject.toml"
        assert result["python"]["runtime"] == ["typer>=0.12"]


class TestDepsAdapterRequirements:
    def setup_method(self):
        self.adapter = DepsAdapter()

    def test_parse_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask>=3.0\nrequests\n# comment\n")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["python"]["runtime"] == ["flask>=3.0", "requests"]
        assert result["python"]["source_file"] == "requirements.txt"

    def test_parse_requirements_dev_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask>=3.0\n")
        (tmp_path / "requirements-dev.txt").write_text("pytest>=8.0\n")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["python"]["dev"] == ["pytest>=8.0"]


class TestDepsAdapterPackageJson:
    def setup_method(self):
        self.adapter = DepsAdapter()

    def test_parse_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["js"]["runtime"] == ["react"]
        assert result["js"]["dev"] == ["jest"]
        assert result["js"]["total"] == 2
        assert result["js"]["source_file"] == "package.json"


class TestDepsAdapterErrors:
    def test_run_raises_when_no_dep_file(self, tmp_path):
        with pytest.raises(AdapterError) as exc_info:
            DepsAdapter().run(tmp_path)
        assert exc_info.value.reason_code == "no_config"


class TestDepsAdapterConfidence:
    def setup_method(self):
        self.adapter = DepsAdapter()

    def test_confidence_full_when_deps_found(self):
        ctx = WalkerContext(total_files=10, files_by_language={})
        parsed = {"python": {"runtime": ["typer"], "dev": [], "total": 1, "source_file": "pyproject.toml"}}
        assert self.adapter.confidence(parsed, ctx) == 1.0

    def test_confidence_zero_when_empty(self):
        ctx = WalkerContext(total_files=10, files_by_language={})
        assert self.adapter.confidence({}, ctx) == 0.0
