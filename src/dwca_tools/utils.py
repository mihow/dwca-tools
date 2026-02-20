"""Utility functions for dwca-tools."""

from __future__ import annotations

import configparser
from pathlib import Path

import humanize

CONFIG_FILE = "defaults.ini"


def human_readable_size(size: int) -> str:
    """Convert byte size to human-readable format."""
    return humanize.naturalsize(size, binary=True)


def human_readable_number(number: int) -> str:
    """Format number with thousands separators."""
    return humanize.intcomma(number)


def read_config() -> configparser.ConfigParser:
    """Read configuration from defaults.ini file."""
    config = configparser.ConfigParser()
    config_path = Path(CONFIG_FILE)
    if config_path.exists():
        config.read(config_path)
    return config


def update_config(config: configparser.ConfigParser) -> None:
    """Write configuration to defaults.ini file."""
    Path(CONFIG_FILE).write_text("")
    with Path(CONFIG_FILE).open("w") as configfile:
        config.write(configfile)
