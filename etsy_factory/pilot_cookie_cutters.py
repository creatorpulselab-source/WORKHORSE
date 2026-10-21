"""Pilot listing #1: Christmas Cookie Cutter STL Pack (10 designs, 2 sizes, press plates, STL + 3MF).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.pilot_cookie_cutters
Stages (each timed into run_report.json): geometry -> product renders -> listing images -> guide PDF + zips -> listing copy.
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
from etsy_factory import shapes_christmas as sc
from etsy_factory.blender_render import render_scenes
from etsy_factory.common import LICENSE_TEXT, RunReport, listing_dirs, zip_folder

SLUG = "christmas_cookie_cutters_stl"
SIZES = (60, 80)
THEME = "christmas"


def build_files(rep: RunReport, dirs) -> dict:
    stl_dir = dirs["files"] / "STL"
    mf_dir = dirs["files"] / "3MF"
    for p in (stl_dir, mf_dir):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    catalog = []
    with rep.stage("build + validate geometry, export STL and 3MF"):
        for n, (key, fn) in enumerate(sc.DESIGNS.items(), start=1):
            nice = sc.NICE_NAMES[key].replace(" ", "_")
            prefix = f"{n:02d}_{nice}"
            entry = {"key": key, "name": sc.NICE_NAMES[key], "files": [], "sizes_mm": {}}
            plate = trimesh.Scene()
            x_off = 0.0
            for size in SIZES:
                poly = sc.normalized(fn(), size)
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


def render_photos(rep: RunReport, dirs) -> dict:
    with rep.stage("render product photos (Blender headless, EEVEE)"):
        scenes = scn.all_scenes(dirs["files"] / "STL", dirs["work"])
        r = render_scenes(scenes, dirs["work"])
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

        cover_src = comp("_raw_cover_grid.png", "christmas_flatlay", 20261018, scale=0.90)
        hero_src = comp("_raw_hero_trio.png", "christmas_table", 20261018, scale=1.0, dy=210)
        ginger_src = comp("_raw_closeup_gingerbread.png", "christmas_flatlay", 7, scale=0.84, dy=-90)
        snow_src = comp("_raw_closeup_snowflake.png", "christmas_flatlay", 21, scale=0.84, dy=-90)
        press_src = comp("_raw_cutter_and_press.png", "christmas_flatlay", 33, scale=0.95, dy=-60)
        sizes_src = comp("_raw_two_sizes.png", "christmas_flatlay", 45, scale=0.95, dy=-60)
        kit.cover_open(cover_src, img / "01_cover.jpg", str(n), "Christmas Cookie Cutters",
                       "STL + 3MF  -  2 sizes  -  press plates",
                       ["Instant Download", "STL & 3MF", "3D Print Ready", "Press Plates", "Sell Your Prints"], THEME,
                       burst=["2 SIZES", "EACH"])
        kit.captioned(hero_src, img / "02_hero.jpg", "Print your own holiday cookie cutters",
                      "Gingerbread  •  Stars  •  Snowflakes  •  Candy Canes  •  and more", THEME)
        kit.captioned(ginger_src, img / "03_closeup_gingerbread.jpg", "Clean cutting edge, comfy grip flange",
                      "0.8 mm cutting edge  •  5 mm flange  •  14 mm tall", THEME)
        kit.captioned(snow_src, img / "04_closeup_snowflake.jpg", "Even the detailed shapes are print-friendly",
                      "Designed for a standard 0.4 mm nozzle", THEME)
        kit.captioned(press_src, img / "05_cutter_and_press.jpg", "A press plate for every design",
                      "Push the shape out cleanly - includes one per design", THEME)
        kit.captioned(sizes_src, img / "06_two_sizes.jpg", "Two sizes: 60 mm and 80 mm",
                      "Both sizes of all 10 designs are in the download", THEME)
        items = [(e["name"], _rings(sc.normalized(sc.DESIGNS[e["key"]](), 80))) for e in catalog]
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


GUIDE_PAGES = None


def make_guide(rep: RunReport, dirs, catalog) -> Path:
    n = len(catalog)
    names = ", ".join(e["name"] for e in catalog)
    pages = [
        ("Christmas Cookie Cutters - Print Guide", [
            f"Thank you for your purchase! This pack contains {n} original Christmas designs ({names}). Every design is included in two sizes (60 mm and 80 mm nominal) plus a matching press plate.",
            "# What is in the download",
            f"- Christmas_Cookie_Cutters_STL.zip: {n * 2} cutters + {n} press plates (STL, millimetres).",
            f"- Christmas_Cookie_Cutters_3MF.zip: {n} plates, one per design, with both cutter sizes and the press plate laid out together.",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PLA or PETG.  Nozzle: 0.4 mm.  Layer height: 0.2 mm.  Walls / perimeters: 3 (1.2 mm).  Infill: 15%.  Supports: none.  Brim: not required.",
            "Print each part flat on the bed with the wide grip flange down - exactly as it is exported. The thin cutting edge (0.8 mm) is on the top of the cutter; slower outer-wall speed gives a cleaner edge.",
            "# Sizes",
            "The size in the file name (60 mm / 80 mm) is the length of the longest side of the shape itself. The grip flange adds about 11 mm in each direction, so the printed part is larger than the number in the name. Exact overall sizes are listed on the listing photos.",
            "# Using the press plate",
            "Press the cutter into rolled dough or clay, then place the matching press plate inside the cutter and push down on the knob to release the shape cleanly.",
        ]),
        ("Care, safety and license", [
            "# Care and food contact",
            "3D-printed plastic is porous and is NOT certified food-safe. These cutters are ideal for play dough, polymer clay and fondant. If you use them with cookie dough, print with a filament sold as food-safe, keep contact brief, hand-wash with warm soapy water and never use a dishwasher. Do not microwave or bake the plastic.",
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
        z1 = zip_folder(dirs["files"] / "STL", out / "Christmas_Cookie_Cutters_STL.zip")
        z2 = zip_folder(dirs["files"] / "3MF", out / "Christmas_Cookie_Cutters_3MF.zip")
    return {"zips": {z.name: round(z.stat().st_size / 1e6, 2) for z in (z1, z2)}}


def write_copy(rep: RunReport, dirs, catalog) -> dict:
    n = len(catalog)
    title = ("Christmas Cookie Cutter STL Bundle, 10 Holiday Shapes x 2 Sizes, Press Plates, 3D Print Files, "
             "STL & 3MF, Instant Download")
    tags = ["cookie cutter stl", "christmas stl", "3d print files", "gingerbread cutter", "3mf files", "holiday cookie",
            "fondant cutter", "playdough cutter", "clay cutter stl", "printable cutter", "stl bundle", "christmas 3d print",
            "baking gift"]
    names = ", ".join(e["name"] for e in catalog)
    desc = f"""Print your own Christmas cookie cutters at home! This instant-download pack gives you {n} original holiday designs, each in TWO sizes with a matching press plate - ready to slice and print.

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
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files.
- Not certified food-safe. Great for play dough, polymer clay and fondant. If using with cookie dough, print in food-safe filament, keep contact brief and hand-wash only.
- Colours in the photos are for display - print in any colour you like.

LICENSE
Personal use is included, and you may sell PHYSICAL items you print from these files. You may not resell, share or redistribute the digital files. All designs are original - no licensed characters or logos.

Questions? Message the shop - happy to help with any print issue."""
    contents = [f"{n * 2} cutter STL files", f"{n} press plate STL files", f"{n} 3MF plates", "PDF guide + license"]
    return lst.write_listing(
        dirs["root"], title=title, tags=tags, description=desc, price_usd=4.99,
        sale_hint="set base price $4.99, then run an Etsy Sale (e.g. 30% off) so the strike-through shows; market range for similar packs is about $1.50-$7",
        category="Craft Supplies & Tools > Patterns & How To > Digital Patterns (or Digital Prints/Templates)",
        materials="Digital STL and 3MF files, PDF guide",
        whats_in_the_files=contents,
        notes=["Etsy digital listing: type = Digital, attach the 3 files from etsy_upload.",
               "Seasonal peak: publish now - Christmas search demand climbs through early December."])


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


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
