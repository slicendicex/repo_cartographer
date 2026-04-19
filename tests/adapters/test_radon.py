"""Tests for RadonAdapter."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from repo_cart.adapters.base import AdapterError, WalkerContext
from repo_cart.adapters.python.radon_adapter import RadonAdapter, _grade


FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "python-sample"

_RADON_OUTPUT = json.dumps({
    "src/main.py": [
        {"name": "simple_function", "complexity": 1, "type": "function", "lineno": 4},
        {"name": "branchy_function", "complexity": 4, "type": "function", "lineno": 10},
        {"name": "complex_function", "complexity": 12, "type": "function", "lineno": 20},
    ]
})


class TestGrade:
    def test_grade_a(self):
        assert _grade(1) == "A"
        assert _grade(5) == "A"

    def test_grade_b(self):
        assert _grade(6) == "B"
        assert _grade(10) == "B"

    def test_grade_c(self):
        assert _grade(11) == "C"

    def test_grade_f(self):
        assert _grade(26) == "F"


class TestRadonAdapterParse:
    def setup_method(self):
        self.adapter = RadonAdapter()

    def test_parse_returns_avg_complexity(self):
        result = self.adapter.parse(_RADON_OUTPUT)
        assert result["avg_complexity"] == round((1 + 4 + 12) / 3, 2)

    def test_parse_returns_function_count(self):
        result = self.adapter.parse(_RADON_OUTPUT)
        assert result["function_count"] == 3

    def test_parse_hotspots_sorted_by_complexity(self):
        result = self.adapter.parse(_RADON_OUTPUT)
        ccs = [h["complexity"] for h in result["hotspots"]]
        assert ccs == sorted(ccs, reverse=True)

    def test_parse_caps_hotspots_at_20(self):
        big = {f"file{i}.py": [{"name": "fn", "complexity": i, "type": "function", "lineno": 1}] for i in range(30)}
        result = self.adapter.parse(json.dumps(big))
        assert len(result["hotspots"]) <= 20

    def test_parse_invalid_json_raises_adapter_error(self):
        with pytest.raises(AdapterError) as exc_info:
            self.adapter.parse("not json")
        assert exc_info.value.reason_code == "parse_error"


class TestRadonAdapterConfidence:
    def setup_method(self):
        self.adapter = RadonAdapter()

    def test_zero_python_files_returns_zero(self):
        ctx = WalkerContext(total_files=10, files_by_language={})
        parsed = {"hotspots": []}
        assert self.adapter.confidence(parsed, ctx) == 0.0

    def test_confidence_capped_at_one(self):
        ctx = WalkerContext(total_files=10, files_by_language={"python": 1})
        parsed = {"hotspots": [{"file": "f1.py"}, {"file": "f2.py"}]}
        assert self.adapter.confidence(parsed, ctx) == 1.0


class TestRadonAdapterCheck:
    def test_check_false_when_radon_absent(self):
        adapter = RadonAdapter()
        with patch("shutil.which", return_value=None):
            assert adapter.check() is False

    def test_check_true_when_radon_present(self):
        adapter = RadonAdapter()
        with patch("shutil.which", return_value="/usr/local/bin/radon"):
            assert adapter.check() is True
