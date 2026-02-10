# iNaturalist Open Data Support

This document describes dwca-tools' support for working with iNaturalist's open data exports.

## Overview

iNaturalist provides monthly snapshots of their observation, taxa, and photo data as tab-separated CSV files stored in an S3 bucket. dwca-tools provides utilities to:

- Download and cache these data files
- Extract and filter records
- Work with the data programmatically

## Data Sources

iNaturalist publishes the following data files:

- **taxa.csv.gz** - Taxonomic classification data (species, genera, families, etc.)
- **observations.csv.gz** - Observation records with location, time, quality grade
- **photos.csv.gz** - Photo metadata linking to S3 storage
- **observers.csv.gz** - User/observer information

All files are available at: `https://inaturalist-open-data.s3.amazonaws.com/`

## Installation

dwca-tools requires Python 3.12+ and the following dependencies:

```bash
pip install dwca-tools
```

Or for development:

```bash
git clone https://github.com/mihow/dwca-tools
cd dwca-tools
pip install -e ".[dev]"
```

## CLI Usage

### Download Data

Download iNaturalist data files to local cache:

```bash
# Download taxa data
dwca-tools inaturalist download taxa

# Download observations data
dwca-tools inaturalist download observations

# Download photos data
dwca-tools inaturalist download photos

# Download all data types
dwca-tools inaturalist download all

# Force re-download even if cached
dwca-tools inaturalist download taxa --force
```

Downloaded files are cached in `~/.cache/dwca-tools/inaturalist/` with versioning based on download date.

### Extract and Filter Data

Extract records from downloaded files with optional filtering:

```bash
# Extract all taxa
dwca-tools inaturalist extract taxa

# Extract only species-level taxa
dwca-tools inaturalist extract taxa --filter rank=species

# Extract multiple ranks
dwca-tools inaturalist extract taxa --filter rank=species,genus

# Extract research-grade observations
dwca-tools inaturalist extract observations --filter quality_grade=research

# Save results to JSON file
dwca-tools inaturalist extract taxa --filter rank=species --output species.json
```

## Python API

### Models

dwca-tools provides Pydantic models for all iNaturalist data types:

```python
from dwca_tools.inaturalist import Taxon, Observation, Photo, Observer

# Create a taxon
taxon = Taxon(
    taxon_id=123,
    name="Papilio machaon",
    rank="species",
    ancestry="48460/1/47120",
    active=True
)

# Create a photo and get its URL
photo = Photo(
    photo_id=789,
    observation_id=123,
    observer_id=456,
    extension="jpg",
    license="CC-BY"
)
print(photo.get_url("medium"))  # Generate S3 URL
```

### Downloading Data

```python
from dwca_tools.inaturalist import download_taxa, download_observations, download_photos

# Download taxa data
file_path, was_downloaded = download_taxa()
print(f"Taxa file: {file_path}")
print(f"Newly downloaded: {was_downloaded}")

# Force re-download
file_path, _ = download_taxa(force=True)

# Download other data types
obs_path, _ = download_observations()
photo_path, _ = download_photos()
```

### Extracting Data

```python
from dwca_tools.inaturalist import extract_taxa, extract_observations, extract_photos

# Extract taxa with filters
taxa, metadata = extract_taxa(
    filters={"rank": ["species", "genus"]},
    download_if_missing=True
)

print(f"Extracted {metadata.total_records} taxa")
for taxon in taxa[:5]:
    print(f"  {taxon.taxon_id}: {taxon.name} ({taxon.rank})")

# Extract observations
observations, metadata = extract_observations(
    filters={"quality_grade": "research"}
)

# Extract photos
photos, metadata = extract_photos(
    filters={"license": ["CC-BY", "CC0"]}
)
```

### Working with DataFrames

For advanced filtering and analysis, work directly with pandas DataFrames:

```python
import pandas as pd
from dwca_tools.inaturalist.extractor import read_taxa_file
from dwca_tools.inaturalist.downloader import get_latest_file

# Get cached file
file_path = get_latest_file("taxa")

# Read as DataFrame
df = read_taxa_file(file_path)

# Filter and analyze
species_df = df[df["rank"] == "species"]
print(f"Total species: {len(species_df)}")

# Group by rank
rank_counts = df["rank"].value_counts()
print(rank_counts)
```

## Data Structure

### Taxa Fields

- `taxon_id`: Unique identifier
- `name`: Scientific name
- `rank`: Taxonomic rank (species, genus, family, etc.)
- `ancestry`: Slash-separated parent taxon IDs
- `active`: Whether taxon is active (vs. synonym)
- `parent_id`: Direct parent taxon ID

### Observation Fields

- `observation_id`: Unique identifier
- `observer_id`: User who made observation
- `latitude` / `longitude`: Location coordinates
- `taxon_id`: Identified species/taxon
- `quality_grade`: research, needs_id, or casual
- `observed_on`: Date of observation
- `created_at` / `updated_at`: Timestamps
- `license`: Creative Commons license

### Photo Fields

- `photo_id`: Unique identifier
- `observation_id`: Associated observation
- `observer_id`: User who uploaded photo
- `extension`: File extension (jpg, png, etc.)
- `license`: Creative Commons license
- `width` / `height`: Image dimensions
- `position`: Position in observation's photo list

## Caching and Versioning

dwca-tools automatically manages file caching and versioning:

- Files are cached in `~/.cache/dwca-tools/inaturalist/{data_type}/`
- Each download is versioned by date: `taxa-2024-01-15.csv.gz`
- A symlink `{data_type}-latest.csv.gz` always points to the most recent version
- Metadata files track download info: `taxa-2024-01-15.metadata.json`
- Duplicate files (same hash) are detected and not re-downloaded

## Photo URLs

Photos are stored in S3 with multiple sizes available:

- `original` - 2048px
- `large` - 1024px
- `medium` - 500px
- `small` - 240px
- `thumb` - 100px
- `square` - 75x75px (cropped)

Generate URLs using the Photo model:

```python
photo = Photo(photo_id=789, extension="jpg", ...)
print(photo.get_url("medium"))
# https://inaturalist-open-data.s3.amazonaws.com/photos/789/medium.jpg
```

## Licenses and Attribution

iNaturalist photos and observations have Creative Commons licenses. When using this data:

- Respect the license terms (CC0, CC-BY, CC-BY-NC, etc.)
- Provide proper attribution when required
- Follow iNaturalist's [data usage guidelines](https://www.inaturalist.org/pages/developers)

Example attribution formats:

- CC0: "Name, no rights reserved (CC0)"
- CC-BY: "© Name, some rights reserved (CC-BY)"
- CC-BY-NC: "© Name, some rights reserved (CC-BY-NC)"

## Resources

- [iNaturalist Open Data Repository](https://github.com/inaturalist/inaturalist-open-data)
- [iNaturalist Open Data S3 Bucket](https://inaturalist-open-data.s3.amazonaws.com/)
- [Darwin Core Standard](https://dwc.tdwg.org/)
- [Creative Commons Licenses](https://creativecommons.org/licenses/)

## Contributing

Contributions are welcome! Please see the main README for development setup and contribution guidelines.

## Known Limitations

- Large data files (observations, photos) may take time to download
- Extraction currently loads full files into memory
- Filtering is done after loading (not during file read)
- Some field names may differ from iNaturalist's documentation

Future improvements may include:
- Streaming/chunked processing for large files
- More efficient filtering during file read
- Support for additional iNaturalist data types
- Integration with Darwin Core Archive format
