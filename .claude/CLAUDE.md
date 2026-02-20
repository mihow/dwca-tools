# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

dwca-tools is a Python CLI for working with Darwin Core Archive (DwC-A) files — a standard zip format used by biodiversity databases like GBIF and iNaturalist. It can inspect archives, convert them to SQL databases, and create aggregation tables.

**CLI entry point**: `dwca-tools` (defined in `pyproject.toml` as `dwca_tools.cli:app`)

## Commands

```bash
make install-dev    # Install with dev deps (uv sync --extra dev)
make ci             # Full CI: lint, format-check, typecheck, test with coverage
make verify         # Full verification: imports, tests, smoke tests, CLI
make lint           # Just linting (ruff)
make test           # Just tests (pytest)
make docker-build   # Build Docker image

# Run a single test
uv run pytest tests/test_cli.py::test_name -v

# Run the CLI directly
uv run dwca-tools summarize archive.zip
uv run dwca-tools convert archive.zip --db-url sqlite:///data.db
uv run dwca-tools aggregate populate-taxa-table --db-url sqlite:///data.db
```

## Context Management

Monitor context usage — keep under 40% (80K/200K tokens) when possible. As context grows, prepare `NEXT_SESSION_PROMPT.md` to summarize progress, compact & commit work, and reference file paths and line numbers. Use offset/limit when reading large files. Prefer command line tools (`jq`, `grep`, `git`) over reading entire files to reduce context. Fix style issues at the end with `make ci`, not incrementally.

## Always-loaded Rules

These rules apply to all work — see `.claude/rules/` for details:

- **Planning and verification** (`planning-and-verification.md`) — think before you act, plan how you'll verify, verify what you change
- **Git conventions** (`git-conventions.md`) — conventional commits, selective staging
- **Writing style** (`writing-style.md`) — measured tone, `gh` CLI workarounds
- **Python style** (`python-style.md`) — modern type annotations (3.10+), imports

## Architecture

### CLI Structure (`src/dwca_tools/cli.py`)

Typer app composed of four sub-apps:

```
dwca-tools
├── summarize <archive.zip>              → summarize.py  (inspect zip + parse meta.xml)
├── convert <archive.zip>                → convert.py    (DwC-A → SQL database)
│   └── sample <db_url>                  →               (show random rows from DB)
├── aggregate populate-taxa-table <url>  → aggregate.py  (build taxa summary table)
└── download                             → download.py   (GBIF occurrence downloads)
    ├── request [TAXA_FILE]              →               (submit + optionally poll & fetch)
    ├── status <download-key>            →               (check status)
    └── fetch <download-key>             →               (download completed archive)
```

### Data Flow

1. **summarize.py** reads the zip without extracting. Parses `meta.xml` (DwC-A standard descriptor) using `xml.etree.ElementTree` to discover tables and columns. Renders Rich tables.

2. **convert.py** orchestrates the full pipeline: calls `summarize_tables()` → `db.create_schema_from_meta()` (creates SQLAlchemy tables, all columns as `String`) → streams CSV data from zip into DB in batches (default 1000 rows). Uses Rich progress bars.

3. **aggregate.py** creates a `taxa` table by joining `occurrence` and `multimedia` tables (must already exist from a `convert` run), grouping by `taxonID`.

4. **download.py** requests GBIF occurrence downloads via the API. Composable predicate builder: `--match-names` queries by `VERBATIM_SCIENTIFIC_NAME` (bypasses GBIF backbone), `--dataset-key` filters by source dataset, plus `--has-images`, `--country`, `--gadm-gid`, `--predicate` (arbitrary JSON). Polls for completion and streams the archive with a Rich progress bar.

### Supporting Modules

- **settings.py** — `GbifSettings` via pydantic-settings. Reads `GBIF_USERNAME`, `GBIF_PASSWORD`, `GBIF_EMAIL` from env vars or `.env` file. `resolve_password()` prompts via getpass if env var is missing. Uses `@lru_cache` (clear with `get_gbif_settings.cache_clear()` in tests).
- **db.py** — SQLAlchemy engine/schema/session utilities. Note: uses deprecated `metadata.bind` pattern with `# type: ignore`.
- **queries.py** — Pre-built SQLAlchemy query functions (occurrence counts, multimedia counts, top-N rankings, family summaries, random sampling).
- **utils.py** — Reads optional `defaults.ini` config via `configparser`.

### Key Dependencies

`typer` (CLI), `rich` (terminal UI), `sqlalchemy` (database), `humanize` (formatting), `psycopg2-binary` (PostgreSQL), `requests` (GBIF API), `pydantic-settings` (credential management). Note: `pydantic`, `pyyaml`, and `lxml` are listed as dependencies but currently unused in source.

### Tests

Tests use `pytest` with `typer.testing.CliRunner`. Currently only CLI smoke tests (help/version). No test archives exist yet — see `docs/TEST_ARCHIVES_PLAN.md`. `asyncio_mode = "auto"` is enabled. Coverage threshold: 20%.

### CI (`test.yml`)

Four parallel jobs: `lint` (ruff), `test` (pytest + Codecov), `typecheck` (pyright), then `build` (package + CLI smoke test). Docker build runs on main only.

## Learnings

- Clear settings cache between tests: `get_settings.cache_clear()`
- Use `tmp_path` fixture for temporary test files
- Always run `make ci` before committing — catches lint/format/type issues
- After pushing workflow changes, check Actions tab for actual results

### uv gotchas

- `[project.optional-dependencies]` are extras, NOT dev deps. `uv sync` alone skips them. Use `uv sync --extra dev` (Makefile:35). Only `[tool.uv] dev-dependencies` are installed by default with `uv sync`.
- Never set `UV_SYSTEM_PYTHON=1` alongside `uv sync`. `uv sync` creates a `.venv`; the env var tells `uv run` to bypass it. The two are mutually exclusive. (.github/workflows/test.yml)

### Pyright (type checker)

- Project uses pyright (not mypy). Config: `pyproject.toml [tool.pyright]`.
- Pyright handles `try/except ImportError` fallback patterns natively — no `type: ignore` needed.

### Debugging CI failures

- `gh run view --log-failed` can return empty output. Use the API instead: `gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs` to get job IDs, then `gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs` for the full log.
- A 12-second CI failure where install passes but the next step fails instantly usually means the tool binary isn't on PATH.
