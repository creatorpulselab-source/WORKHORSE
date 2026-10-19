"""Generic pipeline for 'one STL per item' Etsy listings (desk organizers, can holders, keychains, planters, ...).

A listing is described by a spec dict (see the per-listing modules). The pipeline is:
  build + validate meshes -> export STL (+ optional extras) -> headless Blender renders of the REAL files
  -> vibrant listing images (kit.py) -> guide PDF -> zips -> listing copy + Etsy-limit validation.
Every stage is timed into run_report.json.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

import trimesh

from . import cutters as ct
from . import kit
from . import listing as lst
from .blender_render import render_scenes
from .common import LICENSE_TEXT, RunReport, listing_dirs, zip_folder

PALETTE_BRIGHT = [[0.88, 0.04, 0.06], [0.0, 0.42, 0.95], [1.0, 0.55, 0.02], [0.05, 0.62, 0.25], [0.55, 0.12, 0.85],
                  [0.95, 0.95, 0.93], [0.0, 0.70, 0.72], [0.95, 0.18, 0.50]]

SPOTS = {
    "blue": {"inner": [0.06, 0.16, 0.62], "outer": [0.0, 0.01, 0.10], "radius": 0.20},
    "teal": {"inner": [0.0, 0.62, 0.62], "outer": [0.0, 0.07, 0.12], "radius": 0.07},
    "purple": {"inner": [0.50, 0.10, 0.70], "outer": [0.05, 0.0, 0.12], "radius": 0.07},
    "warm": {"inner": [0.95, 0.45, 0.10], "outer": [0.25, 0.02, 0.0], "radius": 0.07},
    "pink": {"inner": [0.95, 0.25, 0.55], "outer": [0.22, 0.0, 0.10], "radius": 0.07},
    "green": {"inner": [0.10, 0.65, 0.30], "outer": [0.0, 0.10, 0.05], "radius": 0.07},
    "slate": {"inner": [0.30, 0.38, 0.55], "outer": [0.03, 0.04, 0.09], "radius": 0.07},
}


def spot(name: str, radius: float | None = None) -> Dict:
    s = dict(SPOTS[name])
    if radius:
        s["radius"] = radius
    return s


# ----------------------------------------------------------------------------- geometry export
def export_items(rep: RunReport, dirs, defs: Sequence[Tuple[str, Callable]], stl_subdir: str = "STL") -> List[Dict]:
    stl_dir = dirs["files"] / stl_subdir
    if stl_dir.exists():
        shutil.rmtree(stl_dir)
    stl_dir.mkdir(parents=True, exist_ok=True)
    catalog: List[Dict] = []
    with rep.stage("build + validate geometry, export STL"):
        for n, (name, fn) in enumerate(defs, start=1):
            mesh = fn()
            v = ct.assert_printable(name, mesh)
            fname = f"{n:02d}_{name.replace(' ', '_').replace('/', '-')}.stl"
            mesh.export(stl_dir / fname)
            catalog.append({"index": n, "name": name, "file": fname, "size_mm": [round(float(x), 1) for x in mesh.extents],
                            "volume_cm3": round(v["volume_mm3"] / 1000, 1), "faces": v["faces"]})
    return catalog


# ----------------------------------------------------------------------------- layout + scenes
def pack_layout(dims: Sequence[Tuple[float, float]], gap: float) -> Tuple[List[Tuple[float, float]], float, float]:
    """Row-pack footprints to an (approximately) square block. Returns centres, width, depth (centred on 0,0)."""
    total_area = sum((w + gap) * (d + gap) for w, d in dims)
    best = None
    for k in range(10, 60):
        W = math.sqrt(total_area) * (0.7 + k * 0.03)
        rows, cur, cur_w, cur_h = [], [], 0.0, 0.0
        for i, (w, d) in enumerate(dims):
            if cur and cur_w + w + gap > W:
                rows.append((cur, cur_w - gap, cur_h))
                cur, cur_w, cur_h = [], 0.0, 0.0
            cur.append(i)
            cur_w += w + gap
            cur_h = max(cur_h, d)
        if cur:
            rows.append((cur, cur_w - gap, cur_h))
        tw = max(r[1] for r in rows)
        th = sum(r[2] for r in rows) + gap * (len(rows) - 1)
        score = abs(math.log(tw / th))
        if best is None or score < best[0]:
            best = (score, rows, tw, th)
    _, rows, tw, th = best
    pos: List[Tuple[float, float]] = [(0.0, 0.0)] * len(dims)
    y = th / 2
    for idxs, rw, rh in rows:
        x = -rw / 2
        for i in idxs:
            w, d = dims[i]
            pos[i] = (x + w / 2, y - rh / 2)
            x += w + gap
        y -= rh + gap
    return pos, tw, th


def _stl_path(dirs, entry: Dict, subdir: str = "STL") -> str:
    return str(dirs["files"] / subdir / entry["file"])


def scene_cover(dirs, catalog: List[Dict], colors, out: Path, repeat: int = 1, elev: float = 76, spot_name: str = "blue",
                gap: float = 12.0, lens: float = 50, fill: float = 0.97, subdir: str = "STL", spot_radius: float | None = None,
                rot_jitter: float = 0.0) -> Dict:
    entries = [e for _ in range(repeat) for e in catalog]
    dims = [(e["size_mm"][0], e["size_mm"][1]) for e in entries]
    pos, tw, th = pack_layout(dims, gap)
    objs = []
    for i, (e, (x, y)) in enumerate(zip(entries, pos)):
        objs.append({"stl": _stl_path(dirs, e, subdir), "loc": [x, y, 0], "color": colors[(i * 3 + i // 5) % len(colors)],
                     "rot_z": ((i * 37) % 31 - 15) * (rot_jitter / 15.0) if rot_jitter else 0})
    span = max(tw, th) * 1.02
    dist = span / (fill * 36.0 / lens) * (1.0 + 0.10 * max(0.0, (84 - elev)) / 30)
    return {"out": str(out), "res": [2000, 2000], "ground_spot": spot(spot_name, spot_radius or round(span / 2000 * 0.9, 3)),
            "objects": objs, "camera": {"target": [0, 0, 0], "distance": dist, "elevation": elev, "azimuth": 0, "lens": lens}}


def scene_row(dirs, entries: List[Dict], colors, out: Path, spot_name: str = "warm", elev: float = 38, azimuth: float = 12,
              gap: float = 16.0, lens: float = 85, dof: float = 5.0, subdir: str = "STL", fill: float = 0.84,
              rots: Sequence[float] = (-10, 6, 12)) -> Dict:
    dims = [(e["size_mm"][0], e["size_mm"][1]) for e in entries]
    total_w = sum(w for w, _ in dims) + gap * (len(dims) - 1)
    x = -total_w / 2
    objs = []
    for i, (e, (w, d)) in enumerate(zip(entries, dims)):
        objs.append({"stl": _stl_path(dirs, e, subdir), "loc": [x + w / 2, 0, 0], "color": colors[i % len(colors)],
                     "rot_z": rots[i % len(rots)]})
        x += w + gap
    tallest = max(e["size_mm"][2] for e in entries)
    dist = total_w / (fill * 36.0 / lens) * 1.12
    return {"out": str(out), "res": [2000, 2000], "ground_spot": spot(spot_name, round(total_w / 2000 * 0.9, 3)),
            "objects": objs, "camera": {"target": [0, 0, tallest * 0.35], "distance": dist, "elevation": elev,
                                        "azimuth": azimuth, "lens": lens, "dof": dof}}


def scene_single(dirs, entry: Dict, color, out: Path, spot_name: str = "teal", azimuth: float = 28, elev: float = 32,
                 lens: float = 85, dof: float = 6.0, subdir: str = "STL", fill: float = 0.72) -> Dict:
    w, d, h = entry["size_mm"]
    diag = math.sqrt(w * w + d * d + h * h)
    dist = diag / (fill * 36.0 / lens) * 1.0
    return {"out": str(out), "res": [2000, 2000], "ground_spot": spot(spot_name, round(max(w, d) / 2000 * 0.9, 3)),
            "objects": [{"stl": _stl_path(dirs, entry, subdir), "loc": [0, 0, 0], "color": color, "rot_z": 0}],
            "camera": {"target": [0, 0, h * 0.45], "distance": dist, "elevation": elev, "azimuth": azimuth, "lens": lens,
                       "dof": dof}}


def render(rep: RunReport, dirs, scenes: List[Dict], label: str = "render product photos (Blender headless, EEVEE)") -> Dict:
    with rep.stage(label):
        r = render_scenes(scenes, dirs["work"])
    if r["returncode"] or r["missing"]:
        raise RuntimeError(f"render failed: {r['missing']} {r['stderr_tail']}")
    return {"renders": r["rendered"]}


# ----------------------------------------------------------------------------- packaging
def make_pdf(rep: RunReport, dirs, name: str, pages, theme: str) -> Path:
    with rep.stage("guide PDF"):
        out = dirs["root"] / "etsy_upload" / name
        kit.pdf_guide(out, pages, theme)
    return out


def license_lines() -> List[str]:
    return [line for line in LICENSE_TEXT.strip().splitlines() if line.strip() and not set(line.strip()) <= {"="}]


def zip_step(rep: RunReport, dirs, zips: Sequence[Tuple[str, str]]) -> Dict:
    with rep.stage("zip deliverables (Etsy 20 MB per-file cap enforced)"):
        out = dirs["root"] / "etsy_upload"
        out.mkdir(exist_ok=True)
        made = [zip_folder(dirs["files"] / sub, out / zname) for zname, sub in zips]
    return {"zips": {z.name: round(z.stat().st_size / 1e6, 2) for z in made}}


def clear_images(dirs) -> None:
    for old in dirs["images"].glob("*"):
        if old.is_file():
            old.unlink()


def dims_rows(catalog: List[Dict]) -> List[str]:
    return [f"{e['name']}|{e['size_mm'][0]:.0f} x {e['size_mm'][1]:.0f} x {e['size_mm'][2]:.0f} mm" for e in catalog]


def finish(rep: RunReport, dirs, catalog: List[Dict], copy: Dict) -> Dict:
    with rep.stage("listing copy + Etsy limit validation"):
        data = lst.write_listing(dirs["root"], **copy)
    rep.facts["validation_problems"] = data["validation_problems"]
    rep.facts["title_chars"] = data["title_chars"]
    out = rep.save(dirs["root"])
    (dirs["root"] / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return out
