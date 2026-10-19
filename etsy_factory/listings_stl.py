"""The four parametric STL listings: desk organizers, can holders, keychains, planter pack (STL + 3MF + GLB).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.listings_stl desk|cans|keychains|planters|all
Every listing: geometry validated -> real files rendered in Blender (transparent + shadow pass) -> composited on ComfyUI
backdrops -> vibrant listing images -> guide PDF -> zips -> listing copy + Etsy limit validation. Timed per stage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Dict, List

sys.path.insert(0, r"F:\WORKHORSE")

import trimesh

from etsy_factory import comfy_backgrounds as cb
from etsy_factory import kit, shapes3d as s3, shapes_keychain as kc
from etsy_factory import stl_listing as sl
from etsy_factory.common import RunReport, listing_dirs

SEED = 20261018


# ----------------------------------------------------------------------------- generic runner
def run_spec(spec: Dict) -> Dict:
    rep = RunReport(spec["slug"])
    dirs = listing_dirs(spec["slug"])
    W, IMG = dirs["work"], dirs["images"]
    catalog = sl.export_items(rep, dirs, spec["defs"])
    if spec.get("extras"):
        rep.facts.update(spec["extras"](rep, dirs, catalog))
    colors = spec.get("colors", sl.PALETTE_BRIGHT)
    cv, hr = spec["cover"], spec["hero"]

    scenes = [sl.scene_cover(dirs, catalog, colors, W / "_raw_cover.png", repeat=cv.get("repeat", 1), elev=cv.get("elev", 76),
                             gap=cv.get("gap", 12.0), lens=cv.get("lens", 50), rot_jitter=cv.get("jitter", 0.0))]
    scenes.append(sl.scene_row(dirs, [catalog[i] for i in hr["picks"]], colors, W / "_raw_hero.png", elev=hr.get("elev", 28),
                               gap=hr.get("gap", 16.0), fill=hr.get("fill", 0.80)))
    for k, c in enumerate(spec["closeups"]):
        scenes.append(sl.scene_single(dirs, catalog[c["idx"]], colors[c.get("color", k) % len(colors)], W / f"_raw_close{k}.png",
                                      azimuth=c.get("az", 28), elev=c.get("elev", 48), fill=c.get("fill", 0.70)))
    for s in scenes:
        s["transparent"] = True
    rep.facts.update(sl.render(rep, dirs, scenes))

    sl.clear_images(dirs)
    theme = spec["theme"]
    bgs = spec["backdrops"]
    with rep.stage("backdrops (ComfyUI) + composite + listing images"):
        def comp(raw: str, bg: str, seed: int, **kw) -> Path:
            return kit.composite(W / raw, cb.load(bg, seed=seed), W / ("_comp" + raw), **kw)

        n = 1
        cover_src = comp("_raw_cover.png", bgs["flat"], SEED, scale=cv.get("scale", 0.92))
        kit.cover(cover_src, IMG / f"{n:02d}_cover.jpg", cv["big"], cv["l1"], cv["l2"], cv["badges"], theme, burst=cv.get("burst", ()))
        n += 1
        hero_src = comp("_raw_hero.png", bgs["table"], SEED, scale=hr.get("scale", 1.0), dy=hr.get("dy", 200))
        kit.captioned(hero_src, IMG / f"{n:02d}_hero.jpg", hr["caption"], hr["sub"], theme)
        for k, c in enumerate(spec["closeups"]):
            n += 1
            src = comp(f"_raw_close{k}.png", bgs["flat"], 7 + 14 * k, scale=c.get("scale", 0.86), dy=c.get("dy", -80))
            kit.captioned(src, IMG / f"{n:02d}_close{k + 1}.jpg", c["caption"], c["sub"], theme)
        n += 1
        if spec.get("sheet"):
            kit.silhouette_sheet(IMG / f"{n:02d}_designs.jpg", spec["sheet"](catalog), spec["sheet_title"], theme,
                                 cols=spec.get("sheet_cols", 4), footer=spec.get("sheet_footer", ""))
        else:
            kit.card(IMG / f"{n:02d}_inside.jpg", spec["contents_title"], [f"{e['index']:02d}  {e['name']}" for e in catalog],
                     theme, kicker=spec["contents_kicker"], footer=spec.get("contents_footer", ""))
        n += 1
        kit.card(IMG / f"{n:02d}_sizes.jpg", spec["sizes_title"], sl.dims_rows(catalog), theme, kicker="W x D x H - measured from the STL files",
                 footer=spec.get("sizes_footer", ""))
        n += 1
        kit.card(IMG / f"{n:02d}_print.jpg", "Easy to print", spec["print_rows"], theme, kicker="Print guide", footer=spec["print_footer"])
        n += 1
        kit.card(IMG / f"{n:02d}_license.jpg", "What you get", spec["files_rows"], theme, kicker="Files & license", footer=spec["files_footer"])
    rep.facts["images"] = len(list(IMG.glob("*.jpg")))

    sl.make_pdf(rep, dirs, spec["pdf_name"], spec["guide"](catalog), theme)
    rep.facts.update(sl.zip_step(rep, dirs, spec["zips"]))
    out = sl.finish(rep, dirs, catalog, spec["copy"](dirs, catalog))
    return {k: v for k, v in out.items() if k in ("slug", "total_seconds", "stages", "images", "renders", "zips", "validation_problems", "title_chars")}


def license_pages(extra_notes: List[str]) -> tuple:
    return ("Care, safety and license", [*extra_notes, "# License", *sl.license_lines()])


# ----------------------------------------------------------------------------- 1. DESK ORGANIZERS
def desk_spec() -> Dict:
    def guide(cat):
        names = ", ".join(e["name"] for e in cat)
        return [("Desk Organizer Bundle - Print Guide", [
            f"Thank you for your purchase! This pack contains {len(cat)} desk organizers: {names}.",
            "# What is in the download",
            f"- Desk_Organizers_STL.zip: {len(cat)} STL files in millimetres, one per organizer.",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PLA or PETG.  Nozzle: 0.4 mm.  Layer height: 0.2 mm.  Walls: 2.4 mm (6 perimeters on a 0.4 mm nozzle).  Infill: 15%.  Supports: none.",
            "Print every part in the orientation it is exported (flat on its base). The largest part is 196 mm long (Pen and Pencil Tray) - a 220 x 220 mm bed is enough for everything.",
            "# Notes per item",
            "Sticky Note Tray: inside is 81 mm square, sized for 3 x 3 inch (76 mm) notes.",
            "Business Card Holder: the slot is 92 mm long, sized for standard 89 x 51 mm cards.",
            "Phone Stand: the slot at the base is about 18 mm wide - fits most phones including slim cases; measure yours first.",
            "Cable Clips x4: ring 13 mm with a 6 mm opening; the flat back is made for double-sided tape.",
        ]), license_pages(["Printed PLA/PETG is fine for desk use. Keep away from heat (car dashboards, radiators)."])]

    def copy(dirs, cat):
        title = "Desk Organizer STL Bundle, 10 Printable Office Organizers, Pen Holder, Phone Stand, Cable Clips, Tray, 3D Print Files"
        tags = ["desk organizer stl", "3d print files", "pen holder stl", "phone stand stl", "office organizer", "cable clip stl",
                "stl bundle", "3d printed gift", "desk accessories", "printable stl", "pencil cup stl", "desk tray stl",
                "functional 3d print"]
        names = "\n".join(f"- {e['name']} ({e['size_mm'][0]:.0f} x {e['size_mm'][1]:.0f} x {e['size_mm'][2]:.0f} mm)" for e in cat)
        desc = f"""Organize your desk with 10 functional, print-ready STL designs - pen cups, a phone stand, cable clips, trays and more. Instant download.

