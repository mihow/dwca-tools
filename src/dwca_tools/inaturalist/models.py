"""
Data models for iNaturalist open data.

These models represent the structure of iNaturalist's open data exports
as documented at https://github.com/inaturalist/inaturalist-open-data
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Taxon(BaseModel):
    """
    Taxon model representing a taxonomic classification.

    Based on taxa.csv.gz from iNaturalist open data.
    """

    taxon_id: int = Field(..., description="Unique taxon identifier")
    name: str = Field(..., description="Scientific name")
    rank: str = Field(..., description="Taxonomic rank (e.g., species, genus, family)")
    ancestry: str | None = Field(None, description="Slash-separated parent taxon IDs")
    active: bool = Field(default=True, description="Whether taxon is active or a synonym")
    parent_id: int | None = Field(None, description="Direct parent taxon ID")

    class Config:
        """Pydantic model configuration."""

        frozen = False


class Observer(BaseModel):
    """
    Observer model representing an iNaturalist user.

    Based on observers.csv.gz from iNaturalist open data.
    """

    observer_id: int = Field(..., description="Unique observer identifier")
    login: str = Field(..., description="Observer login username")
    name: str | None = Field(None, description="Observer display name")

    class Config:
        """Pydantic model configuration."""

        frozen = False


class Photo(BaseModel):
    """
    Photo model representing an image in iNaturalist.

    Based on photos.csv.gz from iNaturalist open data.
    """

    photo_id: int = Field(..., description="Unique photo identifier")
    observation_id: int = Field(..., description="Associated observation ID")
    observer_id: int = Field(..., description="Observer who uploaded the photo")
    extension: str = Field(..., description="File extension (e.g., jpg, png)")
    license: str = Field(..., description="Creative Commons license")
    width: int | None = Field(None, description="Original width in pixels")
    height: int | None = Field(None, description="Original height in pixels")
    position: int = Field(default=0, description="Position in observation photo list")

    class Config:
        """Pydantic model configuration."""

        frozen = False

    def get_url(self, size: str = "medium") -> str:
        """
        Generate the S3 URL for this photo.

        Args:
            size: Photo size (original, large, medium, small, thumb, square)

        Returns:
            Full S3 URL to the photo
        """
        base_url = "https://inaturalist-open-data.s3.amazonaws.com"
        return f"{base_url}/photos/{self.photo_id}/{size}.{self.extension}"


class Observation(BaseModel):
    """
    Observation model representing an encounter with an organism.

    Based on observations.csv.gz from iNaturalist open data.
    """

    observation_id: int = Field(..., description="Unique observation identifier")
    observer_id: int = Field(..., description="Observer who made the observation")
    latitude: float | None = Field(None, description="Latitude of observation")
    longitude: float | None = Field(None, description="Longitude of observation")
    positional_accuracy: int | None = Field(
        None, description="Position accuracy in meters"
    )
    taxon_id: int | None = Field(None, description="Identified taxon ID")
    quality_grade: str = Field(..., description="Quality grade (research, needs_id, casual)")
    observed_on: str = Field(..., description="Date of observation (YYYY-MM-DD)")
    created_at: datetime = Field(..., description="Timestamp when observation was created")
    updated_at: datetime = Field(..., description="Timestamp when observation was last updated")
    license: str | None = Field(None, description="Creative Commons license")

    class Config:
        """Pydantic model configuration."""

        frozen = False


class DownloadMetadata(BaseModel):
    """Metadata for tracking downloaded iNaturalist data files."""

    download_date: str = Field(..., description="Date when file was downloaded")
    source_url: str = Field(..., description="URL where file was downloaded from")
    file_hash: str = Field(..., description="MD5 hash of downloaded file")
    file_size_bytes: int = Field(..., description="Size of file in bytes")
    last_modified: str | None = Field(
        None, description="Last-Modified header from remote server"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False


class ExtractionMetadata(BaseModel):
    """Metadata for tracking data extraction operations."""

    extracted_at: datetime = Field(default_factory=datetime.now, description="Extraction time")
    source: str = Field(..., description="Data source (e.g., 'inaturalist')")
    total_records: int = Field(..., description="Total number of records extracted")
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Filters applied during extraction"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
