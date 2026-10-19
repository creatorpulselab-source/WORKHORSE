"""Generates the seamless pattern pack files (20 oz skinny tumbler wraps + 12 x 12 in seamless digital paper).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.patterns.pack
Output: F:\\WORKHORSE\\workspace\\etsy_patterns\\<slug>\\{wraps,papers,tiles}/<name>.png  + catalog.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

from PIL import Image

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory.clipart import cutkey as K
from etsy_factory.patterns import engine as E

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_patterns")
SLUG = "seamless_tumbler_wrap_patterns_png"
WRAP_W, WRAP_H = 2790, 2460          # 9.3 x 8.2 in at 300 dpi (20 oz skinny straight tumbler)
PAPER = 3600                         # 12 x 12 in at 300 dpi
PALETTE_MAX_ERR = 3.3
SEED = 7

LABEL = {"checker": "Retro Checkerboard", "stripes": "Candy Stripes", "waves": "Groovy Waves", "arches": "Rainbow Arches",
         "daisies": "Retro Daisies", "hearts": "Outline Hearts", "stars": "Western Stars", "dots": "Polka Dots", "rings": "Retro Rings",
         "gingham": "Gingham Plaid", "leopard": "Leopard Print", "bolts": "Lightning Bolts", "argyle": "Argyle Diamonds"}
PALETTE_LABEL = {"retro_boho": "Retro Boho", "blush": "Blush Pink", "valentine": "Valentine Red", "retro_xmas": "Retro Christmas",
                 "spring": "Spring Pastel", "coastal": "Coastal Teal", "earth": "Earth Tone", "berry": "Berry Bright"}


def catalog() -> List[Dict]:
    out = []
    for ti, kind in enumerate(E.TYPE_ORDER):
        for pal in E.palette_names_for(ti, 4):
            out.append({"index": len(out) + 1, "kind": kind, "palette": pal, "name": f"{len(out) + 1:02d}_{kind}_{pal}",
                        "text": f"{LABEL[kind]} {PALETTE_LABEL[pal]}"})
    return out


def build(force: bool = False) -> List[Dict]:
    base = ROOT / SLUG
    for sub in ("wraps", "papers", "tiles"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    meta = catalog()
    for m in meta:
        w, p, t = base / "wraps" / f"{m['name']}.png", base / "papers" / f"{m['name']}.png", base / "tiles" / f"{m['name']}.png"
        if not force and w.exists() and p.exists() and t.exists():
            continue
        tile = E.make_tile(m["kind"], m["palette"], SEED)
        err = E.seam_error(tile)
        m["seam_error"] = round(err, 3)
        tile.save(t, "PNG", dpi=(300, 300))
        # wrap: tile scaled to 1/3 of the wrap width so the repeat is exactly 3 across; starts at the top-left corner
        K.save_adaptive(E.tile_to(tile, WRAP_W, WRAP_H, WRAP_W // 3).convert("RGBA"), w, PALETTE_MAX_ERR)
        K.save_adaptive(E.tile_to(tile, PAPER, PAPER, PAPER // 3).convert("RGBA"), p, PALETTE_MAX_ERR)
        print("  built", m["name"], f"seam_err={err:.2f}", f"wrap={w.stat().st_size // 1024}KB paper={p.stat().st_size // 1024}KB", flush=True)
    (base / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


if __name__ == "__main__":
    mt = build(force="--force" in sys.argv)
    tot = sum(f.stat().st_size for f in (ROOT / SLUG).rglob("*.png"))
    print(f"{len(mt)} patterns, {tot / 1e6:.1f} MB total")
