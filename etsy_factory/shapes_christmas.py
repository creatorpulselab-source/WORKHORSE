"""Ten ORIGINAL Christmas silhouettes (procedural, shapely). Units: millimetres, y-up. No licensed characters."""
from __future__ import annotations

import math
from typing import Callable, Dict

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


def smooth(g, r: float = 1.6):
    """Round both convex and concave corners so the cutter has no sharp points that tear dough or snag a nozzle."""
    g = g.buffer(-r, join_style=1).buffer(2 * r, join_style=1).buffer(-r, join_style=1)
    return max(g.geoms, key=lambda x: x.area) if g.geom_type == "MultiPolygon" else g


def capsule(p0, p1, width):
    return LineString([p0, p1]).buffer(width / 2, cap_style=1)


def tree():
    tiers = [(0, 0, 34, 20), (0, 14, 28, 18), (0, 27, 22, 16)]          # (cx, base_y, half_width, height)
    parts = [Polygon([(cx - hw, by), (cx + hw, by), (cx, by + h)]) for cx, by, hw, h in tiers]
    parts.append(box(-5, -9, 5, 1))                                     # trunk
    parts.append(Point(0, 44).buffer(3.2))                              # tiny top bauble blends into the tip
    return smooth(unary_union(parts), 1.4)


def star():
    pts = []
    for i in range(10):
        r = 40 if i % 2 == 0 else 17.5
        a = math.radians(90 + i * 36)
        pts.append((r * math.cos(a), r * math.sin(a)))
    return smooth(Polygon(pts), 2.2)


def snowflake():
    arms = []
    for k in range(6):
        a = math.radians(k * 60)
        ux, uy = math.cos(a), math.sin(a)
        arm = [capsule((0, 0), (ux * 40, uy * 40), 6.4)]
        for frac, ln in ((0.55, 14),):
            bx, by = ux * 40 * frac, uy * 40 * frac
            for sgn in (-1, 1):
                ba = a + sgn * math.radians(55)
                arm.append(capsule((bx, by), (bx + math.cos(ba) * ln, by + math.sin(ba) * ln), 5.4))
        arms.extend(arm)
    arms.append(Point(0, 0).buffer(8.5, resolution=6))
    return smooth(unary_union(arms), 1.2)


def gingerbread():
    head = Point(0, 34).buffer(12)
    body = affinity.scale(Point(0, 9).buffer(15), 1.0, 1.3)
    arms = [capsule((-9, 17), (-28, 27), 11.5), capsule((9, 17), (28, 27), 11.5)]
    legs = [capsule((-7, -1), (-16, -26), 12.5), capsule((7, -1), (16, -26), 12.5)]
    return smooth(unary_union([head, body, *arms, *legs]), 2.0)


def candy_cane():
    pts = [(0, -40)] + [(0, 18)]
    for i in range(0, 181, 6):                                            # hook: semicircle, radius 15
        a = math.radians(180 - i)
        pts.append((15 + 15 * math.cos(a), 18 + 15 * math.sin(a)))
    pts.append((30, 8))
    return smooth(LineString(pts).buffer(6.2, cap_style=1, join_style=1), 1.0)


def ornament():
    ball = Point(0, 0).buffer(30, resolution=32)
    cap = box(-8, 26, 8, 36)
    loop = Point(0, 40).buffer(6.0)
    return smooth(unary_union([ball, cap, loop]), 1.6)


def mitten():
    palm = unary_union([box(-16, -14, 16, 10), Point(0, 10).buffer(16)])          # rounded-top palm
    thumb = capsule((-11, -2), (-30, 15), 15)                                       # clearly separate, angled thumb
    cuff = box(-18, -31, 18, -14).buffer(2, join_style=1)
    return smooth(unary_union([palm, thumb, cuff]), 1.4)


def stocking():
    leg = Polygon([(-13, 40), (13, 40), (12, -6), (-12, -6)])                       # tapered leg
    foot = capsule((-4, -18), (24, -16), 25)                                         # rounded toe
    heel = Point(-7, -15).buffer(14)
    cuff = box(-18, 36, 18, 48).buffer(3, join_style=1)
    return smooth(unary_union([leg, foot, heel, cuff]), 2.0)


def bell():
    dome = Point(0, 10).buffer(20).intersection(box(-30, 10, 30, 40))
    body = Polygon([(-20, 10), (20, 10), (31, -18), (-31, -18)])
    lip = box(-33, -22, 33, -15).buffer(2, join_style=1)
    clapper = Point(0, -26).buffer(6.5)
    top = Point(0, 33).buffer(5)
    return smooth(unary_union([dome, body, lip, clapper, top]), 1.6)


def snowman():
    base, mid, head = Point(0, -20).buffer(24), Point(0, 14).buffer(18), Point(0, 40).buffer(13)
    brim = box(-17, 50, 17, 55).buffer(1.5, join_style=1)
    crown = box(-10, 54, 10, 72).buffer(2.5, join_style=1)
    arms = [capsule((-14, 16), (-35, 27), 7.5), capsule((14, 16), (35, 27), 7.5)]
    return smooth(unary_union([base, mid, head, brim, crown, *arms]), 1.4)


DESIGNS: Dict[str, Callable] = {
    "christmas_tree": tree,
    "star": star,
    "snowflake": snowflake,
    "gingerbread_man": gingerbread,
    "candy_cane": candy_cane,
    "bauble_ornament": ornament,
    "mitten": mitten,
    "stocking": stocking,
    "bell": bell,
    "snowman": snowman,
}

NICE_NAMES = {
    "christmas_tree": "Christmas Tree", "star": "Star", "snowflake": "Snowflake", "gingerbread_man": "Gingerbread Man",
    "candy_cane": "Candy Cane", "bauble_ornament": "Bauble Ornament", "mitten": "Mitten", "stocking": "Stocking",
    "bell": "Jingle Bell", "snowman": "Snowman",
}


def normalized(poly: Polygon, max_dim_mm: float) -> Polygon:
    """Scale so the longest side is max_dim_mm and centre on the origin."""
    minx, miny, maxx, maxy = poly.bounds
    s = max_dim_mm / max(maxx - minx, maxy - miny)
    poly = affinity.scale(poly, s, s, origin=(0, 0))
    minx, miny, maxx, maxy = poly.bounds
    return affinity.translate(poly, -(minx + maxx) / 2, -(miny + maxy) / 2)
