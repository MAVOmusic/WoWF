# CONTEXT — WoWF (WoW Forever) Character Mapping

> This file is the **always-growing context panel**. Read it first, in any session.
> It is not a summary of the code — it is the memory of *why* the repo exists.
> Never delete entries. Append, then correct.

Last updated: **2026-11-27** · Repo version: **v0.1.0**

---

## 1. Mission

Give the player a queryable model of their WoW Forever character so we can **predict**
what to equip next, **where** to get it, and **where** to farm (items, gold, ore, cloth,
fish) for maximum benefit at the current level — then keep that model fresh.

Two deliverables, one source of truth:

| Deliverable | Path | Role |
|---|---|---|
| SQLite DB | `data/wowf.db` | Queryable model (built, not hand-edited) |
| Excel workbook | `data/wowf.xlsx` | Human view + editable on the go |
| Canonical JSON | `data/characters/`, `data/catalog/` | Editable source of truth |

Rule: **JSON is authoritative → DB and XLSX are generated.** Edits made in Excel are
merged back into JSON with `scripts/import_xlsx.py`, never written to the DB directly.

---

## 2. Character (canonical facts)

| Fact | Value |
|---|---|
| Character | **Mavo Music** (Forever naming = First `Mavo` + Surname `Music`) |
| Key | `us/mavo-music` |
| Region | **US** — WoW Forever is US **or** EU only, no sub-realms |
| Mode | Normal (`forever`) |
| Faction / Race / Class | Alliance / Human / **Warrior** |
| Build | **Fury** (14 points) — Cruelty 5/5, Unbridled Wrath 5/5, Furious Precision 3/3, Blood Craze 1/3 |
| Level | **23** |
| Guild | `<Mustard Network>` |
| Professions | Mining 112/150 · Blacksmithing 104/150 · Cooking 150/150 · Fishing 150/150 · First Aid 130/150 |
| Armory | https://wowarmory.gg/?region=us&forever=mavo-music |

Because Forever uses `First Surname`, the armory slug is unique **per region** — there is
no realm field and no numeric character id. **Identity = `region + slug`.**

---

## 3. Decisions log (append-only)

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-11-27 | Canonical data lives in JSON; DB + XLSX are generated artifacts | Keeps diffs reviewable and lets Excel be a scratchpad without corrupting the model |
| D2 | 2026-11-27 | Item identity = `item_key` slug (name-based) + nullable `item_id` | The armory exposes icon file ids, not real item ids. Slugs work today; ids can be filled later |
| D3 | 2026-11-27 | Every row carries a `verification` field: `armory` / `classic` / `todo` | Separates what the armory proved from what is general Classic-Era knowledge that still needs in-game checking |
| D4 | 2026-11-27 | No numeric character id; key on `us/mavo-music` | The armory has none, and names are unique per region |
| D5 | 2026-11-27 | Rebuild cadence: after **every** user request, or after every **5** completed work units, whichever comes first | Keeps the model from drifting while levelling |
| D6 | 2026-11-27 | Every structural change bumps `VERSION.md` and appends `CHANGELOG.md` | Continuity across sessions — no "what did we do 10 days ago?" |
| D7 | 2026-11-27 | Armory fetch is manual/agent-driven (`data/raw/`), not a cron job | Sandbox + most CI networks can't reach `wowarmory.gg` |

---

## 4. Refresh protocol (do this every time)

1. Re-fetch the armory page (agent tool or `scripts/fetch_armory.sh` where network allows).
2. Save/extend the extraction in `data/raw/us/mavo-music.md`.
3. `python scripts/parse_armory.py` → rewrites `data/characters/us/mavo-music.json`.
4. `python scripts/build_db.py` → rebuilds `data/wowf.db` + appends a `snapshot` row.
5. `python scripts/export_xlsx.py` → rebuilds `data/wowf.xlsx`.
6. Append to `CHANGELOG.md`; bump `VERSION.md` if the schema/pipeline changed.
7. Commit + push + PR + merge so nothing is lost.

One command for steps 3–5: `bash scripts/refresh.sh`.

---

## 5. Open questions (unresolved)

| # | Question | Impact |
|---|---|---|
| Q1 | WoW Forever item IDs — is there an API or datamine we can sync instead of name slugs? | Would let us join real drop tables |
| Q2 | Exact Forever realm rules for contested zones / dungeon access timings | Affects farm routing |
| Q3 | Are Forever's custom talents/items changing the lvl 20–32 BiS list vs Classic? | Upgrades are tagged `classic` until confirmed in game |
| Q4 | Does the armory expose bag/bank contents or bank gold? | Would improve gold forecasting |

---

## 6. Next actions

- [ ] Fill `item_id` for equipped items as they're confirmed in game.
- [ ] Verify the `classic`-tagged candidates in `data/catalog/upgrade_plan.json` (level 24–32 push).
- [ ] Add Blackfathom Deeps / Gnomeregan loot tables once item names are confirmed.
- [ ] Track gold-per-hour per farm route after a few sessions.

---

## 7. Context Block (paste this into a fresh chat)

```
PROJECT: WoWF — character mapping + farming prediction for WoW Forever.
REPO: MAVOmusic/WoWF, branch arena/ec9cc803-wowf.

CHARACTER: "Mavo Music" (Forever name = first+surname). Alliance Human Warrior,
level 23, Fury 14 (Cruelty 5, Unbridled Wrath 5, Furious Precision 3, Blood Craze 1),
guild <Mustard Network>, region US (no realm/sub-realm — key is us/mavo-music).
Professions: Mining 112/150, Blacksmithing 104/150, Cooking 150/150, Fishing 150/150,
First Aid 130/150. Armory: wowarmory.gg/?region=us&forever=mavo-music

PURPOSE: know what to equip next, where to get it, and where to farm (items, gold,
ore, cloth, fish) at the current level.

ARCHITECTURE: canonical JSON in data/characters + data/catalog → build_db.py →
data/wowf.db (SQLite) → export_xlsx.py → data/wowf.xlsx (editable). Excel edits are
merged back to JSON by import_xlsx.py. Never hand-edit the DB or XLSX-for-data.

TRUST RULES: every row has verification = armory (proven by armory) | classic
(general Classic-Era knowledge, NOT yet confirmed on WoWF) | todo. Never present
`classic` rows as fact; custom Forever content may differ.

CADENCE: re-fetch armory + rebuild after every request or every 5 work units.
Every change updates CHANGELOG.md; structural change bumps VERSION.md. Commit,
push, PR, merge — nothing lives only in the sandbox.
```

---

## 8. Glossary

| Term | Meaning here |
|---|---|
| WoWF | WoW Forever — private server with custom content (custom talents like Spearing Strike, Bloodthrill) |
| Forever naming | First name + Surname character naming, unique per region |
| `verification` | Provenance tag (see D3) |
| `priority` (1–5) | 1 = do immediately, 5 = ignore until later levels |
| `gap` | Empty or weak slot relative to level |
