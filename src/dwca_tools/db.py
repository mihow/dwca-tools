"""Database utilities for dwca-tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from rich import print as rprint
from rich.console import Console
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

console = Console()


def create_engine_and_session(db_url: str) -> tuple[Engine, Session]:
    """Create SQLAlchemy engine and session from database URL."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session


def create_table(
    metadata: MetaData, table_name: str, columns: list[tuple[str | None, str]]
) -> Table:
    """Create a SQLAlchemy table with the given columns."""
    cols = [Column("id", Integer, primary_key=True, autoincrement=True)]
    for idx, col_name in columns:
        if idx is not None:
            cols.append(Column(col_name, String))

    table = Table(table_name, metadata, *cols, extend_existing=True)
    return table


def create_schema_from_meta(
    engine: Engine, tables: list[tuple[str, str, list[tuple[str | None, str]]]]
) -> list[Table]:
    """Create database schema from meta.xml table definitions."""
    metadata = MetaData()
    metadata.bind = engine
    created_tables = []
    for table_name, _file, columns in tables:
        table = create_table(metadata, table_name, columns)
        created_tables.append(table)

    metadata.create_all(engine)
    return created_tables


def summarize_sql_tables(engine: Engine, session: Session) -> None:
    """Print summary of database tables."""
    inspector = sa.inspect(engine)
    for table_name in inspector.get_table_names():
        rprint(f"[cyan]Summary for table {table_name}:[/cyan]")

        # Print row count
        table = Table(table_name, MetaData(), autoload_with=engine)
        stmt = sa.select(sa.func.count()).select_from(table)
        row_count = session.execute(stmt).scalar_one()
        rprint(f"  - Rows: {row_count}")

        # Print column names and types
        columns = inspector.get_columns(table_name)
        for column in columns:
            rprint(f"  - {column['name']} ({column['type']})")
