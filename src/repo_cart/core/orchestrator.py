"""
Orchestrator — discovers available adapters, runs them concurrently,
and assembles the final snapshot dict.

Data flow:
    scan(path)
        │
        ├── walker.walk(path) ──────────────────► WalkerResult (ctx, top_dirs,
        │                                          unreadable_dirs); always attempted
        │
        ├── adapter.check() for each adapter
        │       True  → schedule run()
        │       False → add to skipped_layers[reason_code=not_installed]
        │
        ├── ThreadPoolExecutor(max_workers=len(runnable_adapters))
        │       adapter.run(path) → raw str
        │       adapter.parse(raw) → layer data dict
        │       adapter.confidence(parsed, ctx) → float
        │       AdapterError → skipped_layers[reason_code=from error]
        │       TimeoutError → skipped_layers[reason_code=timeout]
        │
        └── assemble_snapshot(ctx, top_dirs, layers, skipped_layers)
"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from typing import Any

from repo_cart.adapters.base import AdapterBase, AdapterError, WalkerContext
from repo_cart.core.walker import walk, WalkerResult


def scan(path: Path, adapters: list[AdapterBase]) -> dict[str, Any]:
    """
    Run a full scan of ``path`` using the provided adapters.

    Returns a snapshot dict matching the schema defined in the design doc.
    The ``structure`` layer is always present. All other layers depend on
    adapter availability and success.
    """
    resolved = path.resolve()

    # Step 1: walk the repo — always attempted, provides WalkerContext.
    result: WalkerResult = walk(resolved)
    ctx = result.ctx
    top_dirs = result.top_dirs

    # Confidence is 1.0 only when the traversal was complete (no unreadable dirs).
    walk_confidence = 1.0 if not result.had_warnings else round(
        1.0 - len(result.unreadable_dirs) / max(ctx.total_files, 1), 2
    )

    structure_layer: dict[str, Any] = {
        "source": "walker",
        "confidence": walk_confidence,
        "data": {
            "file_count": ctx.total_files,
            "languages": ctx.files_by_language,
            "top_dirs": top_dirs,
            "unreadable_dirs": result.unreadable_dirs,
        },
    }

    layers: dict[str, Any] = {"structure": structure_layer}
    skipped: list[dict[str, Any]] = []

    # Step 2: check which adapters are available.
    runnable: list[AdapterBase] = []
    for adapter in adapters:
        try:
            if adapter.check():
                runnable.append(adapter)
            else:
                skipped.append(_skipped_entry(adapter, "not_installed"))
        except Exception as exc:
            skipped.append(_skipped_entry(adapter, "parse_error", str(exc)))

    # Step 3: run available adapters concurrently.
    if runnable:
        future_to_adapter: dict[Future, AdapterBase] = {}
        with ThreadPoolExecutor(max_workers=len(runnable)) as executor:
            for adapter in runnable:
                future = executor.submit(_run_adapter, adapter, resolved, ctx)
                future_to_adapter[future] = adapter

            for future in as_completed(future_to_adapter):
                adapter = future_to_adapter[future]
                try:
                    layer_key, layer_data = future.result(timeout=adapter.timeout + 1)
                    layers[layer_key] = layer_data
                except AdapterError as exc:
                    skipped.append(_skipped_entry(adapter, exc.reason_code, str(exc)))
                except TimeoutError:
                    skipped.append(_skipped_entry(adapter, "timeout"))
                except Exception as exc:
                    skipped.append(_skipped_entry(adapter, "parse_error", str(exc)))

    return _assemble_snapshot(resolved, layers, skipped)


def _run_adapter(
    adapter: AdapterBase, path: Path, ctx: WalkerContext
) -> tuple[str, dict[str, Any]]:
    """Run one adapter and return (layer_key, layer_dict). Raises AdapterError on failure."""
    raw = adapter.run(path)
    parsed = adapter.parse(raw)
    conf = adapter.confidence(parsed, ctx)
    return adapter.layer, {
        "source": adapter.name,
        "confidence": conf,
        "data": parsed,
    }


def _skipped_entry(
    adapter: AdapterBase,
    reason_code: str,
    message: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "layer": adapter.layer,
        "adapter": adapter.name,
        "reason_code": reason_code,
        "reason": message or reason_code,
    }
    return entry


def _assemble_snapshot(
    repo_path: Path,
    layers: dict[str, Any],
    skipped_layers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "repo": str(repo_path),
        "scanned_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "layers": layers,
        "skipped_layers": skipped_layers,
    }
