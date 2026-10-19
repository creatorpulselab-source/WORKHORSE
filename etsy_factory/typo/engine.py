"""Engine: pick fonts/template per quote, finalize geometry to physical size (weld, clean, QA), produce designs."""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from . import fonts as F
from .templates import TEMPLATES, Ctx, Layered, parse
from .text import polys

TARGET_W_MM = 254.0        # 10 in
MAX_H_MM = 279.0           # 11 in
MIN_ISLAND_MM2 = 1.6
MIN_HOLE_MM2 = 1.0
MIN_STROKE_MM = 0.9


@dataclass
class Design:
    uid: str
    text: str
    template: str
    fonts: Dict[str, str]
    layers: Dict[str, BaseGeometry]     # physical mm, y-up, origin at lower-left of the whole design
    cut: BaseGeometry                   # welded single-colour silhouette
    width_in: float
    height_in: float
    nodes: int
    warnings: List[str] = field(default_factory=list)


def _clean(g: BaseGeometry) -> BaseGeometry:
    if g.is_empty:
        return g
    if not g.is_valid:
        g = make_valid(g)
    keep = []
    for p in polys(g):
        if p.area < MIN_ISLAND_MM2:
            continue
        holes = [r for r in p.interiors if Polygon(r).area >= MIN_HOLE_MM2]
        keep.append(Polygon(p.exterior, holes))
    return unary_union(keep) if keep else Polygon()


def min_stroke(g: BaseGeometry) -> float:
    """Smallest approximate stroke width (2*A/P) over the significant polygons."""
    vals = []
    for p in polys(g):
        if p.area > 12:
            per = p.length
            vals.append(2 * p.area / max(per, 1e-6))
    return min(vals) if vals else 99.0


def finalize(L: Layered, uid: str, text: str, fonts: Dict[str, str], width_mm: float = TARGET_W_MM) -> Design:
    whole = L.union()
    x0, y0, x1, y1 = whole.bounds
    w, h = x1 - x0, y1 - y0
    s = width_mm / w
    if h * s > MAX_H_MM:
        s = MAX_H_MM / h
    layers = {}
    for k, g in L.layers.items():
        g = affinity.scale(g, s, s, origin=(x0, y0))
        layers[k] = g
    warns: List[str] = []
    allg = unary_union(list(layers.values()))
    # weld: close hairline gaps (e.g. between touching script letters / ornament + text) then clean
    welded = allg.buffer(0.18, join_style=1).buffer(-0.18, join_style=1)
    ms = min_stroke(welded)
    grow = 0.0
    for _ in range(3):
        if ms >= MIN_STROKE_MM:
            break
        d = (MIN_STROKE_MM - ms) / 2 + 0.05
        grow += d
        welded = welded.buffer(d, join_style=1)
        ms = min_stroke(welded)
    if grow:
        layers = {k: g.buffer(grow, join_style=1) for k, g in layers.items()}
        warns.append(f"embolden+{grow:.2f}mm")
    welded = _clean(welded).simplify(0.03, preserve_topology=True)
    layers = {k: _clean(g.buffer(0.0)).simplify(0.03, preserve_topology=True) for k, g in layers.items()}
    layers = {k: g for k, g in layers.items() if not g.is_empty}
    fb = welded.bounds
    shift = (-fb[0], -fb[1])
    welded = affinity.translate(welded, *shift)
    layers = {k: affinity.translate(g, *shift) for k, g in layers.items()}
    nodes = sum(len(p.exterior.coords) + sum(len(r.coords) for r in p.interiors) for p in polys(welded))
    wb = welded.bounds
    return Design(uid, text, L.template, fonts, layers, welded, (wb[2] - wb[0]) / 25.4, (wb[3] - wb[1]) / 25.4, nodes, warns)


# ----------------------------------------------------------------------------- recipe selection
@dataclass
class Style:
    mains: Sequence[str]
    accents: Sequence[str]
    alts: Sequence[str] = ()
    templates: Dict[str, float] = field(default_factory=lambda: {"stack": 6, "retro": 1, "badge": 1.2, "frame": 1.2, "banner": 0.5, "arch": 0.3})
    orn: Sequence[str] = ("sparkle", "swash", "divider", "stars")
    caps: Optional[float] = 0.6        # probability main lines are uppercase (None -> font default)
    retro: Sequence[str] = ()          # font pool for the 'retro' template (groovy display faces)


def make(q: str, uid: str, style: Style, rng: random.Random, template: Optional[str] = None,
         recent: Optional[List[str]] = None) -> Design:
    avail = F.available()
    mains = [m for m in style.mains if m in avail]
    accents = [a for a in style.accents if a in avail]
    tpls = dict(style.templates)
    words, _, _ = parse(q)
    n = len(words)
    nchars = len(" ".join(words))
    if n < 3 or nchars > 40:
        tpls.pop("badge", None)
    if nchars > 24 or n < 2:
        tpls.pop("banner", None)
    if nchars > 34:
        tpls.pop("arch", None)
    if recent:
        for t in tpls:
            tpls[t] *= 0.35 if recent[-1:] == [t] else (0.7 if t in recent[-3:] else 1.0)
    order = [template] if template else rng.choices(list(tpls), weights=list(tpls.values()), k=len(tpls))
    seen = []
    for t in order:
        if t in seen:
            continue
        seen.append(t)
    for t in tpls:
        if t not in seen:
            seen.append(t)
    last_err = None
    for t in seen:
        for attempt in range(4):
            pool = [m for m in style.retro if m in avail] if (t == 'retro' and style.retro) else mains
            main = F.get(rng.choice(pool))
            acc = F.get(rng.choice(accents)) if accents else main
            alt = F.get(rng.choice(mains))
            caps = None if style.caps is None else (rng.random() < style.caps)
            ctx = Ctx(rng, main, acc, alt, style.orn, caps)
            try:
                L = TEMPLATES[t](q, ctx)
                if L.union().is_empty:
                    continue
                d = finalize(L, uid, q, {"main": main.key, "accent": acc.key}, TARGET_W_MM)
                return d
            except Exception as e:  # noqa
                last_err = e
                continue
    raise RuntimeError(f"could not build '{q}': {last_err!r}")
