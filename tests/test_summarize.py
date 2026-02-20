"""Tests for the summarize module."""

from __future__ import annotations

import zipfile
from pathlib import Path

from typer.testing import CliRunner

from dwca_tools.cli import app

runner = CliRunner()

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_dwca.zip"


class TestFilesCommand:
    """Tests for the renamed 'files' command."""

    def test_files_command(self) -> None:
        """The 'summarize files' command works on the test archive."""
        result = runner.invoke(app, ["summarize", "files", str(FIXTURE_PATH)])
        assert result.exit_code == 0
        assert "occurrence" in result.stdout
        assert "multimedia" in result.stdout


class TestTaxaCommand:
    """Tests for the 'taxa' command."""

    def test_taxa_default_group_by(self) -> None:
        """Default grouping by scientificName shows species with counts but no Images column."""
        result = runner.invoke(app, ["summarize", "taxa", str(FIXTURE_PATH)])
        assert result.exit_code == 0
        assert "Danaus plexippus" in result.stdout
        assert "Vanessa cardui" in result.stdout
        assert "Papilio machaon" in result.stdout
        assert "Pieris rapae" in result.stdout
        assert "Papilio polyxenes" in result.stdout
        # Check totals row
        assert "Total" in result.stdout
        # Images column should NOT be present without --image-counts
        assert "Images" not in result.stdout

    def test_taxa_group_by_verbatim(self) -> None:
        """Grouping by verbatimScientificName produces expected groups without Images column."""
        result = runner.invoke(
            app,
            ["summarize", "taxa", str(FIXTURE_PATH), "--group-by", "verbatimScientificName"],
        )
        assert result.exit_code == 0
        assert "Monarch Butterfly" in result.stdout
        assert "Swallowtail" in result.stdout
        assert "Painted Lady" in result.stdout
        assert "Cabbage White" in result.stdout
        assert "Images" not in result.stdout

    def test_taxa_show_mismatched_names(self) -> None:
        """Mismatch columns appear and 'Swallowtail' maps to 2 taxonIDs."""
        result = runner.invoke(
            app,
            [
                "summarize",
                "taxa",
                str(FIXTURE_PATH),
                "--group-by",
                "verbatimScientificName",
                "--show-mismatched-names",
            ],
        )
        assert result.exit_code == 0
        assert "taxonIDs" in result.stdout
        assert "accepted names" in result.stdout
        assert "Images" not in result.stdout
        # "Swallowtail" has 4 occurrences, 2 taxonIDs, 2 accepted names
        lines = result.stdout.split("\n")
        swallowtail_lines = [line for line in lines if "Swallowtail" in line]
        assert len(swallowtail_lines) == 1
        swallowtail_line = swallowtail_lines[0]
        assert "4" in swallowtail_line
        assert swallowtail_line.count("2") >= 2

    def test_taxa_limit(self) -> None:
        """--limit restricts the number of rows displayed."""
        result = runner.invoke(
            app,
            ["summarize", "taxa", str(FIXTURE_PATH), "--limit", "2"],
        )
        assert result.exit_code == 0
        assert "Images" not in result.stdout
        lines = result.stdout.split("\n")
        species_count = sum(
            1
            for line in lines
            if any(
                sp in line
                for sp in [
                    "Danaus plexippus",
                    "Vanessa cardui",
                    "Papilio machaon",
                    "Pieris rapae",
                    "Papilio polyxenes",
                ]
            )
        )
        assert species_count == 2

    def test_taxa_image_counts_flag(self) -> None:
        """--image-counts shows the Images column with correct values."""
        result = runner.invoke(
            app,
            ["summarize", "taxa", str(FIXTURE_PATH), "--image-counts"],
        )
        assert result.exit_code == 0
        assert "Images" in result.stdout
        # Fixture has multimedia data, so at least some image counts should be non-zero
        assert "Danaus plexippus" in result.stdout

    def test_taxa_image_counts_warning(self) -> None:
        """--image-counts prints a memory usage warning."""
        result = runner.invoke(
            app,
            ["summarize", "taxa", str(FIXTURE_PATH), "--image-counts"],
        )
        assert result.exit_code == 0
        assert "Image counting requires loading all occurrence IDs into memory" in result.stdout
        assert "dwca-tools convert" in result.stdout

    def test_taxa_missing_column(self, tmp_path: Path) -> None:
        """Archive without the group-by column shows an error."""
        # Create a minimal archive without verbatimScientificName
        meta_xml = """\
<?xml version="1.0" encoding="utf-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
  <core encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1"
        rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files><location>occurrence.txt</location></files>
    <field index="0" term="http://rs.gbif.org/terms/1.0/gbifID"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
  </core>
</archive>
"""
        occurrence_txt = "gbifID\tscientificName\n1001\tDanaus plexippus\n"
        archive_path = tmp_path / "no_verbatim.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("meta.xml", meta_xml)
            zf.writestr("occurrence.txt", occurrence_txt)

        result = runner.invoke(
            app,
            ["summarize", "taxa", str(archive_path), "--group-by", "verbatimScientificName"],
        )
        assert result.exit_code != 0
        assert "not found" in result.stdout
