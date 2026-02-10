"""Common SQL queries for dwca-tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from rich.console import Console
from sqlalchemy import MetaData, Table, func, select

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.orm import Session

console = Console()


def count_occurrences_per_taxon(session: Session) -> list[Row]:
    """Count occurrences per taxon."""
    occurrence = Table(
        "occurrence", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    query = select(occurrence.c.taxonID, func.count().label("occurrence_count")).group_by(
        occurrence.c.taxonID
    )
    result = session.execute(query).fetchall()
    return result


def count_multimedia_per_taxon(session: Session) -> list[Row]:
    """Count multimedia entries per taxon."""
    occurrence = Table(
        "occurrence", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    multimedia = Table(
        "multimedia", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    query = (
        select(
            occurrence.c.taxonID,
            func.count(multimedia.c.gbifID).label("multimedia_count"),
        )
        .join(multimedia, occurrence.c.gbifID == multimedia.c.gbifID)
        .group_by(occurrence.c.taxonID)
    )
    result = session.execute(query).fetchall()
    return result


def highest_occurrences(session: Session, limit: int = 10) -> list[Row]:
    """Get taxa with highest occurrence counts."""
    occurrence = Table(
        "occurrence", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    query = (
        select(occurrence.c.taxonID, func.count().label("occurrence_count"))
        .group_by(occurrence.c.taxonID)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = session.execute(query).fetchall()
    return result


def highest_multimedia(session: Session, limit: int = 10) -> list[Row]:
    """Get taxa with highest multimedia counts."""
    occurrence = Table(
        "occurrence", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    multimedia = Table(
        "multimedia", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    query = (
        select(
            occurrence.c.taxonID,
            func.count(multimedia.c.gbifID).label("multimedia_count"),
        )
        .join(multimedia, occurrence.c.gbifID == multimedia.c.gbifID)
        .group_by(occurrence.c.taxonID)
        .order_by(func.count(multimedia.c.gbifID).desc())
        .limit(limit)
    )
    result = session.execute(query).fetchall()
    return result


def taxa_with_no_entries(session: Session) -> list[Row]:
    """Get taxa with no occurrences or multimedia."""
    taxa = Table("taxa", MetaData(), autoload_with=session.bind, extend_existing=True)
    query = select(taxa.c.taxonID).where(
        (taxa.c.occurrences_count == 0) | (taxa.c.multimedia_count == 0)
    )
    result = session.execute(query).fetchall()
    return result


def family_summary(session: Session) -> list[Row]:
    """Get summary of occurrence counts by family."""
    occurrence = Table(
        "occurrence", MetaData(), autoload_with=session.bind, extend_existing=True
    )
    query = select(occurrence.c.family, func.count().label("family_count")).group_by(
        occurrence.c.family
    )
    result = session.execute(query).fetchall()
    return result


def random_sample_from_table(session: Session, table_name: str, limit: int = 5) -> list[Row]:
    """Get random sample of rows from a table."""
    table = Table(table_name, MetaData(), autoload_with=session.bind, extend_existing=True)
    query = select(table).order_by(sa.func.random()).limit(limit)
    result = session.execute(query).fetchall()
    return result


def random_sample_from_all_tables(session: Session) -> dict[str, list[Row]]:
    """Get random samples from all tables in the database."""
    inspector = sa.inspect(session.bind)
    table_names = inspector.get_table_names()
    samples = {}
    for table_name in table_names:
        samples[table_name] = random_sample_from_table(session, table_name)
    return samples
