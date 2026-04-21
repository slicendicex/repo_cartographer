"""
Renderer — produces terminal summary, JSON, and Markdown from a snapshot dict.

All three outputs are derived from the same snapshot. The snapshot is the
canonical artifact; these are views.

Terminal summary format:
    Repo Cartographer — /path/to/repo
    Scanned at 2026-04-19 16:00:00 UTC

    STRUCTURE (walker, confidence: 1.00)
      142 files  |  python: 89  typescript: 41  other: 12
      Top dirs: src/  tests/  scripts/

    COMPLEXITY (radon, confidence: 0.90)
      Avg complexity: 4.2 (grade B)
      Hotspots:
        src/orchestrator.py   CC=12  B

    SKIPPED LAYERS
      lint   eslint not found   [not_installed]

    Snapshot written to ./repo-cart.json

Colorized by default. Pass use_color=False to strip ANSI.
Top 5 hotspots shown. Top 10 skipped layers shown.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, TextIO


# ANSI escape sequences.
_RESET = "\033[0m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


def _c(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{_RESET}" if use_color else text


def _strip_version(spec: str) -> str:
    return re.split(r"[>=<!~\[\s]", spec)[0].strip()


# ---------------------------------------------------------------------------
# Terminal renderers — each prints directly to file
# ---------------------------------------------------------------------------

def _render_structure(data: dict, use_color: bool, file: TextIO) -> None:
    file_count = data.get("file_count", 0)
    languages = data.get("languages", {})
    top_dirs = data.get("top_dirs", [])
    unreadable = data.get("unreadable_dirs", [])

    lang_parts = "  ".join(f"{lang}: {count}" for lang, count in sorted(languages.items()))
    other = file_count - sum(languages.values())
    if other > 0:
        lang_parts += f"  other: {other}"
    print(f"  {file_count} files  |  {lang_parts}", file=file)

    if top_dirs:
        dirs_str = "  ".join(f"{d}/" for d in top_dirs[:8])
        print(f"  Top dirs: {dirs_str}", file=file)

    if unreadable:
        n = len(unreadable)
        warn = f"  Warning: {n} director{'y' if n == 1 else 'ies'} could not be read (permission denied)"
        print(_c(warn, _YELLOW, use_color), file=file)


def _render_complexity(data: dict, use_color: bool, file: TextIO) -> None:
    avg = data.get("avg_complexity")
    if avg is not None:
        print(f"  Avg complexity: {avg:.1f}", file=file)

    hotspots = data.get("hotspots", [])
    if hotspots:
        print("  Hotspots:", file=file)
        for h in hotspots[:5]:
            fname = h.get("file", "?")
            cc = h.get("complexity", "?")
            grade = h.get("grade", "")
            line = f"    {fname:<40} CC={cc}  {grade}"
            high = isinstance(cc, (int, float)) and cc > 10
            print(_c(line, _YELLOW, use_color) if high else line, file=file)


def _render_lint(data: dict, use_color: bool, file: TextIO) -> None:
    errors = data.get("error_count", 0)
    warnings = data.get("warning_count", 0)
    files = data.get("files_with_issues", [])

    summary = f"  {errors} error{'s' if errors != 1 else ''}  {warnings} warning{'s' if warnings != 1 else ''}"
    has_errors = errors > 0
    print(_c(summary, _YELLOW, use_color) if has_errors else summary, file=file)

    if files:
        print("  Files with issues:", file=file)
        for f in files[:5]:
            fname = f.get("file", "?")
            e = f.get("errors", 0)
            w = f.get("warnings", 0)
            line = f"    {fname:<50} E={e}  W={w}"
            print(_c(line, _YELLOW, use_color) if e > 0 else line, file=file)
            for msg in f.get("messages", [])[:2]:
                rule = msg.get("rule", "?")
                lineno = msg.get("line", 0)
                print(f"      {rule}  line {lineno}", file=file)


def _render_types(data: dict, use_color: bool, file: TextIO) -> None:
    errors = data.get("error_count", 0)
    warnings = data.get("warning_count", 0)
    entries = data.get("errors", [])

    summary = f"  {errors} error{'s' if errors != 1 else ''}  {warnings} warning{'s' if warnings != 1 else ''}"
    print(_c(summary, _YELLOW, use_color) if errors > 0 else summary, file=file)

    if entries:
        print("  Type errors:", file=file)
        for e in entries[:5]:
            fname = e.get("file", "?")
            lineno = e.get("line", 0)
            code = e.get("code", "")
            message = e.get("message", "")
            loc = f"{fname}:{lineno}"
            line = f"    {loc:<50} {code}  {message}"
            print(_c(line, _YELLOW, use_color), file=file)


def _render_dependencies(data: dict, use_color: bool, file: TextIO) -> None:
    for ecosystem, info in data.items():
        runtime = info.get("runtime", [])
        dev = info.get("dev", [])
        total = info.get("total", 0)
        if runtime:
            names = "  ".join(_strip_version(p) for p in runtime)
            print(f"  {ecosystem.capitalize()} runtime: {names}", file=file)
        if dev:
            names = "  ".join(_strip_version(p) for p in dev)
            print(f"  {ecosystem.capitalize()} dev:     {names}  ({total} total)", file=file)
        if not runtime and not dev:
            print(f"  {ecosystem.capitalize()}: no dependencies listed", file=file)


def _render_entry_points(data: dict, use_color: bool, file: TextIO) -> None:
    cli = data.get("cli", [])
    main_modules = data.get("main_modules", [])
    package_main = data.get("package_main")

    if not cli and not main_modules and not package_main:
        print("  No entry points found", file=file)
        return

    if cli:
        print(f"  CLI: {', '.join(cli)}", file=file)
    if main_modules:
        print(f"  __main__.py: {', '.join(main_modules)}", file=file)
    else:
        print("  No __main__.py found", file=file)
    if package_main:
        print(f"  package main: {package_main}", file=file)


def _render_test_coverage(data: dict, use_color: bool, file: TextIO) -> None:
    by_language = data.get("by_language", {})
    line_rate = data.get("line_rate")
    xml_present = data.get("coverage_xml_present", False)
    xml_ts = data.get("coverage_xml_timestamp")

    if xml_present and line_rate is not None:
        pct = int(line_rate * 100)
        ts_note = f"  (coverage.xml, {xml_ts})" if xml_ts else ""
        print(f"  Line coverage: {pct}%{ts_note}", file=file)

    if by_language:
        for lang, info in by_language.items():
            n_src = info.get("source_files", 0)
            n_test = info.get("test_files", 0)
            ratio = info.get("heuristic_ratio", 0.0)
            untested = info.get("untested_modules", [])
            pct = int(ratio * 100)
            print(f"  {lang}: {n_test} test / {n_src} source  ({pct}%)", file=file)
            if untested:
                shown = untested[:3]
                extra = len(untested) - len(shown)
                names = "  ".join(m.replace("src/", "", 1) for m in shown)
                suffix = f"  (+{extra} more)" if extra > 0 else ""
                line = f"    Untested: {names}{suffix}"
                print(_c(line, _YELLOW, use_color), file=file)
    elif not xml_present:
        print("  No test files found", file=file)


def _render_git_activity(data: dict, use_color: bool, file: TextIO) -> None:
    commits = data.get("commits_in_window", 0)
    contributors = data.get("active_contributors", 0)
    coverage = data.get("coverage", 0.0)
    window = data.get("window", "90d")
    is_shallow = data.get("shallow_clone", False)
    hot_files = data.get("hot_files", [])
    hot_dirs = data.get("hot_dirs", [])

    pct = int(coverage * 100)
    print(
        f"  {commits} commit{'s' if commits != 1 else ''}  ·  "
        f"{contributors} contributor{'s' if contributors != 1 else ''}  ·  "
        f"{pct}% of files active  (window: {window})",
        file=file,
    )

    if hot_files:
        shown = hot_files[:3]
        extra = len(hot_files) - len(shown)
        parts = "  ".join(f"{h['path']} (+{h['changes']})" for h in shown)
        suffix = f"  (+{extra} more)" if extra > 0 else ""
        print(f"  Hot files:  {parts}{suffix}", file=file)

    if hot_dirs:
        parts = "  ".join(f"{h['path']}/ (+{h['changes']})" for h in hot_dirs[:5])
        print(f"  Hot dirs:   {parts}", file=file)

    if is_shallow:
        warn = "  ⚠ shallow clone — git history may be incomplete (confidence capped at 0.60)"
        print(_c(warn, _YELLOW, use_color), file=file)


def _render_generic(data: dict, use_color: bool, file: TextIO) -> None:
    print(f"  {data}", file=file)


_TERMINAL_RENDERERS: dict[str, Callable[..., None]] = {
    "structure": _render_structure,
    "complexity": _render_complexity,
    "lint": _render_lint,
    "types": _render_types,
    "dependencies": _render_dependencies,
    "entry_points": _render_entry_points,
    "test_coverage": _render_test_coverage,
    "git_activity": _render_git_activity,
}


def to_terminal(
    snapshot: dict[str, Any],
    use_color: bool = True,
    file: TextIO = sys.stdout,
) -> None:
    """Print the terminal summary to ``file`` (default stdout)."""
    repo = snapshot.get("repo", ".")
    scanned_at = snapshot.get("scanned_at", "")
    layers = snapshot.get("layers", {})
    skipped = snapshot.get("skipped_layers", [])

    print(_c(f"Repo Cartographer — {repo}", _BOLD, use_color), file=file)
    if scanned_at:
        print(f"Scanned at {scanned_at}", file=file)
    print(file=file)

    for layer_key, layer in layers.items():
        source = layer.get("source", layer_key)
        confidence = layer.get("confidence", 0.0)
        data = layer.get("data", {})

        header = f"{layer_key.upper()} ({source}, confidence: {confidence:.2f})"
        print(_c(header, _CYAN, use_color), file=file)

        render_fn = _TERMINAL_RENDERERS.get(layer_key, _render_generic)
        render_fn(data, use_color, file)

        print(file=file)

    if skipped:
        print(_c("SKIPPED LAYERS", _DIM, use_color), file=file)
        for entry in skipped[:10]:
            layer_name = entry.get("layer", "?")
            reason = entry.get("reason", "")
            code = entry.get("reason_code", "")
            line = f"  {layer_name:<12} {reason}"
            if code:
                line += f"  [{code}]"
            print(_c(line, _DIM, use_color), file=file)
        print(file=file)


# ---------------------------------------------------------------------------
# Markdown renderers — each returns a list of lines
# ---------------------------------------------------------------------------

def _md_render_structure(data: dict) -> list[str]:
    lines: list[str] = []
    file_count = data.get("file_count", 0)
    languages = data.get("languages", {})
    top_dirs = data.get("top_dirs", [])
    unreadable = data.get("unreadable_dirs", [])
    lines.append(f"- **{file_count} files**")
    for lang, count in sorted(languages.items()):
        lines.append(f"- {lang}: {count}")
    if top_dirs:
        lines.append(f"- Top dirs: {', '.join(top_dirs)}")
    if unreadable:
        n = len(unreadable)
        lines.append(
            f"- **Warning:** {n} director{'y' if n == 1 else 'ies'} could not be read (permission denied)"
        )
    return lines


def _md_render_complexity(data: dict) -> list[str]:
    lines: list[str] = []
    avg = data.get("avg_complexity")
    if avg is not None:
        lines.append(f"**Average complexity:** {avg:.1f}")
        lines.append("")
    hotspots = data.get("hotspots", [])
    if hotspots:
        lines.append("| File | CC | Grade |")
        lines.append("|------|-----|-------|")
        for h in hotspots[:5]:
            lines.append(f"| `{h.get('file')}` | {h.get('complexity')} | {h.get('grade')} |")
    return lines


def _md_render_lint(data: dict) -> list[str]:
    lines: list[str] = []
    errors = data.get("error_count", 0)
    warnings = data.get("warning_count", 0)
    lines.append(
        f"**{errors} error{'s' if errors != 1 else ''}**, {warnings} warning{'s' if warnings != 1 else ''}"
    )
    files = data.get("files_with_issues", [])
    if files:
        lines.append("")
        lines.append("| File | Errors | Warnings |")
        lines.append("|------|--------|----------|")
        for f in files[:10]:
            lines.append(f"| `{f.get('file')}` | {f.get('errors')} | {f.get('warnings')} |")
    return lines


def _md_render_types(data: dict) -> list[str]:
    lines: list[str] = []
    errors = data.get("error_count", 0)
    warnings = data.get("warning_count", 0)
    lines.append(
        f"**{errors} type error{'s' if errors != 1 else ''}**, {warnings} warning{'s' if warnings != 1 else ''}"
    )
    entries = data.get("errors", [])
    if entries:
        lines.append("")
        lines.append("| File | Line | Code | Message |")
        lines.append("|------|------|------|---------|")
        for e in entries[:10]:
            lines.append(
                f"| `{e.get('file')}` | {e.get('line')} | {e.get('code')} | {e.get('message')} |"
            )
    return lines


def _md_render_dependencies(data: dict) -> list[str]:
    lines: list[str] = []
    for ecosystem, info in data.items():
        runtime = info.get("runtime", [])
        dev = info.get("dev", [])
        total = info.get("total", 0)
        source_file = info.get("source_file", "")
        lines.append(f"**{total} dependencies** ({source_file})")
        lines.append("")
        lines.append("| Scope | Package |")
        lines.append("|-------|---------|")
        for pkg in runtime:
            lines.append(f"| runtime | `{pkg}` |")
        for pkg in dev:
            lines.append(f"| dev | `{pkg}` |")
    return lines


def _md_render_entry_points(data: dict) -> list[str]:
    lines: list[str] = []
    cli = data.get("cli", [])
    main_modules = data.get("main_modules", [])
    package_main = data.get("package_main")

    if not cli and not main_modules and not package_main:
        lines.append("No entry points found.")
        return lines

    if cli:
        n = len(cli)
        lines.append(f"**{n} CLI command{'s' if n != 1 else ''}**")
        lines.append("")
        for name in cli:
            lines.append(f"- `{name}`")
    if main_modules:
        lines.append("")
        lines.append("**`__main__.py` modules**")
        lines.append("")
        for mod in main_modules:
            lines.append(f"- `{mod}`")
    if package_main:
        lines.append("")
        lines.append(f"**package main:** `{package_main}`")
    return lines


def _md_render_test_coverage(data: dict) -> list[str]:
    lines: list[str] = []
    by_language = data.get("by_language", {})
    line_rate = data.get("line_rate")
    xml_present = data.get("coverage_xml_present", False)
    xml_ts = data.get("coverage_xml_timestamp")

    if xml_present and line_rate is not None:
        pct = int(line_rate * 100)
        ts = f" (coverage.xml, {xml_ts})" if xml_ts else ""
        lines.append(f"**Line coverage: {pct}%**{ts}")
        lines.append("")

    for lang, info in by_language.items():
        n_src = info.get("source_files", 0)
        n_test = info.get("test_files", 0)
        ratio = info.get("heuristic_ratio", 0.0)
        untested = info.get("untested_modules", [])
        pct = int(ratio * 100)
        lines.append(f"**{lang}: {pct}% structural** — {n_test} test / {n_src} source")
        if untested:
            lines.append("")
            lines.append(f"Possibly untested {lang} modules:")
            for mod in untested:
                lines.append(f"- `{mod}`")
        lines.append("")

    if not by_language and not xml_present:
        lines.append("No test files found.")
    return lines


def _md_render_git_activity(data: dict) -> list[str]:
    lines: list[str] = []
    commits = data.get("commits_in_window", 0)
    contributors = data.get("active_contributors", 0)
    coverage = data.get("coverage", 0.0)
    window = data.get("window", "90d")
    is_shallow = data.get("shallow_clone", False)
    hot_files = data.get("hot_files", [])
    hot_dirs = data.get("hot_dirs", [])

    pct = int(coverage * 100)
    lines.append(
        f"**{commits} commit{'s' if commits != 1 else ''}** in window `{window}`  —  "
        f"{contributors} contributor{'s' if contributors != 1 else ''},  {pct}% of files active"
    )

    if is_shallow:
        lines.append("")
        lines.append("> **⚠ Shallow clone** — git history may be incomplete (confidence capped at 0.60)")

    if hot_files:
        lines.append("")
        lines.append("**Hot files** (most frequently changed)")
        lines.append("")
        lines.append("| File | Changes |")
        lines.append("|------|---------|")
        for h in hot_files:
            lines.append(f"| `{h['path']}` | {h['changes']} |")

    if hot_dirs:
        lines.append("")
        lines.append("**Hot directories**")
        lines.append("")
        lines.append("| Directory | Changes |")
        lines.append("|-----------|---------|")
        for h in hot_dirs:
            lines.append(f"| `{h['path']}/` | {h['changes']} |")

    return lines


def _md_render_generic(data: dict) -> list[str]:
    return [f"```json\n{json.dumps(data, indent=2)}\n```"]


_MARKDOWN_RENDERERS: dict[str, Callable[[dict], list[str]]] = {
    "structure": _md_render_structure,
    "complexity": _md_render_complexity,
    "lint": _md_render_lint,
    "types": _md_render_types,
    "dependencies": _md_render_dependencies,
    "entry_points": _md_render_entry_points,
    "test_coverage": _md_render_test_coverage,
    "git_activity": _md_render_git_activity,
}


def to_json(snapshot: dict[str, Any]) -> str:
    """Serialize snapshot to a JSON string (pretty-printed, sorted keys)."""
    return json.dumps(snapshot, indent=2, sort_keys=False, default=str)


def to_markdown(snapshot: dict[str, Any]) -> str:
    """Render snapshot to a Markdown report string."""
    lines: list[str] = []
    repo = snapshot.get("repo", ".")
    scanned_at = snapshot.get("scanned_at", "")
    layers = snapshot.get("layers", {})
    skipped = snapshot.get("skipped_layers", [])

    lines.append(f"# Repo Cartographer — {Path(repo).name}")
    lines.append(f"")
    lines.append(f"**Repo:** `{repo}`  ")
    lines.append(f"**Scanned at:** {scanned_at}  ")
    lines.append(f"**Schema version:** {snapshot.get('schema_version', '?')}  ")
    lines.append("")

    for layer_key, layer in layers.items():
        source = layer.get("source", layer_key)
        confidence = layer.get("confidence", 0.0)
        data = layer.get("data", {})

        lines.append(f"## {layer_key.capitalize()} (`{source}`, confidence: {confidence:.2f})")
        lines.append("")

        md_fn = _MARKDOWN_RENDERERS.get(layer_key, _md_render_generic)
        lines.extend(md_fn(data))

        lines.append("")

    if skipped:
        lines.append("## Skipped Layers")
        lines.append("")
        lines.append("| Layer | Reason | Code |")
        lines.append("|-------|--------|------|")
        for entry in skipped:
            lines.append(
                f"| {entry.get('layer')} | {entry.get('reason')} | `{entry.get('reason_code')}` |"
            )
        lines.append("")

    return "\n".join(lines)


def write_outputs(
    snapshot: dict[str, Any],
    output_dir: Path,
    use_color: bool = True,
    stdout_mode: bool = False,
) -> None:
    """
    Write all three outputs.

    stdout_mode=True: JSON goes to stdout, terminal summary goes to stderr.
    stdout_mode=False (default): JSON and markdown written to output_dir,
                                  terminal summary printed to stdout.
    """
    json_str = to_json(snapshot)
    md_str = to_markdown(snapshot)

    if stdout_mode:
        # Terminal summary → stderr so stdout stays clean for piping.
        to_terminal(snapshot, use_color=use_color, file=sys.stderr)
        sys.stdout.write(json_str + "\n")
    else:
        to_terminal(snapshot, use_color=use_color, file=sys.stdout)
        json_path = output_dir / "repo-cart.json"
        md_path = output_dir / "repo-cart.md"
        json_path.write_text(json_str, encoding="utf-8")
        md_path.write_text(md_str, encoding="utf-8")
        print(f"Snapshot written to {json_path}")
        print(f"Report written to   {md_path}")
