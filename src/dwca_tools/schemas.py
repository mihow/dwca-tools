"""Data structures for archive metadata and taxa results."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class ColumnDefinition:
    """A single column from a DwC-A table definition."""

    index: str | None
    name: str


@dataclasses.dataclass(frozen=True, slots=True)
class TableDefinition:
    """A table discovered in meta.xml with its filename and columns."""

    name: str
    filename: str
    columns: list[ColumnDefinition]

    @property
    def column_names(self) -> list[str]:
        return [col.name for col in self.columns]


@dataclasses.dataclass(frozen=True, slots=True)
class TaxaResult:
    """Aggregated taxa summary for a single group."""

    name: str
    occurrence_count: int
    image_count: int
    n_taxon_ids: int
    n_sci_names: int
