"""Tests for TscAdapter."""

from pathlib import Path
from unittest.mock import patch

import pytest

from repo_cart.adapters.base import AdapterError, WalkerContext
from repo_cart.adapters.js_ts.tsc_adapter import TscAdapter, _find_tsc


_TSC_OUTPUT = """
src/main.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'.
src/util.ts(3,1): error TS2304: Cannot find name 'foo'.
src/util.ts(7,2): warning TS6133: 'unused' is declared but its value is never read.
""".strip()


class TestTscAdapterParse:
    def setup_method(self):
        self.adapter = TscAdapter()

    def test_parse_error_count(self):
        result = self.adapter.parse(_TSC_OUTPUT)
        assert result["error_count"] == 2

    def test_parse_warning_count(self):
        result = self.adapter.parse(_TSC_OUTPUT)
        assert result["warning_count"] == 1

    def test_parse_error_fields(self):
        result = self.adapter.parse(_TSC_OUTPUT)
        first = result["errors"][0]
        assert first["file"] == "src/main.ts"
        assert first["line"] == 10
        assert first["code"] == "TS2322"

    def test_parse_empty_output(self):
        result = self.adapter.parse("")
        assert result["error_count"] == 0
        assert result["errors"] == []

    def test_parse_caps_errors_at_20(self):
        lines = [f"f.ts({i},1): error TS1000: msg" for i in range(30)]
        result = self.adapter.parse("\n".join(lines))
        assert len(result["errors"]) <= 20


class TestTscAdapterRun:
    def setup_method(self):
        self.adapter = TscAdapter()

    def test_raises_no_config_when_tsconfig_absent(self, tmp_path):
        with pytest.raises(AdapterError) as exc_info:
            self.adapter.run(tmp_path)
        assert exc_info.value.reason_code == "no_config"


class TestFindTsc:
    def test_prefers_local_binary(self, tmp_path):
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        tsc = bin_dir / "tsc"
        tsc.write_text("#!/bin/sh")
        tsc.chmod(0o755)

        result = _find_tsc(tmp_path)
        assert result == str(tsc)

    def test_falls_back_to_path(self, tmp_path):
        with patch("shutil.which", return_value="/usr/local/bin/tsc"):
            result = _find_tsc(tmp_path)
        assert result == "/usr/local/bin/tsc"


class TestTscAdapterConfidence:
    def setup_method(self):
        self.adapter = TscAdapter()

    def test_zero_ts_files_returns_zero(self):
        ctx = WalkerContext(total_files=10, files_by_language={"python": 10})
        parsed = {"errors": []}
        assert self.adapter.confidence(parsed, ctx) == 0.0

    def test_no_errors_returns_half(self):
        ctx = WalkerContext(total_files=10, files_by_language={"typescript": 5})
        parsed = {"errors": []}
        assert self.adapter.confidence(parsed, ctx) == 0.5
