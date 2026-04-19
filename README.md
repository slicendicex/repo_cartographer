# repo-cart

Give any repo a layered map in one command.

```
repo-cart /path/to/some-project
```

```
STRUCTURE (walker, confidence: 1.00)
  40 files  python: 23  typescript: 1
  Top dirs: docs  src  tests

COMPLEXITY (radon, confidence: 0.52)
  Avg CC: 2.7 — 199 functions analyzed
  Hotspots: renderer.py (CC 23, E)  walker.py (CC 11, C)

DEPENDENCIES (deps_adapter, confidence: 1.00)
  Python runtime: typer
  Python dev:     pytest  pytest-cov  radon  (4 total)

ENTRY POINTS (entry_points_adapter, confidence: 1.00)
  CLI: repo-cart
  Modules: src/repo_cart/__main__.py

TEST COVERAGE (test_coverage_adapter, confidence: 0.35)
  8 test files / 23 source files  (35%)
```

Three outputs from one pass: terminal summary, `repo-cart.json`, `repo-cart.md`.

---

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+. The only required dependency is `typer`. Optional analyzers
(`radon`, `eslint`, `tsc`) are used when available — missing ones are skipped gracefully.

---

## Usage

```bash
# Scan current directory
repo-cart

# Scan a specific path
repo-cart /path/to/repo

# JSON to stdout (for piping or AI context)
repo-cart --stdout /path/to/repo | jq '.layers'

# No color (CI environments)
repo-cart --no-color /path/to/repo
```

Output files written to the scan target:
- `repo-cart.json` — full snapshot, schema version 1.0
- `repo-cart.md` — markdown summary

---

## Layers

Each layer runs independently. If an analyzer is missing or the repo doesn't apply,
that layer is skipped and noted in `skipped_layers` — it never blocks the others.

| # | Key | Analyzer | Requires |
|---|-----|----------|---------|
| 00 | `structure` | walker (built-in) | nothing |
| 01 | `complexity` | radon | `radon` installed |
| 02 | `lint` | eslint | `eslint` + config file |
| 03 | `types` | tsc | `tsc` + `tsconfig.json` |
| 04 | `dependencies` | deps_adapter | pyproject.toml / requirements.txt / package.json |
| 05 | `entry_points` | entry_points_adapter | pyproject.toml / package.json |
| 06 | `test_coverage` | test_coverage_adapter | `tests/` directory |

Layers 04–06 are pure file parsing — no external binaries needed.

---

## JSON snapshot

```json
{
  "schema_version": "1.0",
  "repo": "/absolute/path",
  "scanned_at": "2026-04-19T18:31:50Z",
  "layers": {
    "structure": { "source": "walker", "confidence": 1.0, "data": {} },
    "complexity": { "source": "radon",  "confidence": 0.52, "data": {} }
  },
  "skipped_layers": [
    { "layer": "lint", "adapter": "eslint_adapter", "reason_code": "not_installed", "reason": "..." }
  ]
}
```

`confidence` is always between 0 and 1 — it tells you how much of the repo a given
layer actually analyzed. A skipped layer never appears in `layers`; it goes to
`skipped_layers` with a `reason_code`.

---

## Development

```bash
# Install with dev deps
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run a single suite
pytest tests/adapters/common/test_deps_adapter.py -v
```

143 tests, all passing. No mocks — tests use `tmp_path` fixtures and real file I/O.

---

## Architecture

```
src/repo_cart/
  cli.py                  # Typer entry point, adapter registry
  core/
    walker.py             # File tree traversal, language detection
    orchestrator.py       # Concurrent adapter execution, snapshot assembly
    renderer.py           # Terminal, JSON, Markdown output
  adapters/
    base.py               # AdapterBase ABC, WalkerContext, AdapterError
    common/               # Language-agnostic adapters (pure file parsing)
      deps_adapter.py
      entry_points_adapter.py
      test_coverage_adapter.py
    python/
      radon_adapter.py
    js_ts/
      eslint_adapter.py
      tsc_adapter.py
```

All adapters implement the same four-method interface: `check()` → `run()` → `parse()` → `confidence()`.
Adding a new layer means writing one file and registering it in `cli.py`.

---

## Roadmap

- **v0.1** — current: 7 layers, terminal + JSON + markdown output, concurrent execution
- **v0.3** — watch mode (`repo-cart watch`), incremental re-scan on file change
- **v0.4** — `repo-cart context` for compact AI/LLM snapshots, MCP server mode
