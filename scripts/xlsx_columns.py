"""Column contract shared by export_xlsx.py and import_xlsx.py.

Left-hand side is the JSON field name, right-hand side is the Excel header.
Changing a header means changing it here (and nowhere else).
"""

# Sheets that can be edited in Excel and merged back into JSON.
EDITABLE = {
    "Items": [
        ("item_key", "key"),
        ("name", "Name"),
        ("item_id", "Item ID"),
        ("slot", "Slot"),
        ("item_type", "Type"),
        ("subclass", "Subclass"),
        ("req_level", "Req Lvl"),
        ("armor", "Armor"),
        ("stats", "Stats"),
        ("bind_type", "Bind"),
        ("quality", "Quality"),
        ("sell_copper", "Sell (c)"),
        ("weapon_min", "Dmg Min"),
        ("weapon_max", "Dmg Max"),
        ("weapon_speed", "Speed"),
        ("weapon_dps", "DPS"),
        ("source_type", "Source"),
        ("source_detail", "Source Detail"),
        ("zone", "Zone"),
        ("verification", "Verification"),
        ("notes", "Notes"),
    ],
    "FarmSources": [
        ("source_key", "key"),
        ("item_key", "Item key"),
        ("source_type", "Source"),
        ("zone", "Zone"),
        ("subzone", "Subzone"),
        ("mob", "Mob / Node"),
        ("mob_level", "Mob Level"),
        ("drop_rate", "Drop Rate"),
        ("requirement", "Requirement"),
        ("verification", "Verification"),
        ("notes", "Notes"),
    ],
    "Zones": [
        ("zone_key", "key"),
        ("name", "Zone"),
        ("continent", "Continent"),
        ("level_min", "Lvl Min"),
        ("level_max", "Lvl Max"),
        ("faction", "Faction"),
        ("mining_nodes", "Mining"),
        ("herbs", "Herbs"),
        ("best_for", "Best For"),
        ("notes", "Notes"),
        ("verification", "Verification"),
    ],
    "UpgradePlan": [
        ("plan_key", "key"),
        ("priority", "Priority"),
        ("slot", "Slot"),
        ("current_item", "Current"),
        ("target_item", "Target"),
        ("target_source", "How"),
        ("zone", "Zone"),
        ("req_level", "Req Lvl"),
        ("reason", "Why"),
        ("status", "Status"),
        ("verification", "Verification"),
        ("notes", "Notes"),
    ],
    "ProfessionPlan": [
        ("profession", "Profession"),
        ("current", "Current"),
        ("cap", "Cap"),
        ("band", "Band"),
        ("next_action", "Next Action"),
        ("materials", "Materials"),
        ("zone", "Zone"),
        ("priority", "Priority"),
        ("verification", "Verification"),
        ("notes", "Notes"),
    ],
}

# Which JSON collection each editable sheet maps onto, and its primary key field.
SHEET_TARGETS = {
    "Items": ("data/catalog/items.json", "items", "item_key"),
    "FarmSources": ("data/catalog/sources.json", "sources", "source_key"),
    "Zones": ("data/catalog/zones.json", "zones", "zone_key"),
    "UpgradePlan": ("data/catalog/upgrade_plan.json", "plans", "plan_key"),
    "ProfessionPlan": ("data/catalog/profession_plan.json", "professions", "profession"),
}

VERIFICATION_VALUES = ["armory", "classic", "confirmed", "todo"]
STATUS_VALUES = ["open", "in_progress", "done", "skipped", "hold"]

# Columns that must stay numeric on import.
NUMERIC_FIELDS = {
    "item_id", "req_level", "armor", "sell_copper", "weapon_min", "weapon_max",
    "weapon_speed", "weapon_dps", "level_min", "level_max", "priority", "current", "cap",
    "source_key",  # text, but keeps the coercion map honest about what it is not
}
NUMERIC_FIELDS.discard("source_key")


def fmt_num(value) -> str:
    """3.0 -> '3', 3.5 -> '3.5'"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(num)) if num.is_integer() else f"{num:g}"


def stat_string(stats: dict | None) -> str:
    """{'strength': 3, 'stamina': 4} -> 'strength=3, stamina=4'"""
    if not stats:
        return ""
    return ", ".join(f"{k}={fmt_num(v)}" for k, v in stats.items())


def parse_stat_string(text: str | None) -> dict:
    out: dict = {}
    if not text:
        return out
    for part in str(text).replace(";", ",").split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k or not v:
            continue
        try:
            out[k] = int(v) if float(v).is_integer() else float(v)
        except ValueError:
            continue
    return out
