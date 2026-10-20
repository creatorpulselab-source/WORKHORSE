"""Cute animal faces as layered 2D vector designs (x across, z up, millimetres; origin at the bottom centre).

One source of truth for TWO products: the layered SVG/DXF/PNG cut-file pack (faces/pack.py) and the 3D pencil cups
(shapes_cute.py, which extrudes the silhouette and raises the face parts).

Animal(sil, back, parts): `sil` is the front silhouette (head + ears), `back` sits behind it (dino spikes, lion mane, unicorn hair),
`parts` = [(name, hex colour, geometry, grp)] where grp 0 = flat on the body (ear colour...), 1 = face layer, 2 = detail on top.
Every part is clipped to the silhouette so nothing floats. All art is original geometry - no characters, brands or logos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from etsy_factory import shapes3d as s3

DARK = "#2E2424"
WHITE = "#FFFFFF"


# ----------------------------------------------------------------------------- 2D helpers
def rr(w: float, h: float, r: float, cx: float = 0.0, cz: float = 0.0) -> Polygon:
    return s3.rrect(w, h, r, (cx, cz))


def circ(x: float, z: float, r: float) -> Polygon:
    return Point(x, z).buffer(r, quad_segs=24)


def ell(x: float, z: float, rx: float, rz: float, rot: float = 0.0) -> Polygon:
    e = affinity.scale(Point(0, 0).buffer(1.0, quad_segs=24), rx, rz)
    e = affinity.rotate(e, rot, origin=(0, 0))
    return affinity.translate(e, x, z)


def tri(pts, rad: float = 2.0) -> Polygon:
    return Polygon(pts).buffer(-rad, join_style=1).buffer(rad, join_style=1)


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


def U(*gs):
    return unary_union([g for g in gs if g is not None and not g.is_empty])


def smile(w: float, z: float, depth: float = 3.0, lw: float = 1.9) -> Polygon:
    pts = [(w * t / 8, z - depth * (1 - (t / 8) ** 2)) for t in range(-8, 9)]
    return line(pts, lw)


# ----------------------------------------------------------------------------- model
@dataclass
class Animal:
    key: str
    name: str
    body: str
    sil: Polygon
    back: Optional[Polygon] = None
    back_hex: str = "#555555"
    parts: List[Tuple[str, str, BaseGeometry, int]] = field(default_factory=list)

    def part(self, name: str, hexc: str, g: BaseGeometry, grp: int = 1, clip: bool = True) -> "Animal":
        g = g.intersection(self.sil) if clip else g
        if not g.is_empty:
            self.parts.append((name, hexc, g, grp))
        return self

    def outline(self) -> BaseGeometry:
        """Everything that is part of the cut-out shape (back + silhouette)."""
        return close(U(self.sil, self.back), 0.6)

    def grp(self, n: int) -> BaseGeometry:
        return U(*[g for _, _, g, k in self.parts if k == n])

    def svg_layers(self) -> List[Tuple[str, BaseGeometry, str]]:
        """Bottom -> top, one layer per colour per stacking group. Layer ids are Cricut-friendly."""
        layers: List[Tuple[str, BaseGeometry, str]] = []
        if self.back is not None:
            layers.append(("Back", self.back.difference(self.sil.buffer(-0.2)), self.back_hex))
        layers.append(("Body", self.sil, self.body))
        for k in (0, 1, 2):
            seen: Dict[str, List[BaseGeometry]] = {}
            order: List[str] = []
            for name, hx, g, gk in self.parts:
                if gk != k:
                    continue
                if hx not in seen:
                    seen[hx] = []
                    order.append(hx)
                seen[hx].append(g)
            for hx in order:
                layers.append((f"Detail_{len(layers):02d}", unary_union(seen[hx]), hx))
        # name layers 01.. for the cutting software
        out = []
        for i, (nm, g, hx) in enumerate(layers, 1):
            out.append((f"Layer_{i:02d}_{nm if not nm.startswith('Detail') else 'Detail'}_{hx.lstrip('#').upper()}", g, hx))
        return out

    def stencil(self) -> BaseGeometry:
        """One connected piece: silhouette with the dark face parts cut out (eyes, nose, mouth)."""
        dark = U(*[g for _, hx, g, k in self.parts if hx.upper() in (DARK, "#2B2222", "#2B1D17", "#2B2B2B", "#35282B", "#241E1B", "#2A2018") and k >= 1])
        return close(self.outline().difference(dark.buffer(0.0)), 0.3)


A: Dict[str, Animal] = {}


def reg(a: Animal) -> Animal:
    A[a.key] = a
    return a


# ----------------------------------------------------------------------------- the 8 that are also 3D pencil cups
def _cat():
    sil = close(U(rr(88, 68, 26, 0, 34), both(tri([(-43, 50), (-14, 66), (-38, 94)], 3.0))))
    a = Animal("cat", "Cat", "#F6A04D", sil)
    a.part("inner_ear", "#F7B5C4", both(tri([(-37, 56), (-21, 66), (-34, 83)], 1.5)))
    a.part("eyes", DARK, both(circ(-19, 44, 6.0)))
    a.part("nose", "#E0728A", tri([(-5.5, 36), (5.5, 36), (0, 29.5)], 1.2))
    a.part("mouth", DARK, U(line([(0, 30), (0, 26)]), line([(-9, 27), (-5, 23.5), (0, 26), (5, 23.5), (9, 27)])))
    a.part("whiskers", "#FFF1DD", both(U(*[line([(25, 33 + dz * 0.5), (41, 33 + dz * 1.7)], 1.6) for dz in (4, 0, -4)])))
    a.part("blush", "#F58EA0", both(ell(-30, 33, 5.5, 3.2)))
    a.part("sparkle", WHITE, both(circ(-16.8, 46.6, 2.0)), 2)
    return reg(a)


def _bear():
    sil = close(U(rr(88, 68, 28, 0, 34), both(circ(-33, 66, 15))))
    a = Animal("bear", "Bear", "#A06F46", sil)
    a.part("inner_ear", "#E9D2AE", both(circ(-33, 66, 8.2)))
    a.part("muzzle", "#E9D2AE", ell(0, 27, 16.5, 12.5))
    a.part("eyes", DARK, both(circ(-19, 46, 4.8)))
    a.part("blush", "#F09A92", both(ell(-31, 34, 5.0, 3.2)))
    a.part("nose", DARK, ell(0, 31.5, 5.8, 4.0), 2)
    a.part("mouth", DARK, U(line([(0, 28), (0, 23.5)]), line([(-6.5, 20.5), (0, 23.5), (6.5, 20.5)])), 2)
    a.part("sparkle", WHITE, both(circ(-17.6, 48, 1.7)), 2)
    return reg(a)


def _bunny():
    sil = close(U(rr(84, 62, 28, 0, 31), both(ell(-30, 76, 10, 30, 8))))
    a = Animal("bunny", "Bunny", "#F3E8E2", sil)
    a.part("inner_ear", "#F7B6C6", both(ell(-30, 78, 5, 21, 8)))
    a.part("eyes", DARK, both(circ(-17, 38, 5.0)))
    a.part("nose", "#F28FA7", ell(0, 28.5, 4.2, 3.0))
    a.part("mouth", DARK, line([(-6, 23), (-3, 20), (0, 23), (3, 20), (6, 23)]))
    a.part("teeth", WHITE, rr(8.6, 9, 1.6, 0, 15.5))
    a.part("blush", "#F7A9B8", both(ell(-28, 30, 5.5, 3.2)))
    a.part("sparkle", WHITE, both(circ(-15.8, 40, 1.7)), 2)
    return reg(a)


def _panda():
    head = rr(88, 68, 28, 0, 34)
    sil = close(U(head, both(circ(-33, 66, 14.5))))
    a = Animal("panda", "Panda", "#F7F7F7", sil)
    a.part("ears", "#2B2B2B", both(circ(-33, 66, 14.5)).difference(head), 0)
    a.part("patches", "#2B2B2B", both(ell(-19, 44, 10.5, 8.5, 28)))
    a.part("nose", "#2B2B2B", ell(0, 30, 6.5, 4.4))
    a.part("mouth", "#2B2B2B", U(line([(0, 26), (0, 22)]), line([(-6, 19.5), (0, 22), (6, 19.5)])))
    a.part("pupils", WHITE, both(circ(-19.5, 44.5, 3.4)), 2)
    a.part("blush", "#F7B1BB", both(ell(-32, 27, 5, 3.0)))
    return reg(a)


def _pig():
    head = rr(88, 64, 28, 0, 32)
    ear = both(tri([(-44, 46), (-20, 62), (-46, 78)], 3.0))
    sil = close(U(head, ear))
    a = Animal("pig", "Pig", "#F7B8C6", sil)
    a.part("ears", "#EE96AB", ear.difference(head), 0)
    a.part("snout", "#EE8FA6", ell(0, 25, 18, 13.5))
    a.part("nostrils", "#B8506A", both(ell(-6.2, 25, 2.6, 4.3)), 2)
    a.part("eyes", DARK, both(circ(-21, 43, 4.8)))
    a.part("blush", "#F28FA5", both(ell(-32, 31, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-19.8, 44.8, 1.6)), 2)
    return reg(a)


def _owl():
    sil = close(U(rr(86, 84, 30, 0, 42), both(tri([(-43, 70), (-21, 84), (-45, 100)], 3.0))))
    a = Animal("owl", "Owl", "#9C7B5A", sil)
    a.part("belly", "#D8BE98", ell(0, 20, 28, 20))
    a.part("eye_rings", "#F6EAD2", both(ring(-18, 52, 16, 11.2)))
    a.part("eye_discs", "#FFF8EA", both(circ(-18, 52, 11.2)))
    a.part("pupils", DARK, both(circ(-18, 52, 6.5)))
    a.part("beak", "#F2A33A", tri([(-6.5, 40), (6.5, 40), (0, 27)], 1.2))
    a.part("scales", "#B38E64", U(*[ring(x, 23, 5.4, 3.3) for x in (-16.5, -5.5, 5.5, 16.5)], *[ring(x, 14, 5.4, 3.3) for x in (-11, 0, 11)]), 2)
    a.part("sparkle", WHITE, both(circ(-16, 54.2, 2.0)), 2)
    return reg(a)


def _chick():
    head = U(circ(0, 44, 42), rr(74, 24, 10, 0, 12)).intersection(box(-60, 0, 60, 82))
    crest = U(ell(-9, 84, 4.6, 11, 25), ell(0, 87, 4.6, 12, 0), ell(9, 84, 4.6, 11, -25))
    a = Animal("chick", "Chick", "#F9D74C", close(head), crest, "#F2B72C")
    a.part("wings", "#F2B72C", both(ell(-34, 36, 6.5, 13, 10)))
    a.part("beak", "#F28C28", tri([(-9.5, 42), (9.5, 42), (0, 27)], 1.6))
    a.part("eyes", DARK, both(circ(-20, 50, 5.4)))
    a.part("blush", "#F7A27A", both(ell(-31, 38, 6, 3.8)))
    a.part("sparkle", WHITE, both(circ(-18.6, 52, 1.9)), 2)
    return reg(a)


def _dino():
    spikes = U(*[tri([(x - 9, 58), (x + 9, 58), (x, 66 + h)], 2.0) for x, h in ((-36, 12), (-18, 19), (0, 23), (18, 19), (36, 12))])
    a = Animal("dino", "Dino", "#68CB8C", rr(90, 66, 26, 0, 33), spikes, "#F5A03A")
    a.part("spots", "#4DB07A", U(*[circ(sx * 33, 56, 3.6) for sx in (-1, 1)], *[circ(sx * 37, 36, 3.2) for sx in (-1, 1)]))
    a.part("eyes", DARK, both(circ(-19, 43, 5.4)))
    a.part("nostrils", DARK, both(ell(-6, 33, 2.3, 3.0)))
    a.part("smile", DARK, line([(-14, 28), (-8, 23), (0, 21), (8, 23), (14, 28)], 2.0))
    a.part("blush", "#F7A3B3", both(ell(-27, 30, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-17.6, 45.2, 1.9)), 2)
    return reg(a)


# ----------------------------------------------------------------------------- 12 more (SVG pack only)
def _fox():
    head = rr(86, 60, 26, 0, 30)
    sil = close(U(head, both(tri([(-44, 46), (-16, 60), (-40, 96)], 3.0)), both(tri([(-42, 38), (-54, 20), (-30, 12)], 2.0))))
    a = Animal("fox", "Fox", "#F28A36", sil)
    a.part("inner_ear", "#4A2C22", both(tri([(-38, 54), (-22, 60), (-38, 84)], 1.5)))
    a.part("muzzle", "#FFF4E6", U(ell(0, 15, 34, 22), both(tri([(-42, 36), (-52, 20), (-30, 12)], 1.5))))
    a.part("eyes", DARK, both(ell(-19, 40, 5.4, 6.4, -14)))
    a.part("nose", DARK, ell(0, 29, 6.0, 4.2), 2)
    a.part("mouth", DARK, U(line([(0, 25), (0, 20.5)]), line([(-7, 17.5), (0, 20.5), (7, 17.5)])), 2)
    a.part("blush", "#F58C86", both(ell(-31, 30, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-17.4, 42.2, 1.9)), 2)
    return reg(a)


def _koala():
    sil = close(U(rr(78, 66, 30, 0, 33), both(circ(-36, 62, 18))))
    a = Animal("koala", "Koala", "#B7BCC7", sil)
    a.part("inner_ear", "#F4E1E4", both(circ(-36, 62, 10.5)))
    a.part("eyes", DARK, both(circ(-21, 42, 3.9)))
    a.part("nose", "#3A3238", ell(0, 31, 7.6, 10.4))
    a.part("blush", "#F2B0B8", both(ell(-29, 30, 5.2, 3.2)))
    a.part("nose_shine", "#7A7078", ell(-2.8, 35.5, 2.0, 3.2), 2)
    a.part("sparkle", WHITE, both(circ(-20, 43.6, 1.4)), 2)
    return reg(a)


def _lion():
    mane = U(circ(0, 38, 44), *[circ(46 * math.cos(math.radians(k * 22.5)), 38 + 46 * math.sin(math.radians(k * 22.5)), 13) for k in range(16)])
    sil = close(U(rr(70, 62, 28, 0, 32), both(circ(-31, 62, 10))))
    a = Animal("lion", "Lion", "#F2B35E", sil, mane, "#B8651F")
    a.part("inner_ear", "#F8CF9C", both(circ(-31, 62, 5.8)))
    a.part("muzzle", "#FCE8C2", ell(0, 21, 19, 14))
    a.part("eyes", DARK, both(circ(-15, 40, 4.4)))
    a.part("nose", "#B15A3C", tri([(-5.5, 31), (5.5, 31), (0, 25)], 1.4), 2)
    a.part("mouth", DARK, U(line([(0, 25), (0, 21)]), line([(-7, 18), (0, 21), (7, 18)])), 2)
    a.part("blush", "#F59C8A", both(ell(-27, 31, 4.6, 2.8)))
    a.part("sparkle", WHITE, both(circ(-13.6, 41.6, 1.7)), 2)
    return reg(a)


def _mouse():
    sil = close(U(rr(76, 62, 28, 0, 31), both(circ(-33, 60, 17))))
    a = Animal("mouse", "Mouse", "#C8CDD6", sil)
    a.part("inner_ear", "#F4B6C6", both(circ(-33, 60, 10.5)))
    a.part("eyes", DARK, both(circ(-17, 38, 4.4)))
    a.part("nose", "#E9809B", ell(0, 29, 4.8, 3.5))
    a.part("whiskers", "#5A5460", both(U(*[line([(24, 27 + dz * 0.6), (42, 27 + dz * 1.8)], 1.5) for dz in (4, 0, -4)])))
    a.part("teeth", WHITE, rr(7.4, 8.4, 1.4, 0, 20.5))
    a.part("blush", "#F4A6B6", both(ell(-26, 30, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-15.8, 39.8, 1.6)), 2)
    return reg(a)


def _sheep():
    wool = U(ell(0, 40, 38, 36), *[circ(37 * math.cos(math.radians(k * 30)), 40 + 35 * math.sin(math.radians(k * 30)), 13) for k in range(12)])
    ears = both(ell(-45, 30, 11, 5.6, -20))
    a = Animal("sheep", "Sheep", "#F6F2E9", close(U(wool, ears)))
    a.part("ears", "#4B403B", ears, 0, clip=False)
    a.part("face", "#4B403B", ell(0, 26, 25, 28))
    a.part("eyes", WHITE, both(circ(-10, 32, 4.4)))
    a.part("pupils", "#241E1B", both(circ(-10, 32, 2.3)), 2)
    a.part("nose", "#F0A3B0", ell(0, 20, 4.4, 3.0))
    a.part("smile", "#F4DDD6", smile(8, 15.5, 2.0, 1.6))
    a.part("blush", "#E98E9A", both(ell(-17, 21, 4.2, 2.6)))
    return reg(a)


def _cow():
    head = rr(86, 64, 26, 0, 32)
    ears = both(ell(-47, 52, 13, 7, 20))
    horns = both(tri([(-30, 62), (-20, 62), (-26, 78)], 1.8))
    sil = close(U(head, ears, horns))
    a = Animal("cow", "Cow", "#F7F3EC", sil)
    a.part("ears", "#3B3430", ears.difference(head), 0, clip=False)
    a.part("horns", "#EBD39A", horns.difference(head), 0, clip=False)
    a.part("patches", "#3B3430", U(ell(-31, 55, 11, 8, 25), ell(34, 28, 9, 8, 0)))
    a.part("muzzle", "#F5B5C0", ell(0, 20, 25, 15))
    a.part("eyes", DARK, both(circ(-20, 45, 4.4)))
    a.part("nostrils", "#B8506A", both(ell(-8, 20, 3.0, 4.6)), 2)
    a.part("blush", "#F5A0AA", both(ell(-33, 31, 4.6, 2.8)))
    a.part("sparkle", WHITE, both(circ(-18.6, 46.6, 1.5)), 2)
    return reg(a)


def _frog():
    sil = close(U(rr(90, 56, 26, 0, 28), both(circ(-27, 60, 15))))
    a = Animal("frog", "Frog", "#6CCB6C", sil)
    a.part("eye_whites", WHITE, both(circ(-27, 60, 11)))
    a.part("pupils", DARK, both(circ(-27, 59, 6.2)), 1)
    a.part("belly", "#C8F0A8", ell(0, 14, 28, 12))
    a.part("nostrils", "#3F9A48", both(circ(-6, 38, 1.8)))
    a.part("mouth", "#2E5A2E", smile(26, 24, 5.0, 2.2))
    a.part("blush", "#F7A3A3", both(ell(-34, 26, 5.6, 3.2)))
    a.part("sparkle", WHITE, both(circ(-25, 61.4, 2.0)), 2)
    return reg(a)


def _penguin():
    feet = both(ell(-16, 2, 11, 5))
    body = U(ell(0, 42, 38, 41), rr(46, 12, 5, 0, 6))
    a = Animal("penguin", "Penguin", "#2F3B5C", close(U(body, feet)))
    a.part("feet", "#F5A031", feet, 0, clip=False)
    a.part("face", "#F7F7F7", U(circ(-13, 46, 19), circ(13, 46, 19), ell(0, 30, 27, 19)))
    a.part("eyes", DARK, both(circ(-14, 47, 4.7)))
    a.part("beak", "#F5A031", tri([(-8.5, 37), (8.5, 37), (0, 26)], 1.6), 2)
    a.part("blush", "#F7A0AE", both(ell(-26, 34, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-12.6, 48.8, 1.7)), 2)
    return reg(a)


def _unicorn():
    mane = U(*[circ(sx * x, z, r) for sx in (-1, 1) for x, z, r in ((40, 54, 16), (45, 36, 14), (41, 20, 12), (30, 70, 12))])
    horn = tri([(-8, 62), (8, 62), (0, 104)], 1.2)
    sil = close(U(rr(78, 66, 28, 0, 33), both(tri([(-34, 62), (-20, 64), (-36, 84)], 2.5)), horn))
    a = Animal("unicorn", "Unicorn", "#F7EEF7", sil, mane, "#C48BE2")
    a.part("horn", "#F6C85F", horn.intersection(box(-20, 62, 20, 110)), 0, clip=False)
    a.part("inner_ear", "#F8C2DC", both(tri([(-31, 64), (-23, 65), (-33, 78)], 1.2)))
    a.part("forelock", "#C48BE2", U(ell(-9, 68, 13, 8, 18), ell(9, 70, 11, 7, -12)), 1, clip=False)
    a.part("eyes", DARK, both(ell(-17, 40, 4.4, 5.4)))
    a.part("nostrils", "#E8A0B8", both(ell(-5, 24, 2.0, 2.8)))
    a.part("smile", "#B35C8A", smile(8, 18, 2.0, 1.6))
    a.part("blush", "#F8A8C4", both(ell(-27, 29, 5.4, 3.2)))
    a.part("sparkle", WHITE, both(circ(-15.8, 42, 1.7)), 2)
    return reg(a)


def _giraffe():
    head = rr(70, 62, 26, 0, 31)
    ossi = both(U(rr(6.4, 24, 3, -15, 72), circ(-15, 86, 5.4)))
    ears = both(ell(-41, 54, 12, 6, 25))
    sil = close(U(head, ossi, ears))
    a = Animal("giraffe", "Giraffe", "#F6C453", sil)
    a.part("tips", "#6B4A2A", both(circ(-15, 86, 5.4)), 0, clip=False)
    a.part("ears", "#C98B2E", ears.difference(head), 0, clip=False)
    a.part("spots", "#C98B2E", U(circ(-24, 52, 5), circ(22, 54, 4.2), circ(-8, 56, 3.6), circ(28, 40, 3.8), circ(-30, 40, 3.2)))
    a.part("muzzle", "#F9E3A6", ell(0, 19, 22, 14))
    a.part("eyes", DARK, both(circ(-16, 42, 4.4)))
    a.part("nostrils", "#9B5E2A", both(ell(-7, 20, 2.4, 3.6)), 2)
    a.part("blush", "#F59E86", both(ell(-28, 29, 4.8, 2.8)))
    a.part("sparkle", WHITE, both(circ(-14.6, 43.6, 1.5)), 2)
    return reg(a)


def _elephant():
    ears = both(circ(-42, 46, 24))
    trunk = rr(17, 42, 8, 0, 21)
    sil = close(U(rr(62, 62, 26, 0, 31), ears, trunk))
    a = Animal("elephant", "Elephant", "#9FACBF", sil)
    a.part("inner_ear", "#E8B8C8", both(circ(-42, 46, 15)), 0)
    a.part("trunk_lines", "#7D8BA0", U(*[line([(-6.5, z), (6.5, z)], 1.6) for z in (28, 21, 14)]))
    a.part("eyes", DARK, both(circ(-15, 46, 4.4)))
    a.part("blush", "#F2A5B7", both(ell(-24, 34, 5, 3.0)))
    a.part("tusks", "#FFF6E2", both(tri([(-14, 20), (-8, 20), (-16, 6)], 1.4)), 2)
    a.part("sparkle", WHITE, both(circ(-13.6, 47.6, 1.5)), 2)
    return reg(a)


def _hippo():
    sil = close(U(rr(90, 60, 28, 0, 30), both(circ(-27, 64, 8.5))))
    a = Animal("hippo", "Hippo", "#A98BD8", sil)
    a.part("inner_ear", "#E2C4F0", both(circ(-27, 64, 4.6)))
    a.part("snout", "#C7AFEA", ell(0, 19, 35, 19))
    a.part("nostrils", "#6C4FA6", both(ell(-12, 24, 3.6, 5.0)), 2)
    a.part("eyes", DARK, both(circ(-22, 46, 4.7)))
    a.part("blush", "#F4A5C0", both(ell(-34, 30, 5, 3.0)))
    a.part("sparkle", WHITE, both(circ(-20.6, 47.8, 1.6)), 2)
    return reg(a)


for _f in (_cat, _bear, _bunny, _panda, _pig, _owl, _chick, _dino, _fox, _koala, _lion, _mouse, _sheep, _cow, _frog, _penguin, _unicorn,
           _giraffe, _elephant, _hippo):
    _f()

ORDER = ["cat", "bear", "bunny", "panda", "pig", "owl", "chick", "dino", "fox", "koala", "lion", "mouse", "sheep", "cow", "frog",
         "penguin", "unicorn", "giraffe", "elephant", "hippo"]
CUPS = ["cat", "bear", "bunny", "panda", "pig", "owl", "chick", "dino"]


if __name__ == "__main__":
    from PIL import Image
    from etsy_factory.typo import export as X
    from pathlib import Path
    cols, S = 5, 400
    sheet = Image.new("RGB", (cols * S, ((len(ORDER) + cols - 1) // cols) * S), (255, 255, 255))
    for i, k in enumerate(ORDER):
        a = A[k]
        th = X.thumb_layers([(g, tuple(int(h.lstrip('#')[j:j + 2], 16) for j in (0, 2, 4))) for _, g, h in a.svg_layers()], S - 20, pad=0.04)
        sheet.paste(th, ((i % cols) * S + 10, (i // cols) * S + 10))
    out = Path(r"F:\WORKHORSE\workspace\scratch\faces_sheet.jpg")
    sheet.save(out, quality=90)
    print("saved", out)
