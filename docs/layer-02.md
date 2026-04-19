# Layer 02: Lint

**Key:** `lint`
**Source:** `eslint`
**Language:** JavaScript / TypeScript
**Confidence:** `files_with_issues / total_js_ts_files` (0.5 if no issues found but eslint ran)
**Status:** DONE

---

## What it does

Runs `eslint --format json <path>` and parses the output into a count of errors and
warnings, plus a list of files with issues (top 20 by error count).

Skipped with:
- `reason_code: not_installed` — if no eslint binary found (local or PATH)
- `reason_code: no_config` — if no eslint config file found in the scan root

---

## Requires

eslint must be available either:
- locally at `<scan_path>/node_modules/.bin/eslint` (preferred)
- or globally on PATH

---

## Config detection

Checked in order:

**v9+ (flat config):**
- `eslint.config.js`
- `eslint.config.mjs`
- `eslint.config.cjs`

**v7/v8 (legacy):**
- `.eslintrc`
- `.eslintrc.js`
- `.eslintrc.cjs`
- `.eslintrc.json`
- `.eslintrc.yml`
- `.eslintrc.yaml`

---

## Output schema

```json
{
  "lint": {
    "source": "eslint",
    "confidence": 0.75,
    "data": {
      "error_count": 12,
      "warning_count": 4,
      "files_with_issues": [
        {
          "file": "/repo/src/index.ts",
          "errors": 3,
          "warnings": 1,
          "messages": [
            {
              "rule": "no-unused-vars",
              "severity": 2,
              "line": 5,
              "message": "'x' is declared but its value is never read."
            }
          ]
        }
      ]
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `error_count` | int | Total errors across all files |
| `warning_count` | int | Total warnings across all files |
| `files_with_issues` | list | Files with at least one error or warning (top 20) |
| `files_with_issues[].file` | str | Absolute file path |
| `files_with_issues[].errors` | int | Error count for this file |
| `files_with_issues[].warnings` | int | Warning count for this file |
| `files_with_issues[].messages` | list | Up to 5 message details per file |

---

## Implementation

`src/repo_cart/adapters/js_ts/eslint_adapter.py`

- `check()`: `shutil.which("eslint") is not None`
- `run()`: discovers binary via `_find_eslint(path)` (local first, PATH fallback), checks config, runs eslint
- `parse()`: sums errors/warnings, filters files with issues, sorts by error count desc
- `confidence()`: `analyzed / (js_count + ts_count)` — 0.5 if no issues (eslint ran but clean)

---

## Terminal rendering

Rendered by the generic layer renderer (no custom renderer in MVP):

```
LINT (eslint, confidence: 0.75)
  {'error_count': 12, 'warning_count': 4, 'files_with_issues': [...]}
```

Custom lint renderer is a future improvement.
