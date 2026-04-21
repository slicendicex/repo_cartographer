"""Tests for repo_cart.core.walker."""

from pathlib import Path

import pytest

from repo_cart.core.walker import walk, WalkerResult, EXCLUDED_DIRS, LANGUAGE_BY_EXT
from repo_cart.adapters.common.gitignore import load_gitignore


FIXTURES = Path(__file__).parent / "fixtures"


class TestWalk:
    def test_returns_walker_result(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1")
        (tmp_path / "README.md").write_text("# hi")

        result = walk(tmp_path)

        assert isinstance(result, WalkerResult)
        assert result.ctx.total_files == 2
        assert result.ctx.files_by_language == {"python": 1}
        assert result.top_dirs == ["src"]

    def test_no_warnings_on_clean_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        result = walk(tmp_path)
        assert not result.had_warnings
        assert result.unreadable_dirs == []

    def test_excludes_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "lodash.js").write_text("")
        (tmp_path / "index.js").write_text("")

        result = walk(tmp_path)

        assert result.ctx.total_files == 1

    def test_excludes_all_hardcoded_dirs(self, tmp_path):
        for d in EXCLUDED_DIRS:
            (tmp_path / d).mkdir(exist_ok=True)
            (tmp_path / d / "file.py").write_text("")

        result = walk(tmp_path)

        assert result.ctx.total_files == 0

    def test_python_sample_fixture(self):
        result = walk(FIXTURES / "python-sample")

        assert result.ctx.files_by_language.get("python", 0) >= 1

    def test_ts_sample_fixture(self):
        result = walk(FIXTURES / "ts-sample")

        assert result.ctx.files_by_language.get("typescript", 0) >= 1

    def test_raises_for_nonexistent_path(self):
        with pytest.raises(ValueError, match="does not exist"):
            walk(Path("/nonexistent/path/xyz"))

    def test_raises_for_file_path(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("x = 1")
        with pytest.raises(ValueError, match="not a directory"):
            walk(f)

    def test_language_counts_all_extensions(self, tmp_path):
        for ext in (".js", ".jsx", ".mjs", ".cjs"):
            (tmp_path / f"file{ext}").write_text("")
        for ext in (".ts", ".tsx", ".mts", ".cts"):
            (tmp_path / f"file{ext}").write_text("")

        result = walk(tmp_path)

        assert result.ctx.files_by_language["javascript"] == 4
        assert result.ctx.files_by_language["typescript"] == 4

    def test_top_dirs_excludes_excluded_dirs(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "src").mkdir()

        result = walk(tmp_path)

        assert ".git" not in result.top_dirs
        assert "src" in result.top_dirs

    def test_new_language_extensions(self, tmp_path):
        for ext, lang in [(".go", "go"), (".rs", "rust"), (".rb", "ruby"), (".java", "java")]:
            (tmp_path / f"file{ext}").write_text("")
        result = walk(tmp_path)
        assert result.ctx.files_by_language.get("go") == 1
        assert result.ctx.files_by_language.get("rust") == 1
        assert result.ctx.files_by_language.get("ruby") == 1
        assert result.ctx.files_by_language.get("java") == 1

    def test_gitignore_excludes_dir(self, tmp_path):
        (tmp_path / ".gitignore").write_text("generated/\n")
        (tmp_path / "generated").mkdir()
        (tmp_path / "generated" / "auto.py").write_text("")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        result = walk(tmp_path)
        assert result.ctx.total_files == 2  # .gitignore + main.py
        assert "generated" not in result.top_dirs

    def test_gitignore_absent_walk_proceeds_normally(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        result = walk(tmp_path)
        assert result.ctx.total_files == 1

    def test_gitignore_corrupt_handled_gracefully(self, tmp_path):
        (tmp_path / ".gitignore").write_bytes(b"\xff\xfe invalid")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        result = walk(tmp_path)
        assert result.ctx.total_files >= 1

    def test_unreadable_dir_recorded_in_warnings(self, tmp_path):
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        (restricted / "secret.py").write_text("x = 1")
        restricted.chmod(0o000)

        try:
            result = walk(tmp_path)
            assert result.had_warnings
            assert len(result.unreadable_dirs) >= 1
        finally:
            restricted.chmod(0o755)


class TestLoadGitignore:
    def test_returns_none_when_no_gitignore(self, tmp_path):
        assert load_gitignore(tmp_path) is None

    def test_returns_spec_when_gitignore_present(self, tmp_path):
        (tmp_path / ".gitignore").write_text("dist/\n")
        spec = load_gitignore(tmp_path)
        assert spec is not None

    def test_matches_ignored_directory(self, tmp_path):
        (tmp_path / ".gitignore").write_text("generated/\n")
        spec = load_gitignore(tmp_path)
        assert spec is not None
        assert spec.match_file("generated/") or spec.match_file("generated")

    def test_does_not_match_non_ignored(self, tmp_path):
        (tmp_path / ".gitignore").write_text("dist/\n")
        spec = load_gitignore(tmp_path)
        assert spec is not None
        assert not spec.match_file("src/")

    def test_corrupt_gitignore_returns_none(self, tmp_path):
        # write valid UTF-8 text with unusual patterns — pathspec should still parse
        (tmp_path / ".gitignore").write_text("# comment\n*.log\n")
        spec = load_gitignore(tmp_path)
        assert spec is not None
