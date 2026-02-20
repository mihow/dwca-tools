#!/usr/bin/env python3
"""Generate the test DwC-A fixture at tests/fixtures/test_dwca.zip."""

import zipfile
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "test_dwca.zip"

META_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
  <core encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files>
      <location>occurrence.txt</location>
    </files>
    <field index="0" term="http://rs.gbif.org/terms/1.0/gbifID"/>
    <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/decimalLatitude"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/decimalLongitude"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/eventDate"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/taxonID"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/verbatimScientificName"/>
  </core>
  <extension encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Multimedia">
    <files>
      <location>multimedia.txt</location>
    </files>
    <field index="0" term="http://rs.gbif.org/terms/1.0/gbifID"/>
    <field index="1" term="http://purl.org/dc/terms/identifier"/>
    <field index="2" term="http://purl.org/dc/terms/references"/>
    <field index="3" term="http://purl.org/dc/terms/title"/>
    <field index="4" term="http://purl.org/dc/terms/created"/>
  </extension>
</archive>
"""

# 20 occurrence rows, 4 species + 1 extra (Papilio polyxenes) to create a
# verbatimScientificName mismatch where "Swallowtail" maps to 2 taxonIDs.
OCCURRENCE_ROWS = [
    # gbifID, scientificName, lat, lon, date, kingdom, family, taxonID, verbatimScientificName
    ("1001", "Danaus plexippus", "45.1", "-72.9", "2024-06-01", "Animalia", "Nymphalidae", "1", "Monarch Butterfly"),
    ("1002", "Vanessa cardui", "45.2", "-72.8", "2024-06-02", "Animalia", "Nymphalidae", "2", "Vanessa cardui"),
    ("1003", "Papilio machaon", "45.3", "-72.7", "2024-06-03", "Animalia", "Papilionidae", "3", "Swallowtail"),
    ("1004", "Pieris rapae", "45.4", "-72.6", "2024-06-04", "Animalia", "Pieridae", "4", "Cabbage White"),
    ("1005", "Danaus plexippus", "45.5", "-72.5", "2024-06-05", "Animalia", "Nymphalidae", "1", "Monarch Butterfly"),
    ("1006", "Vanessa cardui", "45.6", "-72.4", "2024-06-06", "Animalia", "Nymphalidae", "2", "Painted Lady"),
    ("1007", "Papilio machaon", "45.7", "-72.3", "2024-06-07", "Animalia", "Papilionidae", "3", "Swallowtail"),
    ("1008", "Pieris rapae", "45.8", "-72.2", "2024-06-08", "Animalia", "Pieridae", "4", "Cabbage White"),
    ("1009", "Danaus plexippus", "45.9", "-72.1", "2024-06-09", "Animalia", "Nymphalidae", "1", "Danaus plexippus"),
    ("1010", "Vanessa cardui", "46.0", "-72.0", "2024-06-10", "Animalia", "Nymphalidae", "2", "Painted Lady"),
    ("1011", "Papilio machaon", "46.1", "-71.9", "2024-06-11", "Animalia", "Papilionidae", "3", "Papilio machaon"),
    ("1012", "Pieris rapae", "46.2", "-71.8", "2024-06-12", "Animalia", "Pieridae", "4", "Pieris rapae"),
    ("1013", "Danaus plexippus", "46.3", "-71.7", "2024-06-13", "Animalia", "Nymphalidae", "1", "Monarch Butterfly"),
    ("1014", "Vanessa cardui", "46.4", "-71.6", "2024-06-14", "Animalia", "Nymphalidae", "2", "Vanessa cardui"),
    ("1015", "Papilio machaon", "46.5", "-71.5", "2024-06-15", "Animalia", "Papilionidae", "3", "Swallowtail"),
    ("1016", "Pieris rapae", "46.6", "-71.4", "2024-06-16", "Animalia", "Pieridae", "4", "Cabbage White"),
    ("1017", "Danaus plexippus", "46.7", "-71.3", "2024-06-17", "Animalia", "Nymphalidae", "1", "Monarch"),
    ("1018", "Vanessa cardui", "46.8", "-71.2", "2024-06-18", "Animalia", "Nymphalidae", "2", "Painted Lady"),
    ("1019", "Papilio polyxenes", "46.9", "-71.1", "2024-06-19", "Animalia", "Papilionidae", "5", "Swallowtail"),
    ("1020", "Pieris rapae", "47.0", "-71.0", "2024-06-20", "Animalia", "Pieridae", "4", "Pieris rapae"),
]

OCCURRENCE_HEADER = "gbifID\tscientificName\tdecimalLatitude\tdecimalLongitude\teventDate\tkingdom\tfamily\ttaxonID\tverbatimScientificName"

# 10 multimedia rows (gbifIDs 1001-1010)
MULTIMEDIA_ROWS = [
    (str(gid), f"https://example.com/img/{gid}.jpg", f"https://example.com/ref/{gid}", f"Photo of specimen {gid}", f"2024-06-{i:02d}")
    for i, gid in enumerate(range(1001, 1011), start=1)
]

MULTIMEDIA_HEADER = "gbifID\tidentifier\treferences\ttitle\tcreated"


def main() -> None:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)

    occurrence_txt = OCCURRENCE_HEADER + "\n"
    for row in OCCURRENCE_ROWS:
        occurrence_txt += "\t".join(row) + "\n"

    multimedia_txt = MULTIMEDIA_HEADER + "\n"
    for row in MULTIMEDIA_ROWS:
        multimedia_txt += "\t".join(row) + "\n"

    with zipfile.ZipFile(FIXTURE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("meta.xml", META_XML)
        zf.writestr("occurrence.txt", occurrence_txt)
        zf.writestr("multimedia.txt", multimedia_txt)

    print(f"Generated {FIXTURE_PATH}")
    print(f"  occurrence rows: {len(OCCURRENCE_ROWS)}")
    print(f"  multimedia rows: {len(MULTIMEDIA_ROWS)}")


if __name__ == "__main__":
    main()
