"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides fixtures
available to all test files.
"""

import pytest


# =============================================================================
# Marker Configurations
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
