# Forever Companion

One small panel that answers the questions you actually have while levelling:

- **Next** — what to equip next, in priority order, with how and where to get it
- **Gear** — every slot, live from your character, with the gap flagged
- **Farm** — zones in your level band, what ore/drops they hold
- **Profs** — the exact next step for each profession

It ships with a **snapshot of your plan** compiled from this repo, so it works with
no data source, no imports, and no auction-house database. When the plan changes,
the data changes with `scripts/build_addon_data.py`.

## Install

Forever lives at `...\World of Warcraft\_forever_\Interface\AddOns`.
This addon targets **Interface 16001** (Forever 1.60.1 / Midnight client, Mainline APIs).

Windows (PowerShell or cmd, from the repo root):

```
xcopy /E /I /Y addon\ForeverCompanion "C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\ForeverCompanion"
```

Then enable **Forever Companion** on the character-select screen (or `/reload` if you
are already in game). Lua-only edits just need `/reload`; a new file or TOC change
needs a full client restart.

## Commands

| Command | Does |
|---|---|
| `/fw` | open / close the panel |
| `/fw next [1-3]` | chat view of the plan at that priority or better |
| `/fw gear` | equipment from the snapshot |
| `/fw farm` | zones and what drops there, for your level |
| `/fw prof` | profession next steps |
| `/fw done <#>` / `/fw undo <#>` / `/fw reset` | tick steps off (saved across sessions) |
| `/fw status` | data build date, open/done counts, snapshot age |

`/forever` works as an alias. `/fw help` prints the list.

## Design constraints (read before extending)

- **No combat log, no unit frames.** Forever runs on the Midnight client where the
  combat log is closed to addons and some values are "secret". This addon only reads
  item links and static data.
- **Live gear comes from `GetInventoryItemLink`**, parsed for the name — never from
  `GetItemInfo` arithmetic. If the API returns something unexpected the panel falls
  back to the snapshot text.
- **The UI is built from plain frames and font strings**, with a guarded
  `BackdropTemplate`. No XML, no template chains that break on patch day.
- **Data is generated, never hand-edited.** `Data.lua` comes from
  `scripts/build_addon_data.py`, which reads the same JSON the SQLite DB and Excel
  workbook come from. One source of truth.

## Files

```
ForeverCompanion.toc   metadata (Interface 16001, SavedVariables ForeverCompanionDB)
Data.lua               GENERATED: character, plan, zones, sources, professions
Core.lua               saved variables, plan logic, slash commands, events
UI.lua                 the panel: tabs, scrolling list, row pool
```

## Testing

`tools/lua_harness/run_harness.py` boots the addon against a stubbed WoW API in a real
Lua runtime, fires the events, drives every slash command and asserts on the render.
It catches nil errors and logic bugs; it cannot judge how it *looks* — that needs the
client.

```bash
pip install -r requirements-dev.txt
python3 tools/lua_harness/run_harness.py
```
