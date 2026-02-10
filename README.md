# dwca-tools

Tools for working with Darwin Core Archive (DwC-A) files, including support for iNaturalist data format.

## Features

- **DwC-A Inspection**: Quickly inspect Darwin Core Archive files without full extraction
- **SQL Conversion**: Convert DwC-A files to SQL databases (SQLite, PostgreSQL, etc.)
- **Aggregation Tools**: Create summary tables and perform common aggregations
- **iNaturalist Support** (Planned): Work efficiently with large iNaturalist open data files
- **Modern Python**: Python 3.12+ with type hints, Pydantic, pytest
- **Rich CLI**: Beautiful command-line interface with progress bars and tables

## Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/mihow/dwca-tools.git
cd dwca-tools
pip install -e .
```

### Usage

```bash
# Inspect a Darwin Core Archive
dwca-tools summarize archive.zip

# Convert to SQL database
dwca-tools convert archive.zip --db-url sqlite:///data.db

# Convert to PostgreSQL
dwca-tools convert archive.zip --db-url postgresql://user:pass@localhost/dbname

# Display random samples from database
dwca-tools convert sample --db-url sqlite:///data.db

# Create aggregated taxa table
dwca-tools aggregate populate-taxa-table --db-url sqlite:///data.db
```

### Docker Setup

```bash
# Run tests in container
docker compose run --rm test

# Development shell
docker compose run --rm dev
```

## Project Structure

```
.
├── docs/                       # Documentation
│   ├── INATURALIST_SUPPORT.md  # iNaturalist support plan
│   └── TEST_ARCHIVES_PLAN.md   # Test archive infrastructure plan
├── src/dwca_tools/             # Main package
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── utils.py                # Utility functions
│   ├── db.py                   # Database operations
│   ├── summarize.py            # Archive inspection
│   ├── convert.py              # Archive conversion
│   ├── aggregate.py            # Aggregation operations
│   └── queries.py              # Common SQL queries
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures
│   └── test_cli.py             # CLI tests
├── .github/workflows/          # CI/CD pipelines
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Development services
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

## Features

### DwC-A Archive Inspection

Quickly inspect Darwin Core Archive files to understand their structure:

```bash
dwca-tools summarize mydata.zip
```

This will show:
- Archive contents and file sizes
- Table definitions from meta.xml
- Column names for each table
- Row count estimates

### SQL Conversion

Convert DwC-A files to SQL databases for easier querying:

```bash
# SQLite (default)
dwca-tools convert mydata.zip

# PostgreSQL
dwca-tools convert mydata.zip --db-url postgresql://localhost/mydb

# Custom batch size
dwca-tools convert mydata.zip --batch-size 5000
```

### Aggregation Tables

Create summary tables from occurrence data:

```bash
dwca-tools aggregate populate-taxa-table --db-url sqlite:///data.db
```

## iNaturalist Support (Planned)

Support for the iNaturalist open data format is planned. See [docs/INATURALIST_SUPPORT.md](docs/INATURALIST_SUPPORT.md) for details on:
- Efficient inspection of large archive files
- Loading subsets by taxon (e.g., Lepidoptera)
- Random sampling strategies
- Schema mapping to SQL databases

## Test Archives

Small test archives will be added to enable CI testing. See [docs/TEST_ARCHIVES_PLAN.md](docs/TEST_ARCHIVES_PLAN.md) for the infrastructure plan.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dwca_tools

# Run specific test
pytest tests/test_cli.py -v
```

### Code Quality

```bash
# Lint
ruff check src tests

# Format
ruff format src tests

# Type check
pyright src
```

## Origins

This project brings together tools from [mihow/dwca-to-sql](https://github.com/mihow/dwca-to-sql) into a more comprehensive package with plans for iNaturalist data support.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with Python 3.12+
