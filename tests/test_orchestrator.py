"""Tests for repo_cart.core.orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext
from repo_cart.core.orchestrator import scan


def _make_adapter(
    *,
    name="mock",
    language="python",
    layer="mock_layer",
    check_returns=True,
    run_returns='{"result": true}',
    parse_returns=None,
    confidence_returns=0.8,
):
    adapter = MagicMock(spec=AdapterBase)
    adapter.name = name
    adapter.language = language
    adapter.layer = layer
    adapter.timeout = 30
    adapter.check.return_value = check_returns
    adapter.run.return_value = run_returns
    adapter.parse.return_value = parse_returns or {"result": True}
    adapter.confidence.return_value = confidence_returns
    return adapter


class TestScan:
    def test_structure_layer_always_present(self, tmp_path):
        snapshot = scan(tmp_path, [])

        assert "structure" in snapshot["layers"]

    def test_structure_layer_has_unreadable_dirs_field(self, tmp_path):
        snapshot = scan(tmp_path, [])
        data = snapshot["layers"]["structure"]["data"]
        assert "unreadable_dirs" in data

    def test_structure_confidence_is_1_on_clean_tree(self, tmp_path):
        snapshot = scan(tmp_path, [])
        assert snapshot["layers"]["structure"]["confidence"] == 1.0

    def test_schema_version_present(self, tmp_path):
        snapshot = scan(tmp_path, [])

        assert snapshot["schema_version"] == "1.1"

    def test_repo_path_in_snapshot(self, tmp_path):
        snapshot = scan(tmp_path, [])

        assert snapshot["repo"] == str(tmp_path)

    def test_scanned_at_present(self, tmp_path):
        snapshot = scan(tmp_path, [])

        assert "scanned_at" in snapshot
        assert snapshot["scanned_at"]

    def test_adapter_not_installed_goes_to_skipped(self, tmp_path):
        adapter = _make_adapter(check_returns=False)

        snapshot = scan(tmp_path, [adapter])

        assert any(s["reason_code"] == "not_installed" for s in snapshot["skipped_layers"])
        assert adapter.layer not in snapshot["layers"]

    def test_successful_adapter_adds_layer(self, tmp_path):
        adapter = _make_adapter(layer="complexity")

        snapshot = scan(tmp_path, [adapter])

        assert "complexity" in snapshot["layers"]
        assert snapshot["layers"]["complexity"]["confidence"] == 0.8

    def test_adapter_run_raises_adapter_error(self, tmp_path):
        adapter = _make_adapter()
        adapter.run.side_effect = AdapterError("boom", "parse_error")

        snapshot = scan(tmp_path, [adapter])

        assert any(s["reason_code"] == "parse_error" for s in snapshot["skipped_layers"])

    def test_multiple_adapters_run_concurrently(self, tmp_path):
        adapters = [_make_adapter(name=f"a{i}", layer=f"layer{i}") for i in range(3)]

        snapshot = scan(tmp_path, adapters)

        for i in range(3):
            assert f"layer{i}" in snapshot["layers"]
