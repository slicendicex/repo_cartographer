"""CLI entry point — repo-cart [path]"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from repo_cart.adapters.common.deps_adapter import DepsAdapter
from repo_cart.adapters.common.entry_points_adapter import EntryPointsAdapter
from repo_cart.adapters.common.test_coverage_adapter import TestCoverageAdapter
from repo_cart.adapters.js_ts.eslint_adapter import ESLintAdapter
from repo_cart.adapters.js_ts.tsc_adapter import TscAdapter
from repo_cart.adapters.python.radon_adapter import RadonAdapter
from repo_cart.adapters.vcs.git_activity_adapter import GitActivityAdapter
from repo_cart.core.orchestrator import scan
from repo_cart.core.renderer import write_outputs

_WINDOW_HELP = "Git activity window: 30d, 90d, 365d, or all. Default: 90d."

app = typer.Typer(
    name="repo-cart",
    help="Layered CLI repo mapper — produces terminal summary, markdown, and JSON from a single scan.",
    add_completion=False,
)


@app.command()
def scan_cmd(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to the repo to scan. Defaults to current directory."),
    ] = None,
    stdout: Annotated[
        bool,
        typer.Option("--stdout", help="Write JSON to stdout instead of disk. Terminal summary goes to stderr."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable ANSI color codes (for CI environments)."),
    ] = False,
    window: Annotated[
        str,
        typer.Option("--window", help=_WINDOW_HELP),
    ] = "90d",
) -> None:
    """Scan a repository and produce a layered map."""
    target = (path or Path(".")).resolve()

    if not target.exists():
        typer.echo(f"Error: path does not exist: {target}", err=True)
        raise typer.Exit(code=1)
    if not target.is_dir():
        typer.echo(f"Error: path is not a directory: {target}", err=True)
        raise typer.Exit(code=1)

    if window not in {"30d", "90d", "365d", "all"}:
        typer.echo(f"Error: --window must be one of 30d, 90d, 365d, all (got {window!r})", err=True)
        raise typer.Exit(code=1)

    adapters = [
        DepsAdapter(),
        EntryPointsAdapter(),
        TestCoverageAdapter(),
        RadonAdapter(),
        ESLintAdapter(),
        TscAdapter(),
        GitActivityAdapter(window=window),
    ]

    use_color = not no_color and sys.stdout.isatty()

    try:
        snapshot = scan(target, adapters)
    except Exception as exc:
        typer.echo(f"Error: scan failed — {exc}", err=True)
        raise typer.Exit(code=1)

    try:
        write_outputs(snapshot, output_dir=target, use_color=use_color, stdout_mode=stdout)
    except Exception as exc:
        typer.echo(f"Error: failed to write outputs — {exc}", err=True)
        raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
