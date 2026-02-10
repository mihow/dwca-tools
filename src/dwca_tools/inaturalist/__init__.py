"""
iNaturalist Open Data integration for dwca-tools.

This module provides tools for downloading, parsing, and working with
iNaturalist's open data exports.
"""

from dwca_tools.inaturalist.downloader import (
    download_observations,
    download_photos,
    download_taxa,
)
from dwca_tools.inaturalist.extractor import (
    extract_observations,
    extract_photos,
    extract_taxa,
)
from dwca_tools.inaturalist.models import (
    DownloadMetadata,
    ExtractionMetadata,
    Observation,
    Observer,
    Photo,
    Taxon,
)

__all__ = [
    "DownloadMetadata",
    "ExtractionMetadata",
    "Observation",
    "Observer",
    "Photo",
    "Taxon",
    "download_observations",
    "download_photos",
    "download_taxa",
    "extract_observations",
    "extract_photos",
    "extract_taxa",
]
