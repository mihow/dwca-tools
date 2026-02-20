"""GBIF credential management via pydantic-settings."""

from __future__ import annotations

import getpass
from functools import lru_cache

from pydantic_settings import BaseSettings


class GbifSettings(BaseSettings):
    """GBIF API credentials loaded from environment variables.

    Reads GBIF_USERNAME, GBIF_PASSWORD, GBIF_EMAIL from env.
    """

    model_config = {"env_prefix": "GBIF_", "env_file": ".env"}

    username: str = ""
    password: str = ""
    email: str = ""


@lru_cache
def get_gbif_settings() -> GbifSettings:
    """Return cached GBIF settings instance."""
    return GbifSettings()


def resolve_password(settings: GbifSettings, username: str) -> str:
    """Return password from settings or prompt the user via getpass."""
    if settings.password:
        return settings.password
    return getpass.getpass(f"Password for GBIF user {username}: ")
