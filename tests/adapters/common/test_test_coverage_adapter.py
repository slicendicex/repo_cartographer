"""Tests for TestCoverageAdapter."""

from pathlib import Path

import pytest

from repo_cart.adapters.base import AdapterError, WalkerContext
from repo_cart.adapters.common.test_coverage_adapter import TestCoverageAdapter

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "simple-python"


class TestTestCoverageAdapterCheck:
    def test_check_always_true(self):
        assert TestCoverageAdapter().check() is True


class TestTestCoverageAdapterHappyPath:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_happy_path_partial_coverage(self):
        result = self.adapter.parse(self.adapter.run(FIXTURE))
        # core.py has test_core.py — tested. utils.py has no test — untested.
        assert result["source_files"] == 2
        assert result["test_files"] == 1
        assert result["coverage_ratio"] == 0.5
        assert any("utils.py" in m for m in result["untested_modules"])
        assert not any("core.py" in m for m in result["untested_modules"])

    def test_fully_tested_repo(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_core.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_ratio"] == 1.0
        assert result["untested_modules"] == []

    def test_empty_tests_dir(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["test_files"] == 0
        assert result["coverage_ratio"] == 0.0
        assert any("core.py" in m for m in result["untested_modules"])


class TestTestCoverageAdapterErrors:
    def test_run_raises_when_no_tests_dir(self, tmp_path):
        with pytest.raises(AdapterError) as exc_info:
            TestCoverageAdapter().run(tmp_path)
        assert exc_info.value.reason_code == "no_config"


class TestTestCoverageAdapterRatioGuards:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_zero_source_files_ratio_guard(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["source_files"] == 0
        assert result["coverage_ratio"] == 0.0

    def test_coverage_ratio_capped_at_one(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("x = 1")
        tests = tmp_path / "tests"
        tests.mkdir()
        for i in range(5):
            (tests / f"test_extra_{i}.py").write_text("")
        (tests / "test_core.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["coverage_ratio"] == 1.0


class TestTestCoverageAdapterStemMatch:
    def setup_method(self):
        self.adapter = TestCoverageAdapter()

    def test_stem_match_test_prefix(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "renderer.py").write_text("x = 1")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_renderer.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["untested_modules"] == []

    def test_stem_match_test_suffix(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "renderer.py").write_text("x = 1")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "renderer_test.py").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["untested_modules"] == []

    def test_typescript_test_files_counted(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("x = 1")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "core.test.ts").write_text("")
        (tests / "utils.spec.ts").write_text("")
        result = self.adapter.parse(self.adapter.run(tmp_path))
        assert result["test_files"] == 2


class TestTestCoverageAdapterConfidence:
    def test_confidence_uses_total_files(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=20, files_by_language={})
        parsed = {"test_files": 4, "source_files": 10, "coverage_ratio": 0.4, "untested_modules": []}
        assert adapter.confidence(parsed, ctx) == pytest.approx(0.2)

    def test_confidence_capped_at_one(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=2, files_by_language={})
        parsed = {"test_files": 10, "source_files": 5, "coverage_ratio": 1.0, "untested_modules": []}
        assert adapter.confidence(parsed, ctx) == 1.0

    def test_confidence_zero_when_no_total_files(self):
        adapter = TestCoverageAdapter()
        ctx = WalkerContext(total_files=0, files_by_language={})
        parsed = {"test_files": 0, "source_files": 0, "coverage_ratio": 0.0, "untested_modules": []}
        assert adapter.confidence(parsed, ctx) == 0.0
