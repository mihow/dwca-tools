"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides fixtures
available to all test files.
"""

import asyncio
from pathlib import Path

import pytest

# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


# =============================================================================
# Async Fixtures (if needed)
# =============================================================================


@pytest.fixture
def event_loop_policy():
    """Use default event loop policy for async tests."""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Marker Configurations
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "unit: marks unit tests")

