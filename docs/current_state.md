# Current State

Last updated: 2026-04-19 (all MVP layers complete — live scan verified)

---

## Status: Phase 1 MVP — All layers implemented, tests green

---

## What exists

### Core pipeline

| Module | File | Status |
|---|---|---|
| Walker | `src/repo_cart/core/walker.py` | Done — returns `WalkerResult`, tracks `unreadable_dirs` |
| Orchestrator | `src/repo_cart/core/orchestrator.py` | Done |
| Renderer | `src/repo_cart/core/renderer.py` | Done — `unreadable_dirs` warning in terminal + markdown |
| CLI | `src/repo_cart/cli.py` | Done |
| AdapterBase | `src/repo_cart/adapters/base.py` | Done |

### Layers

| Layer | Key | Adapter | Status |
|---|---|---|---|
| 00 Structure | `structure` | walker (built-in) | Done |
| 01 Complexity | `complexity` | radon | Complete — live scan verified |
| 02 Lint | `lint` | eslint | Complete — exit code handling, dedicated renderer |
| 03 Types | `types` | tsc | Complete — exit code fix, dedicated renderer, live scan verified |
| 04 Dependencies | `dependencies` | deps_adapter | Complete — pyproject/requirements/package.json parsing |
| 05 Entry Points | `entry_points` | entry_points_adapter | Complete — CLI commands, __main__.py, package main/bin |
| 06 Test Coverage | `test_coverage` | test_coverage_adapter | Complete — heuristic file ratio + untested module stem-match |

### Tests

| Suite | File | Tests |
|---|---|---|
| Walker | `tests/test_walker.py` | 12 |
| Orchestrator | `tests/test_orchestrator.py` | 10 |
| Renderer | `tests/test_renderer.py` | 31 |
| CLI | `tests/test_cli.py` | 6 |
| Radon adapter | `tests/adapters/test_radon.py` | 14 |
| ESLint adapter | `tests/adapters/test_eslint.py` | 16 |
| Tsc adapter | `tests/adapters/test_tsc.py` | 16 |
| Deps adapter | `tests/adapters/common/test_deps_adapter.py` | 10 |
| Entry points adapter | `tests/adapters/common/test_entry_points_adapter.py` | 14 |
| Test coverage adapter | `tests/adapters/common/test_test_coverage_adapter.py` | 13 |
| **Total** | | **141 / 141 passing** |

### Test fixtures

| Fixture | Purpose |
|---|---|
| `tests/fixtures/python-sample/sample.py` | Python file with known CC values (1, 4, 7) |
| `tests/fixtures/ts-sample/sample.ts` | TypeScript file for tsc adapter |
| `tests/fixtures/ts-sample/tsconfig.json` | TypeScript config |
| `tests/fixtures/ts-sample/package.json` | Package manifest |
| `tests/fixtures/simple-python/` | Python repo with partial test coverage (core.py tested, utils.py untested) |

---

## What's NOT done yet

### Pre-ship blockers (TODOS.md)

| # | Item | Notes |
|---|---|---|
| TODO-1 | Walker symlink guard | Already using `followlinks=False` — confirm in tests |
| ~~TODO-2~~ | ~~`--stdout` stderr redirect~~ | Done — implemented in `renderer.py:write_outputs()` |
| TODO-3 | eslint dual-config detection | Already implemented in `eslint_adapter.py` |

All three TODOs may already be resolved in the current implementation. Needs verification.

### Custom terminal renderers

Lint (layer 02) and Types (layer 03) currently use the generic renderer:
```
LINT (eslint, confidence: 0.75)
  {'error_count': 12, ...}
```
A dedicated `_render_lint()` and `_render_types()` in `renderer.py` is a Phase 2 item.

### Packaging / install

`pyproject.toml` is configured. `pip install -e .` works when `typer` is present.
Not yet published to PyPI.

---

## Usage

```bash
# Install
pip install -e ".[dev]"

# Scan current directory
repo-cart

# Scan specific path
repo-cart /path/to/repo

# JSON to stdout for piping
repo-cart --stdout /path/to/repo | jq '.layers'

# No color (CI)
repo-cart --no-color /path/to/repo

# Run tests
pytest tests/
```

---

## Next up (Phase 2 — file-parsing layers)

Implementation order (each layer is an independent slice):

| Layer | Key | Adapter | Location | Prerequisite |
|---|---|---|---|---|
| 04 | `dependencies` | `deps_adapter` | `adapters/common/` | Creates `adapters/common/`, renderer dispatch table refactor |
| 05 | `entry_points` | `entry_points_adapter` | `adapters/common/` | Layer 04 (dispatch table must exist) |
| 06 | `test_coverage` | `test_coverage_adapter` | `adapters/common/` | Layer 04, adds `tests/fixtures/simple-python/` |

All three: pure file parsing, `check()` always returns `True`, registered in `cli.py:_DEFAULT_ADAPTERS`.

See `docs/layer-04.md`, `docs/layer-05.md`, `docs/layer-06.md` for specs and test plans.
