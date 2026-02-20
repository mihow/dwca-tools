"""Database utilities for dwca-tools."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from rich.console import Console
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import sessionmaker

from .schemas import ColumnDefinition, TableDefinition

_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

console = Console()


def validate_sql_identifier(name: str) -> str:
    """Validate that a name is safe to use as a SQL identifier.

    Raises ValueError if the name contains characters outside [A-Za-z0-9_].
    """
    if not _SQL_IDENTIFIER_RE.match(name):
        msg = f"Invalid SQL identifier: {name!r}"
        raise ValueError(msg)
    return name


def create_engine_and_session(db_url: str) -> tuple[Engine, Session]:
    """Create SQLAlchemy engine and session from database URL."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session


def create_table(
    metadata: MetaData, table_name: str, columns: list[ColumnDefinition]
) -> Table:
    """Create a SQLAlchemy table with the given columns."""
    validate_sql_identifier(table_name)
    cols: list[Column[Any]] = [Column("id", Integer, primary_key=True, autoincrement=True)]
    for col in columns:
        if col.index is not None:
            validate_sql_identifier(col.name)
            cols.append(Column(col.name, String))

    table = Table(table_name, metadata, *cols, extend_existing=True)
    return table


def create_schema_from_meta(engine: Engine, tables: list[TableDefinition]) -> list[Table]:
    """Create database schema from meta.xml table definitions."""
    metadata = MetaData()
    created_tables = []
    for table_def in tables:
        table = create_table(metadata, table_def.name, table_def.columns)
        created_tables.append(table)

    metadata.create_all(engine)
    return created_tables


def get_table_column_names(engine: Engine, table_name: str) -> set[str]:
    """Return the set of column names for a table."""
    inspector = sa.inspect(engine)
    return {col["name"] for col in inspector.get_columns(table_name)}


def summarize_sql_tables(engine: Engine, session: Session) -> None:
    """Print summary of database tables."""
    inspector = sa.inspect(engine)
    for table_name in inspector.get_table_names():
        console.print(f"[cyan]Summary for table {table_name}:[/cyan]")

        # Print row count
        table = Table(table_name, MetaData(), autoload_with=engine)
        stmt = sa.select(sa.func.count()).select_from(table)
        row_count = session.execute(stmt).scalar_one()
        console.print(f"  - Rows: {row_count}")

        # Print column names and types
        columns = inspector.get_columns(table_name)
        for column in columns:
            console.print(f"  - {column['name']} ({column['type']})")
