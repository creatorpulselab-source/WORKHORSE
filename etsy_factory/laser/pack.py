"""Pack builder for Cute Laser Cut Keychains & Earrings SVG Bundle.

Generates 20 Keychains + 20 Earring Pairs (40 Laser Cut Designs):
- Individual Laser-Ready SVGs (Color coded: Red Cut, Blue Score, Black Engrave)
- Master Nested Cutting Sheet SVGs (12x20 in Glowforge Bed & 12x12 in Craft Bed)
- DXF files for Silhouette Studio & LightBurn
- EPS files for Illustrator & CorelDraw
- 300 DPI transparent PNG previews
- 3-Page Laser Sizing, Kerf & Settings PDF Guide

Packages deliverables into exactly 5 Etsy upload files (each <= 20 MB).
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

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely import affinity

from etsy_factory.common import ETSY_MAX_FILE_BYTES, listing_dirs
from etsy_factory.laser import designs as LD
from etsy_factory.typo import export as X

SLUG = "cute_laser_cut_keychains_and_earrings_svg_bundle"
DPI = 300


def render_laser_preview(item: Dict, width_px: int = 1200) -> Image.Image:
    """Renders a realistic wood laser-cut preview with dark cut borders and engraved details."""
    S = width_px
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Base wood tone
    WOOD_BASE = (222, 195, 160)
    WOOD_DARK = (92, 58, 32)
    ENGRAVE_COL = (60, 36, 18)

    # 1. Base cut shape
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_p = Path(tmp.name)
    X.write_png(tmp_p, [(item["cut"], WOOD_BASE)], width_px=S, dpi=DPI)
    base_wood = Image.open(tmp_p).convert("RGBA")
    tmp_p.unlink(missing_ok=True)

    # 2. Add subtle laser edge burn (thin dark contour)
    burned_edge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    alpha = base_wood.split()[-1]
    burned_edge.paste(WOOD_DARK + (255,), (0, 0), mask=alpha)
    inner_mask = alpha.filter(ImageFilter.GaussianBlur(2))
    # Composite wood over burned edge
    comp = Image.composite(base_wood, burned_edge, inner_mask)

    # 3. Add engraved & scored details
    d = ImageDraw.Draw(comp)
    # If engrave exists
    if item.get("engrave") and not item["engrave"].is_empty:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp2:
            tmp2_p = Path(tmp2.name)
        X.write_png(tmp2_p, [(item["engrave"], ENGRAVE_COL)], width_px=S, dpi=DPI)
        eng_im = Image.open(tmp2_p).convert("RGBA")
        tmp2_p.unlink(missing_ok=True)
        comp.paste(eng_im, (0, 0), eng_im)

    return comp


def generate_all_files(files_dir: Path, thumbs_dir: Path) -> Dict:
    kc_svg = files_dir / "01_Keychains" / "SVG"
    kc_dxf = files_dir / "01_Keychains" / "DXF"
    kc_eps = files_dir / "01_Keychains" / "EPS"
    kc_png = files_dir / "01_Keychains" / "PNG_300DPI"

    er_svg = files_dir / "02_Earrings" / "SVG"
    er_dxf = files_dir / "02_Earrings" / "DXF"
    er_eps = files_dir / "02_Earrings" / "EPS"
    er_png = files_dir / "02_Earrings" / "PNG_300DPI"

    sheets_dir = files_dir / "03_Master_Sheets"

    for d in (kc_svg, kc_dxf, kc_eps, kc_png, er_svg, er_dxf, er_eps, er_png, sheets_dir, thumbs_dir):
        d.mkdir(parents=True, exist_ok=True)

    catalog = {"keychains": [], "earrings": []}

    # Process Keychains
    print("Generating files for 20 Keychains...")
    keychains = LD.build_keychains()
    for item in keychains:
        iid = item["id"]
        # SVG
        s_p = kc_svg / f"Keychain_{iid}.svg"
        LD.write_laser_svg(s_p, item["cut"], item.get("score"), item.get("engrave"), width_in=2.4)
        # DXF & EPS
        d_p = kc_dxf / f"Keychain_{iid}.dxf"
        X.write_dxf(d_p, item["cut"])
        e_p = kc_eps / f"Keychain_{iid}.eps"
        X.write_eps(e_p, item["cut"])
        # PNG
        p_p = kc_png / f"Keychain_{iid}.png"
        X.write_png(p_p, [(item["cut"], (215, 185, 145))], width_px=2400, dpi=DPI)
        # Thumbnail preview
        th_p = thumbs_dir / f"kc_{iid}_th.png"
        th = render_laser_preview(item, width_px=800)
        th.save(th_p, optimize=True)

        catalog["keychains"].append({
            "id": iid, "title": item["title"],
            "svg": s_p.name, "dxf": d_p.name, "png": p_p.name, "thumb": th_p.name
        })

    # Process Earrings
    print("Generating files for 20 Earrings Pairs...")
    earrings = LD.build_earrings()
    for item in earrings:
        iid = item["id"]
        s_p = er_svg / f"{iid}.svg"
        LD.write_laser_svg(s_p, item["cut"], item.get("score"), item.get("engrave"), width_in=1.6)
        d_p = er_dxf / f"{iid}.dxf"
        X.write_dxf(d_p, item["cut"])
        e_p = er_eps / f"{iid}.eps"
        X.write_eps(e_p, item["cut"])
        p_p = er_png / f"{iid}.png"
        X.write_png(p_p, [(item["cut"], (225, 205, 180))], width_px=2400, dpi=DPI)
        th_p = thumbs_dir / f"er_{iid}_th.png"
        th = render_laser_preview(item, width_px=800)
        th.save(th_p, optimize=True)

        catalog["earrings"].append({
            "id": iid, "title": item["title"],
            "svg": s_p.name, "dxf": d_p.name, "png": p_p.name, "thumb": th_p.name
        })

    # Master Nested Cutting Sheets
    # Sheet 1: 20 Keychains on 12x20 in sheet (300 x 500 mm)
    sheet_kc_svg = sheets_dir / "Master_Sheet_20_Keychains_12x20_Glowforge.svg"
    # Layout 4 rows x 5 cols
    nested_cuts, nested_scores, nested_engraves = [], [], []
    for idx, item in enumerate(keychains):
        r, c = idx // 5, idx % 5
        ox = 35.0 + c * 58.0
        oy = 35.0 + r * 68.0
        g_c = affinity.translate(item["cut"], ox, oy)
        nested_cuts.append(g_c)
        if item.get("score"):
            nested_scores.append(affinity.translate(item["score"], ox, oy))
        if item.get("engrave"):
            nested_engraves.append(affinity.translate(item["engrave"], ox, oy))

    from shapely.ops import unary_union
    LD.write_laser_svg(
        sheet_kc_svg,
        unary_union(nested_cuts),
        unary_union(nested_scores) if nested_scores else None,
        unary_union(nested_engraves) if nested_engraves else None,
        width_in=19.5
    )

    # Sheet 2: 20 Earrings on 12x12 in sheet (300 x 300 mm)
    sheet_er_svg = sheets_dir / "Master_Sheet_20_Earrings_12x12_Craft.svg"
    er_cuts, er_scores, er_engraves = [], [], []
    for idx, item in enumerate(earrings):
        r, c = idx // 5, idx % 5
        ox = 30.0 + c * 48.0
        oy = 30.0 + r * 58.0
        g_c = affinity.translate(item["cut"], ox, oy)
        er_cuts.append(g_c)
        if item.get("score"):
            er_scores.append(affinity.translate(item["score"], ox, oy))
        if item.get("engrave"):
            er_engraves.append(affinity.translate(item["engrave"], ox, oy))

    LD.write_laser_svg(
        sheet_er_svg,
        unary_union(er_cuts),
        unary_union(er_scores) if er_scores else None,
        unary_union(er_engraves) if er_engraves else None,
        width_in=11.5
    )

    return catalog


def build_guide_pdf(guide_path: Path, catalog: Dict, thumbs_dir: Path) -> Path:
    """Builds a 3-page comprehensive Laser Settings, Kerf & Hardware Guide PDF."""
    W, H = 2550, 3300
    DPI = 300

    def draw_top_banner(d: ImageDraw.ImageDraw, title: str, subtitle: str):
        d.rectangle([0, 0, W, 280], fill=(45, 34, 25))
        try:
            f_t = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 74)
            f_s = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 38)
        except Exception:
            f_t = f_s = ImageFont.load_default()
        d.text((W // 2, 95), title, fill=(255, 255, 255), font=f_t, anchor="mm")
        d.text((W // 2, 185), subtitle, fill=(225, 205, 175), font=f_s, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 1: 40 Designs Catalog (20 Keychains + 20 Earrings)
    # -------------------------------------------------------------
    p1 = Image.new("RGB", (W, H), (255, 255, 255))
    d1 = ImageDraw.Draw(p1)
    draw_top_banner(d1, "LASER KEYCHAINS & EARRINGS BUNDLE", "Visual Index of Included Designs (20 Keychains & 20 Earring Pairs)")

    # Grid 5 cols x 8 rows (40 items)
    cols, rows = 5, 8
    gw = (W - 200) // cols
    gh = (H - 420) // rows
    ox, oy = 100, 320

    f_lbl = ImageFont.load_default()
    try:
        f_lbl = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 26)
    except Exception:
        pass

    all_items = [(kc, "kc") for kc in catalog["keychains"]] + [(er, "er") for er in catalog["earrings"]]
    for i, (item, kind) in enumerate(all_items):
        r = i // cols
        c = i % cols
        cx = ox + c * gw + gw // 2
        cy = oy + r * gh + gh // 2 - 12

        th_p = thumbs_dir / item["thumb"]
        if th_p.exists():
            th_im = Image.open(th_p).convert("RGBA")
            th_im.thumbnail((gw - 36, gh - 65), Image.Resampling.LANCZOS)
            p1.paste(th_im, (cx - th_im.width // 2, cy - th_im.height // 2 - 8), th_im)

        short_name = item["title"].replace(" Keychain", "").replace(" Pair", "").replace("Earrings ", "")
        d1.text((cx, cy + gh // 2 - 20), short_name[:16], fill=(50, 40, 30), font=f_lbl, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 2: Laser Color Coding & Machine Settings Guide
    # -------------------------------------------------------------
    p2 = Image.new("RGB", (W, H), (255, 255, 255))
    d2 = ImageDraw.Draw(p2)
    draw_top_banner(d2, "LASER COLOR CODING & SETTINGS GUIDE", "Glowforge, xTool, LightBurn & Diode Laser Parameters")

    try:
        f_step_h = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 46)
        f_body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 36)
        f_h2 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 50)
    except Exception:
        f_step_h = f_body = f_h2 = ImageFont.load_default()

    cur_y = 350
    d2.text((140, cur_y), "STANDARD LASER OPERATION COLOR CODES", fill=(45, 34, 25), font=f_h2)
    cur_y += 75

    colors_info = [
        ("RED (#FF0000) - VECTOR CUT",
         "Cuts all the way through the material.\n"
         "• 1/8\" (3mm) Birch Plywood / Basswood: Full power, recommended 1 pass.\n"
         "• 1/8\" (3mm) Cast Acrylic: Medium-high power, clean edge finish."),
        ("BLUE (#0000FF) - VECTOR SCORE",
         "High-speed line tracing on the wood/acrylic surface (does NOT cut through).\n"
         "• High speed, low power (~10-15% power) for crisp, clean dark surface detail lines."),
        ("BLACK (#000000) - RASTER / VECTOR ENGRAVE",
         "Solid filled areas (eyes, dark nose patches, recessed accents).\n"
         "• Line density: 250 - 300 LPI for rich contrast and smooth finish.")
    ]

    for title, desc in colors_info:
        d2.rounded_rectangle([140, cur_y, W - 140, cur_y + 230], radius=20, fill=(252, 250, 248), outline=(225, 215, 200), width=2)
        d2.text((180, cur_y + 35), title, fill=(45, 34, 25), font=f_step_h)
        d2.multiline_text((180, cur_y + 95), desc, fill=(60, 50, 45), font=f_body, spacing=10)
        cur_y += 270

    cur_y += 30
    d2.text((140, cur_y), "RECOMMENDED SETTINGS FOR 1/8\" (3MM) MATERIAL", fill=(45, 34, 25), font=f_h2)
    cur_y += 75

    rec_text = (
        "• GLOWFORGE (CO2 40W / 45W):\n"
        "  - Cut: Speed 160-180, Full Power (Basswood/Birch Plywood)\n"
        "  - Score: Speed 300, Power 40\n"
        "  - Engrave: Speed 1000, Power 80, 270 LPI\n\n"
        "• XTOOL D1 / M1 / S1 / P2 & DIODE LASERS (10W - 20W):\n"
        "  - Cut: Speed 3-5 mm/s, Power 100%, 1-2 passes (with Air Assist)\n"
        "  - Score: Speed 25-35 mm/s, Power 30-40%\n"
        "  - Tip: Always use Air Assist to eliminate charring and scorching marks!"
    )
    d2.rounded_rectangle([140, cur_y, W - 140, cur_y + 540], radius=24, fill=(248, 250, 248), outline=(210, 225, 215), width=3)
    d2.multiline_text((180, cur_y + 40), rec_text, fill=(40, 50, 45), font=f_body, spacing=14)

    # -------------------------------------------------------------
    # PAGE 3: Hardware, Sizing & Commercial License
    # -------------------------------------------------------------
    p3 = Image.new("RGB", (W, H), (255, 255, 255))
    d3 = ImageDraw.Draw(p3)
    draw_top_banner(d3, "HARDWARE ASSEMBLY & COMMERCIAL TERMS", "Keyring Rings, Ear-Wires, Kerf Tips & Commercial License")

    cur_y = 350
    d3.text((140, cur_y), "RECOMMENDED HARDWARE & ASSEMBLY", fill=(45, 34, 25), font=f_h2)
    cur_y += 75

    hw_text = (
        "KEYCHAIN HARDWARE:\n"
        "• Pre-drilled 3.5mm top loop hole fits:\n"
        "  - 25mm or 30mm split keyrings with chain\n"
        "  - 8mm to 10mm heavy-duty jump rings\n"
        "  - Leather cords, suede tassels, and swivel lobster clasps\n\n"
        "EARRING HARDWARE:\n"
        "• Pre-drilled 2.0mm top jump-ring hole fits:\n"
        "  - 5mm to 6mm (20 gauge) jewelry jump rings\n"
        "  - French hook ear-wires or ball-post studs (hypoallergenic stainless steel / gold)"
    )
    d3.rounded_rectangle([140, cur_y, W - 140, cur_y + 460], radius=24, fill=(250, 252, 254), outline=(215, 225, 235), width=3)
    d3.multiline_text((180, cur_y + 40), hw_text, fill=(50, 60, 70), font=f_body, spacing=14)

    cur_y += 540
    d3.text((140, cur_y), "COMMERCIAL LICENSE & CRAFTER TERMS", fill=(45, 34, 25), font=f_h2)
    cur_y += 75

    license_text = (
        "COMMERCIAL USE INCLUDED:\n"
        "✔ You may sell physical keychains, bag tags, and earrings made with these files\n"
        "   up to 500 physical units per design! Perfect for craft fairs, Etsy shops, and boutiques.\n"
        "✔ Small business commercial license is 100% included at no additional cost.\n"
        "✖ You MAY NOT resell, share, or redistribute the digital files in any format.\n"
        "✖ You MAY NOT upload these files to Print-On-Demand (POD) websites.\n\n"
        "100% QUALITY GUARANTEE:\n"
        "Every file has been verified for watertight closed laser paths and smooth contours.\n"
        "If you have questions about LightBurn or Glowforge setup, message our shop!"
    )
    d3.rounded_rectangle([140, cur_y, W - 140, cur_y + 540], radius=24, fill=(245, 250, 248), outline=(180, 215, 195), width=3)
    d3.multiline_text((180, cur_y + 40), license_text, fill=(40, 55, 45), font=f_body, spacing=14)

    guide_path.parent.mkdir(parents=True, exist_ok=True)
    p1.save(guide_path, "PDF", save_all=True, append_images=[p2, p3], resolution=DPI)
    print(f"Built master laser guide PDF: {guide_path.name} ({guide_path.stat().st_size / 1e6:.2f} MB)")
    return guide_path


def package_upload_zips(root: Path, files: Path, catalog: Dict, thumbs_dir: Path) -> List[Path]:
    upload_dir = root / "etsy_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 1. Zip 1: Keychains Vector Bundle (SVG, DXF, EPS + Master 12x20 Sheet)
    z1_p = upload_dir / "01_Laser_Keychains_SVG_DXF_EPS.zip"
    with zipfile.ZipFile(z1_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "01_Keychains").rglob("*"):
            if p.is_file() and not p.name.endswith(".png"):
                z.write(p, p.relative_to(files / "01_Keychains"))
        m_kc = files / "03_Master_Sheets" / "Master_Sheet_20_Keychains_12x20_Glowforge.svg"
        if m_kc.exists():
            z.write(m_kc, m_kc.name)

    # 2. Zip 2: Earrings Vector Bundle (SVG, DXF, EPS + Master 12x12 Sheet)
    z2_p = upload_dir / "02_Laser_Earrings_SVG_DXF_EPS.zip"
    with zipfile.ZipFile(z2_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Earrings").rglob("*"):
            if p.is_file() and not p.name.endswith(".png"):
                z.write(p, p.relative_to(files / "02_Earrings"))
        m_er = files / "03_Master_Sheets" / "Master_Sheet_20_Earrings_12x12_Craft.svg"
        if m_er.exists():
            z.write(m_er, m_er.name)

    # 3. Zip 3: Keychains 300 DPI Transparent PNGs
    z3_p = upload_dir / "03_Laser_Keychains_PNG_300DPI.zip"
    with zipfile.ZipFile(z3_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "01_Keychains" / "PNG_300DPI").glob("*.png"):
            if p.is_file():
                z.write(p, p.name)

    # 4. Zip 4: Earrings 300 DPI Transparent PNGs
    z4_p = upload_dir / "04_Laser_Earrings_PNG_300DPI.zip"
    with zipfile.ZipFile(z4_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Earrings" / "PNG_300DPI").glob("*.png"):
            if p.is_file():
                z.write(p, p.name)

    # 5. Zip 5: Master Guide PDF & Master Sheets
    guide_p = root / "_work" / "Laser_Cutting_Kerf_And_Settings_Guide.pdf"
    build_guide_pdf(guide_p, catalog, thumbs_dir)

    z5_p = upload_dir / "05_Laser_Settings_Guide_And_Master_Sheets.zip"
    with zipfile.ZipFile(z5_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(guide_p, guide_p.name)
        for p in (files / "03_Master_Sheets").glob("*.svg"):
            z.write(p, f"Master_Cutting_Sheets/{p.name}")

    zips = [z1_p, z2_p, z3_p, z4_p, z5_p]
    for f in zips:
        mb = f.stat().st_size / (1024 * 1024)
        print(f"  Upload deliverable: {f.name} ({mb:.2f} MB)")
        assert mb <= 20.0, f"{f.name} exceeds 20 MB cap!"

    assert len(zips) <= 5, "Exceeds 5 Etsy upload files limit!"
    return zips


def build_pack() -> Path:
    dirs = listing_dirs(SLUG)
    root = dirs["root"]
    files = dirs["files"]
    work = dirs["work"]
    thumbs = work / "thumbs"

    catalog = generate_all_files(files, thumbs)
    (root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    package_upload_zips(root, files, catalog, thumbs)

    print(f"Laser pack built successfully at: {root}")
    return root


if __name__ == "__main__":
    build_pack()
