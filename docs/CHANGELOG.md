# CHANGE LOG — WoWF Character Mapping

Keep-a-Changelog style. **Append-only.** Every session appends an entry, even if the
only change is a data refresh. Dates are absolute (YYYY-MM-DD) so future sessions can
count days — e.g. "13 days ago" resolves against these dates, not memory.

Tags: `[data]` armory refresh · `[model]` schema/DB · `[xlsx]` workbook · `[docs]` ·
`[tooling]` scripts · `[decision]` recorded in CONTEXT.md

---

## 2026-11-27 — v0.2.0 — In-game companion

Second build, same day as v0.1.0.

### Added
- `[tooling]` `addon/ForeverCompanion/` — WoW addon: `.toc` (Interface 16001), `Data.lua`
  (generated), `Core.lua` (state, plan, slash), `UI.lua` (panel with 4 tabs), `README.md`.
- `[tooling]` `scripts/build_addon_data.py` — compiles the JSON model into `Data.lua`;
  added as step 4 of `scripts/refresh.sh`.
- `[tooling]` `tools/lua_harness/` — `wow_stub.lua` (frame/fontstring/slash/API stubs) and
  `run_harness.py` (27 assertions). All pass.
- `[docs]` `docs/ADDONS.md` — verdicts for the 28 addon folders: what to keep, what to fold
  into the companion, and a 5-item fold-in backlog.
- `[tooling]` `requirements-dev.txt` — lupa for the harness.
- `[decision]` D8–D11: Interface 16001 / Mainline APIs, generated addon data, headless
  verification, big data addons stay separate.

### Research
- Confirmed Forever's client: **Interface 16001** (Forever 1.60.1, Midnight retail client,
  Lua 5.1, Mainline APIs). Classic-era addons do not load on it — this changed the whole
  implementation approach.
- Cross-checked a public Forever addon collection (tobarisu1/wow_forever_addons) for TOC
  conventions, event handling and the "secret values / closed combat log" constraints.
  The addon therefore avoids the combat log and `GetItemInfo` arithmetic entirely.

### Noted
- The addon is **untested in a real client**. The harness proves it loads, renders rows and
  that every command path runs; it cannot prove it looks right.

### Next
- One QoL fold-in from `docs/ADDONS.md` (map keybind or minimap drawer).
- In-game layout pass once the client has loaded v0.1.0 once.

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
