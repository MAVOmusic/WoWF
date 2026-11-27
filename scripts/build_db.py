#!/usr/bin/env python3
"""Build data/wowf.db from the canonical JSON files.

JSON is authoritative. This script never writes JSON, and nothing else should
hand-edit the database.

Usage:
    python3 scripts/build_db.py [--db PATH] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sql" / "schema.sql"
CHARACTER_JSON = ROOT / "data" / "characters" / "us" / "mavo-music.json"
ITEMS_JSON = ROOT / "data" / "catalog" / "items.json"
SOURCES_JSON = ROOT / "data" / "catalog" / "sources.json"
ZONES_JSON = ROOT / "data" / "catalog" / "zones.json"
PLAN_JSON = ROOT / "data" / "catalog" / "upgrade_plan.json"
PROF_JSON = ROOT / "data" / "catalog" / "profession_plan.json"
DEFAULT_DB = ROOT / "data" / "wowf.db"


def load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"missing input: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def build(db_path: Path = DEFAULT_DB, quiet: bool = False) -> dict:
    char_doc = load(CHARACTER_JSON)
    items_doc = load(ITEMS_JSON)
    sources_doc = load(SOURCES_JSON)
    zones_doc = load(ZONES_JSON)
    plan_doc = load(PLAN_JSON)
    prof_doc = load(PROF_JSON)

    items_by_key = {i["item_key"]: i for i in items_doc["items"]}
    char = char_doc["character"]

    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con.executemany("INSERT INTO meta(key, value) VALUES (?, ?)", [
        ("built_at", built_at),
        ("character_key", char["key"]),
        ("schema_version", str(char_doc.get("schema_version", 1))),
        ("json_authoritative", "data/characters + data/catalog"),
    ])

    con.execute(
        """INSERT INTO character (character_key, first_name, last_name, display_name,
               region, game_mode, realm_type, faction, race, class, level, guild,
               guild_slug, last_online, item_level, source_url, fetched_at, verification)
           VALUES (:key,:first_name,:last_name,:display_name,:region,:game_mode,
               :realm_type,:faction,:race,:class,:level,:guild,:guild_slug,
               :last_online,:item_level,:source_url,:fetched_at,:verification)""",
        char,
    )

    s = char_doc.get("stats", {})
    con.execute(
        """INSERT INTO character_stats (character_key, health, resource_type, resource,
               strength, agility, stamina, intellect, spirit, armor, attack_power,
               spell_power, melee_crit, ranged_crit, spell_crit, dodge, parry, block)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (char["key"], s.get("health"), s.get("resource_type"), s.get("resource"),
         s.get("strength"), s.get("agility"), s.get("stamina"), s.get("intellect"),
         s.get("spirit"), s.get("armor"), s.get("attack_power"), s.get("spell_power"),
         s.get("melee_crit"), s.get("ranged_crit"), s.get("spell_crit"),
         s.get("dodge"), s.get("parry"), s.get("block")),
    )

    # ---- items + per-item stats -------------------------------------------
    for item in items_doc["items"]:
        con.execute(
            """INSERT INTO item (item_key, name, item_id, slot, item_type, subclass,
                   req_level, armor, bind_type, quality, sell_copper, weapon_min,
                   weapon_max, weapon_speed, weapon_dps, source_type, source_detail,
                   zone, verification, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item.get("item_key"), item.get("name"), item.get("item_id"), item.get("slot"),
             item.get("item_type"), item.get("subclass"), item.get("req_level"),
             item.get("armor"), item.get("bind_type"), item.get("quality"),
             item.get("sell_copper"), item.get("weapon_min"), item.get("weapon_max"),
             item.get("weapon_speed"), item.get("weapon_dps"), item.get("source_type"),
             item.get("source_detail"), item.get("zone"),
             item.get("verification", "todo"), item.get("notes")),
        )
        for stat, value in (item.get("stats") or {}).items():
            con.execute(
                "INSERT INTO item_stat(item_key, stat, value) VALUES (?,?,?)",
                (item["item_key"], stat, value),
            )

    # ---- equipment --------------------------------------------------------
    for eq in char_doc.get("equipment", []):
        key = eq.get("item_key")
        if key and key not in items_by_key:
            sys.exit(f"equipment references unknown item_key: {key}")
        con.execute(
            """INSERT INTO character_equipment (character_key, slot, item_key,
                   durability, durability_max) VALUES (?,?,?,?,?)""",
            (char["key"], eq["slot"], key, eq.get("durability"), eq.get("durability_max")),
        )

    # ---- talents / professions -------------------------------------------
    for tree, talents in char_doc.get("talents", {}).get("trees", {}).items():
        for t in talents:
            con.execute(
                """INSERT INTO character_talent (character_key, tree, talent_name,
                       talent_id, rank, max_rank) VALUES (?,?,?,?,?,?)""",
                (char["key"], tree, t["name"], t.get("id"), t["rank"], t["max_rank"]),
            )

    for p in char_doc.get("professions", []):
        con.execute(
            """INSERT INTO character_profession (character_key, profession, skill,
                   max_skill) VALUES (?,?,?,?)""",
            (char["key"], p["name"], p.get("skill"), p.get("max_skill")),
        )

    # ---- farm sources -----------------------------------------------------
    for src in sources_doc["sources"]:
        key = src.get("item_key")
        if key and key not in items_by_key:
            sys.exit(f"source {src['source_key']} references unknown item_key: {key}")
        con.execute(
            """INSERT INTO farm_source (source_key, item_key, source_type, zone, subzone,
                   mob, mob_level, drop_rate, requirement, verification, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (src["source_key"], key, src.get("source_type"), src.get("zone"),
             src.get("subzone"), src.get("mob"), src.get("mob_level"),
             src.get("drop_rate"), src.get("requirement"),
             src.get("verification", "todo"), src.get("notes")),
        )

    # ---- zones ------------------------------------------------------------
    for z in zones_doc["zones"]:
        con.execute(
            """INSERT INTO zone (zone_key, name, continent, level_min, level_max,
                   faction, mining_nodes, herbs, best_for, notes, verification)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (z["zone_key"], z["name"], z.get("continent"), z.get("level_min"),
             z.get("level_max"), z.get("faction"), z.get("mining_nodes"),
             z.get("herbs"), z.get("best_for"), z.get("notes"),
             z.get("verification", "classic")),
        )

    # ---- upgrade plan -----------------------------------------------------
    for p in plan_doc["plans"]:
        con.execute(
            """INSERT INTO upgrade_plan (plan_key, priority, slot, current_item,
                   target_item, target_source, zone, req_level, reason, status,
                   verification, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p["plan_key"], p["priority"], p.get("slot"), p.get("current_item"),
             p.get("target_item"), p.get("target_source"), p.get("zone"),
             p.get("req_level"), p.get("reason"), p.get("status", "open"),
             p.get("verification", "classic"), p.get("notes")),
        )

    # ---- profession plan ------------------------------------------------
    for p in prof_doc["professions"]:
        con.execute(
            """INSERT INTO profession_plan (profession, current, cap, band, next_action,
                   materials, zone, priority, verification, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (p["profession"], p.get("current"), p.get("cap"), p.get("band"),
             p.get("next_action"), p.get("materials"), p.get("zone"),
             p.get("priority"), p.get("verification", "classic"), p.get("notes")),
        )

    # ---- snapshot history -------------------------------------------------
    equipped = sum(1 for e in char_doc.get("equipment", []) if e.get("item_key"))
    con.execute("DELETE FROM snapshot WHERE character_key = ? AND fetched_at = ?",
                (char["key"], char["fetched_at"]))
    con.execute(
        """INSERT INTO snapshot (character_key, fetched_at, level, item_level,
               equipped_count, source, notes) VALUES (?,?,?,?,?,?,?)""",
        (char["key"], char["fetched_at"], char.get("level"), char.get("item_level"),
         equipped, char.get("source_url"), "built from JSON"),
    )

    con.commit()

    summary = {
        "db": str(db_path),
        "built_at": built_at,
        "items": con.execute("SELECT COUNT(*) FROM item").fetchone()[0],
        "equipment_slots": con.execute("SELECT COUNT(*) FROM character_equipment").fetchone()[0],
        "equipped": equipped,
        "sources": con.execute("SELECT COUNT(*) FROM farm_source").fetchone()[0],
        "zones": con.execute("SELECT COUNT(*) FROM zone").fetchone()[0],
        "plans": con.execute("SELECT COUNT(*) FROM upgrade_plan").fetchone()[0],
        "prof_plan": con.execute("SELECT COUNT(*) FROM profession_plan").fetchone()[0],
        "talents": con.execute("SELECT COUNT(*) FROM character_talent").fetchone()[0],
        "professions": con.execute("SELECT COUNT(*) FROM character_profession").fetchone()[0],
        "snapshots": con.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0],
        "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
    }
    con.close()

    if not quiet:
        for k, v in summary.items():
            print(f"  {k:<16} {v}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    print(f"Building {args.db.relative_to(ROOT) if args.db.is_relative_to(ROOT) else args.db}")
    build(args.db, args.quiet)


if __name__ == "__main__":
    main()
