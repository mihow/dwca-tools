# Test Archive Infrastructure Plan

## Overview
This document outlines the plan for adding small test archives to the repository for CI testing.

## Goals
1. Provide realistic test data for development and CI
2. Keep test archives small enough to commit to git
3. Cover different DwC-A variations and edge cases
4. Enable comprehensive integration testing

## Test Archive Requirements

### Size Constraints
- Each test archive should be < 100KB compressed
- Total test data should be < 500KB
- Use minimal but representative datasets

### Coverage Needed

#### 1. Standard DwC-A Format
- **File**: `tests/data/dwca/simple-dwca.zip`
- **Contents**:
  - meta.xml (standard structure)
  - occurrence.txt (10-20 rows)
  - multimedia.txt (5-10 rows)
  - Simple schema with common fields
- **Purpose**: Basic DwC-A functionality testing

#### 2. DwC-A with Extensions
- **File**: `tests/data/dwca/with-extensions.zip`
- **Contents**:
  - meta.xml with extensions defined
  - occurrence.txt (core)
  - measurements.txt (extension)
  - taxon.txt (extension)
- **Purpose**: Test extension handling

#### 3. Minimal DwC-A
- **File**: `tests/data/dwca/minimal.zip`
- **Contents**:
  - meta.xml
  - occurrence.txt (5 rows, minimal columns)
- **Purpose**: Test minimal valid archive

#### 4. Edge Cases
- **File**: `tests/data/dwca/edge-cases.zip`
- **Contents**:
  - Special characters in data
  - Empty fields
  - Very long field values
  - Unicode characters
- **Purpose**: Robustness testing

## Sources for Test Data

### Option 1: Real Public Datasets (Subset)
- **GBIF**: Download small occurrence datasets
  - Use GBIF portal to create custom downloads
  - Filter by small geographic area or rare species
  - Limit to 10-20 occurrences
- **iDigBio**: Similar approach for US data
- **Pros**: Real-world data, realistic complexity
- **Cons**: Need to attribute source, may contain PII

### Option 2: Synthetic Data
- **Approach**: Generate valid DwC-A archives programmatically
- **Tools**: Python script to create test archives
- **Pros**: Complete control, no licensing issues
- **Cons**: May miss real-world edge cases

### Option 3: Existing Test Data
- **Sources**:
  - Darwin Core GitHub repo (examples)
  - GBIF IPT tool (sample archives)
  - Scientific publications (supplementary data)
- **Pros**: Already validated
- **Cons**: May not fit our specific needs

## Recommended Approach

### Phase 1: Find Real Small Archives
1. Search for existing small DwC-A archives:
   - GBIF API: search for smallest datasets
   - GitHub: search for DwC-A examples
   - Darwin Core examples directory

2. Evaluate candidates:
   - Check license (CC0 or CC-BY preferred)
   - Verify file size
   - Ensure data quality
   - Check for completeness

3. Document sources:
   - Add attribution in README
   - Include license information
   - Note any modifications made

### Phase 2: Create Synthetic Archives
For edge cases and specific scenarios, create synthetic archives:

```python
# scripts/create_test_archives.py
"""Generate synthetic test archives for CI."""
import zipfile
from pathlib import Path

def create_minimal_dwca(output_path: Path):
    """Create a minimal valid DwC-A archive."""
    # Create meta.xml
    # Create occurrence.txt with minimal data
    # Package into zip
    pass

def create_edge_case_dwca(output_path: Path):
    """Create archive with edge cases."""
    # Special characters, unicode, empty fields
    pass
```

### Phase 3: CI Integration
Add test archives to CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Test with sample archives
  run: |
    pytest tests/test_dwca_real.py -v
    pytest tests/test_integration.py -v
```

## Test Archive Inventory

### Small Public Datasets to Search For
- [ ] Single species dataset (e.g., rare endemic)
- [ ] Small geographic area (e.g., city park)
- [ ] Specific collection event
- [ ] Type specimens only
- [ ] Small herbarium collection

### Search Locations
- [ ] GBIF Portal (filter by small record counts)
- [ ] iDigBio Portal
- [ ] VertNet
- [ ] OBIS (marine data)
- [ ] Darwin Core GitHub examples
- [ ] IPT installations (various institutions)

## File Organization

```
tests/
├── data/
│   ├── dwca/
│   │   ├── README.md              # Attribution and sources
│   │   ├── simple-dwca.zip        # Basic archive
│   │   ├── with-extensions.zip    # Archive with extensions
│   │   ├── minimal.zip            # Minimal valid archive
│   │   ├── edge-cases.zip         # Edge cases
│   │   └── real-gbif-sample.zip   # Real GBIF data
│   └── inaturalist/
│       ├── README.md              # iNaturalist test data info
│       ├── mini-observations.csv  # Small observation sample
│       └── mini-taxa.csv          # Corresponding taxa
├── test_dwca_real.py             # Tests with real archives
└── test_integration.py           # End-to-end tests
```

## Test Data Attribution Template

```markdown
# Test Data Sources

## DwC-A Archives

### simple-dwca.zip
- **Source**: GBIF dataset key XXXXXXX
- **Original Size**: 1000 records
- **Modified**: Reduced to 20 records for testing
- **License**: CC0 1.0 Universal
- **Citation**: [Full citation]
- **URL**: https://www.gbif.org/dataset/XXXXXXX

### real-gbif-sample.zip
- **Source**: [Institution Name]
- **License**: CC-BY 4.0
- **Citation**: [Full citation]
- **Modifications**: None / [describe]
```

## .gitignore Considerations

For larger test files that shouldn't be committed:

```gitignore
# Large test data (download separately)
tests/data/large/
*.db
*.sqlite
```

## Alternative: Remote Test Data

If test archives are too large for git:

1. **Option A**: Git LFS
   ```bash
   git lfs track "tests/data/**/*.zip"
   ```

2. **Option B**: Download script
   ```python
   # scripts/download_test_data.py
   """Download test data from remote location."""
   import requests
   
   TEST_DATA_URLS = {
       "simple-dwca.zip": "https://example.com/test-data/simple.zip",
       # ...
   }
   ```

3. **Option C**: CI cache
   ```yaml
   - name: Cache test data
     uses: actions/cache@v2
     with:
       path: tests/data
       key: test-data-v1
   ```

## Next Steps

1. [ ] Search for suitable small public DwC-A archives
2. [ ] Create synthetic test archive generator script
3. [ ] Download and verify at least 2 real archives
4. [ ] Create tests/data directory structure
5. [ ] Add README with attribution
6. [ ] Update .gitignore if needed
7. [ ] Write integration tests using archives
8. [ ] Document in main README how to run tests
9. [ ] Ensure CI runs with test archives

## Success Criteria

- Have at least 3 different test archives
- All test archives < 100KB each
- Clear attribution for all real data
- Integration tests pass with test archives
- CI pipeline uses test archives
- Documentation explains how to add new test archives
