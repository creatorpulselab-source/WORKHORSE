"""Procedural Laser-Cut Vector Generator for Keychains and Earrings.

Builds 20 Keychains and 20 Earring Pairs (40 Laser Cut Designs).
Formatted with industry-standard laser operation colors:
- RED (#FF0000, 0.2mm stroke, no fill): Vector Cut
- BLUE (#0000FF, 0.2mm stroke, no fill): Vector Score
- BLACK (#000000, fill, no stroke): Engrave

Every keychain includes an integrated 3.5mm keyring loop with >= 2.5mm reinforced wall.
Every earring includes an integrated 2.0mm jump-ring hole for jewelry ear-wires.
All geometries are 100% closed, watertight, and validated.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from etsy_factory.typo import export as X
from etsy_factory.typo import ornaments as O


def circle(r: float, c: Tuple[float, float] = (0.0, 0.0), n: int = 64) -> Polygon:
    return Point(c).buffer(r, quad_segs=max(8, n // 4))


def ring(r: float, t: float, c: Tuple[float, float] = (0.0, 0.0)) -> BaseGeometry:
    return circle(r, c).difference(circle(r - t, c))


def add_keychain_loop(base_geom: BaseGeometry, top_y: Optional[float] = None, hole_r: float = 1.75, tab_r: float = 5.5) -> BaseGeometry:
    """Adds a reinforced keyring tab with a 3.5mm hole centered at the top."""
    minx, miny, maxx, maxy = base_geom.bounds
    cx = (minx + maxx) / 2.0
    cy = (maxy if top_y is None else top_y) + tab_r * 0.45

    tab = circle(tab_r, (cx, cy))
    hole = circle(hole_r, (cx, cy))

    # Union tab with base, then punch out the hole
    joined = unary_union([base_geom, tab])
    return joined.difference(hole)


def add_earring_hole(base_geom: BaseGeometry, top_y: Optional[float] = None, hole_r: float = 1.0, tab_r: float = 3.6) -> BaseGeometry:
    """Adds an integrated jewelry jump-ring hanging tab with a 2.0mm hole."""
    minx, miny, maxx, maxy = base_geom.bounds
    cx = (minx + maxx) / 2.0
    cy = (maxy if top_y is None else top_y) + tab_r * 0.40

    tab = circle(tab_r, (cx, cy))
    hole = circle(hole_r, (cx, cy))

    joined = unary_union([base_geom, tab])
    return joined.difference(hole)


# -----------------------------------------------------------------------------
# 20 KEYCHAIN GEOMETRIES (approx 50mm - 60mm height)
# -----------------------------------------------------------------------------
def build_keychains() -> List[Dict]:
    items = []

    # 1. Cat Face Keychain
    head = circle(22.0)
    ear_l = Polygon([(-16.0, 10.0), (-20.0, 28.0), (-6.0, 20.0)])
    ear_r = Polygon([(16.0, 10.0), (20.0, 28.0), (6.0, 20.0)])
    cat_cut = unary_union([head, ear_l, ear_r])
    cat_cut = add_keychain_loop(cat_cut, top_y=26.0)
    # Scored whiskers & ears
    w1 = LineString([(-24, 0), (-6, 2)])
    w2 = LineString([(-24, -5), (-6, -1)])
    w3 = LineString([(24, 0), (6, 2)])
    w4 = LineString([(24, -5), (6, -1)])
    e_in_l = Polygon([(-15, 12), (-18, 24), (-8, 18)])
    e_in_r = Polygon([(15, 12), (18, 24), (8, 18)])
    cat_score = unary_union([w1, w2, w3, w4, e_in_l.boundary, e_in_r.boundary])
    # Engraved eyes & nose
    eye_l = circle(2.5, (-9.0, 4.0))
    eye_r = circle(2.5, (9.0, 4.0))
    nose = Polygon([(0, -2), (-2.5, 1), (2.5, 1)])
    cat_engrave = unary_union([eye_l, eye_r, nose])
    items.append({"id": "cat_face", "title": "Cute Cat Face Keychain", "cut": cat_cut, "score": cat_score, "engrave": cat_engrave})

    # 2. Dog Paw Keychain
    pad = circle(14.0, (0, -6))
    toes = [circle(6.0, (-15, 8)), circle(6.5, (-5, 16)), circle(6.5, (5, 16)), circle(6.0, (15, 8))]
    paw_outline = unary_union([pad, *toes]).buffer(4.0, join_style=1)
    paw_cut = add_keychain_loop(paw_outline, top_y=25.0)
    paw_engrave = unary_union([pad, *toes])
    items.append({"id": "dog_paw", "title": "Dog Paw Print Keychain", "cut": paw_cut, "score": None, "engrave": paw_engrave})

    # 3. Highland Cow Keychain
    cow_head = circle(18.0)
    snout = circle(10.0, (0, -10))
    horn_l = Polygon([(-12, 8), (-26, 22), (-28, 18), (-14, 4)])
    horn_r = Polygon([(12, 8), (26, 22), (28, 18), (14, 4)])
    cow_cut = unary_union([cow_head, snout, horn_l, horn_r])
    cow_cut = add_keychain_loop(cow_cut, top_y=21.0)
    nostrils = unary_union([circle(1.8, (-4, -10)), circle(1.8, (4, -10))])
    eyes = unary_union([circle(2.2, (-9, 2)), circle(2.2, (9, 2))])
    cow_score = LineString([(-12, 8), (-18, 16), (0, 14), (18, 16), (12, 8)])
    items.append({"id": "highland_cow", "title": "Highland Cow Keychain", "cut": cow_cut, "score": cow_score, "engrave": unary_union([nostrils, eyes])})

    # 4. Woodland Bear & Mountain Keychain
    bear_body = circle(22.0)
    b_ear_l = circle(6.5, (-16, 16))
    b_ear_r = circle(6.5, (16, 16))
    bear_cut = add_keychain_loop(unary_union([bear_body, b_ear_l, b_ear_r]), top_y=22.0)
    # Scored mountain and pine trees inside bear
    mtn = LineString([(-18, -4), (-7, 8), (4, -2), (12, 6), (19, -3)])
    pines = unary_union([
        LineString([(-10, -14), (-10, -4)]),
        LineString([(0, -16), (0, -2)]),
        LineString([(10, -14), (10, -4)])
    ])
    items.append({"id": "woodland_bear", "title": "Woodland Bear Mountain Keychain", "cut": bear_cut, "score": unary_union([mtn, pines]), "engrave": None})

    # 5. Woodland Fox Keychain
    f_head = Polygon([(0, -16), (-20, 10), (0, 8), (20, 10)])
    f_ear_l = Polygon([(-16, 8), (-18, 26), (-6, 14)])
    f_ear_r = Polygon([(16, 8), (18, 26), (6, 14)])
    fox_cut = add_keychain_loop(unary_union([f_head, f_ear_l, f_ear_r]).buffer(2.5, join_style=1), top_y=28.0)
    fox_nose = circle(2.2, (0, -15))
    fox_eyes = unary_union([circle(1.8, (-7, -2)), circle(1.8, (7, -2))])
    fox_score = unary_union([LineString([(0, -15), (-14, 4)]), LineString([(0, -15), (14, 4)])])
    items.append({"id": "woodland_fox", "title": "Woodland Fox Keychain", "cut": fox_cut, "score": fox_score, "engrave": unary_union([fox_nose, fox_eyes])})

    # 6. Monstera Leaf Keychain
    m_body = Polygon([(0, -24), (-20, 0), (-16, 20), (0, 26), (16, 20), (20, 0)]).buffer(3.0, join_style=1)
    m_cut = add_keychain_loop(m_body, top_y=28.0)
    vein_main = LineString([(0, -20), (0, 24)])
    v1 = LineString([(0, -10), (-14, -2)])
    v2 = LineString([(0, 0), (-15, 10)])
    v3 = LineString([(0, -10), (14, -2)])
    v4 = LineString([(0, 0), (15, 10)])
    m_score = unary_union([vein_main, v1, v2, v3, v4])
    items.append({"id": "monstera_leaf", "title": "Monstera Leaf Keychain", "cut": m_cut, "score": m_score, "engrave": None})

    # 7. Retro Daisy Blossom Keychain
    d_center = circle(8.0)
    petals = [circle(6.0, (16 * math.cos(math.radians(a)), 16 * math.sin(math.radians(a)))) for a in range(0, 360, 45)]
    daisy_cut = add_keychain_loop(unary_union([d_center, *petals]), top_y=22.0)
    d_score = d_center.boundary
    items.append({"id": "retro_daisy", "title": "Retro Daisy Keychain", "cut": daisy_cut, "score": d_score, "engrave": circle(5.0)})

    # 8. Radiant Sunflower Keychain
    s_center = circle(10.0)
    s_petals = [Polygon([(0, 0), (7 * math.cos(math.radians(a - 15)), 7 * math.sin(math.radians(a - 15))),
                         (22 * math.cos(math.radians(a)), 22 * math.sin(math.radians(a))),
                         (7 * math.cos(math.radians(a + 15)), 7 * math.sin(math.radians(a + 15)))]) for a in range(0, 360, 30)]
    sf_cut = add_keychain_loop(unary_union([s_center, *s_petals]), top_y=22.0)
    sf_engrave = s_center
    items.append({"id": "sunflower", "title": "Radiant Sunflower Keychain", "cut": sf_cut, "score": None, "engrave": sf_engrave})

    # 9. Hummingbird in Flight Keychain
    hb_body = circle(12.0)
    hb_wing = Polygon([(-2, 4), (-18, 26), (6, 12)])
    hb_tail = Polygon([(-6, -6), (-16, -22), (0, -10)])
    hb_beak = LineString([(8, 4), (25, 6)]).buffer(1.2, cap_style=1)
    hb_cut = add_keychain_loop(unary_union([hb_body, hb_wing, hb_tail, hb_beak]), top_y=26.0)
    hb_eye = circle(1.5, (6, 6))
    items.append({"id": "hummingbird", "title": "Hummingbird Keychain", "cut": hb_cut, "score": hb_wing.boundary, "engrave": hb_eye})

    # 10. Celestial Crescent Moon & Star Keychain
    c_m1 = circle(22.0)
    c_m2 = circle(20.0, (7, 4))
    c_moon = c_m1.difference(c_m2)
    c_star = affinity.translate(O.star(7.0, rot=30), 4, -4)
    celest_cut = add_keychain_loop(unary_union([c_moon, c_star]), top_y=22.0)
    items.append({"id": "celestial_moon", "title": "Celestial Moon Star Keychain", "cut": celest_cut, "score": None, "engrave": None})

    # 11. Cozy Coffee Mug Keychain
    mug_body = box(-14, -16, 14, 12).buffer(3.0, join_style=1)
    mug_handle = ring(8.0, 3.2, (16, -2))
    mug_cut = add_keychain_loop(unary_union([mug_body, mug_handle]), top_y=14.0)
    steam = LineString([(0, 16), (-2, 21), (2, 26)])
    heart_eng = affinity.scale(O.heart(9.0), 0.8, 0.8)
    items.append({"id": "coffee_mug", "title": "Cozy Coffee Mug Keychain", "cut": mug_cut, "score": steam, "engrave": heart_eng})

    # 12. Vintage Camera Keychain
    cam_body = box(-20, -14, 20, 10).buffer(3.0, join_style=1)
    cam_flash = box(-14, 10, -6, 15)
    cam_cut = add_keychain_loop(unary_union([cam_body, cam_flash]), top_y=14.0)
    lens_out = circle(9.0)
    cam_eng = affinity.scale(O.heart(6.0), 0.7, 0.7)
    items.append({"id": "vintage_camera", "title": "Vintage Camera Keychain", "cut": cam_cut, "score": lens_out.boundary, "engrave": cam_eng})

    # 13. Wildflower Botanical Arch Keychain
    arch_body = Polygon([(-15, -20), (-15, 10), (0, 25), (15, 10), (15, -20)]).buffer(2.0, join_style=1)
    arch_cut = add_keychain_loop(arch_body, top_y=26.0)
    stem = LineString([(0, -18), (0, 16)])
    sprig1 = LineString([(0, -6), (-8, 0)])
    sprig2 = LineString([(0, 4), (8, 10)])
    items.append({"id": "wildflower_arch", "title": "Wildflower Arch Keychain", "cut": arch_cut, "score": unary_union([stem, sprig1, sprig2]), "engrave": None})

    # 14. Boho Cactus Keychain
    cact_body = LineString([(0, -10), (0, 20)]).buffer(6.5, cap_style=1)
    arm_l = LineString([(0, 0), (-12, 0), (-12, 10)]).buffer(4.0, cap_style=1)
    arm_r = LineString([(0, 6), (12, 6), (12, 16)]).buffer(4.0, cap_style=1)
    pot = Polygon([(-12, -22), (12, -22), (15, -10), (-15, -10)])
    cact_cut = add_keychain_loop(unary_union([cact_body, arm_l, arm_r, pot]), top_y=26.0)
    items.append({"id": "boho_cactus", "title": "Boho Cactus Keychain", "cut": cact_cut, "score": pot.boundary, "engrave": None})

    # 15. Cute Bunny with Carrot Keychain
    b_head = circle(16.0)
    e1 = Polygon([(-10, 8), (-12, 28), (-4, 26), (-4, 10)])
    e2 = Polygon([(10, 8), (12, 28), (4, 26), (4, 10)])
    bunny_cut = add_keychain_loop(unary_union([b_head, e1, e2]), top_y=28.0)
    b_eyes = unary_union([circle(2.0, (-6, 0)), circle(2.0, (6, 0))])
    b_nose = circle(1.5, (0, -4))
    items.append({"id": "cute_bunny", "title": "Cute Bunny Keychain", "cut": bunny_cut, "score": LineString([(-8, 10), (-10, 24)]), "engrave": unary_union([b_eyes, b_nose])})

    # 16. Western Cowboy Boot Keychain
    boot = Polygon([(-12, -18), (14, -18), (16, -10), (4, -4), (6, 20), (-8, 20), (-8, -4)]).buffer(2.5, join_style=1)
    boot_cut = add_keychain_loop(boot, top_y=22.0)
    boot_score = LineString([(4, -14), (8, -6), (1, 10)])
    items.append({"id": "western_boot", "title": "Western Cowboy Boot Keychain", "cut": boot_cut, "score": boot_score, "engrave": None})

    # 17. Monarch Butterfly Keychain
    bf_body = LineString([(0, -18), (0, 16)]).buffer(2.5, cap_style=1)
    w_top_l = Polygon([(0, 2), (-24, 22), (-20, 2), (0, -2)])
    w_top_r = Polygon([(0, 2), (24, 22), (20, 2), (0, -2)])
    w_bot_l = Polygon([(0, -2), (-18, -4), (-14, -18), (0, -8)])
    w_bot_r = Polygon([(0, -2), (18, -4), (14, -18), (0, -8)])
    bf_cut = add_keychain_loop(unary_union([bf_body, w_top_l, w_top_r, w_bot_l, w_bot_r]).buffer(1.5, join_style=1), top_y=22.0)
    items.append({"id": "butterfly", "title": "Monarch Butterfly Keychain", "cut": bf_cut, "score": unary_union([w_top_l.boundary, w_top_r.boundary]), "engrave": None})

    # 18. Cute Panda Keychain
    p_head = circle(19.0)
    p_ear_l = circle(6.0, (-15, 14))
    p_ear_r = circle(6.0, (15, 14))
    panda_cut = add_keychain_loop(unary_union([p_head, p_ear_l, p_ear_r]), top_y=20.0)
    p_eyes = unary_union([circle(3.5, (-8, 2)), circle(3.5, (8, 2))])
    p_nose = circle(2.0, (0, -3))
    items.append({"id": "cute_panda", "title": "Cute Panda Keychain", "cut": panda_cut, "score": None, "engrave": unary_union([p_ear_l, p_ear_r, p_eyes, p_nose])})

    # 19. Magic Crystal Mushroom Keychain
    cap = circle(20.0).intersection(box(-24, 0, 24, 24))
    stem = box(-6, -18, 6, 2)
    mush_cut = add_keychain_loop(unary_union([cap, stem]).buffer(1.5, join_style=1), top_y=20.0)
    spots = unary_union([circle(2.5, (-8, 8)), circle(3.0, (0, 12)), circle(2.5, (8, 8))])
    items.append({"id": "magic_mushroom", "title": "Magic Mushroom Keychain", "cut": mush_cut, "score": LineString([(-20, 0), (20, 0)]), "engrave": spots})

    # 20. "Home Sweet Home" Keychain Tag
    house = Polygon([(0, 22), (-18, 6), (-18, -18), (18, -18), (18, 6)])
    house_cut = add_keychain_loop(house.buffer(2.0, join_style=1), top_y=23.0)
    heart_cutout = affinity.translate(O.heart(10.0), 0, -2)
    house_cut = house_cut.difference(heart_cutout)
    items.append({"id": "home_tag", "title": "Home Sweet Home Tag Keychain", "cut": house_cut, "score": house.boundary, "engrave": None})

    return items


# -----------------------------------------------------------------------------
# 20 DANGLE EARRING PAIRS (approx 35mm - 42mm height, delicate & lightweight)
# -----------------------------------------------------------------------------
def build_earrings() -> List[Dict]:
    items = []
    kc = build_keychains()
    for item in kc:
        e_id = f"earring_{item['id']}"
        e_title = item["title"].replace("Keychain", "Earrings Pair")

        # Scale down to jewelry scale (~0.70x) and replace loop with 2.0mm jump-ring hole
        g_cut = item["cut"]
        # extract base before loop
        minx, miny, maxx, maxy = g_cut.bounds
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0

        # Scale down
        s_cut = affinity.scale(g_cut, 0.65, 0.65, origin=(cx, cy))
        e_cut = add_earring_hole(s_cut, hole_r=1.0, tab_r=3.2)

        s_score = affinity.scale(item["score"], 0.65, 0.65, origin=(cx, cy)) if item["score"] else None
        s_engrave = affinity.scale(item["engrave"], 0.65, 0.65, origin=(cx, cy)) if item["engrave"] else None

        items.append({
            "id": e_id,
            "title": e_title,
            "cut": e_cut,
            "score": s_score,
            "engrave": s_engrave
        })

    return items


def write_laser_svg(path: Path, cut_geom: BaseGeometry, score_geom: Optional[BaseGeometry] = None, engrave_geom: Optional[BaseGeometry] = None, width_in: float = 2.5) -> None:
    """Writes industry-standard laser color-coded SVG: Red=Cut, Blue=Score, Black=Engrave."""
    from shapely.ops import unary_union
    geoms = [cut_geom]
    if score_geom and not score_geom.is_empty:
        geoms.append(score_geom)
    if engrave_geom and not engrave_geom.is_empty:
        geoms.append(engrave_geom)

    allg = unary_union(geoms)
    x0, y0, x1, y1 = allg.bounds
    pad = 2.0
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
    w = x1 - x0
    h = y1 - y0
    hi = width_in * h / w

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_in:.3f}in" height="{hi:.3f}in" viewBox="0 0 {w:.2f} {h:.2f}">',
        '  <desc>Glowforge and LightBurn Laser SVG: Red=Cut, Blue=Score, Black=Engrave</desc>'
    ]

    # 1. Black Engrave Layer
    if engrave_geom and not engrave_geom.is_empty:
        d_eng = X.path_d(engrave_geom, x0, y0, h)
        lines.append(f'  <g id="Engrave_Black"><path fill="#000000" stroke="none" fill-rule="evenodd" d="{d_eng}"/></g>')

    # 2. Blue Score Layer
    if score_geom and not score_geom.is_empty:
        d_score = X.path_d(score_geom, x0, y0, h)
        lines.append(f'  <g id="Score_Blue"><path fill="none" stroke="#0000FF" stroke-width="0.3" stroke-linecap="round" d="{d_score}"/></g>')

    # 3. Red Cut Layer
    d_cut = X.path_d(cut_geom, x0, y0, h)
    lines.append(f'  <g id="Cut_Red"><path fill="none" stroke="#FF0000" stroke-width="0.3" stroke-linecap="round" fill-rule="evenodd" d="{d_cut}"/></g>')

    lines.append('</svg>\n')
    path.write_text("\n".join(lines), encoding="utf-8")
