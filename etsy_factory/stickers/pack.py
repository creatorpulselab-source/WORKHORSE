"""Cute Animal Sticker Sheets Pack Generator.

Generates:
1. 20 Individual Die-Cut Sticker PNGs (300 DPI, transparent, crisp white bleed contour)
2. 20 Digital Planner Sticker PNGs (with realistic soft dropshadow for iPad/GoodNotes)
3. 20 Individual SVG & DXF Cut Lines (kiss-cut contours)
4. 4 Themed Printable Sticker Sheets in US Letter & A4:
   - Sheet 1: Kawaii Pets & Farm (Dog, Cat, Bunny, Pig, Cow + mini paws/hearts)
   - Sheet 2: Woodland Buddies (Bear, Fox, Deer, Owl, Frog + mini acorns/stars)
   - Sheet 3: Safari Pals (Lion, Tiger, Panda, Koala, Monkey + mini leaves/sparkles)
   - Sheet 4: Sweet Pals & Birds (Penguin, Chick, Duck, Sheep, Elephant + mini stars/clouds)
5. Multi-page High-Res Vector-Embedded Print PDFs (US Letter & A4)
6. Sheet-level Cricut / Silhouette Print-Then-Cut SVG cut lines and black silhouette masks
7. Itemized bin-packed upload zips (each <= 20 MB) and comprehensive Printing & Cutting PDF Guide.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from etsy_factory import kit
from etsy_factory.common import ETSY_MAX_FILE_BYTES, RunReport, listing_dirs
from etsy_factory.faces import animals as AN
from etsy_factory.faces import pack as FP
from etsy_factory.typo import export as X
from etsy_factory.typo.text import polys

SLUG = "cute_animal_sticker_sheets_printable_cut_files"
MM_PER_IN = 25.4
DPI = 300

# Decorative filler geometry helpers
def make_star(x: float, y: float, r_outer: float, r_inner: float = 0.0, points: int = 4) -> Polygon:
    if r_inner <= 0:
        r_inner = r_outer * 0.38
    pts = []
    for i in range(points * 2):
        angle = i * math.pi / points - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    return Polygon(pts)


def make_heart(x: float, y: float, size: float) -> Polygon:
    # Parametric heart centered at x, y
    s = size / 32.0
    pts = []
    for t_deg in range(0, 360, 10):
        t = math.radians(t_deg)
        hx = 16 * (math.sin(t) ** 3)
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x + hx * s, y + (hy + 2) * s))
    return Polygon(pts)


def make_paw(x: float, y: float, size: float) -> BaseGeometry:
    s = size / 20.0
    pad = Point(x, y - 2 * s).buffer(5 * s, quad_segs=16)
    t1 = Point(x - 5.5 * s, y + 4 * s).buffer(2.2 * s, quad_segs=16)
    t2 = Point(x - 2.0 * s, y + 7 * s).buffer(2.2 * s, quad_segs=16)
    t3 = Point(x + 2.0 * s, y + 7 * s).buffer(2.2 * s, quad_segs=16)
    t4 = Point(x + 5.5 * s, y + 4 * s).buffer(2.2 * s, quad_segs=16)
    return unary_union([pad, t1, t2, t3, t4])


LOCAL_FONTS = Path(r"F:\WORKHORSE\etsy_factory\fonts")


def get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    p = LOCAL_FONTS / name
    if p.exists():
        return ImageFont.truetype(str(p), size)
    return kit.font("bold" if "Bold" in name or "Anton" in name else "regular", size)


# Themed Sheet Definitions (using exact keys from AN.A)
SHEETS = [
    {
        "key": "kawaii_pets",
        "title": "KAWAII PETS & FARM",
        "animals": ["cat", "bunny", "pig", "cow", "mouse"],
        "accent": (240, 98, 146),      # Pastel Pink
        "bg_hex": "#FFF4F7",
        "fillers": [
            ("paw", "paw", "#FF8DA1", (35, 120), 10.0),
            ("paw", "paw", "#FF8DA1", (175, 120), 10.0),
            ("heart", "heart", "#FFB6C1", (105, 115), 11.0),
            ("star", "star", "#FFD166", (30, 20), 8.0),
            ("star", "star", "#FFD166", (180, 20), 8.0),
            ("heart", "heart", "#FF8DA1", (105, 5), 9.0),
        ]
    },
    {
        "key": "woodland_buddies",
        "title": "WOODLAND & DINO BUDDIES",
        "animals": ["bear", "fox", "owl", "frog", "dino"],
        "accent": (76, 175, 80),       # Warm Green
        "bg_hex": "#F4FAF4",
        "fillers": [
            ("star", "star", "#81C784", (35, 120), 10.0),
            ("star", "star", "#81C784", (175, 120), 10.0),
            ("heart", "heart", "#A5D6A7", (105, 115), 11.0),
            ("star", "star", "#FFD166", (30, 20), 8.0),
            ("star", "star", "#FFD166", (180, 20), 8.0),
            ("heart", "heart", "#E57373", (105, 5), 9.0),
        ]
    },
    {
        "key": "safari_pals",
        "title": "SAFARI & JUNGLE PALS",
        "animals": ["lion", "panda", "koala", "giraffe", "hippo"],
        "accent": (255, 152, 0),       # Warm Orange
        "bg_hex": "#FFF9F0",
        "fillers": [
            ("paw", "paw", "#FFB74D", (35, 120), 10.0),
            ("paw", "paw", "#FFB74D", (175, 120), 10.0),
            ("star", "star", "#FFD54F", (105, 115), 11.0),
            ("star", "star", "#FFCA28", (30, 20), 8.0),
            ("star", "star", "#FFCA28", (180, 20), 8.0),
            ("heart", "heart", "#FF8A65", (105, 5), 9.0),
        ]
    },
    {
        "key": "sweet_cuties",
        "title": "MAGICAL CUTIES & BIRDS",
        "animals": ["penguin", "chick", "sheep", "elephant", "unicorn"],
        "accent": (33, 150, 243),      # Soft Sky Blue
        "bg_hex": "#F0F8FF",
        "fillers": [
            ("heart", "heart", "#64B5F6", (35, 120), 10.0),
            ("heart", "heart", "#64B5F6", (175, 120), 10.0),
            ("star", "star", "#FFF176", (105, 115), 11.0),
            ("star", "star", "#4FC3F7", (30, 20), 8.0),
            ("star", "star", "#4FC3F7", (180, 20), 8.0),
            ("heart", "heart", "#BA68C8", (105, 5), 9.0),
        ]
    }
]


def render_sticker_composite(layers: List[Tuple[str, BaseGeometry, str]], width_px: int) -> Image.Image:
    """Renders layers (including white halo bottom layer) into an antialiased RGBA image."""
    allg = unary_union([g for _, g, _ in layers if not g.is_empty])
    b = allg.bounds
    canvas = None
    for _lid, g, hx in layers:
        if g.is_empty:
            continue
        m = X.mask(g, width_px, bounds=b, supersample=2)
        if canvas is None:
            canvas = Image.new("RGBA", m.size, (0, 0, 0, 0))
        rgb = FP.rgb(hx)
        col = Image.new("RGBA", m.size, rgb + (255,))
        col.putalpha(m)
        canvas.alpha_composite(col)
    return canvas


def make_planner_shadow(sticker: Image.Image, blur: int = 14, offset: Tuple[int, int] = (0, 8), alpha_val: int = 65) -> Image.Image:
    """Adds a realistic soft contact drop shadow for digital planner PNGs."""
    alpha = sticker.split()[3]
    sh_mask = alpha.filter(ImageFilter.GaussianBlur(blur))
    pad_x, pad_y = blur * 2 + abs(offset[0]), blur * 2 + abs(offset[1])
    out = Image.new("RGBA", (sticker.width + pad_x * 2, sticker.height + pad_y * 2), (0, 0, 0, 0))
    sh_layer = Image.new("RGBA", sticker.size, (0, 0, 0, alpha_val))
    sh_layer.putalpha(sh_mask)
    out.alpha_composite(sh_layer, (pad_x + offset[0], pad_y + offset[1]))
    out.alpha_composite(sticker, (pad_x, pad_y))
    # Crop transparent borders cleanly
    bb = out.getbbox()
    return out.crop(bb) if bb else out


def build_individual_stickers(files: Path, thumbs: Path) -> List[Dict]:
    """Builds individual die-cut PNGs, planner PNGs, and cut-line SVGs/DXFs."""
    ind_png_dir = files / "01_Individual_Stickers" / "PNG_Transparent_300DPI"
    ind_planner_dir = files / "01_Individual_Stickers" / "PNG_Digital_Planner_Shadow"
    ind_svg_dir = files / "01_Individual_Stickers" / "SVG_Cut_Lines"
    ind_dxf_dir = files / "01_Individual_Stickers" / "DXF_Cut_Lines"
    for d in (ind_png_dir, ind_planner_dir, ind_svg_dir, ind_dxf_dir, thumbs):
        d.mkdir(parents=True, exist_ok=True)

    meta = []
    animal_keys = [k for s in SHEETS for k in s["animals"]]

    for idx, key in enumerate(animal_keys, 1):
        a = AN.A[key]
        name = f"{idx:02d}_{a.name}"
        outline = a.outline()
        # White die-cut contour buffer: 3.5 mm bleed halo
        halo = outline.buffer(3.5, quad_segs=24, join_style=1)
        layers = [("halo", halo, "#FFFFFF")] + [(lid, g, hx) for lid, g, hx in a.svg_layers()]

        # 1. Individual 300 DPI Transparent PNG (width ~1500 px = 5 inches at 300 DPI)
        st_img = render_sticker_composite(layers, 1500)
        st_png_path = ind_png_dir / f"{name}_Sticker_300DPI.png"
        st_img.save(st_png_path, dpi=(DPI, DPI))

        # 2. Digital Planner PNG (with soft realistic drop shadow)
        pl_img = make_planner_shadow(st_img, blur=16, offset=(0, 10), alpha_val=60)
        pl_png_path = ind_planner_dir / f"{name}_Planner_Sticker.png"
        pl_img.save(pl_png_path, dpi=(DPI, DPI))

        # 3. Individual Cut Line SVG (kiss-cut path)
        w_in, h_in = FP.width_in(halo)
        svg_cut_path = ind_svg_dir / f"{name}_CutLine.svg"
        X.write_svg(svg_cut_path, [("CutContour", halo, "#FF1493")], width_in=w_in, title=f"{a.name} sticker cut line")

        # 4. Individual DXF Cut Line
        dxf_cut_path = ind_dxf_dir / f"{name}_CutLine.dxf"
        FP.write_dxf_scaled(dxf_cut_path, halo)

        # 5. Thumbnail for media kit
        th = X.thumb_layers([(g, FP.rgb(hx)) for _, g, hx in layers], 520, pad=0.04)
        th.save(thumbs / f"{name}_sticker.png")
        th.save(thumbs / f"{name}_c.png")
        th.save(thumbs / f"{name}.png")

        meta.append({
            "index": idx,
            "key": key,
            "name": name,
            "display_name": a.name,
            "width_in": w_in,
            "height_in": h_in,
            "png_file": st_png_path.name,
            "planner_file": pl_png_path.name,
            "svg_file": svg_cut_path.name
        })

    return meta


def build_printable_sheets(files: Path, thumbs: Path) -> List[Dict]:
    """Builds US Letter and A4 Printable Sheets (PNG, PDF, SVG cut lines, Silhouette masks)."""
    sheet_meta = []

    # Page configurations (mm and pixels at 300 DPI)
    # US Letter: 8.5 x 11.0 in = 215.9 x 279.4 mm -> 2550 x 3300 px
    # A4: 210 x 297 mm -> 2480 x 3508 px
    PAGES = {
        "US_Letter": {
            "w_mm": 215.9, "h_mm": 279.4,
            "w_px": 2550, "h_px": 3300,
            "name": "US_Letter"
        },
        "A4": {
            "w_mm": 210.0, "h_mm": 297.0,
            "w_px": 2480, "h_px": 3508,
            "name": "A4"
        }
    }

    # Relative layout coordinates for the 5 animals on a sheet (in mm, sheet origin at bottom-left)
    # 5 positions: Row 1 (top): left, center, right; Row 2 (bottom): mid-left, mid-right
    # Generously spaced so stickers are ~65-70 mm wide (~2.6-2.8 in)
    POSITIONS_LETTER = [
        (46.0, 195.0),    # Top left
        (108.0, 195.0),   # Top center
        (170.0, 195.0),   # Top right
        (72.0, 95.0),     # Bottom left
        (144.0, 95.0),    # Bottom right
    ]
    POSITIONS_A4 = [
        (44.0, 205.0),
        (105.0, 205.0),
        (166.0, 205.0),
        (70.0, 105.0),
        (140.0, 105.0),
    ]

    sheet_png_dir = files / "02_Printable_Sheets" / "PNG_Sheets_300DPI"
    sheet_pdf_dir = files / "02_Printable_Sheets" / "PDF_Sheets_PrintReady"
    sheet_cut_dir = files / "03_Cut_Files_Cricut_Silhouette" / "SVG_Print_Then_Cut"
    sheet_mask_dir = files / "03_Cut_Files_Cricut_Silhouette" / "Silhouette_Black_Masks"

    for d in (sheet_png_dir, sheet_pdf_dir, sheet_cut_dir, sheet_mask_dir):
        d.mkdir(parents=True, exist_ok=True)

    pdf_letter_images = []
    pdf_a4_images = []

    for s_idx, s_def in enumerate(SHEETS, 1):
        s_key = s_def["key"]
        s_title = s_def["title"]
        s_animals = s_def["animals"]
        s_accent = s_def["accent"]

        for p_key, page in PAGES.items():
            w_mm, h_mm = page["w_mm"], page["h_mm"]
            w_px, h_px = page["w_px"], page["h_px"]
            positions = POSITIONS_LETTER if p_key == "US_Letter" else POSITIONS_A4

            # Prepare sheet geometry layers
            # We will collect:
            # 1. sticker_layers: list of (layer_id, geom_placed, hex_col)
            # 2. cut_contours: list of BaseGeometry for cut line SVG
            # 3. filler_layers: decorative stars/hearts with cut lines
            sticker_layers = []
            cut_contours = []

            # Target animal sticker size in mm: width ~60-64 mm
            target_w_mm = 62.0

            for a_key, (pos_x, pos_y) in zip(s_animals, positions):
                a = AN.A[a_key]
                outline = a.outline()
                halo = outline.buffer(3.5, quad_segs=24, join_style=1)
                
                # Scale animal to target width
                ox0, oy0, ox1, oy1 = halo.bounds
                scale_f = target_w_mm / (ox1 - ox0)
                cx_orig = (ox0 + ox1) / 2
                cy_orig = (oy0 + oy1) / 2

                # Transform halo
                halo_placed = affinity.scale(halo, xfact=scale_f, yfact=scale_f, origin=(cx_orig, cy_orig))
                halo_placed = affinity.translate(halo_placed, xoff=pos_x - cx_orig, yoff=pos_y - cy_orig)
                
                cut_contours.append(halo_placed)
                sticker_layers.append((f"{a_key}_halo", halo_placed, "#FFFFFF"))

                # Transform colored layers
                for lid, g, hx in a.svg_layers():
                    g_placed = affinity.scale(g, xfact=scale_f, yfact=scale_f, origin=(cx_orig, cy_orig))
                    g_placed = affinity.translate(g_placed, xoff=pos_x - cx_orig, yoff=pos_y - cy_orig)
                    sticker_layers.append((f"{a_key}_{lid}", g_placed, hx))

            # Add decorative filler mini-stickers
            for f_idx, (f_type, _f_name, f_hex, (fx_pct, fy_pct), f_size) in enumerate(s_def["fillers"]):
                fx_mm = (fx_pct / 215.9) * w_mm
                fy_mm = (fy_pct / 279.4) * h_mm
                if f_type == "star":
                    fg = make_star(fx_mm, fy_mm, f_size)
                elif f_type == "paw":
                    fg = make_paw(fx_mm, fy_mm, f_size)
                else:
                    fg = make_heart(fx_mm, fy_mm, f_size)
                
                f_halo = fg.buffer(2.0, quad_segs=16, join_style=1)
                cut_contours.append(f_halo)
                sticker_layers.append((f"fill_halo_{f_idx}", f_halo, "#FFFFFF"))
                sticker_layers.append((f"fill_{f_idx}", fg, f_hex))

            # Render 300 DPI Transparent PNG of the stickers
            all_cut_union = unary_union(cut_contours)
            # Render against the full sheet dimensions: bounds = (0, 0, w_mm, h_mm)
            sheet_bounds = (0.0, 0.0, w_mm, h_mm)
            
            sheet_canvas = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
            for lid, g, hx in sticker_layers:
                m = X.mask(g, w_px, bounds=sheet_bounds, supersample=2)
                col = Image.new("RGBA", m.size, FP.rgb(hx) + (255,))
                col.putalpha(m)
                sheet_canvas.alpha_composite(col)

            # Create the Print-Ready sheet (White background + Cute Header + Border)
            print_sheet = Image.new("RGB", (w_px, h_px), (255, 255, 255))
            draw = ImageDraw.Draw(print_sheet)

            # Header Banner
            header_h = int(h_px * 0.09)
            draw.rectangle([(0, 0), (w_px, header_h)], fill=(250, 250, 252))
            draw.line([(0, header_h), (w_px, header_h)], fill=(230, 230, 235), width=3)

            # Title & Subtitle in header
            f_title = get_font("Anton-Regular.ttf", 80)
            f_sub = get_font("Poppins-SemiBold.ttf", 38)
            f_brand = get_font("Poppins-Regular.ttf", 32)

            draw.text((w_px // 2, int(header_h * 0.38)), s_title, font=f_title, fill=s_accent, anchor="mm")
            draw.text((w_px // 2, int(header_h * 0.72)), "PRINTABLE STICKER SHEET  *  KISS-CUT LINES INCLUDED",
                      font=f_sub, fill=(100, 100, 110), anchor="mm")

            # Footer
            footer_y = int(h_px * 0.96)
            draw.line([(int(w_px * 0.08), footer_y), (int(w_px * 0.92), footer_y)], fill=(230, 230, 235), width=2)
            draw.text((w_px // 2, int(h_px * 0.978)),
                      f"Print at 100% Scale on Sticker Paper  *  {page['name'].replace('_', ' ')} (300 DPI)  *  Personal & Commercial Use",
                      font=f_brand, fill=(130, 130, 140), anchor="mm")

            # Paste transparent stickers onto the print sheet
            print_sheet.paste(sheet_canvas, (0, 0), mask=sheet_canvas.split()[3])

            # Save PNG files
            sheet_slug = f"Sheet_{s_idx:02d}_{s_key}_{page['name']}"
            png_trans_path = sheet_png_dir / f"{sheet_slug}_Transparent.png"
            png_print_path = sheet_png_dir / f"{sheet_slug}_PrintReady.png"
            
            sheet_canvas.save(png_trans_path, dpi=(DPI, DPI), optimize=True)
            print_sheet.save(png_print_path, dpi=(DPI, DPI), optimize=True)

            # Save single-sheet PDF
            single_pdf_path = sheet_pdf_dir / f"{sheet_slug}.pdf"
            print_sheet.save(single_pdf_path, "PDF", resolution=DPI)

            if p_key == "US_Letter":
                pdf_letter_images.append(print_sheet)
            else:
                pdf_a4_images.append(print_sheet)

            # Save Cricut / Silhouette Print-Then-Cut SVG Cut Lines
            # Cut lines matching sheet dimensions
            cut_svg_path = sheet_cut_dir / f"{sheet_slug}_CutLines.svg"
            w_in = w_mm / MM_PER_IN
            h_in = h_mm / MM_PER_IN
            body = []
            for c_i, cg in enumerate(cut_contours):
                body.append(f'<path fill="none" stroke="#FF0055" stroke-width="0.35" d="{X.path_d(cg, 0, 0, h_mm)}"/>')
            svg_text = (
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_in:.3f}in" height="{h_in:.3f}in" viewBox="0 0 {w_mm:.2f} {h_mm:.2f}">\n'
                f'<title>{s_title} Cut Lines - {page["name"]}</title>\n'
                f'<g id="CutContour">\n' + "\n".join(body) + "\n</g>\n</svg>\n"
            )
            cut_svg_path.write_text(svg_text, encoding="utf-8")

            # Save Silhouette Black Mask PNG (Solid black silhouettes for auto-trace)
            mask_canvas = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
            for cg in cut_contours:
                m = X.mask(cg, w_px, bounds=sheet_bounds, supersample=2)
                blk = Image.new("RGBA", m.size, (0, 0, 0, 255))
                blk.putalpha(m)
                mask_canvas.alpha_composite(blk)
            
            mask_path = sheet_mask_dir / f"{sheet_slug}_SilhouetteMask.png"
            mask_canvas.save(mask_path, dpi=(DPI, DPI), optimize=True)

            sheet_meta.append({
                "sheet_num": s_idx,
                "sheet_key": s_key,
                "title": s_title,
                "page": p_key,
                "print_png": png_print_path.name,
                "trans_png": png_trans_path.name,
                "pdf": single_pdf_path.name,
                "cut_svg": cut_svg_path.name,
                "mask_png": mask_path.name,
                "stickers_count": len(s_animals) + len(s_def["fillers"])
            })

    # Save Multi-Page Master PDFs
    master_letter_pdf = sheet_pdf_dir / "Cute_Animal_Stickers_All_4_Sheets_US_Letter.pdf"
    master_a4_pdf = sheet_pdf_dir / "Cute_Animal_Stickers_All_4_Sheets_A4.pdf"
    
    if pdf_letter_images:
        pdf_letter_images[0].save(master_letter_pdf, "PDF", save_all=True, append_images=pdf_letter_images[1:], resolution=DPI)
    if pdf_a4_images:
        pdf_a4_images[0].save(master_a4_pdf, "PDF", save_all=True, append_images=pdf_a4_images[1:], resolution=DPI)

    return sheet_meta


def build_guide_pdf(guide_path: Path) -> Path:
    """Builds a comprehensive visual printing, cutting, and commercial license PDF guide."""
    # 2 pages: Page 1 = Printing & Cutting Guide, Page 2 = Commercial License & Tips
    S_W, S_H = 2550, 3300   # US Letter @ 300 DPI
    p1 = Image.new("RGB", (S_W, S_H), (255, 255, 255))
    d1 = ImageDraw.Draw(p1)

    f_hero = get_font("Anton-Regular.ttf", 90)
    f_h2 = get_font("Anton-Regular.ttf", 54)
    f_body = get_font("Poppins-Regular.ttf", 34)
    f_bold = get_font("Poppins-Bold.ttf", 36)
    f_small = get_font("Poppins-Regular.ttf", 28)

    # Header
    d1.rectangle([(0, 0), (S_W, 260)], fill=(240, 98, 146))
    d1.text((S_W // 2, 90), "CUTE ANIMAL STICKER SHEETS", font=f_hero, fill=(255, 255, 255), anchor="mm")
    d1.text((S_W // 2, 190), "PRINTING & CUTTING QUICK-START GUIDE", font=get_font("Poppins-Bold.ttf", 42), fill=(255, 240, 245), anchor="mm")

    # Section 1: Choosing Your Sticker Paper
    y = 330
    d1.text((120, y), "1. CHOOSING YOUR STICKER PAPER", font=f_h2, fill=(240, 98, 146))
    y += 75
    bullet_items_1 = [
        ("Matte Sticker Paper:", "Great for planners, bullet journals, paper crafts, and indoor labeling. Easy to write on with gel pens."),
        ("Glossy Vinyl Sticker Paper:", "Vibrant, photographic colors. Recommended for laptops, phone cases, and display art."),
        ("Waterproof Vinyl + Clear Laminate:", "If applying to water bottles, tumblers, or hydroflasks, apply a self-adhesive clear laminate sheet over the printed vinyl before cutting.")
    ]
    for b_title, b_desc in bullet_items_1:
        d1.text((140, y), "•", font=f_bold, fill=(240, 98, 146))
        d1.text((170, y), b_title, font=f_bold, fill=(35, 30, 35))
        y += 45
        d1.text((170, y), b_desc, font=f_body, fill=(70, 70, 75))
        y += 65

    # Section 2: Printer Settings
    y += 30
    d1.text((120, y), "2. PRINTER SETTINGS FOR BEST QUALITY", font=f_h2, fill=(240, 98, 146))
    y += 75
    bullet_items_2 = [
        ("Scale:", "Always set scale to 100% or 'Actual Size'. DO NOT select 'Fit to Page' or 'Shrink to Fit'."),
        ("Print Quality:", "Select 'High' or 'Best' quality in your printer dialogue box."),
        ("Paper Type:", "Set paper type to 'Photo Paper Glossy' or 'Matte Photo Paper' (even when using vinyl), to prevent ink pooling.")
    ]
    for b_title, b_desc in bullet_items_2:
        d1.text((140, y), "•", font=f_bold, fill=(240, 98, 146))
        d1.text((170, y), b_title, font=f_bold, fill=(35, 30, 35))
        y += 45
        d1.text((170, y), b_desc, font=f_body, fill=(70, 70, 75))
        y += 65

    # Section 3: Cutting Instructions (Cricut, Silhouette, Scissors)
    y += 30
    d1.text((120, y), "3. CUTTING YOUR STICKERS", font=f_h2, fill=(240, 98, 146))
    y += 75
    bullet_items_3 = [
        ("Cricut Print Then Cut:", "Upload the transparent PNG to Cricut Design Space as 'Print Then Cut'. Resize to sheet dimensions. The smooth white border cuts automatically!"),
        ("Silhouette Studio:", "Open the sheet PNG. Open the Trace panel, select the sheet, set High Pass off, and click 'Trace Outer Edge' for an instant kiss-cut border."),
        ("Cutting by Hand (Scissor-Friendly):", "Every sticker has a generous, clean white outline contour, making hand-cutting with craft scissors super easy and forgiving.")
    ]
    for b_title, b_desc in bullet_items_3:
        d1.text((140, y), "•", font=f_bold, fill=(240, 98, 146))
        d1.text((170, y), b_title, font=f_bold, fill=(35, 30, 35))
        y += 45
        d1.text((170, y), b_desc, font=f_body, fill=(70, 70, 75))
        y += 65

    # Footer
    d1.line([(120, S_H - 140), (S_W - 120, S_H - 140)], fill=(220, 220, 225), width=2)
    d1.text((S_W // 2, S_H - 80), "Page 1 of 2  •  Cute Animal Sticker Sheets Guide", font=f_small, fill=(140, 140, 145), anchor="mm")

    # Page 2: Commercial License & Digital Planners
    p2 = Image.new("RGB", (S_W, S_H), (255, 255, 255))
    d2 = ImageDraw.Draw(p2)

    d2.rectangle([(0, 0), (S_W, 260)], fill=(0, 160, 170))
    d2.text((S_W // 2, 90), "COMMERCIAL LICENSE & USAGE", font=f_hero, fill=(255, 255, 255), anchor="mm")
    d2.text((S_W // 2, 190), "SMALL BUSINESS COMMERCIAL USE INCLUDED", font=get_font("Poppins-Bold.ttf", 42), fill=(235, 252, 255), anchor="mm")

    y = 330
    d2.text((120, y), "WHAT IS ALLOWED (COMMERCIAL USE):", font=f_h2, fill=(0, 160, 170))
    y += 75
    allowed = [
        "You MAY sell printed physical sticker sheets, die-cut stickers, and labels up to 500 units per design.",
        "You MAY use the stickers on physical handmade products: gift bags, packaging, party favors, craft kits.",
        "No credit or attribution is required on your physical products."
    ]
    for item in allowed:
        d2.text((140, y), "✔", font=f_bold, fill=(0, 160, 170))
        d2.text((180, y), item, font=f_body, fill=(40, 40, 45))
        y += 75

    y += 40
    d2.text((120, y), "WHAT IS STRICTLY PROHIBITED:", font=f_h2, fill=(220, 50, 50))
    y += 75
    prohibited = [
        "You MAY NOT resell, share, redistribute, sub-license or give away these digital files in any format.",
        "You MAY NOT upload these files to Print-On-Demand (POD) websites (e.g. Redbubble, Zazzle, TeePublic, Amazon Merch).",
        "You MAY NOT claim these designs or vector geometries as your own original artwork or trademark."
    ]
    for item in prohibited:
        d2.text((140, y), "✖", font=f_bold, fill=(220, 50, 50))
        d2.text((180, y), item, font=f_body, fill=(40, 40, 45))
        y += 75

    y += 40
    d2.text((120, y), "USING WITH DIGITAL PLANNERS (GOODNOTES / IPAD):", font=f_h2, fill=(0, 160, 170))
    y += 75
    planner_tips = [
        "Your download includes a dedicated folder of pre-cropped individual PNG stickers with realistic drop shadows.",
        "To use in GoodNotes: Open your iPad Files app, drag and drop the PNG stickers directly into your digital notebook or sticker book.",
        "Stickers can be resized, rotated, and positioned freely on any digital page."
    ]
    for item in planner_tips:
        d2.text((140, y), "★", font=f_bold, fill=(0, 160, 170))
        d2.text((180, y), item, font=f_body, fill=(40, 40, 45))
        y += 75

    # Footer
    d2.line([(120, S_H - 140), (S_W - 120, S_H - 140)], fill=(220, 220, 225), width=2)
    d2.text((S_W // 2, S_H - 80), "Page 2 of 2  •  Commercial License Terms", font=f_small, fill=(140, 140, 145), anchor="mm")

    guide_path.parent.mkdir(parents=True, exist_ok=True)
    p1.save(guide_path, "PDF", save_all=True, append_images=[p2], resolution=DPI)
    return guide_path


def package_upload_zips(root: Path, files: Path) -> List[Path]:
    """Packages all files into Etsy-compliant zip archives (<= 20 MB each, <= 5 total upload files)."""
    upload_dir = root / "etsy_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)
    for old in upload_dir.glob("*.zip"):
        old.unlink()

    # 1. Zip 1: Individual Stickers (40 PNGs = 20 transparent + 20 planner drop-shadow)
    z1_path = upload_dir / "01_Individual_Stickers_PNG.zip"
    with zipfile.ZipFile(z1_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "01_Individual_Stickers").rglob("*.*"):
            if p.is_file():
                arcname = p.relative_to(files / "01_Individual_Stickers")
                z.write(p, arcname)

    # 2. Zip 2: Printable PDF Sheets (US Letter & A4 multi-page & single page PDFs)
    z2_path = upload_dir / "02_Printable_Sheets_PDF.zip"
    with zipfile.ZipFile(z2_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Printable_Sheets" / "PDF_Sheets_PrintReady").glob("*.pdf"):
            if p.is_file():
                z.write(p, p.name)

    # 3. Zip 3: Printable PNG Sheets (US Letter & A4 300 DPI Transparent & PrintReady)
    z3_path = upload_dir / "03_Printable_Sheets_PNG.zip"
    with zipfile.ZipFile(z3_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "02_Printable_Sheets" / "PNG_Sheets_300DPI").glob("*.png"):
            if p.is_file():
                z.write(p, p.name)

    # 4. Zip 4: Cricut & Silhouette Cut Files (SVGs, DXFs, and Black Silhouette Masks)
    z4_path = upload_dir / "04_Cricut_Silhouette_Cut_Files.zip"
    with zipfile.ZipFile(z4_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (files / "03_Cut_Files_Cricut_Silhouette").rglob("*.*"):
            if p.is_file():
                arcname = p.relative_to(files / "03_Cut_Files_Cricut_Silhouette")
                z.write(p, arcname)
        for p in (files / "01_Individual_Stickers" / "SVG_Cut_Lines").glob("*.svg"):
            z.write(p, f"Individual_SVG_CutLines/{p.name}")
        for p in (files / "01_Individual_Stickers" / "DXF_Cut_Lines").glob("*.dxf"):
            z.write(p, f"Individual_DXF_CutLines/{p.name}")

    # 5. File 5: Printing & Cutting PDF Guide directly in etsy_upload folder
    guide_upload_path = upload_dir / "Sticker_Printing_And_Cutting_Guide.pdf"
    build_guide_pdf(guide_upload_path)

    zips = [z1_path, z2_path, z3_path, z4_path, guide_upload_path]
    for f in zips:
        mb = f.stat().st_size / (1024 * 1024)
        print(f"  Upload file: {f.name} ({mb:.2f} MB)")
        assert mb <= 20.0, f"File {f.name} exceeds Etsy 20 MB limit ({mb:.2f} MB)"

    assert len(zips) <= 5, f"Too many upload files ({len(zips)} > 5)"
    return zips


def build() -> Dict:
    dirs = listing_dirs(SLUG)
    root, files, work = dirs["root"], dirs["files"], dirs["work"]
    thumbs = work / "thumbs"
    root.mkdir(parents=True, exist_ok=True)

    print("Building Individual Stickers...")
    ind_meta = build_individual_stickers(files, thumbs)
    print(f"  Built {len(ind_meta)} individual stickers.")

    print("Building Printable Sheets (US Letter & A4)...")
    sheet_meta = build_printable_sheets(files, thumbs)
    print(f"  Built {len(sheet_meta)} printable sheets.")

    print("Packaging upload files...")
    upload_files = package_upload_zips(root, files)

    # Save catalog.json
    catalog_data = {
        "slug": SLUG,
        "total_animals": len(ind_meta),
        "total_sheets": len(SHEETS),
        "individual_stickers": ind_meta,
        "sheets": sheet_meta,
        "upload_files": [f.name for f in upload_files]
    }
    (root / "catalog.json").write_text(json.dumps(catalog_data, indent=2), encoding="utf-8")
    print("Pack generation complete!")
    return catalog_data


if __name__ == "__main__":
    build()
