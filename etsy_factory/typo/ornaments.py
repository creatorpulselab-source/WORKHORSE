"""Procedural ornaments (shapely, y-UP). Every function returns a geometry centred (roughly) on the origin, sized in the
same units as the text it decorates."""
from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def soften(g: BaseGeometry, s: float) -> BaseGeometry:
    """Round both convex and concave corners by radius s (clean, cuttable corners)."""
    if s <= 0:
        return g
    return g.buffer(-s, join_style=1).buffer(2 * s, join_style=1).buffer(-s, join_style=1)


def circle(r: float, c=(0.0, 0.0), n: int = 96) -> Polygon:
    return Point(c).buffer(r, quad_segs=max(8, n // 4))


def ring(r: float, t: float) -> BaseGeometry:
    return circle(r).difference(circle(r - t))


def bar(w: float, t: float) -> BaseGeometry:
    return LineString([(-w / 2, 0), (w / 2, 0)]).buffer(t / 2, cap_style=1)


def diamond(s: float) -> Polygon:
    return Polygon([(0, s), (s * 0.62, 0), (0, -s), (-s * 0.62, 0)])


def star(r: float, points: int = 5, inner: float = 0.46, rot: float = 90.0) -> BaseGeometry:
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180.0 / points)
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return soften(Polygon(pts), r * 0.045)


def sparkle(r: float, pinch: float = 3.0) -> BaseGeometry:
    t = np.linspace(0, 2 * math.pi, 160, endpoint=False)
    x, y = r * np.cos(t) ** pinch, r * np.sin(t) ** pinch
    return soften(Polygon(zip(x, y)), r * 0.02)


def heart(w: float) -> BaseGeometry:
    t = np.linspace(0, 2 * math.pi, 240, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    g = Polygon(zip(x, y))
    s = w / 32.0
    g = affinity.scale(g, s, s, origin=(0, 0))
    return affinity.translate(g, 0, -g.centroid.y)


def bolt(h: float) -> BaseGeometry:
    pts = [(0.15, 1.0), (-0.55, -0.05), (-0.08, -0.05), (-0.25, -1.0), (0.6, 0.12), (0.1, 0.12), (0.5, 1.0)]
    g = Polygon([(x * h / 2, y * h / 2) for x, y in pts])
    return soften(g, h * 0.015)


def cross(h: float, thick: float = 0.17, bar_pos: float = 0.34) -> BaseGeometry:
    w = h * thick
    v = box(-w / 2, -h / 2, w / 2, h / 2)
    y = h / 2 - h * bar_pos
    hz = box(-h * 0.30, y - w / 2, h * 0.30, y + w / 2)
    return soften(unary_union([v, hz]), w * 0.08)


def lens(length: float, width: float) -> BaseGeometry:
    """Leaf blade pointing +x from the origin."""
    r = (length ** 2 / 4 + width ** 2) / (2 * width)
    a = circle(r, (length / 2, -(r - width)), 96)
    b = circle(r, (length / 2, (r - width)), 96)
    return a.intersection(b)


def leaf(length: float, width: float, angle: float) -> BaseGeometry:
    return affinity.rotate(lens(length, width), angle, origin=(0, 0))


def _bez(p0, p1, p2, p3, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def tapered(path: np.ndarray, t: float, power: float = 0.7, start_full: bool = False) -> BaseGeometry:
    """Brush-stroke style ribbon along a polyline, thickest in the middle (or at the start) and tapered to points."""
    n = len(path)
    d = np.gradient(path, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
    u = np.linspace(0, 1, n)
    prof = (np.sin(math.pi * u) ** power) if not start_full else (1 - u) ** power
    w = (t / 2) * np.maximum(prof, 0.02)[:, None]
    left = path + nrm * w
    right = path - nrm * w
    g = Polygon(np.vstack([left, right[::-1]]))
    return g if g.is_valid else g.buffer(0)


def swash(w: float, t: float, curl: float = 1.0, flip: bool = False) -> BaseGeometry:
    """Calligraphic underline flourish with a curled end."""
    p = _bez((-w / 2, 0), (-w * 0.22, -t * 2.2 * curl), (w * 0.18, t * 2.2 * curl), (w / 2, t * 0.3))
    g = tapered(p, t, 0.55)
    tail = _bez((w / 2, t * 0.3), (w / 2 + w * 0.05, t * 1.6 * curl), (w / 2 - w * 0.07, t * 3.2 * curl), (w / 2 - w * 0.13, t * 1.9 * curl))
    g = unary_union([g, tapered(tail, t * 0.8, 0.8, start_full=True)])
    return affinity.scale(g, 1, -1 if flip else 1, origin=(0, 0))


def divider(w: float, t: float, kind: str = "diamond") -> BaseGeometry:
    gap = t * 3.2
    side = (w - gap * 2) / 2
    parts = [affinity.translate(bar(side, t), -(gap + side / 2), 0), affinity.translate(bar(side, t), gap + side / 2, 0)]
    if kind == "diamond":
        parts.append(diamond(t * 2.2))
    elif kind == "heart":
        parts.append(heart(t * 4.2))
    elif kind == "star":
        parts.append(star(t * 2.4))
    elif kind == "dots":
        parts += [circle(t * 0.9, (dx, 0)) for dx in (-t * 2.4, 0, t * 2.4)]
    elif kind == "sparkle":
        parts.append(sparkle(t * 2.6))
    return unary_union(parts)


def banner(w: float, h: float, tail: float, drop: float, notch: float = 0.45) -> BaseGeometry:
    """Folded ribbon silhouette (filled). Text sits on the main band."""
    main = box(-w / 2, -h / 2, w / 2, h / 2)
    tw = tail
    left = Polygon([(-w / 2 + tw * 0.35, -h / 2 - drop), (-w / 2 - tw * 0.65, -h / 2 - drop), (-w / 2 - tw * 0.65 + tw * notch, -drop), (-w / 2 - tw * 0.65, h / 2 - drop), (-w / 2 + tw * 0.35, h / 2 - drop)])
    right = affinity.scale(left, -1, 1, origin=(0, 0))
    folds = [Polygon([(-w / 2, -h / 2), (-w / 2 + tw * 0.35, -h / 2), (-w / 2 + tw * 0.35, -h / 2 - drop)]),
             Polygon([(w / 2, -h / 2), (w / 2 - tw * 0.35, -h / 2), (w / 2 - tw * 0.35, -h / 2 - drop)])]
    return unary_union([main, left, right, *folds])


def outline(g: BaseGeometry, t: float) -> BaseGeometry:
    return g.difference(g.buffer(-t, join_style=2, mitre_limit=3))


def rounded_rect(w: float, h: float, r: float) -> BaseGeometry:
    return box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, join_style=1, quad_segs=24)


def scallop_rect(w: float, h: float, n_w: int, n_h: int, depth: float) -> BaseGeometry:
    base = box(-w / 2, -h / 2, w / 2, h / 2)
    r = w / n_w / 2
    parts = [base]
    for i in range(n_w):
        x = -w / 2 + r + i * 2 * r
        parts += [circle(r, (x, h / 2)), circle(r, (x, -h / 2))]
    rh = h / n_h / 2
    for j in range(n_h):
        y = -h / 2 + rh + j * 2 * rh
        parts += [circle(rh, (-w / 2, y)), circle(rh, (w / 2, y))]
    return unary_union(parts)


def sunburst(r_in: float, r_out: float, n: int = 24, frac: float = 0.35) -> BaseGeometry:
    rays = []
    for i in range(n):
        a = 2 * math.pi * i / n
        da = math.pi / n * frac
        rays.append(Polygon([(r_in * math.cos(a - da), r_in * math.sin(a - da)), (r_out * math.cos(a), r_out * math.sin(a)),
                             (r_in * math.cos(a + da), r_in * math.sin(a + da))]))
    return unary_union(rays)


def sun(r: float, rays: int = 12) -> BaseGeometry:
    return unary_union([circle(r), sunburst(r * 1.25, r * 2.0, rays, 0.55)])


def rainbow(r_out: float, bands: int = 4, bw: float = None, gap: float = None, flat: bool = True) -> BaseGeometry:
    bw = bw or r_out * 0.13
    gap = gap or bw * 0.55
    parts = []
    for i in range(bands):
        ro = r_out - i * (bw + gap)
        parts.append(circle(ro).difference(circle(ro - bw)))
    g = unary_union(parts)
    return g.intersection(box(-r_out * 2, 0, r_out * 2, r_out * 2)) if flat else g


def daisy(r: float, petals: int = 8, hole: bool = True) -> BaseGeometry:
    parts = []
    for i in range(petals):
        a = 360.0 * i / petals
        e = affinity.scale(circle(1.0, (0, 0), 48), r * 0.28, r * 0.50, origin=(0, 0))
        e = affinity.translate(e, 0, r * 0.5)
        parts.append(affinity.rotate(e, a, origin=(0, 0)))
    g = unary_union(parts + [circle(r * 0.30)])
    return g.difference(circle(r * 0.14)) if hole else g


def sprig(length: float, leaves: int = 5, leaf_len: float = None, t: float = None) -> BaseGeometry:
    """Horizontal botanical sprig: curved stem with alternating leaves."""
    leaf_len = leaf_len or length * 0.17
    t = t or length * 0.012
    xs = np.linspace(-length / 2, length / 2, 60)
    ys = leaf_len * 0.12 * np.sin(xs / length * math.pi * 1.2)
    stem = tapered(np.stack([xs, ys], axis=1), t * 1.8, 0.35)
    parts = [stem]
    for i in range(leaves):
        u = (i + 0.7) / (leaves + 0.2)
        x = -length / 2 + u * length * 0.96
        y = leaf_len * 0.12 * math.sin((x) / length * math.pi * 1.2)
        side = 1 if i % 2 == 0 else -1
        lf = leaf(leaf_len * (1.0 - 0.25 * u), leaf_len * 0.30, side * 52)
        parts.append(affinity.translate(lf, x, y))
    tip = leaf(leaf_len * 0.9, leaf_len * 0.28, 0)
    parts.append(affinity.translate(tip, length / 2 - leaf_len * 0.15, ys[-1]))
    return unary_union(parts)


def laurel(radius: float, leaves: int = 9, span: float = 150.0, leaf_len: float = None, start: float = 215.0, t: float = None) -> BaseGeometry:
    """Half wreath (left branch) on a circle of `radius`, running from `start` deg round the left side to the top."""
    leaf_len = leaf_len or radius * 0.30
    t = t or radius * 0.018
    angs = np.linspace(start, start - span, 60)
    stem = np.stack([radius * np.cos(np.radians(angs)), radius * np.sin(np.radians(angs))], axis=1)
    parts = [tapered(stem, t * 2.4, 0.4)]
    for i in range(leaves):
        a = start - span * (i + 0.5) / leaves
        x, y = radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a))
        tang = a - 90
        for side in (-1, 1):
            lf = leaf(leaf_len * (1 - 0.35 * i / leaves), leaf_len * 0.30, tang + side * 38)
            parts.append(affinity.translate(lf, x, y))
    return unary_union(parts)


def wreath(radius: float, leaves: int = 9, span: float = 150.0, leaf_len: float = None) -> BaseGeometry:
    left = laurel(radius, leaves, span, leaf_len, start=265.0)
    return unary_union([left, affinity.scale(left, -1, 1, origin=(0, 0))])


def mug(h: float) -> BaseGeometry:
    """Coffee mug icon with steam."""
    w = h * 0.78
    bh = h * 0.62
    body = rounded_rect(w, bh, h * 0.12)
    body = unary_union([body, box(-w / 2, bh / 2 - h * 0.12, w / 2, bh / 2)])         # square top edge
    cavity = affinity.translate(rounded_rect(w * 0.76, bh * 0.80, h * 0.07), 0, h * 0.06)
    body = body.difference(cavity.intersection(box(-w, -h, w, bh / 2 - h * 0.05 + 1e-3)))
    handle = affinity.translate(ring(h * 0.19, h * 0.07), w / 2 + h * 0.06, 0).difference(box(-w, -h, w / 2 - h * 0.02, h))
    steam = []
    for dx in (-w * 0.2, w * 0.2):
        p = _bez((dx, bh / 2 + h * 0.08), (dx - h * 0.12, bh / 2 + h * 0.2), (dx + h * 0.12, bh / 2 + h * 0.3), (dx, bh / 2 + h * 0.46))
        steam.append(tapered(p, h * 0.075, 0.5))
    g = unary_union([body, handle, *steam])
    return affinity.translate(g, 0, -g.centroid.y)


def wave(w: float, amp: float, periods: float, t: float) -> BaseGeometry:
    xs = np.linspace(-w / 2, w / 2, 160)
    ys = amp * np.sin(xs / w * 2 * math.pi * periods)
    return LineString(np.stack([xs, ys], axis=1)).buffer(t / 2, cap_style=1)


def speech_bubble(w: float, h: float, tail: str = "bl") -> BaseGeometry:
    body = rounded_rect(w, h, min(w, h) * 0.22)
    sx = -1 if "l" in tail else 1
    sy = -1
    tri = Polygon([(sx * w * 0.20, sy * h * 0.40), (sx * w * 0.36, sy * h * 0.40), (sx * w * 0.30, sy * h * 0.72)])
    return unary_union([body, tri])


def stars_row(n: int, r: float, gap: float) -> BaseGeometry:
    total = (n - 1) * gap
    return unary_union([affinity.translate(star(r), -total / 2 + i * gap, 0) for i in range(n)])


def hearts_row(n: int, w: float, gap: float) -> BaseGeometry:
    total = (n - 1) * gap
    return unary_union([affinity.translate(heart(w), -total / 2 + i * gap, 0) for i in range(n)])


def sparkle_cluster(r: float, rng: random.Random) -> BaseGeometry:
    return unary_union([sparkle(r), affinity.translate(sparkle(r * 0.5), r * 1.1, r * 0.9), affinity.translate(sparkle(r * 0.32), -r * 0.2, r * 1.5)])


def mountains(w: float, h: float) -> BaseGeometry:
    """Layered flat mountain silhouette (for boho/outdoor badges)."""
    a = Polygon([(-w / 2, 0), (-w * 0.2, h), (w * 0.05, h * 0.25), (w * 0.25, h * 0.8), (w / 2, 0)])
    return a
