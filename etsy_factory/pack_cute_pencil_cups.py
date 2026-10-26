"""Listing: Cute Animal Pencil Cup STL pack (8 kawaii desk buddies, STL + 3MF + GLB).

Geometry lives in shapes_cute.py (already validated). This module only describes the listing (spec dict) and lets
listings_stl.run_spec do the rest: validate + export STL -> headless Blender renders -> ComfyUI backdrops -> listing images
-> guide PDF -> zips -> listing copy + Etsy limit validation.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.pack_cute_pencil_cups
"""
from __future__ import annotations

import json
import sys
from typing import Dict

sys.path.insert(0, r"F:\WORKHORSE")

import trimesh

from etsy_factory import shapes_cute as sc
from etsy_factory.listings_stl import license_pages, run_spec

# bright cup colours, one per animal in ITEMS order: cat, bear, bunny, panda, pig, owl, chick, dino
COLORS = [[1.0, 0.55, 0.12], [0.55, 0.32, 0.16], [0.97, 0.62, 0.78], [0.94, 0.94, 0.92],
          [0.98, 0.45, 0.60], [0.55, 0.40, 0.85], [1.0, 0.82, 0.10], [0.10, 0.70, 0.45]]


def spec() -> Dict:
    items = sc.ITEMS
    n = len(items)
    names = ", ".join(nm.replace(" Pencil Cup", "") for nm, _ in items)

    def extras(rep, dirs, catalog):
        """One 3MF plate and one coloured GLB per cup (same geometry as the STL)."""
        with rep.stage("3MF plates + GLB models"):
            mf, gl = dirs["files"] / "3MF", dirs["files"] / "GLB"
            for d in (mf, gl):
                d.mkdir(parents=True, exist_ok=True)
                for old in d.glob("*"):
                    old.unlink()
            for i, (nm, fn) in enumerate(items):
                mesh = fn()
                tag = f"{i + 1:02d}_{nm.replace(' ', '_')}"
                plate = trimesh.Scene()
                plate.add_geometry(mesh.copy(), node_name="pencil_cup")
                plate.export(mf / f"{tag}.3mf")
                c = COLORS[i % len(COLORS)]
                m2 = mesh.copy()
                m2.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                    baseColorFactor=[c[0], c[1], c[2], 1.0], metallicFactor=0.0, roughnessFactor=0.55, name="pla"))
                scene = trimesh.Scene()
                scene.add_geometry(m2, node_name="pencil_cup")
                scene.apply_transform(trimesh.transformations.rotation_matrix(-3.14159265 / 2, (1, 0, 0)))   # glTF is y-up
                scene.export(gl / f"{tag}.glb")
        return {"3mf_files": len(list(mf.glob("*.3mf"))), "glb_files": len(list(gl.glob("*.glb")))}

    def guide(cat):
        return [("Cute Animal Pencil Cups - Print Guide", [
            f"Thank you for your purchase! This pack has {n} original animal pencil cups: {names}.",
            "# What is in the download",
            f"- Cute_Animal_Pencil_Cups_STL.zip: {n} STL files (millimetres).",
            f"- Cute_Animal_Pencil_Cups_3MF.zip: {n} 3MF files, one cup per file.",
            f"- Cute_Animal_Pencil_Cups_GLB.zip: {n} coloured GLB models for previews, AR or Blender/Unity.",
            "- This guide (PDF) and the license.",
            "# Recommended print settings",
            "Material: PLA or PETG.  Nozzle 0.4 mm.  Layer height 0.2 mm.  Walls 3 perimeters (1.2 mm).  Infill 15%.  Supports: none.  Brim: optional.",
            "Print each cup upright, exactly as exported: the open pocket faces up and the animal face is on the front wall. The face is a raised relief only "
            "2.2 mm high (plus a 1.2 mm highlight layer), so it prints cleanly without supports.",
            "# Colour tips",
            "A single colour looks great. For a two-colour face add filament changes at the layer where the raised face starts, or paint the eyes and "
            "cheeks with acrylic paint after printing.",
            "# Using the cup",
            "The pocket is about 40 mm wide - it holds pens, pencils, markers, makeup brushes and small tools. The cups are for dry desk use.",
        ]), license_pages(["Printed plastic is not intended for direct food contact. Small raised details - keep away from very young children."])]

    def copy(dirs, cat):
        title = f"Cute Animal Pencil Holder STL, {n} Kawaii Desk Organizer Cups, Cat Bear Bunny Panda Pig Owl, STL 3MF GLB, 3D Print Files"
        tags = ["pencil holder stl", "pencil cup stl", "animal pencil holder", "kawaii desk stl", "3d print files", "desk organizer stl",
                "3mf files", "glb 3d model", "cute desk decor", "stl bundle", "panda stl", "cat stl", "printable gift"]
        sizes = "; ".join(f"{e['name'].replace(' Pencil Cup', '')} {e['size_mm'][0]:.0f} x {e['size_mm'][2]:.0f} mm" for e in cat)
        desc = f"""{n} adorable animal pencil cups you can 3D print at home - {names}. Instant download in STL, 3MF AND GLB formats.

WHAT'S INCLUDED
- {n} STL files (one pencil cup per animal)
- {n} 3MF files
- {n} coloured GLB models for previews, AR, Blender or Unity
- PDF print guide + license

EASY TO PRINT
- Any FDM printer, 0.4 mm nozzle, PLA or PETG
- 0.2 mm layers, 3 perimeters, 15% infill, no supports - print upright as exported
- Raised 2.2 mm face relief, so the face prints crisp without supports
- Every file is checked to be a closed (watertight) mesh before packaging

SIZES (width x height, measured from the files)
{sizes}
Each cup has a pocket about 40 mm wide for pens, pencils, markers and brushes.

GOOD TO KNOW
- DIGITAL DOWNLOAD ONLY - no physical item is shipped. Photos are 3D renders of the actual files on AI-generated backdrops.
- Not for food contact. Raised details are small - keep away from very young children.
- The GLB files are clean geometry with a simple coloured material, not game-ready retopologised assets.
- Colours in the photos are for display - print in any colour you like.

LICENSE
Personal use included, and you may sell PHYSICAL cups you print from these files (craft fairs, your own shop). You may not resell, share or redistribute the digital files. All designs are original - no licensed characters.

DESIGN & CREATION TRANSPARENCY
- Original 3D designs created by CraftyMyia using AI-assisted 3D concept modeling and procedural CAD engineering in Blender (watertight voxel remeshing, planar base leveling, and manifold verification).
- Listing photos show 3D renders and AI-assisted studio scene backdrops for display.

COMPATIBILITY & TRADEMARK NOTICE
- Compatible with Bambu Lab, Prusa, Creality, Anycubic, and standard FDM slicers. All printer and slicer brand names are trademarks of their respective owners; CraftyMyia is an independent studio and is not affiliated with or endorsed by them.

Questions? Message the shop."""
        return dict(title=title, tags=tags, description=desc, price_usd=4.99,
                    sale_hint="set base price $4.99, then run an Etsy Sale so the strike-through shows",
                    category="Craft Supplies & Tools > Patterns & How To (digital) / 3D printing files",
                    materials="Digital STL, 3MF and GLB files, PDF guide",
                    whats_in_the_files=[f"{n} STL files", f"{n} 3MF files", f"{n} GLB models", "PDF guide + license"],
                    notes=["Etsy allows 5 files per listing - this one uses 4 (3 zips + PDF)."])

    return dict(
        slug="cute_animal_pencil_cups_stl_3mf_glb", theme="sunny", defs=items, extras=extras, colors=COLORS, pdf_name="Print_Guide_and_License.pdf",
        zips=[("Cute_Animal_Pencil_Cups_STL.zip", "STL"), ("Cute_Animal_Pencil_Cups_3MF.zip", "3MF"), ("Cute_Animal_Pencil_Cups_GLB.zip", "GLB")],
        backdrops={"flat": "colorful_flatlay", "table": "desk_table"},
        cover=dict(big=str(n), l1="Cute Animal Pencil Cups", l2="STL  -  3MF  -  GLB  -  print-ready", elev=46, gap=10, repeat=1, scale=0.95, jitter=4, open=True,
                   badges=["Instant Download", "STL 3MF GLB", "3D Print Ready", "No Supports", "Sell Your Prints"], burst=[str(n), "ANIMALS"]),
        hero=dict(picks=[0, 3, 5], caption="Print your own kawaii desk buddies", sub="Cat  *  Panda  *  Owl  *  and 5 more", elev=20, fill=0.84),
        closeups=[dict(idx=3, caption="Crisp raised face - no supports", sub="2.2 mm relief prints standing up", az=-8, elev=22),
                  dict(idx=1, caption="Fits pens, pencils and brushes", sub="About 40 mm wide pocket", az=18, elev=30),
                  dict(idx=2, caption="Pastel kawaii desk decor", sub="Bunny cup - 3MF and GLB included", az=-15, elev=26),
                  dict(idx=7, caption="Fun gift for kids & crafters", sub="Cute Dino cup - sturdy 1.2 mm walls", az=22, elev=28)],
        contents_title=f"{n} animal pencil cups", contents_kicker="What's inside",
        contents_footer="Provided as STL (print), 3MF and GLB (3D preview).",
        sizes_title="Measured sizes", sizes_footer="Sizes measured from the actual STL files (mm).",
        print_rows=["Printer|Any FDM (0.4 mm nozzle)", "Material|PLA or PETG", "Layer height|0.2 mm", "Walls|3 perimeters (1.2 mm)",
                    "Infill|15%", "Supports|None needed", "Orientation|Upright, as exported"],
        print_footer="Every file is checked to be a closed, watertight mesh before it is packaged. A printable guide PDF is included.",
        files_rows=[f"STL|{n} files (one per animal)", f"3MF|{n} files", f"GLB|{n} coloured 3D models", "Guide|PDF print guide + license",
                    "Delivery|Instant digital download", "Use|Personal use. Sell the PRINTED cups freely.", "Not allowed|Reselling or sharing the digital files"],
        files_footer="Colours in the photos are for display - print in any colour. GLB = clean geometry + simple material, not game-ready retopology.",
        guide=guide, copy=copy)


if __name__ == "__main__":
    print(json.dumps(run_spec(spec()), indent=2))
