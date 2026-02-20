#!/usr/bin/env bash
# Vermont butterfly iNaturalist download workflow
#
# Downloads iNaturalist occurrences for a curated list of butterfly species:
#   Run 1: Vermont only (GADM geo filter)
#   Run 2: All locations (no geo filter)
#
# For each archive: summarize files, summarize taxa grouped by verbatim name
# with mismatch diagnostics, convert to SQLite, aggregate taxa table.
#
# Usage:
#   ./scripts/vermont_workflow.sh
#
# Requires: dwca-tools CLI, sqlite3
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
VT_GADM="USA.45_1"  # Vermont — verify: https://www.gbif.org/occurrence/search?gadmGid=USA.45_1
TAXA_FILE="scripts/vermont_species.txt"
POLL_INTERVAL=30  # seconds between GBIF status checks

mkdir -p data

# ── 1. Write taxa list ─────────────────────────────────────────────────────────

cat > "$TAXA_FILE" << 'EOF'
Coenonympha california
Lethe appalachia
Lethe anthedon
Lethe eurydice
Cercyonis pegala
Oeneis jutta
Megisto cymela
Euphydryas phaeton
Chlosyne nycteis
Chlosyne harrisii
Phyciodes cocyta
Phyciodes tharos
Polygonia interrogationis
Polygonia comma
Polygonia progne
Polygonia faunus
Junonia coenia
Aglais milberti
Nymphalis antiopa
Nymphalis californica
Nymphalis l-album
Asterocampa celtis
Asterocampa clyton
Vanessa cardui
Vanessa virginiensis
Vanessa atalanta
Speyeria cybele
Speyeria aphrodite
Speyeria idalia
Speyeria atlantis
Limenitis archippus
Limenitis arthemis
Boloria bellona
Euptoieta claudia
Danaus plexippus
Libytheana carinenta
Polyommatus icarus
Glaucopsyche lygdamus
Cupido comyntas
Erora laeta
Celastrina neglecta
Celastrina serotina
Celastrina lucia
Parrhasius m-album
Strymon melinus
Callophrys irus
Callophrys henrici
Callophrys niphon
Callophrys gryneus
Callophrys augustinus
Satyrium liparops
Satyrium calanus
Satyrium caryaevorus
Satyrium titus
Satyrium acadica
Feniseca tarquinius
Ancyloxypha numitor
Hylephila phyleus
Thymelicus lineola
Amblyscirtes hegon
Amblyscirtes vialis
Thorybes pylades
Urbanus proteus
Epargyreus clarus
Erynnis lucilius
Erynnis persius
Erynnis baptisiae
Erynnis horatius
Erynnis juvenalis
Erynnis icelus
Pholisora catullus
Atrytonopsis hianna
Euphyes vestris
Euphyes bimacula
Euphyes conspicua
Euphyes dion
Anatrytone logan
Poanes viator
Poanes massasoit
Polites mystic
Polites origenes
Polites themistocles
Hesperia leonardus
Hesperia metea
Hesperia sassacus
Pieris rapae
Pieris virginiensis
Pieris oleracea
Colias eurytheme
Colias philodice
Colias interior
Papilio polyxenes
Battus philenor
Phoebis sennae
Aglais io
Lycaena hypophlaeas
Tharsalea epixanthe
Tharsalea hyllus
Callophrys lanoraieensis
Burnsius communis
Carterocephalus mandan
Vernia verna
Lon hobomok
Polites egeremet
Polites coras
Boloria myrina
Phyciodes diminutor
Dione incarnata
Satyrium edwardsii
Hesperia colorado
Papilio troilus
Satyrium favonius
Atalopedes huron
Papilio solstitius
Papilio canadensis
Papiliio glaucus
Lon zabulon
Calycopis cecrops
Eurema lisa
Papilio cresphontes
EOF

echo "Wrote $(wc -l < "$TAXA_FILE") species to $TAXA_FILE"

# ── 2. Download: Vermont only (small) ─────────────────────────────────────────

echo ""
echo "=== Download 1: Vermont only (GADM: $VT_GADM) ==="
echo "  --match-names --dataset-key $DATASET_KEY --gadm-gid $VT_GADM"
gbif_download data/vermont_inat_vt.zip "$TAXA_FILE" \
  --match-names \
  --dataset-key "$DATASET_KEY" \
  --gadm-gid "$VT_GADM" \
  --poll-interval "$POLL_INTERVAL"

# ── 3. Summarize small file before starting the large download ─────────────────

echo ""
echo "=== Vermont only: archive files ==="
uv run dwca-tools summarize data/vermont_inat_vt.zip

echo ""
echo "=== Vermont only: taxa (verbatim names, mismatches) ==="
uv run dwca-tools summarize taxa data/vermont_inat_vt.zip \
  --group-by verbatimScientificName \
  --show-mismatched-names

# ── 4. Download: All locations (large) ────────────────────────────────────────

echo ""
echo "=== Download 2: All locations (no geo filter) ==="
echo "  --match-names --dataset-key $DATASET_KEY"
gbif_download data/vermont_inat_all.zip "$TAXA_FILE" \
  --match-names \
  --dataset-key "$DATASET_KEY" \
  --poll-interval "$POLL_INTERVAL"

# ── 5. Process both archives ───────────────────────────────────────────────────

process_archive() {
  local archive="$1"
  local label="$2"
  local db="${archive%.zip}.db"

  echo ""
  echo "════════════════════════════════════════"
  echo "  $label"
  echo "  Archive : $archive"
  echo "  Database: $db"
  echo "════════════════════════════════════════"

  echo ""
  echo "--- Summarize archive files ---"
  uv run dwca-tools summarize "$archive"

  echo ""
  echo "--- Taxa: verbatim names, occurrence & image counts, mismatch diagnostics ---"
  uv run dwca-tools summarize taxa "$archive" \
    --group-by verbatimScientificName \
    --show-mismatched-names

  # echo ""
  # echo "--- Convert to SQLite: $db ---"
  # uv run dwca-tools convert "$archive" --db-url "sqlite:///$db"

  # echo ""
  # echo "--- Aggregate taxa table ---"
  # uv run dwca-tools aggregate populate-taxa-table --db-url "sqlite:///$db"

  # echo ""
  # echo "--- Species summary (occurrences & images) ---"
  # sqlite3 -column -header "$db" \
  #   "SELECT scientificName, occurrences_count, multimedia_count
  #    FROM taxa
  #    ORDER BY scientificName;"
}

process_archive "data/vermont_inat_vt.zip"  "Vermont only (GADM: $VT_GADM)"
process_archive "data/vermont_inat_all.zip" "All locations"

echo ""
echo "Done. Output files:"
echo "  data/vermont_inat_vt.zip  / data/vermont_inat_vt.db"
echo "  data/vermont_inat_all.zip / data/vermont_inat_all.db"
