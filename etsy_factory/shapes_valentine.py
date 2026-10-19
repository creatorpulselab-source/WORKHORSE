"""Ten ORIGINAL Valentine silhouettes (procedural, shapely). Units: millimetres, y-up. No licensed characters.

Every shape is a single solid polygon (no holes) so the cutter wall and press plate stay simple and printable.
"""
from __future__ import annotations

import math
from typing import Callable, Dict

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from etsy_factory.shapes_christmas import capsule, normalized, smooth  # noqa: F401  (normalized re-exported)


def _heart_poly(cx: float = 0.0, cy: float = 0.0, w: float = 60.0, n: int = 120) -> Polygon:
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * w / 32.0, cy + y * w / 32.0))
    return Polygon(pts)


def heart():
    return smooth(_heart_poly(0, 0, 70), 1.2)


def double_hearts():
    a = affinity.rotate(_heart_poly(-14, 6, 50), 14, origin=(-14, 6))
    b = affinity.rotate(_heart_poly(16, -4, 56), -12, origin=(16, -4))
    return smooth(unary_union([a, b]), 1.4)


def cupid_arrow():
    """A heart pierced by an arrow: shaft crosses the heart diagonally, head top-right, feathers bottom-left."""
    shaft = capsule((-40, -40), (32, 32), 6.5)
    head = Polygon([(44, 44), (18, 40), (40, 18)]).buffer(1.2, join_style=1)
    fletch = []
    for k in (0, 1):
        bx, by = -40 + k * 11, -40 + k * 11
        fletch.append(Polygon([(bx, by), (bx - 16, by + 3), (bx - 24, by - 9), (bx - 7, by - 16)]))
    return smooth(unary_union([_heart_poly(-2, -2, 56), shaft, head, *fletch]), 1.4)


def lips():
    """Closed-mouth lips silhouette: two peaks with a cupid's-bow dip on top, fuller rounded lower lip, pointed corners."""
    top = [(-34, 0), (-26, 9), (-14, 15), (-6, 12), (0, 8), (6, 12), (14, 15), (26, 9), (34, 0)]
    bottom = [(26, -9), (14, -17), (0, -21), (-14, -17), (-26, -9)]
    return smooth(Polygon(top + bottom).buffer(1.5, join_style=1), 2.2)


def teddy():
    head = Point(0, 8).buffer(26)
    ears = [Point(-22, 30).buffer(11), Point(22, 30).buffer(11)]
    body = affinity.scale(Point(0, -30).buffer(24), 1.0, 0.9)
    arms = [capsule((-16, -20), (-34, -12), 13), capsule((16, -20), (34, -12), 13)]
    legs = [capsule((-12, -46), (-22, -54), 15), capsule((12, -46), (22, -54), 15)]
    return smooth(unary_union([head, *ears, body, *arms, *legs]), 2.0)


def rose():
    """Blooming flower: eight separate petals around a centre so the outline reads as a flower, not a blob."""
    petals = [affinity.rotate(affinity.scale(Point(24, 0).buffer(11), 1.5, 0.82), a, origin=(0, 0)) for a in range(0, 360, 45)]
    return smooth(unary_union([*petals, Point(0, 0).buffer(14)]), 1.4)


def key():
    head = unary_union([Point(0, 34).buffer(17), Point(-14, 40).buffer(10), Point(14, 40).buffer(10)])
    shaft = box(-5.5, -38, 5.5, 26)
    teeth = [box(5.5, -38, 18, -30), box(5.5, -22, 15, -15), box(5.5, -8, 18, -1)]
    return smooth(unary_union([head, shaft, *teeth]), 1.3)


def candy():
    body = affinity.scale(Point(0, 0).buffer(20), 1.3, 1.0)
    l = Polygon([(-20, 0), (-52, 22), (-44, 0), (-52, -22)])
    r = Polygon([(20, 0), (52, 22), (44, 0), (52, -22)])
    return smooth(unary_union([body, l.buffer(2, join_style=1), r.buffer(2, join_style=1)]), 1.8)


def gift_box():
    base = box(-30, -30, 30, 4).buffer(2.5, join_style=1)
    lid = box(-34, 2, 34, 15).buffer(2.5, join_style=1)
    ribbon_v = box(-5.5, -30, 5.5, 15)
    loop_l = affinity.rotate(affinity.scale(Point(-13, 27).buffer(8.5), 1.45, 0.85), 32, origin=(-13, 27))
    loop_r = affinity.rotate(affinity.scale(Point(13, 27).buffer(8.5), 1.45, 0.85), -32, origin=(13, 27))
    knot = Point(0, 19).buffer(5.5)
    u = unary_union([base, lid, ribbon_v, loop_l, loop_r, knot, box(-9, 12, 9, 24)])
    s = smooth(Polygon(u.exterior), 1.2)
    return Polygon(s.exterior)   # smoothing can close tiny gaps into holes - fill them (hole-free shapes only)


def cupcake():
    wrapper = Polygon([(-24, -8), (24, -8), (18, -42), (-18, -42)]).buffer(1.5, join_style=1)
    frosting = unary_union([affinity.scale(Point(0, 2).buffer(30), 1.0, 0.62), Point(0, 18).buffer(19), Point(0, 32).buffer(11)])
    cherry = Point(0, 48).buffer(7)
    return smooth(unary_union([wrapper, frosting, cherry]), 1.8)


DESIGNS: Dict[str, Callable] = {
    "classic_heart": heart,
    "double_hearts": double_hearts,
    "cupid_arrow": cupid_arrow,
    "kiss_lips": lips,
    "teddy_bear": teddy,
    "flower_bloom": rose,
    "love_key": key,
    "wrapped_candy": candy,
    "gift_box": gift_box,
    "cupcake": cupcake,
}

NICE_NAMES = {
    "classic_heart": "Classic Heart", "double_hearts": "Double Hearts", "cupid_arrow": "Heart and Arrow", "kiss_lips": "Kiss Lips",
    "teddy_bear": "Teddy Bear", "flower_bloom": "Flower Bloom", "love_key": "Love Key", "wrapped_candy": "Wrapped Candy",
    "gift_box": "Gift Box", "cupcake": "Cupcake",
}




