# ADDONS — what to keep, what to fold in

Verdicts are based on **what each addon does**, not on a code review of your copies.
28 folders in `Interface\AddOns` usually means ~10 real addons plus per-class and
library modules that are dead weight for a Human Warrior.

## The rule

An addon earns its slot if it does a job that **cannot** be done by 300 lines of your own
code: a quest database, an auction engine, a full bag rewrite. Everything else is a
candidate for the companion.

## Verdicts

| Folder | What it is | Verdict |
|---|---|---|
| Questie, QuestieDB, QuestieTrace | Quest database + tracker + map pins | **Keep.** ~10 MB of hand-curated quest data. Nothing you'd rebuild. |
| Bagnon, Bagnon_Bank, Bagnon_Config, Bagnon_GuildBank | Bag/bank/G-bank window | **Keep** (one family). A bag rewrite is real work for little gain. |
| BagBrother | Data backend for Bagnon | **Keep** — it is Bagnon's dependency, not a separate choice. |
| Auctionator | Auction house workflow | **Keep** if you trade; nothing in the companion competes with it. |
| Guidelime, Guidelime_TUGs_Forever | Leveling route guide | **Keep** while levelling, drop at 60. |
| GearQuestForever + _ItemStats + _Languages | Gear-from-quests recommendations | **Keep the core + Warrior module; delete the other 7 class folders** (DRUID, HUNTER, MAGE, PALADIN, PRIEST, ROGUE, SHAMAN, WARLOCK). They cannot activate on a warrior. |
| GearQuestForever_WARRIOR | Warrior data for the above | **Keep.** |
| ForeverDungeonJournal | Dungeon loot journal | **Keep.** Loot tables are data, not logic. |
| BlizzMove, BlizzMove_Debug | Move Blizzard frames | **Fold into the companion later.** ~80 lines. Debug module is not needed outside development. |
| BetterFishing | Fishing quality-of-life (lure, double-click) | **Fold later** if you fish a lot; you do (Fishing 150/150). |
| MinimapButtonButton | Minimap icon drawer | **Fold later** — a collection frame is small. |
| OpenMap | One-key map open | **Fold now** — trivial keybind, not worth a folder. |
| NeedRoll | Auto need/greed on rolls | **Fold later.** Small, but touching loot rolls needs care. |
| WhatsTraining | What the class trainer teaches | **Fold later** — data + a list, fits the companion's "what next" theme. |
| Auctionator/Bagnon etc. config folders | settings | keep with their parents |

## Why not one addon for everything?

Because three of these are **databases**, not features: Questie's quest table, Auctionator's
pricing, the dungeon journal. Merging them would mean shipping ~15 MB of someone else's
data with your name on it, and re-merging their databases every patch.

The realistic shape is: **Forever Companion** owns the *planning* layer — what to wear,
where to farm, what to train, what to click next — and the big addons stay as sensors and
databases underneath. That is why the companion reads your equipped items from the game
but keeps the plan in this repo.

## Fold-in backlog (each is a self-contained slice)

1. `/fw map` — one-key world map (replaces OpenMap).
2. Minimap icon + drawer (replaces MinimapButtonButton).
3. Trainer list: what is available at your level (replaces WhatsTraining).
4. Frame mover for Blizzard windows (replaces BlizzMove).
5. Fishing helper: lure reminder + double-right-click (replaces BetterFishing).
