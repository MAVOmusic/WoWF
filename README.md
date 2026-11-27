# WoWF — WoW Forever character mapping & farming planner

A queryable model of **Mavo Music** (US · Alliance · Human · Fury Warrior · level 23) that
answers three questions at any level:

1. **What do I equip next?** → `UpgradePlan` sheet / `v_upgrades` view
2. **Where do I get it?** → `FarmSources` + `Zones` sheets / `farm_source`, `zone` tables
3. **Where do I farm for gold, ore, cloth and fish?** → same tables, plus `ProfessionPlan`

Outputs: a **SQLite database** (for queries), an **Excel workbook** (for reading and editing
on the go), and canonical **JSON** (the actual source of truth).

---

## Quickstart

```bash
pip install -r requirements.txt        # only openpyxl is needed

bash scripts/refresh.sh                # parse armory capture → DB → XLSX
python3 -c "import sqlite3; ..."       # or just open data/wowf.xlsx
```

| Task | Command |
|---|---|
| Refresh everything | `bash scripts/refresh.sh` |
| Parse a new armory capture | `python3 scripts/parse_armory.py` |
| Rebuild the database | `python3 scripts/build_db.py` |
| Rebuild the workbook | `python3 scripts/export_xlsx.py` |
| Apply your Excel edits | `python3 scripts/import_xlsx.py` (add `--dry-run` first) |

## Files

```
docs/CONTEXT.md      ← read this first: mission, character facts, decisions, context block
docs/VERSION.md      ← what shipped in each version
docs/CHANGELOG.md    ← dated, append-only history (never loses a checkpoint)
docs/SCHEMA.md       ← table-by-table reference + example queries
sql/schema.sql       ← the model

data/raw/us/mavo-music.md          armory capture (the only external input)
data/characters/us/mavo-music.json canonical character snapshot
data/catalog/items.json            item catalog: equipped, materials, candidates
data/catalog/sources.json          item → zone → mob/quest/craft
data/catalog/zones.json            zones by level band + mining nodes
data/catalog/upgrade_plan.json     prioritised slot plan
data/catalog/profession_plan.json  next step per profession
data/wowf.db                       generated SQLite database
data/wowf.xlsx                     generated workbook (12 sheets)

scripts/                           parse_armory · build_db · export_xlsx · import_xlsx
```

## Data trust rule

Every row carries a `verification` value:

| Value | Meaning |
|---|---|
| `armory` | Read directly off the armory — proven for this character |
| `classic` | General Classic-Era knowledge, **not yet confirmed on WoW Forever** |
| `confirmed` | You checked it in game |
| `todo` | Placeholder (e.g. "any quest neck") |

WoW Forever has custom content, so `classic` rows are hypotheses. Never quote them as facts.

## Refresh cadence

Per `docs/CONTEXT.md` (decision D5): re-fetch the armory and rebuild after **every user
request**, or after every **5** completed work units — whichever comes first. Every
structural change bumps `docs/VERSION.md` and appends to `docs/CHANGELOG.md`.

## Refreshing the armory capture

`wowarmory.gg` is not reachable from every sandbox/CI network, so the capture lives in
`data/raw/us/mavo-music.md` in a fixed, parseable layout. Open the armory page, copy the
profile block into that file keeping the same headings, and run `scripts/refresh.sh`.
