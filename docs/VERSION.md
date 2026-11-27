# VERSION LOG — WoWF Character Mapping

Semantic-ish versioning for the **data model + pipeline**, not for the character.
One entry per shipped increment. Newest first. Never delete.

---

## v0.1.0 — 2026-11-27 — "Bootstrap: character mapping"

**Status:** current · **Character level:** 23 · **Armory snapshot:** 2026-11-27

### What exists in this version
- Repo scaffold: `docs/`, `sql/`, `data/`, `scripts/`.
- SQLite model (`sql/schema.sql`): 13 tables (character, stats, item, item_stat,
  equipment, talents, professions, farm_source, zone, upgrade_plan, profession_plan,
  snapshot, meta) + 3 views.
- Parsed armory snapshot for `us/mavo-music` (level 23 Alliance Human Fury Warrior).
- Item catalog: 12 equipped items (armory-verified) + materials + candidate upgrades.
- Farm-source table: 27 rows, item → zone → mob/quest/craft, plus gold/cloth/ore/fish routes.
- Zone table: 15 zones for the level 1–45 band with mining nodes.
- Upgrade plan: 12 slot rows with priority + target + confidence.
- Excel export (12 sheets) with 5 editable catalog/plan sheets.
- Excel import that merges edits back into JSON.
- `refresh.sh` one-shot rebuild pipeline.

### Known limitations
- No real WoW Forever item IDs (armory exposes icon file ids only) → `item_id` nullable.
- Candidate upgrades tagged `classic` have not been confirmed on WoWF.
- No bag/bank/gold data source exists yet.
- Item level reported as `0` by the armory; computed stats only, no ilvl average.

### Next version target (v0.2.0)
- Verify level 24–32 candidates in game and flip `verification` → `confirmed`.
- Add Blackfathom Deeps + Gnomeregan loot tables.
- Add gold-per-hour tracking per farm route.

---

## Version rules
- **MAJOR** — model redesign that invalidates previous snapshots.
- **MINOR** — new table, new sheet, new data domain (e.g. loot tables, gold log).
- **PATCH** — data refresh, correction, new rows in existing tables.
