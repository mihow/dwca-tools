"""Archive summarization utilities for dwca-tools."""

from __future__ import annotations

import csv
import dataclasses
import enum
import io
import locale
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .schemas import ColumnDefinition, TableDefinition
from .utils import human_readable_number, human_readable_size, read_config

if TYPE_CHECKING:
    from collections.abc import Generator
    from zipfile import ZipFile

app = typer.Typer(no_args_is_help=True)

console = Console()

locale.setlocale(locale.LC_ALL, "")

DEFAULT_AVERAGE_LINE_LENGTH = 300


def estimate_line_count(file_size: int, average_line_length: int) -> int:
    """Estimate number of lines in a file based on average line length."""
    return file_size // average_line_length


def summarize_zip(zip_ref: ZipFile) -> None:
    """Print summary of zip file contents."""
    file_info_list = zip_ref.infolist()
    root_files: list[tuple[str, int]] = []
    dir_files: dict[str, list[tuple[str, int]]] = {}

    for file_info in file_info_list:
        filepath = file_info.filename
        if "/" not in filepath:
            root_files.append((filepath, file_info.file_size))
        else:
            directory = filepath.split("/")[0]
            if directory not in dir_files:
                dir_files[directory] = []
            dir_files[directory].append((filepath, file_info.file_size))

    table = Table(title="Summary of the Zip File")
    table.add_column("Path", justify="left", style="cyan")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Estimated Lines", justify="right", style="yellow")

    for filepath, size in root_files:
        table.add_row(
            filepath,
            human_readable_size(size),
        )

    for directory, files in dir_files.items():
        if len(files) > 5:
            for filepath, size in files[:5]:
                table.add_row(
                    filepath,
                    human_readable_size(size),
                )
            table.add_row(f"{directory}/", f"{len(files)} files (sample shown above)", "-")
        else:
            for filepath, size in files:
                table.add_row(
                    filepath,
                    human_readable_size(size),
                )

    console.print(table)
    rprint(
        "[cyan]Total files:[/cyan]"
        f" {human_readable_number(len(root_files) + sum(len(files) for files in dir_files.values()))}"
    )
    rprint(f"[cyan]Total directories:[/cyan] {human_readable_number(len(dir_files))}")


def extract_name_from_term(term: str) -> str:
    """Extract the last component of a term URI."""
    return term.rsplit("/", maxsplit=1)[-1]


def extract_table_name_from_rowtype(rowtype: str) -> str:
    """Extract table name from rowtype URI."""
    return rowtype.rsplit("/", maxsplit=1)[-1].lower()


def extract_table_name_from_filename(filename: str) -> str:
    """Extract table name from filename."""
    return urlparse(filename).path.split("/")[-1].split(".")[0].lower()


def summarize_tables(
    zip_ref: ZipFile, meta_filename: str = "meta.xml"
) -> list[TableDefinition]:
    """Parse meta.xml and return table definitions."""
    rprint("[cyan]Parsing meta.xml to get table definitions.[/cyan]")
    with zip_ref.open(meta_filename) as meta_file:
        tree = ET.parse(meta_file)
    root = tree.getroot()

    namespace = {"dwc": "http://rs.tdwg.org/dwc/text/"}

    tables: list[TableDefinition] = []
    core = root.find("dwc:core", namespace)
    if core is not None:
        filename_el = core.find("dwc:files/dwc:location", namespace)
        filename = filename_el.text if filename_el is not None and filename_el.text else "Unknown"
        table_name = extract_table_name_from_filename(filename)

        columns: list[ColumnDefinition] = []
        for field in core.findall("dwc:field", namespace):
            index = field.get("index")
            term = field.get("term")
            if term:
                column_name = extract_name_from_term(term)
                columns.append(ColumnDefinition(index=index, name=column_name))
        tables.append(TableDefinition(name=table_name, filename=filename, columns=columns))

    for extension in root.findall("dwc:extension", namespace):
        filename_el = extension.find("dwc:files/dwc:location", namespace)
        filename = filename_el.text if filename_el is not None and filename_el.text else "Unknown"
        table_name = extract_table_name_from_filename(filename)
        columns = []
        for field in extension.findall("dwc:field", namespace):
            index = field.get("index")
            term = field.get("term")
            if term:
                column_name = extract_name_from_term(term)
                columns.append(ColumnDefinition(index=index, name=column_name))
        tables.append(TableDefinition(name=table_name, filename=filename, columns=columns))

    if not tables:
        rprint("[yellow]No tables found in meta.xml.[/yellow]")
    else:
        rprint("[cyan]Finished parsing meta.xml.[/cyan]")
        rprint("[cyan]Summary of tables and columns discovered:[/cyan]")
        table = Table(title="Tables and Columns")
        table.add_column("Table", justify="left", style="cyan")
        table.add_column("File", justify="left", style="magenta")
        table.add_column("Columns", justify="left", style="green")
        for table_def in tables:
            column_info = ", ".join(table_def.column_names)
            table.add_row(table_def.name, table_def.filename, column_info)
        console.print(table)

    return tables


