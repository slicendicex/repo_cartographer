# Layer 00: Structure

**Key:** `structure`
**Source:** `walker` (built-in, no external tool)
**Confidence:** `1.0` when traversal is complete; reduced proportionally if unreadable directories are encountered
**Status:** DONE

---

## What it does

Walks the file tree of the target repo using `os.walk(followlinks=False)` and produces
a structural map: total file count, per-language file counts, and top-level directory names.

This layer is always attempted in every scan. It has no external analyzer dependencies
and does not appear in `skipped_layers`. It does not guarantee completeness — filesystem
permission errors will cause partial traversal, which is recorded in `unreadable_dirs`
and reflected in a reduced confidence score.

It runs before any adapter and provides `WalkerContext` to all adapters for their
`confidence()` calculations.

---

## Excluded directories

Hardcoded; `.gitignore` parsing is intentionally deferred from MVP (Phase 2 item):

```
node_modules  .git  __pycache__  .venv  venv  dist  build
.mypy_cache   .pytest_cache  .tox  .nox  coverage  .eggs
```

These directories are pruned in-place during traversal so their subtrees are never
entered. When `.gitignore` parsing is added in Phase 2, it will supplement this list
rather than replace it.

---

## Output schema

```json
{
  "structure": {
    "source": "walker",
    "confidence": 1.0,
    "data": {
      "file_count": 142,
      "languages": {
        "python": 89,
        "typescript": 41,
        "javascript": 12
      },
      "top_dirs": ["src", "tests", "scripts"],
      "unreadable_dirs": []
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `file_count` | int | Total files found (all extensions, excluding pruned dirs) |
| `languages` | dict[str, int] | Count per recognized language |
| `top_dirs` | list[str] | Top-level directory names, sorted, excludes pruned dirs |
| `unreadable_dirs` | list[str] | Paths that could not be traversed due to permission or I/O errors |

### Confidence scoring

| State | Confidence |
|---|---|
| Full traversal, no errors | `1.0` |
| Partial traversal (`n` unreadable dirs) | `1.0 - n / max(file_count, 1)` |

When `unreadable_dirs` is non-empty, the terminal summary should be treated as incomplete.

---

## Recognized extensions

| Extension | Language |
|---|---|
| `.py` | python |
| `.js` `.jsx` `.mjs` `.cjs` | javascript |
| `.ts` `.tsx` `.mts` `.cts` | typescript |

All other extensions increment `file_count` but are not counted in `languages`. The
`other` count shown in terminal rendering is a display-only derived value:
`file_count - sum(languages.values())`. It is not stored in the schema.

---

## Return type

`walk()` returns a `WalkerResult` dataclass (not a plain tuple):

```python
@dataclass
class WalkerResult:
    ctx: WalkerContext           # passed to all adapters
    top_dirs: list[str]          # top-level dir names
    unreadable_dirs: list[str]   # paths that triggered OSError during traversal

    @property
    def had_warnings(self) -> bool: ...
```

`WalkerContext` is a separate dataclass shared with adapters:

```python
@dataclass
class WalkerContext:
    total_files: int
    files_by_language: dict[str, int]
```

---

## Implementation

`src/repo_cart/core/walker.py` — `walk(path: Path) -> WalkerResult`

Key behaviors:
- `dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]` prunes subtrees in-place
- `followlinks=False` prevents infinite loops on repos with circular symlinks
- `onerror=_on_error` captures `OSError` from unreadable directories without aborting

---

## Terminal rendering

```
STRUCTURE (walker, confidence: 1.00)
  142 files  |  python: 89  typescript: 41  javascript: 12  other: 0
  Top dirs: src/  tests/  scripts/
```

The `other` count is rendered as `file_count - sum(languages.values())` and shown only
when greater than zero. It is a rendering artifact and not part of the stored schema.

If `unreadable_dirs` is non-empty, a warning line is shown:
```
  Warning: 2 director(ies) could not be read (permission denied)
```
