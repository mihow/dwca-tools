"""Application settings via pydantic-settings."""

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


class ConvertSettings(BaseSettings):
    """Settings for the convert pipeline.

    Reads DWCA_CHUNK_SIZE, DWCA_NUM_THREADS, etc. from env.
    """

    model_config = {"env_prefix": "DWCA_"}

    chunk_size: int = 500
    num_threads: int = 4
    columns_of_interest: dict[str, list[str]] = {
        "occurrence": [
            "gbifID",
            "scientificName",
            "decimalLatitude",
            "decimalLongitude",
            "eventDate",
        ],
        "verbatim": [
            "gbifID",
            "verbatimScientificName",
            "verbatimLatitude",
            "verbatimLongitude",
            "eventDate",
        ],
        "multimedia": [
            "gbifID",
            "identifier",
            "references",
            "title",
            "created",
        ],
    }
    indexes: dict[str, list[str]] = {
        "occurrence": ["gbifID", "scientificName", "eventDate"],
        "verbatim": ["gbifID", "verbatimScientificName", "eventDate"],
        "multimedia": ["gbifID", "identifier", "created"],
    }


@lru_cache
def get_convert_settings() -> ConvertSettings:
    """Return cached convert settings instance."""
    return ConvertSettings()
