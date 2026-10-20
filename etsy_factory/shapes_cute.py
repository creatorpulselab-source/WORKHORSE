"""Cute animal desk buddies: flat-faced pencil cups with ears, snouts, beaks and sticker-style faces.

Each animal is a FRONT SILHOUETTE (head + ears) extruded 52 mm deep, with a 40 mm-wide pocket cut from the top for pens/brushes.
The face is raised 2.2 mm (+1.2 mm for highlights) on the flat front, so it is crisp, needs no supports and prints standing up.
Back plates (dino spikes, chick crest) are thin slabs on the back wall so they never block the pocket. Front of the face is -Y.
All dimensions are millimetres; every builder returns ONE watertight trimesh sitting on z = 0.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

import trimesh
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from etsy_factory import shapes3d as s3

D = 52.0                 # silhouette depth
BACK_T = 6.0             # back wall thickness (also the thickness of back plates)
FRONT_T = 7.0            # front wall thickness behind the face
POCKET_W = 40.0
FLOOR = 4.0
FEAT, FEAT2 = 2.2, 1.2   # raised face layers


# ----------------------------------------------------------------------------- 2D helpers (x across, z up)
def rr(w: float, h: float, r: float, cx: float = 0.0, cz: float = 0.0) -> Polygon:
    return s3.rrect(w, h, r, (cx, cz))


def circ(x: float, z: float, r: float) -> Polygon:
    return Point(x, z).buffer(r, quad_segs=24)


def ell(x: float, z: float, rx: float, rz: float, rot: float = 0.0) -> Polygon:
    e = affinity.scale(Point(0, 0).buffer(1.0, quad_segs=24), rx, rz)
    e = affinity.rotate(e, rot, origin=(0, 0))
    return affinity.translate(e, x, z)


def tri(pts, rad: float = 2.0) -> Polygon:
    p = Polygon(pts)
    return p.buffer(-rad, join_style=1).buffer(rad, join_style=1)


def line(pts, w: float = 1.8) -> Polygon:
    return LineString(pts).buffer(w / 2, cap_style=1, join_style=1)


def mirror(p):
    return affinity.scale(p, xfact=-1, yfact=1, origin=(0, 0))


def both(p):
    return unary_union([p, mirror(p)])


def close(p, r: float = 0.8):
    return p.buffer(r, join_style=1).buffer(-r, join_style=1)


def ring(x: float, z: float, r_out: float, r_in: float) -> Polygon:
    return circ(x, z, r_out).difference(circ(x, z, r_in))


# ----------------------------------------------------------------------------- 3D assembly
def solid(g, t0: float, t1: float) -> trimesh.Trimesh:
    """Prism of the XZ-plane shape g between depth t0 and t1 measured from the back (y=0) toward the front (-Y)."""
    meshes = s3.extrude(g, t1 - t0, z0=t0)
    m = s3.union(meshes)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))      # (x, y, z) -> (x, -z, y)
    return m


def build(sil: Polygon, back: Optional[Polygon] = None, r1: Optional[Polygon] = None, r2: Optional[Polygon] = None) -> trimesh.Trimesh:
    parts = [solid(sil, 0, D)]
    if back is not None:
        parts.append(solid(back, 0, BACK_T))
    if r1 is not None and not r1.is_empty:
        parts.append(solid(r1, D - 0.8, D + FEAT))
    if r2 is not None and not r2.is_empty:
        parts.append(solid(r2, D + FEAT - 0.6, D + FEAT + FEAT2))
    m = s3.union(parts)
    y_back, y_front = -BACK_T, -(D - FRONT_T)
    ellipse = Polygon([(POCKET_W / 2 * math.cos(t), (y_back - y_front) / 2 * math.sin(t) + (y_back + y_front) / 2)
                       for t in [i * math.pi / 32 for i in range(64)]])
    pocket = trimesh.creation.extrude_polygon(ellipse, 300.0)
    pocket.apply_translation((0, 0, FLOOR))
    return s3.ground(s3.diff(m, [pocket]))


EYE_Z = 44.0


# ----------------------------------------------------------------------------- animals
def cat():
    ear = tri([(-43, 50), (-14, 66), (-38, 94)], 3.0)
    sil = close(unary_union([rr(88, 68, 26, 0, 34), both(ear)]))
    inner = both(tri([(-37, 56), (-21, 66), (-34, 83)], 1.5))
    eyes = both(circ(-19, EYE_Z, 6.0))
    nose = tri([(-5.5, 36), (5.5, 36), (0, 29.5)], 1.2)
    mouth = unary_union([line([(0, 30), (0, 26)]), line([(-9, 27), (-5, 23.5), (0, 26), (5, 23.5), (9, 27)])])
    whisk = both(unary_union([line([(25, 33 + dz * 0.5), (41, 33 + dz * 1.7)], 1.6) for dz in (4, 0, -4)]))
    blush = both(ell(-30, 33, 5.5, 3.2))
    hl = both(circ(-16.8, EYE_Z + 2.6, 2.0))
    return build(sil, None, unary_union([inner, eyes, nose, mouth, whisk, blush]), hl)


def bear():
    sil = close(unary_union([rr(88, 68, 28, 0, 34), both(circ(-33, 66, 15))]))
    inner = both(circ(-33, 66, 8.2))
    muzzle = ell(0, 27, 16.5, 12.5)
    eyes = both(circ(-19, 46, 4.8))
    cheeks = both(ell(-31, 34, 5.0, 3.2))
    nose = ell(0, 31.5, 5.8, 4.0)
    mouth = unary_union([line([(0, 28), (0, 23.5)]), line([(-6.5, 20.5), (0, 23.5), (6.5, 20.5)])])
    return build(sil, None, unary_union([inner, muzzle, eyes, cheeks]), unary_union([nose, mouth, both(circ(-17.6, 48, 1.7))]))


def bunny():
    ear = ell(-30, 76, 10, 30, 8)
    sil = close(unary_union([rr(84, 62, 28, 0, 31), both(ear)]))
    inner = both(ell(-30, 78, 5, 21, 8))
    eyes = both(circ(-17, 38, 5.0))
    nose = ell(0, 28.5, 4.2, 3.0)
    mouth = line([(-6, 23), (-3, 20), (0, 23), (3, 20), (6, 23)])
    teeth = rr(8.6, 9, 1.6, 0, 15.5)
    blush = both(ell(-28, 30, 5.5, 3.2))
    return build(sil, None, unary_union([inner, eyes, nose, mouth, teeth, blush]), both(circ(-15.8, 40, 1.7)))


def panda():
    sil = close(unary_union([rr(88, 68, 28, 0, 34), both(circ(-33, 66, 14.5))]))
    patches = both(ell(-19, 44, 10.5, 8.5, 28))
    nose = ell(0, 30, 6.5, 4.4)
    mouth = unary_union([line([(0, 26), (0, 22)]), line([(-6, 19.5), (0, 22), (6, 19.5)])])
    pupils = both(circ(-19.5, 44.5, 3.4))
    return build(sil, None, unary_union([patches, nose, mouth]), pupils)


def pig():
    ear = tri([(-44, 46), (-20, 62), (-46, 78)], 3.0)
    sil = close(unary_union([rr(88, 64, 28, 0, 32), both(ear)]))
    snout = ell(0, 25, 18, 13.5).difference(both(ell(-6.2, 25, 2.6, 4.3)))
    eyes = both(circ(-21, 43, 4.8))
    blush = both(ell(-32, 31, 5, 3.0))
    return build(sil, None, unary_union([snout, eyes, blush]), both(circ(-19.8, 44.8, 1.6)))


def owl():
    tuft = tri([(-43, 70), (-21, 84), (-45, 100)], 3.0)
    sil = close(unary_union([rr(86, 84, 30, 0, 42), both(tuft)]))
    rings = both(ring(-18, 52, 16, 11.2))
    pupils = both(circ(-18, 52, 6.5))
    beak = tri([(-6.5, 40), (6.5, 40), (0, 27)], 1.2)
    scales = unary_union([ring(x, 23, 5.4, 3.3) for x in (-16.5, -5.5, 5.5, 16.5)] + [ring(x, 14, 5.4, 3.3) for x in (-11, 0, 11)])
    return build(sil, None, unary_union([rings, pupils, beak, scales]), both(circ(-16, 54.2, 2.0)))


def chick():
    head = unary_union([circ(0, 44, 42), rr(58, 22, 7, 0, 11)]).intersection(box(-60, 0, 60, 82))
    crest = unary_union([ell(-9, 84, 4.6, 11, 25), ell(0, 87, 4.6, 12, 0), ell(9, 84, 4.6, 11, -25)])
    beak = tri([(-9.5, 42), (9.5, 42), (0, 27)], 1.6)
    eyes = both(circ(-20, 50, 5.4))
    wings = both(ell(-34, 36, 6.5, 13, 10))
    blush = both(ell(-31, 38, 6, 3.8))
    return build(close(head), crest, unary_union([beak, eyes, wings, blush]), both(circ(-18.6, 52, 1.9)))


def dino():
    spikes = unary_union([tri([(x - 9, 58), (x + 9, 58), (x, 66 + h)], 2.0) for x, h in ((-36, 12), (-18, 19), (0, 23), (18, 19), (36, 12))])
    sil = rr(90, 66, 26, 0, 33)
    eyes = both(circ(-19, 43, 5.4))
    nostrils = both(ell(-6, 33, 2.3, 3.0))
    smile = line([(-14, 28), (-8, 23), (0, 21), (8, 23), (14, 28)], 2.0)
    spots = unary_union([circ(sx * 33, 56, 3.6) for sx in (-1, 1)] + [circ(sx * 37, 36, 3.2) for sx in (-1, 1)])
    blush = both(ell(-27, 30, 5, 3.0))
    return build(sil, spikes, unary_union([eyes, nostrils, smile, spots, blush]), both(circ(-17.6, 45.2, 1.9)))


ITEMS = [("Cat Pencil Cup", cat), ("Bear Pencil Cup", bear), ("Bunny Pencil Cup", bunny), ("Panda Pencil Cup", panda),
         ("Pig Pencil Cup", pig), ("Owl Pencil Cup", owl), ("Chick Pencil Cup", chick), ("Dino Pencil Cup", dino)]


if __name__ == "__main__":
    from pathlib import Path
    out = Path(r"F:\WORKHORSE\workspace\scratch\cute_preview")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in ITEMS:
        try:
            m = fn()
            print(f"{name:20s} watertight={m.is_watertight} vol={m.volume / 1000:.0f}cm3 ext={[round(float(x), 1) for x in m.extents]} faces={len(m.faces)}", flush=True)
            m.export(out / f"{name.replace(' ', '_')}.stl")
        except Exception as e:  # noqa: BLE001
            print(f"{name:20s} FAILED {type(e).__name__}: {e}", flush=True)
