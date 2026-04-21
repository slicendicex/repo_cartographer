# Repo Cartographer — Project Plan

## Mission

Give any developer a layered map of any repo in one command. Output is terminal-readable,
machine-parseable (JSON), and doc-friendly (Markdown). Designed to be the first thing
you run on an unfamiliar codebase or feed to an AI agent.

---

## Phases

### Phase 1 — MVP (v0.1)

**Goal:** Ship the core pipeline with 4 layers, 3 adapters, and a working CLI.

**Layers:**
- [x] Layer 00: Structure (walker, built-in) — complete including partial-scan warnings
- [x] Layer 01: Complexity (radon, Python) — complete, live scan verified
- [x] Layer 02: Lint (eslint, JS/TS) — complete including exit code fix, dedicated renderer
- [x] Layer 03: Types (tsc, TypeScript) — complete, live scan verified

**Infrastructure:**
- [x] `AdapterBase` ABC with `WalkerContext`, `AdapterError`
- [x] `_run_subprocess()` DRY helper on `AdapterBase`
- [x] `ThreadPoolExecutor` concurrent adapter execution
- [x] `scan()` orchestrator with `check()` → `run()` → `parse()` → `confidence()` flow
- [x] Three outputs from one pass: terminal summary, `repo-cart.json`, `repo-cart.md`
- [x] `--stdout` flag (JSON → stdout, terminal summary → stderr)
- [x] `--no-color` flag
- [x] 69 tests, all passing

**Packaging:**
- [x] `src/` layout, hatchling build backend
- [x] `pyproject.toml` with entry point `repo-cart`
- [x] Test fixtures: `tests/fixtures/python-sample/`, `tests/fixtures/ts-sample/`

**Before v0.1 ships (see TODOS.md):**
- [ ] TODO-1: Walker symlink loop guard (already using `followlinks=False` — verify)
- [x] TODO-2: `--stdout` stderr redirect — already implemented in `renderer.py:write_outputs()`
- [ ] TODO-3: eslint dual-config detection (already implemented in `eslint_adapter.py`)

---

### Phase 2 — File-Parsing Layers (v0.2)

**Goal:** Three new layers via pure file parsing — no external binaries, always present.

**Layers:**
- [x] Layer 04: Dependencies (`deps_adapter`, `adapters/common/`) — runtime + dev deps from pyproject.toml / requirements.txt / package.json. Includes renderer dispatch table refactor.
- [x] Layer 05: Entry Points (`entry_points_adapter`, `adapters/common/`) — CLI commands, `__main__.py`, package.json main/bin
- [x] Layer 06: Test Coverage (`test_coverage_adapter`, `adapters/common/`) — heuristic test file ratio + untested module list

**Implementation order (conflict-minimizing):**
1. Layer 04 first: creates `adapters/common/`, does renderer dispatch table refactor, adds `_render_dependencies()`
2. Layer 05 next: adds `entry_points_adapter.py` + `_render_entry_points()` to existing dispatch table
3. Layer 06 last: adds `test_coverage_adapter.py` + `_render_test_coverage()` + `tests/fixtures/simple-python/`

**Infrastructure (included in Layer 04):**
- `adapters/common/__init__.py`
- Renderer dispatch table refactor: `_TERMINAL_RENDERERS` + `_MARKDOWN_RENDERERS` dicts replacing elif chains
- Reduces `to_markdown()` CC from 23 to ~8

**Shipped ahead of v0.3:**
- [x] Layer 07: Git Activity (`git log` parsing) — sentinel format, `--window` flag, coverage/confidence split, 21 tests

**Deferred to v0.3:**
- Custom terminal renderers for lint (02) and types (03) layers
- `.gitignore` parsing in walker
- Adapter auto-discovery via entry points (plugin architecture)

---

### Phase 3 — Watch Mode + Incremental (v0.3)

**Goal:** Live feedback loop. Re-run on file change, diff-only output.

- `repo-cart watch [path]` — inotify/FSEvents-based file watcher
- Incremental scan: only re-run adapters for changed files
- Rich live terminal output (diff-style: what changed since last scan)

---

### Phase 4 — AI Integration (v0.4)

**Goal:** Make the JSON snapshot a first-class AI context source.

- `repo-cart context [path]` — emit a compact, token-efficient summary for LLM context
- MCP server mode: expose snapshot as MCP tool responses
- Schema stability guarantee for downstream tooling

---

## Architecture principles

1. **Adapter isolation** — each adapter fails independently, never blocks others
2. **Batch output** — no streaming in MVP, all outputs written after all adapters finish
3. **Schema stability** — `schema_version` field in every snapshot
4. **Confidence scoring** — every layer reports how much of the repo it actually analyzed
5. **Zero required deps at scan time** — if an analyzer isn't installed, layer is skipped gracefully

---

## Key files

| File | Role |
|---|---|
| `src/repo_cart/adapters/base.py` | `AdapterBase`, `WalkerContext`, `AdapterError` |
| `src/repo_cart/core/walker.py` | File tree traversal, language detection |
| `src/repo_cart/core/orchestrator.py` | Concurrent adapter execution, snapshot assembly |
| `src/repo_cart/core/renderer.py` | Terminal, JSON, Markdown output |
| `src/repo_cart/cli.py` | Typer CLI entry point |
| `docs/layer-XX.md` | Spec for each layer |
| `docs/current_state.md` | Live project status |
| `TODOS.md` | Pre-ship blockers |

---

## Snapshot schema (v1.0)

```json
{
  "schema_version": "1.0",
  "repo": "/absolute/path/to/repo",
  "scanned_at": "2026-04-19T16:00:00+00:00",
  "layers": {
    "<layer_key>": {
      "source": "<adapter_name>",
      "confidence": 0.0,
      "data": {}
    }
  },
  "skipped_layers": [
    {
      "layer": "<layer_key>",
      "adapter": "<adapter_name>",
      "reason_code": "not_installed | timeout | parse_error | no_config | unsupported_repo",
      "reason": "<human-readable message>"
    }
  ]
}
```
