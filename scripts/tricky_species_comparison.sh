#!/usr/bin/env bash
# Backbone resolution comparison: verbatim vs. GBIF backbone name matching
#
# Uses reference/tricky_species.tsv — a curated list of names with known
# backbone resolution issues (synonyms, genus transfers) — to show the
# difference between:
#
#   Run 1 (verbatim): --match-names  →  searches VERBATIM_SCIENTIFIC_NAME
#   Run 2 (backbone): no flag        →  names resolved to GBIF TAXON_KEYs first
#
# Uses --format SPECIES_LIST (small CSV, no DwC-A overhead). To switch to
# full DwC-A with a North America geo filter instead, comment out the
# SPECIES_LIST lines and uncomment the DwC-A block below.
#
# Usage:
#   ./scripts/tricky_species_comparison.sh
#
# Requires: dwca-tools CLI, curl, jq, python3
# GBIF credentials: GBIF_USERNAME, GBIF_PASSWORD, GBIF_EMAIL (env or .env)

set -euo pipefail

# Skip the GBIF request/download if the output file already exists.
gbif_download() {
  local output="$1"; shift
  if [[ -f "$output" ]]; then
    echo "  Skipping download — $output already exists"
  else
    uv run dwca-tools download request "$@" --output "$output"
  fi
}

TAXA_FILE="reference/tricky_species.tsv"
TAXA_KEYS_FILE="scripts/tricky_species_taxon_keys.txt"
POLL_INTERVAL=30

mkdir -p data

# ── 1. Resolve names to GBIF backbone taxon keys ──────────────────────────────

echo "Resolving names to GBIF backbone taxon keys..."

> "$TAXA_KEYS_FILE"

while IFS= read -r name || [[ -n "$name" ]]; do
  [[ -z "$name" ]] && continue
  encoded=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$name")
  result=$(curl -sf "https://api.gbif.org/v1/species/match?name=$encoded")
  key=$(echo "$result" | jq '.usageKey')
  matched=$(echo "$result" | jq -r '.canonicalName // "?"')
  mtype=$(echo "$result" | jq -r '.matchType')
  tax_status=$(echo "$result" | jq -r '.status // "?"')
  if [ -z "$key" ] || [ "$key" = "null" ]; then
    echo "  WARNING: no backbone match for '$name'" >&2
  elif [ "$tax_status" = "SYNONYM" ]; then
    accepted_key=$(echo "$result" | jq -r '.acceptedUsageKey // empty')
    if [ -n "$accepted_key" ]; then
      accepted_result=$(curl -sf "https://api.gbif.org/v1/species/$accepted_key")
      accepted_name=$(echo "$accepted_result" | jq -r '.canonicalName // "?"')
      echo "  $name  →  $matched  [SYNONYM of $accepted_name, $mtype, key: $accepted_key]"
      echo "$accepted_key" >> "$TAXA_KEYS_FILE"
    else
      echo "  $name  →  $matched  [$tax_status, $mtype, key: $key]"
      echo "$key" >> "$TAXA_KEYS_FILE"
    fi
  else
    echo "  $name  →  $matched  [$tax_status, $mtype, key: $key]"
    echo "$key" >> "$TAXA_KEYS_FILE"
  fi
done < "$TAXA_FILE"

# Deduplicate: synonyms often resolve to the same accepted name
sort -u "$TAXA_KEYS_FILE" -o "$TAXA_KEYS_FILE"
echo "Resolved $(wc -l < "$TAXA_KEYS_FILE") unique taxon keys (from $(grep -c . "$TAXA_FILE") names)"

# ── 2. Download: verbatim name search ─────────────────────────────────────────

echo ""
echo "=== Download 1: verbatim (--match-names, SPECIES_LIST) ==="
echo "  Predicate key: VERBATIM_SCIENTIFIC_NAME"
gbif_download data/tricky_verbatim_species.zip "$TAXA_FILE" \
  --match-names \
  --format SPECIES_LIST \
  --poll-interval "$POLL_INTERVAL"

# -- DwC-A alternative (comment out SPECIES_LIST block above and uncomment):
# uv run dwca-tools download request "$TAXA_FILE" \
#   --match-names \
#   --predicate reference/predicate_north_america.json \
#   --output data/tricky_verbatim.zip \
#   --poll-interval "$POLL_INTERVAL"

# ── 3. Download: backbone taxon key search ────────────────────────────────────

echo ""
echo "=== Download 2: backbone (taxon keys, SPECIES_LIST) ==="
echo "  Predicate key: TAXON_KEY (resolved via GBIF species/match API)"
gbif_download data/tricky_backbone_species.zip "$TAXA_KEYS_FILE" \
  --format SPECIES_LIST \
  --poll-interval "$POLL_INTERVAL"

# -- DwC-A alternative:
# uv run dwca-tools download request "$TAXA_KEYS_FILE" \
#   --predicate reference/predicate_north_america.json \
#   --output data/tricky_backbone.zip \
#   --poll-interval "$POLL_INTERVAL"

# ── 4. Show species list results ───────────────────────────────────────────────
#
# SPECIES_LIST is a CSV, not a DwC-A, so we display it directly.
# For DwC-A output use: dwca-tools summarize taxa <archive>
#   --group-by verbatimScientificName --show-mismatched-names

show_species_list() {
  local archive="$1"
  local label="$2"

  echo ""
  echo "════════════════════════════════════════"
  echo "  $label"
  echo "  Archive: $archive"
  echo "════════════════════════════════════════"
  unzip -p "$archive" | column -t -s $'\t'
}

show_species_list "data/tricky_verbatim_species.zip" "Verbatim (VERBATIM_SCIENTIFIC_NAME)"
show_species_list "data/tricky_backbone_species.zip" "Backbone (TAXON_KEY)"

echo ""
echo "Done."
echo "  data/tricky_verbatim_species.zip  — verbatim name matches"
echo "  data/tricky_backbone_species.zip  — backbone-resolved taxon key matches"
