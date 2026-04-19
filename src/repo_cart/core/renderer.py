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
import sys
from pathlib import Path
from typing import Any, TextIO


# ANSI escape sequences.
_RESET = "\033[0m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


def _c(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{_RESET}" if use_color else text


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

        if layer_key == "structure":
            _render_structure(data, use_color, file)
        elif layer_key == "complexity":
            _render_complexity(data, use_color, file)
        elif layer_key == "lint":
            _render_lint(data, use_color, file)
        else:
            # Generic layer rendering for future adapters.
            print(f"  {data}", file=file)

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


def to_json(snapshot: dict[str, Any]) -> str:
    """Serialize snapshot to a JSON string (pretty-printed, sorted keys)."""
    return json.dumps(snapshot, indent=2, sort_keys=False, default=str)


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

        if layer_key == "structure":
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
                lines.append(f"- **Warning:** {n} director{'y' if n == 1 else 'ies'} could not be read (permission denied)")
        elif layer_key == "complexity":
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
        elif layer_key == "lint":
            errors = data.get("error_count", 0)
            warnings = data.get("warning_count", 0)
            lines.append(f"**{errors} error{'s' if errors != 1 else ''}**, {warnings} warning{'s' if warnings != 1 else ''}")
            files = data.get("files_with_issues", [])
            if files:
                lines.append("")
                lines.append("| File | Errors | Warnings |")
                lines.append("|------|--------|----------|")
                for f in files[:10]:
                    lines.append(f"| `{f.get('file')}` | {f.get('errors')} | {f.get('warnings')} |")
        else:
            lines.append(f"```json\n{json.dumps(data, indent=2)}\n```")

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
