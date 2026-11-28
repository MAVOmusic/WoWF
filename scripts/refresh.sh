#!/usr/bin/env bash
# Rebuild the whole pipeline from the armory capture.
#   1. parse the raw armory capture  -> data/characters/*.json (+ items.json upsert)
#   2. rebuild the SQLite model     -> data/wowf.db
#   3. rebuild the Excel workbook   -> data/wowf.xlsx
#   4. compile the addon snapshot   -> addon/ForeverCompanion/Data.lua
#   5. package the addon            -> release/ForeverCompanion-<version>.zip
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-python3}"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi

echo "==> 1/5 parse armory capture"
"$PY" scripts/parse_armory.py "$@"

echo "==> 2/5 build database"
"$PY" scripts/build_db.py

echo "==> 3/5 export workbook"
"$PY" scripts/export_xlsx.py

echo "==> 4/5 compile addon data"
"$PY" scripts/build_addon_data.py

echo "==> 5/5 package addon zip"
"$PY" scripts/build_addon_zip.py

echo
echo "Reminder: append to docs/CHANGELOG.md and bump docs/VERSION.md if the model changed."
