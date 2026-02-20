# dwca-tools

A Python CLI for working with [Darwin Core Archive](https://dwc.tdwg.org/) (DwC-A) files — the standard zip format used by biodiversity databases like [GBIF](https://www.gbif.org/) and [iNaturalist](https://www.inaturalist.org/).

## Installation

```bash
git clone https://github.com/mihow/dwca-tools.git
cd dwca-tools
uv sync
source .venv/bin/activate
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

## Commands

### `summarize` — Inspect archives

Inspect Darwin Core Archive files without extracting them.

```bash
# Show archive structure: files, tables, columns, row counts
dwca-tools summarize files archive.zip

# Summarize taxa with occurrence and image counts
dwca-tools summarize taxa archive.zip

# Group by verbatim name and show backbone resolution mismatches
dwca-tools summarize taxa archive.zip --group-by verbatimScientificName --show-mismatched-names

# Filter to species-rank only, limit output
dwca-tools summarize taxa archive.zip --species-only --limit 20
```

### `convert` — Load into a database

Convert DwC-A files to SQL databases (SQLite, PostgreSQL, etc.) for querying.

```bash
# SQLite
dwca-tools convert convert archive.zip --db-url sqlite:///data.db

# PostgreSQL
dwca-tools convert convert archive.zip --db-url postgresql://user@localhost/dbname

# Custom batch size
dwca-tools convert convert archive.zip --db-url sqlite:///data.db --batch-size 5000

# Display random samples from an existing database
dwca-tools convert sample --db-url sqlite:///data.db
```

### `aggregate` — Build summary tables

Create a `taxa` summary table by joining occurrence and multimedia data (requires a prior `convert` run).

```bash
dwca-tools aggregate populate-taxa-table --db-url sqlite:///data.db
```

### `download` — GBIF occurrence downloads

Request, monitor, and fetch occurrence downloads from the [GBIF API](https://www.gbif.org/developer/occurrence#download). Requires a GBIF account (`GBIF_USERNAME`, `GBIF_PASSWORD`, `GBIF_EMAIL` env vars or `.env` file).

```bash
# Download by taxon keys (submits request, polls until ready, downloads the archive)
dwca-tools download request taxon_keys.txt --has-images -o output.zip

# Use verbatim scientific names instead of backbone keys
dwca-tools download request names.txt --match-names --has-images

# Filter by country, dataset, or arbitrary predicate
dwca-tools download request keys.txt --country US --dataset-key <uuid>
dwca-tools download request keys.txt --predicate filters.json

# Submit without waiting
dwca-tools download request keys.txt --no-wait

# Check status / fetch a completed download separately
dwca-tools download status <download-key>
dwca-tools download fetch <download-key> -o output.zip
```

## Development

```bash
make install-dev    # Install with dev deps
make ci             # Lint, format-check, typecheck, test with coverage
make test           # Just tests (pytest)
make docker-build   # Build Docker image
```

## Origins

This project builds on [mihow/dwca-to-sql](https://github.com/mihow/dwca-to-sql).

## License

MIT License — see [LICENSE](LICENSE) for details.
