"""Common SQL queries for dwca-tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import MetaData, Table, func, select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def reflect_table(name: str, session: Session) -> Table:
    """Reflect an existing database table by name."""
    return Table(name, MetaData(), autoload_with=session.bind, extend_existing=True)


def count_occurrences_per_taxon(session: Session) -> Any:
    """Count occurrences per taxon."""
    occurrence = reflect_table("occurrence", session)
    query = select(occurrence.c.taxonID, func.count().label("occurrence_count")).group_by(
        occurrence.c.taxonID
    )
    result = session.execute(query).fetchall()
    return result


def count_multimedia_per_taxon(session: Session) -> Any:
    """Count multimedia entries per taxon."""
    occurrence = reflect_table("occurrence", session)
    multimedia = reflect_table("multimedia", session)
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


def highest_occurrences(session: Session, limit: int = 10) -> Any:
    """Get taxa with highest occurrence counts."""
    occurrence = reflect_table("occurrence", session)
    query = (
        select(occurrence.c.taxonID, func.count().label("occurrence_count"))
        .group_by(occurrence.c.taxonID)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = session.execute(query).fetchall()
    return result


def highest_multimedia(session: Session, limit: int = 10) -> Any:
    """Get taxa with highest multimedia counts."""
    occurrence = reflect_table("occurrence", session)
    multimedia = reflect_table("multimedia", session)
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


def taxa_with_no_entries(session: Session) -> Any:
    """Get taxa with no occurrences or multimedia."""
    taxa = reflect_table("taxa", session)
    query = select(taxa.c.taxonID).where(
        (taxa.c.occurrences_count == 0) | (taxa.c.multimedia_count == 0)
    )
    result = session.execute(query).fetchall()
    return result


def family_summary(session: Session) -> Any:
    """Get summary of occurrence counts by family."""
    occurrence = reflect_table("occurrence", session)
    query = select(occurrence.c.family, func.count().label("family_count")).group_by(
        occurrence.c.family
    )
    result = session.execute(query).fetchall()
    return result


def random_sample_from_table(session: Session, table_name: str, limit: int = 5) -> Any:
    """Get random sample of rows from a table."""
    table = reflect_table(table_name, session)
    query = select(table).order_by(sa.func.random()).limit(limit)
    result = session.execute(query).fetchall()
    return result


def random_sample_from_all_tables(session: Session) -> dict[str, Any]:
    """Get random samples from all tables in the database."""
    inspector = sa.inspect(session.bind)
    if inspector is None:
        return {}
    table_names = inspector.get_table_names()
    samples = {}
    for table_name in table_names:
        samples[table_name] = random_sample_from_table(session, table_name)
    return samples
