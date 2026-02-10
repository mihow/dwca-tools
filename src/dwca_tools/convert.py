"""Archive conversion utilities for dwca-tools."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table as RichTable
from sqlalchemy import MetaData, Table

from . import queries
from .db import create_engine_and_session, create_schema_from_meta, summarize_sql_tables
from .summarize import extract_name_from_term, summarize_tables
from .utils import read_config

if TYPE_CHECKING:
    from zipfile import ZipFile

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

app = typer.Typer()
console = Console()


def get_default_db_url(dwca_path: str) -> str:
    """Generate default database URL from archive path."""
    base_name = Path(dwca_path).stem
    return f"sqlite:///{base_name}.db"


def insert_data_from_zip(
    engine: Engine,
    session: Session,
    zip_ref: ZipFile,
    tables: list[tuple[str, str, list[tuple[str | None, str]]]],
    batch_size: int,
) -> None:
    """Insert data from archive files into database tables."""
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.completed]{task.completed} rows"),
        TimeElapsedColumn(),
    ) as progress:
        for table_name, file, columns in tables:
            table = Table(table_name, MetaData(), autoload_with=engine, extend_existing=True)
            task = progress.add_task(f"[cyan]Inserting data into {table_name}...")
            _schema_fields = [
                extract_name_from_term(col) for idx, col in columns if col is not None
            ]

            with zip_ref.open(file) as file_obj:
                reader = csv.reader(file_obj.read().decode("utf-8").splitlines(), delimiter="\t")
                rows = []
                row_count = 0
                # Skip header row
                _first_row = next(reader)

                for line in reader:
                    data = {
                        extract_name_from_term(col): line[int(idx)]
                        for idx, col in columns
                        if idx is not None and int(idx) < len(line)
                    }
                    rows.append(data)
                    if len(rows) >= batch_size:
                        session.execute(table.insert(), rows)
                        session.commit()
                        row_count += len(rows)
                        progress.update(task, advance=len(rows))
                        rows = []
                if rows:
                    session.execute(table.insert(), rows)
                    session.commit()
                    row_count += len(rows)
                    progress.update(task, advance=len(rows))
            progress.update(task, completed=row_count)
            progress.remove_task(task)
            rprint(f"[green]Inserted {row_count} rows into {table_name}.[/green]")


def display_query_results(session: Session) -> None:
    """Display results of common queries."""
    queries_to_run = [
        ("Count Occurrences per Taxon", queries.count_occurrences_per_taxon),
        ("Count Multimedia per Taxon", queries.count_multimedia_per_taxon),
        ("Highest Occurrences", queries.highest_occurrences),
        ("Highest Multimedia Entries", queries.highest_multimedia),
        ("Family Summary", queries.family_summary),
    ]

    for description, query_func in queries_to_run:
        result = query_func(session)
        table = RichTable(title=description)
        if result:
            first_row = result[0]
            keys = first_row._fields
            for key in keys:
                table.add_column(key)
            for row in result:
                table.add_row(*[str(getattr(row, key)) for key in keys])
        else:
            table.add_column("No data found")
        console.print(table)


def display_random_samples(session: Session) -> None:
    """Display random samples from all tables."""
    samples = queries.random_sample_from_all_tables(session)
    max_columns = 10
    for table_name, result in samples.items():
        table = RichTable(title=f"Random Sample from {table_name}")
        if result:
            first_row = result[0]
            keys = first_row._fields
            display_keys = keys[:max_columns]
            hidden_columns = len(keys) - max_columns
            for key in display_keys:
                table.add_column(key)
            if hidden_columns > 0:
                table.add_column(f"[dim]{hidden_columns} more columns hidden[/dim]")
            for row in result:
                table.add_row(*[str(getattr(row, key)) for key in display_keys])
        else:
            table.add_column("No data found")
        console.print(table)


@app.command()
def convert(
    dwca_path: str, db_url: str | None = None, batch_size: int = 1000
) -> None:
    """Convert a Darwin Core Archive to a SQL database."""
    if db_url is None:
        db_url = get_default_db_url(dwca_path)

    rprint(f"[cyan]Starting conversion of DwC-A file to database:[/cyan] {db_url}")

    _config = read_config()
    zip_ref = zipfile.ZipFile(dwca_path, "r")
    tables = summarize_tables(zip_ref, "meta.xml")

    engine, session = create_engine_and_session(db_url)

    rprint("[cyan]Creating schema...[/cyan]")
    create_schema_from_meta(engine, tables)

    rprint("[cyan]Inserting data...[/cyan]")
    insert_data_from_zip(engine, session, zip_ref, tables, batch_size)

    rprint("[cyan]Summarizing SQL tables...[/cyan]")
    summarize_sql_tables(engine, session)

    rprint("[cyan]Displaying Query Results...[/cyan]")
    display_query_results(session)

    rprint("[cyan]Displaying Random Samples...[/cyan]")
    display_random_samples(session)

    rprint("[green]Conversion completed successfully![/green]")

    rprint(f"[cyan]Database URL:[/cyan] {db_url}")


@app.command()
def sample(db_url: str) -> None:
    """Display random samples from an existing database."""
    engine, session = create_engine_and_session(db_url)
    rprint("[cyan]Displaying Random Samples...[/cyan]")
    display_random_samples(session)
    rprint("[green]Random samples displayed successfully![/green]")


if __name__ == "__main__":
    app()
