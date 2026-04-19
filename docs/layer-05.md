# Layer 05: Entry Points

**Key:** `entry_points`
**Source:** `entry_points_adapter`
**Language:** any
**Confidence:** `1.0` if any entry point found, `0.0` otherwise
**Status:** COMPLETE

---

## What it does

Finds where the repo starts: CLI commands, `__main__.py` modules, and `package.json`
main/bin fields. Answers "how do I run this thing?" on first glance.

Pure file parsing — no subprocess, no external binaries. `check()` always returns `True`.

Never skipped. Returns an empty layer with `confidence: 0.0` when no entry points found.

---

## Requires

Nothing. Always available.

Parses any of the following that exist:
- `pyproject.toml` — `[project.scripts]`
- `package.json` — `main` and `bin` fields
- `src/**/` — any `__main__.py` file

---

## Output schema

```json
{
  "entry_points": {
    "source": "entry_points_adapter",
    "confidence": 1.0,
    "data": {
      "cli": ["repo-cart"],
      "main_modules": [],
      "package_main": null
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `cli` | list[str] | CLI command names from `pyproject.toml` scripts or `package.json` bin keys |
| `main_modules` | list[str] | Paths to `__main__.py` files found under `src/` |
| `package_main` | str or null | `package.json` `"main"` field value, or `null` |

Empty layer (no entry points found): all three fields empty/null, confidence 0.0.

---

## Implementation

`src/repo_cart/adapters/common/entry_points_adapter.py`

- `check()`: returns `True`
- `run(path)`: reads pyproject.toml + package.json, walks src/ for `__main__.py`, returns `json.dumps(result)`
- `parse(raw)`: returns `json.loads(raw)`
- `confidence(parsed, ctx)`: `1.0 if (parsed.get("cli") or parsed.get("main_modules") or parsed.get("package_main")) else 0.0`

### `package.json` bin field handling

`bin` can be a string or a dict:
- String: `"bin": "./cli.js"` — treated as one unnamed entry, skipped for CLI name list
- Dict: `"bin": {"mycli": "./cli.js"}` — keys become CLI names

---

## Terminal rendering

```
ENTRY POINTS (entry_points_adapter, confidence: 1.00)
  CLI: repo-cart
  No __main__.py found
```

Empty:
```
ENTRY POINTS (entry_points_adapter, confidence: 0.00)
  No entry points found
```

---

## Markdown rendering

```markdown
**1 CLI command**

- `repo-cart` (pyproject.toml scripts)
```

---

## Tests

File: `tests/adapters/common/test_entry_points_adapter.py`

| Test | What it covers |
|---|---|
| `test_check_always_true` | `check()` returns `True` unconditionally |
| `test_cli_from_pyproject_scripts` | `[project.scripts]` in pyproject.toml |
| `test_package_main_field` | `"main"` field in package.json |
| `test_package_bin_string` | `"bin"` as string shape |
| `test_package_bin_dict` | `"bin"` as dict shape — keys become CLI names |
| `test_main_module_detected` | `__main__.py` found under `src/` |
| `test_no_entry_points_returns_empty_with_zero_confidence` | empty layer, confidence 0.0 |
| `test_confidence_full_when_cli_found` | `confidence()` returns `1.0` |
| `test_confidence_zero_when_no_entry_points` | `confidence()` returns `0.0` |
