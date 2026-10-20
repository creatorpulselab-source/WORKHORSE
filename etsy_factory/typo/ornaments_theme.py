"""Themed ornament icons for the military-family and magical-vacation quote packs (shapely, y-UP, centred near the origin).

Every shape is original geometry (generic fairy-tale castle, wand, balloon, anchor, dog tag, combat boot, ship wheel) - no
licensed characters, logos, seals or emblems. `place()` is called from templates.add_ornaments.
"""
from __future__ import annotations

import math
import random
from typing import Tuple

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from . import ornaments as O

KINDS = ("castle", "wand", "balloon", "anchor", "dogtag", "boot", "wheel")


def _arch(cx: float, y0: float, w: float, h: float) -> BaseGeometry:
    """Window / door opening: rectangle with a round top, base at y0."""
    r = w / 2
    return unary_union([box(cx - r, y0, cx + r, y0 + h - r), O.circle(r, (cx, y0 + h - r), 48)])


def _centre(g: BaseGeometry) -> BaseGeometry:
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)


def castle(h: float) -> BaseGeometry:
    """Symmetric fairy-tale castle: tall centre tower with a pennant, two mid towers, two corner turrets, arched gate."""
    parts, holes = [], []

    def tower(cx, tw, th, roof, flag=False):
        parts.append(box(cx - tw / 2, 0, cx + tw / 2, th))
        parts.append(Polygon([(cx - tw * 0.70, th), (cx + tw * 0.70, th), (cx, th + roof)]))
        if flag:
            top = th + roof
            parts.append(box(cx - tw * 0.035, top - roof * 0.05, cx + tw * 0.035, top + roof * 0.5))
            parts.append(Polygon([(cx + tw * 0.035, top + roof * 0.5), (cx + tw * 0.035 + roof * 0.62, top + roof * 0.36),
                                  (cx + tw * 0.035, top + roof * 0.22)]))
        holes.append(_arch(cx, th * 0.55, tw * 0.34, th * 0.28))

    parts.append(box(-0.50 * h, 0, 0.50 * h, 0.27 * h))
    for i in range(-5, 6):                                    # battlements along the wall top
        parts.append(box(i * 0.085 * h - 0.028 * h, 0.27 * h, i * 0.085 * h + 0.028 * h, 0.31 * h))
    tower(0.0, 0.22 * h, 0.56 * h, 0.24 * h, flag=True)
    for s in (-1, 1):
        tower(s * 0.28 * h, 0.15 * h, 0.44 * h, 0.19 * h)
        tower(s * 0.45 * h, 0.105 * h, 0.35 * h, 0.15 * h)
    g = unary_union(parts)
    holes.append(_arch(0.0, 0.0, 0.11 * h, 0.17 * h))        # gate
    for s in (-1, 1):
        holes.append(_arch(s * 0.155 * h, 0.07 * h, 0.05 * h, 0.1 * h))
    g = g.difference(unary_union(holes))
    return _centre(O.soften(g, h * 0.006))


def wand(h: float) -> BaseGeometry:
    """Magic wand with a star tip and two sparkles, tilted up to the right."""
    stick = O.LineString([(-0.34 * h, -0.46 * h), (0.10 * h, 0.14 * h)]).buffer(h * 0.032, cap_style=1)
    tip = affinity.translate(O.star(h * 0.24, 5, 0.46), 0.17 * h, 0.27 * h)
    sp1 = affinity.translate(O.sparkle(h * 0.1), 0.40 * h, 0.02 * h)
    sp2 = affinity.translate(O.sparkle(h * 0.075), -0.1 * h, 0.40 * h)
    return _centre(unary_union([stick, tip, sp1, sp2]))


def balloon(h: float) -> BaseGeometry:
    """Party balloon with a knot, curly string and a highlight cut-out."""
    body = affinity.scale(O.circle(0.3 * h, (0, 0.16 * h)), 1.0, 1.2, origin=(0, 0.16 * h))
    knot = Polygon([(0, -0.185 * h), (-0.05 * h, -0.26 * h), (0.05 * h, -0.26 * h)])
    string = O.tapered(O._bez((0, -0.26 * h), (-0.14 * h, -0.36 * h), (0.14 * h, -0.46 * h), (0.0, -0.58 * h)), h * 0.028, 0.3)
    shine = affinity.rotate(affinity.scale(O.circle(0.055 * h, (-0.14 * h, 0.3 * h)), 0.6, 1.5), 25, origin=(-0.14 * h, 0.3 * h))
    return _centre(unary_union([body.difference(shine), knot, string]))


