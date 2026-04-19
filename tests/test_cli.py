"""Tests for repo_cart.cli."""

from pathlib import Path

from typer.testing import CliRunner

from repo_cart.cli import app

runner = CliRunner()


class TestScanCmd:
    def test_nonexistent_path_exits_1(self):
        result = runner.invoke(app, ["/nonexistent/path/xyz"])
        assert result.exit_code == 1

    def test_file_path_exits_1(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        result = runner.invoke(app, [str(f)])
        assert result.exit_code == 1

    def test_valid_path_exits_0(self, tmp_path):
        result = runner.invoke(app, [str(tmp_path)])
        assert result.exit_code == 0

    def test_stdout_flag_writes_json_to_stdout(self, tmp_path):
        result = runner.invoke(app, ["--stdout", str(tmp_path)])
        assert result.exit_code == 0
        assert "schema_version" in result.output

    def test_no_color_flag_accepted(self, tmp_path):
        result = runner.invoke(app, ["--no-color", str(tmp_path)])
        assert result.exit_code == 0

    def test_default_path_is_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, [])
        assert result.exit_code == 0
