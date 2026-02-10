# iNaturalist Data Format Support Plan

## Overview
This document outlines the plan for adding support for iNaturalist open data format to dwca-tools.

## iNaturalist Data Format

### Current Understanding

The iNaturalist Open Dataset has a different structure than standard Darwin Core Archives:

1. **Format**: Tab-separated CSV files (not using quotes around text columns)
2. **Archive Structure**: Available as:
   - Single gzipped archive containing all 4 files (`inaturalist-open-data-latest.tar.gz`)
   - Separate gzipped CSV files at root of S3 bucket

3. **Tables**:
   - `observations.csv.gz` - Observation records
   - `observers.csv.gz` - Observer/user information
   - `photos.csv.gz` - Photo metadata
   - `taxa.csv.gz` - Taxonomy hierarchy

### Schema Details

#### Observations Table
- observation_uuid (uuid)
- observer_id (integer)
- latitude (numeric)
- longitude (numeric)
- positional_accuracy (integer)
- taxon_id (integer)
- quality_grade (string: Casual, Needs ID, Research Grade)
- observed_on (date)
- anomaly_score (double precision)

#### Observers Table
- observer_id (integer)
- login (string)
- name (string)

#### Photos Table
- photo_uuid (uuid)
- photo_id (integer)
- observation_uuid (uuid)
- observer_id (integer)
- extension (string: jpeg, etc.)
- license (string)
- width (smallint)
- height (smallint)
- position (smallint)

#### Taxa Table
- taxon_id (integer)
- ancestry (string: backslash-separated taxon_ids)
- rank_level (double precision)
- rank (string: Kingdom, Phylum, Class, Order, Family, Genus, Species, etc.)
- name (string: scientific name)
- active (boolean)

### Key Differences from Standard DwC-A

1. **No meta.xml**: iNaturalist data doesn't use standard DwC-A meta.xml
2. **Different Schema**: Custom schema optimized for iNaturalist's use case
3. **UUID Identifiers**: Uses UUIDs instead of integer IDs for some entities
4. **Gzipped CSVs**: Files are compressed with gzip, not zip
5. **No Quotes**: Text fields don't use quotes, contains raw quotes in data
6. **Very Large Files**: Can be multiple gigabytes compressed

## Implementation Plan

### Phase 1: Research and Prototype
- [x] Document iNaturalist data format differences
- [ ] Download sample iNaturalist dataset for testing
- [ ] Analyze file sizes and compression ratios
- [ ] Test decompression and parsing performance
- [ ] Create proof-of-concept parser

### Phase 2: Efficient Archive Inspection
Goal: Inspect large archives without fully decompressing them

Features to implement:
- [ ] Stream-based gzip decompression (avoid loading entire file)
- [ ] Sample first N rows for quick inspection
- [ ] Estimate total row counts from file sizes
- [ ] Display schema information (column names and types)
- [ ] Show file size and compression statistics
- [ ] Quick peek at data distributions

Implementation approach:
```python
import gzip
import csv
from pathlib import Path

def inspect_inat_archive(archive_path: Path):
    """Efficiently inspect iNaturalist archive without full decompression."""
    # Extract metadata from archive structure
    # Stream first N rows from each table
    # Calculate statistics
    pass
```

### Phase 3: Selective Loading Strategies
Goal: Load only relevant subsets of data

Features to implement:
- [ ] Filter by taxonomic groups (e.g., Lepidoptera, Aves)
- [ ] Filter by geographic bounds (lat/lon bbox)
- [ ] Filter by quality grade (Research Grade only)
- [ ] Random sampling (stratified by taxon)
- [ ] Time-based filtering (date ranges)
- [ ] Observer-based filtering

Example use cases:
```bash
# Load only Lepidoptera observations
dwca-tools inaturalist load data.tar.gz --taxon Lepidoptera --db-url postgres://...

# Load random sample of 1000 observations
dwca-tools inaturalist load data.tar.gz --sample 1000 --db-url sqlite:///sample.db

# Load only Research Grade observations in a region
dwca-tools inaturalist load data.tar.gz --quality research --bbox "-122,37,-121,38"
```

### Phase 4: SQL Schema Mapping
Goal: Map iNaturalist schema to SQL database

Considerations:
- [ ] Create appropriate indexes for common queries
- [ ] Handle UUID columns efficiently
- [ ] Preserve ancestry information for taxonomic queries
- [ ] Add foreign key relationships
- [ ] Consider denormalization for performance

SQL Schema:
```sql
-- Based on structure.sql from iNaturalist repo
CREATE TABLE observations (...);
CREATE TABLE observers (...);
CREATE TABLE photos (...);
CREATE TABLE taxa (...);

-- Add indexes for performance
CREATE INDEX idx_observations_taxon ON observations(taxon_id);
CREATE INDEX idx_observations_observer ON observations(observer_id);
CREATE INDEX idx_photos_observation ON photos(observation_uuid);
CREATE INDEX idx_taxa_active ON taxa(active) WHERE active = true;
```

### Phase 5: Integration with Existing Tools
Goal: Seamlessly integrate iNaturalist support into existing dwca-tools

Tasks:
- [ ] Add iNaturalist format detection
- [ ] Create unified interface for both DwC-A and iNaturalist formats
- [ ] Update CLI to support both formats
- [ ] Add conversion between formats if useful
- [ ] Update documentation and examples

### Phase 6: Testing and Optimization
- [ ] Add unit tests for iNaturalist parsers
- [ ] Add integration tests with sample data
- [ ] Performance benchmarks for large files
- [ ] Memory usage profiling
- [ ] Optimize for streaming operations
- [ ] Add progress bars and ETA for long operations

## Technical Challenges

### 1. File Size
- **Challenge**: iNaturalist archives can be 10+ GB compressed, 100+ GB uncompressed
- **Solution**: Stream processing, never load entire file into memory
- **Tools**: Python gzip module with streaming, pandas chunking

### 2. Memory Efficiency
- **Challenge**: Cannot load entire dataset into memory
- **Solution**: Process in batches, use database for storage
- **Approach**: Read N rows, insert to DB, repeat

### 3. Performance
- **Challenge**: Large files take time to process
- **Solutions**:
  - Show progress indicators
  - Provide early estimates
  - Allow cancellation and resumption
  - Consider parallel processing for independent tables

### 4. Data Quality
- **Challenge**: Handle quotes and special characters in unquoted CSV
- **Solution**: Careful CSV parsing configuration, test with real data
- **Note**: Fields may contain single/double quotes, newlines

### 5. Filtering Efficiency
- **Challenge**: Filtering during load vs. after load
- **Solution**: Pre-filter during streaming to avoid unnecessary I/O
- **Approach**: Apply filters during CSV reading, before DB insertion

## Success Criteria

1. Can inspect a 10GB iNaturalist archive in < 10 seconds
2. Can load filtered subset (e.g., one taxonomic order) in reasonable time
3. Can handle random sampling efficiently
4. Memory usage stays under 500MB regardless of file size
5. Clear progress indicators and ETA
6. Comprehensive documentation and examples

## Future Enhancements

- Support for incremental updates
- Direct download from iNaturalist S3 bucket
- Built-in data validation
- Summary statistics generation
- Export to other formats (GeoJSON, Parquet)
- Integration with spatial databases (PostGIS)

## Resources

- [iNaturalist Open Data Repo](https://github.com/inaturalist/inaturalist-open-data)
- [Metadata Documentation](https://github.com/inaturalist/inaturalist-open-data/tree/main/Metadata)
- [AWS Open Data Registry](https://registry.opendata.aws/inaturalist-open-data/)
