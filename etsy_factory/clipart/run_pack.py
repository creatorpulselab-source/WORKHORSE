"""Generate + cut one clipart pack.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.clipart.run_pack <cow|xmas|boho> [rounds=2] [--redo name,name]

Output: F:\\WORKHORSE\\workspace\\etsy_clipart\\<slug>\\{raw,png,qc.json,sheets\\sheet_XX.jpg}
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")

from PIL import Image, ImageDraw

from etsy_factory.clipart import comfy_gen as G
from etsy_factory.clipart import cutkey as K
from etsy_factory.clipart import packs as P

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_clipart")


def run(key: str, rounds: int = 2, redo: tuple = ()) -> dict:
    pk = P.PACKS[key]
    base = ROOT / pk.slug
    raw, png, sheets = base / "raw", base / "png", base / "sheets"
    jl = P.jobs(pk, styles_per_subject=rounds)
    for nm in redo:  # force regeneration with a fresh seed
        for j in jl:
            if j[0].startswith(nm) or nm in j[0]:
                (raw / f"{j[0]}.png").unlink(missing_ok=True)
                (png / f"{j[0]}.png").unlink(missing_ok=True)
    seed_bump = {nm: 1000 for nm in redo}
    jobs = []
    for name, prompt, seed, sk, stk in jl:
        bump = sum(v for nm, v in seed_bump.items() if nm in name)
        jobs.append((name, prompt, seed + bump))
    t0 = time.time()
    print(f"[{key}] generate {len(jobs)} images", flush=True)
    res = G.generate_many(jobs, raw, parallel=2,
                          progress=lambda i, n, nm: print(f"  gen [{i}/{n}] {nm} t={time.time() - t0:.0f}s", flush=True))
    png.mkdir(parents=True, exist_ok=True)
    qc, tiles = {}, []
    for name, prompt, seed, sk, stk in jl:
        src = res.get(name)
        if not src:
            qc[name] = {"error": "no image"}
            continue
        dst = png / f"{name}.png"
        if not dst.exists():
            st = K.cut_key(src, dst, long_side=2400)
        else:
            im = Image.open(dst)
            st = {"w": im.width, "h": im.height, "bytes": dst.stat().st_size, "mode": "cached", "coverage": None}
        qc[name] = st or {"error": "empty cut"}
        if st:
            tiles.append((name, dst))
        print(f"  cut {name}: {qc[name].get('mode')} {qc[name].get('bytes', 0) / 1e6:.2f}MB cov={qc[name].get('coverage')}", flush=True)
    (base / "qc.json").write_text(json.dumps(qc, indent=1), encoding="utf-8")
    # contact sheets (5 x 4, dark + light halves to expose halos and holes)
    sheets.mkdir(exist_ok=True)
    for old in sheets.glob("*.jpg"):
        old.unlink()
    S, cols, rows = 400, 5, 4
    for si in range(0, len(tiles), cols * rows):
        chunk = tiles[si:si + cols * rows]
        sh = Image.new("RGB", (S * cols, S * rows), (58, 58, 66))
        d = ImageDraw.Draw(sh)
        for i, (nm, p) in enumerate(chunk):
            im = Image.open(p).convert("RGBA")
            im.thumbnail((S - 24, S - 40))
            x, y = (i % cols) * S, (i // cols) * S
            sh.paste(im, (x + (S - im.width) // 2, y + 8 + (S - 40 - im.height) // 2), im)
            d.text((x + 8, y + S - 22), nm[:46], fill=(235, 235, 235))
        sh.save(sheets / f"sheet_{si // (cols * rows) + 1:02d}.jpg", quality=88)
    total = sum(v.get("bytes", 0) for v in qc.values())
    print(f"[{key}] done {len(tiles)} cut, {total / 1e6:.1f} MB, {time.time() - t0:.0f}s", flush=True)
    return qc


if __name__ == "__main__":
    k = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 2
    redo = ()
    if "--redo" in sys.argv:
        redo = tuple(sys.argv[sys.argv.index("--redo") + 1].split(","))
    run(k, rounds, redo)
