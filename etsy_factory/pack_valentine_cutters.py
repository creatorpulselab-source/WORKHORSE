"""Listing #2 in the cutter family: Valentine Cookie Cutter STL Pack (10 designs, 2 sizes, press plates, STL + 3MF).

Same pipeline as pilot_cookie_cutters.py (geometry -> Blender renders -> ComfyUI backdrops -> listing images -> guide PDF + zips -> copy)
with Valentine shapes, palette, backdrops and copy.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.pack_valentine_cutters
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")

import trimesh

from etsy_factory import cutters as ct
from etsy_factory import kit
from etsy_factory import listing as lst
from etsy_factory import scenes_cutters as scn
from etsy_factory import shapes_valentine as sv
from etsy_factory.blender_render import render_scenes
from etsy_factory.common import LICENSE_TEXT, RunReport, listing_dirs, zip_folder

SLUG = "valentine_cookie_cutters_stl"
SIZES = (60, 80)
THEME = "valentine"

RED, PINK, WHITE, GOLD, PLUM = [0.85, 0.03, 0.10], [0.98, 0.38, 0.58], [0.95, 0.93, 0.92], [1.0, 0.62, 0.08], [0.45, 0.06, 0.32]
PALETTE = [RED, PINK, WHITE, GOLD, PLUM]
ROSE_SPOT = {"inner": [0.80, 0.10, 0.35], "outer": [0.12, 0.0, 0.05], "radius": 0.10}
PINK_SPOT = {"inner": [0.95, 0.40, 0.60], "outer": [0.20, 0.02, 0.10], "radius": 0.08}
PLUM_SPOT = {"inner": [0.55, 0.12, 0.60], "outer": [0.07, 0.0, 0.10], "radius": 0.07}

# design order (file index): 1 heart, 2 double hearts, 3 heart+arrow, 4 lips, 5 teddy, 6 flower, 7 key, 8 candy, 9 gift box, 10 cupcake
IDX = {k: i for i, k in enumerate(sv.DESIGNS, start=1)}


def build_files(rep: RunReport, dirs) -> dict:
    stl_dir, mf_dir = dirs["files"] / "STL", dirs["files"] / "3MF"
    for p in (stl_dir, mf_dir):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    catalog = []
    with rep.stage("build + validate geometry, export STL and 3MF"):
        for n, (key, fn) in enumerate(sv.DESIGNS.items(), start=1):
            nice = sv.NICE_NAMES[key].replace(" ", "_")
            prefix = f"{n:02d}_{nice}"
            entry = {"key": key, "name": sv.NICE_NAMES[key], "files": [], "sizes_mm": {}}
            plate, x_off = trimesh.Scene(), 0.0
            for size in SIZES:
                poly = sv.normalized(fn(), size)
                cutter = ct.build_cutter(poly)
                v = ct.assert_printable(f"{key}_cutter_{size}", cutter)
                name = f"{prefix}_Cutter_{size}mm.stl"
                cutter.export(stl_dir / name)
                entry["files"].append({"file": name, **v})
                entry["sizes_mm"][str(size)] = [round(float(cutter.extents[0]), 1), round(float(cutter.extents[1]), 1)]
                moved = cutter.copy()
                moved.apply_translation((x_off - moved.bounds[0][0], -moved.bounds[0][1], 0))
                plate.add_geometry(moved, node_name=f"cutter_{size}")
                x_off += moved.extents[0] + 8
                if size == max(SIZES):
                    press = ct.build_press(poly)
                    pv = ct.assert_printable(f"{key}_press", press)
                    pname = f"{prefix}_Press_Plate_{size}mm.stl"
                    press.export(stl_dir / pname)
                    entry["files"].append({"file": pname, **pv})
                    pm = press.copy()
                    pm.apply_translation((x_off - pm.bounds[0][0], -pm.bounds[0][1], -pm.bounds[0][2]))
                    plate.add_geometry(pm, node_name="press")
            plate.export(mf_dir / f"{prefix}_All_Parts.3mf")
            catalog.append(entry)
    return {"catalog": catalog, "stl_files": len(list(stl_dir.glob("*.stl"))), "3mf_files": len(list(mf_dir.glob("*.3mf")))}


def _scenes(stl_dir: Path, img: Path):
    img.mkdir(parents=True, exist_ok=True)
    scn.PALETTE[:] = PALETTE                         # cover_grid / hero_trio pick colours from this list
    S = lambda i, kind="Cutter", size=80: scn._stl(stl_dir, i, kind, size)
    scenes = [
        scn.cover_grid(stl_dir, img / "_raw_cover_grid.png", n=5, pitch=104, distance=800),
        scn.hero_trio(stl_dir, img / "_raw_hero_trio.png", picks=(IDX["teddy_bear"], IDX["classic_heart"], IDX["cupcake"])),
        scn.closeup(stl_dir, img / "_raw_closeup_heart.png", IDX["classic_heart"], RED, elevation=60, spot=ROSE_SPOT),
        scn.closeup(stl_dir, img / "_raw_closeup_teddy.png", IDX["teddy_bear"], PINK, azimuth=-20, elevation=62, spot=PINK_SPOT),
        {"out": str(img / "_raw_cutter_and_press.png"), "res": [2000, 2000], "ground_spot": PLUM_SPOT,
         "objects": [{"stl": S(IDX["teddy_bear"]), "loc": [-58, 0, 0], "color": RED, "rot_z": -10},
                     {"stl": S(IDX["teddy_bear"], "Press_Plate"), "loc": [58, 0, 0], "color": GOLD, "rot_z": 12}],
         "camera": {"target": [0, 0, 6], "distance": 430, "elevation": 44, "azimuth": 0, "lens": 75, "dof": 6.0}},
        {"out": str(img / "_raw_two_sizes.png"), "res": [2000, 2000], "ground_spot": ROSE_SPOT,
         "objects": [{"stl": S(IDX["classic_heart"], size=80), "loc": [-52, 0, 0], "color": PINK, "rot_z": 0},
                     {"stl": S(IDX["classic_heart"], size=60), "loc": [58, -6, 0], "color": GOLD, "rot_z": 0}],
         "camera": {"target": [4, 0, 5], "distance": 470, "elevation": 50, "azimuth": 0, "lens": 75, "dof": 7.0}},
    ]
    for s in scenes:
        s["transparent"] = True
    scenes[1]["camera"]["elevation"] = 26            # hero is staged low (3/4 view) for the 'table' backdrop
    scenes[1]["camera"]["distance"] = 800            # pull back: the 3 cutters are ~290 mm wide and were clipped by the frame at 500 / 640
    scenes[1]["ground_spot"] = PINK_SPOT
    return scenes


def render_photos(rep: RunReport, dirs) -> dict:
    with rep.stage("render product photos (Blender headless)"):
        r = render_scenes(_scenes(dirs["files"] / "STL", dirs["work"]), dirs["work"])
    if r["returncode"] or r["missing"]:
        raise RuntimeError(f"render failed: {r['missing']} {r['stderr_tail']}")
    return {"renders": r["rendered"]}


def _rings(poly):
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return [list(poly.exterior.coords)] + [list(i.coords) for i in poly.interiors]


def compose_images(rep: RunReport, dirs, catalog) -> dict:
    W, img = dirs["work"], dirs["images"]
    for old in img.glob("*"):
        if old.is_file():
            old.unlink()
    n = len(catalog)
    with rep.stage("backdrops (ComfyUI) + composite + compose listing images"):
        from etsy_factory import comfy_backgrounds as cb

        def comp(raw: str, bg: str, seed: int, **kw) -> Path:
            return kit.composite(W / raw, cb.load(bg, seed=seed), W / ("_comp" + raw), **kw)

        cover_src = comp("_raw_cover_grid.png", "valentine_flatlay", 20261019, scale=1.0, bg_dim=0.30)
        hero_src = comp("_raw_hero_trio.png", "valentine_table", 20261019, scale=0.92, dy=230)
        heart_src = comp("_raw_closeup_heart.png", "valentine_flatlay", 7, scale=0.84, dy=-90)
        teddy_src = comp("_raw_closeup_teddy.png", "valentine_flatlay", 21, scale=0.84, dy=-90)
        press_src = comp("_raw_cutter_and_press.png", "valentine_flatlay", 33, scale=0.95, dy=-60)
        sizes_src = comp("_raw_two_sizes.png", "valentine_flatlay", 45, scale=0.95, dy=-60)
        kit.cover_open(cover_src, img / "01_cover.jpg", str(n), "Valentine Cookie Cutters", "STL + 3MF  -  2 sizes  -  press plates",
                       ["Instant Download", "STL & 3MF", "3D Print Ready", "Press Plates", "Sell Your Prints"], THEME, burst=["2 SIZES", "EACH"])
        kit.captioned(hero_src, img / "02_hero.jpg", "Print your own Valentine cookie cutters",
                      "Hearts  *  Teddy Bear  *  Cupcake  *  Lips  *  and more", THEME)
        kit.captioned(heart_src, img / "03_closeup_heart.jpg", "Clean cutting edge, comfy grip flange",
                      "0.8 mm cutting edge  *  5 mm flange  *  14 mm tall", THEME)
        kit.captioned(teddy_src, img / "04_closeup_teddy.jpg", "Even the detailed shapes are print-friendly",
                      "Designed for a standard 0.4 mm nozzle", THEME)
        kit.captioned(press_src, img / "05_cutter_and_press.jpg", "A press plate for every design",
                      "Push the shape out cleanly - includes one per design", THEME)
        kit.captioned(sizes_src, img / "06_two_sizes.jpg", "Two sizes: 60 mm and 80 mm",
                      f"Both sizes of all {n} designs are in the download", THEME)
        items = [(e["name"], _rings(sv.normalized(sv.DESIGNS[e["key"]](), 80))) for e in catalog]
        kit.silhouette_sheet(img / "07_designs.jpg", items, f"All {n} designs included", THEME, cols=5,
                             footer="Each design in 2 sizes + a matching press plate")
        rows = [f"{e['name']}|{e['sizes_mm']['60'][0]:.0f}x{e['sizes_mm']['60'][1]:.0f}  /  "
                f"{e['sizes_mm']['80'][0]:.0f}x{e['sizes_mm']['80'][1]:.0f} mm" for e in catalog]
        kit.card(img / "08_sizes.jpg", "Measured sizes (W x H)", rows, THEME, kicker="Small  /  Large  - including grip flange",
                 footer="Sizes are measured from the actual STL files, flange included. Cutting area is about 11 mm smaller than the overall size.")
        kit.card(img / "09_print_guide.jpg", "Easy to print", [
            "Printer|Any FDM (0.4 mm nozzle)", "Material|PLA or PETG", "Layer height|0.2 mm", "Walls|3 perimeters (1.2 mm)",
            "Infill|15%  (walls carry the shape)", "Supports|None needed", "Orientation|Flange down, as exported",
        ], THEME, kicker="Print guide", footer="Every file is checked to be a closed, watertight mesh before it is packaged. A printable guide PDF is included.")
        kit.card(img / "10_files_license.jpg", "What you get", [
            f"STL cutters|{n * 2} files  ({n} designs x 2 sizes)", f"STL press plates|{n} files",
            f"3MF plates|{n} files  (all parts per design)", "Guide|PDF print guide + license",
            "Delivery|Instant digital download", "Use|Personal use. Sell the PRINTED items freely.",
            "Not allowed|Reselling or sharing the digital files",
        ], THEME, kicker="Files & license",
            footer="Not certified food-safe: great for play dough, clay & fondant. For cookies use food-safe filament, keep contact brief, hand-wash only.")
    return {"images": len(list(img.glob("*.jpg")))}


def make_guide(rep: RunReport, dirs, catalog) -> Path:
    n = len(catalog)
    names = ", ".join(e["name"] for e in catalog)
    pages = [
        ("Valentine Cookie Cutters - Print Guide", [
            f"Thank you for your purchase! This pack contains {n} original Valentine designs ({names}). Every design is included in two sizes "
            "(60 mm and 80 mm nominal) plus a matching press plate.",
            "# What is in the download",
            f"- Valentine_Cookie_Cutters_STL.zip: {n * 2} cutters + {n} press plates (STL, millimetres).",
            f"- Valentine_Cookie_Cutters_3MF.zip: {n} plates, one per design, with both cutter sizes and the press plate laid out together.",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PLA or PETG.  Nozzle: 0.4 mm.  Layer height: 0.2 mm.  Walls / perimeters: 3 (1.2 mm).  Infill: 15%.  Supports: none.  Brim: not required.",
            "Print each part flat on the bed with the wide grip flange down - exactly as it is exported. The thin cutting edge (0.8 mm) is on the top of the "
            "cutter; slower outer-wall speed gives a cleaner edge.",
            "# Sizes",
            "The size in the file name (60 mm / 80 mm) is the length of the longest side of the shape itself. The grip flange adds about 11 mm in each "
            "direction, so the printed part is larger than the number in the name. Exact overall sizes are listed on the listing photos.",
            "# Using the press plate",
            "Press the cutter into rolled dough or clay, then place the matching press plate inside the cutter and push down on the knob to release the shape cleanly.",
        ]),
        ("Care, safety and license", [
            "# Care and food contact",
            "3D-printed plastic is porous and is NOT certified food-safe. These cutters are ideal for play dough, polymer clay and fondant. If you use them with "
            "cookie dough, print with a filament sold as food-safe, keep contact brief, hand-wash with warm soapy water and never use a dishwasher. "
            "Do not microwave or bake the plastic.",
            "# License",
            *[line for line in LICENSE_TEXT.strip().splitlines() if line.strip() and not set(line.strip()) <= {"="}],
        ]),
    ]
    with rep.stage("guide PDF"):
        out = dirs["root"] / "etsy_upload" / "Print_Guide_and_License.pdf"
        kit.pdf_guide(out, pages, THEME)
    return out


def package(rep: RunReport, dirs) -> dict:
    with rep.stage("zip deliverables (Etsy 20 MB per-file cap enforced)"):
        out = dirs["root"] / "etsy_upload"
        out.mkdir(exist_ok=True)
        z1 = zip_folder(dirs["files"] / "STL", out / "Valentine_Cookie_Cutters_STL.zip")
        z2 = zip_folder(dirs["files"] / "3MF", out / "Valentine_Cookie_Cutters_3MF.zip")
    return {"zips": {z.name: round(z.stat().st_size / 1e6, 2) for z in (z1, z2)}}


def write_copy(rep: RunReport, dirs, catalog) -> dict:
    n = len(catalog)
    title = ("Valentine Cookie Cutter STL Bundle, 10 Valentine's Day Shapes x 2 Sizes, Heart Teddy Bear Cupcake, Press Plates, "
             "3D Print Files, STL & 3MF")
    tags = ["valentine stl", "cookie cutter stl", "heart cookie cutter", "3d print files", "valentines day stl", "3mf files",
            "fondant cutter", "playdough cutter", "clay cutter stl", "printable cutter", "stl bundle", "valentine 3d print", "baking gift"]
    names = ", ".join(e["name"] for e in catalog)
    desc = f"""Print your own Valentine's Day cookie cutters at home! This instant-download pack gives you {n} original designs, each in TWO sizes with a matching press plate - ready to slice and print.

