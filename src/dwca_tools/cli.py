"""
Command-line interface for dwca-tools.

This module provides the main entry point for the CLI.
"""

from __future__ import annotations

import typer

from . import __version__
from .aggregate import app as aggregate_app
from .convert import app as convert_app
from .summarize import app as summarize_app

app = typer.Typer(
    no_args_is_help=True,
    help="Tools for working with Darwin Core Archive (DwC-A) files",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"dwca-tools version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Darwin Core Archive Tools - Inspect and convert DwC-A files."""
    pass


# Add subcommands
app.add_typer(summarize_app, name="summarize", help="Inspect and summarize DwC-A files")
app.add_typer(convert_app, name="convert", help="Convert DwC-A files to SQL databases")
app.add_typer(aggregate_app, name="aggregate", help="Create aggregation tables")


if __name__ == "__main__":
    app()

