"""Taxa summarization from Darwin Core Archives."""

from __future__ import annotations

import csv
import dataclasses
import enum
import io
import json
import sys
import zipfile
from collections import defaultdict
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from . import summarize as _summarize_mod
from .schemas import TaxaResult
from .summarize import summarize_tables

if TYPE_CHECKING:
    from collections.abc import Generator
    from zipfile import ZipFile

console = Console()


def _read_table_as_dicts(
    zip_ref: ZipFile, filename: str, columns: list[str]
) -> Generator[dict[str, str], None, None]:
    """Yield rows as dicts from a tab-delimited file inside a zip.

    Only includes keys listed in *columns* that exist in the file header.
    """
    with zip_ref.open(filename, "r") as raw:
        text_file = io.TextIOWrapper(raw, encoding="utf-8")
        reader = csv.reader(text_file, delimiter="\t")
        header = next(reader)
        # Map column name -> index for the columns we care about
        col_indices = {col: header.index(col) for col in columns if col in header}
        for row in reader:
            yield {col: row[idx] for col, idx in col_indices.items() if idx < len(row)}


@dataclasses.dataclass
class _TaxaGroup:
    """Accumulator for per-group taxa stats."""

    gbif_ids: set[str] = dataclasses.field(default_factory=set)
    count: int = 0
    taxon_ids: set[str] = dataclasses.field(default_factory=set)
    sci_names: set[str] = dataclasses.field(default_factory=set)
    taxon_ranks: set[str] = dataclasses.field(default_factory=set)


class GroupByColumn(enum.StrEnum):
    """Columns available for taxa grouping."""

    scientificName = "scientificName"
    verbatimScientificName = "verbatimScientificName"


class OutputFormat(enum.StrEnum):
    """Output format for taxa summary."""

    table = "table"
    csv = "csv"
    json = "json"


def _aggregate_occurrences(  # noqa: PLR0912
    zip_ref: ZipFile,
    occ_filename: str,
    group_col: str,
    show_mismatched_names: bool,
    species_only: bool = False,
    collect_gbif_ids: bool = False,
) -> dict[str, _TaxaGroup]:
    """Stream occurrence CSV and build per-group aggregation.

    When *collect_gbif_ids* is False (the default), gbifID values are not
    stored, keeping memory usage proportional to the number of unique groups
    rather than the number of occurrences.
    """
    needed_cols = [group_col]
    if collect_gbif_ids:
        needed_cols.append("gbifID")
    if show_mismatched_names:
        for col in ("taxonID", "scientificName"):
            if col not in needed_cols:
                needed_cols.append(col)
    if "taxonRank" not in needed_cols:
        needed_cols.append("taxonRank")

    groups: dict[str, _TaxaGroup] = defaultdict(_TaxaGroup)
    for row in _read_table_as_dicts(zip_ref, occ_filename, needed_cols):
        if species_only and row.get("taxonRank", "").upper() != "SPECIES":
            continue
        key = row.get(group_col, "")
        entry = groups[key]
        entry.count += 1
        rank = row.get("taxonRank", "")
        if rank:
            entry.taxon_ranks.add(rank)
        if collect_gbif_ids:
            gbif_id = row.get("gbifID", "")
            if gbif_id:
                entry.gbif_ids.add(gbif_id)
        if show_mismatched_names:
            tid = row.get("taxonID", "")
            if tid:
                entry.taxon_ids.add(tid)
            sn = row.get("scientificName", "")
            if sn:
                entry.sci_names.add(sn)
    return groups


def _aggregate_images(zip_ref: ZipFile, mm_filename: str) -> dict[str, int]:
    """Stream multimedia CSV and count images per gbifID."""
    counts: dict[str, int] = defaultdict(int)
    for row in _read_table_as_dicts(zip_ref, mm_filename, ["gbifID"]):
        gbif_id = row.get("gbifID", "")
        if gbif_id:
            counts[gbif_id] += 1
    return counts


def _build_taxa_results(
    groups: dict[str, _TaxaGroup],
    image_counts: dict[str, int],
) -> list[TaxaResult]:
    """Calculate per-group totals and sort by occurrence count descending."""
    results: list[TaxaResult] = []
    for name, entry in groups.items():
        img_count = sum(image_counts.get(gid, 0) for gid in entry.gbif_ids)
        ranks = " | ".join(sorted(entry.taxon_ranks)) if entry.taxon_ranks else ""
        results.append(
            TaxaResult(
                name=name,
                occurrence_count=entry.count,
                image_count=img_count,
                n_taxon_ids=len(entry.taxon_ids),
                n_sci_names=len(entry.sci_names),
                taxon_ranks=ranks,
            )
        )
    results.sort(key=lambda r: (-r.occurrence_count, r.name))
    return results


