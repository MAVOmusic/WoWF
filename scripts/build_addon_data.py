#!/usr/bin/env python3
"""Compile the repo's JSON model into addon/ForeverCompanion/Data.lua.

The addon ships a read-only snapshot so it works with zero API dependency:
game data feeds the "live" side, this file feeds the "plan" side.

Run after any data change:  python3 scripts/build_addon_data.py
(it is also the last step of scripts/refresh.sh)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARACTER = ROOT / "data" / "characters" / "us" / "mavo-music.json"
ITEMS = ROOT / "data" / "catalog" / "items.json"
SOURCES = ROOT / "data" / "catalog" / "sources.json"
ZONES = ROOT / "data" / "catalog" / "zones.json"
PLAN = ROOT / "data" / "catalog" / "upgrade_plan.json"
PROF_PLAN = ROOT / "data" / "catalog" / "profession_plan.json"
OUT = ROOT / "addon" / "ForeverCompanion" / "Data.lua"

# Short display names for slots, matching the in-game inventory slots.
SLOT_LABEL = {
    "head": "Head", "neck": "Neck", "shoulder": "Shoulder", "back": "Back",
    "chest": "Chest", "shirt": "Shirt", "tabard": "Tabard", "wrist": "Wrist",
    "hands": "Hands", "waist": "Waist", "legs": "Legs", "feet": "Feet",
    "ring1": "Ring 1", "ring2": "Ring 2", "trinket1": "Trinket 1",
    "trinket2": "Trinket 2", "main_hand": "Main Hand", "off_hand": "Off Hand",
}


def lua_str(value) -> str:
    """Emit a safe double-quoted Lua string literal."""
    if value is None:
        return "nil"
    text = str(value)
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 32:
            out.append("\\%03d" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def lua_val(value) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return lua_str(value)
    if isinstance(value, dict):
        return table([(k, v) for k, v in value.items()])
    if isinstance(value, list):
        return table(value)
    return lua_str(str(value))


def table(items: list, indent: int = 0) -> str:
    """Render a Lua table; keep each record on one line for readable diffs."""
    pad = " " * indent
    inner = " " * (indent + 2)
    lines = []
    for item in items:
        if isinstance(item, tuple):
            key, value = item
            lines.append(f'{inner}{key if key.isidentifier() else "[" + lua_str(key) + "]"}'
                         f" = {lua_val(value)},")
        elif isinstance(item, dict):
            fields = ", ".join(
                f'{k if k.isidentifier() else "[" + lua_str(k) + "]"} = {lua_val(v)}'
                for k, v in item.items() if v is not None
            )
            lines.append(f"{inner}{{ {fields} }},")
        else:
            lines.append(f"{inner}{lua_val(item)},")
    if not lines:
        return "{}"
    return "{\n" + "\n".join(lines) + "\n" + pad + "}"


def build() -> str:
    char_doc = json.loads(CHARACTER.read_text(encoding="utf-8"))
    items_doc = json.loads(ITEMS.read_text(encoding="utf-8"))
    sources_doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    zones_doc = json.loads(ZONES.read_text(encoding="utf-8"))
    plan_doc = json.loads(PLAN.read_text(encoding="utf-8"))
    prof_doc = json.loads(PROF_PLAN.read_text(encoding="utf-8"))

    char = char_doc["character"]
    item_names = {i["item_key"]: i["name"] for i in items_doc["items"]}

    equipment = []
    for eq in char_doc.get("equipment", []):
        key = eq.get("item_key")
        equipment.append({
            "slot": eq["slot"],
            "label": SLOT_LABEL.get(eq["slot"], eq["slot"]),
            "itemKey": key,
            "name": item_names.get(key) if key else None,
        })

    plan = []
    for p in sorted(plan_doc["plans"], key=lambda x: (x["priority"], x.get("slot") or "")):
        plan.append({
            "key": p["plan_key"],
            "priority": p["priority"],
            "slot": p.get("slot"),
            "label": SLOT_LABEL.get(p.get("slot"), p.get("slot")),
            "current": p.get("current_item"),
            "target": p.get("target_item"),
            "how": p.get("target_source"),
            "zone": p.get("zone") or None,
            "reqLevel": p.get("req_level"),
            "reason": p.get("reason"),
            "status": p.get("status"),
            "verification": p.get("verification"),
        })

    zones = []
    for z in zones_doc["zones"]:
        zones.append({
            "name": z["name"],
            "levelMin": z.get("level_min"),
            "levelMax": z.get("level_max"),
            "faction": z.get("faction"),
            "mining": z.get("mining_nodes"),
            "bestFor": z.get("best_for"),
            "notes": z.get("notes"),
        })

    sources = []
    for s in sources_doc["sources"]:
        sources.append({
            "item": item_names.get(s.get("item_key")) if s.get("item_key") else None,
            "type": s.get("source_type"),
            "zone": s.get("zone"),
            "subzone": s.get("subzone"),
            "mob": s.get("mob"),
            "level": s.get("mob_level"),
            "requirement": s.get("requirement"),
            "verification": s.get("verification"),
            "notes": s.get("notes"),
        })

    professions = [
        {"name": p["name"], "skill": p.get("skill"), "max": p.get("max_skill")}
        for p in char_doc.get("professions", [])
    ]

    prof_plan = []
    for p in prof_doc["professions"]:
        prof_plan.append({
            "profession": p["profession"],
            "current": p.get("current"),
            "cap": p.get("cap"),
            "band": p.get("band"),
            "action": p.get("next_action"),
            "materials": p.get("materials"),
            "zone": p.get("zone"),
            "priority": p.get("priority"),
            "verification": p.get("verification"),
        })

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blocks = [
        "-- Data.lua — GENERATED FILE, do not edit by hand.",
        "-- Source: data/characters + data/catalog  →  scripts/build_addon_data.py",
        f"-- Generated: {generated}",
        "",
        "ForeverCompanionData = {",
        f"  generatedAt = {lua_str(generated)},",
        f"  characterKey = {lua_str(char.get('key'))},",
        f"  snapshotFetchedAt = {lua_str(char.get('fetched_at'))},",
        "  character = {",
        f"    name = {lua_str(char.get('display_name'))},",
        f"    level = {lua_val(char.get('level'))},",
        f"    faction = {lua_str(char.get('faction'))},",
        f"    race = {lua_str(char.get('race'))},",
        f"    class = {lua_str(char.get('class'))},",
        f"    guild = {lua_str(char.get('guild'))},",
        f"    region = {lua_str(char.get('region'))},",
        f"    spec = {lua_str('Fury')},",
        f"    armory = {lua_str(char.get('source_url'))},",
        f"    lastOnline = {lua_str(char.get('last_online'))},",
        "  },",
        "  stats = " + table([(k, v) for k, v in char_doc.get("stats", {}).items()]) + ",",
        "  professions = " + table(professions) + ",",
        "  equipment = " + table(equipment) + ",",
        "  plan = " + table(plan) + ",",
        "  zones = " + table(zones) + ",",
        "  sources = " + table(sources) + ",",
        "  professionPlan = " + table(prof_plan) + ",",
        "}",
        "",
    ]
    return "\n".join(blocks)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = build()
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(text) / 1024:.1f} KB, "
          f"{text.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
