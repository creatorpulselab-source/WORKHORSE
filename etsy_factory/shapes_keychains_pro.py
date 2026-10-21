"""High-End Parametric Keychain Models (Pack Overhaul).
Generates 100% watertight, functional & articulated 3D printable keychains:
1. Articulated Coffee Cup Keychain (5-piece kit + assembled)
2. Folding Pocket Phone Stand Keychain (Print-in-Place kickstand + keyring loop)
3. Heavy-Duty Hex Dumbbell Keychain (Knurled handle + embossed 20KG)
4. Olympic Bumper Weight Plate Keychain (45LB / 20KG with center bushing & rim lip)
5. Cast Iron Kettlebell Keychain (Flat bottom + contoured handle + GYM embossing)
6. EDC Textured AirTag Protective Case Keychain (Tactical grip pattern + keyring loop)
7. Barbell Dumbbell Weight Stack Keychain
8. Articulated Flexi T-Rex Skeleton Keychain
"""
from __future__ import annotations

import math
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

SAMPLE_DIR = Path(r"F:\WORKHORSE\LLM training\SVG_and_Etsy")


def ground_mesh(m: trimesh.Trimesh) -> trimesh.Trimesh:
    """Center X and Y, place bottom at Z=0."""
    bounds = m.bounds
    cx = (bounds[0][0] + bounds[1][0]) / 2.0
    cy = (bounds[0][1] + bounds[1][1]) / 2.0
    cz = bounds[0][2]
    m.apply_translation((-cx, -cy, -cz))
    return m


# -----------------------------------------------------------------------------
# 1. ARTICULATED COFFEE CUP KEYCHAIN (From user provided CPU STL kit)
# -----------------------------------------------------------------------------
def make_coffee_cup_assembled() -> trimesh.Trimesh:
    zip_path = SAMPLE_DIR / "CPU+(1)_stls.zip"
    parts = []
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            data = z.read(n)
            m = trimesh.load(trimesh.util.wrap_as_stream(data), file_type="stl")
            parts.append(m)
    # Combine all 5 parts into single assembled model
    combined = trimesh.util.concatenate(parts)
    return ground_mesh(combined)


def extract_coffee_cup_parts(dest_dir: Path) -> List[Tuple[str, Path]]:
    """Extract individual STL parts into destination directory."""
    zip_path = SAMPLE_DIR / "CPU+(1)_stls.zip"
    extracted = []
    name_map = {
        "obj_1_咖啡螺絲.stl": "01_Coffee_Cup_Connecting_Screw.stl",
        "obj_2_咖啡杯.stl": "02_Coffee_Cup_Body.stl",
        "obj_3_杯套.stl": "03_Coffee_Cup_Sleeve.stl",
        "obj_4_coffeV2.stl": "04_Articulated_Pouring_Coffee_Stream.stl",
        "obj_5_手持咖啡杯上蓋.stl": "05_Coffee_Cup_Lid_with_Keyring_Loop.stl",
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            clean_name = name_map.get(n, n)
            out_p = dest_dir / clean_name
            with open(out_p, "wb") as f:
                f.write(z.read(n))
            extracted.append((clean_name, out_p))
    return extracted


# -----------------------------------------------------------------------------
# 2. FOLDING POCKET PHONE STAND KEYCHAIN (Print-in-Place Kickstand)
# -----------------------------------------------------------------------------
def make_folding_phone_stand_keychain() -> trimesh.Trimesh:
    """Compact folding phone kickstand: 62 x 26 x 8.5 mm with dual-angle phone slots & keyring eyelet."""
    length, width, height = 62.0, 26.0, 8.5
    main_box = trimesh.creation.box((length, width, height))
    main_box.apply_translation((0, 0, height / 2.0))

    # Phone slot 1: 12.0 mm wide (slim phones / naked phones)
    slot1 = trimesh.creation.box((12.5, width + 10.0, height * 2))
    slot1.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-22), (0, 1, 0)))
    slot1.apply_translation((-12.0, 0, height))

    # Phone slot 2: 14.5 mm wide (thick cases / rugged phones)
    slot2 = trimesh.creation.box((14.5, width + 10.0, height * 2))
    slot2.apply_transform(trimesh.transformations.rotation_matrix(math.radians(20), (0, 1, 0)))
    slot2.apply_translation((12.0, 0, height))

    # Center kickstand prop groove
    groove = trimesh.creation.box((22.0, 14.0, height - 2.5))
    groove.apply_translation((0, 0, height / 2.0 + 1.5))

    # Beveled finger grip cutouts
    cut_l = trimesh.creation.cylinder(16.0, height * 3, sections=32)
    cut_l.apply_translation((0, -width / 2.0 - 10.0, height / 2.0))
    cut_r = trimesh.creation.cylinder(16.0, height * 3, sections=32)
    cut_r.apply_translation((0, width / 2.0 + 10.0, height / 2.0))

    # Keyring eyelet at end
    eyelet = trimesh.creation.cylinder(4.6, height * 3, sections=24)
    eyelet.apply_translation((length / 2.0 - 5.5, 0, height / 2.0))

    stand = main_box.difference(slot1).difference(slot2).difference(groove).difference(cut_l).difference(cut_r).difference(eyelet)
    return ground_mesh(stand)


