"""Regenerate ONLY the shirt / tote mockup photos of finished listings (after changing media.MOCKUP_BOXES), overwriting them in place.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.remock [all | typo:<key> | clip:<cow|xmas|boho>] ...

Uses each listing's own catalog.json + mockup config, so the same designs are shown; covers, sheets, zips and listing text are untouched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory.clipart import build_listing as CB
from etsy_factory.clipart import packs as P
from etsy_factory.typo import build_listing as TB
from etsy_factory.typo.pack import get_niche

OUT = Path(r"F:\WORKHORSE\workspace\etsy_listings")


def _target(imgs: Path, kind: str) -> Path | None:
    hits = sorted(imgs.glob(f"*_mockup_{kind}.jpg"))
    return hits[0] if hits else None


def typo(key: str) -> int:
    niche, cfg = get_niche(key), TB.MEDIA[key]
    root = OUT / niche.slug
    meta = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    n = 0
    for kind, text, sub in cfg["mockups"]:
        dst, idx = _target(root / "images", kind), TB._idx_for(meta, text)
        if dst is None or idx is None:
            print(f"  ! {key}: skip {kind} ({text})")
            continue
        n += bool(TB._mockup(kind, root / "files", idx, sub, dst))
    print(f"typo:{key}: {n} mockups")
    return n


def clip(key: str) -> int:
    pack, look = P.PACKS[key], CB.LOOK[key]
    root = OUT / pack.slug
    meta = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    png_dir, n = CB.ROOT / pack.slug / "png", 0
    for i, (kind, sk) in enumerate(look["mock"]):
        dst = _target(root / "images", kind)
        m = CB._find(meta, sk) or meta[(5 + i) % len(meta)]
        if dst is None:
            print(f"  ! {key}: skip {kind}")
            continue
        n += bool(CB.mockup(kind, png_dir / m["file"], dst))
    print(f"clip:{key}: {n} mockups")
    return n


if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    if args == ["all"]:
        args = [f"typo:{k}" for k in TB.MEDIA] + [f"clip:{k}" for k in CB.LOOK]
    for a in args:
        kind, key = a.split(":")
        (typo if kind == "typo" else clip)(key)
