"""Archive summarization utilities for dwca-tools."""

from __future__ import annotations

import locale
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .schemas import ColumnDefinition, TableDefinition
from .utils import human_readable_number, human_readable_size

if TYPE_CHECKING:
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


# Register the taxa command from the extracted module
from .taxa import taxa as _taxa_command  # noqa: E402

app.command("taxa")(_taxa_command)


if __name__ == "__main__":
    app()
