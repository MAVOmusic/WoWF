# VERSION LOG — WoWF Character Mapping

Semantic-ish versioning for the **data model + pipeline**, not for the character.
One entry per shipped increment. Newest first. Never delete.

---

## v0.2.2 — 2026-11-27 — "One-file install"

**Status:** current · **Addon version:** 0.1.1 · **Package:** `release/ForeverCompanion-0.1.1.zip`

### Added
- **`scripts/build_addon_zip.py`** — packages the addon into
  `release/ForeverCompanion-<version>.zip` with a top-level `ForeverCompanion/` folder,
  a fixed timestamp and sorted entries, so the same version always produces the same
  bytes (verified: identical sha256 across two full pipeline runs). Integrity-tested with
  `zipfile.testzip()`, prints sha256.
- **`install-addon.bat`** — Windows: finds the newest `release\ForeverCompanion-*.zip`,
  extracts it into `%ProgramFiles(x86)%\World of Warcraft\_forever_\Interface\AddOns`,
  or into any path passed as the first argument.
- `refresh.sh` is now 5 steps; packaging is the last one.
- GitHub Release `companion-v0.1.1` is the landing page; it links the committed zip
  (`/raw/main/release/...`) because uploading a release *asset* needs `uploads.github.com`,
  which this build sandbox cannot reach. Manual step if you want the asset attached:
  open the release page → Edit → drag the zip in.

### Fixed
- **Snapshot dates were being faked.** `parse_armory.py` stamped `fetched_at` with today's
  date on every run, even when the armory capture had not changed. It now stores
  `capture_sha256` and only advances the date when the raw capture actually differs.

### Verified
- Zip round-trip: extract into a clean directory → `ForeverCompanion/ForeverCompanion.toc`
  at the archive root, 5 files, `testzip()` clean.
- Harness still 33/33.

---

## v0.2.1 — 2026-11-27 — "Companion v0.1.1: make it visible"

**Status:** current · **Addon version:** 0.1.1

Reported symptom: addon enabled in the list, nothing on screen, nothing in chat.

### Fixed
- **Secret-value crash path.** `UnitLevel` was read unguarded; on the Midnight client a
  secret value would abort the whole `PLAYER_LOGIN` handler before any message printed —
  exactly the reported "does nothing" symptom. All unit reads now go through
  `FC.SafeNumber` (pcall + `issecretvalue` + tonumber fallback to the snapshot level).
- **Silent failures.** Event and slash handlers are wrapped in `pcall` and print the error.
- **Auto-open never fired.** v0.1.0 set `everShown` at login without ever showing the
  panel, so the first-open check could never be true. Replaced with a new `autoOpened` flag.
- **Close button never created.** The code tested a global (`UIPanelCloseButton`) that does
  not exist; it is a template *string*. Now created inside pcall.
- Panel raised to `FULLSCREEN_DIALOG` + toplevel so it is not buried behind other windows.

### Added
- **Minimap button** (`/fw button`) so there is always a visible entry point.
- **`/fw diag`** — version, client build, data state, plan counts, panel state, last error.
- **`/fw resetpos`** — recover a panel dragged off-screen.
- **Load banner** at login: "v0.1.1 loaded · N step(s) open" — proves the addon runs.

### Verified
- Harness extended to 33 assertions: auto-open, minimap button, `/fw diag`, `/fw resetpos`,
  and a simulated **secret `UnitLevel`** that must not break login.

---

## v0.2.0 — 2026-11-27 — "In-game companion"

**Status:** current · **Character level:** 23 · **Addon version:** 0.1.0

### What this version adds
- **Forever Companion addon** (`addon/ForeverCompanion/`): one panel, four tabs
  (Next / Gear / Farm / Profs), slash command `/fw`, saved tick-offs, level-drift warning.
  Targets Interface **16001** (Forever 1.60.1 / Midnight client, Mainline APIs, Lua 5.1).
- **Data compiler** (`scripts/build_addon_data.py`): JSON → `Data.lua`, runs as step 4 of
  `refresh.sh`. The addon can never drift from the DB.
- **Headless harness** (`tools/lua_harness/`): stubbed WoW API + 27 assertions covering
  load, events, every slash command, tick-off persistence, level drift, live-vs-snapshot
  gear and empty slots.
- **`docs/ADDONS.md`**: keep / fold verdict for the 28 addon folders in the client.

### Known limitations
- The addon has **not been run in a real client** (no game here). Layout, fonts and
  backdrop behaviour are unverified; logic and API surface are harness-tested.
- Panel is chat-and-list only: no minimap button, no tooltips, no keybinds yet.
- `GetItemInfo` is deliberately avoided (Midnight "secret values"); live gear is read by
  parsing `GetInventoryItemLink`.

### Next version target (v0.3.0)
- One QoL fold-in from the backlog (map keybind or minimap drawer).
- In-game feedback pass and layout fixes.

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
