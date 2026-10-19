"""Listing photo scenes for the cookie-cutter pack. Every scene renders the ACTUAL STL files being sold.

Style: saturated glossy PLA colours on vivid spot-lit backdrops (marketplace look). Final grading is done in kit.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

RED, GREEN, WHITE, GOLD = [0.85, 0.03, 0.05], [0.02, 0.50, 0.12], [0.92, 0.92, 0.90], [1.0, 0.55, 0.02]
PALETTE = [RED, GREEN, WHITE, GOLD]

BLUE_SPOT = {"inner": [0.06, 0.16, 0.62], "outer": [0.0, 0.01, 0.10], "radius": 0.20}
TEAL_SPOT = {"inner": [0.0, 0.62, 0.62], "outer": [0.0, 0.07, 0.12], "radius": 0.07}
PURPLE_SPOT = {"inner": [0.50, 0.10, 0.70], "outer": [0.05, 0.0, 0.12], "radius": 0.07}
WARM_SPOT = {"inner": [0.95, 0.45, 0.10], "outer": [0.25, 0.02, 0.0], "radius": 0.07}


def _stl(stl_dir: Path, idx: int, kind: str, size: int) -> str:
    pat = f"{idx:02d}_*_{kind}_{size}mm.stl"
    return str(next(iter(sorted(stl_dir.glob(pat)))))


def cover_grid(stl_dir: Path, out: Path) -> Dict:
    """Dense 6 x 6 full-frame checkerboard collage of real cutters: 80 mm on one colour of the board, 60 mm on the other."""
    objs = []
    k = 0
    n = 6
    for row in range(n):
        for col in range(n):
            idx = (k * 7 + row) % 10 + 1
            size = 80 if (row + col) % 2 == 0 else 60
            objs.append({"stl": _stl(stl_dir, idx, "Cutter", size), "loc": [(col - (n - 1) / 2) * 90, ((n - 1) / 2 - row) * 90, 0],
                         "color": PALETTE[(k * 3 + row * 2) % 4], "rot_z": (k * 37) % 50 - 25})
            k += 1
    return {"out": str(out), "res": [2000, 2000], "ground_spot": BLUE_SPOT, "objects": objs,
            "camera": {"target": [0, 0, 0], "distance": 790, "elevation": 84, "azimuth": 0, "lens": 50}}


def hero_trio(stl_dir: Path, out: Path, picks=(4, 2, 5)) -> Dict:
    """Three cutters staged on a vivid spot backdrop with shallow depth of field."""
    locs = [(-100, 4, 0), (4, 22, 0), (106, 0, 0)]
    objs = [{"stl": _stl(stl_dir, i, "Cutter", 80), "loc": list(l), "color": PALETTE[n % 4], "rot_z": [-12, 8, 14][n]}
            for n, (i, l) in enumerate(zip(picks, locs))]
    return {"out": str(out), "res": [2000, 2000], "ground_spot": WARM_SPOT, "objects": objs,
            "camera": {"target": [4, 6, 6], "distance": 500, "elevation": 40, "azimuth": 10, "lens": 85, "dof": 5.0}}


def closeup(stl_dir: Path, out: Path, idx: int, color, size: int = 80, azimuth: float = 25, elevation: float = 38,
            spot=None) -> Dict:
    return {"out": str(out), "res": [2000, 2000], "ground_spot": spot or TEAL_SPOT,
            "objects": [{"stl": _stl(stl_dir, idx, "Cutter", size), "loc": [0, 0, 0], "color": color, "rot_z": 0}],
            "camera": {"target": [0, 0, 5], "distance": 290, "elevation": elevation, "azimuth": azimuth, "lens": 85, "dof": 5.0}}


def cutter_and_press(stl_dir: Path, out: Path, idx: int = 4) -> Dict:
    """Cutter beside its matching press plate - shows the pair that is included."""
    return {"out": str(out), "res": [2000, 2000], "ground_spot": PURPLE_SPOT,
            "objects": [
                {"stl": _stl(stl_dir, idx, "Cutter", 80), "loc": [-58, 0, 0], "color": RED, "rot_z": -10},
                {"stl": _stl(stl_dir, idx, "Press_Plate", 80), "loc": [58, 0, 0], "color": GOLD, "rot_z": 12},
            ],
            "camera": {"target": [0, 0, 6], "distance": 430, "elevation": 44, "azimuth": 0, "lens": 75, "dof": 6.0}}


def size_pair(stl_dir: Path, out: Path, idx: int = 1) -> Dict:
    """Both included sizes of one design side by side."""
    return {"out": str(out), "res": [2000, 2000], "ground_spot": TEAL_SPOT,
            "objects": [
                {"stl": _stl(stl_dir, idx, "Cutter", 80), "loc": [-52, 0, 0], "color": GREEN, "rot_z": 0},
                {"stl": _stl(stl_dir, idx, "Cutter", 60), "loc": [58, -6, 0], "color": GOLD, "rot_z": 0},
            ],
            "camera": {"target": [4, 0, 5], "distance": 470, "elevation": 50, "azimuth": 0, "lens": 75, "dof": 7.0}}


def all_scenes(stl_dir: Path, img_dir: Path) -> List[Dict]:
    """Transparent renders (composited onto ComfyUI backdrops by the pilot). Elevations suit top-down flat-lay backdrops."""
    img_dir.mkdir(parents=True, exist_ok=True)
    scenes = [
        cover_grid(stl_dir, img_dir / "_raw_cover_grid.png"),
        hero_trio(stl_dir, img_dir / "_raw_hero_trio.png"),
        closeup(stl_dir, img_dir / "_raw_closeup_gingerbread.png", 4, RED, elevation=60),
        closeup(stl_dir, img_dir / "_raw_closeup_snowflake.png", 3, WHITE, azimuth=-20, elevation=62),
        closeup(stl_dir, img_dir / "_raw_closeup_tree.png", 1, GREEN, azimuth=18, elevation=58),
        cutter_and_press(stl_dir, img_dir / "_raw_cutter_and_press.png"),
        size_pair(stl_dir, img_dir / "_raw_two_sizes.png"),
    ]
    for s in scenes:
        s["transparent"] = True
    # the hero is staged low (3/4 view) for the 'table' backdrop
    scenes[1]["camera"]["elevation"] = 26
    return scenes