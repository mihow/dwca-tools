"""Archive conversion utilities for dwca-tools."""

from __future__ import annotations

import csv
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table as RichTable
from sqlalchemy import MetaData, Table, text

from . import queries
from .db import (
    create_engine_and_session,
    create_schema_from_meta,
    get_table_column_names,
    summarize_sql_tables,
)
from .schemas import TableDefinition
from .settings import get_convert_settings
from .summarize import summarize_tables
from .utils import human_readable_number

if TYPE_CHECKING:
    from collections.abc import Generator
    from concurrent.futures import Future
    from zipfile import ZipFile

    from rich.progress import TaskID
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

app = typer.Typer(no_args_is_help=True)
console = Console()

csv.field_size_limit(sys.maxsize)


# -- Chunked reading --


def read_chunks(
    zip_ref: ZipFile, filename: str, chunk_size: int
) -> Generator[tuple[list[str], list[list[str]]], None, None]:
    """Yield (headers, chunk) tuples from a tab-delimited file inside a zip."""
    with zip_ref.open(filename, "r") as f, TextIOWrapper(f, encoding="utf-8") as text_file:
        reader = csv.reader(text_file, delimiter="\t")
        headers = next(reader)
        chunk: list[list[str]] = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield headers, chunk
                chunk = []
        if chunk:
            yield headers, chunk


def filter_columns(headers: list[str], columns_of_interest: list[str] | None) -> list[str]:
    """Return intersection of headers with desired columns, preserving header order."""
    if columns_of_interest is not None:
        return [col for col in headers if col in columns_of_interest]
    return headers


# -- Row estimation --


def _count_newlines(file_obj: object, task: TaskID, progress: Progress) -> int:
    """Count newlines in a binary file object using buffered reads."""

    def _make_gen(reader: object) -> Generator[bytes, None, None]:
        while True:
            b = reader(2**16)  # type: ignore[operator]
            if not b:
                break
            yield b

    total = 0
    for buf in _make_gen(file_obj.read):  # type: ignore[union-attr]
        n = buf.count(b"\n")
        total += n
        progress.update(task, advance=n)
    return total


def estimate_row_count(zip_ref: ZipFile, filename: str, progress: Progress, task: TaskID) -> int:
    """Estimate rows by counting newlines in the file."""
    with zip_ref.open(filename, "r") as f:
        return _count_newlines(f, task, progress)


def estimate_and_display_row_counts(
    zip_ref: ZipFile,
    tables: list[TableDefinition],
    num_threads: int,
) -> dict[str, int]:
    """Count rows for each table in parallel and display results."""
    table_row_counts: dict[str, int] = {}
    with (
        Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.completed]{task.completed} rows"),
            TimeElapsedColumn(),
        ) as progress,
        ThreadPoolExecutor(max_workers=num_threads) as executor,
    ):
        future_to_table: dict[Future[int], tuple[str, TaskID]] = {}
        for table_def in tables:
            task = progress.add_task(
                f"[cyan]Counting rows in {table_def.name}...", total=None
            )
            future = executor.submit(
                estimate_row_count, zip_ref, table_def.filename, progress, task
            )
            future_to_table[future] = (table_def.name, task)

        for future in as_completed(future_to_table):
            table_name, task = future_to_table[future]
            row_count = future.result()
            table_row_counts[table_name] = row_count
            rprint(
                f"[green]Estimated rows for {table_name}:"
                f" {human_readable_number(row_count)}[/green]"
            )
            progress.remove_task(task)
    return table_row_counts


# -- PostgreSQL fast path: COPY --


def _pg_copy_chunk(
    engine: Engine,
    table_name: str,
    headers: list[str],
    chunk: list[list[str]],
    filtered_columns: list[str],
) -> None:
    """Copy a chunk into PostgreSQL using COPY FROM STDIN."""
    col_indices = [headers.index(col) for col in filtered_columns]
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(filtered_columns)
    for row in chunk:
        writer.writerow(row[i] for i in col_indices)
    buffer.seek(0)

    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()
        col_list = ", ".join(f'"{col}"' for col in filtered_columns)
        cursor.copy_expert(  # type: ignore[attr-defined]
            f"COPY {table_name} ({col_list}) FROM STDIN"
            " WITH (FORMAT CSV, DELIMITER '\t', HEADER TRUE)",
            buffer,
        )
        conn.commit()
    finally:
        conn.close()


def _pg_insert_table(
    engine: Engine,
    zip_ref: ZipFile,
    table_name: str,
    filename: str,
    columns: list[str] | None,
    chunk_size: int,
    num_threads: int,
    total_rows: int,
) -> None:
    """Insert data into PostgreSQL using threaded COPY."""
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.completed]{task.completed} rows"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(f"[cyan]Inserting data into {table_name}...", total=total_rows)
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures: dict[Future[None], int] = {}
            for headers, chunk in read_chunks(zip_ref, filename, chunk_size):
                filtered_columns = filter_columns(headers, columns)
                chunk_len = len(chunk)
                future = executor.submit(
                    _pg_copy_chunk, engine, table_name, headers, chunk, filtered_columns
                )
                futures[future] = chunk_len
            for future in as_completed(futures):
                future.result()
                progress.update(task, advance=futures[future])


# -- SQLite path: batched SQLAlchemy insert --


