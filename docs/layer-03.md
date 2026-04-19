# Layer 03: Types

**Key:** `types`
**Source:** `tsc`
**Language:** TypeScript
**Confidence:** `files_with_errors / total_typescript_files` (0.5 if clean)
**Status:** DONE

---

## What it does

Runs `tsc --noEmit --pretty false` in the scan root and parses the compiler output into
a count of type errors and warnings, plus the top 20 error entries.

Skipped with:
- `reason_code: not_installed` — if no tsc binary found (local or PATH)
- `reason_code: no_config` — if `tsconfig.json` is not present in the scan root

---

## Requires

tsc must be available either:
- locally at `<scan_path>/node_modules/.bin/tsc` (preferred)
- or globally on PATH

A `tsconfig.json` must exist at the scan root.

---

## Output schema

```json
{
  "types": {
    "source": "tsc",
    "confidence": 0.60,
    "data": {
      "error_count": 5,
      "warning_count": 1,
      "errors": [
        {
          "file": "src/main.ts",
          "line": 10,
          "col": 5,
          "code": "TS2322",
          "message": "Type 'string' is not assignable to type 'number'."
        }
      ]
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `error_count` | int | Total type errors |
| `warning_count` | int | Total warnings |
| `errors` | list | Top 20 error entries |
| `errors[].file` | str | File path as reported by tsc |
| `errors[].line` | int | Line number |
| `errors[].col` | int | Column number |
| `errors[].code` | str | TypeScript error code, e.g. `TS2322` |
| `errors[].message` | str | Human-readable error message |

---

## tsc exit code behavior

tsc exits non-zero when type errors exist — which is the normal "success" case for this
adapter. `run()` catches non-zero exits and returns the raw output instead of raising,
so `parse()` can process the error lines. Only genuine failures (`not_installed`,
`timeout`) are re-raised.

---

## Implementation

`src/repo_cart/adapters/js_ts/tsc_adapter.py`

- `check()`: `shutil.which("tsc") is not None`
- `run()`: checks for `tsconfig.json`, discovers binary via `_find_tsc(path)`, runs tsc
- `parse()`: regex-parses `file(line,col): error|warning TSxxxx: message` lines
- `confidence()`: `len({e["file"] for e in errors}) / ts_count` — 0.5 if no errors

---

## Parse regex

```
^(.+?)\((\d+),(\d+)\): (error|warning) (TS\d+): (.+)$
```

Groups: `file`, `line`, `col`, `severity`, `code`, `message`.

---

## Terminal rendering

Rendered by the generic layer renderer (no custom renderer in MVP):

```
TYPES (tsc, confidence: 0.60)
  {'error_count': 5, 'warning_count': 1, 'errors': [...]}
```

Custom types renderer is a future improvement.
