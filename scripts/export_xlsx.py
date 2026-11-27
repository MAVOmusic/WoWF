#!/usr/bin/env python3
"""Export data/wowf.db to data/wowf.xlsx (11 sheets).

Sheets with an unbroken blue header are editable in Excel; merge your edits back
with scripts/import_xlsx.py. Sheets with a grey header are generated — edits there
are overwritten on the next export.

Usage:
    python3 scripts/export_xlsx.py [--db PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.formatting.rule import CellIsRule
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required:  pip install -r requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx_columns import (  # noqa: E402
    EDITABLE, STATUS_VALUES, VERIFICATION_VALUES, fmt_num, stat_string,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "wowf.db"
DEFAULT_OUT = ROOT / "data" / "wowf.xlsx"

HEADER_FILL = PatternFill("solid", start_color="FF1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFFFF", size=11)
GEN_FILL = PatternFill("solid", start_color="FF595959")
SECTION_FILL = PatternFill("solid", start_color="FFD9E1F2")
SECTION_FONT = Font(bold=True, color="FF1F3864", size=12)
TITLE_FONT = Font(bold=True, size=16, color="FF1F3864")
WARN_FILL = PatternFill("solid", start_color="FFFCE4E4")
OK_FILL = PatternFill("solid", start_color="FFE2EFDA")
THIN = Side(style="thin", color="FFBFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def write_table(ws, headers, rows, editable=True, widths=None, start_row=1):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=c, value=h)
        cell.fill = HEADER_FILL if editable else GEN_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[start_row].height = 28
    for r, row in enumerate(rows, start_row + 1):
        for c, value in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=False)
    if rows:
        ws.auto_filter.ref = (
            f"A{start_row}:{get_column_letter(len(headers))}{start_row + len(rows)}"
        )
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    return start_row + len(rows)


def section(ws, row, text, span=8):
    cell = ws.cell(row=row, column=1, value=text)
    cell.fill = SECTION_FILL
    cell.font = SECTION_FONT
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    return row + 1


def build(db_path: Path = DEFAULT_DB, out_path: Path = DEFAULT_OUT) -> Path:
    if not db_path.exists():
        sys.exit(f"missing {db_path} — run scripts/build_db.py first")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731

    char = q("SELECT * FROM character LIMIT 1")[0]
    stats = q("SELECT * FROM character_stats LIMIT 1")[0]
    meta = {r["key"]: r["value"] for r in q("SELECT * FROM meta")}
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    wb = Workbook()

    # ------------------------------------------------------------------ Dashboard
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_properties.tabColor = "1F3864"
    ws["A1"] = f"{char['display_name']} — WoW Forever character mapping"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = (f"Level {char['level']} {char['faction']} {char['race']} {char['class']}"
                f" · Fury · {char['region'].upper()} · <{char['guild']}>")
    ws["A3"] = f"Excel rebuilt {built_at} · armory snapshot {char['fetched_at']}"
    ws["A3"].font = Font(italic=True, size=9, color="FF7F7F7F")

    r = 5
    r = section(ws, r, "Snapshot")
    facts = [
        ("Character key", char["character_key"]),
        ("Armory", char["source_url"]),
        ("Last online (armory)", char["last_online"]),
        ("Level", char["level"]),
        ("Item level (armory-reported)", char["item_level"]),
        ("Health / Armor / Attack power",
         f"{stats['health']} / {stats['armor']} / {stats['attack_power']}"),
        ("Strength / Agility / Stamina",
         f"{stats['strength']} / {stats['agility']} / {stats['stamina']}"),
        ("Melee crit / Parry / Dodge",
         f"{stats['melee_crit']}% / {stats['parry']}% / {stats['dodge']}%"),
        ("Professions",
         ", ".join(f"{p['profession']} {p['skill']}/{p['max_skill']}"
                   for p in q("SELECT * FROM character_profession"))),
    ]
    for k, v in facts:
        ws.cell(row=r, column=1, value=k).font = Font(bold=True)
        ws.cell(row=r, column=2, value=v)
        r += 1

    r += 1
    r = section(ws, r, "Do these next (priority 1-2)")
    rows = q("""SELECT priority, slot, target_item, target_source, zone, req_level, reason
                FROM upgrade_plan WHERE priority <= 2 AND status IN ('open','in_progress')
                ORDER BY priority, slot""")
    r = write_table(ws, ["Priority", "Slot", "Target", "How", "Zone", "Req Lvl", "Why"],
                    [[x["priority"], x["slot"], x["target_item"], x["target_source"],
                      x["zone"], x["req_level"], x["reason"]] for x in rows],
                    editable=False, start_row=r) + 2

    r = section(ws, r, "Empty slots")
    gaps = q("SELECT slot, item_name, state FROM v_slot_gaps WHERE state = 'EMPTY'")
    r = write_table(ws, ["Slot", "Item"], [[g["slot"], g["item_name"] or "—"] for g in gaps],
                    editable=False, start_row=r,
                    widths=None) + 2

    r = section(ws, r, "Where to farm right now (level band)")
    lvl = char["level"] or 1
    zones = q("""SELECT name, level_min, level_max, faction, mining_nodes, best_for
                 FROM zone WHERE level_min - 3 <= ? AND level_max + 5 >= ?
                 AND mining_nodes <> 'none' ORDER BY level_min""", lvl, lvl)
    r = write_table(ws, ["Zone", "Levels", "Faction", "Mining", "Best for"],
                    [[z["name"], f"{z['level_min']}-{z['level_max']}", z["faction"],
                      z["mining_nodes"], z["best_for"]] for z in zones],
                    editable=False, start_row=r) + 2

    r = section(ws, r, "Professions — next step")
    profs = q("""SELECT p.profession, p.skill, p.max_skill, pp.next_action, pp.verification
                 FROM character_profession p
                 LEFT JOIN profession_plan pp ON pp.profession = p.profession
                 ORDER BY p.skill DESC""")
    r = write_table(ws, ["Profession", "Skill", "Next action", "Trust"],
                    [[p["profession"], f"{p['skill']}/{p['max_skill']}",
                      p["next_action"] or "", p["verification"] or ""] for p in profs],
                    editable=False, start_row=r) + 2

    r = section(ws, r, "How to read this file")
    notes = [
        "Blue header = editable: Items, FarmSources, Zones, UpgradePlan, ProfessionPlan. "
        "Edit away, then run: python3 scripts/import_xlsx.py",
        "Grey header = generated from the DB. Edits there are lost on the next export.",
        f"Verification: armory (read off the armory) / classic (general Classic-Era "
        f"knowledge, NOT confirmed on WoW Forever) / confirmed / todo.",
        f"Workbook rebuilt from {meta.get('json_authoritative', 'JSON')} via "
        f"scripts/build_db.py + export_xlsx.py.",
    ]
    for n in notes:
        ws.cell(row=r, column=1, value="•")
        ws.cell(row=r, column=2, value=n).alignment = Alignment(wrap_text=False)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        wx = ws.column_dimensions
        wx["A"].width = 26
        wx["B"].width = 52
        r += 1
    for col, w in {"C": 16, "D": 22, "E": 30, "F": 10, "G": 60, "H": 14}.items():
        ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------ Character
    ws = wb.create_sheet("Character")
    ws.sheet_properties.tabColor = "7F7F7F"
    rows = [[k, char[k]] for k in char.keys()]
    write_table(ws, ["Field", "Value"], rows, editable=False, widths=[26, 60])

    # ------------------------------------------------------------------ Stats
    ws = wb.create_sheet("Stats")
    ws.sheet_properties.tabColor = "7F7F7F"
    rows = [[k, stats[k]] for k in stats.keys()]
    write_table(ws, ["Stat", "Value"], rows, editable=False, widths=[26, 16])
    ws.cell(row=len(rows) + 3, column=1,
            value="Equipped-gear stat totals (sum of item stats, not character sheet):")
    ws.cell(row=len(rows) + 3, column=1).font = Font(bold=True)
    start = len(rows) + 4
    totals = q("SELECT stat, total, items FROM v_equipped_stat_totals")
    write_table(ws, ["Stat", "Total on gear", "Items"],
                [[t["stat"], t["total"], t["items"]] for t in totals],
                editable=False, start_row=start)

    # ------------------------------------------------------------------ Equipment
    ws = wb.create_sheet("Equipment")
    ws.sheet_properties.tabColor = "7F7F7F"
    eq = q("""SELECT g.slot, g.item_name, g.item_key, g.armor, g.req_level, g.subclass,
                     g.state, e.durability, e.durability_max, i.verification
              FROM v_slot_gaps g
              LEFT JOIN character_equipment e ON e.slot = g.slot
              LEFT JOIN item i ON i.item_key = g.item_key""")
    plan_by_slot = {p["slot"]: p for p in q(
        "SELECT slot, target_item, target_source, priority FROM upgrade_plan")}
    stat_cache = {}
    for row in q("SELECT item_key, stat, value FROM item_stat"):
        stat_cache.setdefault(row["item_key"], []).append(
            f"{row['stat']}+{fmt_num(row['value'])}")
    rows = []
    for e in eq:
        stats_txt = " ".join(stat_cache.get(e["item_key"], [])) if e["item_key"] else ""
        plan = plan_by_slot.get(e["slot"])
        rows.append([e["slot"], e["item_name"] or "EMPTY", e["subclass"], e["armor"],
                     e["req_level"], stats_txt,
                     f"{e['durability']}/{e['durability_max']}"
                     if e["durability"] is not None else "",
                     e["verification"] or "",
                     plan["target_item"] if plan else "",
                     plan["priority"] if plan else ""])
    write_table(ws, ["Slot", "Equipped", "Type", "Armor", "Req Lvl", "Stats",
                     "Durability", "Trust", "Planned upgrade", "Prio"], rows,
                editable=False, widths=[12, 34, 18, 8, 9, 34, 11, 9, 32, 6])
    ws.conditional_formatting.add(
        f"B2:B{len(rows) + 1}",
        CellIsRule(operator="equal", formula=['"EMPTY"'], fill=WARN_FILL))

    # ------------------------------------------------------------------ Talents
    ws = wb.create_sheet("Talents")
    ws.sheet_properties.tabColor = "7F7F7F"
    t = q("SELECT tree, talent_name, talent_id, rank, max_rank FROM character_talent "
          "ORDER BY CASE tree WHEN 'Arms' THEN 1 WHEN 'Fury' THEN 2 ELSE 3 END, talent_name")
    write_table(ws, ["Tree", "Talent", "Talent ID", "Rank", "Max"],
                [[x["tree"], x["talent_name"], x["talent_id"], x["rank"], x["max_rank"]]
                 for x in t], editable=False, widths=[12, 34, 12, 7, 6])
    pts = q("SELECT tree, SUM(rank) AS pts FROM character_talent GROUP BY tree")
    start = len(t) + 4
    write_table(ws, ["Tree", "Points spent"],
                [[p["tree"], p["pts"]] for p in pts], editable=False, start_row=start)

    # ------------------------------------------------------------------ Professions
    ws = wb.create_sheet("Professions")
    ws.sheet_properties.tabColor = "7F7F7F"
    p = q("""SELECT cp.profession, cp.skill, cp.max_skill, pp.band, pp.next_action,
                    pp.materials, pp.zone, pp.verification
             FROM character_profession cp
             LEFT JOIN profession_plan pp ON pp.profession = cp.profession
             ORDER BY cp.skill DESC""")
    write_table(ws, ["Profession", "Skill", "Cap", "Band", "Next action", "Materials",
                     "Zone", "Trust"],
                [[x["profession"], x["skill"], x["max_skill"], x["band"],
                  x["next_action"], x["materials"], x["zone"], x["verification"]]
                 for x in p], editable=False,
                widths=[16, 8, 8, 30, 70, 34, 30, 10])

    # ------------------------------------------------------------------ Items
    ws = wb.create_sheet("Items")
    ws.sheet_properties.tabColor = "2E75B6"
    cols = EDITABLE["Items"]
    rows = []
    for it in q("SELECT * FROM item ORDER BY "
                "CASE WHEN slot = 'material' THEN 2 ELSE 1 END, slot, name"):
        stats_txt = stat_string({r["stat"]: r["value"]
                                 for r in q("SELECT stat, value FROM item_stat "
                                            "WHERE item_key = ?", it["item_key"])})
        rows.append([stats_txt if f == "stats" else it[f] for f, _ in cols])
    write_table(ws, [h for _, h in cols], rows, editable=True,
                widths=[30, 34, 8, 11, 12, 16, 8, 8, 40, 8, 8, 8, 8, 7, 7, 14, 46, 22, 11, 60])
    dv = DataValidation(type="list", formula1='"' + ",".join(VERIFICATION_VALUES) + '"',
                        allow_blank=True)
    ws.add_data_validation(dv)
    vcol = [h for _, h in cols].index("Verification") + 1
    dv.add(f"{get_column_letter(vcol)}2:{get_column_letter(vcol)}{len(rows) + 1}")

    # ------------------------------------------------------------------ FarmSources
    ws = wb.create_sheet("FarmSources")
    ws.sheet_properties.tabColor = "2E75B6"
    cols = EDITABLE["FarmSources"]
    rows = [[x[f] for f, _ in cols] for x in q(
        "SELECT * FROM farm_source ORDER BY source_type, zone, source_key")]
    write_table(ws, [h for _, h in cols], rows, editable=True,
                widths=[28, 26, 12, 24, 26, 26, 11, 12, 30, 11, 70])

    # ------------------------------------------------------------------ Zones
    ws = wb.create_sheet("Zones")
    ws.sheet_properties.tabColor = "2E75B6"
    cols = EDITABLE["Zones"]
    rows = [[x[f] for f, _ in cols] for x in q("SELECT * FROM zone ORDER BY level_min, name")]
    write_table(ws, [h for _, h in cols], rows, editable=True,
                widths=[24, 26, 20, 8, 8, 12, 34, 40, 44, 60, 11])

    # ------------------------------------------------------------------ UpgradePlan
    ws = wb.create_sheet("UpgradePlan")
    ws.sheet_properties.tabColor = "2E75B6"
    cols = EDITABLE["UpgradePlan"]
    rows = [[x[f] for f, _ in cols] for x in q(
        "SELECT * FROM upgrade_plan ORDER BY priority, slot")]
    write_table(ws, [h for _, h in cols], rows, editable=True,
                widths=[30, 9, 12, 30, 34, 22, 34, 8, 62, 12, 10, 46])
    sc = [h for _, h in cols].index("Status") + 1
    dv2 = DataValidation(type="list", formula1='"' + ",".join(STATUS_VALUES) + '"',
                         allow_blank=True)
    ws.add_data_validation(dv2)
    dv2.add(f"{get_column_letter(sc)}2:{get_column_letter(sc)}{len(rows) + 1}")
    ws.conditional_formatting.add(
        f"J2:J{len(rows) + 1}",
        CellIsRule(operator="equal", formula=['"done"'], fill=OK_FILL))
    ws.conditional_formatting.add(
        f"J2:J{len(rows) + 1}",
        CellIsRule(operator="equal", formula=['"skipped"'], fill=WARN_FILL))

    # ------------------------------------------------------------------ ProfessionPlan
    ws = wb.create_sheet("ProfessionPlan")
    ws.sheet_properties.tabColor = "2E75B6"
    cols = EDITABLE["ProfessionPlan"]
    rows = [[x[f] for f, _ in cols] for x in q(
        "SELECT * FROM profession_plan ORDER BY priority, profession")]
    write_table(ws, [h for _, h in cols], rows, editable=True,
                widths=[16, 8, 8, 32, 70, 40, 34, 8, 10, 50])

    # ------------------------------------------------------------------ History
    ws = wb.create_sheet("History")
    ws.sheet_properties.tabColor = "7F7F7F"
    snaps = q("SELECT fetched_at, level, item_level, equipped_count, source, notes "
              "FROM snapshot ORDER BY fetched_at")
    write_table(ws, ["Armory snapshot", "Level", "Item level (reported)",
                     "Equipped pieces", "Source", "Notes"],
                [[s["fetched_at"], s["level"], s["item_level"], s["equipped_count"],
                  s["source"], s["notes"]] for s in snaps],
                editable=False, widths=[24, 8, 20, 16, 60, 30])
    start = len(snaps) + 4
    write_table(ws, ["Build metadata", "Value"], [[k, v] for k, v in sorted(meta.items())],
                editable=False, start_row=start, widths=[26, 60])
    ws.cell(row=start + len(meta) + 3, column=1,
            value="Full narrative history lives in docs/CHANGELOG.md and docs/VERSION.md.")

    con.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = build(args.db, args.out)
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
