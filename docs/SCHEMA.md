# SCHEMA — WoWF character mapping

Generated from `sql/schema.sql` by `scripts/build_db.py`. **JSON is authoritative**; the
database is a build artifact. Excel edits are hydrated into JSON by `import_xlsx.py` and
then flow back through `build_db.py`.

---

## Tables

### `character`
One row per character. Primary key is `character_key` = `region/slug` (e.g.
`us/mavo-music`). There is no numeric character id and no realm field — WoW Forever is
US or EU only, and Forever's First+Surname naming makes the slug unique per region.

### `character_stats`
Character-sheet numbers at the snapshot: attributes, armor, attack power, crit/parry/dodge.
Note these include base stats, so they do **not** equal the sum of gear stats.

### `item`
The item catalog. `item_key` is a name slug; `item_id` is the real WoW item id when known
(the armory does not expose it, so it is usually `NULL`). Holds slot, type/subclass,
requirement, armor, weapon damage/speed/dps, bind type, vendor value, where it comes from,
and `verification`.

### `item_stat`
Long-format item stats: `(item_key, stat, value)`. `stat` includes `strength`, `stamina`,
`agility`, `intellect`, `spirit`, `attack_power`, and server-specific ones such as
`ap_vs_humanoids`. Long format means new stats need no schema change.

### `character_equipment`
One row per slot (18 canonical slots, empty ones included). `item_key` is `NULL` for an
empty slot, which is how gaps are detected.

### `character_talent` / `character_profession`
Talent ranks per tree (custom Forever talents are flagged in JSON with `"custom": true`)
and profession skill/cap.

### `farm_source`
Where an item comes from: `drop | quest | craft | vendor | fish | node`. `item_key` may be
`NULL` for a generic activity (e.g. "Blackfathom Deeps run"). Free-text `zone`, `subzone`,
`mob`, `mob_level`, `drop_rate`, `requirement`.

### `zone`
Level band, faction, mining nodes, herbs, what the zone is best for.

### `upgrade_plan`
Prioritised slot plan: `priority` 1–5, `current_item`, `target_item`, `target_source`,
`zone`, `req_level`, `reason`, `status` (`open | in_progress | done | skipped | hold`),
`verification`.

### `profession_plan`
Next actionable step per profession: current/cap, band, action, materials, zone.

### `snapshot`
History of armory captures (level, reported item level, equipped count, source, timestamp).
Rebuilding with the same `fetched_at` replaces that row instead of duplicating it.

### `meta`
Build metadata: `built_at`, `character_key`, `schema_version`, `json_authoritative`.

---

## Views

| View | Purpose |
|---|---|
| `v_slot_gaps` | All 18 slots in canonical order, with item and `EMPTY`/`filled` state |
| `v_equipped_stat_totals` | Sum of each stat across equipped gear |
| `v_upgrades` | Upgrade plan joined to what is currently equipped, ordered by priority |

---

## Example queries

```sql
-- what is empty right now
SELECT slot FROM v_slot_gaps WHERE state = 'EMPTY';

-- what to do next, and where
SELECT priority, slot, target_item, target_source, zone
FROM v_upgrades WHERE status IN ('open','in_progress') ORDER BY priority;

-- everything farmable in my current level band
SELECT z.name, z.level_min, z.level_max, z.mining_nodes, f.mob, f.item_key
FROM zone z LEFT JOIN farm_source f ON f.zone = z.name
WHERE z.level_min <= 30 AND z.level_max >= 20
ORDER BY z.level_min, z.name;

-- where does iron come from, and what do I need to mine it
SELECT item_key, zone, mob, requirement FROM farm_source WHERE item_key = 'iron_ore';

-- which of my equipped items are weakest by explicit stats
SELECT e.slot, i.name, SUM(s.value) AS explicit_stats
FROM character_equipment e
JOIN item i ON i.item_key = e.item_key
LEFT JOIN item_stat s ON s.item_key = e.item_key
GROUP BY e.slot ORDER BY explicit_stats;

-- stat mix on gear (feeds the "intellect is wasted" argument)
SELECT stat, total, items FROM v_equipped_stat_totals;
```

---

## Excel ↔ JSON contract

Five sheets are editable (blue header) and map to JSON collections in
`scripts/xlsx_columns.py`:

| Sheet | JSON | Key |
|---|---|---|
| Items | `data/catalog/items.json` → `items` | `item_key` |
| FarmSources | `data/catalog/sources.json` → `sources` | `source_key` |
| Zones | `data/catalog/zones.json` → `zones` | `zone_key` |
| UpgradePlan | `data/catalog/upgrade_plan.json` → `plans` | `plan_key` |
| ProfessionPlan | `data/catalog/profession_plan.json` → `professions` | `profession` |

Import rules: rows are upserted by key, blank cells equal blank values (no churn on
round-trip), rows deleted in Excel are kept unless `--prune` is passed, and unmatched
sheets/columns are reported rather than guessed.

Item stats are edited in the single `Stats` column as `strength=3, stamina=4`.
