"""Listing photo scenes for the cookie-cutter pack. Every scene renders the ACTUAL STL files being sold."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

RED, GREEN, WHITE = [0.55, 0.03, 0.06], [0.03, 0.30, 0.13], [0.80, 0.79, 0.75]
PALETTE = [RED, GREEN, WHITE]


def _stl(stl_dir: Path, idx: int, kind: str, size: int) -> str:
    pat = f"{idx:02d}_*_{kind}_{size}mm.stl"
    return str(next(iter(sorted(stl_dir.glob(pat)))))


def cover_grid(stl_dir: Path, out: Path) -> Dict:
    """5 x 2 flat-lay of all ten 80 mm cutters on a wooden table (title/badges are added by PIL around it)."""
    objs = []
    for i in range(10):
        col, row = i % 5, i // 5
        objs.append({"stl": _stl(stl_dir, i + 1, "Cutter", 80), "loc": [(col - 2) * 100, (0.5 - row) * 106, 0],
                     "color": PALETTE[i % 3], "rot_z": 0})
    return {"out": str(out), "res": [2000, 2000], "ground": "slate", "objects": objs,
            "camera": {"target": [0, 60, 0], "distance": 790, "elevation": 82, "azimuth": 0, "lens": 50}}


def hero_trio(stl_dir: Path, out: Path, picks=(4, 2, 5)) -> Dict:
    """Three cutters staged at an angle on a muted blush surface with shallow depth of field."""
    locs = [(-96, -2, 0), (2, 14, 0), (100, -6, 0)]
    objs = [{"stl": _stl(stl_dir, i, "Cutter", 80), "loc": list(l), "color": PALETTE[n % 3], "rot_z": [-18, 8, 20][n]}
            for n, (i, l) in enumerate(zip(picks, locs))]
    return {"out": str(out), "res": [2000, 2000], "ground": "blush", "objects": objs,
            "camera": {"target": [0, 0, 6], "distance": 660, "elevation": 34, "azimuth": 14, "lens": 85, "dof": 4.5}}


def closeup(stl_dir: Path, out: Path, idx: int, color, size: int = 80, azimuth: float = 25, elevation: float = 38,
            ground: str = "cream") -> Dict:
    return {"out": str(out), "res": [2000, 2000], "ground": ground,
            "objects": [{"stl": _stl(stl_dir, idx, "Cutter", size), "loc": [0, 0, 0], "color": color, "rot_z": 0}],
            "camera": {"target": [0, 0, 5], "distance": 290, "elevation": elevation, "azimuth": azimuth, "lens": 85, "dof": 5.0}}


def cutter_and_press(stl_dir: Path, out: Path, idx: int = 4) -> Dict:
    """Cutter beside its matching press plate - shows the pair that is included."""
    return {"out": str(out), "res": [2000, 2000], "ground": "slate",
            "objects": [
                {"stl": _stl(stl_dir, idx, "Cutter", 80), "loc": [-62, 0, 0], "color": RED, "rot_z": -10},
                {"stl": _stl(stl_dir, idx, "Press_Plate", 80), "loc": [62, 0, 0], "color": WHITE, "rot_z": 12},
            ],
            "camera": {"target": [0, 0, 6], "distance": 430, "elevation": 42, "azimuth": 0, "lens": 75, "dof": 6.0}}


def size_pair(stl_dir: Path, out: Path, idx: int = 1) -> Dict:
    """Both included sizes of one design side by side."""
    return {"out": str(out), "res": [2000, 2000], "ground": "sage",
            "objects": [
                {"stl": _stl(stl_dir, idx, "Cutter", 80), "loc": [-52, 0, 0], "color": WHITE, "rot_z": 0},
                {"stl": _stl(stl_dir, idx, "Cutter", 60), "loc": [58, -6, 0], "color": RED, "rot_z": 0},
            ],
            "camera": {"target": [4, 0, 5], "distance": 520, "elevation": 48, "azimuth": 0, "lens": 75, "dof": 7.0}}


def all_scenes(stl_dir: Path, img_dir: Path) -> List[Dict]:
    img_dir.mkdir(parents=True, exist_ok=True)
    return [
        cover_grid(stl_dir, img_dir / "_raw_cover_grid.png"),
        hero_trio(stl_dir, img_dir / "_raw_hero_trio.png"),
        closeup(stl_dir, img_dir / "_raw_closeup_gingerbread.png", 4, RED, ground="sage"),
        closeup(stl_dir, img_dir / "_raw_closeup_snowflake.png", 3, WHITE, azimuth=-20, elevation=44, ground="slate"),
        closeup(stl_dir, img_dir / "_raw_closeup_tree.png", 1, GREEN, azimuth=18),
        cutter_and_press(stl_dir, img_dir / "_raw_cutter_and_press.png"),
        size_pair(stl_dir, img_dir / "_raw_two_sizes.png"),
    ]
