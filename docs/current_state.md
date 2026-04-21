# Current State

Last updated: 2026-04-21 (Phase 1 + 2 complete, Layer 07 added, quality improvements — 8 layers, 186 tests green)

---

## Status: Phase 1 + 2 complete, Layer 07 (Git Activity) added — no blocking TODOs

---

## What exists

### Core pipeline

| Module | File | Status |
|---|---|---|
| Walker | `src/repo_cart/core/walker.py` | Done — gitignore parsing, 20+ languages, `unreadable_dirs` |
| Orchestrator | `src/repo_cart/core/orchestrator.py` | Done — schema_version 1.1 |
| Renderer | `src/repo_cart/core/renderer.py` | Done — per-language test coverage, coverage.xml support |
| CLI | `src/repo_cart/cli.py` | Done |
| AdapterBase | `src/repo_cart/adapters/base.py` | Done |
| Gitignore utility | `src/repo_cart/adapters/common/gitignore.py` | Done — pathspec-backed, shared by walker + adapters |

### Layers

| Layer | Key | Adapter | Status |
|---|---|---|---|
| 00 Structure | `structure` | walker (built-in) | Done — gitignore-aware, 20+ languages |
| 01 Complexity | `complexity` | radon | Complete — live scan verified |
| 02 Lint | `lint` | eslint | Complete — exit code handling, dedicated renderer |
| 03 Types | `types` | tsc | Complete — exit code fix, dedicated renderer, live scan verified |
| 04 Dependencies | `dependencies` | deps_adapter | Complete — pyproject/requirements/package.json parsing |
| 05 Entry Points | `entry_points` | entry_points_adapter | Complete — CLI commands, __main__.py, package main/bin |
| 06 Test Coverage | `test_coverage` | test_coverage_adapter | Complete — per-language breakdown, whole-tree discovery, coverage.xml support |
| 07 Git Activity | `git_activity` | git_activity_adapter | Complete — sentinel git log parsing, --window flag, coverage/confidence split |

### Tests

| Suite | File | Tests |
|---|---|---|
| Walker | `tests/test_walker.py` | 21 |
| Orchestrator | `tests/test_orchestrator.py` | 10 |
| Renderer | `tests/test_renderer.py` | 36 |
| CLI | `tests/test_cli.py` | 6 |
| Radon adapter | `tests/adapters/test_radon.py` | 14 |
| ESLint adapter | `tests/adapters/test_eslint.py` | 16 |
| Tsc adapter | `tests/adapters/test_tsc.py` | 16 |
| Deps adapter | `tests/adapters/common/test_deps_adapter.py` | 12 |
| Entry points adapter | `tests/adapters/common/test_entry_points_adapter.py` | 14 |
| Test coverage adapter | `tests/adapters/common/test_test_coverage_adapter.py` | 30 |
| Git activity adapter | `tests/adapters/vcs/test_git_activity_adapter.py` | 21 |
| **Total** | | **186 / 186 passing** |

### Test fixtures

| Fixture | Purpose |
|---|---|
| `tests/fixtures/python-sample/sample.py` | Python file with known CC values (1, 4, 7) |
| `tests/fixtures/ts-sample/sample.ts` | TypeScript file for tsc adapter |
| `tests/fixtures/ts-sample/tsconfig.json` | TypeScript config |
| `tests/fixtures/ts-sample/package.json` | Package manifest |
| `tests/fixtures/simple-python/` | Python repo with partial test coverage (core.py tested, utils.py untested) |
| `tests/fixtures/ts-colocated/` | TypeScript repo with co-located *.test.tsx files (no tests/ dir) |

### VCS adapter

| Module | File | Status |
|---|---|---|
| Git Activity | `src/repo_cart/adapters/vcs/git_activity_adapter.py` | Done |

---

## What's NOT done yet

### Pre-ship blockers (TODOS.md)

| # | Item | Notes |
|---|---|---|
| ~~TODO-1~~ | ~~Walker symlink guard~~ | Done — `walker.py` + all new adapters use `os.walk(followlinks=False)`. |
| ~~TODO-2~~ | ~~`--stdout` stderr redirect~~ | Done — implemented in `renderer.py:write_outputs()` |
| ~~TODO-3~~ | ~~eslint dual-config detection~~ | Done — both v7/v8 and v9+ flat config formats detected in `eslint_adapter.py` |

All three pre-ship TODOs are resolved. No blocking items remain for v0.1.

### Packaging / install

`pyproject.toml` is configured. `pip install -e .` works when `typer` and `pathspec` are present.
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

## Next up (Phase 3 — v0.3)

Phase 2 is complete. Layer 07 (Git Activity) shipped ahead of Phase 3.

Remaining deferred items (v0.3 candidates):

| Item | Notes |
|---|---|
| Watch mode (`repo-cart watch`) | inotify/FSEvents watcher, incremental re-scan on file change |
| Incremental scan | Only re-run adapters for changed files |
| TypeScript untested_modules | Co-located test matching (utils.ts ↔ utils.test.tsx) deferred |
| entry_points_adapter gitignore | Currently uses rglob(); needs os.walk + load_gitignore to benefit |
| Adapter auto-discovery via entry points | Plugin architecture for third-party adapters |
| Custom terminal renderers for lint (02) and types (03) | Currently using shared renderer |
| PyPI publish | `pyproject.toml` is ready; not yet published |