def _sqlite_insert_table(
    engine: Engine,
    session: Session,
    zip_ref: ZipFile,
    table_name: str,
    filename: str,
    columns: list[str] | None,
    chunk_size: int,
    total_rows: int,
) -> None:
    """Insert data into SQLite using batched SQLAlchemy inserts."""
    table = Table(table_name, MetaData(), autoload_with=engine, extend_existing=True)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.completed]{task.completed} rows"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(f"[cyan]Inserting data into {table_name}...", total=total_rows)
        for headers, chunk in read_chunks(zip_ref, filename, chunk_size):
            filtered_columns = filter_columns(headers, columns)
            col_indices = [headers.index(col) for col in filtered_columns]
            rows = [
                {col: row[idx] for col, idx in zip(filtered_columns, col_indices, strict=True)}
                for row in chunk
            ]
            session.execute(table.insert(), rows)
            session.commit()
            progress.update(task, advance=len(chunk))


# -- Index creation --


def create_indexes(engine: Engine, table_name: str, indexes: list[str]) -> None:
    """Create indexes on specified columns, skipping columns not in schema."""
    existing_columns_lower = {c.lower() for c in get_table_column_names(engine, table_name)}
    with engine.connect() as conn:
        for col in indexes:
            if col.lower() not in existing_columns_lower:
                continue
            conn.execute(
                text(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{col} ON {table_name} ("{col}")')
            )
            conn.commit()


# -- Data insertion dispatcher --


def _is_postgres(engine: Engine) -> bool:
    """Check if engine is connected to PostgreSQL."""
    return engine.dialect.name == "postgresql"


def insert_data(
    engine: Engine,
    session: Session,
    zip_ref: ZipFile,
    tables: list[TableDefinition],
    table_row_counts: dict[str, int],
    chunk_size: int,
    num_threads: int,
) -> None:
    """Insert data from archive into database, choosing PG COPY or SQLite fallback."""
    settings = get_convert_settings()
    use_pg = _is_postgres(engine)

    if use_pg:
        with engine.connect() as conn:
            conn.execute(text("SET session_replication_role = 'replica'"))
            conn.commit()

    for table_def in tables:
        row_count = table_row_counts[table_def.name]
        rprint(
            f"[cyan]Processing table: {table_def.name}"
            f" with {human_readable_number(row_count)} rows[/cyan]"
        )

        # Intersect desired columns with actual schema columns (case-insensitive
        # because PostgreSQL folds unquoted identifiers to lowercase)
        schema_columns_lower = {c.lower() for c in get_table_column_names(engine, table_def.name)}
        columns_of_interest = settings.columns_of_interest.get(table_def.name)
        if columns_of_interest is not None:
            columns_of_interest = [
                c for c in columns_of_interest if c.lower() in schema_columns_lower
            ]

        if use_pg:
            _pg_insert_table(
                engine,
                zip_ref,
                table_def.name,
                table_def.filename,
                columns_of_interest,
                chunk_size,
                num_threads,
                row_count,
            )
        else:
            _sqlite_insert_table(
                engine,
                session,
                zip_ref,
                table_def.name,
                table_def.filename,
                columns_of_interest,
                chunk_size,
                row_count,
            )

        table_indexes = settings.indexes.get(table_def.name, [])
        if table_indexes:
            create_indexes(engine, table_def.name, table_indexes)

        rprint(
            f"[green]Inserted {human_readable_number(row_count)} rows"
            f" into {table_def.name}.[/green]"
        )

    if use_pg:
        with engine.connect() as conn:
            conn.execute(text("SET session_replication_role = 'origin'"))
            conn.commit()


# -- Display helpers (unchanged) --


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


# -- CLI commands --


@app.command()
def convert(
    dwca_path: str,
    db_url: str | None = None,
    chunk_size: int | None = None,
    num_threads: int | None = None,
) -> None:
    """Convert a Darwin Core Archive to a SQL database."""
    settings = get_convert_settings()
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if num_threads is None:
        num_threads = settings.num_threads
    if db_url is None:
        db_url = get_default_db_url(dwca_path)

    rprint(f"[cyan]Starting conversion of DwC-A file to database:[/cyan] {db_url}")

    zip_ref = zipfile.ZipFile(dwca_path, "r")
    tables = summarize_tables(zip_ref, "meta.xml")

    engine, session = create_engine_and_session(db_url)

    rprint("[cyan]Creating schema...[/cyan]")
    create_schema_from_meta(engine, tables)

    table_row_counts = estimate_and_display_row_counts(zip_ref, tables, num_threads)

    rprint("[cyan]Inserting data...[/cyan]")
    insert_data(engine, session, zip_ref, tables, table_row_counts, chunk_size, num_threads)

    rprint("[cyan]Summarizing SQL tables...[/cyan]")
    summarize_sql_tables(engine, session)

    rprint("[green]Conversion completed successfully![/green]")
    rprint(f"[cyan]Database URL:[/cyan] {db_url}")

    session.close()


@app.command()
def sample(db_url: str) -> None:
    """Display random samples from an existing database."""
    _engine, session = create_engine_and_session(db_url)
    rprint("[cyan]Displaying Random Samples...[/cyan]")
    display_random_samples(session)
    rprint("[green]Random samples displayed successfully![/green]")


def get_default_db_url(dwca_path: str) -> str:
    """Generate default database URL from archive path."""
    base_name = Path(dwca_path).stem
    return f"sqlite:///{base_name}.db"


if __name__ == "__main__":
    app()
