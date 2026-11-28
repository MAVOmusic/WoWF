#!/usr/bin/env python3
"""Parse an armory capture (data/raw/...) into the canonical character JSON.

The capture format is the normalised profile block described in
data/raw/us/mavo-music.md — capture that file, run this script, then
scripts/build_db.py.

It also upserts the equipped items into data/catalog/items.json so changed gear,
durability and stats flow through automatically. Candidate upgrade rows are never
deleted, only added/updated.

Usage:
    python3 scripts/parse_armory.py [--raw PATH] [--out PATH] [--no-items] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "us" / "mavo-music.md"
OUT = ROOT / "data" / "characters" / "us" / "mavo-music.json"
ITEMS = ROOT / "data" / "catalog" / "items.json"

SLOTS = {
    "head": "head", "neck": "neck", "shoulder": "shoulder", "back": "back",
    "chest": "chest", "shirt": "shirt", "tabard": "tabard", "wrist": "wrist",
    "hands": "hands", "waist": "waist", "legs": "legs", "feet": "feet",
    "ring 1": "ring1", "ring 2": "ring2", "trinket 1": "trinket1",
    "trinket 2": "trinket2", "main hand": "main_hand", "off hand": "off_hand",
}

STAT_NAMES = {
    "strength": "strength", "agility": "agility", "stamina": "stamina",
    "intellect": "intellect", "spirit": "spirit", "armor": "armor",
    "attack power": "attack_power", "spell power": "spell_power",
    "attack power vs humanoids": "ap_vs_humanoids",
}

TZ_OFFSETS = {"EST": "-05:00", "EDT": "-04:00", "CST": "-06:00", "CDT": "-05:00",
              "MST": "-07:00", "MDT": "-06:00", "PST": "-08:00", "PDT": "-07:00",
              "UTC": "+00:00", "GMT": "+00:00"}


def slug(name: str) -> str:
    s = name.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def money_to_copper(text: str | None) -> int | None:
    if not text:
        return None
    total = 0
    for amount, unit in re.findall(r"(\d+)\s*([gsc])", text.lower()):
        total += int(amount) * {"g": 10000, "s": 100, "c": 1}[unit]
    return total or None


def parse_last_online(text: str) -> str:
    raw = text.replace("(2 days ago)", "").strip()
    m = re.match(r"([A-Za-z]{3}) (\d{1,2}), (\d{4}),? (\d{1,2}):(\d{2}) ([AP]M)\s*(\w+)?", raw)
    if not m:
        return text
    mon, day, year, hour, minute, ap, tz = m.groups()
    dt = datetime.strptime(f"{mon} {day} {year} {hour}:{minute} {ap}",
                           "%b %d %Y %I:%M %p")
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + TZ_OFFSETS.get((tz or "").upper(), "+00:00")


def parse_items_section(text: str) -> list[dict]:
    """Split the '## Equipment' block into per-slot item dicts."""
    body = text.split("## Equipment", 1)[1].split("## Stats", 1)[0]
    blocks = re.split(r"\n### ", "\n" + body)
    out = []
    for block in blocks:
        lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("# ").strip()
        slot = SLOTS.get(title.lower())
        if not slot:
            continue
        name = lines[1] if len(lines) > 1 else ""
        rest = lines[2:]
        if not name or name.lower() == "empty":
            out.append({"slot": slot, "item_key": None})
            continue

        item: dict = {"slot": slot, "name": name, "item_key": slug(name)}
        stats: dict = {}
        for ln in rest:
            low = ln.lower()
            if low.startswith("binds when picked up"):
                item["bind_type"] = "BoP"
            elif low.startswith("binds when equipped"):
                item["bind_type"] = "BoE"
            elif m := re.match(r"(Requires Level|Requires level)\s*(\d+)", ln):
                item["req_level"] = int(m.group(2))
            elif m := re.match(r"^(\d+)\s*Armor$", ln):
                item["armor"] = int(m.group(1))
            elif m := re.match(r"^Durability\s*(\d+)\s*/\s*(\d+)", ln):
                item["durability"], item["durability_max"] = int(m.group(1)), int(m.group(2))
            elif low.startswith("sell price:"):
                item["sell_copper"] = money_to_copper(ln.split(":", 1)[1])
            elif m := re.match(r"^(\d+)\s*-\s*(\d+)\s*Damage$", ln):
                item["weapon_min"], item["weapon_max"] = int(m.group(1)), int(m.group(2))
            elif m := re.match(r"^Speed\s*([\d.]+)", ln):
                item["weapon_speed"] = float(m.group(1))
            elif m := re.match(r"^\(([\d.]+) damage per second\)", ln):
                item["weapon_dps"] = float(m.group(1))
            elif m := re.match(r"^\+(\d+)\s+(.+)$", ln):
                stat_key = STAT_NAMES.get(m.group(2).strip().lower())
                if stat_key:
                    stats[stat_key] = int(m.group(1))
            elif ln in ("One-Hand", "Two-Hand", "Off Hand", "Main Hand"):
                item["hand"] = ln
            elif ln in ("Dagger", "Axe", "One-Handed Axe", "One-Handed Sword", "Sword",
                        "Mace", "One-Handed Mace", "Staff", "Polearm", "Fist Weapon"):
                item["subclass"] = ln
            elif ln in ("Mail", "Leather", "Cloth", "Plate"):
                item["subclass"] = ln
                item["item_type"] = "Armor"
            elif ln in ("Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet",
                        "Back", "Shirt", "Finger", "Neck", "Head", "Trinket", "Tabard"):
                item["slot_label"] = ln
        if stats:
            item["stats"] = stats
        if "weapon_min" in item:
            item["item_type"] = "Weapon"
        elif "armor" in item and "item_type" not in item:
            item["item_type"] = "Armor"
        out.append(item)
    return out


def parse_talents(text: str, previous: dict | None = None) -> dict:
    body = text.split("## Specializations & talents", 1)[1].split("## Professions", 1)[0]
    trees: dict = {}
    points: dict = {}
    current = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if m := re.match(r"^###\s+(\w+)\s+(\d+)$", line):
            current = m.group(1)
            trees[current] = []
            points[current] = int(m.group(2))
            continue
        if current and "—" in line:
            name_part, _, rank_part = line.partition("—")
            rank_m = re.search(r"Rank\s+(\d+)\s+of\s+(\d+)", rank_part)
            if not rank_m:
                continue
            tid_m = re.search(r"talent id\s+(\d+)", line)
            talent = {
                "name": name_part.strip(),
                "id": int(tid_m.group(1)) if tid_m else None,
                "rank": int(rank_m.group(1)),
                "max_rank": int(rank_m.group(2)),
            }
            if "Forever custom" in line:
                talent["custom"] = True
            if talent["id"] is None and previous:
                for prev_tree in previous.get("trees", {}).values():
                    for prev in prev_tree:
                        if prev.get("name") == talent["name"] and prev.get("id"):
                            talent["id"] = prev["id"]
                            break
            trees[current].append(talent)
    return {"points": points, "trees": trees}


def parse_stats(text: str) -> dict:
    body = text.split("## Stats", 1)[1].split("## Specializations", 1)[0]
    stats: dict = {}
    for line in body.splitlines():
        m = re.match(r"^-\s*([A-Za-z ]+):\s*([\d.]+)%?$", line.strip())
        if not m:
            continue
        key = m.group(1).strip().lower().replace(" ", "_")
        value = float(m.group(2))
        pct = key in ("melee_crit", "ranged_crit", "spell_crit", "dodge", "parry", "block")
        stats[key] = float(value) if pct else (int(value) if value.is_integer() else value)
    out = {}
    for k, v in stats.items():
        if k == "rage":
            out["resource_type"], out["resource"] = "Rage", int(v)
        elif k == "health":
            out["health"] = int(v)
        else:
            out[k] = v
    return out


def parse_professions(text: str) -> list[dict]:
    body = text.split("## Professions", 1)[1]
    out = []
    for m in re.finditer(r"^-\s*([A-Za-z ]+?)\s+(\d+)\s*/\s*(\d+)\s*$", body, re.M):
        out.append({"name": m.group(1).strip(), "skill": int(m.group(2)),
                    "max_skill": int(m.group(3))})
    return out


def parse_character(text: str, previous: dict, capture_hash: str) -> dict:
    char = dict(previous.get("character", {}))
    m = re.search(r"^#\s+(.+?)\n\s*\n(US|EU)\b", text, re.M)
    if not m:
        m = re.search(r"^\*\*([^*:\n]+)\*\*\s*$", text, re.M)
    if m:
        name = m.group(1).strip()
        char["display_name"] = name
        parts = name.split()
        char["first_name"], char["last_name"] = parts[0], " ".join(parts[1:])
    header = re.search(r"^(.*·.*)$", text, re.M)
    if header:
        bits = [b.strip() for b in header.group(1).split("·")]
        char["faction"] = bits[0]
        char["class"] = bits[1]
        lvl = re.match(r"(\d+)\s+(\w+)", bits[2])
        if lvl:
            char["level"] = int(lvl.group(1))
            char["race"] = lvl.group(2)
        mode = re.search(r",\s*(\w+)\s*\((US|EU)\)", bits[2])
        if mode:
            char["realm_type"], char["region"] = mode.group(1), mode.group(2).lower()
        gm = re.search(r"<([^>]+)>", header.group(1))
        if gm:
            char["guild"] = gm.group(1)
            char["guild_slug"] = slug(gm.group(1))
    if m := re.search(r"Last online:\s*(.+)", text):
        char["last_online"] = parse_last_online(m.group(1))
    if m := re.search(r"Item level:\s*(\d+)", text):
        char["item_level"] = int(m.group(1))
    char["key"] = f"{char.get('region', 'us')}/{slug(char.get('display_name', ''))}"
    char["slug"] = char["key"].split("/", 1)[1]
    # Only claim a fresh capture when the raw file actually changed. Re-running the
    # pipeline on an unchanged capture must not rewrite the snapshot date.
    previous_char = previous.get("character", {})
    same_capture = previous.get("capture_sha256") == capture_hash
    if same_capture and previous_char.get("fetched_at"):
        char["fetched_at"] = previous_char["fetched_at"]
    else:
        char["fetched_at"] = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    return char


def merge_items(parsed: list[dict]) -> tuple[dict, int, int]:
    doc = json.loads(ITEMS.read_text(encoding="utf-8"))
    index = {i["item_key"]: i for i in doc["items"]}
    added = updated = 0
    for p in parsed:
        if not p.get("item_key"):
            continue
        key = p["item_key"]
        fields = {k: v for k, v in p.items()
                  if k in ("name", "slot", "item_type", "subclass", "req_level", "armor",
                           "bind_type", "sell_copper", "weapon_min", "weapon_max",
                           "weapon_speed", "weapon_dps", "stats")}
        if key not in index:
            fields["verification"] = "armory"
            fields["notes"] = "Added automatically from a later armory capture."
            doc["items"].append(fields)
            index[key] = fields
            added += 1
        else:
            changed = {k: v for k, v in fields.items()
                       if index[key].get(k) != v and k != "slot"}
            if changed:
                index[key].update(changed)
                index[key]["verification"] = "armory"
                updated += 1
    return doc, added, updated


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-items", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.raw.exists():
        sys.exit(f"missing armory capture: {args.raw}")
    text = args.raw.read_text(encoding="utf-8")
    old = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}

    capture_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    char = parse_character(text, old, capture_hash)
    equipment = parse_items_section(text)
    doc = {
        "schema_version": old.get("schema_version", 1),
        "capture_sha256": capture_hash,
        "character": char,
        "stats": parse_stats(text),
        "talents": parse_talents(text, old.get("talents")),
        "professions": parse_professions(text),
        "equipment": [
            {k: v for k, v in e.items()
             if k in ("slot", "item_key", "durability", "durability_max")}
            for e in equipment
        ],
    }

    # report what changed
    changes = []
    old_char = old.get("character", {})
    if old.get("capture_sha256") and old.get("capture_sha256") != capture_hash:
        changes.append("armory capture changed (new snapshot)")
    for f in ("level", "item_level", "guild", "last_online"):
        if old_char.get(f) != char.get(f):
            changes.append(f"{f}: {old_char.get(f)!r} -> {char.get(f)!r}")
    if old.get("stats") != doc["stats"]:
        changes.append("stats changed")
    old_eq = {e["slot"]: e.get("item_key") for e in old.get("equipment", [])}
    new_eq = {e["slot"]: e.get("item_key") for e in doc["equipment"]}
    for slot in sorted(set(old_eq) | set(new_eq)):
        if old_eq.get(slot) != new_eq.get(slot):
            changes.append(f"{slot}: {old_eq.get(slot)} -> {new_eq.get(slot)}")
    old_prof = {p["name"]: p["skill"] for p in old.get("professions", [])}
    for p in doc["professions"]:
        if old_prof.get(p["name"]) not in (None, p["skill"]):
            changes.append(f"{p['name']}: {old_prof[p['name']]} -> {p['skill']}")

    print(f"Parsed {args.raw.relative_to(ROOT)}")
    print(f"  level {char.get('level')} · {len([e for e in equipment if e.get('item_key')])}"
          f"/{len(equipment)} slots filled · {len(doc['professions'])} professions · "
          f"{sum(len(t) for t in doc['talents']['trees'].values())} talents")
    if changes:
        print("  changes vs previous snapshot:")
        for c in changes:
            print(f"    - {c}")
    else:
        print("  no field-level changes vs previous snapshot")

    items_doc, added, updated = (None, 0, 0)
    if not args.no_items:
        items_doc, added, updated = merge_items(equipment)
        print(f"  items.json: +{added} new, {updated} updated")

    if args.dry_run:
        print("  --dry-run: nothing written")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(jsonio.dump(doc), encoding="utf-8")
    print(f"  wrote {args.out.relative_to(ROOT)}")
    if items_doc is not None:
        ITEMS.write_text(jsonio.dump(items_doc), encoding="utf-8")
        print(f"  wrote {ITEMS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
