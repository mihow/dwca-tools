# dwca-tools

Tools for working with Darwin Core Archive (DWCA) and iNaturalist open data.

## Features

- **iNaturalist Open Data Support**: Download, cache, and extract iNaturalist's monthly data exports
- **Data Models**: Pydantic models for observations, taxa, photos, and more
- **CLI Interface**: Command-line tools for common operations
- **Python API**: Programmatic access to all functionality
- **Caching & Versioning**: Automatic file caching with date-based versioning
- **Modern Python**: Python 3.12+ with type hints, Pydantic, pytest

## Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/mihow/dwca-tools
cd dwca-tools
pip install -e ".[dev]"
```

### CLI Usage

```bash
# Download iNaturalist taxa data
dwca-tools inaturalist download taxa

# Extract species-level taxa
dwca-tools inaturalist extract taxa --filter rank=species --output species.json

# Download all data types
dwca-tools inaturalist download all
```

### Python API

```python
from dwca_tools.inaturalist import download_taxa, extract_taxa

# Download and extract taxa
file_path, _ = download_taxa()
taxa, metadata = extract_taxa(filters={"rank": ["species", "genus"]})

print(f"Extracted {metadata.total_records} taxa")
for taxon in taxa[:5]:
    print(f"  {taxon.name} ({taxon.rank})")
```

## Documentation

- [iNaturalist Support Guide](docs/INATURALIST_SUPPORT.md) - Comprehensive guide to working with iNaturalist data
- See inline documentation and type hints in the code

## Available Commands

```bash
# General
dwca-tools --help              # Show all commands
dwca-tools --version           # Show version
dwca-tools info                # Show application info

# iNaturalist Operations
dwca-tools inaturalist download <type>    # Download data (taxa, observations, photos, all)
dwca-tools inaturalist extract <type>     # Extract and filter data
```

## Development

### Setup

```bash
# Clone and install
git clone https://github.com/mihow/dwca-tools
cd dwca-tools
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests

# Type checking
pyright src
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dwca_tools

# Run specific test file
pytest tests/test_inaturalist_models.py

# Run tests by marker
pytest -m "not slow"
```

## Project Structure

```
.
├── src/dwca_tools/           # Main package
│   ├── inaturalist/          # iNaturalist integration
│   │   ├── models.py         # Data models
│   │   ├── downloader.py     # Download utilities
│   │   └── extractor.py      # Extraction utilities
│   ├── cli.py                # Command-line interface
│   ├── config.py             # Configuration
│   └── models.py             # Core models
├── tests/                    # Test suite
│   ├── test_inaturalist_models.py
│   ├── test_cli.py
│   └── ...
├── docs/                     # Documentation
│   └── INATURALIST_SUPPORT.md
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Data Sources

This tool works with data from:

- [iNaturalist Open Data](https://github.com/inaturalist/inaturalist-open-data) - Monthly snapshots of observations, taxa, and photos
- Darwin Core Archive format (coming soon)

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## Resources

- [iNaturalist](https://www.inaturalist.org)
- [iNaturalist Open Data Repository](https://github.com/inaturalist/inaturalist-open-data)
- [Darwin Core Standard](https://dwc.tdwg.org/)
- [GBIF - Global Biodiversity Information Facility](https://www.gbif.org/)

---

Built with ❤️ for biodiversity research
