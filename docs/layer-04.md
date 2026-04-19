# Layer 04: Dependencies

**Key:** `dependencies`
**Source:** `deps_adapter`
**Language:** any
**Confidence:** `1.0` if dep file found, `0.0` otherwise
**Status:** COMPLETE

---

## What it does

Parses dependency manifests in the scan root and returns runtime vs dev dependencies
with counts, source file name, and per-ecosystem breakdown.

Pure file parsing — no subprocess, no external binaries. `check()` always returns `True`.

Skipped with:
- `reason_code: no_config` — if no dependency file found at repo root

---

## Requires

Nothing. Always available.

One of the following must exist at the scan root:
- `pyproject.toml` (Python — `[project.dependencies]` + `[project.optional-dependencies.dev]`)
- `requirements.txt` (Python runtime)
- `requirements-dev.txt` (Python dev)
- `package.json` (JS/TS — `dependencies` + `devDependencies`)

Priority: `pyproject.toml` wins over `requirements.txt` when both exist.

---

## Output schema

```json
{
  "dependencies": {
    "source": "deps_adapter",
    "confidence": 1.0,
    "data": {
      "python": {
        "runtime": ["typer>=0.12"],
        "dev": ["pytest>=8.0", "pytest-cov>=5.0", "radon>=6.0"],
        "total": 4,
        "source_file": "pyproject.toml"
      }
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `python` / `js` | dict | Per-ecosystem block (only keys present if file found) |
| `runtime` | list[str] | Runtime dependency specifiers as written in the manifest |
| `dev` | list[str] | Dev dependency specifiers |
| `total` | int | `len(runtime) + len(dev)` |
| `source_file` | str | Filename that was parsed (e.g. `pyproject.toml`) |

---

## Implementation

`src/repo_cart/adapters/common/deps_adapter.py`

- `check()`: returns `True`
- `run(path)`: reads dep files, builds result dict, returns `json.dumps(result)`
- `parse(raw)`: returns `json.loads(raw)`
- `confidence(parsed, ctx)`: `1.0 if parsed else 0.0`

Also includes: renderer dispatch table refactor in `renderer.py` (replaces elif chains
with `_TERMINAL_RENDERERS` and `_MARKDOWN_RENDERERS` dicts).

---

## Terminal rendering

```
DEPENDENCIES (deps_adapter, confidence: 1.00)
  Python runtime: typer
  Python dev:     pytest  pytest-cov  radon  (4 total)
```

---

## Markdown rendering

```markdown
**4 dependencies** (pyproject.toml)

| Scope | Package |
|-------|---------|
| runtime | `typer>=0.12` |
| dev | `pytest>=8.0` |
| dev | `pytest-cov>=5.0` |
| dev | `radon>=6.0` |
```

---

## Tests

File: `tests/adapters/common/test_deps_adapter.py`

| Test | What it covers |
|---|---|
| `test_check_always_true` | `check()` returns `True` unconditionally |
| `test_parse_pyproject_runtime_and_dev` | Reads `[project.dependencies]` + `[project.optional-dependencies.dev]` |
| `test_parse_pyproject_runtime_only` | pyproject with no optional-dependencies |
| `test_parse_requirements_txt` | `requirements.txt` fallback |
| `test_parse_requirements_dev_txt` | `requirements-dev.txt` as dev scope |
| `test_parse_package_json` | `dependencies` + `devDependencies` |
| `test_run_raises_when_no_dep_file` | `AdapterError`, `reason_code="no_config"` |
| `test_pyproject_takes_priority_over_requirements` | pyproject.toml wins when both exist |
| `test_confidence_full_when_deps_found` | `confidence()` returns `1.0` |
| `test_confidence_zero_when_empty` | `confidence()` returns `0.0` |
