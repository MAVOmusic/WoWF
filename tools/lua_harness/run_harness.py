#!/usr/bin/env python3
"""Headless smoke test for the Forever Companion addon.

Loads the stub API, then Data.lua / Core.lua / UI.lua in a real Lua runtime,
fires the addon's events, drives every slash command and asserts on the result.

What it proves: the addon parses, boots, renders a panel, and every command
path runs without a Lua error. What it cannot prove: how it looks in game — that
needs the client.

Usage:
    python3 tools/lua_harness/run_harness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import lupa
except ImportError:  # pragma: no cover
    sys.exit("lupa is required:  pip install -r requirements-dev.txt")

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "addon" / "ForeverCompanion"
STUB = ROOT / "tools" / "lua_harness" / "wow_stub.lua"
FILES = ["Data.lua", "Core.lua", "UI.lua"]

failures: list[str] = []
checks = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if condition:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}" + (f"  [{detail}]" if detail else ""))
        failures.append(label)


def main() -> int:
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUB.read_text(encoding="utf-8"))
    harness = lua.globals().Harness

    print("Load")
    for name in FILES:
        path = ADDON / name
        if not path.exists():
            sys.exit(f"missing {path}")
        try:
            lua.execute(path.read_text(encoding="utf-8"))
        except lupa.LuaError as exc:
            sys.exit(f"{name} failed to load: {exc}")
        check(f"{name} loads", True)

    data = lua.globals().ForeverCompanionData
    plan = data.plan
    equipment = data.equipment
    check("Data.lua exposes a plan", len(plan) > 0, f"{len(plan)} entries")
    check("Data.lua exposes equipment", len(equipment) == 18, f"{len(equipment)} slots")
    check("character name is set", bool(data.character.name), str(data.character.name))

    print("\nEvents")
    fired = harness.FireEvent(harness, "ADDON_LOADED", "ForeverCompanion")
    check("ADDON_LOADED handled", fired > 0, f"{fired} listeners")
    harness.ResetChat(harness)
    harness.FireEvent(harness, "PLAYER_LOGIN")
    text = harness.GetChatText(harness)
    check("PLAYER_LOGIN prints a plan hint", "upgrade step" in text or "/fw" in text, text[:90])

    print("\nSlash commands")
    slash = lua.globals().SlashCmdList["FOREVERCOMPANION"]

    harness.ResetChat(harness)
    slash("")
    panel = lua.globals()._G["ForeverCompanionFrame"]
    check("empty command builds the panel", panel is not None)

    for tab in ("next", "gear", "farm", "profs"):
        lua.globals().ForeverCompanion.tab = tab
        try:
            panel.Refresh(panel)
        except lupa.LuaError as exc:
            check(f"render {tab}", False, str(exc))
        else:
            check(f"render {tab}", True)
    rows = panel.rows
    check("panel rendered rows", len(rows) > 0, f"{len(rows)} rows")
    first_title = rows[1].title.text if rows[1] and rows[1].title else None
    check("row 1 has text", bool(first_title), str(first_title)[:60])

    for command, needle in [
        ("next", "next"),
        ("gear", "equipment"),
        ("farm", "farming"),
        ("prof", "professions"),
        ("status", "plan:"),
        ("help", "commands"),
        ("bogus", "commands"),
    ]:
        harness.ResetChat(harness)
        try:
            slash(command)
        except lupa.LuaError as exc:
            check(f"/fw {command}", False, str(exc))
            continue
        out = harness.GetChatText(harness)
        check(f"/fw {command}", needle in out.lower(), out[:80].replace("\n", " / "))

    print("\nTick-off flow")
    fc = lua.globals().ForeverCompanion
    open_before = len(fc.OpenPlan(fc, 3))
    harness.ResetChat(harness)
    slash("done 1")
    open_after = len(fc.OpenPlan(fc, 3))
    check("done 1 removes one open step", open_after == open_before - 1,
          f"{open_before} -> {open_after}")
    slash("reset")
    check("reset restores the step", len(fc.OpenPlan(fc, 3)) == open_before)

    print("\nLevel drift")
    harness.unitLevel = 30
    harness.ResetChat(harness)
    harness.FireEvent(harness, "PLAYER_LOGIN")
    text = harness.GetChatText(harness)
    check("warns when the snapshot is behind your level",
          "snapshot" in text and "30" in text, text[:120].replace("\n", " / "))
    harness.unitLevel = 23

    print("\nLive vs snapshot gear")
    lua.execute('Harness.links[1] = "|cff1eff00|Hitem:2450:0:0:0:0:0:0|h[Green Iron Helm]|h|r"')
    lua.globals().ForeverCompanion.tab = "gear"
    panel.Refresh(panel)
    titles = " ".join((panel.rows[i].title.text or "") for i in range(1, len(panel.rows) + 1))
    check("live item link overrides the snapshot name", "Green Iron Helm" in titles)

    print("\nMissing-slot handling")
    lua.execute("Harness.links[1] = nil")
    panel.Refresh(panel)
    titles = " ".join((panel.rows[i].title.text or "") for i in range(1, len(panel.rows) + 1))
    check("empty head slot shows EMPTY", "EMPTY" in titles.upper())

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failures: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
