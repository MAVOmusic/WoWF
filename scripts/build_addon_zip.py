#!/usr/bin/env python3
"""Package the addon into release/ForeverCompanion-<version>.zip.

The archive root contains a single `ForeverCompanion/` folder holding the .toc and
its .lua files, which is exactly what the client expects under Interface/AddOns.

Deterministic on purpose: sorted entries and a fixed timestamp, so rebuilding the
same version produces a byte-identical file (no pointless git churn).

Usage:
    python3 scripts/build_addon_zip.py [--outdir release]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = ROOT / "addon" / "ForeverCompanion"
ADDON_NAME = "ForeverCompanion"
# Fixed timestamp keeps the archive reproducible.
FIXED_TIME = (2026, 11, 27, 0, 0, 0)
# Files that belong in the archive (everything else in the folder is dev-only).
ALLOWED_SUFFIXES = {".toc", ".lua", ".md"}


def addon_version(toc: Path) -> str:
    match = re.search(r"^##\s*Version:\s*(\S+)", toc.read_text(encoding="utf-8"), re.M)
    if not match:
        sys.exit(f"no ## Version: line in {toc.name}")
    return match.group(1)


def build(outdir: Path = ROOT / "release") -> Path:
    toc = ADDON_DIR / f"{ADDON_NAME}.toc"
    if not toc.exists():
        sys.exit(f"missing {toc}")

    version = addon_version(toc)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{ADDON_NAME}-{version}.zip"

    files = sorted(
        path for path in ADDON_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    )
    if not files:
        sys.exit(f"no addon files found in {ADDON_DIR}")

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            arcname = f"{ADDON_NAME}/{path.relative_to(ADDON_DIR).as_posix()}"
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    with zipfile.ZipFile(out) as archive:
        broken = archive.testzip()
        if broken:
            sys.exit(f"corrupt entry in {out.name}: {broken}")
        names = archive.namelist()

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    size_kb = out.stat().st_size / 1024

    print(f"Wrote {out.relative_to(ROOT)} ({size_kb:.1f} KB, {len(names)} files)")
    for name in names:
        print(f"  {name}")
    print(f"  sha256 {digest}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    build(args.outdir)


if __name__ == "__main__":
    main()