@app.command("files")
def files(dwca_path: str) -> None:
    """Summarize the files and table schemas in a Darwin Core Archive."""
    _config = read_config()
    dwca_file = Path(dwca_path)
    dwca_size = dwca_file.stat().st_size
    rprint(
        "[cyan]Starting processing of DwC-A file:[/cyan]"
        f" {dwca_path} ({human_readable_size(dwca_size)})"
    )

    with zipfile.ZipFile(dwca_path, "r") as zip_ref:
        summarize_zip(zip_ref)
        summarize_tables(zip_ref)

    rprint("[cyan]Processing completed.[/cyan]")


# -- Taxa summarization --


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
        # Map column name → index for the columns we care about
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


class GroupByColumn(enum.StrEnum):
    """Columns available for taxa grouping."""

    scientificName = "scientificName"
    verbatimScientificName = "verbatimScientificName"


def _aggregate_occurrences(
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
    if species_only:
        needed_cols.append("taxonRank")

    groups: dict[str, _TaxaGroup] = defaultdict(_TaxaGroup)
    for row in _read_table_as_dicts(zip_ref, occ_filename, needed_cols):
        if species_only and row.get("taxonRank", "").upper() != "SPECIES":
            continue
        key = row.get(group_col, "")
        entry = groups[key]
        entry.count += 1
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
) -> list[tuple[str, int, int, int, int]]:
    """Calculate per-group totals and sort by occurrence count descending."""
    results: list[tuple[str, int, int, int, int]] = []
    for name, entry in groups.items():
        img_count = sum(image_counts.get(gid, 0) for gid in entry.gbif_ids)
        results.append((name, entry.count, img_count, len(entry.taxon_ids), len(entry.sci_names)))
    results.sort(key=lambda r: (-r[1], r[0]))
    return results


def _display_taxa_table(
    results: list[tuple[str, int, int, int, int]],
    show_mismatched_names: bool,
    show_images: bool = False,
    total_groups: int | None = None,
) -> None:
    """Render the taxa summary as a Rich table."""
    table = Table(title="Taxa Summary")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Occurrences", justify="right", style="green")
    if show_images:
        table.add_column("Images", justify="right", style="yellow")
    if show_mismatched_names:
        table.add_column("# taxonIDs", justify="right", style="magenta")
        table.add_column("# accepted names", justify="right", style="magenta")

    total_occ = 0
    total_img = 0
    for i, (name, occ_count, img_count, n_taxon_ids, n_sci_names) in enumerate(results, 1):
        row_values = [str(i), name, str(occ_count)]
        if show_images:
            row_values.append(str(img_count))
        if show_mismatched_names:
            row_values.extend([str(n_taxon_ids), str(n_sci_names)])
        table.add_row(*row_values)
        total_occ += occ_count
        total_img += img_count

    total_row: list[str] = ["", "[bold]Total[/bold]", f"[bold]{total_occ}[/bold]"]
    if show_images:
        total_row.append(f"[bold]{total_img}[/bold]")
    if show_mismatched_names:
        total_row.extend(["", ""])
    table.add_row(*total_row)

    console.print(table)
    total = total_groups if total_groups is not None else len(results)
    shown = len(results)
    if total != shown:
        rprint(f"[cyan]Unique groups:[/cyan] {shown} shown, {total} total")
    else:
        rprint(f"[cyan]Unique groups:[/cyan] {total}")


@app.command("taxa")
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
) -> None:
    """Summarize taxa from a Darwin Core Archive, showing occurrence and image counts."""
    with zipfile.ZipFile(dwca_path, "r") as zip_ref:
        tables = summarize_tables(zip_ref)

        occ_table = next((t for t in tables if t.name == "occurrence"), None)
        mm_table = next((t for t in tables if t.name == "multimedia"), None)

        if occ_table is None:
            rprint("[red]No occurrence table found in archive.[/red]")
            raise typer.Exit(code=1)

        occ_columns = occ_table.column_names
        group_col = group_by.value
        if group_col not in occ_columns:
            rprint(f"[red]Column '{group_col}' not found in occurrence table.[/red]")
            rprint(f"[yellow]Available columns: {', '.join(occ_columns)}[/yellow]")
            raise typer.Exit(code=1)

        if species_only and "taxonRank" not in occ_columns:
            rprint(
                "[red]Column 'taxonRank' not found in occurrence table — cannot use --species-only.[/red]"
            )
            raise typer.Exit(code=1)

        if image_counts_flag and mm_table is not None:
            rprint(
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
    _display_taxa_table(
        results, show_mismatched_names, show_images=image_counts_flag, total_groups=total_groups
    )


if __name__ == "__main__":
    app()
