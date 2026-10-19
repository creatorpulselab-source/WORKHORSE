"""12 original keychain silhouettes -> flat, print-friendly keychains (2.4 mm base + 1.2 mm raised border + ring hole)."""
from __future__ import annotations

import math
from typing import Callable, List, Tuple

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from .shapes3d import circle, extrude, ground, union

BASE_H, RIM_H, RIM_W = 2.4, 1.2, 1.4
SIZE_MM = 44.0
HOLE_R, TAB_R = 2.6, 6.2


def _ellipse(cx, cy, rx, ry, rot=0.0):
    e = affinity.scale(Point(0, 0).buffer(1.0, quad_segs=24), rx, ry)
    e = affinity.rotate(e, rot, origin=(0, 0))
    return affinity.translate(e, cx, cy)


def heart():
    t = np.linspace(0, 2 * math.pi, 240)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return Polygon(zip(x, y))


def star():
    pts = []
    for i in range(10):
        r = 24 if i % 2 == 0 else 11.5
        a = math.pi * i / 5 + math.pi / 2
        pts.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(pts).buffer(1.6).buffer(-0.4)


def paw():
    pad = _ellipse(0, -4, 14.5, 12.5)
    toes = [_ellipse(-19, 6, 5.6, 7.6, 30), _ellipse(-7, 15, 5.6, 7.6, 10), _ellipse(7, 15, 5.6, 7.6, -10), _ellipse(19, 6, 5.6, 7.6, -30)]
    g = pad
    for tz in toes:
        g = g.union(tz)
    g = g.buffer(2.4).buffer(-2.4)
    return Polygon(g.exterior)          # fill any enclosed pinholes between toes

def bone():
    shaft = box(-18, -4.5, 18, 4.5)
    ends = [circle(6.5, (sx * 20, sy * 5.2), 48) for sx in (-1, 1) for sy in (-1, 1)]
    g = shaft
    for e in ends:
        g = g.union(e)
    return affinity.rotate(g.buffer(1.0).buffer(-1.0), 35, origin=(0, 0))


def house():
    body = Polygon([(-18, -16), (18, -16), (18, 3), (0, 22), (-18, 3)])
    door = box(-5, -16.5, 5, -3)
    window = circle(3.6, (0, 5), 32)
    return body.difference(door).difference(window).buffer(0.8).buffer(-0.8)


def moon():
    g = circle(22, (0, 0), 96).difference(circle(18, (10, 4), 96))
    return g.buffer(-1.6).buffer(1.6)


def cloud():
    g = (circle(9.5, (-15, -3), 48).union(circle(12.5, (-5, 5), 48)).union(circle(11.5, (8, 6), 48))
         .union(circle(9, (17, -2), 48)).union(box(-22, -12.5, 23, -1)))
    g = g.intersection(box(-30, -12.5, 30, 30))  # flat base: lobes must not bulge below it
    return g.buffer(2.0).buffer(-2.0)

def bolt():
    return Polygon([(5, 24), (-14, -3), (-3, -3), (-8, -24), (15, 5), (3.5, 5), (11, 24)]).buffer(1.2)


def flower():
    g = circle(7.5, (0, 0), 48)
    for i in range(6):
        a = math.radians(60 * i + 90)
        g = g.union(circle(8.5, (13 * math.cos(a), 13 * math.sin(a)), 48))
    return g.buffer(1.0).buffer(-1.0).difference(circle(2.6, (0, 0), 24))


def cactus():
    body = LineString([(0, -14), (0, 16)]).buffer(6.5)
    arm_l = LineString([(-6, -2), (-14, -2), (-14, 9)]).buffer(4.2)
    arm_r = LineString([(6, 3), (14.5, 3), (14.5, 12)]).buffer(4.2)
    pot = box(-11, -27, 11, -14)
    return body.union(arm_l).union(arm_r).union(pot).buffer(1.2).buffer(-1.2)


def mushroom():
    cap = _ellipse(0, 3, 23, 19).intersection(box(-30, 3, 30, 30))
    stem = box(-7.5, -22, 7.5, 5).buffer(2.0).buffer(-2.0)
    g = cap.union(stem)
    for c, r in (((-9, 11), 3.2), ((6, 14), 2.6), ((10, 8), 2.0)):
        g = g.difference(circle(r, c, 24))
    return g


def leaf():
    lens = circle(24, (-7.5, 0), 160).intersection(circle(24, (7.5, 0), 160))
    stem = LineString([(0, -20), (0, -30)]).buffer(2.6)
    return lens.union(stem).buffer(1.0).buffer(-1.0)

SHAPES: List[Tuple[str, Callable]] = [
    ("Heart", heart), ("Star", star), ("Paw Print", paw), ("Dog Bone", bone), ("Little House", house), ("Crescent Moon", moon),
    ("Cloud", cloud), ("Lightning Bolt", bolt), ("Flower", flower), ("Cactus", cactus), ("Mushroom", mushroom), ("Leaf", leaf),
]


def _largest(g) -> Polygon:
    if isinstance(g, MultiPolygon):
        return max(g.geoms, key=lambda p: p.area)
    return g


def keychain_poly(builder: Callable) -> Polygon:
    g = _largest(builder())
    minx, miny, maxx, maxy = g.bounds
    g = affinity.scale(g, SIZE_MM / max(maxx - minx, maxy - miny), SIZE_MM / max(maxx - minx, maxy - miny), origin=(0, 0))
    minx, miny, maxx, maxy = g.bounds
    g = affinity.translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    # ring tab at the highest vertex
    vx, vy = max(g.exterior.coords, key=lambda p: p[1])
    tab_c = (vx, vy - 1.0)
    g = g.union(Point(*tab_c).buffer(TAB_R, quad_segs=16)).buffer(0.6).buffer(-0.6)
    g = g.difference(Point(*tab_c).buffer(HOLE_R, quad_segs=16))
    g = _largest(g)
    if not isinstance(g, Polygon) or g.is_empty:
        raise ValueError("keychain outline broke")
    return g


def keychain_mesh(builder: Callable) -> trimesh.Trimesh:
    g = keychain_poly(builder)
    rim = g.difference(g.buffer(-RIM_W))
    parts = extrude(g, BASE_H) + extrude(rim, RIM_H, z0=BASE_H)
    return ground(union(parts))


KEYCHAIN_ITEMS: List[Tuple[str, Callable]] = [(f"{n} Keychain", (lambda b=b: keychain_mesh(b))) for n, b in SHAPES]


def sheet_items():
    out = []
    for n, b in SHAPES:
        g = keychain_poly(b)
        out.append((n, [list(g.exterior.coords)] + [list(i.coords) for i in g.interiors]))
    return out
