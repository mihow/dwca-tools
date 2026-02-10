"""Tests for iNaturalist data models."""

from __future__ import annotations

from datetime import datetime

import pytest

from dwca_tools.inaturalist.models import (
    DownloadMetadata,
    ExtractionMetadata,
    Observation,
    Observer,
    Photo,
    Taxon,
)


class TestTaxon:
    """Tests for Taxon model."""

    def test_create_minimal(self) -> None:
        """Can create taxon with minimal fields."""
        taxon = Taxon(
            taxon_id=123,
            name="Papilio machaon",
            rank="species",
        )
        assert taxon.taxon_id == 123
        assert taxon.name == "Papilio machaon"
        assert taxon.rank == "species"
        assert taxon.active is True

    def test_create_full(self) -> None:
        """Can create taxon with all fields."""
        taxon = Taxon(
            taxon_id=123,
            name="Papilio machaon",
            rank="species",
            ancestry="48460/1/47120",
            active=True,
            parent_id=47120,
        )
        assert taxon.taxon_id == 123
        assert taxon.ancestry == "48460/1/47120"
        assert taxon.parent_id == 47120


class TestObserver:
    """Tests for Observer model."""

    def test_create_observer(self) -> None:
        """Can create observer."""
        observer = Observer(
            observer_id=456,
            login="testuser",
            name="Test User",
        )
        assert observer.observer_id == 456
        assert observer.login == "testuser"
        assert observer.name == "Test User"


class TestPhoto:
    """Tests for Photo model."""

    def test_create_photo(self) -> None:
        """Can create photo."""
        photo = Photo(
            photo_id=789,
            observation_id=123,
            observer_id=456,
            extension="jpg",
            license="CC-BY",
        )
        assert photo.photo_id == 789
        assert photo.observation_id == 123
        assert photo.license == "CC-BY"

    def test_get_url(self) -> None:
        """Can generate photo URL."""
        photo = Photo(
            photo_id=789,
            observation_id=123,
            observer_id=456,
            extension="jpg",
            license="CC-BY",
        )
        url = photo.get_url("medium")
        assert url == "https://inaturalist-open-data.s3.amazonaws.com/photos/789/medium.jpg"

    def test_get_url_different_sizes(self) -> None:
        """Can generate URLs for different sizes."""
        photo = Photo(
            photo_id=789,
            observation_id=123,
            observer_id=456,
            extension="jpg",
            license="CC-BY",
        )
        assert "large.jpg" in photo.get_url("large")
        assert "small.jpg" in photo.get_url("small")
        assert "thumb.jpg" in photo.get_url("thumb")


class TestObservation:
    """Tests for Observation model."""

    def test_create_observation(self) -> None:
        """Can create observation."""
        now = datetime.now()
        observation = Observation(
            observation_id=123,
            observer_id=456,
            quality_grade="research",
            observed_on="2024-01-15",
            created_at=now,
            updated_at=now,
        )
        assert observation.observation_id == 123
        assert observation.quality_grade == "research"
        assert observation.observed_on == "2024-01-15"

    def test_optional_fields(self) -> None:
        """Optional fields can be None."""
        now = datetime.now()
        observation = Observation(
            observation_id=123,
            observer_id=456,
            latitude=None,
            longitude=None,
            taxon_id=None,
            quality_grade="needs_id",
            observed_on="2024-01-15",
            created_at=now,
            updated_at=now,
        )
        assert observation.latitude is None
        assert observation.longitude is None
        assert observation.taxon_id is None


class TestDownloadMetadata:
    """Tests for DownloadMetadata model."""

    def test_create_metadata(self) -> None:
        """Can create download metadata."""
        metadata = DownloadMetadata(
            download_date="2024-01-15",
            source_url="https://example.com/taxa.csv.gz",
            file_hash="abc123",
            file_size_bytes=1024,
        )
        assert metadata.download_date == "2024-01-15"
        assert metadata.file_hash == "abc123"
        assert metadata.file_size_bytes == 1024


class TestExtractionMetadata:
    """Tests for ExtractionMetadata model."""

    def test_create_metadata(self) -> None:
        """Can create extraction metadata."""
        metadata = ExtractionMetadata(
            source="inaturalist",
            total_records=100,
            filters={"rank": "species"},
        )
        assert metadata.source == "inaturalist"
        assert metadata.total_records == 100
        assert metadata.filters == {"rank": "species"}
        assert isinstance(metadata.extracted_at, datetime)