WHAT'S INCLUDED
{names}
- PDF print guide + license

EASY TO PRINT
- Any FDM printer with a 220 x 220 mm bed, 0.4 mm nozzle, PLA or PETG
- 0.2 mm layers, 2.4 mm walls, 15% infill
- No supports needed - every part prints in the orientation it is exported
- Every file is checked to be a closed (watertight) mesh before packaging
- Dimensions in the listing photos are measured from the actual files

GOOD TO KNOW
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- Sticky Note Tray fits 3 x 3 in notes, Business Card Holder fits standard 89 x 51 mm cards, Phone Stand slot is about 18 mm wide - measure your own items first.
- Print in any colour you like - the colours in the photos are just for display.

LICENSE
Personal use included, and you may sell PHYSICAL items you print from these files. You may not resell, share or redistribute the digital files. All designs are original.

Questions? Message the shop - happy to help with any print issue."""
        return dict(title=title, tags=tags, description=desc, price_usd=4.99,
                    sale_hint="set base price $4.99, then run an Etsy Sale (e.g. 30% off); similar functional bundles list at roughly $1.50-$7",
                    category="Craft Supplies & Tools > Patterns & How To (digital) / 3D printing files", materials="Digital STL files, PDF guide",
                    whats_in_the_files=[f"{len(cat)} STL files", "PDF guide + license"],
                    notes=["Etsy digital listing: attach Desk_Organizers_STL.zip and Print_Guide_and_License.pdf from etsy_upload.",
                           "Photos use AI-generated backdrops (ComfyUI) - mention in the listing/AI disclosure if you wish."])

    return dict(
        slug="desk_organizers_stl", theme="tech", defs=s3.DESK_ITEMS, pdf_name="Print_Guide_and_License.pdf",
        zips=[("Desk_Organizers_STL.zip", "STL")],
        backdrops={"flat": "desk_flatlay", "table": "desk_bokeh"},
        cover=dict(big="10", l1="Desk Organizer", l2="STL bundle  -  print-ready", elev=62, gap=10, scale=0.94, jitter=8,
                   badges=["Instant Download", "STL Files", "3D Print Ready", "No Supports", "Sell Your Prints"], burst=["10", "DESIGNS"]),
        hero=dict(picks=[3, 0, 5], caption="Print a tidier desk", sub="Phone stand  •  pen cup  •  card holder  •  and 7 more", elev=26, fill=0.84),
        closeups=[dict(idx=3, caption="Phone stand with a front lip", sub="Slot about 18 mm wide - measure your phone", az=-30, elev=40),
                  dict(idx=7, caption="4-compartment desk tray", sub="184 x 124 x 42 mm", az=20, elev=55),
                  dict(idx=4, caption="Cable clips x4 in one print", sub="13 mm ring, 6 mm opening, flat tape-on back", az=25, elev=50)],
        contents_title="10 organizers included", contents_kicker="What's inside", contents_footer="Each is a separate STL file in millimetres.",
        sizes_title="Measured sizes",
        sizes_footer="Sizes are measured from the actual STL files. Largest part: 196 mm - fits a 220 mm bed.",
        print_rows=["Printer|Any FDM, 220 x 220 mm bed", "Material|PLA or PETG", "Layer height|0.2 mm", "Walls|2.4 mm (6 perimeters)",
                    "Infill|15%", "Supports|None needed", "Orientation|As exported (flat on base)"],
        print_footer="Every file is checked to be a closed, watertight mesh before it is packaged. A printable guide PDF is included.",
        files_rows=["STL files|10 (one per organizer)", "Guide|PDF print guide + license", "Delivery|Instant digital download",
                    "Use|Personal use. Sell the PRINTED items freely.", "Not allowed|Reselling or sharing the digital files"],
        files_footer="Colours in the photos are for display - print in any colour. Always measure your own phone, cards and notes before printing.",
        guide=guide, copy=copy)


# ----------------------------------------------------------------------------- 2. CAN HOLDERS
def cans_spec() -> Dict:
    def guide(cat):
        return [("Can Holder Bundle - Print Guide", [
            f"Thank you for your purchase! This pack has {len(cat)} drink holders for standard (66 mm) and slim (58 mm) cans.",
            "# What is in the download",
            f"- Can_Holders_STL.zip: {len(cat)} STL files in millimetres.",
            "- This guide (PDF) and the license.",
            "# Fit",
            "Standard holders are sized for a 66.2 mm can (inside diameter 67.5 mm). Slim holders are sized for a 58 mm can (inside diameter 59.3 mm). Every cup has an 8.4 mm drain hole in the floor.",
            "Cans and bottles vary by brand - measure yours and scale the STL in your slicer (for example 101%) if needed.",
            "# Recommended print settings",
            "Material: PETG is recommended for outdoor and wet use; PLA works indoors.  Nozzle 0.4 mm.  Layer height 0.2 mm.  Walls 2.4 mm (6 perimeters).  Infill 15-20%.  Supports: none - print upright as exported.",
            "The 4-Can and 6-Can Caddies are large and heavy prints (about 154 x 154 mm and 228 x 155 mm footprints) - check your bed size first.",
            "# Clip loop",
            "The loop versions have a 9 mm hole at the base for a carabiner or cord.",
        ]), license_pages(["PLA softens at around 55-60 C - do not leave printed holders in a hot car. Printed plastic is not intended for direct food contact."])]

    def copy(dirs, cat):
        title = "Can Holder STL Bundle, 8 Printable Drink Holders, Standard and Slim Cans, Clip Loop, Cup Holder Adapter, Can Caddy"
        tags = ["can holder stl", "drink holder stl", "cooler can holder", "beer can holder", "can caddy stl", "cup holder adapter",
                "slim can holder", "3d print files", "party drink holder", "summer 3d print", "stl bundle", "tailgate gift",
                "camping 3d print"]
        names = "\n".join(f"- {e['name']} ({e['size_mm'][0]:.0f} x {e['size_mm'][1]:.0f} x {e['size_mm'][2]:.0f} mm)" for e in cat)
        desc = f"""Print your own can holders for the cooler, the deck or the car - 8 STL designs for standard and slim cans, including clip-loop versions, a cup-holder adapter and 4- and 6-can caddies. Instant download.

