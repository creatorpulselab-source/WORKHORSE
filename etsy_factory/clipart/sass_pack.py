"""Sarcastic leopard-accessory animal shirt designs: AI art (text-free) + procedural captions.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.clipart.sass_pack [--only 1,2,3] [--recompose] [--redo name,name]

Per design: FLUX Krea art on a key colour -> BiRefNet matte + colour-key edge clean-up (art/) -> captions set in real fonts, the top
in charcoal/navy and the bottom filled with a generated leopard print with a dark outline, straight or arched -> png/<name>.png
(transparent, ready for sublimation / DTF). Captions come from sass_data.SASS and are always spelled exactly as written there.
Outputs: F:\\WORKHORSE\\workspace\\etsy_clipart\\sarcastic_leopard_animals_shirt_designs_png\\{raw,art,png,sheets}
"""
from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from etsy_factory.clipart import comfy_gen as G
from etsy_factory.clipart import cutkey as K
from etsy_factory.clipart import matte_comfy as MC
from etsy_factory.clipart import packs as P
from etsy_factory.clipart.sass_data import SASS

FONTS = Path(r"F:\WORKHORSE\etsy_factory\fonts")
ROOT = Path(r"F:\WORKHORSE\workspace\etsy_clipart")
PACK = P.PACKS["sass"]
CHARCOAL, NAVY, BROWN = (38, 38, 42), (28, 42, 80), (88, 50, 22)
TOP_FONTS = ["Anton-Regular.ttf", "BebasNeue-Regular.ttf", "ArchivoBlack-Regular.ttf", "Anton-Regular.ttf"]
BOT_FONTS = ["Anton-Regular.ttf", "AlfaSlabOne-Regular.ttf", "ArchivoBlack-Regular.ttf", "Anton-Regular.ttf"]
MAX_W = 2150


# ---------------------------------------------------------------------------------------------------- leopard texture
def leopard(w: int, h: int, seed: int = 7) -> Image.Image:
    rnd = random.Random(seed)
    im = Image.new("RGB", (w, h), (226, 178, 108))
    d = ImageDraw.Draw(im)
    n = int(w * h / (44 * 44))
    for _ in range(n):
        x, y, r = rnd.uniform(-20, w + 20), rnd.uniform(-20, h + 20), rnd.uniform(12, 19)
        d.ellipse((x - r * 0.62, y - r * 0.62, x + r * 0.62, y + r * 0.62), fill=(200, 146, 78))
        a0 = rnd.uniform(0, 360)
        for k in range(rnd.randint(3, 5)):
            s = a0 + k * 360 / 5 + rnd.uniform(-10, 10)
            d.arc((x - r, y - r, x + r, y + r), s, s + rnd.uniform(40, 62), fill=BROWN, width=int(r * rnd.uniform(0.24, 0.34)))
        for _ in range(rnd.randint(0, 2)):
            dx, dy, rr = rnd.uniform(-r * 1.4, r * 1.4), rnd.uniform(-r * 1.4, r * 1.4), rnd.uniform(2, 4.5)
            d.ellipse((x + dx - rr, y + dy - rr, x + dx + rr, y + dy + rr), fill=(96, 56, 26))
    return im.filter(ImageFilter.GaussianBlur(0.9))


# ---------------------------------------------------------------------------------------------------- text helpers
def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / file), size)


def split_lines(text: str) -> List[str]:
    """One line if short, otherwise two balanced lines (never splits a word)."""
    words = text.split()
    if len(text) <= 17 or len(words) < 2:
        return [text]
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def fit_size(file: str, lines: List[str], max_w: int, start: int) -> int:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    s = start
    while s > 60:
        f = _font(file, s)
        if all(probe.textlength(l, font=f) <= max_w for l in lines):
            return s
        s -= 6
    return 60


def straight_mask(size: Tuple[int, int], lines: List[str], file: str, fs: int, cx: int, y: int, gap: int = 30) -> Tuple[Image.Image, int]:
    """Draw lines centred on cx starting at y. Returns (mask, bottom y)."""
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    f = _font(file, fs)
    for l in lines:
        bb = d.textbbox((0, 0), l, font=f)
        d.text((cx - (bb[0] + bb[2]) / 2, y - bb[1]), l, font=f, fill=255)
        y += (bb[3] - bb[1]) + gap
    return m, y - gap


