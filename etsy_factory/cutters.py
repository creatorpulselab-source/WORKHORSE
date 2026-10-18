"""Parametric cookie-cutter + press-plate geometry. Every mesh is validated (watertight, positive volume) as it is built."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon

# Printability constants (0.4 mm nozzle): 1.2 mm = 3 perimeters, 0.8 mm = 2 perimeters
WALL_MM = 1.2
EDGE_MM = 0.8            # thin cutting edge on the top 3 mm
EDGE_HEIGHT_MM = 3.0
TOTAL_HEIGHT_MM = 14.0
FLANGE_WIDTH_MM = 5.0    # outward grip flange so thumbs don't press on a thin wall
FLANGE_HEIGHT_MM = 2.4
PRESS_CLEARANCE_MM = 0.35
PRESS_THICKNESS_MM = 3.0


def _polys(g) -> List[Polygon]:
    if g.is_empty:
        return []
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]


def _extrude(g, height: float, z0: float = 0.0) -> List[trimesh.Trimesh]:
    out = []
    for p in _polys(g):
        if p.area < 0.5:
            continue
        m = trimesh.creation.extrude_polygon(p, height)
        m.apply_translation((0, 0, z0))
        out.append(m)
    return out


def _union(meshes: List[trimesh.Trimesh]) -> trimesh.Trimesh:
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def build_cutter(outline: Polygon) -> trimesh.Trimesh:
    """Hollow wall + thin cutting edge + outward grip flange, flat on the bed (no supports needed)."""
    w = WALL_MM / 2
    wall = outline.buffer(w, join_style=1).difference(outline.buffer(-w, join_style=1))
    edge = outline.buffer(EDGE_MM / 2, join_style=1).difference(outline.buffer(-EDGE_MM / 2, join_style=1))
    flange = outline.buffer(w + FLANGE_WIDTH_MM, join_style=1).difference(outline.buffer(-w, join_style=1))
    parts = (
        _extrude(flange, FLANGE_HEIGHT_MM)
        + _extrude(wall, TOTAL_HEIGHT_MM - EDGE_HEIGHT_MM)
        + _extrude(edge, EDGE_HEIGHT_MM, z0=TOTAL_HEIGHT_MM - EDGE_HEIGHT_MM)
    )
    return _union(parts)


def build_press(outline: Polygon) -> trimesh.Trimesh:
    """Press plate that fits INSIDE the cutter (clears the wall) with a round knob - pushes dough out cleanly."""
    inner = outline.buffer(-(WALL_MM / 2) - PRESS_CLEARANCE_MM, join_style=1)
    if inner.is_empty:
        raise ValueError("outline too small for a press plate")
    inner = max(_polys(inner), key=lambda p: p.area)
    plate = _extrude(inner, PRESS_THICKNESS_MM)
    # knob sits at the most 'inside' point of the shape
    c = inner.representative_point()
    inradius = inner.exterior.distance(c)
    r = float(np.clip(inradius * 0.55, 3.0, 9.0))
    knob = trimesh.creation.cylinder(radius=r, height=11.0, sections=48)
    knob.apply_translation((c.x, c.y, PRESS_THICKNESS_MM + 5.5 - 0.2))
    return _union(plate + [knob])


def validate(mesh: trimesh.Trimesh) -> Dict[str, object]:
    return {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "volume_mm3": round(float(mesh.volume), 1),
        "faces": int(len(mesh.faces)),
        "size_mm": [round(float(x), 1) for x in mesh.extents],
    }


def assert_printable(name: str, mesh: trimesh.Trimesh) -> Dict[str, object]:
    v = validate(mesh)
    if not (v["watertight"] and v["winding_consistent"] and v["volume_mm3"] > 0):
        raise RuntimeError(f"{name} failed printability validation: {v}")
    return v