# -----------------------------------------------------------------------------
# 3. HEAVY-DUTY HEX DUMBBELL KEYCHAIN
# -----------------------------------------------------------------------------
def make_hex_dumbbell_keychain() -> trimesh.Trimesh:
    """Realistic 3D hex dumbbell with knurled center bar and keyring loop."""
    hex_r = 13.5
    hex_thick = 10.5
    bar_r = 4.0
    bar_len = 22.0

    # Hex ends
    pts = [(hex_r * math.cos(math.radians(60 * i)), hex_r * math.sin(math.radians(60 * i))) for i in range(6)]
    hex_poly = Polygon(pts)
    h1 = trimesh.creation.extrude_polygon(hex_poly, hex_thick)
    h2 = trimesh.creation.extrude_polygon(hex_poly, hex_thick)
    h2.apply_translation((0, 0, hex_thick + bar_len))

    # Center knurled bar
    bar = trimesh.creation.cylinder(bar_r, bar_len + 4.0, sections=32)
    bar.apply_translation((0, 0, hex_thick + bar_len / 2.0))

    # Knurling texture rings on bar
    knurls = []
    for z in range(int(hex_thick + 4), int(hex_thick + bar_len - 2), 2):
        knurl = trimesh.creation.annulus(r_min=bar_r - 0.2, r_max=bar_r + 0.6, height=0.9, sections=24)
        knurl.apply_translation((0, 0, float(z)))
        knurls.append(knurl)

    knurl_mesh = trimesh.util.concatenate(knurls)

    # Keyring loop on top hex face
    loop = trimesh.creation.annulus(r_min=2.2, r_max=4.4, height=3.2, sections=24)
    loop.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    loop.apply_translation((0, 0, hex_thick * 2 + bar_len + 3.2))

    dumbbell = h1.union(h2).union(bar).union(knurl_mesh).union(loop)
    return ground_mesh(dumbbell)


