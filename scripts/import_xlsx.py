#!/usr/bin/env python3
"""Merge edits from data/wowf.xlsx back into the canonical JSON files.

Only the five blue-header sheets are read: Items, FarmSources, Zones,
UpgradePlan, ProfessionPlan. Rows are matched on their key column and updated
field by field; rows you deleted in Excel are kept in JSON and reported (use
--prune to drop them). Run it with --dry-run first if you want to see the diff.

Usage:
    python3 scripts/import_xlsx.py [--xlsx PATH] [--dry-run] [--prune]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required:  pip install -r requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonio  # noqa: E402
from xlsx_columns import (  # noqa: E402
    EDITABLE, NUMERIC_FIELDS, SHEET_TARGETS, parse_stat_string,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XLSX = ROOT / "data" / "wowf.xlsx"


def clean(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def coerce(field: str, value):
    value = clean(value)
    if value is None:
        return None
    if field in NUMERIC_FIELDS:
        try:
            num = float(value)
            return int(num) if num.is_integer() else num
        except (TypeError, ValueError):
            return None
    if field in ("priority", "current", "cap", "level_min", "level_max", "req_level",
                 "item_id", "armor", "sell_copper", "weapon_min", "weapon_max"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return value


def read_sheet(ws, sheet: str) -> tuple[list[dict], list[str]]:
    cols = EDITABLE[sheet]
    header = [clean(c.value) for c in ws[1]]
    header_map = {h: i for i, h in enumerate(header) if h}
    missing = [h for _, h in cols if h not in header_map]
    if missing:
        return [], missing
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(v not in (None, "") for v in row):
            continue
        record = {}
        for field, h in cols:
            idx = header_map[h]
            record[field] = row[idx] if idx < len(row) else None
        rows.append(record)
    return rows, []


def same(old, new) -> bool:
    """Treat blank-cell None as equal to '' or {} so round-trips don't churn."""
    if old == new:
        return True
    if new is None and old in ("", {}, []):
        return True
    if old is None and new in ("", {}, []):
        return True
    return False


def merge(sheet: str, records: list[dict], prune: bool) -> dict:
    rel_path, collection, key_field = SHEET_TARGETS[sheet]
    path = ROOT / rel_path
    doc = json.loads(path.read_text(encoding="utf-8"))
    existing = doc.get(collection, [])
    index = {str(e.get(key_field)): e for e in existing}

    added = updated = 0
    changed_fields: list[str] = []
    seen = set()

    for rec in records:
        key = clean(rec.get(key_field))
        if key is None:
            continue
        key = str(key)
        seen.add(key)
        # normalise values
        new = {}
        for field, _ in EDITABLE[sheet]:
            if field == "stats":
                continue
            new[field] = coerce(field, rec.get(field))
        if sheet == "Items":
            stats = parse_stat_string(rec.get("stats"))
            if stats:
                new["stats"] = stats

        if key not in index:
            item = {k: v for k, v in new.items() if v is not None}
            item[key_field] = key
            existing.append(item)
            index[key] = item
            added += 1
            changed_fields.append(f"{sheet}: +{key}")
            continue

        target = index[key]
        diff = [f for f, v in new.items() if not same(target.get(f), v)]
        if diff:
            for f in diff:
                target[f] = new[f]
            updated += 1
            changed_fields.append(f"{sheet}: {key} ({', '.join(diff)})")

    pruned = []
    if prune:
        for key in list(index):
            if key not in seen:
                existing.remove(index.pop(key))
                pruned.append(key)

    if added or updated or pruned:
        doc[collection] = existing
        path.write_text(jsonio.dump(doc), encoding="utf-8")

    return {"sheet": sheet, "added": added, "updated": updated,
            "pruned": pruned, "changes": changed_fields,
            "orphans": [k for k in index if k not in seen]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune", action="store_true")
    args = ap.parse_args()

    if not args.xlsx.exists():
        sys.exit(f"missing workbook: {args.xlsx}")
    wb = load_workbook(args.xlsx, data_only=True)

    results = []
    for sheet in EDITABLE:
        if sheet not in wb.sheetnames:
            print(f"  ! sheet '{sheet}' not found — skipped")
            continue
        records, missing = read_sheet(wb[sheet], sheet)
        if missing:
            print(f"  ! '{sheet}' is missing columns: {', '.join(missing)} — skipped")
            continue
        if args.dry_run:
            results.append({"sheet": sheet, "added": 0, "updated": 0,
                            "pruned": [], "changes": [f"(dry-run) {len(records)} rows read"],
                            "orphans": []})
            continue
        results.append(merge(sheet, records, args.prune))

    total = sum(r["added"] + r["updated"] for r in results)
    for r in results:
        print(f"{r['sheet']:<15} +{r['added']} new, {r['updated']} updated"
              + (f", {len(r['pruned'])} pruned" if r["pruned"] else ""))
        for c in r["changes"][:40]:
            print(f"    {c}")
        if len(r["changes"]) > 40:
            print(f"    ... {len(r['changes']) - 40} more")
        if r["orphans"]:
            print(f"    kept (not in sheet): {', '.join(r['orphans'])}")

    if args.dry_run:
        print("\nDry run — nothing written. Re-run without --dry-run to apply.")
        return
    if not total:
        print("\nNo changes detected — JSON untouched.")
        return
    print(f"\nMerged {total} row change(s) into JSON.")
    print("Next: python3 scripts/build_db.py && python3 scripts/export_xlsx.py")
    print("(or: bash scripts/refresh.sh)")


if __name__ == "__main__":
    main()
