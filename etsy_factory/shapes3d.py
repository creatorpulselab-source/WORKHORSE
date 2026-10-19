"""Parametric printable products: desk organizers, can holders, planters. Every builder returns ONE trimesh that is
validated (watertight, positive volume) by the caller. All dimensions are millimetres.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box

WALL = 2.4
FLOOR = 3.0


# ----------------------------------------------------------------------------- helpers
def _polys(g) -> List[Polygon]:
    if g.is_empty:
        return []
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]


def extrude(g, height: float, z0: float = 0.0) -> List[trimesh.Trimesh]:
    out = []
    for p in _polys(g):
        if p.area < 0.5:
            continue
        m = trimesh.creation.extrude_polygon(p, height)
        m.apply_translation((0, 0, z0))
        out.append(m)
    return out


def union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    meshes = list(meshes)
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def diff(a: trimesh.Trimesh, b: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    return trimesh.boolean.difference([a, *b], engine="manifold")


def circle(r: float, c=(0, 0), n: int = 64) -> Polygon:
    return Point(*c).buffer(r, quad_segs=n // 4)


def rrect(w: float, d: float, r: float, c=(0, 0)) -> Polygon:
    return box(c[0] - w / 2 + r, c[1] - d / 2 + r, c[0] + w / 2 - r, c[1] + d / 2 - r).buffer(r, quad_segs=12)


def regular(n: int, radius: float, rot_deg: float = 0.0, c=(0, 0)) -> Polygon:
    pts = [(c[0] + radius * math.cos(math.radians(rot_deg) + 2 * math.pi * i / n),
            c[1] + radius * math.sin(math.radians(rot_deg) + 2 * math.pi * i / n)) for i in range(n)]
    return Polygon(pts)


def container(outline: Polygon, height: float, wall: float = WALL, floor: float = FLOOR) -> trimesh.Trimesh:
    """Open-top box/cup from any outline polygon."""
    inner = outline.buffer(-wall, join_style=1)
    parts = extrude(outline, floor) + extrude(outline.difference(inner), height - floor, z0=floor)
    return union(parts)


def frustum(poly_bottom: Polygon, poly_top: Polygon, z0: float, z1: float) -> trimesh.Trimesh:
    pts = [(x, y, z0) for x, y in poly_bottom.exterior.coords[:-1]] + [(x, y, z1) for x, y in poly_top.exterior.coords[:-1]]
    return trimesh.convex.convex_hull(np.array(pts))


def box3(sx, sy, sz, c=(0, 0, 0)) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=(sx, sy, sz))
    m.apply_translation(c)
    return m


def cyl(r: float, h: float, c=(0, 0, 0), axis: str = "z", sections: int = 64) -> trimesh.Trimesh:
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "x":
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0)))
    elif axis == "y":
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    m.apply_translation(c)
    return m


def ground(m: trimesh.Trimesh) -> trimesh.Trimesh:
    """Centre on XY, sit on z = 0."""
    b = m.bounds
    m.apply_translation((-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]))
    return m


# ----------------------------------------------------------------------------- DESK ORGANIZERS
def d_round_pen_cup():
    return ground(container(circle(40), 95))


def d_hex_pen_cup():
    return ground(container(regular(6, 44, 0).buffer(3, join_style=1), 95))


def d_square_pencil_holder():
    return ground(container(rrect(80, 80, 8), 100))


def d_phone_stand():
    """Side profile (x along, z up) extruded 70 mm wide: base + 65-degree back rest + front lip."""
    from shapely.geometry import LineString
    base = box(0, 0, 100, 8)
    back = LineString([(72, 4), (36, 92)]).buffer(4.2, cap_style=2)
    lip = box(30, 0, 42, 20)
    prof = base.union(back).union(lip).buffer(1.2, join_style=1).buffer(-1.2, join_style=1)
    m = trimesh.creation.extrude_polygon(prof, 70)          # extrudes along z; stand it up so profile is x/z
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    return ground(m)


def d_cable_clips():
    """Four cable clips in one print: C-clip with a flat base that can be glued or taped to a desk."""
    clips = []
    for i in range(4):
        r_out, r_in = 11.0, 6.5
        ring = circle(r_out, (0, r_out + 3)).difference(circle(r_in, (0, r_out + 3)))
        slot = box(-3.0, r_out + 3 + 2, 3.0, r_out + 3 + r_out + 2)
        pro = ring.difference(slot).union(box(-r_out - 6, 0, r_out + 6, 3.2))
        ms = extrude(pro.buffer(0.6).buffer(-0.6), 14)
        m = union(ms)
        m.apply_translation((i * 36 - 54, 0, 0))
        clips.append(m)
    return ground(union(clips))


def d_card_holder():
    block = box3(98, 38, 20, (0, 0, 10))
    slot = box3(92, 12, 30, (0, 0, 0))
    slot.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-14), (1, 0, 0)))
    slot.apply_translation((0, 0, 26))
    m = diff(block, [slot])
    return ground(m)


def d_sticky_tray():
    m = container(rrect(86, 86, 6), 22)
    notch = cyl(16, 12, (0, -44, 22 + 4), axis="y")
    return ground(diff(m, [notch]))


def d_four_compartment_tray():
    outline = rrect(184, 124, 8)
    base = container(outline, 42)
    dv = [box3(2.2, 120, 38, (0, 0, 3 + 19)), box3(180, 2.2, 38, (0, 0, 3 + 19))]
    return ground(union([base] + dv))


def d_pen_tray():
    outline = rrect(196, 46, 10)
    base = container(outline, 24)
    divider = box3(2.2, 44, 21, (28, 0, 3 + 10.5))
    return ground(union([base, divider]))


def d_desk_dish():
    outer = frustum(circle(30, n=64), circle(40, n=64), 0, 16)
    inner = frustum(circle(26.5, n=64), circle(36.7, n=64), 3.0, 16.5)
    return ground(diff(outer, [inner]))


DESK_ITEMS = [
    ("Round Pen Cup", d_round_pen_cup), ("Hex Pen Cup", d_hex_pen_cup), ("Square Pencil Holder", d_square_pencil_holder),
    ("Phone Stand", d_phone_stand), ("Cable Clips x4", d_cable_clips), ("Business Card Holder", d_card_holder),
    ("Sticky Note Tray", d_sticky_tray), ("4-Compartment Desk Tray", d_four_compartment_tray),
    ("Pen and Pencil Tray", d_pen_tray), ("Desk Dish", d_desk_dish),
]


# ----------------------------------------------------------------------------- CAN HOLDERS
CAN_STD_D = 66.2     # standard 12 oz / 16 oz can body diameter
CAN_SLIM_D = 58.0    # slim can diameter
CLEARANCE = 1.3


def _can_cup(can_d: float, height: float, ear: bool = False) -> trimesh.Trimesh:
    r_in = can_d / 2 + CLEARANCE / 2
    r_out = r_in + WALL
    outline = circle(r_out)
    drain = cyl(4.2, FLOOR * 3, (0, 0, 0))
    cup = container(outline, height)
    parts = [cup]
    if ear:
        cx = r_out + 8
        tab = circle(11, (cx, 0)).union(box(r_out - 3, -7, cx, 7))
        tab = tab.difference(circle(4.6, (cx + 1, 0)))
        parts += extrude(tab, FLOOR + 1.5)
    m = union(parts)
    return diff(m, [drain])


def c_std_holder():
    return ground(_can_cup(CAN_STD_D, 95))


def c_std_loop():
    return ground(_can_cup(CAN_STD_D, 95, ear=True))


def c_slim_holder():
    return ground(_can_cup(CAN_SLIM_D, 95))


def c_slim_loop():
    return ground(_can_cup(CAN_SLIM_D, 95, ear=True))


def c_tall_holder():
    return ground(_can_cup(CAN_STD_D, 120))


def c_cupholder_adapter():
    """Slim-can sleeve with a 73 mm outside diameter - a spacer for cup holders sized for larger drinks."""
    r_out = 36.5
    r_in = CAN_SLIM_D / 2 + CLEARANCE / 2
    ring = circle(r_out).difference(circle(r_in))
    parts = extrude(ring, 80) + extrude(circle(r_out), FLOOR)
    m = union(parts)
    return ground(diff(m, [cyl(4.2, FLOOR * 3, (0, 0, 0))]))


def _caddy(cols: int, rows: int) -> trimesh.Trimesh:
    r_in = CAN_STD_D / 2 + CLEARANCE / 2
    r_out = r_in + WALL
    pitch = 2 * r_out + 1.0
    xs = [(i - (cols - 1) / 2) * pitch for i in range(cols)]
    ys = [(j - (rows - 1) / 2) * pitch for j in range(rows)]
    base_outline = rrect(cols * pitch + 8, rows * pitch + 8, 12)
    parts = extrude(base_outline, FLOOR)
    holes = []
    for x in xs:
        for y in ys:
            ring = circle(r_out, (x, y)).difference(circle(r_in, (x, y)))
            parts += extrude(ring, 46, z0=0)
            holes.append(cyl(4.2, FLOOR * 3, (x, y, 0)))
    # centre handle plate running across the width, oval finger hole
    hw, hh, ht = cols * pitch * 0.55, 78.0, 10.0
    handle = trimesh.creation.box(extents=(hw, ht, hh))
    handle.apply_translation((0, 0, hh / 2))
    oval = affinity.scale(circle(1.0, n=64), hw * 0.30, hh * 0.20)
    oval_m = trimesh.creation.extrude_polygon(oval, ht * 3)
    oval_m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    oval_m.apply_translation((0, ht * 1.5, hh * 0.62))
    handle = diff(handle, [oval_m])
    # soften the top corners of the handle with a hull-free cut: keep it simple and strong
    parts.append(handle)
    m = union(parts)
    return ground(diff(m, holes))


def c_caddy4():
    return _caddy(2, 2)


def c_caddy6():
    return _caddy(3, 2)


CAN_ITEMS = [
    ("Standard Can Holder", c_std_holder), ("Standard Can Holder with Clip Loop", c_std_loop),
    ("Slim Can Holder", c_slim_holder), ("Slim Can Holder with Clip Loop", c_slim_loop),
    ("Tall Can Holder 16oz", c_tall_holder), ("Slim Can Cup-Holder Adapter", c_cupholder_adapter),
    ("4-Can Caddy with Handle", c_caddy4), ("6-Can Caddy with Handle", c_caddy6),
]


# ----------------------------------------------------------------------------- PLANTERS (STL + 3MF + GLB pack)
PLANTER_SPECS: List[Dict] = [
    {"name": "Hex Taper", "n": 6, "rb": 34, "rt": 46, "twist": 0, "h": 70},
    {"name": "Octagon Taper", "n": 8, "rb": 32, "rt": 44, "twist": 0, "h": 66},
    {"name": "Twisted Hex", "n": 6, "rb": 34, "rt": 44, "twist": 30, "h": 76},
    {"name": "Twisted Square", "n": 4, "rb": 34, "rt": 46, "twist": 45, "h": 70},
    {"name": "Twisted Triangle", "n": 3, "rb": 34, "rt": 52, "twist": 60, "h": 70},
    {"name": "Faceted Round", "n": 12, "rb": 32, "rt": 42, "twist": 0, "h": 60},
    {"name": "Tall Hex Vase", "n": 6, "rb": 26, "rt": 34, "twist": 0, "h": 96},
    {"name": "Wide Bowl", "n": 10, "rb": 34, "rt": 60, "twist": 0, "h": 48},
]


def planter(spec: Dict) -> trimesh.Trimesh:
    n, rb, rt, tw, h = spec["n"], spec["rb"], spec["rt"], spec["twist"], spec["h"]
    outer = frustum(regular(n, rb, 0), regular(n, rt, tw), 0, h)
    # inner cavity: same taper, shrunk by the wall measured on the apothem, starting at the floor
    shrink = WALL / math.cos(math.pi / n)
    slope = (rt - rb) / h

    def r_at(z):
        return rb + slope * z

    zi0, zi1 = FLOOR, h + 1.0
    rin0, rin1 = r_at(zi0) - shrink, r_at(zi1) - shrink
    inner = frustum(regular(n, rin0, tw * zi0 / h), regular(n, rin1, tw * zi1 / h), zi0, zi1)
    m = diff(outer, [inner, cyl(3.5, FLOOR * 3, (0, 0, 0))])
    return ground(m)


def saucer(spec: Dict) -> trimesh.Trimesh:
    rb = spec["rb"]
    outer = cyl(rb + 9, 9.0, (0, 0, 4.5))
    recess = cyl(rb + 2.6, 9.0, (0, 0, 3.0 + 4.5))
    return ground(diff(outer, [recess]))