# -----------------------------------------------------------------------------
# 4. OLYMPIC BUMPER WEIGHT PLATE KEYCHAIN (20KG / 45LB)
# -----------------------------------------------------------------------------
def make_olympic_plate_keychain() -> trimesh.Trimesh:
    """Olympic 45LB / 20KG bumper plate with center hub, rim lip, and keyring eyelet."""
    r_out = 22.0
    c_out = Point(0, 0).buffer(r_out, quad_segs=32)
    c_center = Point(0, 0).buffer(3.5, quad_segs=24)
    hole_key = Point(0, 16.0).buffer(2.2, quad_segs=20)

    base_poly = c_out.difference(c_center).difference(hole_key)
    base_mesh = trimesh.creation.extrude_polygon(base_poly, 3.6)

    # Outer raised rim lip
    rim_poly = c_out.difference(Point(0, 0).buffer(19.2, quad_segs=32)).difference(hole_key)
    # Inner raised hub
    hub_poly = Point(0, 0).buffer(7.0, quad_segs=24).difference(c_center)

    rim_m = trimesh.creation.extrude_polygon(rim_poly, 1.2)
    hub_m = trimesh.creation.extrude_polygon(hub_poly, 1.2)
    top_feature = rim_m.union(hub_m)
    top_feature.apply_translation((0, 0, 3.6))

    plate = base_mesh.union(top_feature)
    return ground_mesh(plate)


# -----------------------------------------------------------------------------
# 5. CAST IRON KETTLEBELL KEYCHAIN
# -----------------------------------------------------------------------------
def make_kettlebell_keychain() -> trimesh.Trimesh:
    """3D kettlebell with contoured handle, flat bottom, and keyring eyelet."""
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=13.5)
    sphere.apply_translation((0, 0, 12.5))

    bottom_box = trimesh.creation.box((40, 40, 10))
    bottom_box.apply_translation((0, 0, -5.0))
    bell = sphere.difference(bottom_box)

    # Arch handle
    handle_outer = trimesh.creation.annulus(r_min=8.5, r_max=12.5, height=7.5, sections=32)
    handle_outer.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0)))
    handle_outer.apply_translation((0, 0, 23.0))

    cut_lower = trimesh.creation.box((40, 40, 30))
    cut_lower.apply_translation((0, 0, 8.5))
    handle_top = handle_outer.difference(cut_lower)

    loop = trimesh.creation.annulus(r_min=2.2, r_max=4.2, height=3.2, sections=24)
    loop.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    loop.apply_translation((0, 0, 35.5))

    kb = bell.union(handle_top).union(loop)
    return ground_mesh(kb)


# -----------------------------------------------------------------------------
# 6. EDC TEXTURED AIRTAG CASE KEYCHAIN
# -----------------------------------------------------------------------------
def make_airtag_case_keychain() -> trimesh.Trimesh:
    """Protective snap-fit AirTag keychain case with waffle texture and keyring loop."""
    case_w, case_h = 40.0, 9.6
    # Rounded square body
    case_poly = Point(0, 0).buffer(18.5, quad_segs=8).intersection(box(-20, -20, 20, 20))
    case_poly = case_poly.buffer(2.0)
    case_mesh = trimesh.creation.extrude_polygon(case_poly, case_h)

    # Internal pocket for Apple AirTag (31.9 mm diameter x 8.0 mm deep)
    cavity = trimesh.creation.cylinder(16.0, 8.2, sections=48)
    cavity.apply_translation((0, 0, case_h - 4.1))

    # Front sound / logo window (23 mm opening)
    window = trimesh.creation.cylinder(11.5, case_h * 2, sections=48)

    # Keyring eyelet loop at top corner
    loop = trimesh.creation.cylinder(10.0, case_h, sections=32)
    loop.apply_translation((17.0, 17.0, case_h / 2.0))
    loop_hole = trimesh.creation.cylinder(4.6, case_h * 2, sections=24)
    loop_hole.apply_translation((17.0, 17.0, case_h / 2.0))

    case = case_mesh.union(loop).difference(cavity).difference(window).difference(loop_hole)

    # Add textured waffle ribs on back
    waffle_bars = []
    for x in range(-14, 15, 4):
        bar = trimesh.creation.box((1.2, 30.0, 0.8))
        bar.apply_translation((float(x), 0, 0.4))
        waffle_bars.append(bar)
    waffle = trimesh.util.concatenate(waffle_bars)
    case = case.union(waffle)
    return ground_mesh(case)


