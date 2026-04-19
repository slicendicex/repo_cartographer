# Layer 06: Test Coverage

**Key:** `test_coverage`
**Source:** `test_coverage_adapter`
**Language:** any
**Confidence:** `min(test_files / total_files, 1.0)` using `ctx.total_files`
**Status:** PLANNED

---

## What it does

Heuristic test coverage: counts test files vs source files, computes a ratio, and
identifies source modules with no matching test file by stem. No pytest or jest
invocation — pure file matching.

Pure file parsing — no subprocess, no external binaries. `check()` always returns `True`.

Skipped with:
- `reason_code: no_config` — if no `tests/` directory found at repo root

---

## Requires

Nothing. Always available when a `tests/` directory exists.

---

## Source file definition

Python files under `src/` (fallback: repo root if no `src/`) that:
- are not `__init__.py`
- are not in `EXCLUDED_DIRS` (node_modules, .venv, dist, etc.)
- do not match test file patterns

## Test file patterns

- `test_*.py`
- `*_test.py`
- `*.test.ts`
- `*.spec.ts`

## Stem-match for untested_modules

For each source file `src/repo_cart/core/renderer.py`:
- check if `test_renderer.py` OR `renderer_test.py` exists anywhere under `tests/` (case-insensitive stem)
- if no match: file is added to `untested_modules`

This is heuristic — naming conventions vary. `untested_modules` means "possibly untested."

---

## Output schema

```json
{
  "test_coverage": {
    "source": "test_coverage_adapter",
    "confidence": 0.35,
    "data": {
      "test_files": 8,
      "source_files": 23,
      "coverage_ratio": 0.35,
      "untested_modules": [
        "src/repo_cart/core/renderer.py",
        "src/repo_cart/adapters/js_ts/tsc_adapter.py"
      ]
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `test_files` | int | Count of files matching test patterns under `tests/` |
| `source_files` | int | Count of non-test source files under `src/` |
| `coverage_ratio` | float | `test_files / source_files`, capped at `1.0`. `0.0` if `source_files == 0` |
| `untested_modules` | list[str] | Source files with no stem-matching test file in `tests/` |

---

## Implementation

`src/repo_cart/adapters/common/test_coverage_adapter.py`

- `check()`: returns `True`
- `run(path)`: walks `src/` for source files, walks `tests/` for test stems, computes ratio and gaps, returns `json.dumps(result)`
- `parse(raw)`: returns `json.loads(raw)`
- `confidence(parsed, ctx)`: `min(parsed["test_files"] / ctx.total_files, 1.0) if ctx.total_files > 0 else 0.0`

---

## Terminal rendering

```
TEST COVERAGE (test_coverage_adapter, confidence: 0.35)
  8 test files / 23 source files  (35%)
  Untested: core/renderer.py  adapters/js_ts/tsc_adapter.py  (+N more)
```

Truncate `untested_modules` to top 3 in terminal. Full list in JSON and markdown.

---

## Markdown rendering

```markdown
**35% structural coverage** — 8 test files / 23 source files

Possibly untested modules:
- `src/repo_cart/core/renderer.py`
- `src/repo_cart/adapters/js_ts/tsc_adapter.py`
```

---

## Fixture

`tests/fixtures/simple-python/` — used by test_coverage_adapter tests:

```
tests/fixtures/simple-python/
  src/
    mypackage/
      __init__.py
      core.py
      utils.py
  tests/
    test_core.py       ← matches core.py by stem
  pyproject.toml       ← [project.dependencies] + [project.optional-dependencies.dev]
```

`utils.py` has no matching test file — appears in `untested_modules`.

---

## Tests

File: `tests/adapters/common/test_test_coverage_adapter.py`

| Test | What it covers |
|---|---|
| `test_check_always_true` | `check()` returns `True` unconditionally |
| `test_happy_path_partial_coverage` | source + tests dir, some tested, some not |
| `test_fully_tested_repo` | all source files have stem-matching tests |
| `test_empty_tests_dir` | `tests/` exists but has no test files |
| `test_run_raises_when_no_tests_dir` | `AdapterError`, `reason_code="no_config"` |
| `test_zero_source_files_ratio_guard` | `coverage_ratio = 0.0` when `source_files == 0` |
| `test_coverage_ratio_capped_at_one` | more test files than source files → ratio capped at 1.0 |
| `test_stem_match_test_prefix` | `test_renderer.py` matches `renderer.py` |
| `test_stem_match_test_suffix` | `renderer_test.py` matches `renderer.py` |
| `test_typescript_test_files_counted` | `.test.ts` and `.spec.ts` files detected |
| `test_confidence_uses_total_files` | `confidence()` uses `ctx.total_files` as denominator |
