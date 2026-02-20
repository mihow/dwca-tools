"""Tests for the GBIF download module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from dwca_tools.cli import app
from dwca_tools.download import (
    build_predicate,
    build_request_body,
    load_extra_predicate,
    load_values_from_file,
    predicate_and,
    predicate_equals,
    predicate_in,
)
from dwca_tools.settings import GbifSettings, get_gbif_settings

runner = CliRunner()


# ---------------------------------------------------------------------------
# Predicate builders
# ---------------------------------------------------------------------------


class TestPredicateBuilder:
    """Unit tests for predicate builder functions."""

    def test_predicate_in_single_key(self) -> None:
        result = predicate_in("TAXON_KEY", ["12345"])
        assert result == {"type": "in", "key": "TAXON_KEY", "values": ["12345"]}

    def test_predicate_in_multiple_keys(self) -> None:
        result = predicate_in("TAXON_KEY", ["1", "2", "3"])
        assert result["values"] == ["1", "2", "3"]

    def test_predicate_equals(self) -> None:
        result = predicate_equals("COUNTRY", "US")
        assert result == {"type": "equals", "key": "COUNTRY", "value": "US"}

    def test_predicate_and_single(self) -> None:
        """Single predicate is returned as-is, not wrapped."""
        pred = predicate_equals("COUNTRY", "US")
        result = predicate_and([pred])
        assert result == pred

    def test_predicate_and_multiple(self) -> None:
        p1 = predicate_in("TAXON_KEY", ["1"])
        p2 = predicate_equals("COUNTRY", "US")
        result = predicate_and([p1, p2])
        assert result["type"] == "and"
        assert len(result["predicates"]) == 2

    def test_build_predicate_taxon_keys_only(self) -> None:
        result = build_predicate(["123", "456"])
        assert result == {"type": "in", "key": "TAXON_KEY", "values": ["123", "456"]}

    def test_build_predicate_match_names(self) -> None:
        result = build_predicate(["Canis lupus"], match_names=True)
        assert result["key"] == "VERBATIM_SCIENTIFIC_NAME"

    def test_build_predicate_has_images(self) -> None:
        result = build_predicate(["1"], has_images=True)
        assert result["type"] == "and"
        media_pred = result["predicates"][1]
        assert media_pred == {"type": "equals", "key": "MEDIA_TYPE", "value": "StillImage"}

    def test_build_predicate_country(self) -> None:
        result = build_predicate(["1"], country="US")
        assert result["type"] == "and"
        country_pred = result["predicates"][1]
        assert country_pred == {"type": "equals", "key": "COUNTRY", "value": "US"}

    def test_build_predicate_gadm_gid(self) -> None:
        result = build_predicate(["1"], gadm_gid="ETH.1_1")
        assert result["type"] == "and"
        gadm_pred = result["predicates"][1]
        assert gadm_pred == {"type": "equals", "key": "GADM_GID", "value": "ETH.1_1"}

    def test_build_predicate_extra_predicate(self) -> None:
        extra = {"type": "equals", "key": "BASIS_OF_RECORD", "value": "HUMAN_OBSERVATION"}
        result = build_predicate(["1"], extra_predicate=extra)
        assert result["type"] == "and"
        assert result["predicates"][1] == extra

    def test_build_predicate_dataset_key(self) -> None:
        result = build_predicate(["1"], dataset_key="50c9509d-22c7-4a22-a47d-8c48425ef4a7")
        assert result["type"] == "and"
        ds_pred = result["predicates"][1]
        assert ds_pred == {
            "type": "equals",
            "key": "DATASET_KEY",
            "value": "50c9509d-22c7-4a22-a47d-8c48425ef4a7",
        }

    def test_build_predicate_all_filters(self) -> None:
        extra = {"type": "equals", "key": "YEAR", "value": "2024"}
        result = build_predicate(
            ["1", "2"],
            match_names=True,
            has_images=True,
            country="US",
            gadm_gid="USA.1_1",
            dataset_key="50c9509d-22c7-4a22-a47d-8c48425ef4a7",
            extra_predicate=extra,
        )
        assert result["type"] == "and"
        assert len(result["predicates"]) == 6
        assert result["predicates"][0]["key"] == "VERBATIM_SCIENTIFIC_NAME"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


class TestLoadValuesFromFile:
    """Tests for load_values_from_file."""

    def test_reads_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "keys.txt"
        f.write_text("111\n222\n333\n")
        assert load_values_from_file(f) == ["111", "222", "333"]

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "keys.txt"
        f.write_text("111\n\n  \n222\n")
        assert load_values_from_file(f) == ["111", "222"]

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        f = tmp_path / "keys.txt"
        f.write_text("  111  \n  222  \n")
        assert load_values_from_file(f) == ["111", "222"]

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "keys.txt"
        f.write_text("")
        assert load_values_from_file(f) == []


class TestLoadExtraPredicate:
    """Tests for load_extra_predicate."""

    def test_loads_json(self, tmp_path: Path) -> None:
        f = tmp_path / "pred.json"
        pred = {"type": "equals", "key": "YEAR", "value": "2024"}
        f.write_text(json.dumps(pred))
        assert load_extra_predicate(f) == pred


# ---------------------------------------------------------------------------
# Request body builder
# ---------------------------------------------------------------------------


class TestBuildRequestBody:
    """Tests for build_request_body."""

    def test_structure(self) -> None:
        pred = predicate_in("TAXON_KEY", ["1"])
        body = build_request_body(pred, "user1", "user@example.com", "DWCA")
        assert body["creator"] == "user1"
        assert body["notificationAddresses"] == ["user@example.com"]
        assert body["format"] == "DWCA"
        assert body["predicate"] == pred
        assert body["sendNotification"] is True


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestGbifSettings:
    """Tests for GbifSettings via pydantic-settings."""

    def test_defaults_are_empty(self) -> None:
        get_gbif_settings.cache_clear()
        settings = GbifSettings(username="", password="", email="")
        assert settings.username == ""
        assert settings.password == ""
        assert settings.email == ""

    def test_env_vars_loaded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_gbif_settings.cache_clear()
        monkeypatch.setenv("GBIF_USERNAME", "testuser")
        monkeypatch.setenv("GBIF_PASSWORD", "testpass")
        monkeypatch.setenv("GBIF_EMAIL", "test@example.com")
        settings = GbifSettings()
        assert settings.username == "testuser"
        assert settings.password == "testpass"
        assert settings.email == "test@example.com"

    def test_get_gbif_settings_caches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_gbif_settings.cache_clear()
        monkeypatch.setenv("GBIF_USERNAME", "cached")
        s1 = get_gbif_settings()
        s2 = get_gbif_settings()
        assert s1 is s2
        get_gbif_settings.cache_clear()


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


class TestDownloadCLI:
    """Smoke tests for download CLI commands."""

    def test_download_help(self) -> None:
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "download" in result.stdout.lower()

    def test_request_help(self) -> None:
        result = runner.invoke(app, ["download", "request", "--help"])
        assert result.exit_code == 0
        assert "--taxon-keys" in result.stdout

    def test_status_help(self) -> None:
        result = runner.invoke(app, ["download", "status", "--help"])
        assert result.exit_code == 0
        assert "download-key" in result.stdout.lower() or "DOWNLOAD_KEY" in result.stdout

    def test_fetch_help(self) -> None:
        result = runner.invoke(app, ["download", "fetch", "--help"])
        assert result.exit_code == 0
        assert "download-key" in result.stdout.lower() or "DOWNLOAD_KEY" in result.stdout

    def test_request_no_taxa_exits_with_error(self) -> None:
        get_gbif_settings.cache_clear()
        result = runner.invoke(app, ["download", "request"])
        assert result.exit_code != 0

    def test_request_both_file_and_keys_errors(self, tmp_path: Path) -> None:
        get_gbif_settings.cache_clear()
        f = tmp_path / "keys.txt"
        f.write_text("123\n")
        result = runner.invoke(app, ["download", "request", str(f), "--taxon-keys", "456"])
        assert result.exit_code != 0
        assert "not both" in result.stdout.lower()

    @patch("dwca_tools.download.submit_download_request")
    def test_request_no_wait_flow(
        self, mock_submit: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        get_gbif_settings.cache_clear()
        monkeypatch.setenv("GBIF_USERNAME", "user")
        monkeypatch.setenv("GBIF_PASSWORD", "pass")
        monkeypatch.setenv("GBIF_EMAIL", "u@example.com")
        mock_submit.return_value = "0000000-240101"

        result = runner.invoke(app, ["download", "request", "--taxon-keys", "123,456", "--no-wait"])
        assert result.exit_code == 0
        assert "0000000-240101" in result.stdout
        mock_submit.assert_called_once()