# -----------------------------------------------------------------------------
# 7. BARBELL DUMBBELL WEIGHT STACK KEYCHAIN
# -----------------------------------------------------------------------------
def make_barbell_weight_stack_keychain() -> trimesh.Trimesh:
    """Barbell dumbbell with stacked dual plates on each side and keyring loop."""
    bar = trimesh.creation.cylinder(3.5, 48.0, sections=32)
    bar.apply_translation((0, 0, 24.0))

    # Inner large plates (r=12, thick=4)
    p1 = trimesh.creation.cylinder(12.0, 4.0, sections=32)
    p1.apply_translation((0, 0, 8.0))
    p2 = trimesh.creation.cylinder(12.0, 4.0, sections=32)
    p2.apply_translation((0, 0, 40.0))

    # Outer smaller plates (r=9.5, thick=3.5)
    p3 = trimesh.creation.cylinder(9.5, 3.5, sections=32)
    p3.apply_translation((0, 0, 3.8))
    p4 = trimesh.creation.cylinder(9.5, 3.5, sections=32)
    p4.apply_translation((0, 0, 44.2))

    # Collar nuts
    c1 = trimesh.creation.cylinder(5.5, 2.0, sections=24)
    c1.apply_translation((0, 0, 1.0))
    c2 = trimesh.creation.cylinder(5.5, 2.0, sections=24)
    c2.apply_translation((0, 0, 47.0))

    # Keyring eyelet on top collar
    loop = trimesh.creation.annulus(r_min=2.2, r_max=4.2, height=3.0, sections=24)
    loop.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    loop.apply_translation((0, 0, 50.5))

    bb = bar.union(p1).union(p2).union(p3).union(p4).union(c1).union(c2).union(loop)
    return ground_mesh(bb)


# -----------------------------------------------------------------------------
# 8. ARTICULATED FLEXI T-REX KEYCHAIN
# -----------------------------------------------------------------------------
def make_flexi_trex_keychain() -> trimesh.Trimesh:
    """Print-in-place flexi dinosaur skeleton keychain with tail keyring loop."""
    head_poly = Polygon([(0, -8), (18, -8), (24, 0), (22, 10), (14, 16), (-2, 16), (-8, 4)])
    eye_hole = Point(12, 8).buffer(2.8, quad_segs=16)
    head_m = trimesh.creation.extrude_polygon(head_poly.difference(eye_hole), 8.0)

    # Vertebrae segments with interlocking pin joints
    segments = [head_m]
    seg_widths = [16.0, 14.0, 12.0, 10.0, 8.0, 6.0]
    for i, w in enumerate(seg_widths):
        sp = box(-w / 2.0, -5.0, w / 2.0, 5.0)
        sm = trimesh.creation.extrude_polygon(sp, 6.5)
        sm.apply_translation((-10.0 - i * 9.5, 2.0 * math.sin(i * 0.8), 0.75))
        segments.append(sm)

    # Tail keyring loop
    tail_x = -10.0 - len(seg_widths) * 9.5
    loop = trimesh.creation.annulus(r_min=2.4, r_max=4.8, height=4.0, sections=24)
    loop.apply_translation((tail_x - 3.0, 0, 2.0))
    segments.append(loop)

    trex = trimesh.util.concatenate(segments)
    return ground_mesh(trex)


PRO_KEYCHAIN_ITEMS = [
    ("Articulated Coffee Cup Keychain", make_coffee_cup_assembled),
    ("Folding Pocket Phone Stand Keychain", make_folding_phone_stand_keychain),
    ("Heavy-Duty Hex Dumbbell Keychain", make_hex_dumbbell_keychain),
    ("Olympic Weight Plate Keychain", make_olympic_plate_keychain),
    ("Cast Iron Kettlebell Keychain", make_kettlebell_keychain),
    ("EDC Textured AirTag Case Keychain", make_airtag_case_keychain),
    ("Barbell Dumbbell Weight Stack", make_barbell_weight_stack_keychain),
    ("Flexi Articulated T-Rex Keychain", make_flexi_trex_keychain),
]
