"""CLI entry point — repo-cart [path]"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from repo_cart.adapters.common.deps_adapter import DepsAdapter
from repo_cart.adapters.common.entry_points_adapter import EntryPointsAdapter
from repo_cart.adapters.js_ts.eslint_adapter import ESLintAdapter
from repo_cart.adapters.js_ts.tsc_adapter import TscAdapter
from repo_cart.adapters.python.radon_adapter import RadonAdapter
from repo_cart.core.orchestrator import scan
from repo_cart.core.renderer import write_outputs

# All registered adapters. New adapters are added here.
_DEFAULT_ADAPTERS = [
    DepsAdapter(),
    EntryPointsAdapter(),
    RadonAdapter(),
    ESLintAdapter(),
    TscAdapter(),
]

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
) -> None:
    """Scan a repository and produce a layered map."""
    target = (path or Path(".")).resolve()

    if not target.exists():
        typer.echo(f"Error: path does not exist: {target}", err=True)
        raise typer.Exit(code=1)
    if not target.is_dir():
        typer.echo(f"Error: path is not a directory: {target}", err=True)
        raise typer.Exit(code=1)

    use_color = not no_color and sys.stdout.isatty()

    try:
        snapshot = scan(target, _DEFAULT_ADAPTERS)
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
