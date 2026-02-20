"""Utility functions for dwca-tools."""

from __future__ import annotations

import humanize


def human_readable_size(size: int) -> str:
    """Convert byte size to human-readable format."""
    return humanize.naturalsize(size, binary=True)


def human_readable_number(number: int) -> str:
    """Format number with thousands separators."""
    return humanize.intcomma(number)
