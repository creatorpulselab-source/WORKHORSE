"""Font shaping (HarfBuzz: kerning, ligatures, script connections) + glyph outlines -> welded shapely geometry.

Coordinates are y-UP, units are whatever `size` you pass (em height).  All text comes out as ONE welded compound shape so
script/cursive letters never cut as separate overlapping pieces (the #1 buyer complaint on cut files).
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"


class _FlatPen(BasePen):
    def __init__(self, glyph_set, steps: int = 10):
        super().__init__(glyph_set)
        self.contours: List[List[Tuple[float, float]]] = []
        self.cur: Optional[List[Tuple[float, float]]] = None
        self.steps = steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        n = self.steps
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self.cur.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                             mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        n = self.steps
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self.cur.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                             mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))

    def _closePath(self):
        if self.cur and len(self.cur) >= 3:
            self.contours.append(self.cur)
        self.cur = None

    def _endPath(self):
        self._closePath()


def _area(c) -> float:
    return 0.5 * sum(c[i][0] * c[(i + 1) % len(c)][1] - c[(i + 1) % len(c)][0] * c[i][1] for i in range(len(c)))


def _poly(c) -> BaseGeometry:
    p = Polygon(c)
    return p if p.is_valid else p.buffer(0)


@dataclass
class Placed:
    glyph: str
    geom: BaseGeometry   # in output units, positioned at its pen position (baseline y=0)
    x: float
    adv: float


@dataclass
class Shaped:
    geom: BaseGeometry
    glyphs: List[Placed]
    advance: float
    size: float
    cap: float
    xh: float
    asc: float
    desc: float

    @property
    def bounds(self):
        return self.geom.bounds


class Face:
    def __init__(self, path: Path, weight: Optional[int] = None, width: Optional[int] = None):
        tt = TTFont(str(path))
        if "fvar" in tt:
            from fontTools.varLib import instancer
            axes = {}
            for a in tt["fvar"].axes:
                if a.axisTag == "wght":
                    axes["wght"] = weight if weight is not None else min(max(700, a.minValue), a.maxValue)
                elif a.axisTag == "wdth":
                    axes["wdth"] = width if width is not None else a.defaultValue
                elif a.axisTag == "opsz":
                    axes["opsz"] = a.defaultValue
                else:
                    axes[a.axisTag] = a.defaultValue
            tt = instancer.instantiateVariableFont(tt, axes, inplace=False)
        self.tt = tt
        buf = io.BytesIO()
        tt.save(buf)
        self.blob = hb.Blob(buf.getvalue())
        self.hbface = hb.Face(self.blob)
        self.hbfont = hb.Font(self.hbface)
        self.upem = tt["head"].unitsPerEm
        self.gs = tt.getGlyphSet()
        self.order = tt.getGlyphOrder()
        os2 = tt["OS/2"] if "OS/2" in tt else None
        self.cap = float(getattr(os2, "sCapHeight", 0) or 0.7 * self.upem)
        self.xh = float(getattr(os2, "sxHeight", 0) or 0.5 * self.upem)
        hhea = tt["hhea"]
        self.asc, self.desc = float(hhea.ascent), float(hhea.descent)
        self.path = path
        self._cache: Dict[str, BaseGeometry] = {}

    def glyph_geom(self, name: str) -> BaseGeometry:
        g = self._cache.get(name)
        if g is not None:
            return g
        pen = _FlatPen(self.gs, steps=10)
        try:
            self.gs[name].draw(pen)
        except Exception:
            self._cache[name] = Polygon()
            return self._cache[name]
        cs = [c for c in pen.contours if abs(_area(c)) > 1e-6]
        if not cs:
            geom: BaseGeometry = Polygon()
        else:
            big = max(cs, key=lambda c: abs(_area(c)))
            outer_sign = 1 if _area(big) > 0 else -1
            outers = [_poly(c) for c in cs if (_area(c) > 0) == (outer_sign > 0)]
            holes = [_poly(c) for c in cs if (_area(c) > 0) != (outer_sign > 0)]
            geom = unary_union(outers)
            if holes:
                geom = geom.difference(unary_union(holes))
        self._cache[name] = geom
        return geom

    def shape(self, text: str, size: float = 100.0, tracking: float = 0.0, features: Optional[dict] = None,
              keep_glyphs: bool = True) -> Shaped:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        feats = {"kern": True, "liga": True, "calt": True, "clig": True}
        if features:
            feats.update(features)
        hb.shape(self.hbfont, buf, feats)
        s = size / self.upem
        x = 0.0
        placed: List[Placed] = []
        parts = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = self.order[info.codepoint] if info.codepoint < len(self.order) else ".notdef"
            g = self.glyph_geom(name)
            gx = x + pos.x_offset * s
            gy = pos.y_offset * s
            if not g.is_empty:
                gg = affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), gx, gy)
                parts.append(gg)
                if keep_glyphs:
                    placed.append(Placed(name, gg, x, pos.x_advance * s))
            elif keep_glyphs:
                placed.append(Placed(name, Polygon(), x, pos.x_advance * s))
            x += pos.x_advance * s + tracking * size
        geom = unary_union(parts) if parts else Polygon()
        return Shaped(geom, placed, x, size, self.cap * s, self.xh * s, self.asc * s, self.desc * s)


_FACES: Dict[Tuple[str, Optional[int], Optional[int]], Face] = {}


def load_face(file_name: str, weight: Optional[int] = None, width: Optional[int] = None) -> Face:
    key = (file_name, weight, width)
    f = _FACES.get(key)
    if f is None:
        f = Face(FONT_DIR / file_name, weight, width)
        _FACES[key] = f
    return f


# ----------------------------------------------------------------------------- geometry helpers
def polys(g: BaseGeometry) -> List[Polygon]:
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for geom in getattr(g, "geoms", []) for p in polys(geom)]


def fit_width(g: BaseGeometry, width: float) -> BaseGeometry:
    x0, y0, x1, y1 = g.bounds
    if x1 - x0 <= 0:
        return g
    s = width / (x1 - x0)
    return affinity.scale(g, s, s, origin=(x0, y0))


def move_to(g: BaseGeometry, x: float, y: float, anchor: str = "cc") -> BaseGeometry:
    """Translate so the bbox anchor point (l/c/r + b/c/t) lands at (x, y)."""
    x0, y0, x1, y1 = g.bounds
    ax = {"l": x0, "c": (x0 + x1) / 2, "r": x1}[anchor[0]]
    ay = {"b": y0, "c": (y0 + y1) / 2, "t": y1}[anchor[1]]
    return affinity.translate(g, x - ax, y - ay)


def on_arc(face: Face, text: str, size: float, radius: float, centre_angle_deg: float = 90.0, outside: bool = True,
           tracking: float = 0.02, cx: float = 0.0, cy: float = 0.0) -> BaseGeometry:
    """Lay text along a circle. outside=True: reads left->right across the TOP of the circle (letters' tops point outward);
    outside=False: reads left->right along the BOTTOM (letters' tops point to the centre, text upright)."""
    sh = face.shape(text, size=size, tracking=tracking, keep_glyphs=True)
    total = sh.advance - tracking * size
    parts = []
    for p in sh.glyphs:
        if p.geom.is_empty:
            continue
        mid = p.x + p.adv / 2 - total / 2           # signed distance of glyph centre from text centre
        ang = mid / radius                          # radians along the arc
        if outside:
            theta = math.radians(centre_angle_deg) - ang
            rot = math.degrees(theta) - 90.0
            g = affinity.translate(p.geom, -(p.x + p.adv / 2), 0)
            g = affinity.rotate(g, rot, origin=(0, 0))
            g = affinity.translate(g, cx + radius * math.cos(theta), cy + radius * math.sin(theta))
        else:
            theta = math.radians(centre_angle_deg) + ang
            rot = math.degrees(theta) + 90.0
            g = affinity.translate(p.geom, -(p.x + p.adv / 2), -sh.cap)
            g = affinity.rotate(g, rot, origin=(0, 0))
            g = affinity.translate(g, cx + radius * math.cos(theta), cy + radius * math.sin(theta))
        parts.append(g)
    return unary_union(parts) if parts else Polygon()
