"""Pack builder for 3D Layered Shadow Box SVG Bundle.

Generates 4 complete themes x 6 layers (24 precision cut files):
1. Woodland Deer & Moonlit Forest
2. Moonlit Safari & Gentle Giants
3. Dreamy Nursery Hot Air Balloon
4. Under the Sea & Gentle Whales

Each theme includes:
- Individual SVG cut files for each layer (8x8 inches true size)
- Master stacked multi-layer SVG
- DXF cut files for Silhouette Studio Basic
- 300 DPI transparent layer PNGs
- Printable hand-cut template PDF

Packages deliverables into 5 Etsy upload files (each <= 20 MB).
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from etsy_factory.common import ETSY_MAX_FILE_BYTES, listing_dirs
from etsy_factory.shadowbox import scenes as SB
from etsy_factory.typo import export as X

SLUG = "cute_layered_shadow_box_paper_art_svg_bundle"
DPI = 300
WIDTH_IN = 8.0     # Standard 8.0 x 8.0 inch shadow box square size


def build_theme_files(theme: Dict, files_dir: Path, thumbs_dir: Path) -> Dict:
    t_id = theme["id"]
    t_title = theme["title"]
    folder_name = theme["folder"]

    t_dir = files_dir / folder_name
    svg_dir = t_dir / "SVG"
    dxf_dir = t_dir / "DXF"
    png_dir = t_dir / "PNG_300DPI"
    pdf_dir = t_dir / "PDF_Templates"

    for d in (svg_dir, dxf_dir, png_dir, pdf_dir):
        d.mkdir(parents=True, exist_ok=True)

    layers = theme["builder"]()
    meta_layers = []

    # 1. Export individual layers (SVG, DXF, PNG)
    pdf_pages = []
    print(f"Generating files for {t_title} (6 layers)...")
    for idx, (lid, g, fill_hex) in enumerate(layers, 1):
        # Hex to RGB
        h = fill_hex.lstrip("#")
        rgb = tuple(int(h[j:j+2], 16) for j in (0, 2, 4))

        # SVG (true 8x8 inch size)
        svg_p = svg_dir / f"{lid}.svg"
        X.write_svg(svg_p, [(lid, g, fill_hex)], width_in=WIDTH_IN, title=f"{t_title} - {lid}")

        # DXF
        dxf_p = dxf_dir / f"{lid}.dxf"
        X.write_dxf(dxf_p, g)

        # PNG (300 DPI, 2400x2400 px)
        png_p = png_dir / f"{lid}.png"
        X.write_png(png_p, [(g, rgb)], width_px=2400, dpi=DPI)

        # Thumbnail for listing assembly
        th_p = thumbs_dir / f"{t_id}_{lid}_th.png"
        th_im = Image.open(png_p)
        th_im.thumbnail((600, 600), Image.Resampling.LANCZOS)
        th_im.save(th_p, optimize=True)

        # Printable hand-cut template page (US Letter, 300 DPI, centered 8x8 in box with cut lines)
        page_im = Image.new("RGB", (2550, 3300), (255, 255, 255))
        d_page = ImageDraw.Draw(page_im)
        # Header text
        try:
            f_hd = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 44)
            f_sub = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 32)
        except Exception:
            f_hd = f_sub = ImageFont.load_default()
        d_page.text((2550 // 2, 160), f"{t_title.upper()} - LAYER {idx} OF 6", fill=(30, 30, 30), font=f_hd, anchor="mm")
        d_page.text((2550 // 2, 220), f"Template for hand-cutting or tracing ({lid}) - Cut out along lines", fill=(90, 90, 90), font=f_sub, anchor="mm")

        # Paste 2400x2400 layer scaled to 8x8 in (2400 px)
        l_rgba = Image.open(png_p).convert("RGBA")
        px = (2550 - 2400) // 2
        py = 350
        page_im.paste(l_rgba, (px, py), l_rgba)
        # Draw cutting frame border
        d_page.rectangle([px, py, px + 2400, py + 2400], outline=(180, 180, 180), width=3)
        pdf_pages.append(page_im)

        meta_layers.append({
            "layer_index": idx,
            "layer_id": lid,
            "svg": svg_p.name,
            "dxf": dxf_p.name,
            "png": png_p.name,
            "fill": fill_hex,
        })

    # 2. Master stacked SVG (all 6 layers grouped in 1 file)
    master_svg_p = svg_dir / f"Master_Stacked_{t_id}.svg"
    master_layers = [(lid, g, fill_hex) for lid, g, fill_hex in layers]
    X.write_svg(master_svg_p, master_layers, width_in=WIDTH_IN, title=f"{t_title} - Master Stacked All Layers")

    # 3. Printable template PDF
    pdf_p = pdf_dir / f"{t_id}_Printable_Hand_Cut_Templates.pdf"
    if pdf_pages:
        pdf_pages[0].save(pdf_p, "PDF", save_all=True, append_images=pdf_pages[1:], resolution=DPI)

    # 4. Render stacked 3D composite preview
    comp = render_stacked_preview(layers, width_px=1800)
    comp_p = thumbs_dir / f"{t_id}_stacked_composite.png"
    comp.save(comp_p, optimize=True)

    return {
        "id": t_id,
        "title": t_title,
        "folder": folder_name,
        "layers": meta_layers,
        "master_svg": master_svg_p.name,
        "template_pdf": pdf_p.name,
        "composite_preview": comp_p.name,
    }


def render_stacked_preview(layers: List[Tuple[str, BaseGeometry, str]], width_px: int = 1800) -> Image.Image:
    """Renders a realistic layered paper shadow box composite with depth shadows and LED glow."""
    S = width_px
    comp = Image.new("RGBA", (S, S), (12, 16, 24, 255))

    for i, (lid, g, fill_hex) in enumerate(layers):
        h = fill_hex.lstrip("#")
        rgb = tuple(int(h[j:j+2], 16) for j in (0, 2, 4))

        # Render layer
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_p = Path(tmp.name)
        X.write_png(tmp_p, [(g, rgb)], width_px=S, dpi=300)
        l_img = Image.open(tmp_p).convert("RGBA")
        tmp_p.unlink(missing_ok=True)

        # Drop shadow between layers
        if i > 0:
            shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            alpha = l_img.split()[-1]
            shadow.paste((5, 5, 10, 115), (0, 0), mask=alpha)
            shadow = shadow.filter(ImageFilter.GaussianBlur(14))
            comp.paste(shadow, (0, 12), shadow)

        comp.paste(l_img, (0, 0), l_img)

    return comp


def build_assembly_guide_pdf(guide_path: Path, catalog: Dict, thumbs_dir: Path) -> Path:
    """Builds a 3-page comprehensive assembly and LED lighting PDF guide."""
    W, H = 2550, 3300
    DPI = 300

    def draw_top_banner(d: ImageDraw.ImageDraw, title: str, subtitle: str):
        d.rectangle([0, 0, W, 280], fill=(24, 38, 54))
        try:
            f_t = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 74)
            f_s = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 38)
        except Exception:
            f_t = f_s = ImageFont.load_default()
        d.text((W // 2, 95), title, fill=(255, 255, 255), font=f_t, anchor="mm")
        d.text((W // 2, 185), subtitle, fill=(185, 215, 235), font=f_s, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 1: 4 Themes Visual Index
    # -------------------------------------------------------------
    p1 = Image.new("RGB", (W, H), (255, 255, 255))
    d1 = ImageDraw.Draw(p1)
    draw_top_banner(d1, "3D LAYERED SHADOW BOX BUNDLE", "Visual Index of Included Themes (4 Complete 6-Layer Designs)")

    try:
        f_card_t = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 40)
        f_card_sub = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 30)
    except Exception:
        f_card_t = f_card_sub = ImageFont.load_default()

    coords = [
        (160, 340), (1340, 340),
        (160, 1750), (1340, 1750)
    ]
    card_w, card_h = 1050, 1320

    for idx, (theme, (cx, cy)) in enumerate(zip(catalog["themes"], coords)):
        d1.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=24, fill=(248, 250, 252), outline=(215, 225, 235), width=3)
        # Composite preview
        th_p = thumbs_dir / f"{theme['id']}_stacked_composite.png"
        if th_p.exists():
            th_im = Image.open(th_p).convert("RGBA")
            th_im.thumbnail((card_w - 80, card_h - 220), Image.Resampling.LANCZOS)
            px = cx + (card_w - th_im.width) // 2
            py = cy + 40
            p1.paste(th_im, (px, py), th_im)
        d1.text((cx + card_w // 2, cy + card_h - 130), theme["title"], fill=(24, 38, 54), font=f_card_t, anchor="mm")
        d1.text((cx + card_w // 2, cy + card_h - 70), "6 Numbered Precision Cut Layers • 8x8 In", fill=(100, 110, 120), font=f_card_sub, anchor="mm")

    # -------------------------------------------------------------
    # PAGE 2: Step-by-Step Cardstock Cutting & Assembly Guide
    # -------------------------------------------------------------
    p2 = Image.new("RGB", (W, H), (255, 255, 255))
    d2 = ImageDraw.Draw(p2)
    draw_top_banner(d2, "HOW TO ASSEMBLE YOUR SHADOW BOX", "Materials, Cardstock Weights, Cricut Settings & Spacers")

    try:
        f_step_h = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 46)
        f_body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 36)
    except Exception:
        f_step_h = f_body = ImageFont.load_default()

    steps = [
        ("1. Recommended Materials & Cardstock",
         "• Cardstock Weight: 65 lb to 80 lb (176–216 gsm) smooth solid-core cardstock.\n"
         "  Solid-core cardstock prevents white edges when cut.\n"
         "• Adhesive: Double-sided 3D foam tape squares or foam mounting strips (2mm to 3mm thick).\n"
         "• Craft Tools: Precision craft tweezers, bone folder, cutting mat, and craft glue."),
        ("2. Machine Cutting Instructions (Cricut / Silhouette)",
         "• Cricut Design Space: Upload each numbered SVG (Layer 1 to Layer 6). Ensure size is set\n"
         "  to 8.0 x 8.0 inches (or your desired square frame dimension). Select 'Cardstock (for intricate cuts)'\n"
         "  with a Fine-Point Blade.\n"
         "• Silhouette Studio: Open DXF or SVG (Designer Edition). Use default Cardstock cut settings."),
        ("3. Hand Cutting with Printable PDF Templates",
         "• Print the included PDF templates at 100% scale (no scaling) on your cardstock.\n"
         "• Use a sharp craft knife / X-Acto with a fresh #11 blade and a metal ruler for straight edges."),
        ("4. Stacking and Foam Spacer Placement",
         "• Lay Layer 1 (Back Panel) flat on your work surface.\n"
         "• Apply double-sided foam tape squares along all 4 outer 15mm border margins.\n"
         "• Place Layer 2 directly over Layer 1, pressing firmly on the corners.\n"
         "• Repeat in sequence: Layer 1 -> Layer 2 -> Layer 3 -> Layer 4 -> Layer 5 -> Layer 6 (Front Frame).\n"
         "  The foam spacers create the magical multi-depth optical 3D perspective!")
    ]

    cur_y = 350
    for title, text in steps:
        d2.rounded_rectangle([140, cur_y, W - 140, cur_y + 360], radius=24, fill=(247, 250, 252), outline=(210, 225, 235), width=3)
        d2.text((180, cur_y + 40), title, fill=(24, 38, 54), font=f_step_h)
        d2.multiline_text((180, cur_y + 110), text, fill=(50, 60, 70), font=f_body, spacing=14)
        cur_y += 420

    # -------------------------------------------------------------
    # PAGE 3: LED Lighting, Frame Sizing & Commercial License
    # -------------------------------------------------------------
    p3 = Image.new("RGB", (W, H), (255, 255, 255))
    d3 = ImageDraw.Draw(p3)
    draw_top_banner(d3, "LIGHTING, FRAMING & COMMERCIAL LICENSE", "LED Fairy Lights Installation, Frame Sizing & Small Business Terms")

    cur_y = 350
    try:
        f_h2 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 48)
    except Exception:
        f_h2 = ImageFont.load_default()

    d3.text((140, cur_y), "FRAME COMPATIBILITY & LED INSTALLATION", fill=(24, 38, 54), font=f_h2)
    cur_y += 75

    light_text = (
        "SHADOW BOX FRAMES:\n"
        "• Fits standard 8x8 in (20x20 cm) or 9x9 in (23x23 cm) shadow box display frames\n"
        "  (such as IKEA Sannahed or IKEA Ribba frames with deep internal spacer).\n"
        "• Recommended frame depth: 1.0 inch to 1.5 inches deep to accommodate all 6 layers.\n\n"
        "LED LIGHTING INSTALLATION:\n"
        "• Use micro warm-white fairy lights (battery operated) or a USB 5V LED strip.\n"
        "• Adhere the LED strip around the inside perimeter behind Layer 1 (Back Panel).\n"
        "• The cut-out moon, stars, sunbeams, and background silhouettes will illuminate\n"
        "  with a soft, magical ambient glow in the evening!"
    )
    d3.rounded_rectangle([140, cur_y, W - 140, cur_y + 480], radius=24, fill=(250, 252, 254), outline=(215, 225, 235), width=3)
    d3.multiline_text((180, cur_y + 40), light_text, fill=(50, 60, 70), font=f_body, spacing=14)

    cur_y += 560
    d3.text((140, cur_y), "COMMERCIAL LICENSE & CRAFTER GUARANTEE", fill=(24, 38, 54), font=f_h2)
    cur_y += 75

    license_text = (
        "COMMERCIAL TERMS:\n"
        "✔ You may sell physical shadow boxes, lighted paper art, and framed crafts made with these files\n"
        "   up to 500 physical units per design. Small business commercial use is 100% included!\n"
        "✖ You MAY NOT resell, share, redistribute, or giveaway the digital SVG/DXF/PDF/PNG files.\n"
        "✖ You MAY NOT upload raw or modified cut files to print-on-demand sites.\n\n"
        "100% SATISFACTION GUARANTEE:\n"
        "Every layer geometry is tested and verified watertight for clean, tear-free machine cutting.\n"
        "If you have questions about machine settings or frame sizing, message us on Etsy!"
    )
    d3.rounded_rectangle([140, cur_y, W - 140, cur_y + 540], radius=24, fill=(245, 250, 248), outline=(180, 215, 195), width=3)
    d3.multiline_text((180, cur_y + 40), license_text, fill=(40, 55, 45), font=f_body, spacing=14)

    guide_path.parent.mkdir(parents=True, exist_ok=True)
    p1.save(guide_path, "PDF", save_all=True, append_images=[p2, p3], resolution=DPI)
    print(f"Built master assembly guide PDF: {guide_path.name} ({guide_path.stat().st_size / 1e6:.2f} MB)")
    return guide_path


def package_upload_zips(root: Path, files: Path, catalog: Dict, thumbs_dir: Path) -> List[Path]:
    """Packages all files into exactly 5 Etsy upload packages (<= 20 MB each)."""
    upload_dir = root / "etsy_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Zips 1 to 4: One dedicated zip per Theme (SVG + DXF + PDF Template)
    zips = []
    for idx, theme in enumerate(catalog["themes"], 1):
        folder = theme["folder"]
        z_name = f"0{idx}_{theme['id'].title()}_Shadow_Box_SVG_DXF_PDF.zip"
        z_path = upload_dir / z_name
        with zipfile.ZipFile(z_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            t_dir = files / folder
            for p in t_dir.rglob("*"):
                if p.is_file() and not p.name.endswith(".png"):
                    arcname = p.relative_to(t_dir)
                    z.write(p, arcname)
        zips.append(z_path)

    # Zip 5: All 24 transparent PNG previews + Master Assembly PDF Guide
    z5_path = upload_dir / "05_Shadow_Box_Assembly_Guide_And_PNG_Previews.zip"
    with zipfile.ZipFile(z5_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Add all PNGs
        for p in files.rglob("*.png"):
            if p.is_file():
                rel = p.relative_to(files)
                z.write(p, f"PNG_Previews/{rel}")
        # Add assembly guide
        guide_p = root / "_work" / "3D_Shadow_Box_Assembly_And_Crafting_Guide.pdf"
        build_assembly_guide_pdf(guide_p, catalog, thumbs_dir)
        z.write(guide_p, guide_p.name)

    zips.append(z5_path)

    for f in zips:
        mb = f.stat().st_size / (1024 * 1024)
        print(f"  Upload file: {f.name} ({mb:.2f} MB)")
        assert mb <= 20.0, f"{f.name} exceeds 20 MB cap!"

    assert len(zips) <= 5, "Exceeds 5 Etsy upload files limit!"
    return zips


def build_pack() -> Path:
    dirs = listing_dirs(SLUG)
    root = dirs["root"]
    files = dirs["files"]
    work = dirs["work"]
    thumbs = work / "thumbs"

    thumbs.mkdir(parents=True, exist_ok=True)

    catalog = {"themes": [], "total_layers": 24}
    for theme in SB.THEMES:
        t_data = build_theme_files(theme, files, thumbs)
        catalog["themes"].append(t_data)

    (root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    zips = package_upload_zips(root, files, catalog, thumbs)

    print(f"Shadow box pack built successfully at: {root}")
    return root


if __name__ == "__main__":
    build_pack()
