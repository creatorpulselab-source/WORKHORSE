"""Re-cut specific clipart designs with the ComfyUI BiRefNet matte (fixes blush/cream subjects and ground-shadow problems).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.clipart.rematte <cow|xmas|boho> name,name,...

Reads the existing raw image, writes the new cut over png/<name>.png (the previous cut is kept in png_old/).
Re-run build_listing afterwards (without --drop for the repaired designs).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory.clipart import cutkey as K
from etsy_factory.clipart import matte_comfy as MC
from etsy_factory.clipart import packs as P

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_clipart")


def run(key: str, names: list) -> dict:
    base = ROOT / P.PACKS[key].slug
    raw, png, old = base / "raw", base / "png", base / "png_old"
    old.mkdir(exist_ok=True)
    res = {}
    for nm in names:
        src = raw / f"{nm}.png"
        if not src.exists():
            res[nm] = "no raw image"
            continue
        if (png / f"{nm}.png").exists() and not (old / f"{nm}.png").exists():
            shutil.copy2(png / f"{nm}.png", old / f"{nm}.png")
        mask = MC.matte_mask(src)
        st = K.cut_key(src, png / f"{nm}.png", long_side=2400, matte=mask) if mask is not None else None
        res[nm] = f"{st['mode']} {st['bytes'] / 1e6:.2f}MB" if st else "FAILED"
        print(f"  {nm}: {res[nm]}", flush=True)
    return res


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2].split(","))