WHAT'S INCLUDED
{names}
- PDF print guide + license

FIT
- Standard holders: inside diameter 67.5 mm, for a 66.2 mm (12 oz / 16 oz) can
- Slim holders: inside diameter 59.3 mm, for a 58 mm slim can
- 8.4 mm drain hole in every cup
- Brands vary - measure your can and scale the file in your slicer if needed

EASY TO PRINT
- FDM printer, 0.4 mm nozzle, PETG recommended outdoors (PLA indoors)
- 0.2 mm layers, 2.4 mm walls, 15-20% infill
- No supports needed - prints upright as exported
- Every file is checked to be a closed (watertight) mesh before packaging
- The caddies are big prints (about 154 x 154 mm and 228 x 155 mm) - check your bed

GOOD TO KNOW
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- PLA softens in a hot car. Not intended for direct food contact.

LICENSE
Personal use included, and you may sell PHYSICAL items you print from these files. You may not resell, share or redistribute the digital files. All designs are original.

Questions? Message the shop."""
        return dict(title=title, tags=tags, description=desc, price_usd=4.99,
                    sale_hint="set base price $4.99, then run an Etsy Sale; comparable can-holder files list around $1.50-$6",
                    category="Craft Supplies & Tools > Patterns & How To (digital) / 3D printing files", materials="Digital STL files, PDF guide",
                    whats_in_the_files=[f"{len(cat)} STL files", "PDF guide + license"],
                    notes=["Do not use the word 'Koozie' (a registered trademark) in the title or tags."])

    return dict(
        slug="can_holders_stl", theme="forest", defs=s3.CAN_ITEMS, pdf_name="Print_Guide_and_License.pdf",
        zips=[("Can_Holders_STL.zip", "STL")],
        backdrops={"flat": "summer_flatlay", "table": "summer_bokeh"},
        cover=dict(big="8", l1="Can Holder", l2="STL bundle  -  standard + slim", elev=58, gap=10, scale=0.94, jitter=10,
                   badges=["Instant Download", "STL Files", "3D Print Ready", "Standard & Slim", "Sell Your Prints"], burst=["CLIP", "LOOPS"]),
        hero=dict(picks=[0, 2, 4], caption="Hold your drink anywhere", sub="Standard  •  slim  •  tall 16 oz", elev=26, fill=0.80),
        closeups=[dict(idx=1, caption="Clip loop for a carabiner", sub="9 mm hole at the base", az=40, elev=40),
                  dict(idx=6, caption="4-can caddy with handle", sub="Carry four standard cans", az=25, elev=45),
                  dict(idx=5, caption="Slim can cup-holder adapter", sub="73 mm outside diameter", az=-25, elev=45)],
        contents_title="8 holders included", contents_kicker="What's inside", contents_footer="Each is a separate STL file in millimetres.",
        sizes_title="Measured sizes",
        sizes_footer="Inside diameter 67.5 mm (standard 66.2 mm can) and 59.3 mm (slim 58 mm can). Measure your own can first.",
        print_rows=["Printer|Any FDM (0.4 mm nozzle)", "Material|PETG (outdoor) or PLA", "Layer height|0.2 mm", "Walls|2.4 mm (6 perimeters)",
                    "Infill|15-20%", "Supports|None needed", "Orientation|Upright, as exported"],
        print_footer="Every file is checked to be a closed, watertight mesh before it is packaged. PLA softens in a hot car; not for direct food contact.",
        files_rows=["STL files|8 (one per holder)", "Guide|PDF print guide + license", "Delivery|Instant digital download",
                    "Use|Personal use. Sell the PRINTED items freely.", "Not allowed|Reselling or sharing the digital files"],
        files_footer="Colours in the photos are for display - print in any colour.", guide=guide, copy=copy)


# ----------------------------------------------------------------------------- 3. KEYCHAINS
def keychains_spec() -> Dict:
    def guide(cat):
        names = ", ".join(e["name"] for e in cat)
        return [("Keychain Bundle - Print Guide", [
            f"Thank you for your purchase! This pack has {len(cat)} original keychains: {names}.",
            "# What is in the download",
            f"- Keychains_STL.zip: {len(cat)} STL files in millimetres. Keychains are 31-49 mm tall (see the measured sizes in the listing).",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PLA or PETG.  Nozzle 0.4 mm.  Layer height 0.2 mm.  Walls 3 perimeters.  Infill 100% (they are thin).  Supports: none.  Print flat as exported - about 6 keychains fit on one 220 mm bed in a few minutes each.",
            "Each keychain has a 5.2 mm ring hole - a standard split ring or lobster clasp fits.",
            "# Two-colour trick",
            "The base plate is 2.4 mm thick and a 1.2 mm raised border sits on top. Add a filament change at layer 13 (2.4 mm at 0.2 mm layers) for a two-colour look on any single-nozzle printer, or print the whole piece in one colour.",
        ]), license_pages(["Keychains are small parts - keep away from young children."])]

    def copy(dirs, cat):
        title = "Keychain STL Bundle, 12 Cute Printable Keychain Designs, Heart, Star, Paw, Cactus, Flat Keyring Files, 3D Print"
        tags = ["keychain stl", "3d print keychain", "keychain bundle", "keyring stl", "stl files", "3d printed gift", "cute keychain",
                "printable keychain", "craft fair idea", "small business 3d", "paw keychain", "stl bundle", "bag charm stl"]
        names = ", ".join(e["name"] for e in cat)
        desc = f"""12 original, print-ready keychain designs in one instant-download pack: {names}.

