"""Vibrant 'top-seller style' cover: tilted colourful card collage, giant 3D gold number, ribbons, starburst, feature strip.

Built to match what the best sellers on Etsy do (screenshots in research/): dense colourful proof of the real contents, a
huge number as the hook, heavy outlined type, badge strip - but every claim on it is true for the pack.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import media as M

RGB = Tuple[int, int, int]
SIZE = M.SIZE


def _mask_text(size, xy, t, f, anchor, stroke=0) -> Image.Image:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).text(xy, t, font=f, fill=255, anchor=anchor, stroke_width=stroke)
    return m


def power_text(img: Image.Image, xy, t: str, f, top: RGB, bottom: RGB, stroke: RGB, sw: int, extrude: int = 0,
               ex_col: RGB = (0, 0, 0), anchor: str = "mm", shine: bool = True) -> Tuple[int, int, int, int]:
    """Gradient-filled, thick-outlined, optionally extruded (3D) text. Returns the stroked bbox."""
    ms = _mask_text(img.size, xy, t, f, anchor, sw)
    bb = ms.getbbox()
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 120), (0, extrude + 14), ms.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(sh)
    for k in range(extrude, 0, -2):
        img.paste(ex_col + (255,), (0, k), ms)
    img.paste(stroke + (255,), (0, 0), ms)
    m = _mask_text(img.size, xy, t, f, anchor, 0)
    x0, y0, x1, y1 = m.getbbox()
    h = max(1, y1 - y0)
    ramp = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    col = (np.array(top, np.float32) * (1 - ramp) + np.array(bottom, np.float32) * ramp)
    grad = Image.new("RGB", img.size, bottom)
    grad.paste(Image.fromarray(np.repeat(col, x1 - x0, axis=1).astype(np.uint8)), (x0, y0))
    img.paste(grad, (0, 0), m)
    if shine:   # light band across the upper third of the glyphs
        band = Image.new("L", img.size, 0)
        ImageDraw.Draw(band).rectangle((x0, y0 + int(h * 0.10), x1, y0 + int(h * 0.30)), fill=70)
        img.paste((255, 255, 255), (0, 0), Image.composite(band, Image.new("L", img.size, 0), m))
    return bb


def ribbon(img: Image.Image, cx: int, cy: int, w: int, h: int, col: RGB, dark: RGB, ink: RGB, text: str, font, tcol: RGB = (255, 255, 255),
           tail: int = 120) -> None:
    d = ImageDraw.Draw(img)
    for sgn in (-1, 1):
        xi, xo = cx + sgn * (w // 2 - 30), cx + sgn * (w // 2 + tail)
        pts = [(xi, cy - h // 2 + 34), (xo, cy - h // 2 + 34), (xo - sgn * 56, cy + 34), (xo, cy + h // 2 + 34), (xi, cy + h // 2 + 34)]
        d.polygon(pts, fill=dark, outline=ink, width=7)
        d.polygon([(xi, cy + h // 2), (xi + sgn * 0, cy + h // 2 + 34), (xi - sgn * 40, cy + h // 2)], fill=ink)
    d.rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), fill=col, outline=ink, width=8)
    d.rectangle((cx - w // 2 + 14, cy - h // 2 + 14, cx + w // 2 - 14, cy + h // 2 - 14), outline=(255, 255, 255, 140), width=3)
    d.text((cx + 5, cy + 7), text, font=font, fill=ink, anchor="mm")
    d.text((cx, cy), text, font=font, fill=tcol, anchor="mm", stroke_width=4, stroke_fill=ink)


def starburst(img: Image.Image, cx: int, cy: int, r: int, fill: RGB, ink: RGB, lines: Sequence[str], font, rot: float = -12, spikes: int = 22) -> None:
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = []
    for q in range(spikes * 2):
        a = math.pi * q / spikes
        rr = r if q % 2 == 0 else r * 0.78
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon([(cx + 14 + (p[0] - cx), cy + 18 + (p[1] - cy)) for p in pts], fill=(0, 0, 0, 120))
    d.polygon(pts, fill=fill + (255,), outline=ink + (255,), width=9)
    d.polygon([(cx + (p[0] - cx) * 0.86, cy + (p[1] - cy) * 0.86) for p in pts], outline=(255, 255, 255, 255), width=4)
    n = len(lines)
    for i, l in enumerate(lines):
        y = cy + (i - (n - 1) / 2) * font.size * 1.0
        d.text((cx, y), l, font=font, fill=ink + (255,), anchor="mm")
    lay = lay.rotate(rot, center=(cx, cy), resample=Image.BICUBIC)
    img.alpha_composite(lay)


def collage(meta, thumbs_dir: Path, seed: int, bg: RGB, edge_cols: Sequence[RGB]) -> Image.Image:
    rng = random.Random(seed)
    th = [t for t in M.load_thumbs(thumbs_dir, meta, colored=True)]
    big = int(SIZE * 1.55)
    base = Image.new("RGBA", (big, big), bg + (255,))
    order = th[:]
    rng.shuffle(order)
    row_h, gap = 350, 30
    y, k = -60, 0
    while y < big:
        x = -rng.randrange(0, 250)
        while x < big:
            t = order[k % len(order)]
            k += 1
            s = (row_h - 50) / t.height
            tw = min(int(t.width * s), 640)
            tt = t.resize((max(60, int(t.width * min(s, (640) / t.width))), int(t.height * min(s, 640 / t.width))), Image.LANCZOS)
            cw, ch = tt.width + 56, row_h
            card = M.rounded((cw, ch), 38, (255, 255, 255, 255), outline=rng.choice(edge_cols) + (255,), width=10)
            card.alpha_composite(tt.convert("RGBA"), ((cw - tt.width) // 2, (ch - tt.height) // 2))
            base.alpha_composite(card, (x, y))
            x += cw + gap
        y += row_h + gap
    base = base.rotate(8, resample=Image.BICUBIC, center=(big // 2, big // 2), fillcolor=bg + (255,))
    o = (big - SIZE) // 2
    return base.crop((o, o, o + SIZE, o + SIZE))


def vibrant(meta, thumbs_dir: Path, out: Path, big: str, kicker: str, title_lines: Sequence[str], sub: str, ribbon_cols: Sequence[Tuple[RGB, RGB]],
            ink: RGB, bg: RGB, badges: Sequence[Tuple[str, str, RGB]], burst: Sequence[str] = ("INSTANT", "DOWNLOAD"), seed: int = 5) -> Path:
    edge = [rc[0] for rc in ribbon_cols] + [(255, 183, 3)]
    img = collage(meta, thumbs_dir, seed, bg, edge)
    # central darkening glow so the type pops without hiding the designs at the edges
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((60, 180, SIZE - 60, SIZE - 330), fill=bg + (165,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150)))
    d = ImageDraw.Draw(img)
    gold_t, gold_b = (255, 236, 90), (255, 140, 0)


    y = 150
    rf = M.fit(d, kicker, M.anton, 1500, 170, 80)
    kb = d.textbbox((0, 0), kicker, font=rf, anchor="mm")
    rh = 240
    ribbon(img, SIZE // 2, y + rh // 2, kb[2] - kb[0] + 220, rh, ribbon_cols[0][0], ribbon_cols[0][1], ink, kicker, rf)
    y += rh + 100

    # giant 3D gold number: measure the glyph box on a scratch canvas, then place it exactly
    fb = M.anton(700)
    scratch = _mask_text((SIZE, SIZE * 2), (SIZE // 2, SIZE), big, fb, "mm", 30).getbbox()
    cy_num = y - (scratch[1] - SIZE)
    bb = power_text(img, (SIZE // 2, cy_num), big, fb, gold_t, gold_b, ink, 30, extrude=34, ex_col=(120, 40, 10), anchor="mm")
    y = bb[3] + 34 + 70

    for ln in title_lines:
        fl = M.fit(d, ln, M.anton, SIZE - 320, 175, 80)
        tb = power_text(img, (SIZE // 2, y + fl.size // 2), ln, fl, (255, 255, 255), (255, 214, 235), ink, 16, extrude=10, ex_col=ink, anchor="mm", shine=False)
        y = tb[3] + 10 + 34
    y += 20
    sf = M.fit(d, sub, M.poppins_x, 1500, 74, 36)
    sb = d.textbbox((0, 0), sub, font=sf, anchor="mm")
    sh = 160
    ribbon(img, SIZE // 2, y + sh // 2, sb[2] - sb[0] + 200, sh, ribbon_cols[1][0], ribbon_cols[1][1], ink, sub, sf, tail=100)
    sub_bottom = y + sh + 34

    # feature strip (all claims are true for the pack)
    sy0, sy1 = 2050, 2330
    assert sub_bottom < sy0 - 10, f"vibrant cover overlap: ribbon ends {sub_bottom}, strip starts {sy0}"
    strip = M.rounded((SIZE - 200, sy1 - sy0), 50, ink + (255,), outline=(255, 200, 40, 255), width=8)
    M.shadowed(img, strip, (100, sy0), blur=22, off=(0, 12), alpha=150)
    n = len(badges)
    cw = (SIZE - 200) // n
    for i, (lab, cap, col) in enumerate(badges):
        cx = 100 + cw * i + cw // 2
        sq = M.rounded((150, 110), 28, col + (255,), outline=(255, 255, 255, 255), width=5)
        img.alpha_composite(sq, (cx - 75, sy0 + 30))
        lf = M.fit(d, lab, M.anton, 130, 64, 28)
        d.text((cx, sy0 + 85), lab, font=lf, fill=(255, 255, 255), anchor="mm")
        for li, line in enumerate(cap.split("\n")):
            d.text((cx, sy0 + 178 + li * 44), line, font=M.poppins(34), fill=(255, 255, 255), anchor="mm")

    starburst(img, SIZE - 250, 330, 235, (255, 214, 0), ink, burst, M.anton(86))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=94, subsampling=0)
    return out
