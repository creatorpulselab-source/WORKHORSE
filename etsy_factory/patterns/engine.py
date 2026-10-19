"""Procedural seamless patterns. Every pattern is drawn on a TT x TT supersampled tile with 3x3 wrap-around so it tiles perfectly,
then downscaled to a T x T tile. No AI is involved - these are plain geometry, so they are original work and print crisp.

Palette = dict(bg, a, b, c, d) of RGB tuples.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

RGB = Tuple[int, int, int]
SS = 2
T = 1200                 # final tile size in px
TT = T * SS              # supersampled tile
OFFS = [(dx * TT, dy * TT) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


# ----------------------------------------------------------------------------- palettes
PALETTES: Dict[str, Dict[str, RGB]] = {
    "retro_boho": dict(bg=(248, 238, 220), a=(196, 98, 62), b=(124, 150, 118), c=(226, 168, 52), d=(110, 66, 46)),
    "blush":      dict(bg=(252, 240, 234), a=(226, 140, 148), b=(176, 110, 130), c=(232, 188, 130), d=(214, 190, 176)),
    "valentine":  dict(bg=(255, 232, 238), a=(214, 38, 76), b=(246, 128, 160), c=(112, 40, 88), d=(255, 255, 255)),
    "retro_xmas": dict(bg=(250, 242, 224), a=(190, 36, 44), b=(36, 112, 84), c=(232, 170, 52), d=(34, 140, 150)),
    "spring":     dict(bg=(255, 246, 214), a=(250, 170, 140), b=(150, 208, 176), c=(196, 164, 226), d=(244, 120, 110)),
    "coastal":    dict(bg=(250, 246, 236), a=(32, 140, 150), b=(28, 56, 104), c=(240, 130, 110), d=(228, 210, 176)),
    "earth":      dict(bg=(240, 230, 210), a=(176, 92, 50), b=(110, 120, 70), c=(86, 58, 42), d=(214, 188, 140)),
    "berry":      dict(bg=(246, 240, 250), a=(104, 40, 110), b=(214, 52, 130), c=(250, 150, 60), d=(40, 160, 160)),
}
PALETTE_ORDER = list(PALETTES)


# ----------------------------------------------------------------------------- shape helpers
def _poly(d: ImageDraw.ImageDraw, pts: Sequence[Tuple[float, float]], fill: RGB) -> None:
    d.polygon([(float(x), float(y)) for x, y in pts], fill=fill)


def heart_pts(cx: float, cy: float, w: float, n: int = 90) -> List[Tuple[float, float]]:
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * w / 34.0, cy + (y + 2.5) * w / 34.0))
    return pts


def star_pts(cx: float, cy: float, R: float, inner: float = 0.46, rot: float = -90.0) -> List[Tuple[float, float]]:
    pts = []
    for i in range(10):
        r = R if i % 2 == 0 else R * inner
        a = math.radians(rot + i * 36)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse_pts(cx: float, cy: float, rx: float, ry: float, ang: float, n: int = 28) -> List[Tuple[float, float]]:
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def bolt_pts(cx: float, cy: float, s: float, rot_deg: float = -12.0) -> List[Tuple[float, float]]:
    base = [(0.12, -1.0), (-0.50, 0.12), (-0.06, 0.12), (-0.22, 1.0), (0.52, -0.22), (0.06, -0.22)]
    ca, sa = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    return [(cx + s * (x * ca - y * sa), cy + s * (x * sa + y * ca)) for x, y in base]


def grid_cells(cols: int, rows: int, shift: bool = True) -> List[Tuple[float, float, int, int]]:
    """Cell centres on the tile; odd rows shifted half a cell (rows must be even so the pattern still wraps)."""
    W, H = TT / cols, TT / rows
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append(((c + 0.5 + (0.5 if (shift and r % 2) else 0.0)) * W, (r + 0.5) * H, r, c))
    return out


def new_tile(pal: Dict[str, RGB]) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (TT, TT), pal["bg"])
    return img, ImageDraw.Draw(img)


# ----------------------------------------------------------------------------- pattern generators: (pal, rng) -> RGB image TT x TT
def p_checker(pal, rng):
    img, d = new_tile(pal)
    n = 8
    s = TT / n
    for i in range(n):
        for j in range(n):
            x0, y0 = i * s, j * s
            if (i + j) % 2:
                d.rectangle((x0, y0, x0 + s, y0 + s), fill=pal["a"])
                d.rectangle((x0 + s * .32, y0 + s * .32, x0 + s * .68, y0 + s * .68), fill=pal["b"])
            else:
                d.ellipse((x0 + s * .38, y0 + s * .38, x0 + s * .62, y0 + s * .62), fill=pal["c"])
    return img


def p_stripes(pal, rng):
    img, d = new_tile(pal)
    n = 12
    w = TT / n
    cols = [pal["a"], pal["bg"], pal["b"], pal["bg"], pal["c"], pal["bg"]]
    for i in range(n):
        d.rectangle((i * w, 0, (i + 1) * w + 1, TT), fill=cols[i % 6])
    for i in range(n):
        if i % 6 in (1, 3, 5):
            d.rectangle((i * w + w * .45, 0, i * w + w * .55, TT), fill=pal["d"])
    return img


def p_waves(pal, rng):
    img, d = new_tile(pal)
    nb, freq, amp = 10, 3, TT * 0.028
    cols = [pal["bg"], pal["a"], pal["b"], pal["c"], pal["d"]]
    xs = list(range(0, TT + 1, 8))

    def edge(k):
        return [(x, k * TT / nb + amp * math.sin(2 * math.pi * freq * x / TT)) for x in xs]

    for k in range(-1, nb + 1):
        top, bot = edge(k), edge(k + 1)
        _poly(d, top + bot[::-1], cols[k % 5])
    return img


def p_arches(pal, rng):
    img, d = new_tile(pal)
    cols_n, rows_n = 3, 4
    W, H = TT / cols_n, TT / rows_n
    R = W * 0.46
    levels = [(1.0, pal["a"]), (0.80, pal["b"]), (0.60, pal["c"]), (0.40, pal["bg"]), (0.22, pal["d"])]
    for r in range(rows_n):
        for c in range(cols_n):
            cx = (c + 0.5 + (0.5 if r % 2 else 0.0)) * W
            cy = (r + 0.78) * H
            for ox, oy in OFFS:
                for k, col in levels:
                    rr = R * k
                    d.pieslice((cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr), 180, 360, fill=col)
    return img


def p_daisies(pal, rng):
    img, d = new_tile(pal)
    W = TT / 3
    R = W * 0.40
    for cx, cy, r, c in grid_cells(3, 4):
        pc = pal["a"] if (r + c) % 2 == 0 else pal["b"]
        for ox, oy in OFFS:
            for k in range(12):
                a = math.radians(k * 30)
                _poly(d, ellipse_pts(cx + ox + math.cos(a) * R * .58, cy + oy + math.sin(a) * R * .58, R * .44, R * .20, a), pc)
            d.ellipse((cx + ox - R * .26, cy + oy - R * .26, cx + ox + R * .26, cy + oy + R * .26), fill=pal["c"])
    for cx, cy, r, c in grid_cells(3, 4):
        for ox, oy in OFFS:
            x, y = cx + ox, cy + oy + TT / 8
            d.ellipse((x - 26, y - 26, x + 26, y + 26), fill=pal["d"])
    return img


def p_hearts(pal, rng):
    img, d = new_tile(pal)
    W = TT / 3
    ws = [pal["a"], pal["b"], pal["c"]]
    for cx, cy, r, c in grid_cells(3, 4):
        for ox, oy in OFFS:
            _poly(d, heart_pts(cx + ox, cy + oy, W * 0.62), ws[(r + c) % 3])
            _poly(d, heart_pts(cx + ox, cy + oy, W * 0.30), pal["bg"])
    return img


def p_stars(pal, rng):
    img, d = new_tile(pal)
    W = TT / 3
    ws = [pal["a"], pal["b"], pal["c"]]
    for cx, cy, r, c in grid_cells(3, 4):
        for ox, oy in OFFS:
            _poly(d, star_pts(cx + ox, cy + oy, W * 0.36), ws[(r + c) % 3])
            x, y = cx + ox, cy + oy + TT / 8
            d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=pal["d"])
    return img


def p_dots(pal, rng):
    img, d = new_tile(pal)
    ws = [pal["a"], pal["b"], pal["c"]]
    W = TT / 6
    for cx, cy, r, c in grid_cells(6, 8):
        rr = W * (0.30 if (r + c) % 2 == 0 else 0.20)
        for ox, oy in OFFS:
            d.ellipse((cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr), fill=ws[(r + c) % 3])
    return img


def p_rings(pal, rng):
    img, d = new_tile(pal)
    W = TT / 3
    for cx, cy, r, c in grid_cells(3, 4):
        order = [pal["a"], pal["b"], pal["c"], pal["d"]]
        if (r + c) % 2:
            order = order[::-1]
        for ox, oy in OFFS:
            for k, rad in enumerate((0.46, 0.35, 0.24, 0.13)):
                rr = W * rad
                d.ellipse((cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr), fill=order[k])
    return img


def p_gingham(pal, rng):
    base = Image.new("RGBA", (TT, TT), pal["bg"] + (255,))
    n = 12
    s = TT / n
    for horizontal in (True, False):
        layer = Image.new("RGBA", (TT, TT), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for i in range(0, n, 2):
            box = (0, i * s, TT, (i + 1) * s) if horizontal else (i * s, 0, (i + 1) * s, TT)
            ld.rectangle(box, fill=pal["a"] + (140,))
        base.alpha_composite(layer)
    layer = Image.new("RGBA", (TT, TT), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(0, n, 2):
        for j in range(0, n, 2):
            ld.rectangle((i * s + s * .38, j * s + s * .38, i * s + s * .62, j * s + s * .62), fill=pal["b"] + (180,))
    base.alpha_composite(layer)
    return base.convert("RGB")


def p_leopard(pal, rng):
    img, d = new_tile(pal)
    blobs: List[Tuple[float, float, float]] = []
    tries = 0
    while len(blobs) < 44 and tries < 6000:
        tries += 1
        x, y, r = rng.uniform(0, TT), rng.uniform(0, TT), rng.uniform(0.040, 0.066) * TT
        ok = True
        for bx, by, br in blobs:
            dx, dy = abs(x - bx), abs(y - by)
            dx, dy = min(dx, TT - dx), min(dy, TT - dy)
            if math.hypot(dx, dy) < (r + br) * 1.30:
                ok = False
                break
        if ok:
            blobs.append((x, y, r))
    for x, y, r in blobs:
        nb = 16
        noise = [0.82 + 0.36 * rng.random() for _ in range(nb)]
        rot = rng.uniform(0, 2 * math.pi)

        def shape(scale, dx=0.0, dy=0.0):
            return [(dx + scale * r * noise[i] * math.cos(rot + 2 * math.pi * i / nb), dy + scale * r * noise[i] * math.sin(rot + 2 * math.pi * i / nb)) for i in range(nb)]

        for ox, oy in OFFS:
            outer = [(x + ox + px, y + oy + py) for px, py in shape(1.0)]
            inner = [(x + ox + px, y + oy + py) for px, py in shape(0.66, r * 0.10, r * 0.06)]
            _poly(d, outer, pal["c"])
            _poly(d, inner, pal["a"])
            _poly(d, [(x + ox + px, y + oy + py) for px, py in shape(0.22, r * 0.12, r * 0.08)], pal["d"])
    return img


def p_bolts(pal, rng):
    img, d = new_tile(pal)
    ws = [pal["a"], pal["b"], pal["c"]]
    H = TT / 4
    for cx, cy, r, c in grid_cells(4, 4):
        for ox, oy in OFFS:
            _poly(d, bolt_pts(cx + ox, cy + oy, H * 0.40), ws[(r + c) % 3])
            x, y = cx + ox + TT / 8, cy + oy + H * 0.02
            _poly(d, star_pts(x, y, 60, 0.4), pal["d"])
    return img


def p_argyle(pal, rng):
    img, d = new_tile(pal)
    n = 4
    W = TT / n
    for i in range(-1, n + 1):
        for j in range(-1, n + 1):
            cx, cy = i * W, j * W
            _poly(d, [(cx, cy - W / 2), (cx + W / 2, cy), (cx, cy + W / 2), (cx - W / 2, cy)], pal["a"])
            hx, hy = cx + W / 2, cy + W / 2
            _poly(d, [(hx, hy - W * .36), (hx + W * .36, hy), (hx, hy + W * .36), (hx - W * .36, hy)], pal["b"])
            _poly(d, [(hx, hy - W * .16), (hx + W * .16, hy), (hx, hy + W * .16), (hx - W * .16, hy)], pal["bg"])
    return img


GENERATORS: Dict[str, Callable] = {
    "checker": p_checker, "stripes": p_stripes, "waves": p_waves, "arches": p_arches, "daisies": p_daisies,
    "hearts": p_hearts, "stars": p_stars, "dots": p_dots, "rings": p_rings, "gingham": p_gingham,
    "leopard": p_leopard, "bolts": p_bolts, "argyle": p_argyle,
}
TYPE_ORDER = list(GENERATORS)


def palette_names_for(type_idx: int, count: int = 4) -> List[str]:
    return [PALETTE_ORDER[(type_idx + k * 2) % len(PALETTE_ORDER)] for k in range(count)]


def make_tile(kind: str, pal_name: str, seed: int = 7) -> Image.Image:
    """Return the T x T seamless RGB tile."""
    rng = random.Random(seed * 1000 + sum(map(ord, kind + pal_name)))
    big = GENERATORS[kind](PALETTES[pal_name], rng)
    return big.resize((T, T), Image.LANCZOS)


def tile_to(tile: Image.Image, w: int, h: int, tile_px: int) -> Image.Image:
    """Repeat `tile` (scaled to tile_px) across a w x h canvas starting at the top-left corner."""
    t = tile.resize((tile_px, tile_px), Image.LANCZOS) if tile.width != tile_px else tile
    out = Image.new("RGB", (w, h))
    for y in range(0, h, tile_px):
        for x in range(0, w, tile_px):
            out.paste(t, (x, y))
    return out


def seam_error(tile: Image.Image) -> float:
    """Mean abs difference between the tile's opposite edges and its interior neighbour columns - near the interior gradient = seamless."""
    import numpy as np
    a = np.asarray(tile.convert("RGB")).astype("float32")
    edge = np.abs(a[:, 0] - a[:, -1]).mean() + np.abs(a[0] - a[-1]).mean()
    inner = np.abs(a[:, 600] - a[:, 601]).mean() + np.abs(a[600] - a[601]).mean()
    return float(edge - inner)
