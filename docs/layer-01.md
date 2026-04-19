# Layer 01: Complexity

**Key:** `complexity`
**Source:** `radon`
**Language:** Python
**Confidence:** `files_with_hotspots / total_python_files` (capped at 1.0)
**Status:** COMPLETE

---

## What it does

Runs `radon cc -j <path>` to compute cyclomatic complexity (CC) for every Python function,
method, and class in the repo. Returns the top 20 hotspots sorted by CC descending, plus
the average CC across all analyzed functions.

Skipped with `reason_code: not_installed` if `radon` is not on PATH.

---

## Requires

```
pip install radon
```

---

## Output schema

```json
{
  "complexity": {
    "source": "radon",
    "confidence": 0.90,
    "data": {
      "avg_complexity": 4.2,
      "function_count": 38,
      "hotspots": [
        {
          "file": "src/repo_cart/core/orchestrator.py",
          "name": "scan",
          "complexity": 12,
          "grade": "B",
          "type": "function",
          "line": 36
        }
      ]
    }
  }
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `avg_complexity` | float | Mean CC across all analyzed functions |
| `function_count` | int | Total functions/methods/classes analyzed |
| `hotspots` | list | Top 20 items by CC descending |
| `hotspots[].file` | str | File path as returned by radon |
| `hotspots[].name` | str | Function or class name |
| `hotspots[].complexity` | int | Cyclomatic complexity score |
| `hotspots[].grade` | str | A–F grade derived from CC |
| `hotspots[].type` | str | `function`, `method`, or `class` |
| `hotspots[].line` | int | Line number of the definition |

---

## Grade scale

| CC | Grade | Risk |
|---|---|---|
| 1–5 | A | Low |
| 6–10 | B | Moderate |
| 11–15 | C | High |
| 16–20 | D | Very high |
| 21–25 | E | Critical |
| 26+ | F | Untestable |

---

## Implementation

`src/repo_cart/adapters/python/radon_adapter.py`

- `check()`: `shutil.which("radon") is not None`
- `run()`: `radon cc -j <path>` via `_run_subprocess()`
- `parse()`: builds hotspots list, computes avg, sorts by CC desc, caps at 20
- `confidence()`: `len({h["file"] for h in hotspots}) / ctx.files_by_language["python"]`

---

## Terminal rendering

```
COMPLEXITY (radon, confidence: 0.90)
  Avg complexity: 4.2
  Hotspots:
    src/repo_cart/core/orchestrator.py       CC=12  B
    src/repo_cart/core/walker.py             CC=8   B
```

CC > 10 renders in yellow when color is enabled.