def arc_mask(size: Tuple[int, int], text: str, file: str, fs: int, cx: int, cy: float, radius: float, top: bool) -> Image.Image:
    """Characters placed along a circle: top=True arches over (cap tops outward), top=False is a smile under."""
    m = Image.new("L", size, 0)
    f = _font(file, fs)
    adv = [f.getlength(c) for c in text]
    total = sum(adv) / radius
    th = -total / 2
    S = int(fs * 1.9)
    for c, a in zip(text, adv):
        mid = th + (a / radius) / 2
        th += a / radius
        if c == " ":
            continue
        tile = Image.new("L", (S, S), 0)
        ImageDraw.Draw(tile).text((S / 2, S / 2), c, font=f, fill=255, anchor="mm")
        deg = math.degrees(mid)
        rot = tile.rotate(-deg if top else deg, resample=Image.BICUBIC, expand=True)
        px = cx + radius * math.sin(mid)
        py = cy - radius * math.cos(mid) if top else cy + radius * math.cos(mid)
        x0, y0 = int(px - rot.width / 2), int(py - rot.height / 2)
        m.paste(255, (x0, y0, x0 + rot.width, y0 + rot.height), rot)
    return m


def colorize(mask: Image.Image, fill, outline: Optional[Tuple[int, int, int]] = None, stroke: int = 0) -> Image.Image:
    layer = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    if outline and stroke:
        om = mask.filter(ImageFilter.MaxFilter(2 * stroke + 1))
        o = Image.new("RGBA", mask.size, outline + (255,))
        o.putalpha(om)
        layer.alpha_composite(o)
    f = fill if isinstance(fill, Image.Image) else Image.new("RGB", mask.size, fill)
    f = f.convert("RGBA")
    f.putalpha(mask)
    layer.alpha_composite(f)
    return layer


