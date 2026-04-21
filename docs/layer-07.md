# Layer 07: Git Activity

**Key:** `git_activity`
**Adapter:** `git_activity_adapter`
**Source:** `src/repo_cart/adapters/vcs/git_activity_adapter.py`
**Status:** Complete

---

## What it does

Runs `git log` via subprocess to produce a time-windowed activity snapshot: commit
volume, active contributors, hot files (most frequently changed), and hot directories.

Always present on git repos. Skips cleanly (`unsupported_repo`) on non-git directories.

---

## Schema

```json
{
  "source": "git_activity_adapter",
  "confidence": 0.85,
  "data": {
    "window": "90d",
    "shallow_clone": false,
    "commits_in_window": 47,
    "active_contributors": 3,
    "coverage": 0.62,
    "hot_files": [
      {"path": "src/repo_cart/core/renderer.py", "changes": 18},
      {"path": "src/repo_cart/adapters/base.py", "changes": 12}
    ],
    "hot_dirs": [
      {"path": "src", "changes": 31},
      {"path": "tests", "changes": 24}
    ]
  }
}
```

### Field definitions

| Field | Type | Description |
|-------|------|-------------|
| `window` | str | Active window: `30d`, `90d`, `365d`, or `all` |
| `shallow_clone` | bool | True if `git rev-parse --is-shallow-repository` returned `"true"` |
| `commits_in_window` | int | Number of commits in the window |
| `active_contributors` | int | Unique author emails in the window |
| `coverage` | float | Fraction of `git ls-files` output touched in the window |
| `hot_files` | list | Top 10 files by commit frequency (path + changes count) |
| `hot_dirs` | list | Top 10 first-level directories by commit frequency |

`changes` = number of commits touching that file/directory in the window.
Root-level files (`Makefile`, `README.md`, etc.) are excluded from `hot_dirs`.
Binary files (numstat shows `-`) are excluded from `hot_files`.

---

## Confidence scoring

| Condition | Effect |
|-----------|--------|
| command success, ≥ 5 commits | 1.0 |
| shallow clone | capped at 0.6 |
| < 5 commits in window | −0.2 |
| 0 commits in window | 0.0 |
| command failure | 0.0 (via AdapterError) |

`coverage` and `confidence` are separate fields. Coverage is the fraction of
tracked files touched; confidence is the trustworthiness of the signal.

---

## check() / run() behaviour

`check()` returns `shutil.which("git") is not None` — verifies git is on PATH only.

`run()` validates the repo with `git rev-parse --is-inside-work-tree` via direct
`subprocess.run` (not `_run_subprocess`). This handles worktrees correctly. If the
check fails, raises `AdapterError("not a git repository", "unsupported_repo")` →
clean `skipped_layers` entry.

---

## --window flag

```bash
repo-cart --window 30d /path/to/repo   # last 30 days
repo-cart --window 90d /path/to/repo   # default
repo-cart --window 365d /path/to/repo  # last year
repo-cart --window all /path/to/repo   # full history (no --since)
```

`timeout` is overridden to 120s at the class level (full-history scans on large repos).

---

## Terminal output

```
GIT ACTIVITY (git_activity_adapter, confidence: 0.85)
  47 commits  ·  3 contributors  ·  62% of files active  (window: 90d)
  Hot files:  src/repo_cart/core/renderer.py (+18)  src/repo_cart/adapters/base.py (+12)  ...
  Hot dirs:   src/ (+31)  tests/ (+24)
```

Shallow clone warning (if applicable):
```
  ⚠ shallow clone — git history may be incomplete (confidence capped at 0.60)
```

---

## File layout

```
src/repo_cart/adapters/vcs/
  __init__.py
  git_activity_adapter.py

tests/adapters/vcs/
  __init__.py
  test_git_activity_adapter.py  (21 tests)
```

---

## Tests

21 tests covering:

- `check()` with git available / missing
- `check()` with worktree layout
- Constructor validation (invalid window)
- `_parse_sentinel`: single commit, multiple commits, binary files, empty commits, excluded dirs
- `hot_files` sort order
- `hot_dirs` depth-1 aggregation and root-file exclusion
- `run()` raises `unsupported_repo` on non-git directory
- `--window all` and `--window 30d`
- Coverage calculation (divide-by-zero guard)
- `confidence()`: full, zero, shallow, low-commit-count cases
