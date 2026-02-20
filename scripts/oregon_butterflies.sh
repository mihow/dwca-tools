#!/usr/bin/env bash
# Oregon butterfly download workflow
#
# Downloads all butterfly occurrences from iNaturalist for Oregon, then
# summarizes the archive and shows taxa grouped by verbatim name with
# mismatch diagnostics.
#
# GBIF does not support superfamily-level filtering, so all 7 butterfly
# families are specified by GBIF taxon key (reference/gbif_taxon_keys.txt).
#
# Usage:
#   ./scripts/oregon_butterflies.sh
#
# Requires: dwca-tools CLI
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

DATASET_KEY=$(awk 'NF && !/^#/ {print $1; exit}' reference/gbif_datasets.txt)
OR_GADM="USA.38_1"  # Oregon — verify: https://www.gbif.org/occurrence/search?gadmGid=USA.38_1

TAXA_FILE="scripts/oregon_butterfly_taxon_keys.txt"
OUT_ARCHIVE="data/oregon_butterflies_inat.zip"
POLL_INTERVAL=30

mkdir -p data

# ── 1. Build taxon key file from reference ─────────────────────────────────────

echo "Building taxon key list from reference/gbif_taxon_keys.txt..."

awk 'NF && !/^#/ && $2 == "FAMILY" {print $1}' reference/gbif_taxon_keys.txt \
  > "$TAXA_FILE"

echo "Taxon keys:"
paste "$TAXA_FILE" \
  <(awk 'NF && !/^#/ && $2 == "FAMILY" {print $3}' reference/gbif_taxon_keys.txt) \
  | column -t -s $'\t'

# ── 2. Download from GBIF ──────────────────────────────────────────────────────
#
# No --match-names: file contains GBIF TAXON_KEYs. GBIF resolves each family
# key to all descendant species in the occurrence index.

echo ""
echo "=== Downloading Oregon butterflies from iNaturalist ==="
echo "  --dataset-key $DATASET_KEY --gadm-gid $OR_GADM"
echo ""

gbif_download "$OUT_ARCHIVE" "$TAXA_FILE" \
  --dataset-key "$DATASET_KEY" \
  --gadm-gid "$OR_GADM" \
  --poll-interval "$POLL_INTERVAL"

# ── 3. Summarize archive files ─────────────────────────────────────────────────

echo ""
echo "=== Archive summary ==="
uv run dwca-tools summarize "$OUT_ARCHIVE"

# ── 4. Taxa: verbatim names, occurrence & image counts, mismatch diagnostics ───

echo ""
echo "=== Taxa summary ==="
uv run dwca-tools summarize taxa "$OUT_ARCHIVE" \
  --group-by verbatimScientificName \
  --show-mismatched-names

echo ""
echo "Done. Archive: $OUT_ARCHIVE"
