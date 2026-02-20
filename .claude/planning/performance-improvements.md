# Incorporate dwca-to-sql performance improvements into dwca-tools

## Context

The `dwca-to-sql` repo (`~/Projects/eButterfly/dwca-to-sql`) has changes that significantly improve the data insertion pipeline: chunked file reading (generator-based, no full-file memory load), PostgreSQL COPY fast path with threading, SQLite batched fallback, row count estimation, and index creation. These changes were tested and committed in dwca-to-sql. Now they need to be ported to `dwca-tools` (`~/Projects/dwca-tools/`), the newer, properly-structured successor repo.

Key differences between the repos:
- dwca-tools uses `src/` layout, hatchling, uv, ruff, pyright, proper type hints
- dwca-tools has `aggregate.py`, `queries.py`, tests, CI, Docker — more complete
- dwca-tools convert.py still has the old insertion logic (loads entire file into memory, no PG optimization)
- dwca-tools keeps `display_query_results`, `display_random_samples`, `sample` command (we keep them)
- User wants DWCA_COLUMNS_OF_INTEREST and INDEXES as configurable pydantic-settings with defaults
- pydantic-settings is already a dependency; CLAUDE.md mentions `get_settings.cache_clear()` pattern

**Project conventions** (from `.claude/rules/`):
- Package manager: `uv` (not poetry). Install: `uv sync --extra dev`
- Verification: `make ci` (lint + format-check + typecheck + test with coverage)
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`
- Selective staging: never `git add -A`, use specific files or `git add -p`
- Modern Python 3.12+: `list[str]`, `dict[str, int] | None`, no `from typing import List`
- Google-style docstrings on public functions
- One test file per module: `test_<module>.py`
- Tests: `pytest` with `typer.testing.CliRunner`, markers: slow, integration, unit
- Secrets: never plaintext passwords in CLI examples

## Files to modify

| File | Action |
|------|--------|
| `src/dwca_tools/settings.py` | **Create** — pydantic-settings model for columns_of_interest, indexes, chunk_size, num_threads |
| `src/dwca_tools/convert.py` | **Rewrite insertion pipeline** — chunked reading, PG COPY, SQLite fallback, row estimation, indexes |
| `src/dwca_tools/utils.py` | **Add** human_readable_size, human_readable_number (move from summarize.py) |
| `src/dwca_tools/summarize.py` | **Update** imports to use utils.py for human_readable_* |
| `src/dwca_tools/db.py` | Minor: add `_get_table_column_names` helper |
| `pyproject.toml` | Bump typer to `>=0.15.0` (str\|None support), clean up unused deps |
| `tests/test_convert.py` | **Create** — convert integration test with a small DwC-A fixture |
| `tests/fixtures/test_dwca.zip` | **Create** — small test archive (~20 rows) |

## Step-by-step plan

### Step 1: Create `src/dwca_tools/settings.py`

New pydantic-settings model. Provides defaults that match dwca-to-sql's hardcoded values, but are overridable via env vars. Include a cached `get_settings()` accessor (CLAUDE.md already documents `get_settings.cache_clear()` in test learnings).

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class ConvertSettings(BaseSettings):
    """Settings for the convert pipeline."""
    model_config = SettingsConfigDict(env_prefix="DWCA_")

    chunk_size: int = 500
    num_threads: int = 4
    columns_of_interest: dict[str, list[str]] = {
        "occurrence": ["gbifID", "scientificName", "decimalLatitude", "decimalLongitude", "eventDate"],
        "verbatim": ["gbifID", "verbatimScientificName", "verbatimLatitude", "verbatimLongitude", "eventDate"],
        "multimedia": ["gbifID", "identifier", "references", "title", "created"],
    }
    indexes: dict[str, list[str]] = {
        "occurrence": ["gbifID", "scientificName", "eventDate"],
        "verbatim": ["gbifID", "verbatimScientificName", "eventDate"],
        "multimedia": ["gbifID", "identifier", "created"],
    }

@lru_cache
def get_settings() -> ConvertSettings:
    return ConvertSettings()
```

### Step 2: Move human_readable helpers to `utils.py`

Move `human_readable_size` and `human_readable_number` from `summarize.py` to `utils.py`. Update `summarize.py` imports. This matches the dwca-to-sql refactor and makes them available to convert.py.

