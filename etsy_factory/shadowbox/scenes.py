"""Procedural 3D Layered Shadow Box vector geometry generator.

Builds 4 complete multi-depth shadow box art themes, each with 6 numbered layers:
1. Woodland Deer & Forest (Moonlit forest, mama deer & fawn, pine trees, owl)
2. Moonlit Safari & Gentle Giants (Savanna moon, mama & baby elephant, acacia trees)
3. Dreamy Nursery Hot Air Balloon (Crescent moon, clouds, hot air balloon, stars)
4. Under the Sea & Gentle Whales (Ocean depth, humpback whale & calf, coral, kelp)

Standard coordinate system: 200.0 x 200.0 mm (8.0 x 8.0 inches), scalable to any square frame.
Every layer contains a continuous solid outer perimeter (15 mm margin) for foam adhesive spacers,
and 100% closed, cuttable compound paths for Cricut & Silhouette cutting.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from etsy_factory.typo import ornaments as O

SIZE_MM = 200.0       # 8x8 inches = 203.2 mm, 200 mm clean round coordinate space
MARGIN = 15.0         # 15 mm border margin for double-sided foam tape adhesive


def outer_frame() -> Polygon:
    """Outer 200x200 mm border with inner 170x170 mm window cut out."""
    outer = box(0, 0, SIZE_MM, SIZE_MM)
    inner = box(MARGIN, MARGIN, SIZE_MM - MARGIN, SIZE_MM - MARGIN)
    return outer.difference(inner)


def base_frame(content: BaseGeometry) -> BaseGeometry:
    """Unions custom silhouette content with the outer spacer frame, keeping 0..SIZE bounds."""
    f = outer_frame()
    # Clip content to inside the outer bounds
    clipped = content.intersection(box(0, 0, SIZE_MM, SIZE_MM))
    welded = unary_union([f, clipped])
    return welded


# -----------------------------------------------------------------------------
# SHADOW BOX THEME 1: WOODLAND DEER & FOREST
# -----------------------------------------------------------------------------
def build_woodland_deer_layers() -> List[Tuple[str, BaseGeometry, str]]:
    """Returns 6 layers from back (Layer 1) to front (Layer 6)."""
    layers = []

    # Layer 1: Solid Back Panel with Crescent Moon & Twinkling Stars (for LED backlighting)
    full_back = box(0, 0, SIZE_MM, SIZE_MM)
    # Crescent moon
    moon_r = 18.0
    c1 = Point(145.0, 150.0).buffer(moon_r)
    c2 = Point(139.0, 154.0).buffer(moon_r * 0.95)
    crescent = c1.difference(c2)
    # Star cutouts
    stars = [
        O.star(5.5, rot=15).buffer(0.2) if hasattr(O, "star") else Point(0, 0).buffer(3),
        O.star(4.0, rot=45).buffer(0.2),
        O.star(6.0, rot=25).buffer(0.2),
        O.star(4.5, rot=70).buffer(0.2),
        O.star(3.5, rot=10).buffer(0.2),
        O.star(5.0, rot=30).buffer(0.2),
    ]
    star_pos = [(40.0, 160.0), (75.0, 175.0), (105.0, 155.0), (165.0, 172.0), (60.0, 140.0), (90.0, 125.0)]
    star_geoms = [affinity.translate(s, px, py) for s, (px, py) in zip(stars, star_pos)]
    l1 = full_back.difference(unary_union([crescent, *star_geoms]))
    layers.append(("Layer_01_Back_Moon_Stars", l1, "#1B2430"))

    # Layer 2: Distant Mountain Range & Far Tree Silhouettes
    # Mountain ridge across bottom up to y=105
    pts2 = [
        (MARGIN, MARGIN), (MARGIN, 85.0), (55.0, 115.0), (90.0, 95.0),
        (135.0, 122.0), (165.0, 98.0), (SIZE_MM - MARGIN, 110.0),
        (SIZE_MM - MARGIN, MARGIN)
    ]
    mtn = Polygon(pts2)
    layers.append(("Layer_02_Distant_Mountains", base_frame(mtn), "#2C3E50"))

    # Layer 3: Midground Pine Forest & Flying Owl
    # Tree shapes across y=55 to y=110
    tree_pts = []
    # Row of triangular pine peaks
    xs = np.linspace(MARGIN, SIZE_MM - MARGIN, 9)
    pines = []
    for i, x in enumerate(xs):
        th = 40.0 + (i % 3) * 12.0
        p = Polygon([(x - 12.0, MARGIN), (x, MARGIN + th), (x + 12.0, MARGIN)])
        pines.append(p)
    # Ground slab
    pines.append(box(MARGIN, MARGIN, SIZE_MM - MARGIN, MARGIN + 40.0))
    # Owl silhouette flying top left
    owl_body = Point(65.0, 145.0).buffer(4.0)
    owl_w1 = Polygon([(65.0, 145.0), (48.0, 158.0), (58.0, 143.0)])
    owl_w2 = Polygon([(65.0, 145.0), (82.0, 158.0), (72.0, 143.0)])
    owl = unary_union([owl_body, owl_w1, owl_w2])
    l3_geom = unary_union([*pines, owl])
    layers.append(("Layer_03_Midground_Forest_Owl", base_frame(l3_geom), "#3D5A5B"))

    # Layer 4: Mama Deer & Baby Fawn Resting Among Ferns
    ground4 = Polygon([
        (MARGIN, MARGIN), (MARGIN, 48.0), (50.0, 56.0), (100.0, 46.0),
        (150.0, 54.0), (SIZE_MM - MARGIN, 46.0), (SIZE_MM - MARGIN, MARGIN)
    ])
    # Mama deer silhouette (standing gracefully facing right)
    d_body = Point(75.0, 68.0).buffer(9.0)
    d_chest = Point(82.0, 72.0).buffer(7.0)
    d_neck = Polygon([(78.0, 74.0), (86.0, 92.0), (92.0, 90.0), (84.0, 70.0)])
    d_head = Point(89.0, 93.0).buffer(5.5)
    d_snout = Polygon([(89.0, 95.0), (98.0, 91.0), (90.0, 89.0)])
    d_ear = Polygon([(86.0, 96.0), (84.0, 104.0), (90.0, 98.0)])
    # Legs
    leg1 = box(70.0, MARGIN, 73.5, 65.0)
    leg2 = box(74.5, MARGIN, 77.5, 66.0)
    leg3 = box(81.0, MARGIN, 84.5, 68.0)
    leg4 = box(86.0, MARGIN, 89.0, 69.0)
    mama_deer = unary_union([d_body, d_chest, d_neck, d_head, d_snout, d_ear, leg1, leg2, leg3, leg4])

    # Baby fawn lying down (right side)
    f_body = Point(115.0, 56.0).buffer(6.5)
    f_neck = Polygon([(117.0, 58.0), (122.0, 70.0), (126.0, 68.0), (121.0, 56.0)])
    f_head = Point(124.0, 71.0).buffer(4.0)
    f_ear = Polygon([(122.0, 73.0), (121.0, 78.0), (125.0, 75.0)])
    fawn = unary_union([f_body, f_neck, f_head, f_ear])

    l4_geom = unary_union([ground4, mama_deer, fawn])
    layers.append(("Layer_04_Mama_And_Baby_Deer", base_frame(l4_geom), "#537A68"))

    # Layer 5: Foreground Arching Birch Trunks & Ferns
    # Left tree trunk arching in
    tr_l = Polygon([(MARGIN, MARGIN), (MARGIN, SIZE_MM - MARGIN), (MARGIN + 16.0, SIZE_MM - MARGIN), (MARGIN + 22.0, 120.0), (MARGIN + 14.0, MARGIN)])
    # Left branch
    br_l = Polygon([(MARGIN + 16.0, 140.0), (75.0, 168.0), (74.0, 162.0), (MARGIN + 18.0, 134.0)])
    # Right tree trunk arching in
    tr_r = Polygon([(SIZE_MM - MARGIN - 14.0, MARGIN), (SIZE_MM - MARGIN - 20.0, 110.0), (SIZE_MM - MARGIN - 12.0, SIZE_MM - MARGIN), (SIZE_MM - MARGIN, SIZE_MM - MARGIN), (SIZE_MM - MARGIN, MARGIN)])
    br_r = Polygon([(SIZE_MM - MARGIN - 14.0, 130.0), (130.0, 158.0), (131.0, 153.0), (SIZE_MM - MARGIN - 12.0, 125.0)])
    # Foreground rolling hill with grassy tufts
    fg_hill = Polygon([
        (MARGIN, MARGIN), (MARGIN, 34.0), (60.0, 39.0), (110.0, 32.0),
        (160.0, 38.0), (SIZE_MM - MARGIN, 35.0), (SIZE_MM - MARGIN, MARGIN)
    ])
    l5_geom = unary_union([tr_l, br_l, tr_r, br_r, fg_hill])
    layers.append(("Layer_05_Foreground_Birch_Trees", base_frame(l5_geom), "#709775"))

    # Layer 6: Decorative Front Frame with Rounded Inner Bevel Corners
    outer_box = box(0, 0, SIZE_MM, SIZE_MM)
    inner_cut = box(MARGIN + 2, MARGIN + 2, SIZE_MM - MARGIN - 2, SIZE_MM - MARGIN - 2)
    l6 = outer_box.difference(inner_cut)
    layers.append(("Layer_06_Front_Decorative_Frame", l6, "#8FA792"))

    return layers


# -----------------------------------------------------------------------------
# SHADOW BOX THEME 2: MOONLIT SAFARI & GENTLE GIANTS
# -----------------------------------------------------------------------------
def build_moonlit_safari_layers() -> List[Tuple[str, BaseGeometry, str]]:
    layers = []

    # Layer 1: Solid Back Panel with Large Savanna Harvest Moon
    full_back = box(0, 0, SIZE_MM, SIZE_MM)
    moon = Point(100.0, 135.0).buffer(28.0)
    # Flying birds silhouettes across moon
    birds = [
        Polygon([(60.0, 168.0), (68.0, 172.0), (64.0, 167.0), (68.0, 165.0)]),
        Polygon([(82.0, 174.0), (90.0, 178.0), (86.0, 173.0), (90.0, 171.0)]),
        Polygon([(135.0, 166.0), (142.0, 170.0), (138.0, 165.0), (142.0, 163.0)]),
    ]
    l1 = full_back.difference(unary_union([moon, *birds]))
    layers.append(("Layer_01_Back_Savanna_Moon", l1, "#261C14"))

    # Layer 2: Distant Savanna Horizon & Rolling Hills
    hill_pts = [
        (MARGIN, MARGIN), (MARGIN, 75.0), (65.0, 95.0), (120.0, 80.0),
        (170.0, 102.0), (SIZE_MM - MARGIN, 88.0), (SIZE_MM - MARGIN, MARGIN)
    ]
    h2 = Polygon(hill_pts)
    layers.append(("Layer_02_Distant_Hills", base_frame(h2), "#453224"))

    # Layer 3: Sprawling Acacia Tree & Distant Giraffe
    # Acacia trunk on right side branching outwards
    trunk = Polygon([
        (145.0, MARGIN), (148.0, 70.0), (155.0, 105.0), (170.0, 128.0),
        (178.0, 126.0), (160.0, 100.0), (152.0, 68.0), (152.0, MARGIN)
    ])
    # Umbrella foliage canopies
    c1 = Point(165.0, 132.0).buffer(22.0).intersection(box(120, 122, 195, 142))
    c2 = Point(135.0, 124.0).buffer(18.0).intersection(box(100, 116, 160, 134))
    c3 = Point(110.0, 115.0).buffer(15.0).intersection(box(85, 108, 135, 123))

    # Distant giraffe silhouette left side
    g_body = Point(50.0, 72.0).buffer(7.0)
    g_neck = Polygon([(51.0, 76.0), (56.0, 112.0), (60.0, 110.0), (55.0, 74.0)])
    g_head = Point(58.0, 114.0).buffer(4.0)
    g_ears = Polygon([(57.0, 116.0), (56.0, 121.0), (60.0, 117.0)])
    g_leg1 = box(46.0, MARGIN, 48.5, 70.0)
    g_leg2 = box(52.0, MARGIN, 54.5, 70.0)
    giraffe = unary_union([g_body, g_neck, g_head, g_ears, g_leg1, g_leg2])

    ground3 = box(MARGIN, MARGIN, SIZE_MM - MARGIN, MARGIN + 42.0)
    l3_geom = unary_union([ground3, trunk, c1, c2, c3, giraffe])
    layers.append(("Layer_03_Acacia_Canopy_Giraffe", base_frame(l3_geom), "#694D36"))

    # Layer 4: Mama Elephant & Baby Calf Walking Trunk-in-Hand
    ground4 = Polygon([
        (MARGIN, MARGIN), (MARGIN, 46.0), (70.0, 52.0), (120.0, 44.0),
        (170.0, 48.0), (SIZE_MM - MARGIN, 44.0), (SIZE_MM - MARGIN, MARGIN)
    ])
    # Mama elephant
    e_body = Point(98.0, 72.0).buffer(16.0)
    e_head = Point(116.0, 78.0).buffer(11.0)
    e_trunk = Polygon([(122.0, 80.0), (134.0, 72.0), (130.0, 56.0), (126.0, 58.0), (129.0, 70.0), (119.0, 74.0)])
    e_ear = Point(112.0, 76.0).buffer(8.0)
    e_leg1 = box(87.0, MARGIN, 93.0, 68.0)
    e_leg2 = box(97.0, MARGIN, 103.0, 68.0)
    e_leg3 = box(107.0, MARGIN, 113.0, 68.0)
    mama_e = unary_union([e_body, e_head, e_trunk, e_ear, e_leg1, e_leg2, e_leg3])

    # Baby calf behind mama
    b_body = Point(68.0, 58.0).buffer(9.0)
    b_head = Point(78.0, 62.0).buffer(6.5)
    b_trunk = Polygon([(82.0, 64.0), (89.0, 58.0), (87.0, 52.0), (84.0, 54.0), (86.0, 58.0), (80.0, 60.0)])
    b_ear = Point(75.0, 62.0).buffer(5.0)
    b_leg1 = box(62.0, MARGIN, 66.0, 56.0)
    b_leg2 = box(70.0, MARGIN, 74.0, 56.0)
    baby_e = unary_union([b_body, b_head, b_trunk, b_ear, b_leg1, b_leg2])

    l4_geom = unary_union([ground4, mama_e, baby_e])
    layers.append(("Layer_04_Mama_And_Baby_Elephant", base_frame(l4_geom), "#8C6A4F"))

    # Layer 5: Foreground Savanna Tall Grass & Reeds
    reeds = []
    for x in np.linspace(MARGIN + 5, SIZE_MM - MARGIN - 5, 22):
        rh = 28.0 + (int(x * 7) % 20)
        bend = 4.0 if (int(x) % 2 == 0) else -4.0
        blade = Polygon([(x - 1.5, MARGIN), (x + bend, MARGIN + rh), (x + 1.5, MARGIN)])
        reeds.append(blade)
    fg_ground = box(MARGIN, MARGIN, SIZE_MM - MARGIN, MARGIN + 18.0)
    l5_geom = unary_union([fg_ground, *reeds])
    layers.append(("Layer_05_Foreground_Savanna_Grass", base_frame(l5_geom), "#B38E6D"))

    # Layer 6: Decorative Front Frame
    l6 = outer_frame()
    layers.append(("Layer_06_Front_Frame", l6, "#D4AF8B"))

    return layers


# -----------------------------------------------------------------------------
# SHADOW BOX THEME 3: DREAMY NURSERY HOT AIR BALLOON
# -----------------------------------------------------------------------------
def build_nursery_balloon_layers() -> List[Tuple[str, BaseGeometry, str]]:
    layers = []

    # Layer 1: Solid Back Panel with Sleeping Crescent Moon & Stars
    full_back = box(0, 0, SIZE_MM, SIZE_MM)
    c1 = Point(60.0, 145.0).buffer(22.0)
    c2 = Point(68.0, 149.0).buffer(21.0)
    moon = c1.difference(c2)
    stars = [
        O.star(5.0, rot=20), O.star(6.5, rot=40), O.star(4.0, rot=10),
        O.star(5.5, rot=30), O.star(4.5, rot=60), O.star(6.0, rot=15)
    ]
    spos = [(110.0, 165.0), (145.0, 155.0), (170.0, 140.0), (130.0, 125.0), (160.0, 175.0), (90.0, 140.0)]
    star_geoms = [affinity.translate(s, px, py) for s, (px, py) in zip(stars, spos)]
    l1 = full_back.difference(unary_union([moon, *star_geoms]))
    layers.append(("Layer_01_Back_Moon_And_Stars", l1, "#1E2749"))

    # Layer 2: High Billowing Cloud Bank with Hanging Star Ribbons
    # Fluffy cloud mounds across top and sides
    c_blobs = [
        Point(45.0, 120.0).buffer(26.0), Point(85.0, 115.0).buffer(30.0),
        Point(135.0, 110.0).buffer(28.0), Point(170.0, 118.0).buffer(25.0)
    ]
    clouds2 = unary_union(c_blobs).intersection(box(MARGIN, MARGIN, SIZE_MM - MARGIN, 128.0))
    g2 = unary_union([box(MARGIN, MARGIN, SIZE_MM - MARGIN, 80.0), clouds2])
    layers.append(("Layer_02_Billowing_Cloud_Bank", base_frame(g2), "#313D6A"))

    # Layer 3: Hot Air Balloon Envelope in Midground
    # Classic hot air balloon silhouette at (120, 125)
    b_top = Point(120.0, 138.0).buffer(22.0)
    b_cone = Polygon([(101.0, 134.0), (113.0, 108.0), (127.0, 108.0), (139.0, 134.0)])
    envelope = unary_union([b_top, b_cone])
    basket = box(116.0, 96.0, 124.0, 103.0)
    ropes = unary_union([
        box(115.0, 103.0, 116.5, 108.0),
        box(123.5, 103.0, 125.0, 108.0)
    ])
    balloon = unary_union([envelope, basket, ropes])

    # Left cloud ledge
    c_left = Point(40.0, 70.0).buffer(25.0).union(Point(75.0, 62.0).buffer(22.0))
    g3 = unary_union([box(MARGIN, MARGIN, SIZE_MM - MARGIN, 55.0), c_left, balloon])
    layers.append(("Layer_03_Hot_Air_Balloon_Envelope", base_frame(g3), "#49588E"))

    # Layer 4: Floating Clouds & Cute Sleeping Character in Basket
    c_mid = unary_union([
        Point(145.0, 65.0).buffer(26.0), Point(110.0, 58.0).buffer(22.0),
        Point(75.0, 54.0).buffer(20.0), Point(35.0, 58.0).buffer(24.0)
    ])
    g4 = unary_union([box(MARGIN, MARGIN, SIZE_MM - MARGIN, 45.0), c_mid])
    layers.append(("Layer_04_Floating_Clouds_Mid", base_frame(g4), "#6E7DAF"))

    # Layer 5: Foreground Soft Pillowy Clouds
    c_fg = unary_union([
        Point(50.0, 32.0).buffer(24.0), Point(95.0, 36.0).buffer(26.0),
        Point(145.0, 30.0).buffer(25.0), Point(180.0, 35.0).buffer(22.0)
    ])
    g5 = unary_union([box(MARGIN, MARGIN, SIZE_MM - MARGIN, 24.0), c_fg])
    layers.append(("Layer_05_Foreground_Puffy_Clouds", base_frame(g5), "#9AA7D1"))

    # Layer 6: Decorative Front Frame
    l6 = outer_frame()
    layers.append(("Layer_06_Front_Frame", l6, "#C5CEE8"))

    return layers


# -----------------------------------------------------------------------------
# SHADOW BOX THEME 4: UNDER THE SEA & GENTLE WHALES
# -----------------------------------------------------------------------------
def build_ocean_dreams_layers() -> List[Tuple[str, BaseGeometry, str]]:
    layers = []

    # Layer 1: Solid Back Panel with Surface Sunbeams & Distant Fish Silhouettes
    full_back = box(0, 0, SIZE_MM, SIZE_MM)
    beams = [
        Polygon([(50.0, SIZE_MM), (70.0, SIZE_MM), (85.0, 110.0), (75.0, 110.0)]),
        Polygon([(100.0, SIZE_MM), (125.0, SIZE_MM), (135.0, 105.0), (120.0, 105.0)]),
        Polygon([(155.0, SIZE_MM), (172.0, SIZE_MM), (180.0, 115.0), (170.0, 115.0)]),
    ]
    # Small fish
    fish = [
        Point(45.0, 150.0).buffer(3.5).union(Polygon([(45.0, 150.0), (37.0, 154.0), (37.0, 146.0)])),
        Point(58.0, 158.0).buffer(3.0).union(Polygon([(58.0, 158.0), (51.0, 161.0), (51.0, 155.0)])),
        Point(145.0, 142.0).buffer(4.0).union(Polygon([(145.0, 142.0), (136.0, 146.0), (136.0, 138.0)])),
    ]
    l1 = full_back.difference(unary_union([*beams, *fish]))
    layers.append(("Layer_01_Back_Sunbeams_Fish", l1, "#0A192F"))

    # Layer 2: Deep Sea Arch & Swimming Sea Turtle
    # Distant reef arch
    arch_base = Polygon([
        (MARGIN, MARGIN), (MARGIN, 110.0), (55.0, 125.0), (85.0, 95.0),
        (135.0, 85.0), (SIZE_MM - MARGIN, 98.0), (SIZE_MM - MARGIN, MARGIN)
    ])
    # Turtle silhouette top left
    t_shell = Point(65.0, 135.0).buffer(9.0)
    t_head = Point(53.0, 137.0).buffer(4.0)
    t_flipper1 = Polygon([(62.0, 142.0), (52.0, 155.0), (66.0, 146.0)])
    t_flipper2 = Polygon([(68.0, 128.0), (60.0, 118.0), (72.0, 126.0)])
    turtle = unary_union([t_shell, t_head, t_flipper1, t_flipper2])
    l2_geom = unary_union([arch_base, turtle])
    layers.append(("Layer_02_Deep_Reef_Turtle", base_frame(l2_geom), "#11324D"))

    # Layer 3: Gentle Mother Humpback Whale
    # Whale body swimming toward right
    w_body = Point(105.0, 95.0).buffer(18.0)
    w_head = Point(128.0, 92.0).buffer(14.0)
    w_snout = Polygon([(135.0, 98.0), (148.0, 88.0), (135.0, 84.0)])
    w_tail_cone = Polygon([(95.0, 102.0), (60.0, 108.0), (62.0, 100.0), (95.0, 88.0)])
    w_fluke = Polygon([(60.0, 104.0), (45.0, 118.0), (50.0, 104.0), (45.0, 90.0)])
    w_flipper = Polygon([(112.0, 86.0), (105.0, 62.0), (116.0, 66.0), (120.0, 84.0)])
    mama_whale = unary_union([w_body, w_head, w_snout, w_tail_cone, w_fluke, w_flipper])

    reef_left = Polygon([(MARGIN, MARGIN), (MARGIN, 85.0), (45.0, 80.0), (60.0, MARGIN)])
    reef_right = Polygon([(145.0, MARGIN), (160.0, 68.0), (SIZE_MM - MARGIN, 74.0), (SIZE_MM - MARGIN, MARGIN)])
    l3_geom = unary_union([mama_whale, reef_left, reef_right, box(MARGIN, MARGIN, SIZE_MM - MARGIN, MARGIN + 25.0)])
    layers.append(("Layer_03_Mother_Humpback_Whale", base_frame(l3_geom), "#1D5C6F"))

    # Layer 4: Baby Whale Calf & Rising Air Bubbles
    # Baby whale swimming above mama
    c_body = Point(82.0, 122.0).buffer(10.0)
    c_head = Point(94.0, 120.0).buffer(8.0)
    c_snout = Polygon([(98.0, 123.0), (106.0, 118.0), (98.0, 115.0)])
    c_tail = Polygon([(76.0, 126.0), (56.0, 130.0), (58.0, 124.0), (76.0, 118.0)])
    c_fluke = Polygon([(56.0, 127.0), (46.0, 136.0), (50.0, 127.0), (46.0, 118.0)])
    c_flipper = Polygon([(86.0, 116.0), (81.0, 102.0), (88.0, 104.0), (90.0, 115.0)])
    baby_whale = unary_union([c_body, c_head, c_snout, c_tail, c_fluke, c_flipper])

    # Rising air bubbles
    bubbles = [
        Point(108.0, 128.0).buffer(3.0), Point(115.0, 138.0).buffer(2.2),
        Point(111.0, 148.0).buffer(1.8), Point(122.0, 155.0).buffer(2.5)
    ]
    ground4 = Polygon([
        (MARGIN, MARGIN), (MARGIN, 44.0), (60.0, 48.0), (110.0, 38.0),
        (160.0, 46.0), (SIZE_MM - MARGIN, 42.0), (SIZE_MM - MARGIN, MARGIN)
    ])
    l4_geom = unary_union([ground4, baby_whale, *bubbles])
    layers.append(("Layer_04_Baby_Whale_And_Bubbles", base_frame(l4_geom), "#3C8899"))

    # Layer 5: Foreground Coral Reef, Kelp & Starfish
    # Kelp stalks rising left and right using smooth buffered lines
    from shapely.geometry import LineString
    kelp = []
    for x in [MARGIN + 10, MARGIN + 22, SIZE_MM - MARGIN - 20, SIZE_MM - MARGIN - 10]:
        k_line = LineString([(x, MARGIN), (x + 4.0, 45.0), (x - 4.0, 80.0), (x + 2.0, 115.0)])
        kelp.append(k_line.buffer(2.2, cap_style=1))
    # Foreground rolling sea bed
    bed = box(MARGIN, MARGIN, SIZE_MM - MARGIN, MARGIN + 28.0)
    # Starfish on sea bed
    starfish = O.star(7.5, points=5, inner=0.55).buffer(0.4)
    starfish = affinity.translate(starfish, 95.0, 32.0)
    l5_geom = unary_union([bed, *kelp, starfish])
    layers.append(("Layer_05_Foreground_Coral_Kelp", base_frame(l5_geom), "#66B2B2"))

    # Layer 6: Decorative Front Frame
    l6 = outer_frame()
    layers.append(("Layer_06_Front_Frame", l6, "#A7D7C5"))

    return layers


THEMES = [
    {
        "id": "woodland_deer",
        "title": "Woodland Deer & Moonlit Forest",
        "folder": "01_Woodland_Deer_Forest",
        "builder": build_woodland_deer_layers,
    },
    {
        "id": "moonlit_safari",
        "title": "Moonlit Safari & Gentle Giants",
        "folder": "02_Moonlit_Safari_Giants",
        "builder": build_moonlit_safari_layers,
    },
    {
        "id": "nursery_balloon",
        "title": "Dreamy Nursery Hot Air Balloon",
        "folder": "03_Dreamy_Hot_Air_Balloon",
        "builder": build_nursery_balloon_layers,
    },
    {
        "id": "ocean_dreams",
        "title": "Under the Sea & Gentle Whales",
        "folder": "04_Ocean_Whales_Coral_Reef",
        "builder": build_ocean_dreams_layers,
    },
]
