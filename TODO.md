# Download module TODOs

- [ ] Test `--match-names` with `--format SPECIES_LIST` — likely returns backbone-resolved names rather than verbatim names in the output species list. Verify and document the behavior.
- [ ] Add a command to extract a species list from a DwC-A's occurrence table, using verbatimScientificName, acceptedNameUsage, or other name fields (so the user controls which name column is used, rather than relying on GBIF's SPECIES_LIST format which goes through backbone resolution).
- [ ] Add image counts per species in the archive summary (join occurrence + multimedia tables by gbifID, group by species name).
