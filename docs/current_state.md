# Current State

Last updated: 2026-04-19 (layers 00, 01, 02 complete — live scan verified)

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
| 03 Types | `types` | tsc | Done |

### Tests

| Suite | File | Tests |
|---|---|---|
| Walker | `tests/test_walker.py` | 12 |
| Orchestrator | `tests/test_orchestrator.py` | 10 |
| Renderer | `tests/test_renderer.py` | 25 |
| CLI | `tests/test_cli.py` | 6 |
| Radon adapter | `tests/adapters/test_radon.py` | 14 |
| ESLint adapter | `tests/adapters/test_eslint.py` | 16 |
| Tsc adapter | `tests/adapters/test_tsc.py` | 11 |
| **Total** | | **93 / 93 passing** |

### Test fixtures

| Fixture | Purpose |
|---|---|
| `tests/fixtures/python-sample/sample.py` | Python file with known CC values (1, 4, 7) |
| `tests/fixtures/ts-sample/sample.ts` | TypeScript file for tsc adapter |
| `tests/fixtures/ts-sample/tsconfig.json` | TypeScript config |
| `tests/fixtures/ts-sample/package.json` | Package manifest |

---

## What's NOT done yet

### Pre-ship blockers (TODOS.md)

| # | Item | Notes |
|---|---|---|
| TODO-1 | Walker symlink guard | Already using `followlinks=False` — confirm in tests |
| TODO-2 | `--stdout` stderr redirect | Already implemented in `renderer.py:write_outputs()` |
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

## Next up (Phase 2)

- Layer 04: Dependencies (`pip-audit` / `npm audit`)
- Layer 05: Coverage (`coverage.py` / `jest --coverage`)
- Custom terminal renderers for lint and types layers
- `.gitignore`-aware walker
