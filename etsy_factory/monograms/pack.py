"""Pack generator for Cute Floral Split Monogram SVG Bundle.

Generates:
- 26 Split Monograms (A-Z)
- 26 Full Botanical Monograms (A-Z)
- 10 Split Monograms (0-9)
- 10 Full Botanical Monograms (0-9)
- 2 Monograms (&)
Total: 74 designs x (SVG, DXF, EPS, PNG 300 DPI) + 2-layer SVGs + multi-page PDF Guide.
Produces exactly 5 Etsy upload files, each <= 20 MB.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

from PIL import Image, ImageDraw, ImageFont

from etsy_factory.common import ETSY_MAX_FILE_BYTES, listing_dirs
from etsy_factory.monograms import shapes as MS
from etsy_factory.typo import export as X

SLUG = "cute_floral_monogram_alphabet_svg_cut_files"
DPI = 300
WIDTH_IN = 6.0       # Standard 6-inch default import width for Cricut Design Space


def char_slug(char: str) -> str:
    if char == "&":
        return "Ampersand"
    if char.isdigit():
        return f"Number_{char}"
    return f"Letter_{char}"


def generate_all_monograms(files_dir: Path, thumbs_dir: Path) -> Dict:
    """Builds all vector files, DXFs, EPSs, PNGs, and thumbnails."""
    split_svg_dir = files_dir / "01_Split_Monograms" / "SVG"
    split_2layer_dir = files_dir / "01_Split_Monograms" / "SVG_2Layer"
    split_dxf_dir = files_dir / "01_Split_Monograms" / "DXF"
    split_eps_dir = files_dir / "01_Split_Monograms" / "EPS"
    split_png_dir = files_dir / "01_Split_Monograms" / "PNG_300DPI"

    full_svg_dir = files_dir / "02_Full_Botanical" / "SVG"
    full_dxf_dir = files_dir / "02_Full_Botanical" / "DXF"
    full_eps_dir = files_dir / "02_Full_Botanical" / "EPS"
    full_png_dir = files_dir / "02_Full_Botanical" / "PNG_300DPI"

    all_dirs = [
        split_svg_dir, split_2layer_dir, split_dxf_dir, split_eps_dir, split_png_dir,
        full_svg_dir, full_dxf_dir, full_eps_dir, full_png_dir, thumbs_dir
    ]
    for d in all_dirs:
        d.mkdir(parents=True, exist_ok=True)

    catalog = {"characters": [], "total_designs": len(MS.CHARACTERS) * 2}

    print(f"Generating vectors for {len(MS.CHARACTERS)} characters (Split + Full Botanical)...")
    for idx, char in enumerate(MS.CHARACTERS, 1):
        c_slug = char_slug(char)

        # -------------------------------------------------------------
        # 1. SPLIT MONOGRAM
        # -------------------------------------------------------------
        split_g = MS.build_split_monogram(char)
        split_base, split_bot = MS.build_split_monogram_layers(char)

        # Single piece welded SVG
        s_svg_p = split_svg_dir / f"{c_slug}_Split.svg"
        X.write_svg(s_svg_p, [("monogram", split_g, "#222222")], width_in=WIDTH_IN, title=f"{c_slug} Split Monogram")

        # 2-Layer SVG (letter and botanicals separated)
        s_2layer_p = split_2layer_dir / f"{c_slug}_Split_2Layer.svg"
        X.write_svg(s_2layer_p, [
            ("letter_and_bars", split_base, "#222222"),
            ("botanicals", split_bot, "#4A6B53")
        ], width_in=WIDTH_IN, title=f"{c_slug} Split 2-Layer Monogram")

        # DXF & EPS
        s_dxf_p = split_dxf_dir / f"{c_slug}_Split.dxf"
        X.write_dxf(s_dxf_p, split_g)
        s_eps_p = split_eps_dir / f"{c_slug}_Split.eps"
        X.write_eps(s_eps_p, split_g)

        # 300 DPI Transparent PNG
        s_png_p = split_png_dir / f"{c_slug}_Split.png"
        X.write_png(s_png_p, [(split_g, (34, 34, 34))], width_px=3600, dpi=DPI)

        # Fast thumbnail for listing assembly
        th_split = thumbs_dir / f"{c_slug}_split_th.png"
        th_img = Image.open(s_png_p)
        th_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        th_img.save(th_split, optimize=True)

        # -------------------------------------------------------------
        # 2. FULL BOTANICAL MONOGRAM
        # -------------------------------------------------------------
        full_g = MS.build_full_monogram(char)

        # Single piece welded SVG
        f_svg_p = full_svg_dir / f"{c_slug}_Botanical.svg"
        X.write_svg(f_svg_p, [("monogram", full_g, "#222222")], width_in=WIDTH_IN, title=f"{c_slug} Botanical Monogram")

        # DXF & EPS
        f_dxf_p = full_dxf_dir / f"{c_slug}_Botanical.dxf"
        X.write_dxf(f_dxf_p, full_g)
        f_eps_p = full_eps_dir / f"{c_slug}_Botanical.eps"
        X.write_eps(f_eps_p, full_g)

        # 300 DPI Transparent PNG
        f_png_p = full_png_dir / f"{c_slug}_Botanical.png"
        X.write_png(f_png_p, [(full_g, (34, 34, 34))], width_px=3600, dpi=DPI)

        # Fast thumbnail
        th_full = thumbs_dir / f"{c_slug}_botanical_th.png"
        th_img_f = Image.open(f_png_p)
        th_img_f.thumbnail((800, 800), Image.Resampling.LANCZOS)
        th_img_f.save(th_full, optimize=True)

        catalog["characters"].append({
            "character": char,
            "slug": c_slug,
            "split_svg": s_svg_p.name,
            "split_png": s_png_p.name,
            "full_svg": f_svg_p.name,
            "full_png": f_png_p.name,
        })
        if idx % 10 == 0 or idx == len(MS.CHARACTERS):
            print(f"  Processed {idx}/{len(MS.CHARACTERS)} characters...")

    return catalog


def build_guide_pdf(guide_path: Path, thumbs_dir: Path) -> Path:
    """Builds a 3-page comprehensive PDF guide: Visual Letter Index, Cricut Guide, Font Pairings & License."""
    W, H = 2550, 3300   # US Letter @ 300 DPI
    DPI = 300

    def draw_top_banner(draw: ImageDraw.ImageDraw, title: str, subtitle: str):
        draw.rectangle([0, 0, W, 280], fill=(42, 60, 48))      # Elegant forest green banner
        f_title = ImageFont.load_default()
        try:
            f_title = ImageFont.truetype(str(MS.FONT_PATH), 90)
            f_sub = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 40)
        except Exception:
            f_sub = ImageFont.load_default()
        draw.text((W // 2, 90), title, fill=(255, 255, 255), font=f_title, anchor="mm")
        draw.text((W // 2, 190), subtitle, fill=(210, 230, 215), font=f_sub, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 1: Visual Alphabet Index
    # -------------------------------------------------------------
    p1 = Image.new("RGB", (W, H), (255, 255, 255))
    d1 = ImageDraw.Draw(p1)
    draw_top_banner(d1, "FLORAL MONOGRAM ALPHABET", "Complete Visual Index - Letters A-Z, Numbers 0-9 & Ampersand")

    # Grid of characters: 6 columns x 7 rows
    cols, rows = 6, 7
    gw = (W - 200) // cols
    gh = (H - 420) // rows
    ox = 100
    oy = 320

    f_lbl = ImageFont.load_default()
    try:
        f_lbl = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 36)
    except Exception:
        pass

    for i, char in enumerate(MS.CHARACTERS):
        r = i // cols
        c = i % cols
        cx = ox + c * gw + gw // 2
        cy = oy + r * gh + gh // 2 - 15

        c_slug = char_slug(char)
        th_p = thumbs_dir / f"{c_slug}_split_th.png"
        if th_p.exists():
            th_im = Image.open(th_p).convert("RGBA")
            th_im.thumbnail((gw - 40, gh - 70), Image.Resampling.LANCZOS)
            p1.paste(th_im, (cx - th_im.width // 2, cy - th_im.height // 2), th_im)

        d1.text((cx, cy + gh // 2 - 25), f"Split {char}", fill=(60, 60, 60), font=f_lbl, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 2: Step-by-Step Cricut & Silhouette Tutorial
    # -------------------------------------------------------------
    p2 = Image.new("RGB", (W, H), (255, 255, 255))
    d2 = ImageDraw.Draw(p2)
    draw_top_banner(d2, "HOW TO PERSONALIZE YOUR MONOGRAM", "Step-by-Step Cricut Design Space & Silhouette Studio Guide")

    try:
        f_h2 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 52)
        f_body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 38)
        f_step = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 44)
    except Exception:
        f_h2 = f_body = f_step = ImageFont.load_default()

    steps = [
        ("Step 1: Upload the SVG File",
         "1. Open Cricut Design Space and click 'Upload' -> 'Upload Image'.\n"
         "2. Choose the SVG file for your desired letter (e.g., Letter_M_Split.svg).\n"
         "3. Add the design onto your Canvas. The monogram is pre-sized to 6 inches wide\n"
         "   and 100% pre-welded so you do not have to weed disjointed loose pieces!"),
        ("Step 2: Add Your Custom Name or Text",
         "1. Select the Text tool (T) from the left sidebar.\n"
         "2. Type your personalized surname, first name, or date in ALL CAPS or Script.\n"
         "3. Scale the text so it fits comfortably inside the open horizontal ribbon between\n"
         "   the dual parallel split bars. Keep a clean ~1/8 inch breathing room on all sides."),
        ("Step 3: Align and Weld for Cutting",
         "1. Select both the Split Monogram and your custom text.\n"
         "2. Click 'Align' -> 'Center Horizontally' on the top toolbar.\n"
         "3. With both selected, click the 'Combine' -> 'Weld' button in the bottom right.\n"
         "   Your monogram and name will instantly fuse into a single perfect cutting file!\n"
         "4. Click 'Make It', choose your material (HTV / Iron-on or Vinyl), and cut!"),
        ("Using Silhouette Studio (Basic & Designer Edition)",
         "- Designer Edition / Business Edition: Simply open the SVG file directly.\n"
         "- Basic Edition (Free): Open the DXF file (e.g., Letter_M_Split.dxf) or drag & drop\n"
         "  the high-resolution 300 DPI PNG file and use the 'Trace' panel.")
    ]

    cur_y = 340
    for title, text in steps:
        # Box background
        d2.rounded_rectangle([120, cur_y, W - 120, cur_y + 360], radius=24, fill=(247, 250, 248), outline=(210, 225, 215), width=3)
        d2.text((160, cur_y + 40), title, fill=(42, 60, 48), font=f_step)
        d2.multiline_text((160, cur_y + 110), text, fill=(50, 50, 50), font=f_body, spacing=14)
        cur_y += 410

    # -------------------------------------------------------------
    # PAGE 3: Font Pairings & Commercial License
    # -------------------------------------------------------------
    p3 = Image.new("RGB", (W, H), (255, 255, 255))
    d3 = ImageDraw.Draw(p3)
    draw_top_banner(d3, "CURATED FONT PAIRINGS & LICENSE", "Recommended Free Fonts + Commercial Terms")

    cur_y = 340
    d3.text((120, cur_y), "RECOMMENDED FREE FONTS FOR THE SPLIT SPACE", fill=(42, 60, 48), font=f_h2)
    cur_y += 70

    font_pairs = [
        ("Classic Modern Sans: Montserrat Bold or Poppins SemiBold",
         "Gives a clean, sophisticated, high-end bridal or modern nursery aesthetic.\n"
         "Available 100% free for commercial use on Google Fonts."),
        ("Elegant Calligraphy Script: Great Vibes, Allura, or Alex Brush",
         "Perfect for romantic wedding signs, personalized bridal party robes, and mama tumblers.\n"
         "Available 100% free on Google Fonts."),
        ("Playful Whimsical: Caveat Brush or Fredoka",
         "Ideal for kids' water bottles, preschool lunchboxes, teacher gifts, and back-to-school totes.\n"
         "Available 100% free on Google Fonts.")
    ]

    for title, desc in font_pairs:
        d3.rounded_rectangle([120, cur_y, W - 120, cur_y + 180], radius=18, fill=(250, 250, 252), outline=(220, 225, 230), width=2)
        d3.text((150, cur_y + 30), title, fill=(20, 40, 30), font=f_step)
        d3.multiline_text((150, cur_y + 85), desc, fill=(80, 80, 80), font=f_body, spacing=10)
        cur_y += 220

    cur_y += 40
    d3.text((120, cur_y), "COMMERCIAL LICENSE & USAGE TERMS", fill=(42, 60, 48), font=f_h2)
    cur_y += 70

    license_text = (
        "YOU MAY:\n"
        "- Use these cut files to create physical products (shirts, signs, totes, mugs, decals, hats, party decor)\n"
        "  to sell in your handmade shop or small business, up to 500 physical units per design.\n"
        "- Modify colors, resize, and weld with custom personalized names.\n"
        "- Sell physical decals, laser-cut signs, and heat-transfer vinyl crafts.\n\n"
        "YOU MAY NOT:\n"
        "- Resell, redistribute, share, giveaway, or sublicense the digital files in any format (SVG, PNG, DXF, EPS).\n"
        "- Upload these raw or modified files to Print-On-Demand (POD) websites (such as Redbubble, Zazzle, TeePublic).\n"
        "- Claim the vector artwork or designs as your own digital creations.\n\n"
        "100% SATISFACTION GUARANTEE:\n"
        "If you encounter any difficulty with software compatibility or cutting machine settings, please reach out\n"
        "directly via Etsy messaging and we will promptly assist you!"
    )

    d3.rounded_rectangle([120, cur_y, W - 120, cur_y + 700], radius=24, fill=(245, 248, 245), outline=(180, 210, 190), width=3)
    d3.multiline_text((160, cur_y + 40), license_text, fill=(40, 50, 45), font=f_body, spacing=14)

    guide_path.parent.mkdir(parents=True, exist_ok=True)
    p1.save(guide_path, "PDF", save_all=True, append_images=[p2, p3], resolution=DPI)
    print(f"Built multi-page guide PDF: {guide_path.name} ({guide_path.stat().st_size / 1e6:.2f} MB)")
    return guide_path


def package_upload_zips(root: Path, files: Path, thumbs_dir: Path) -> List[Path]:
    """Packages all files into 5 Etsy upload archives (<= 20 MB each)."""
    upload_dir = root / "etsy_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 1. Zip 1: Split Monograms Vector Bundle (SVG, DXF, EPS + 2Layer SVG)
    z1_path = upload_dir / "01_Split_Monograms_SVG_DXF_EPS.zip"
    with zipfile.ZipFile(z1_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "01_Split_Monograms").rglob("*"):
            if p.is_file() and not p.name.endswith(".png"):
                arcname = p.relative_to(files / "01_Split_Monograms")
                z.write(p, arcname)

    # 2. Zip 2: Full Botanical Monograms Vector Bundle (SVG, DXF, EPS)
    z2_path = upload_dir / "02_Full_Botanical_Monograms_SVG_DXF_EPS.zip"
    with zipfile.ZipFile(z2_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Full_Botanical").rglob("*"):
            if p.is_file() and not p.name.endswith(".png"):
                arcname = p.relative_to(files / "02_Full_Botanical")
                z.write(p, arcname)

    # 3. Zip 3: Split Monograms 300 DPI Transparent PNGs
    z3_path = upload_dir / "03_Split_Monograms_PNG_300DPI.zip"
    with zipfile.ZipFile(z3_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "01_Split_Monograms" / "PNG_300DPI").glob("*.png"):
            if p.is_file():
                z.write(p, p.name)

    # 4. Zip 4: Full Botanical Monograms 300 DPI Transparent PNGs
    z4_path = upload_dir / "04_Full_Botanical_Monograms_PNG_300DPI.zip"
    with zipfile.ZipFile(z4_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Full_Botanical" / "PNG_300DPI").glob("*.png"):
            if p.is_file():
                z.write(p, p.name)

    # 5. File 5: Monogram Guide & Font Pairings PDF directly in etsy_upload
    guide_upload_path = upload_dir / "Monogram_Crafting_Guide_And_Font_Pairings.pdf"
    build_guide_pdf(guide_upload_path, thumbs_dir)

    zips = [z1_path, z2_path, z3_path, z4_path, guide_upload_path]
    for f in zips:
        mb = f.stat().st_size / (1024 * 1024)
        print(f"  Upload deliverable: {f.name} ({mb:.2f} MB)")
        assert mb <= 20.0, f"File {f.name} exceeds 20 MB limit!"

    assert len(zips) <= 5, "Exceeds 5 Etsy upload files limit!"
    return zips


def build_pack() -> Path:
    dirs = listing_dirs(SLUG)
    root = dirs["root"]
    files = dirs["files"]
    work = dirs["work"]
    thumbs = work / "thumbs"

    catalog = generate_all_monograms(files, thumbs)
    (root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    zips = package_upload_zips(root, files, thumbs)
    print(f"Pack built successfully at: {root}")
    return root


if __name__ == "__main__":
    build_pack()