def _display_taxa_table(
    results: list[TaxaResult],
    show_mismatched_names: bool,
    show_images: bool = False,
    total_groups: int | None = None,
) -> None:
    """Render the taxa summary as a Rich table."""
    table = Table(title="Taxa Summary")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Rank", style="blue")
    table.add_column("Occurrences", justify="right", style="green")
    if show_images:
        table.add_column("Images", justify="right", style="yellow")
    if show_mismatched_names:
        table.add_column("# taxonIDs", justify="right", style="magenta")
        table.add_column("# accepted names", justify="right", style="magenta")

    total_occ = 0
    total_img = 0
    for i, result in enumerate(results, 1):
        row_values = [str(i), result.name, result.taxon_ranks, str(result.occurrence_count)]
        if show_images:
            row_values.append(str(result.image_count))
        if show_mismatched_names:
            row_values.extend([str(result.n_taxon_ids), str(result.n_sci_names)])
        table.add_row(*row_values)
        total_occ += result.occurrence_count
        total_img += result.image_count

    total_row: list[str] = ["", "[bold]Total[/bold]", "", f"[bold]{total_occ}[/bold]"]
    if show_images:
        total_row.append(f"[bold]{total_img}[/bold]")
    if show_mismatched_names:
        total_row.extend(["", ""])
    table.add_row(*total_row)

    console.print(table)
    total = total_groups if total_groups is not None else len(results)
    shown = len(results)
    if total != shown:
        console.print(f"[cyan]Unique groups:[/cyan] {shown} shown, {total} total")
    else:
        console.print(f"[cyan]Unique groups:[/cyan] {total}")


def _result_to_dict(
    result: TaxaResult,
    show_mismatched_names: bool,
    show_images: bool,
) -> dict[str, str | int]:
    """Convert a TaxaResult to a flat dict for serialization."""
    d: dict[str, str | int] = {
        "name": result.name,
        "rank": result.taxon_ranks,
        "occurrences": result.occurrence_count,
    }
    if show_images:
        d["images"] = result.image_count
    if show_mismatched_names:
        d["taxon_ids"] = result.n_taxon_ids
        d["accepted_names"] = result.n_sci_names
    return d


def _output_csv(
    results: list[TaxaResult],
    show_mismatched_names: bool,
    show_images: bool,
) -> None:
    """Write taxa results as CSV to stdout."""
    if not results:
        return
    rows = [_result_to_dict(r, show_mismatched_names, show_images) for r in results]
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def _output_json(
    results: list[TaxaResult],
    show_mismatched_names: bool,
    show_images: bool,
) -> None:
    """Write taxa results as JSON to stdout."""
    rows = [_result_to_dict(r, show_mismatched_names, show_images) for r in results]
    json.dump(rows, sys.stdout, indent=2)
    sys.stdout.write("\n")


def taxa(
    dwca_path: str,
    group_by: GroupByColumn = typer.Option(
        GroupByColumn.scientificName,
        "--group-by",
        "-g",
        help="Column to group taxa by.",
    ),
    show_mismatched_names: bool = typer.Option(
        False,
        "--show-mismatched-names",
        help="Show columns for # distinct taxonIDs and # distinct scientificNames per group.",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit the number of rows displayed.",
    ),
    species_only: bool = typer.Option(
        False,
        "--species-only",
        help="Filter to rows where taxonRank=SPECIES.",
    ),
    image_counts_flag: bool = typer.Option(
        False,
        "--image-counts",
        help="Include image counts per group (requires holding all gbifIDs in memory).",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format: table (Rich), csv, or json.",
    ),
) -> None:
    """Summarize taxa from a Darwin Core Archive, showing occurrence and image counts."""
    # When outputting data formats, redirect Rich status messages to stderr
    # so stdout stays clean for piping.
    if output_format != OutputFormat.table:
        _summarize_mod.console = Console(stderr=True)

    with zipfile.ZipFile(dwca_path, "r") as zip_ref:
        tables = summarize_tables(zip_ref)

        occ_table = next((t for t in tables if t.name == "occurrence"), None)
        mm_table = next((t for t in tables if t.name == "multimedia"), None)

        if occ_table is None:
            console.print("[red]No occurrence table found in archive.[/red]")
            raise typer.Exit(code=1)

        occ_columns = occ_table.column_names
        group_col = group_by.value
        if group_col not in occ_columns:
            console.print(f"[red]Column '{group_col}' not found in occurrence table.[/red]")
            console.print(f"[yellow]Available columns: {', '.join(occ_columns)}[/yellow]")
            raise typer.Exit(code=1)

        if species_only and "taxonRank" not in occ_columns:
            console.print(
                "[red]Column 'taxonRank' not found in occurrence table"
                " — cannot use --species-only.[/red]"
            )
            raise typer.Exit(code=1)

        if image_counts_flag and mm_table is not None:
            console.print(
                "\n[yellow]Note:[/yellow] Image counting requires loading all occurrence IDs"
                " into memory. For large archives\n(>1M occurrences), consider importing to a"
                " database instead:\n"
                "\n    dwca-tools convert archive.zip --db-url sqlite:///data.db"
                "\n    dwca-tools aggregate populate-taxa-table sqlite:///data.db\n"
            )

        groups = _aggregate_occurrences(
            zip_ref,
            occ_table.filename,
            group_col,
            show_mismatched_names,
            species_only,
            collect_gbif_ids=image_counts_flag,
        )

        image_counts: dict[str, int] = {}
        if image_counts_flag and mm_table is not None:
            image_counts = _aggregate_images(zip_ref, mm_table.filename)

    results = _build_taxa_results(groups, image_counts)
    total_groups = len(results)
    if limit is not None:
        results = results[:limit]

    if output_format == OutputFormat.csv:
        _output_csv(results, show_mismatched_names, show_images=image_counts_flag)
    elif output_format == OutputFormat.json:
        _output_json(results, show_mismatched_names, show_images=image_counts_flag)
    else:
        _display_taxa_table(
            results, show_mismatched_names, show_images=image_counts_flag, total_groups=total_groups
        )
