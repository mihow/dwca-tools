"""Utility functions for dwca-tools."""

from __future__ import annotations

import configparser
from pathlib import Path

CONFIG_FILE = "defaults.ini"


def read_config() -> configparser.ConfigParser:
    """Read configuration from defaults.ini file."""
    config = configparser.ConfigParser()
    config_path = Path(CONFIG_FILE)
    if config_path.exists():
        config.read(config_path)
    return config


def update_config(config: configparser.ConfigParser) -> None:
    """Write configuration to defaults.ini file."""
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)
