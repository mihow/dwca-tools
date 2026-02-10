"""
Smoke tests - verify the application actually runs.

These tests execute real code paths, not just unit test mocks.
If these fail, the application is broken regardless of unit test results.
"""

import subprocess
import sys
from pathlib import Path


class TestImports:
    """Verify all modules import without errors."""

    def test_package_imports(self) -> None:
        """Main package imports successfully."""
        from dwca_tools import Example, Settings, __version__

        assert __version__
        assert Settings is not None
        assert Example is not None

    def test_all_modules_import(self) -> None:
        """All submodules import without errors."""
        from dwca_tools import cli, config, core, models

        assert cli
        assert config
        assert core
        assert models


class TestCLI:
    """Verify CLI actually executes."""

    def test_cli_info_runs(self) -> None:
        """CLI info command executes and returns success."""
        result = subprocess.run(
            [sys.executable, "-m", "dwca_tools.cli", "info"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "dwca-tools" in result.stdout.lower() or "version" in result.stdout.lower()

    def test_cli_run_executes(self) -> None:
        """CLI run command executes without error."""
        result = subprocess.run(
            [sys.executable, "-m", "dwca_tools.cli", "run", "--name", "smoke-test"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "success" in result.stdout.lower()

    def test_cli_help_works(self) -> None:
        """CLI --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "dwca_tools.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


class TestCoreIntegration:
    """Verify core functionality works end-to-end."""

    def test_create_and_process(self) -> None:
        """Full workflow: create example, process it, verify result."""
        from dwca_tools.core import create_example, process_example
        from dwca_tools.models import Status

        # Create
        example = create_example("integration-test", metadata={"test": "true"})
        assert example.id
        assert example.status == Status.PENDING

        # Process
        result = process_example("integration-test")
        assert result.success is True
        assert result.data is not None
        assert "id" in result.data

    def test_config_loads(self) -> None:
        """Configuration loads from environment."""
        from dwca_tools.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.app_name
        assert settings.app_env
