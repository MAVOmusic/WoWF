# CHANGE LOG — WoWF Character Mapping

Keep-a-Changelog style. **Append-only.** Every session appends an entry, even if the
only change is a data refresh. Dates are absolute (YYYY-MM-DD) so future sessions can
count days — e.g. "13 days ago" resolves against these dates, not memory.

Tags: `[data]` armory refresh · `[model]` schema/DB · `[xlsx]` workbook · `[docs]` ·
`[tooling]` scripts · `[decision]` recorded in CONTEXT.md

---

## 2026-11-27 — v0.1.0 — Bootstrap

Initial build. Day 0 of the log.

### Added
- `[docs]` `docs/CONTEXT.md` — mission, canonical character facts, decisions D1–D7,
  refresh protocol, open questions, paste-ready Context Block, glossary.
- `[docs]` `docs/VERSION.md` — version log starting at v0.1.0.
- `[docs]` `docs/CHANGELOG.md` — this file.
- `[docs]` `docs/SCHEMA.md` — table-by-table reference, views, example queries, Excel↔JSON contract.
- `[tooling]` `scripts/jsonio.py` — one-record-per-line JSON writer so diffs stay small.
- `[model]` `sql/schema.sql` — 13 tables + 3 views (`v_slot_gaps`, `v_equipped_stat_totals`, `v_upgrades`).
- `[data]` `data/raw/us/mavo-music.md` — armory extraction captured 2026-11-27
  (profile portion verbatim; site chrome/articles trimmed).
- `[data]` `data/characters/us/mavo-music.json` — snapshot: level 23, Ally Human
  Warrior, Fury 14, 423 HP, 150 AP, 235 armor, 5 professions.
- `[data]` `data/catalog/items.json` — 12 equipped items (verified) + materials +
  candidate upgrades.
- `[data]` `data/catalog/sources.json` — 27 farm sources (drops, quests, crafts, vendor,
  plus gold/cloth/ore/fish routes).
- `[data]` `data/catalog/zones.json` — 11 zones for the 18–35 band with mining nodes.
- `[data]` `data/catalog/upgrade_plan.json` — 12 prioritized slot rows.
- `[tooling]` `scripts/parse_armory.py` — armory text → snapshot JSON.
- `[tooling]` `scripts/build_db.py` — JSON → SQLite (`data/wowf.db`), logs a snapshot row.
- `[tooling]` `scripts/export_xlsx.py` — SQLite → 12-sheet workbook (`data/wowf.xlsx`), 5 sheets
  editable (blue header) with dropdown validation for `verification` and `status`.
- `[tooling]` `scripts/import_xlsx.py` — workbook edits → JSON (merge, not clobber; blank cells
  do not churn; `--dry-run` and `--prune` supported).
- `[tooling]` `scripts/refresh.sh` — parse → build → export in one shot.
- `[decision]` D1–D7 recorded (JSON authoritative; verification tags; cadence; etc.).

### Verified
- Armory → JSON round-trip reproduces the hand-entered snapshot exactly.
- XLSX → JSON → DB → XLSX round-trip is idempotent ("No changes detected" on an untouched
  workbook); a single cell edit changes exactly one JSON field.
- `PRAGMA integrity_check` = ok; all views return expected rows.

### Noted
- Armory reports **item level 0** despite 12 equipped pieces — treated as an armory
  quirk; we rely on raw stats instead.
- Empty slots at snapshot: head, neck, tabard, ring 2, trinket ×2.
- All item IDs unknown (`item_id: null`); armory icon paths are file ids, not item ids.

### Next
- Verify the `classic`-tagged lvl 24–32 candidates in game.
- Add Blackfathom Deeps / Gnomeregan loot tables.
