"""Tests for ESLintAdapter."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from repo_cart.adapters.base import AdapterError, WalkerContext
from repo_cart.adapters.js_ts.eslint_adapter import ESLintAdapter, _has_config, _find_eslint


_ESLINT_OUTPUT = json.dumps([
    {
        "filePath": "/repo/src/index.ts",
        "errorCount": 2,
        "warningCount": 1,
        "messages": [
            {"ruleId": "no-unused-vars", "severity": 2, "line": 5, "message": "'x' is unused"},
            {"ruleId": "no-console", "severity": 1, "line": 10, "message": "Unexpected console"},
        ],
    },
    {
        "filePath": "/repo/src/util.ts",
        "errorCount": 0,
        "warningCount": 0,
        "messages": [],
    },
])


class TestESLintAdapterParse:
    def setup_method(self):
        self.adapter = ESLintAdapter()

    def test_parse_error_and_warning_counts(self):
        result = self.adapter.parse(_ESLINT_OUTPUT)
        assert result["error_count"] == 2
        assert result["warning_count"] == 1

    def test_parse_only_includes_files_with_issues(self):
        result = self.adapter.parse(_ESLINT_OUTPUT)
        assert len(result["files_with_issues"]) == 1
        assert result["files_with_issues"][0]["file"] == "/repo/src/index.ts"

    def test_parse_invalid_json_raises_adapter_error(self):
        with pytest.raises(AdapterError) as exc_info:
            self.adapter.parse("not json")
        assert exc_info.value.reason_code == "parse_error"

    def test_parse_caps_files_at_20(self):
        big = [{"filePath": f"f{i}.ts", "errorCount": 1, "warningCount": 0, "messages": []} for i in range(30)]
        result = self.adapter.parse(json.dumps(big))
        assert len(result["files_with_issues"]) <= 20


class TestHasConfig:
    def test_detects_v9_config(self, tmp_path):
        (tmp_path / "eslint.config.js").write_text("")
        assert _has_config(tmp_path) is True

    def test_detects_legacy_eslintrc(self, tmp_path):
        (tmp_path / ".eslintrc.json").write_text("{}")
        assert _has_config(tmp_path) is True

    def test_returns_false_when_no_config(self, tmp_path):
        assert _has_config(tmp_path) is False


class TestFindEslint:
    def test_prefers_local_binary(self, tmp_path):
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        eslint = bin_dir / "eslint"
        eslint.write_text("#!/bin/sh")
        eslint.chmod(0o755)

        result = _find_eslint(tmp_path)
        assert result == str(eslint)

    def test_falls_back_to_path(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/eslint"):
            result = _find_eslint(tmp_path)
        assert result == "/usr/bin/eslint"


class TestESLintAdapterRun:
    def setup_method(self):
        self.adapter = ESLintAdapter()

    def _mock_run(self, returncode, stdout="", stderr=""):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = stdout
        mock.stderr = stderr
        return mock

    def test_raises_no_config_when_missing(self, tmp_path):
        with patch("repo_cart.adapters.js_ts.eslint_adapter._find_eslint", return_value="/usr/bin/eslint"):
            with pytest.raises(AdapterError) as exc_info:
                self.adapter.run(tmp_path)
        assert exc_info.value.reason_code == "no_config"

    def test_exit_0_returns_stdout(self, tmp_path):
        (tmp_path / "eslint.config.js").write_text("")
        with patch("repo_cart.adapters.js_ts.eslint_adapter._find_eslint", return_value="/usr/bin/eslint"), \
             patch("subprocess.run", return_value=self._mock_run(0, stdout=_ESLINT_OUTPUT)):
            result = self.adapter.run(tmp_path)
        assert "filePath" in result

    def test_exit_1_returns_stdout(self, tmp_path):
        # exit 1 = lint errors found — should NOT raise, should return JSON
        (tmp_path / ".eslintrc.json").write_text("{}")
        with patch("repo_cart.adapters.js_ts.eslint_adapter._find_eslint", return_value="/usr/bin/eslint"), \
             patch("subprocess.run", return_value=self._mock_run(1, stdout=_ESLINT_OUTPUT)):
            result = self.adapter.run(tmp_path)
        assert "filePath" in result

    def test_exit_2_raises_parse_error(self, tmp_path):
        (tmp_path / ".eslintrc.json").write_text("{}")
        with patch("repo_cart.adapters.js_ts.eslint_adapter._find_eslint", return_value="/usr/bin/eslint"), \
             patch("subprocess.run", return_value=self._mock_run(2, stderr="Invalid config")):
            with pytest.raises(AdapterError) as exc_info:
                self.adapter.run(tmp_path)
        assert exc_info.value.reason_code == "parse_error"

    def test_timeout_raises_adapter_error(self, tmp_path):
        (tmp_path / ".eslintrc.json").write_text("{}")
        with patch("repo_cart.adapters.js_ts.eslint_adapter._find_eslint", return_value="/usr/bin/eslint"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="eslint", timeout=30)):
            with pytest.raises(AdapterError) as exc_info:
                self.adapter.run(tmp_path)
        assert exc_info.value.reason_code == "timeout"


class TestESLintAdapterConfidence:
    def setup_method(self):
        self.adapter = ESLintAdapter()

    def test_zero_js_ts_files_returns_zero(self):
        ctx = WalkerContext(total_files=10, files_by_language={"python": 10})
        parsed = {"files_with_issues": []}
        assert self.adapter.confidence(parsed, ctx) == 0.0

    def test_no_issues_returns_half(self):
        ctx = WalkerContext(total_files=10, files_by_language={"typescript": 10})
        parsed = {"files_with_issues": []}
        assert self.adapter.confidence(parsed, ctx) == 0.5
