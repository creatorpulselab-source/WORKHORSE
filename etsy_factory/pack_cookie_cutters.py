"""Package and validate Christmas Cookie Cutters STL + 3MF Listing."""
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import kit, listing

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_listings\christmas_cookie_cutters_stl")
FILES_DIR = ROOT / "files"
UPLOAD_DIR = ROOT / "etsy_upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 1. Package Clean STL Zip
zip_stl = "Christmas_Cookie_Cutters_STL.zip"
zp_stl = UPLOAD_DIR / zip_stl
stls = sorted([f.name for f in (FILES_DIR / "STL").glob("*.stl")])
assert len(stls) == 30, f"Expected 30 STLs, got {len(stls)}"

with zipfile.ZipFile(zp_stl, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for sname in stls:
        sp = FILES_DIR / "STL" / sname
        zf.write(sp, arcname=sname)
size_stl_mb = zp_stl.stat().st_size / 1e6
print(f"Created {zip_stl}: {len(stls)} STLs ({size_stl_mb:.2f} MB)")
assert size_stl_mb <= 20.0

# 2. Package Clean 3MF Zip
zip_3mf = "Christmas_Cookie_Cutters_3MF.zip"
zp_3mf = UPLOAD_DIR / zip_3mf
mfs = sorted([f.name for f in (FILES_DIR / "3MF").glob("*.3mf")])
assert len(mfs) == 10, f"Expected 10 3MFs, got {len(mfs)}"

with zipfile.ZipFile(zp_3mf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for mname in mfs:
        mp = FILES_DIR / "3MF" / mname
        zf.write(mp, arcname=mname)
size_3mf_mb = zp_3mf.stat().st_size / 1e6
print(f"Created {zip_3mf}: {len(mfs)} 3MFs ({size_3mf_mb:.2f} MB)")
assert size_3mf_mb <= 20.0

# 3. PDF Guide
pdf_path = UPLOAD_DIR / "Print_Guide_and_License.pdf"
pages = [
    ("Christmas Cookie Cutters - Print Guide", [
        "Thank you for your purchase! This collection includes 10 original holiday shapes, each provided in two sizes (60mm and 80mm nominal) plus a matching press plate for clean dough and clay release.",
        "# What is in your download",
        "- Christmas_Cookie_Cutters_STL.zip: 30 Watertight STL Files (20 cutters + 10 press plates).",
        "- Christmas_Cookie_Cutters_3MF.zip: 10 Pre-arranged multi-part 3MF plates for Bambu Studio / OrcaSlicer.",
        "- Printable PDF setup guide and lifetime commercial print license.",
        "# Included Holiday Designs (100% Watertight & Slicer Tested)",
        "01. Christmas Tree (60mm & 80mm + Press Plate)",
        "02. Golden Star (60mm & 80mm + Press Plate)",
        "03. Intricate Snowflake (60mm & 80mm + Press Plate)",
        "04. Gingerbread Man (60mm & 80mm + Press Plate)",
        "05. Holiday Candy Cane (60mm & 80mm + Press Plate)",
        "06. Bauble Ornament (60mm & 80mm + Press Plate)",
        "07. Cozy Mitten (60mm & 80mm + Press Plate)",
        "08. Holiday Stocking (60mm & 80mm + Press Plate)",
        "09. Jingle Bell (60mm & 80mm + Press Plate)",
        "10. Winter Snowman (60mm & 80mm + Press Plate)",
        "# Recommended Slicer Settings",
        "- Nozzle: 0.4 mm",
        "- Layer Height: 0.20 mm standard (or 0.16 mm for sharpest edge taper)",
        "- Walls / Perimeters: 3 to 4 walls (1.2 - 1.6 mm)",
        "- Infill: 15% - 20% Gyroid or Grid",
        "- Orientation: Print flat with wide comfort grip flange down on build plate",
        "- Supports: 0% NONE needed - 100% self-supporting geometry"
    ]),
    ("Food Safety & Commercial Print License", [
        "# Care and Food Contact",
        "- 3D-printed plastic is porous and not certified food-safe. Ideal for play dough, polymer clay and fondant.",
        "- If used with cookie dough: print with food-safe filament, keep contact brief, hand-wash with warm soapy water (never dishwasher), and do not microwave or bake.",
        "# Commercial Print Rights",
        "- You have full commercial permission to 3D print and sell physical cutters made with these files.",
        "- Unlimited physical sales volume with zero recurring royalty fees.",
        "- Ideal for Etsy shops, craft fairs, bakeries, and holiday markets.",
        "# Digital Restrictions",
        "- You may NOT resell, share, redistribute, or remix the digital 3D model files (STL, 3MF).",
        "- Digital copyright remains exclusively with WORKHORSE."
    ])
]
kit.pdf_guide(pdf_path, pages, theme="christmas")
pdf_mb = pdf_path.stat().st_size / 1e6
print(f"Created {pdf_path.name} ({pdf_mb:.2f} MB)")

upload_files = [
    {"name": zip_stl, "mb": round(size_stl_mb, 2)},
    {"name": zip_3mf, "mb": round(size_3mf_mb, 2)},
    {"name": pdf_path.name, "mb": round(pdf_mb, 2)}
]

images_in_upload_order = [
    "01_cover.jpg",
    "02_cover_grid.jpg",
    "03_preview_1.jpg",
    "04_preview_2.jpg",
    "05_mockup_cluster.jpg",
    "06_mockup_press_action.jpg",
    "07_mockup_two_sizes.jpg",
    "08_specs_settings.jpg",
    "09_whats_included.jpg",
    "10_license.jpg"
]

# Update listing.json
lp = ROOT / "listing.json"
with open(lp, "r", encoding="utf-8") as f:
    ld = json.load(f)

ld["upload_files"] = upload_files
ld["images_in_upload_order"] = images_in_upload_order

with open(lp, "w", encoding="utf-8") as f:
    json.dump(ld, f, indent=2)

print("Updated listing.json upload_files and images.")

# Validate
title = ld["title"]
tags = ld["tags"]
images = [ROOT / "images" / img for img in images_in_upload_order]
uploads = [UPLOAD_DIR / u["name"] for u in upload_files]

res = listing.validate(title, tags, images, uploads)
print("Christmas Cookie Cutters Validation problems:", res)
assert len(res) == 0, f"Validation problems found: {res}"
print("Christmas Cookie Cutters 100% VALIDATED - 0 ERRORS!")
