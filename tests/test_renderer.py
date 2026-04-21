"""Tests for repo_cart.core.renderer."""

import io
import json

from repo_cart.core.renderer import to_terminal, to_json, to_markdown, write_outputs


_SNAPSHOT = {
    "schema_version": "1.1",
    "repo": "/some/repo",
    "scanned_at": "2026-04-19T16:00:00+00:00",
    "layers": {
        "structure": {
            "source": "walker",
            "confidence": 1.0,
            "data": {
                "file_count": 42,
                "languages": {"python": 30, "typescript": 12},
                "top_dirs": ["src", "tests"],
                "unreadable_dirs": [],
            },
        },
        "complexity": {
            "source": "radon",
            "confidence": 0.9,
            "data": {
                "avg_complexity": 4.2,
                "function_count": 10,
                "hotspots": [
                    {"file": "src/main.py", "name": "fn", "complexity": 12, "grade": "B", "type": "function", "line": 1},
                ],
            },
        },
    },
    "skipped_layers": [
        {"layer": "lint", "adapter": "eslint", "reason_code": "not_installed", "reason": "eslint not found"},
    ],
}


class TestToTerminal:
    def test_includes_repo_path(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "/some/repo" in out.getvalue()

    def test_includes_layer_names(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        text = out.getvalue()
        assert "STRUCTURE" in text
        assert "COMPLEXITY" in text

    def test_includes_skipped_layers(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "SKIPPED" in out.getvalue()
        assert "lint" in out.getvalue()

    def test_hotspot_shown(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "src/main.py" in out.getvalue()

    def test_no_warning_when_unreadable_dirs_empty(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "Warning" not in out.getvalue()

    def test_warning_shown_when_unreadable_dirs_present(self):
        snapshot = {**_SNAPSHOT, "layers": {
            **_SNAPSHOT["layers"],
            "structure": {
                **_SNAPSHOT["layers"]["structure"],
                "data": {**_SNAPSHOT["layers"]["structure"]["data"], "unreadable_dirs": ["/repo/secret"]},
            },
        }}
        out = io.StringIO()
        to_terminal(snapshot, use_color=False, file=out)
        assert "Warning" in out.getvalue()
        assert "1 directory" in out.getvalue()

    def test_no_color_strips_ansi(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "\033[" not in out.getvalue()


class TestRenderComplexity:
    def test_shows_avg_complexity(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "Avg complexity: 4.2" in out.getvalue()

    def test_shows_hotspot_file(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "src/main.py" in out.getvalue()

    def test_shows_cc_and_grade(self):
        out = io.StringIO()
        to_terminal(_SNAPSHOT, use_color=False, file=out)
        assert "CC=12" in out.getvalue()
        assert "B" in out.getvalue()

    def test_markdown_has_avg(self):
        result = to_markdown(_SNAPSHOT)
        assert "4.2" in result

    def test_markdown_has_hotspot_table(self):
        result = to_markdown(_SNAPSHOT)
        assert "| File |" in result
        assert "src/main.py" in result

    def test_empty_hotspots_renders_cleanly(self):
        snapshot = {**_SNAPSHOT, "layers": {
            **_SNAPSHOT["layers"],
            "complexity": {
                "source": "radon",
                "confidence": 0.0,
                "data": {"avg_complexity": 0.0, "function_count": 0, "hotspots": []},
            },
        }}
        out = io.StringIO()
        to_terminal(snapshot, use_color=False, file=out)
        assert "Avg complexity: 0.0" in out.getvalue()


_LINT_SNAPSHOT = {
    **_SNAPSHOT,
    "layers": {
        **_SNAPSHOT["layers"],
        "lint": {
            "source": "eslint",
            "confidence": 0.75,
            "data": {
                "error_count": 3,
                "warning_count": 1,
                "files_with_issues": [
                    {
                        "file": "/repo/src/index.ts",
                        "errors": 3,
                        "warnings": 1,
                        "messages": [
                            {"rule": "no-unused-vars", "severity": 2, "line": 5, "message": "unused"},
                        ],
                    }
                ],
            },
        },
    },
}


class TestRenderLint:
    def test_shows_error_and_warning_counts(self):
        out = io.StringIO()
        to_terminal(_LINT_SNAPSHOT, use_color=False, file=out)
        assert "3 errors" in out.getvalue()
        assert "1 warning" in out.getvalue()

    def test_shows_file_with_issue(self):
        out = io.StringIO()
        to_terminal(_LINT_SNAPSHOT, use_color=False, file=out)
        assert "index.ts" in out.getvalue()

    def test_shows_rule_name(self):
        out = io.StringIO()
        to_terminal(_LINT_SNAPSHOT, use_color=False, file=out)
        assert "no-unused-vars" in out.getvalue()

    def test_markdown_has_error_count(self):
        result = to_markdown(_LINT_SNAPSHOT)
        assert "3 errors" in result

    def test_markdown_has_file_table(self):
        result = to_markdown(_LINT_SNAPSHOT)
        assert "| File |" in result
        assert "index.ts" in result

    def test_no_errors_renders_cleanly(self):
        snapshot = {**_LINT_SNAPSHOT, "layers": {
            **_LINT_SNAPSHOT["layers"],
            "lint": {
                "source": "eslint",
                "confidence": 0.5,
                "data": {"error_count": 0, "warning_count": 0, "files_with_issues": []},
            },
        }}
        out = io.StringIO()
        to_terminal(snapshot, use_color=False, file=out)
        assert "0 errors" in out.getvalue()


_TYPES_SNAPSHOT = {
    **_SNAPSHOT,
    "layers": {
        **_SNAPSHOT["layers"],
        "types": {
            "source": "tsc",
            "confidence": 0.60,
            "data": {
                "error_count": 2,
                "warning_count": 1,
                "errors": [
                    {"file": "src/main.ts", "line": 10, "col": 5, "code": "TS2322",
                     "message": "Type 'string' is not assignable to type 'number'."},
                    {"file": "src/util.ts", "line": 3, "col": 1, "code": "TS2304",
                     "message": "Cannot find name 'foo'."},
                ],
            },
        },
    },
}


class TestRenderTypes:
    def test_shows_error_and_warning_counts(self):
        out = io.StringIO()
        to_terminal(_TYPES_SNAPSHOT, use_color=False, file=out)
        assert "2 errors" in out.getvalue()
        assert "1 warning" in out.getvalue()

    def test_shows_file_and_line(self):
        out = io.StringIO()
        to_terminal(_TYPES_SNAPSHOT, use_color=False, file=out)
        assert "src/main.ts:10" in out.getvalue()

    def test_shows_error_code(self):
        out = io.StringIO()
        to_terminal(_TYPES_SNAPSHOT, use_color=False, file=out)
        assert "TS2322" in out.getvalue()

    def test_markdown_has_error_count(self):
        result = to_markdown(_TYPES_SNAPSHOT)
        assert "2 type errors" in result

    def test_markdown_has_error_table(self):
        result = to_markdown(_TYPES_SNAPSHOT)
        assert "| File |" in result
        assert "TS2322" in result

    def test_no_errors_renders_cleanly(self):
        snapshot = {**_TYPES_SNAPSHOT, "layers": {
            **_TYPES_SNAPSHOT["layers"],
            "types": {
                "source": "tsc",
                "confidence": 0.5,
                "data": {"error_count": 0, "warning_count": 0, "errors": []},
            },
        }}
        out = io.StringIO()
        to_terminal(snapshot, use_color=False, file=out)
        assert "0 errors" in out.getvalue()


_TEST_COVERAGE_SNAPSHOT = {
    **_SNAPSHOT,
    "layers": {
        **_SNAPSHOT["layers"],
        "test_coverage": {
            "source": "test_coverage_adapter",
            "confidence": 0.5,
            "data": {
                "by_language": {
                    "python": {
                        "source_files": 4,
                        "test_files": 2,
                        "heuristic_ratio": 0.5,
                        "untested_modules": ["src/utils.py"],
                    }
                },
                "coverage_xml_present": False,
                "line_rate": None,
                "branch_rate": None,
                "coverage_xml_timestamp": None,
            },
        },
    },
}

_TEST_COVERAGE_XML_SNAPSHOT = {
    **_SNAPSHOT,
    "layers": {
        **_SNAPSHOT["layers"],
        "test_coverage": {
            "source": "test_coverage_adapter",
            "confidence": 1.0,
            "data": {
                "by_language": {},
                "coverage_xml_present": True,
                "line_rate": 0.87,
                "branch_rate": 0.72,
                "coverage_xml_timestamp": "2026-04-20T10:00:00",
            },
        },
    },
}


class TestRenderTestCoverage:
    def test_shows_language_and_ratio(self):
        out = io.StringIO()
        to_terminal(_TEST_COVERAGE_SNAPSHOT, use_color=False, file=out)
        assert "python" in out.getvalue()
        assert "50%" in out.getvalue()

    def test_shows_untested_module(self):
        out = io.StringIO()
        to_terminal(_TEST_COVERAGE_SNAPSHOT, use_color=False, file=out)
        assert "utils.py" in out.getvalue()

    def test_shows_line_rate_from_xml(self):
        out = io.StringIO()
        to_terminal(_TEST_COVERAGE_XML_SNAPSHOT, use_color=False, file=out)
        assert "87%" in out.getvalue()
        assert "coverage.xml" in out.getvalue()

    def test_markdown_shows_ratio(self):
        result = to_markdown(_TEST_COVERAGE_SNAPSHOT)
        assert "50%" in result

    def test_markdown_shows_line_rate_from_xml(self):
        result = to_markdown(_TEST_COVERAGE_XML_SNAPSHOT)
        assert "87%" in result
        assert "coverage.xml" in result


class TestToJson:
    def test_valid_json(self):
        result = to_json(_SNAPSHOT)
        parsed = json.loads(result)
        assert parsed["schema_version"] == "1.1"

    def test_pretty_printed(self):
        result = to_json(_SNAPSHOT)
        assert "\n" in result


class TestToMarkdown:
    def test_contains_repo_name(self):
        result = to_markdown(_SNAPSHOT)
        assert "repo" in result.lower()

    def test_contains_hotspot_table(self):
        result = to_markdown(_SNAPSHOT)
        assert "| File |" in result or "File" in result

    def test_contains_skipped_table(self):
        result = to_markdown(_SNAPSHOT)
        assert "Skipped" in result

    def test_warning_in_markdown_when_unreadable_dirs(self):
        snapshot = {**_SNAPSHOT, "layers": {
            **_SNAPSHOT["layers"],
            "structure": {
                **_SNAPSHOT["layers"]["structure"],
                "data": {**_SNAPSHOT["layers"]["structure"]["data"], "unreadable_dirs": ["/repo/a", "/repo/b"]},
            },
        }}
        result = to_markdown(snapshot)
        assert "Warning" in result
        assert "2 directories" in result


class TestWriteOutputs:
    def test_writes_json_and_md_files(self, tmp_path):
        write_outputs(_SNAPSHOT, output_dir=tmp_path, use_color=False, stdout_mode=False)

        assert (tmp_path / "repo-cart.json").exists()
        assert (tmp_path / "repo-cart.md").exists()

    def test_json_file_is_valid(self, tmp_path):
        write_outputs(_SNAPSHOT, output_dir=tmp_path, use_color=False, stdout_mode=False)

        data = json.loads((tmp_path / "repo-cart.json").read_text())
        assert data["schema_version"] == "1.1"