WHAT'S INCLUDED
- {n} designs: {names}
- {n * 2} cutter STL files (each design in 60 mm and 80 mm nominal size)
- {n} press plate STL files (push the shape out cleanly)
- {n} 3MF plates (both cutter sizes + press plate laid out together)
- PDF print guide + license

EASY TO PRINT
- Any FDM printer, 0.4 mm nozzle, PLA or PETG, 0.2 mm layers, 3 perimeters, 15% infill
- No supports needed - parts print flat with the grip flange down
- Every file is checked to be a closed (watertight) mesh before packaging
- 0.8 mm cutting edge, 14 mm tall, 5 mm grip flange for comfortable pressing

SIZES
The size in each file name is the length of the longest side of the shape. The grip flange adds roughly 11 mm, so the real printed size is a little larger - full measured sizes are in the listing photos.

IMPORTANT
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- Not certified food-safe. Great for play dough, polymer clay and fondant. If using with cookie dough, print in food-safe filament, keep contact brief and hand-wash only.
- Colours in the photos are for display - print in any colour you like.

LICENSE
Personal use is included, and you may sell PHYSICAL items you print from these files. You may not resell, share or redistribute the digital files. All designs are original - no licensed characters or logos.

Questions? Message the shop - happy to help with any print issue."""
    return lst.write_listing(
        dirs["root"], title=title, tags=tags, description=desc, price_usd=4.99,
        sale_hint="set base price $4.99, then run an Etsy Sale (e.g. 30% off) so the strike-through shows; market range for similar packs is about $1.50-$7",
        category="Craft Supplies & Tools > Patterns & How To > Digital Patterns (or Digital Prints/Templates)",
        materials="Digital STL and 3MF files, PDF guide",
        whats_in_the_files=[f"{n * 2} cutter STL files", f"{n} press plate STL files", f"{n} 3MF plates", "PDF guide + license"],
        notes=["Etsy digital listing: type = Digital, attach the 3 files from etsy_upload.",
               "Seasonal: publish by early January - Valentine's search demand climbs through January and peaks early February.",
               "Photos use AI-generated backdrops (ComfyUI) - mention in the listing/AI disclosure if you wish."])


def run() -> dict:
    rep = RunReport(SLUG)
    dirs = listing_dirs(SLUG)
    facts = build_files(rep, dirs)
    catalog = facts.pop("catalog")
    rep.facts.update(facts)
    rep.facts.update(render_photos(rep, dirs))
    rep.facts.update(compose_images(rep, dirs, catalog))
    make_guide(rep, dirs, catalog)
    rep.facts.update(package(rep, dirs))
    with rep.stage("listing copy + Etsy limit validation"):
        data = write_copy(rep, dirs, catalog)
    rep.facts["validation_problems"] = data["validation_problems"]
    rep.facts["title_chars"] = data["title_chars"]
    out = rep.save(dirs["root"])
    (dirs["root"] / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return out


def refresh_covers() -> dict:
    """Re-render and recompose ONLY 01_cover.jpg and 02_hero.jpg of the finished listing (geometry, zips and copy untouched)."""
    from etsy_factory import comfy_backgrounds as cb
    dirs = listing_dirs(SLUG)
    W, img = dirs["work"], dirs["images"]
    n = len(json.loads((dirs["root"] / "catalog.json").read_text(encoding="utf-8")))
    scenes = _scenes(dirs["files"] / "STL", W)[:2]
    r = render_scenes(scenes, W)
    if r["returncode"] or r["missing"]:
        raise RuntimeError(f"render failed: {r['missing']} {r['stderr_tail']}")
    cover_src = kit.composite(W / "_raw_cover_grid.png", cb.load("valentine_flatlay", seed=20261019), W / "_comp_raw_cover_grid.png",
                              scale=1.0, bg_dim=0.30)
    hero_src = kit.composite(W / "_raw_hero_trio.png", cb.load("valentine_table", seed=20261019), W / "_comp_raw_hero_trio.png",
                             scale=0.92, dy=230)
    kit.cover_open(cover_src, img / "01_cover.jpg", str(n), "Valentine Cookie Cutters", "STL + 3MF  -  2 sizes  -  press plates",
                   ["Instant Download", "STL & 3MF", "3D Print Ready", "Press Plates", "Sell Your Prints"], THEME, burst=["2 SIZES", "EACH"])
    kit.captioned(hero_src, img / "02_hero.jpg", "Print your own Valentine cookie cutters",
                  "Hearts  *  Teddy Bear  *  Cupcake  *  Lips  *  and more", THEME)
    return {"cover": str(img / "01_cover.jpg"), "hero": str(img / "02_hero.jpg")}


if __name__ == "__main__":
    print(json.dumps(refresh_covers() if "--covers" in sys.argv else run(), indent=2))
