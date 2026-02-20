# Plan: `dwca-tools species` command

## Context

The tricky_species_comparison.sh script resolves verbatim names to GBIF backbone taxon keys using
inline `curl | jq` loops. This is fragile, verbose, and leaks the plumbing into workflow scripts.
A dedicated `dwca-tools species` CLI command gives users a clean way to resolve names, inspect
backbone matches, and pipe the resolved keys directly into `dwca-tools download request`.

## New command surface

```
dwca-tools species resolve [NAMES_FILE]     # resolve names → backbone keys
dwca-tools species info <TAXON_KEY>         # show full taxon record for a single key
```

### `species resolve`

```
dwca-tools species resolve [NAMES_FILE]
  [--name "Burnsius communis"]     # single name (alternative to file)
  [--output-keys PATH]             # write resolved keys, one per line (deduped)
  [--all]                          # keep duplicate keys (synonyms → same accepted)
```

- NAMES_FILE: one name per line (same format as existing species list files)
- Uses `GET https://api.gbif.org/v1/species/match?name=...` per name (no auth needed)
- Rich table output columns: Verbatim Name | Accepted Name | Status | Match Type | Key
- Status styled: ACCEPTED=green, SYNONYM=yellow, DOUBTFUL=red
- Writes deduped taxon keys to --output-keys if given (ready for `download request`)
- No bulk API needed — the match endpoint is fast per-name; batch via file is sufficient

### `species info`

```
dwca-tools species info <TAXON_KEY>
```

- Uses `GET https://api.gbif.org/v1/species/<key>`
- Displays full record: kingdom, phylum, class, order, family, genus, rank, status, synonyms
- No auth required

## Implementation

### New file: `src/dwca_tools/species.py`

```python
app = typer.Typer(no_args_is_help=True)
GBIF_SPECIES_API = "https://api.gbif.org/v1/species"

def match_name(name: str) -> dict:
    """Call GBIF species/match API for one name."""
    resp = requests.get(f"{GBIF_SPECIES_API}/match", params={"name": name}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_species(key: int) -> dict:
    """Call GBIF species API for one taxon key."""
    resp = requests.get(f"{GBIF_SPECIES_API}/{key}", timeout=10)
    resp.raise_for_status()
    return resp.json()

@app.command()
def resolve(names_file, name, output_keys, all_keys): ...

@app.command()
def info(taxon_key): ...
```

### Wire into CLI: `src/dwca_tools/cli.py`

```python
from .species import app as species_app
app.add_typer(species_app, name="species", help="Look up taxa in the GBIF backbone")
```

### Update `scripts/tricky_species_comparison.sh`

Replace the `curl | jq` resolution loop with:
```bash
uv run dwca-tools species resolve "$TAXA_FILE" \
  --output-keys "$TAXA_KEYS_FILE"
```

## Rich table style

Follow `summarize.py` pattern (`Table`, `console.print`).

| Column        | Style   |
|---------------|---------|
| Verbatim Name | cyan    |
| Accepted Name | white   |
| Status        | green/yellow/red by value |
| Match Type    | dim     |
| Key           | dim     |

## Files to change

- **create** `src/dwca_tools/species.py`
- **edit** `src/dwca_tools/cli.py` — add `app.add_typer(species_app, ...)`
- **edit** `scripts/tricky_species_comparison.sh` — replace curl/jq loop

## Verification

```bash
uv run dwca-tools species --help
uv run dwca-tools species resolve reference/tricky_species.tsv
uv run dwca-tools species resolve reference/tricky_species.tsv --output-keys /tmp/keys.txt && cat /tmp/keys.txt
uv run dwca-tools species resolve --name "Burnsius communis"
uv run dwca-tools species info 1898286
make ci
```
