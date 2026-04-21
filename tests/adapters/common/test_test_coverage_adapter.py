"""Tests for TestCoverageAdapter."""

from pathlib import Path

import pytest

from repo_cart.adapters.base import WalkerContext
from repo_cart.adapters.common.test_coverage_adapter import TestCoverageAdapter

SIMPLE_PYTHON = Path(__file__).parent.parent.parent / "fixtures" / "simple-python"
TS_COLOCATED = Path(__file__).parent.parent.parent / "fixtures" / "ts-colocated"


class TestCheck:
    def test_check_always_true(self):
        assert TestCoverageAdapter().check() is True


class TestPythonHappyPath:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_partial_coverage_simple_python_fixture(self):
        result = self.adapter.parse(self.adapter.run(SIMPLE_PYTHON))
        py = result["by_language"]["python"]
        assert py["source_files"] == 2
        assert py["test_files"] == 1
        assert py["heuristic_ratio"] == 0.5
        assert any("utils.py" in m for m in py["untested_modules"])
        assert not any("core.py" in m for m in py["untested_modules"])

    def test_fully_tested_repo(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_core.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        py = result["by_language"]["python"]
        assert py["heuristic_ratio"] == 1.0
        assert py["untested_modules"] == []

    def test_stem_match_test_suffix(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "renderer.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "renderer_test.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["by_language"]["python"]["untested_modules"] == []

    def test_no_tests_dir_returns_zero_not_error(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        py = result["by_language"]["python"]
        assert py["heuristic_ratio"] == 0.0
        assert any("core.py" in m for m in py["untested_modules"])

    def test_zero_source_files_ratio_zero(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        py = result["by_language"]["python"]
        assert py["source_files"] == 0
        assert py["heuristic_ratio"] == 0.0

    def test_ratio_capped_at_one(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        for i in range(5):
            (tmp_path / "tests" / f"test_extra_{i}.py").write_text("")
        (tmp_path / "tests" / "test_core.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["by_language"]["python"]["heuristic_ratio"] == 1.0


class TestTypescriptDiscovery:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_colocated_ts_tests_discovered(self):
        result = self.adapter.parse(self.adapter.run(TS_COLOCATED))
        ts = result["by_language"]["typescript"]
        assert ts["source_files"] == 2
        assert ts["test_files"] == 1

    def test_colocated_ts_ratio(self):
        result = self.adapter.parse(self.adapter.run(TS_COLOCATED))
        ts = result["by_language"]["typescript"]
        assert ts["heuristic_ratio"] == 0.5

    def test_ts_test_patterns_recognized(self, tmp_path):
        for ext in ("test.ts", "spec.ts", "test.tsx", "spec.tsx"):
            (tmp_path / f"foo.{ext}").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["by_language"]["typescript"]["test_files"] == 4

    def test_js_test_patterns_recognized(self, tmp_path):
        for ext in ("test.js", "spec.js", "test.jsx"):
            (tmp_path / f"bar.{ext}").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["by_language"]["javascript"]["test_files"] == 3

    def test_dts_files_excluded_from_source(self, tmp_path):
        (tmp_path / "types.d.ts").write_text("")
        (tmp_path / "main.ts").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        ts = result["by_language"]["typescript"]
        assert ts["source_files"] == 1

    def test_no_tests_returns_empty_by_language(self, tmp_path):
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["by_language"] == {}
        assert result["coverage_xml_present"] is False


class TestCoverageXml:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_coverage_xml_populates_line_rate(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?>'
            '<coverage line-rate="0.87" branch-rate="0.72" version="7.2"></coverage>'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_present"] is True
        assert result["line_rate"] == pytest.approx(0.87)
        assert result["branch_rate"] == pytest.approx(0.72)

    def test_coverage_xml_absent_line_rate_null(self, tmp_path):
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_present"] is False
        assert result["line_rate"] is None
        assert result["branch_rate"] is None

    def test_coverage_xml_timestamp_present(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<coverage line-rate="0.9" branch-rate="0.8"></coverage>'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_timestamp"] is not None
        assert "T" in result["coverage_xml_timestamp"]

    def test_malformed_coverage_xml_falls_back(self, tmp_path):
        (tmp_path / "coverage.xml").write_text("not xml at all <<<")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_present"] is False
        assert result["line_rate"] is None

    def test_coverage_xml_missing_line_rate_falls_back(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<coverage branch-rate="0.5"></coverage>'
        )
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_present"] is False

    def test_empty_coverage_xml_falls_back(self, tmp_path):
        (tmp_path / "coverage.xml").write_bytes(b"")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_xml_present"] is False


class TestConfidence:
    def test_confidence_uses_test_file_ratio(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=20, files_by_language={})
        parsed = {
            "by_language": {"python": {"test_files": 4}},
            "coverage_xml_present": False,
        }
        assert adapter.confidence(parsed, ctx) == pytest.approx(0.2)

    def test_confidence_one_when_xml_present(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=20, files_by_language={})
        parsed = {"by_language": {}, "coverage_xml_present": True}
        assert adapter.confidence(parsed, ctx) == 1.0

    def test_confidence_zero_when_no_total_files(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=0, files_by_language={})
        parsed = {"by_language": {}, "coverage_xml_present": False}
        assert adapter.confidence(parsed, ctx) == 0.0

    def test_confidence_capped_at_one(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=2, files_by_language={})
        parsed = {
            "by_language": {"python": {"test_files": 10}},
            "coverage_xml_present": False,
        }
        assert adapter.confidence(parsed, ctx) == 1.0
