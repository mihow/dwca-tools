"""Aggregation utilities for dwca-tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from sqlalchemy import Column, Integer, MetaData, String, Table, func, select

from .db import create_engine_and_session, summarize_sql_tables

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

app = typer.Typer(no_args_is_help=True)
console = Console()


def create_taxa_table(engine: Engine, session: Session, batch_size: int) -> None:
    """Create and populate a taxa aggregation table."""
    metadata = MetaData()
    taxa = Table(
        "taxa",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("taxonID", String, unique=True),
        Column("scientificName", String),
        Column("family", String),
        Column("occurrences_count", Integer),
        Column("multimedia_count", Integer),
        extend_existing=True,
    )
    metadata.create_all(engine)

    occurrence = Table("occurrence", metadata, autoload_with=engine, extend_existing=True)
    multimedia = Table("multimedia", metadata, autoload_with=engine, extend_existing=True)

    query = (
        select(
            occurrence.c.taxonID,
            occurrence.c.scientificName,
            occurrence.c.family,
            func.count(occurrence.c.taxonID).label("occurrences_count"),
            func.count(multimedia.c.taxonID).label("multimedia_count"),
        )
        .select_from(occurrence.outerjoin(multimedia, occurrence.c.taxonID == multimedia.c.taxonID))
        .group_by(occurrence.c.taxonID, occurrence.c.scientificName, occurrence.c.family)
    )

    result = session.execute(query).fetchall()
    unique_taxon_ids = {row.taxonID: row for row in result if row.taxonID is not None}

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.completed]{task.completed} rows"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(
            "[cyan]Inserting data into taxa table...", total=len(unique_taxon_ids)
        )
        rows = []
        for _count, taxon_id in enumerate(unique_taxon_ids.keys(), 1):
            taxon_info = unique_taxon_ids[taxon_id]
            rows.append(
                {
                    "taxonID": taxon_id,
                    "scientificName": taxon_info.scientificName,
                    "family": taxon_info.family,
                    "occurrences_count": taxon_info.occurrences_count,
                    "multimedia_count": taxon_info.multimedia_count,
                }
            )
            if len(rows) >= batch_size:
                session.execute(taxa.insert(), rows)
                session.commit()
                progress.update(task, advance=len(rows))
                rows = []
        if rows:
            session.execute(taxa.insert(), rows)
            session.commit()
            progress.update(task, advance=len(rows))
        progress.remove_task(task)
        console.print(f"[green]Inserted {len(unique_taxon_ids)} rows into taxa table.[/green]")


@app.command()
def populate_taxa_table(db_url: str, batch_size: int = 1000) -> None:
    """Populate taxa aggregation table in an existing database."""
    console.print(f"[cyan]Populating taxa table in database:[/cyan] {db_url}")

    engine, session = create_engine_and_session(db_url)

    console.print("[cyan]Creating taxa table...[/cyan]")
    create_taxa_table(engine, session, batch_size)

    console.print("[cyan]Summarizing SQL tables...[/cyan]")
    summarize_sql_tables(engine, session)

    console.print("[green]Taxa table populated successfully![/green]")


if __name__ == "__main__":
    app()
