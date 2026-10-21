import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import kit, listing

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_listings\desk_organizers_stl")
STL_DIR = ROOT / "files" / "STL"
UPLOAD_DIR = ROOT / "etsy_upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 1. Package Clean Zip under 20MB limit
zip_name = "Desk_Organizers_STL.zip"
zp = UPLOAD_DIR / zip_name
if zp.exists():
    zp.unlink()

stls = sorted([f.name for f in STL_DIR.glob("*.stl")])
assert len(stls) == 10, f"Expected 10 STLs, got {len(stls)}"

with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for sname in stls:
        sp = STL_DIR / sname
        zf.write(sp, arcname=sname)

size_mb = zp.stat().st_size / 1e6
print(f"Created {zip_name}: {len(stls)} STLs ({size_mb:.2f} MB)")
assert size_mb <= 20.0, f"{zip_name} exceeds Etsy 20MB limit ({size_mb:.2f} MB)"

# 2. PDF Guide via kit.pdf_guide
pdf_path = UPLOAD_DIR / "Print_Guide_and_License.pdf"
pages = [
    ("Desk Organizers STL Bundle - Print Guide", [
        "Thank you for your purchase! This collection includes 10 functional, modular 3D printable desk organizers engineered for 100% support-free printing, watertight topology, and clean modern workspace utility.",
        "# What is in your download",
        "- Desk_Organizers_STL.zip: 10 Watertight STL Files.",
        "- Printable PDF setup guide and lifetime commercial print license.",
        "# Included 3D Models (100% Watertight & Slicer Tested)",
        "01. Round Pen Cup (80 x 80 x 95 mm) - Fluted lip, heavy base, fits 20+ pens and pencils.",
        "02. Hex Pen Cup (94 x 82 x 95 mm) - Faceted hexagonal walls, modern geometric aesthetic.",
        "03. Square Pencil Holder (80 x 80 x 100 mm) - 100mm deep minimalist block for tall brushes & markers.",
        "04. Ergonomic Phone Stand (100 x 70 x 94 mm) - 18mm case-friendly slot, angled 65-deg view, cable cut-thru.",
        "05. Cable Clips x4 Bundle (142 x 25 x 14 mm) - 4 snap wire loops with flat tape-on mounting backs.",
        "06. Business Card Holder (98 x 38 x 20 mm) - 92mm display slot holds 40+ standard business cards.",
        "07. Sticky Note Tray (86 x 86 x 22 mm) - Precision inner fit for standard 3x3in Post-it pads with finger notch.",
        "08. 4-Compartment Desk Tray (184 x 124 x 42 mm) - Modular caddy for flash drives, erasers & paper clips.",
        "09. Pen & Pencil Tray (196 x 46 x 24 mm) - Long horizontal tray fits Apple Pencils, styluses & pens.",
        "10. Desk Valet Dish (80 x 80 x 16 mm) - Rounded catchall bowl for keys, coins, rings & small accessories.",
        "# Recommended Slicer Settings",
        "- Nozzle: 0.4 mm",
        "- Layer Height: 0.20 mm standard (or 0.28 mm for fast draft)",
        "- Walls / Perimeters: 4 to 6 walls (2.4 mm) for rigid desk durability",
        "- Infill: 15% - 20% Gyroid or Grid pattern",
        "- Supports: 0% NONE needed - 100% self-supporting geometry",
        "- Materials: Matte PLA recommended for aesthetics; PETG for extra toughness"
    ]),
    ("Commercial Print License & Terms", [
        "# Commercial Use Rights",
        "- You have full commercial permission to 3D print and sell physical prints of all 10 designs.",
        "- Unlimited physical sales volume with zero recurring royalty fees.",
        "- Ideal for Etsy shops, craft fairs, local markets, and gift boutiques.",
        "# Digital Restrictions",
        "- You may NOT resell, share, redistribute, or remix the digital 3D model files (STL).",
        "- Digital copyright remains exclusively with WORKHORSE.",
        "# Customer Support",
        "- If you have any questions or need custom slicing advice, please contact our shop."
    ])
]
kit.pdf_guide(pdf_path, pages)
pdf_mb = pdf_path.stat().st_size / 1e6
print(f"Created {pdf_path.name} ({pdf_mb:.2f} MB)")

upload_files = [
    {"name": zip_name, "mb": round(size_mb, 2)},
    {"name": pdf_path.name, "mb": round(pdf_mb, 2)}
]

images_in_upload_order = [
    "01_cover.jpg",
    "02_cover_grid.jpg",
    "03_preview_1.jpg",
    "04_preview_2.jpg",
    "05_mockup_cluster.jpg",
    "06_mockup_phone_stand.jpg",
    "07_mockup_pen_cups.jpg",
    "08_specs_settings.jpg",
    "09_whats_included.jpg",
    "10_license.jpg"
]

# Update listing.json
lp = ROOT / "listing.json"
with open(lp, "r", encoding="utf-8") as f:
    ld = json.load(f)

ld["images_in_upload_order"] = images_in_upload_order
ld["upload_files"] = upload_files

with open(lp, "w", encoding="utf-8") as f:
    json.dump(ld, f, indent=2)

print("Updated listing.json images and upload_files.")

# Validate
title = ld["title"]
tags = ld["tags"]
images = [ROOT / "images" / img for img in images_in_upload_order]
uploads = [UPLOAD_DIR / u["name"] for u in upload_files]

res = listing.validate(title, tags, images, uploads)
print("Desk Organizers Validation problems:", res)
assert len(res) == 0, f"Validation problems found: {res}"
print("Desk Organizers 100% VALIDATED - 0 ERRORS!")