- `src/dwca_tools/utils.py` — add the two functions + `import humanize`
- `src/dwca_tools/summarize.py` — change to `from .utils import human_readable_number, human_readable_size`

### Step 3: Add schema inspection helper to `db.py`

Add `get_table_column_names(engine, table_name) -> set[str]` to query actual column names from the database. Used by convert.py to validate columns_of_interest against the schema (case-insensitive, handles PG vs SQLite).

### Step 4: Rewrite convert.py insertion pipeline

Port from dwca-to-sql with these adaptations for dwca-tools:

**New functions to add:**
- `_is_postgres(engine)` — dialect check
- `_count_newlines(file_obj, task, progress)` — fast newline counting
- `estimate_row_count(zip_ref, filename, progress, task)` — row estimation
- `read_chunks(zip_ref, filename, chunk_size)` — generator yielding (headers, chunk) tuples
- `filter_columns(headers, columns_of_interest)` — intersect headers with desired columns, `None` means all
- `_pg_copy_chunk(engine, table_name, headers, chunk, filtered_columns)` — PostgreSQL COPY with quoted column names
- `_pg_insert_table(...)` — threaded PG insertion with progress
- `_sqlite_insert_table(...)` — batched SQLAlchemy insert with progress
- `create_indexes(engine, table_name, indexes)` — CREATE INDEX with quoted columns, schema validation
- `estimate_and_display_row_counts(zip_ref, tables, num_threads)` — parallel row counting
- `insert_data(engine, session, zip_ref, tables, ...)` — dispatcher: PG vs SQLite path

**Keep existing functions (from current dwca-tools):**
- `get_default_db_url(dwca_path)` — unchanged
- `display_query_results(session)` — unchanged
- `display_random_samples(session)` — unchanged
- `convert()` command — update to use new pipeline + settings, add `--chunk-size` and `--num-threads` CLI options
- `sample()` command — unchanged

**Key details:**
- `csv.field_size_limit(sys.maxsize)` at module level
- Quote column names in COPY and CREATE INDEX for PostgreSQL
- Case-insensitive schema column validation
- `filter_columns` uses `is not None` (not truthiness) to distinguish "no filter" from "empty filter"
- `session.close()` at end of convert command
- Load settings via `get_settings()` in the convert command, use as defaults for CLI options

### Step 5: Update pyproject.toml

- Bump `typer>=0.15.0` (for `str | None` support in command signatures — 0.15+ supports it, 0.24 is current)
- Remove `pyyaml>=6.0` if unused (check first)
- Remove `lxml>=5.0.0` if unused (summarize.py uses `xml.etree.ElementTree`, not lxml)

### Step 6: Add test fixture and integration test

Create a minimal DwC-A test fixture and add a test that exercises the convert pipeline with SQLite.

- `tests/fixtures/test_dwca.zip` — small archive with meta.xml + occurrence.txt + multimedia.txt (~20 rows)
- `tests/test_convert.py` — integration test: convert fixture → SQLite, verify row counts

## Commits (conventional, one per step)

1. `refactor: move human_readable helpers to utils module`
2. `feat: add pydantic-settings for convert pipeline configuration`
3. `feat: chunked reading with PostgreSQL COPY and SQLite fallback`
4. `chore: bump typer, clean unused dependencies`
5. `test: add convert integration test with DwC-A fixture`

## Verification

1. `make ci` — full CI (lint + format-check + typecheck + test with coverage)
2. Manual test with SQLite: `uv run dwca-tools convert convert tests/fixtures/test_dwca.zip`
3. Manual test with PostgreSQL (if Docker available): start container, run convert with `--db-url`
4. Verify existing tests still pass: `uv run pytest tests/test_cli.py -v`

## Reference: dwca-to-sql final convert.py

The tested, working version is at `~/Projects/eButterfly/dwca-to-sql/dwca_to_sql/convert.py` (commit `07ef362`). Key patterns to port:
- `read_chunks()` generator at line 86
- `_pg_copy_chunk()` with quoted columns at line 110
- `_sqlite_insert_table()` at line 157
- `insert_data()` dispatcher with `_is_postgres()` check at line 214
- `create_indexes()` with case-insensitive schema validation at line 185
- `estimate_and_display_row_counts()` with ThreadPoolExecutor at line 197
