"""
Tests for CLI functionality.

These tests verify the command-line interface logic.
"""

from __future__ import annotations

from typer.testing import CliRunner

from dwca_tools import __version__
from dwca_tools.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version_flag(self) -> None:
        """Version flag displays version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_displays(self) -> None:
        """Help message displays."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Darwin Core Archive" in result.stdout or "DwC-A" in result.stdout

    def test_summarize_help(self) -> None:
        """Summarize command help displays."""
        result = runner.invoke(app, ["summarize", "--help"])
        assert result.exit_code == 0
        assert "summarize" in result.stdout.lower()

    def test_convert_help(self) -> None:
        """Convert command help displays."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "convert" in result.stdout.lower()

    def test_aggregate_help(self) -> None:
        """Aggregate command help displays."""
        result = runner.invoke(app, ["aggregate", "--help"])
        assert result.exit_code == 0
        assert "aggregate" in result.stdout.lower()