def prep_art(art: Image.Image) -> Image.Image:
    """Remove the cyan key spill from the fur/feather edge band, trim a 1 px rim, and feather the bottom edge when the AI cropped the
    subject at the frame (a flat cut line) so it reads as a soft watercolor fade instead of a hard edge."""
    from scipy import ndimage as ndi
    a = np.asarray(art).astype(np.float32)
    al = a[..., 3] / 255.0
    solid = al > 0.5
    band = ndi.binary_dilation(solid, iterations=20) & ~ndi.binary_erosion(solid, iterations=20)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    spill = np.clip(np.minimum(g, b) - r, 0, None) * band
    a[..., 1] = g - spill * 1.15
    a[..., 2] = b - spill * 1.15
    al = ndi.minimum_filter(al, size=3)
    h = al.shape[0]
    flat = (al[int(h * 0.97):] > 0.5).any(axis=0).mean() > 0.12      # a wide opaque run on the last rows = cut by the frame
    if flat:
        fade = int(h * 0.11)
        ramp = np.ones(h, np.float32)
        ramp[h - fade:] = np.linspace(1, 0, fade) ** 1.4
        al = al * ramp[:, None]
    a[..., 3] = np.clip(al, 0, 1) * 255
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------------------------------------------- composition
def compose(art_path: Path, top: str, bottom: str, idx: int, out: Path) -> Path:
    art = prep_art(Image.open(art_path).convert("RGBA"))
    bb = art.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb:
        art = art.crop(bb)
    s = min(2100 / art.width, 1850 / art.height)
    art = art.resize((max(1, round(art.width * s)), max(1, round(art.height * s))), Image.LANCZOS)
    tf, bf = TOP_FONTS[idx % 4], BOT_FONTS[idx % 4]
    tl, bl = split_lines(top), split_lines(bottom)
    tcol = CHARCOAL if idx % 2 == 0 else NAVY
    arch = idx % 3 == 0 and len(tl) == 1 and len(bl) == 1
    CW, CH, cx = 2600, 4200, 1300
    tex = leopard(CW, CH, seed=idx * 13 + 5)
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    margin = 70
    if arch:
        fs_t = min(fit_size(tf, tl, 1500, 300), 300)
        fs_b = min(fit_size(bf, bl, 1500, 300), 300)
        ft, fb = _font(tf, fs_t), _font(bf, fs_b)
        tw, bw = sum(ft.getlength(c) for c in tl[0]), sum(fb.getlength(c) for c in bl[0])
        rt, rb = max(2300.0, tw / 0.8), max(2300.0, bw / 0.8)
        apex = margin + fs_t * 0.55
        cy_t = apex + rt
        art_top = int(apex + fs_t * 0.55 + 40 + 0.8 * rt * (1 - math.cos(tw / rt / 2)))
        canvas.alpha_composite(colorize(arc_mask((CW, CH), tl[0], tf, fs_t, cx, cy_t, rt, True), tcol), (0, 0))
        canvas.alpha_composite(art, (cx - art.width // 2, art_top))
        art_bot = art_top + art.height
        edge = math.cos(bw / rb / 2)
        cy_b = art_bot + 40 + fs_b * 0.55 - rb * edge
        bm = arc_mask((CW, CH), bl[0], bf, fs_b, cx, cy_b, rb, False)
        canvas.alpha_composite(colorize(bm, tex, BROWN, 5), (0, 0))
    else:
        fs_t = fit_size(tf, tl, MAX_W, 330)
        fs_b = fit_size(bf, bl, MAX_W, 360)
        tm, y = straight_mask((CW, CH), tl, tf, fs_t, cx, margin)
        canvas.alpha_composite(colorize(tm, tcol), (0, 0))
        art_top = y + 60
        canvas.alpha_composite(art, (cx - art.width // 2, art_top))
        bm, _ = straight_mask((CW, CH), bl, bf, fs_b, cx, art_top + art.height + 60)
        canvas.alpha_composite(colorize(bm, tex, BROWN, 5), (0, 0))
    box = canvas.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    canvas = canvas.crop(box)
    pad = 40
    final = Image.new("RGBA", (canvas.width + 2 * pad, canvas.height + 2 * pad), (0, 0, 0, 0))
    final.paste(canvas, (pad, pad))
    out.parent.mkdir(parents=True, exist_ok=True)
    K.save_adaptive(final, out)
    return out


# ---------------------------------------------------------------------------------------------------- pipeline
def caption_for(sk: str) -> Tuple[str, str]:
    for k, _s, t, b in SASS:
        if k == sk:
            return t, b
    raise KeyError(sk)


def contact_sheets(tiles: List[Tuple[str, Path]], out: Path) -> None:
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    S, cols, rows = 480, 4, 3
    for si in range(0, len(tiles), cols * rows):
        sh = Image.new("RGB", (S * cols, S * rows), (255, 255, 255))
        d = ImageDraw.Draw(sh)
        for i, (nm, p) in enumerate(tiles[si:si + cols * rows]):
            im = Image.open(p).convert("RGBA")
            im.thumbnail((S - 16, S - 34))
            x, y = (i % cols) * S, (i // cols) * S
            sh.paste(im, (x + (S - im.width) // 2, y + 6 + (S - 34 - im.height) // 2), im)
            d.text((x + 8, y + S - 22), nm[:48], fill=(60, 60, 60))
        sh.save(out / f"sheet_{si // (cols * rows) + 1:02d}.jpg", quality=90)


def run(only: Optional[List[int]] = None, recompose: bool = False, redo: Tuple[str, ...] = ()) -> None:
    G.DEFAULT_ENGINE = "flux"
    base = ROOT / PACK.slug
    raw, art, png = base / "raw", base / "art", base / "png"
    jl = P.jobs(PACK, styles_per_subject=1)
    if only:
        jl = [j for i, j in enumerate(jl, 1) if i in only]
    for nm in redo:
        for j in jl:
            if nm in j[0]:
                for d in (raw, art, png):
                    (d / f"{j[0]}.png").unlink(missing_ok=True)
    t0 = time.time()
    print(f"[sass] generate {len(jl)} (FLUX Krea)", flush=True)
    jobs = [(n, p, s + (1000 if any(r in n for r in redo) else 0)) for n, p, s, _sk, _st in jl]
    res = G.generate_many(jobs, raw, parallel=2, progress=lambda i, n, nm: print(f"  gen [{i}/{n}] {nm} t={time.time() - t0:.0f}s", flush=True))
    art.mkdir(exist_ok=True)
    tiles = []
    for idx, (name, _p, _s, sk, _st) in enumerate(jl):
        src = res.get(name)
        if not src:
            print(f"  ! no image {name}")
            continue
        if not (art / f"{name}.png").exists():
            mask = MC.matte_mask(src)
            st = K.cut_key(src, art / f"{name}.png", long_side=2200, matte=mask, hole_frac=0.06) if mask is not None else None
            if not st:
                print(f"  ! cut failed {name}")
                continue
        top, bottom = caption_for(sk)
        n_index = [j[0] for j in P.jobs(PACK, styles_per_subject=1)].index(name)
        dst = png / f"{name}.png"
        if recompose or not dst.exists():
            compose(art / f"{name}.png", top, bottom, n_index, dst)
        tiles.append((name, dst))
        print(f"  done {name}: {Image.open(dst).size} {dst.stat().st_size / 1e6:.2f}MB", flush=True)
    contact_sheets(tiles, base / "sheets")
    print(f"[sass] {len(tiles)} designs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    a = sys.argv
    only = [int(x) for x in a[a.index("--only") + 1].split(",")] if "--only" in a else None
    redo = tuple(a[a.index("--redo") + 1].split(",")) if "--redo" in a else ()
    run(only, "--recompose" in a, redo)
