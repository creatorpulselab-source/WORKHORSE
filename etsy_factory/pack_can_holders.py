import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import kit, listing

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_listings\can_holders_stl")
STL_DIR = ROOT / "files" / "STL"
UPLOAD_DIR = ROOT / "etsy_upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 1. Package Clean Zip under 20MB limit
zip_name = "Can_Holders_STL.zip"
zp = UPLOAD_DIR / zip_name
if zp.exists():
    zp.unlink()

stls = sorted([f.name for f in STL_DIR.glob("*.stl")])
assert len(stls) == 8, f"Expected 8 STLs, got {len(stls)}"

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
    ("Can & Drink Holders STL Bundle - Print Guide", [
        "Thank you for your purchase! This collection includes 8 functional, original 3D printable can holders, car adapters, and cup carriers engineered for support-free printing and everyday durability.",
        "# What is in your download",
        "- Can_Holders_STL.zip: 8 Watertight STL Files.",
        "- Printable PDF setup guide and lifetime commercial print license.",
        "# Included 3D Models (100% Watertight & Slicer Tested)",
        "01. QuadGrip 4-Cup Drink Caddy (189 x 189 x 165 mm) - Fits coffee cups and takeout drinks with bridge carry handle.",
        "02. DuoCaddy Twin Carrier (162 x 76 x 138 mm) - Compact 2-can carrier with ergonomic center finger loop.",
        "03. HexaCool Can Cooler (79 x 79 x 98 mm) - Fits standard 12oz cans with diamond tactile knurling.",
        "04. SlimGrip Can Cooler (68 x 67 x 105 mm) - Fits slim 12oz seltzer cans with recessed grip ribs.",
        "05. TrailLock Holster (97 x 80 x 98 mm) - Adventure holster with reinforced carabiner clip loop.",
        "06. DualDrive Car Expander (90 x 90 x 127 mm) - Stepped base converts 68mm car console to 88mm.",
        "07. Titan 16oz Chiller (78 x 78 x 126 mm) - Tallboy cooler with thermal horizontal ribbing.",
        "08. FlipBase Stabilizer (112 x 112 x 42 mm) - Wide anti-tip desk coaster dock with drain slots.",
        "# Recommended Slicer Settings",
        "- Nozzle: 0.4 mm",
        "- Layer Height: 0.20 mm (or 0.28 mm for fast prints)",
        "- Walls / Perimeters: 4 to 6 walls (2.4 mm) for rugged rigidity",
        "- Infill: 15% - 20% Gyroid or Grid",
        "- Supports: 0% NONE needed - 100% self-supporting geometry",
        "- Materials: PETG recommended for automotive/outdoor use; PLA for indoor desks"
    ]),
    ("Commercial Print License & Terms", [
        "# Commercial Use Rights",
        "- You have full commercial permission to 3D print and sell physical prints of all 8 designs.",
        "- Unlimited physical sales volume with zero recurring royalty fees.",
        "- Ideal for Etsy shops, craft fairs, farmers markets, and local retail.",
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
    "06_mockup_coolers.jpg",
    "07_mockup_caddy.jpg",
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
print("Can Holders Validation problems:", res)
assert len(res) == 0, f"Validation problems found: {res}"
print("Can Holders 100% VALIDATED - 0 ERRORS!")