def anchor(h: float) -> BaseGeometry:
    """Classic anchor: ring, shaft, stock, curved arms with pointed flukes."""
    shaft = box(-0.035 * h, -0.4 * h, 0.035 * h, 0.3 * h)
    top = affinity.translate(O.ring(0.09 * h, 0.038 * h), 0, 0.38 * h)
    stock = affinity.translate(O.bar(0.32 * h, 0.05 * h), 0, 0.2 * h)
    arc = affinity.translate(O.ring(0.30 * h, 0.05 * h), 0, -0.1 * h).intersection(box(-h, -h, h, -0.1 * h))
    flukes = [Polygon([(s * 0.21 * h, -0.1 * h), (s * 0.35 * h, -0.1 * h), (s * 0.325 * h, 0.0)]) for s in (-1, 1)]
    return _centre(O.soften(unary_union([shaft, top, stock, arc] + flukes), h * 0.006))


def dogtag(h: float) -> BaseGeometry:
    """Dog tag on a key ring with an inner border groove and a star cut-out."""
    w, th = 0.6 * h, 0.95 * h
    tag = O.rounded_rect(w, th, 0.15 * h)
    groove = O.rounded_rect(w - 0.1 * h, th - 0.1 * h, 0.11 * h).difference(O.rounded_rect(w - 0.15 * h, th - 0.15 * h, 0.1 * h))
    tag = tag.difference(groove).difference(O.circle(0.04 * h, (0, th / 2 - 0.1 * h))).difference(affinity.translate(O.star(0.13 * h), 0, -0.02 * h))
    ring = affinity.translate(O.ring(0.075 * h, 0.028 * h), 0, th / 2 + 0.005 * h)
    return _centre(unary_union([tag, ring]))


def boot(h: float) -> BaseGeometry:
    """Combat boot (toe to the right): tall shaft, rounded toe, heel block with an arch gap, lace bars and a cuff line."""
    pts = [(0.03, 0.0), (0.86, 0.0), (0.89, 0.06), (0.85, 0.15), (0.71, 0.20), (0.57, 0.25), (0.53, 0.33), (0.53, 1.0), (0.15, 1.0),
           (0.14, 0.42), (0.09, 0.25), (0.01, 0.12)]
    g = Polygon([(x * h, y * h) for x, y in pts])
    cuts = [Polygon([(0.30 * h, -0.01 * h), (0.52 * h, -0.01 * h), (0.47 * h, 0.05 * h), (0.34 * h, 0.05 * h)])]   # arch under the instep
    for i in range(5):                                        # lace bars across the front of the shaft
        y = (0.40 + i * 0.105) * h
        cuts.append(O.LineString([(0.22 * h, y), (0.47 * h, y + 0.035 * h)]).buffer(h * 0.017, cap_style=1))
    cuts.append(O.LineString([(0.0, 0.075 * h), (0.9 * h, 0.075 * h)]).buffer(h * 0.009, cap_style=2).intersection(g.buffer(-h * 0.001)))
    cuts.append(O.LineString([(0.14 * h, 0.9 * h), (0.54 * h, 0.9 * h)]).buffer(h * 0.011, cap_style=2))
    g = g.difference(unary_union(cuts))
    return _centre(O.soften(g, h * 0.008))


def wheel(h: float) -> BaseGeometry:
    """Ship's wheel: rim, hub and eight spokes with handle knobs."""
    parts = [O.ring(0.3 * h, 0.05 * h), O.circle(0.075 * h)]
    for i in range(8):
        a = math.radians(i * 45)
        ex, ey = 0.43 * h * math.cos(a), 0.43 * h * math.sin(a)
        parts.append(O.LineString([(0, 0), (ex, ey)]).buffer(h * 0.022, cap_style=1))
        parts.append(O.circle(0.04 * h, (ex, ey), 32))
    return _centre(unary_union(parts))


_BUILD = dict(castle=castle, wand=wand, balloon=balloon, anchor=anchor, dogtag=dogtag, boot=boot, wheel=wheel)


def place(kind: str, bounds: Tuple[float, float, float, float], unit: float, rng: random.Random) -> BaseGeometry:
    """Return the ornament positioned above the text block (like the existing cross / mug ornaments)."""
    x0, y0, x1, y1 = bounds
    cx = (x0 + x1) / 2
    size = {"castle": 2.6, "wand": 2.1, "balloon": 2.3, "anchor": 2.1, "dogtag": 2.1, "boot": 2.0, "wheel": 2.1}[kind] * unit
    g = _BUILD[kind](size)
    if kind in ("castle", "anchor"):
        dx, dy = cx, y1 + unit * 0.45 + size * 0.5
    elif kind in ("wand", "dogtag", "wheel"):
        dx, dy = x1 - unit * 0.5, y1 + unit * 0.4 + size * 0.5
    else:                                                     # balloon, boot sit top-left
        dx, dy = x0 + unit * 0.5, y1 + unit * 0.4 + size * 0.5
    return affinity.translate(g, dx, dy)