WHAT'S INCLUDED
- {len(cat)} keychain STL files, 31-49 mm tall
- 5.2 mm ring hole for a split ring or clasp
- PDF print guide + license

EASY TO PRINT
- Any FDM printer, 0.4 mm nozzle, PLA or PETG
- Flat on the bed, no supports - a few minutes per keychain
- 2.4 mm base with a 1.2 mm raised border: add a colour change at layer 13 for a two-colour look
- Every file is checked to be a closed (watertight) mesh before packaging

GOOD TO KNOW
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- Small parts - keep away from young children.

LICENSE
Personal use included, and you may sell PHYSICAL keychains you print from these files (craft fairs, your own shop). You may not resell, share or redistribute the digital files. All designs are original - no licensed characters.

Questions? Message the shop."""
        return dict(title=title, tags=tags, description=desc, price_usd=3.99,
                    sale_hint="set base price $3.99, then run an Etsy Sale; the keychain bundles in your screenshots sold around $1.50-$5",
                    category="Craft Supplies & Tools > Patterns & How To (digital) / 3D printing files", materials="Digital STL files, PDF guide",
                    whats_in_the_files=[f"{len(cat)} STL files", "PDF guide + license"], notes=[])

    return dict(
        slug="keychains_stl", theme="sunny", defs=kc.KEYCHAIN_ITEMS, pdf_name="Print_Guide_and_License.pdf",
        zips=[("Keychains_STL.zip", "STL")], colors=sl.PALETTE_BRIGHT,
        backdrops={"flat": "colorful_flatlay", "table": "colorful_flatlay"},
        cover=dict(big="12", l1="Keychain", l2="STL bundle  -  print-ready", elev=80, gap=6, repeat=2, scale=0.95, jitter=12,
                   badges=["Instant Download", "STL Files", "3D Print Ready", "Two-Colour Trick", "Sell Your Prints"], burst=["12", "DESIGNS"]),
        hero=dict(picks=[0, 1, 2, 3], caption="Print. Clip. Sell.", sub="12 cute keychain designs", elev=70, fill=0.86, dy=60, gap=10),
        closeups=[dict(idx=2, caption="Two-colour border trick", sub="Colour change at layer 13 - no AMS needed", az=0, elev=70),
                  dict(idx=8, caption="Chunky, print-friendly shapes", sub="2.4 mm base + 1.2 mm raised border", az=15, elev=62)],
        sheet=lambda cat: kc.sheet_items(), sheet_title="All 12 designs included", sheet_cols=4,
        sheet_footer="Each keychain has a 5.2 mm ring hole", sizes_title="Measured sizes",
        sizes_footer="Sizes measured from the actual STL files (mm).",
        print_rows=["Printer|Any FDM (0.4 mm nozzle)", "Material|PLA or PETG", "Layer height|0.2 mm", "Walls|3 perimeters",
                    "Infill|100% (thin parts)", "Supports|None needed", "Orientation|Flat, as exported"],
        print_footer="Every file is checked to be a closed, watertight mesh before it is packaged. A printable guide PDF is included.",
        files_rows=["STL files|12 (one per keychain)", "Guide|PDF print guide + license", "Delivery|Instant digital download",
                    "Use|Personal use. Sell the PRINTED keychains freely.", "Not allowed|Reselling or sharing the digital files"],
        files_footer="Colours in the photos are for display - print in any colour. Small parts: keep away from young children.",
        guide=guide, copy=copy, hero_closeup_notes=None)


# ----------------------------------------------------------------------------- 4. PLANTERS (STL + 3MF + GLB)
def planters_spec() -> Dict:
    designs = s3.PLANTER_SPECS
    defs = [(p["name"] + " Planter", (lambda p=p: s3.planter(p))) for p in designs] + \
           [(p["name"] + " Saucer", (lambda p=p: s3.saucer(p))) for p in designs]
    pot_colors = [[0.88, 0.30, 0.10], [0.05, 0.60, 0.55], [0.95, 0.75, 0.10], [0.85, 0.15, 0.45], [0.30, 0.25, 0.85],
                  [0.10, 0.65, 0.30], [0.95, 0.50, 0.15], [0.20, 0.45, 0.95]]

    def extras(rep, dirs, catalog):
        """3MF plates (pot + saucer) and coloured GLB (pot + saucer) per design."""
        with rep.stage("3MF plates + GLB models"):
            mf, gl = dirs["files"] / "3MF", dirs["files"] / "GLB"
            for d in (mf, gl):
                d.mkdir(parents=True, exist_ok=True)
                for old in d.glob("*"):
                    old.unlink()
            for i, p in enumerate(designs):
                pot, sau = s3.planter(p), s3.saucer(p)
                tag = f"{i + 1:02d}_{p['name'].replace(' ', '_')}"
                plate = trimesh.Scene()
                a, b = pot.copy(), sau.copy()
                b.apply_translation((a.extents[0] / 2 + b.extents[0] / 2 + 8, 0, 0))
                plate.add_geometry(a, node_name="planter")
                plate.add_geometry(b, node_name="saucer")
                plate.export(mf / f"{tag}_Planter_and_Saucer.3mf")
                col = pot_colors[i % len(pot_colors)]
                scene = trimesh.Scene()
                for nm, m, c in (("planter", pot, col), ("saucer", sau, [min(1, x * 0.8 + 0.1) for x in col])):
                    m2 = m.copy()
                    m2.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                        baseColorFactor=[c[0], c[1], c[2], 1.0], metallicFactor=0.0, roughnessFactor=0.55, name=f"{nm}_pla"))
                    scene.add_geometry(m2, node_name=nm)
                # glTF is y-up: rotate so the model stands up in Blender/AR viewers
                scene.apply_transform(trimesh.transformations.rotation_matrix(-3.14159265 / 2, (1, 0, 0)))
                scene.export(gl / f"{tag}.glb")
        return {"3mf_files": len(list(mf.glob("*.3mf"))), "glb_files": len(list(gl.glob("*.glb")))}

    def guide(cat):
        return [("Geometric Planter Pack - Print Guide", [
            "Thank you for your purchase! This pack has 8 faceted planter designs, each with a matching saucer, in three formats.",
            "# What is in the download",
            "- Geometric_Planters_STL.zip: 8 planters + 8 saucers (16 STL files, millimetres).",
            "- Geometric_Planters_3MF.zip: 8 plates, each with a planter and its saucer laid out together.",
            "- Geometric_Planters_GLB.zip: 8 coloured GLB models (planter + saucer) for previews, AR or Blender/Unity.",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PETG or PLA.  Nozzle 0.4 mm.  Layer height 0.2 mm.  Walls 2.4 mm (6 perimeters).  Infill 15%.  Supports: none - print upright as exported.  Slow, thin-layer prints give the cleanest facets.",
            "Each planter has a 7 mm drain hole in the floor; the saucer's recess is wider than the planter base.",
            "# Watering note",
            "FDM prints are not guaranteed waterproof. For wet soil use a small nursery pot inside the planter, or seal the print with a plant-safe sealant. The drain hole is meant for use with the saucer.",
            "# About the GLB files",
            "The GLB files are the same clean geometry as the STL files with a simple coloured material - handy for product previews, AR viewers and game or render scenes. They are not retopologised game assets.",
        ]), license_pages(["Printed plastic is not intended for direct food contact."])]

    def copy(dirs, cat):
        title = "Geometric Planter STL Pack, 8 Faceted Planters with Saucers, STL 3MF GLB Files, Succulent Pot, 3D Print Files"
        tags = ["planter stl", "succulent pot stl", "geometric planter", "3d print planter", "3mf files", "glb 3d model",
                "faceted vase stl", "plant pot 3d", "stl bundle", "3d print files", "desk planter", "low poly planter", "home decor stl"]
        names = ", ".join(p["name"] for p in designs)
        desc = f"""8 faceted, geometric planters with matching saucers - in STL, 3MF AND GLB formats. Instant download.

