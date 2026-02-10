"""
Extractor utilities for iNaturalist open data.

Handles reading, parsing, and filtering iNaturalist CSV data files.
"""

from __future__ import annotations

import gzip
from typing import TYPE_CHECKING, Any

import pandas as pd

from dwca_tools.inaturalist.downloader import download_observations, download_photos, download_taxa
from dwca_tools.inaturalist.models import ExtractionMetadata, Observation, Photo, Taxon

if TYPE_CHECKING:
    from pathlib import Path


def read_taxa_file(file_path: Path, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    Read and filter taxa CSV file.

    Args:
        file_path: Path to taxa CSV file (can be .gz compressed)
        filters: Optional filters to apply (e.g., {'rank': ['species', 'genus']})

    Returns:
        DataFrame with taxa data
    """
    # Read the tab-separated file
    with gzip.open(file_path, "rt") as f:
        df = pd.read_csv(f, sep="\t", low_memory=False)

    # Apply filters if provided
    if filters:
        for column, values in filters.items():
            if column in df.columns:
                if isinstance(values, list):
                    df = df[df[column].isin(values)]
                else:
                    df = df[df[column] == values]

    return df


def read_observations_file(
    file_path: Path, filters: dict[str, Any] | None = None
) -> pd.DataFrame:
    """
    Read and filter observations CSV file.

    Args:
        file_path: Path to observations CSV file (can be .gz compressed)
        filters: Optional filters to apply (e.g., {'quality_grade': 'research'})

    Returns:
        DataFrame with observations data
    """
    # Read the tab-separated file
    with gzip.open(file_path, "rt") as f:
        df = pd.read_csv(f, sep="\t", low_memory=False)

    # Apply filters if provided
    if filters:
        for column, values in filters.items():
            if column in df.columns:
                if isinstance(values, list):
                    df = df[df[column].isin(values)]
                else:
                    df = df[df[column] == values]

    return df


def read_photos_file(file_path: Path, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    Read and filter photos CSV file.

    Args:
        file_path: Path to photos CSV file (can be .gz compressed)
        filters: Optional filters to apply (e.g., {'license': ['CC-BY', 'CC0']})

    Returns:
        DataFrame with photos data
    """
    # Read the tab-separated file
    with gzip.open(file_path, "rt") as f:
        df = pd.read_csv(f, sep="\t", low_memory=False)

    # Apply filters if provided
    if filters:
        for column, values in filters.items():
            if column in df.columns:
                if isinstance(values, list):
                    df = df[df[column].isin(values)]
                else:
                    df = df[df[column] == values]

    return df


def extract_taxa(
    filters: dict[str, Any] | None = None,
    download_if_missing: bool = True,
) -> tuple[list[Taxon], ExtractionMetadata]:
    """
    Extract taxa records from iNaturalist data.

    Args:
        filters: Optional filters to apply
        download_if_missing: Download data if not cached

    Returns:
        Tuple of (taxa list, metadata)
    """
    # Get or download file
    if download_if_missing:
        file_path, _ = download_taxa()
    else:
        from dwca_tools.inaturalist.downloader import get_latest_file

        file_path = get_latest_file("taxa")
        if file_path is None:
            raise FileNotFoundError("No cached taxa file found. Use download_if_missing=True")

    # Read and filter data
    df = read_taxa_file(file_path, filters)

    # Convert to Taxon objects (sample first 1000 for now to avoid memory issues)
    taxa = []
    for _, row in df.head(1000).iterrows():
        taxon = Taxon(
            taxon_id=int(row["taxon_id"]),
            name=str(row["name"]),
            rank=str(row["rank"]),
            ancestry=str(row["ancestry"]) if pd.notna(row["ancestry"]) else None,
            active=bool(row.get("active", True)),
            parent_id=int(row["parent_id"]) if pd.notna(row.get("parent_id")) else None,
        )
        taxa.append(taxon)

    # Generate metadata
    metadata = ExtractionMetadata(
        source="inaturalist",
        total_records=len(taxa),
        filters=filters or {},
    )

    return taxa, metadata


def extract_observations(
    filters: dict[str, Any] | None = None,
    download_if_missing: bool = True,
) -> tuple[list[Observation], ExtractionMetadata]:
    """
    Extract observation records from iNaturalist data.

    Args:
        filters: Optional filters to apply
        download_if_missing: Download data if not cached

    Returns:
        Tuple of (observations list, metadata)
    """
    # Get or download file
    if download_if_missing:
        file_path, _ = download_observations()
    else:
        from dwca_tools.inaturalist.downloader import get_latest_file

        file_path = get_latest_file("observations")
        if file_path is None:
            raise FileNotFoundError(
                "No cached observations file found. Use download_if_missing=True"
            )

    # Read and filter data
    df = read_observations_file(file_path, filters)

    # Convert to Observation objects (sample first 1000 for now)
    observations = []
    for _, row in df.head(1000).iterrows():
        observation = Observation(
            observation_id=int(row["observation_uuid"]),
            observer_id=int(row["observer_id"]),
            latitude=float(row["latitude"]) if pd.notna(row.get("latitude")) else None,
            longitude=float(row["longitude"]) if pd.notna(row.get("longitude")) else None,
            positional_accuracy=(
                int(row["positional_accuracy"]) if pd.notna(row.get("positional_accuracy")) else None
            ),
            taxon_id=int(row["taxon_id"]) if pd.notna(row.get("taxon_id")) else None,
            quality_grade=str(row["quality_grade"]),
            observed_on=str(row["observed_on"]),
            created_at=pd.to_datetime(row["created_at"]),
            updated_at=pd.to_datetime(row["updated_at"]),
            license=str(row["license"]) if pd.notna(row.get("license")) else None,
        )
        observations.append(observation)

    # Generate metadata
    metadata = ExtractionMetadata(
        source="inaturalist",
        total_records=len(observations),
        filters=filters or {},
    )

    return observations, metadata


def extract_photos(
    filters: dict[str, Any] | None = None,
    download_if_missing: bool = True,
) -> tuple[list[Photo], ExtractionMetadata]:
    """
    Extract photo records from iNaturalist data.

    Args:
        filters: Optional filters to apply
        download_if_missing: Download data if not cached

    Returns:
        Tuple of (photos list, metadata)
    """
    # Get or download file
    if download_if_missing:
        file_path, _ = download_photos()
    else:
        from dwca_tools.inaturalist.downloader import get_latest_file

        file_path = get_latest_file("photos")
        if file_path is None:
            raise FileNotFoundError("No cached photos file found. Use download_if_missing=True")

    # Read and filter data
    df = read_photos_file(file_path, filters)

    # Convert to Photo objects (sample first 1000 for now)
    photos = []
    for _, row in df.head(1000).iterrows():
        photo = Photo(
            photo_id=int(row["photo_id"]),
            observation_id=int(row["observation_uuid"]),
            observer_id=int(row["observer_id"]),
            extension=str(row["extension"]),
            license=str(row["license"]),
            width=int(row["width"]) if pd.notna(row.get("width")) else None,
            height=int(row["height"]) if pd.notna(row.get("height")) else None,
            position=int(row.get("position", 0)),
        )
        photos.append(photo)

    # Generate metadata
    metadata = ExtractionMetadata(
        source="inaturalist",
        total_records=len(photos),
        filters=filters or {},
    )

    return photos, metadata
