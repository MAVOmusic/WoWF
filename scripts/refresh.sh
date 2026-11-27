#!/usr/bin/env bash
# Rebuild the whole pipeline from the armory capture.
#   1. parse the raw armory capture  -> data/characters/*.json (+ items.json upsert)
#   2. rebuild the SQLite model     -> data/wowf.db
#   3. rebuild the Excel workbook   -> data/wowf.xlsx
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-python3}"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi

echo "==> 1/3 parse armory capture"
"$PY" scripts/parse_armory.py "$@"

echo "==> 2/3 build database"
"$PY" scripts/build_db.py

echo "==> 3/3 export workbook"
"$PY" scripts/export_xlsx.py

echo
echo "Reminder: append to docs/CHANGELOG.md and bump docs/VERSION.md if the model changed."
