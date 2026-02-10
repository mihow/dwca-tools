"""
Downloader utilities for iNaturalist open data.

Handles downloading, caching, and versioning of iNaturalist data files.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen, urlretrieve

from dwca_tools.inaturalist.models import DownloadMetadata

# iNaturalist Open Data URLs
INAT_BASE_URL = "https://inaturalist-open-data.s3.amazonaws.com"
INAT_TAXA_URL = f"{INAT_BASE_URL}/taxa.csv.gz"
INAT_OBSERVATIONS_URL = f"{INAT_BASE_URL}/observations.csv.gz"
INAT_PHOTOS_URL = f"{INAT_BASE_URL}/photos.csv.gz"
INAT_OBSERVERS_URL = f"{INAT_BASE_URL}/observers.csv.gz"


def get_cache_dir(data_type: str) -> Path:
    """
    Get cache directory for a specific data type.

    Args:
        data_type: Type of data (taxa, observations, photos, observers)

    Returns:
        Path to cache directory
    """
    cache_dir = Path.home() / ".cache" / "dwca-tools" / "inaturalist" / data_type
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate MD5 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        MD5 hash as hex string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_remote_last_modified(url: str) -> str | None:
    """
    Get Last-Modified header from remote URL.

    Args:
        url: URL to check

    Returns:
        Last-Modified header value or None
    """
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=10) as response:
            return response.headers.get("Last-Modified")
    except (URLError, TimeoutError):
        return None


def download_file(
    url: str,
    data_type: str,
    force: bool = False,
    progress_callback: Any = None,
) -> tuple[Path, bool]:
    """
    Download iNaturalist data file with versioning and caching.

    Creates a versioned copy based on download date and maintains symlink to 'latest'.
    Skips download if file hash matches existing file (unless force=True).

    Args:
        url: URL to download from
        data_type: Type of data (taxa, observations, photos, observers)
        force: Force re-download even if file exists
        progress_callback: Optional callback function for progress updates

    Returns:
        Tuple of (file_path, was_downloaded)
        - file_path: Path to the versioned file
        - was_downloaded: True if file was newly downloaded
    """
    cache_dir = get_cache_dir(data_type)
    today = date.today().strftime("%Y-%m-%d")
    versioned_filename = f"{data_type}-{today}.csv.gz"
    versioned_path = cache_dir / versioned_filename
    latest_symlink = cache_dir / f"{data_type}-latest.csv.gz"
    metadata_path = cache_dir / f"{data_type}-{today}.metadata.json"

    # Check if versioned file already exists
    if versioned_path.exists() and not force:
        # Ensure symlink points to this version
        if latest_symlink.exists() or latest_symlink.is_symlink():
            latest_symlink.unlink()
        if not latest_symlink.exists():
            latest_symlink.symlink_to(versioned_filename)

        return versioned_path, False

    # Download to temporary file first
    temp_path = cache_dir / f"{data_type}-{today}.tmp.gz"

    # Get last modified timestamp
    last_modified = get_remote_last_modified(url)

    # Download file
    if progress_callback:
        urlretrieve(url, temp_path, reporthook=progress_callback)
    else:
        urlretrieve(url, temp_path)

    # Calculate hash
    file_hash = calculate_file_hash(temp_path)

    # Check if we already have this exact file from a previous download
    for existing_file in cache_dir.glob(f"{data_type}-*.csv.gz"):
        if existing_file.name.startswith(f"{data_type}-") and existing_file.name.endswith(
            ".csv.gz"
        ):
            if not existing_file.name.endswith(".tmp.gz") and existing_file != versioned_path:
                if calculate_file_hash(existing_file) == file_hash:
                    # File is identical, just update symlink
                    temp_path.unlink()
                    if latest_symlink.exists() or latest_symlink.is_symlink():
                        latest_symlink.unlink()
                    latest_symlink.symlink_to(existing_file.name)
                    return existing_file, False

    # Move temp file to versioned location
    shutil.move(str(temp_path), str(versioned_path))

    # Save metadata
    metadata = DownloadMetadata(
        download_date=today,
        source_url=url,
        last_modified=last_modified,
        file_hash=file_hash,
        file_size_bytes=versioned_path.stat().st_size,
    )
    with open(metadata_path, "w") as f:
        json.dump(metadata.model_dump(), f, indent=2)

    # Update 'latest' symlink
    if latest_symlink.exists() or latest_symlink.is_symlink():
        latest_symlink.unlink()
    latest_symlink.symlink_to(versioned_filename)

    return versioned_path, True


def download_taxa(force: bool = False) -> tuple[Path, bool]:
    """Download iNaturalist taxa data."""
    return download_file(INAT_TAXA_URL, "taxa", force=force)


def download_observations(force: bool = False) -> tuple[Path, bool]:
    """Download iNaturalist observations data."""
    return download_file(INAT_OBSERVATIONS_URL, "observations", force=force)


def download_photos(force: bool = False) -> tuple[Path, bool]:
    """Download iNaturalist photos data."""
    return download_file(INAT_PHOTOS_URL, "photos", force=force)


def download_observers(force: bool = False) -> tuple[Path, bool]:
    """Download iNaturalist observers data."""
    return download_file(INAT_OBSERVERS_URL, "observers", force=force)


def get_latest_file(data_type: str) -> Path | None:
    """
    Get the latest cached file for a data type.

    Args:
        data_type: Type of data (taxa, observations, photos, observers)

    Returns:
        Path to latest file or None if not found
    """
    cache_dir = get_cache_dir(data_type)
    latest_symlink = cache_dir / f"{data_type}-latest.csv.gz"

    if latest_symlink.exists():
        return latest_symlink

    return None