DESIGNS
{names}

WHAT'S INCLUDED
- 8 planter STL files + 8 saucer STL files
- 8 3MF plates (planter + saucer together)
- 8 coloured GLB models (planter + saucer) for previews, AR, Blender or Unity
- PDF print guide + license

EASY TO PRINT
- Any FDM printer, 0.4 mm nozzle, PETG or PLA
- 0.2 mm layers, 2.4 mm walls, 15% infill, no supports - print upright as exported
- 7 mm drain hole in every planter; saucers included
- Every file is checked to be a closed (watertight) mesh before packaging

GOOD TO KNOW
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- FDM prints are not guaranteed waterproof: use a small nursery pot inside, or a plant-safe sealant, for wet soil.
- The GLB files are clean geometry with a simple coloured material, not game-ready retopologised assets.

LICENSE
Personal use included, and you may sell PHYSICAL planters you print from these files. You may not resell, share or redistribute the digital files. All designs are original.

Questions? Message the shop."""
        return dict(title=title, tags=tags, description=desc, price_usd=5.99,
                    sale_hint="set base price $5.99, then run an Etsy Sale; GLB/3MF extras justify a slightly higher price than STL-only bundles",
                    category="Craft Supplies & Tools > Patterns & How To (digital) / 3D printing files", materials="Digital STL, 3MF and GLB files, PDF guide",
                    whats_in_the_files=["16 STL files", "8 3MF plates", "8 GLB models", "PDF guide + license"],
                    notes=["Etsy allows 5 files per listing - this one uses 4 (3 zips + PDF)."])

    return dict(
        slug="geometric_planters_stl_3mf_glb", theme="forest", defs=defs, extras=extras, colors=pot_colors, pdf_name="Print_Guide_and_License.pdf",
        zips=[("Geometric_Planters_STL.zip", "STL"), ("Geometric_Planters_3MF.zip", "3MF"), ("Geometric_Planters_GLB.zip", "GLB")],
        backdrops={"flat": "plants_flatlay", "table": "plants_bokeh"},
        cover=dict(big="8", l1="Geometric Planter", l2="STL  -  3MF  -  GLB  -  with saucers", elev=60, gap=8, scale=0.94, jitter=6,
                   badges=["Instant Download", "STL 3MF GLB", "3D Print Ready", "Saucers Included", "Sell Your Prints"], burst=["+ SAUCERS"]),
        hero=dict(picks=[2, 3, 4], caption="Faceted planters you can print", sub="Twisted hex  •  twisted square  •  twisted triangle", elev=24, fill=0.82),
        closeups=[dict(idx=0, caption="Planter + matching saucer", sub="7 mm drain hole in the floor", az=30, elev=40),
                  dict(idx=6, caption="Tall hex vase", sub="96 mm tall", az=-25, elev=35),
                  dict(idx=7, caption="Wide faceted bowl", sub="120 mm wide", az=20, elev=50)],
        contents_title="8 planters + 8 saucers", contents_kicker="What's inside",
        contents_footer="Provided as STL (print), 3MF (plates) and GLB (3D preview).",
        sizes_title="Measured sizes", sizes_footer="Sizes measured from the actual STL files (mm).",
        print_rows=["Printer|Any FDM (0.4 mm nozzle)", "Material|PETG or PLA", "Layer height|0.2 mm", "Walls|2.4 mm (6 perimeters)",
                    "Infill|15%", "Supports|None needed", "Orientation|Upright, as exported"],
        print_footer="Every file is checked to be a closed, watertight mesh. FDM prints are not guaranteed waterproof - use a nursery pot liner for wet soil.",
        files_rows=["STL|16 files (8 planters + 8 saucers)", "3MF|8 plates (planter + saucer)", "GLB|8 coloured 3D models",
                    "Guide|PDF print guide + license", "Delivery|Instant digital download", "Use|Personal use. Sell the PRINTED items freely."],
        files_footer="Colours in the photos are for display - print in any colour. GLB = clean geometry + simple material, not game-ready retopology.",
        guide=guide, copy=copy)


SPECS: Dict[str, Callable[[], Dict]] = {"desk": desk_spec, "cans": cans_spec, "keychains": keychains_spec, "planters": planters_spec}

if __name__ == "__main__":
    which = sys.argv[1:] or ["all"]
    keys = list(SPECS) if which == ["all"] else which
    results = {}
    for k in keys:
        results[k] = run_spec(SPECS[k]())
        print(json.dumps({k: results[k]}, indent=2), flush=True)
