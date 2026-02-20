# GBIF Predicate Reference

The `--predicate` flag on `dwca-tools download request` accepts a **path to a JSON file**
containing a single GBIF predicate object. It is AND-merged with whatever other filters
are passed (taxon keys, `--gadm-gid`, `--dataset-key`, etc.).

Full predicate documentation: https://www.gbif.org/developer/occurrence#predicates

---

## Predicate types

```json
// equals — single value
{"type": "equals", "key": "KEY", "value": "VALUE"}

// in — multiple values
{"type": "in", "key": "KEY", "values": ["A", "B", "C"]}

// and — combine multiple predicates
{"type": "and", "predicates": [pred1, pred2]}

// or
{"type": "or", "predicates": [pred1, pred2]}

// not
{"type": "not", "predicate": pred1}

// isNotNull — field must be present
{"type": "isNotNull", "parameter": "KEY"}
```

---

## Common predicate keys

| Key                        | Example value          | Notes                                      |
|----------------------------|------------------------|--------------------------------------------|
| `CONTINENT`                | `NORTH_AMERICA`        | AFRICA, ANTARCTICA, ASIA, EUROPE, NORTH_AMERICA, OCEANIA, SOUTH_AMERICA |
| `COUNTRY`                  | `US`                   | ISO 3166-1 alpha-2                         |
| `GADM_GID`                 | `USA.38_1`             | GADM level-1 unit (state/province)         |
| `DATASET_KEY`              | `50c9509d-...`         | GBIF dataset UUID                          |
| `TAXON_KEY`                | `9417`                 | GBIF backbone taxon key                    |
| `VERBATIM_SCIENTIFIC_NAME` | `Burnsius communis`    | Exact name as submitted by publisher       |
| `MEDIA_TYPE`               | `StillImage`           | Has images                                 |
| `OCCURRENCE_STATUS`        | `PRESENT`              |                                            |
| `BASIS_OF_RECORD`          | `HUMAN_OBSERVATION`    | HUMAN_OBSERVATION, PRESERVED_SPECIMEN, etc.|
| `YEAR`                     | `2020`                 | Supports range predicates                  |
| `HAS_COORDINATE`           | `true`                 |                                            |
| `HAS_GEOSPATIAL_ISSUE`     | `false`                |                                            |

---

## Files in this directory

| File                              | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `predicate_north_america.json`    | CONTINENT = NORTH_AMERICA (covers Central America too) |

---

## Example: North + Central America, research-grade, with images

```json
{
  "type": "and",
  "predicates": [
    {"type": "equals", "key": "CONTINENT",         "value": "NORTH_AMERICA"},
    {"type": "equals", "key": "MEDIA_TYPE",         "value": "StillImage"},
    {"type": "equals", "key": "OCCURRENCE_STATUS",  "value": "PRESENT"},
    {"type": "equals", "key": "HAS_COORDINATE",     "value": "true"}
  ]
}
```
