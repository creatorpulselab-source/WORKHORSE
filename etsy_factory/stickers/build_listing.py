"""Media kit and listing builder for Cute Animal Sticker Sheets Pack.

Generates 10 Etsy listing photos (2400x2400 high-res):
01_cover.jpg: Vibrant top-seller open collage cover
02_sheet_overview.jpg: 4-up display of the 4 themed printable sheets
03_individual_stickers.jpg: Grid of all 20 individual die-cut stickers with white bleed borders
04_mockup_laptop.jpg: Realistic laptop lid with die-cut stickers applied
05_mockup_water_bottle.jpg: Pastel water bottle / tumbler with stickers applied
06_mockup_planner.jpg: Open iPad / bullet journal digital planner mockup
07_mockup_desk_sheet.jpg: Flat-lay desk scene with printed sticker sheet
08_print_then_cut_guide.jpg: Cricut / Silhouette / Hand-cut compatibility infographic
09_whats_included.jpg: Itemized breakdown of all digital deliverables
10_commercial_license.jpg: Commercial license terms & guarantee

Also writes:
- listing.json and listing.md with SEO title, tags (13 tags <= 20 chars), rich description, pricing
- runs Etsy listing validator to guarantee 0 errors.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from etsy_factory import kit
from etsy_factory import listing as lst
from etsy_factory.common import listing_dirs
from etsy_factory.stickers import pack as PK
from etsy_factory.typo import cover2
from etsy_factory.typo import export as X
from etsy_factory.typo import media as M

PINK = (240, 98, 146)
TEAL = (0, 160, 170)
SUN = (255, 183, 3)
PURPLE = (126, 87, 194)
GREEN = (76, 175, 80)
INK = (45, 35, 45)
BG = (255, 248, 245)
VBG = (255, 232, 238)

RIBBONS = [((240, 98, 146), (180, 40, 90)), ((0, 160, 170), (0, 100, 110))]

TITLE = "Cute Animal Sticker Sheets Printable, Kawaii Animal Stickers PNG PDF SVG Cut Files for Cricut Silhouette, Planner Stickers Commercial Use"
TAGS = [
    "printable stickers",
    "cute animal stickers",
    "sticker sheets",
    "kawaii stickers",
    "cricut cut file",
    "silhouette stickers",
    "print then cut",
    "planner stickers png",
    "digital stickers",
    "sticker bundle",
    "laptop stickers",
    "animal sticker sheet",
    "commercial use"
]
PRICE = 4.99
LIST_PRICE = 12.99


def create_sheet_overview_card(catalog: Dict, files: Path, out_path: Path) -> Path:
    """Card 02: 4-up presentation of all 4 printable sheets."""
    S = M.SIZE
    base = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(base)

    # Header
    ft = M.fit(d, "4 THEMED STICKER SHEETS", M.anton, S - 260, 150, 70)
    d.text((S // 2, 70), "4 THEMED STICKER SHEETS", font=ft, fill=INK, anchor="ma")
    sub = "US Letter & A4 Sizes  •  Print Ready PDF + 300 DPI PNG  •  Cut Lines Included"
    fs = M.fit(d, sub, M.poppins_x, S - 320, 50, 26)
    d.text((S // 2, 70 + ft.size + 12), sub, font=fs, fill=PINK, anchor="ma")

    # 2x2 Grid of sheets scaled so both rows fit 100% without clipping
    cols = 2
    ch = 880
    cw = int(ch / 1.294)  # ~680 px for US Letter aspect ratio
    col_gap = 70
    row_gap = 70
    total_w = cols * cw + (cols - 1) * col_gap
    x0 = (S - total_w) // 2
    top_y = 70 + ft.size + fs.size + 70

    for i, s_def in enumerate(PK.SHEETS):
        r, c = divmod(i, cols)
        x = x0 + c * (cw + col_gap)
        y = top_y + r * (ch + row_gap)

        sheet_slug = f"Sheet_{i+1:02d}_{s_def['key']}_US_Letter_PrintReady.png"
        sheet_path = files / "02_Printable_Sheets" / "PNG_Sheets_300DPI" / sheet_slug
        if sheet_path.exists():
            sh_img = Image.open(sheet_path).convert("RGBA")
            sh_resized = sh_img.resize((cw, ch), Image.LANCZOS)
            
            # Card backing with drop shadow
            card = M.rounded((cw, ch), 22, (255, 255, 255, 255), outline=(210, 210, 220, 255), width=3)
            M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=70)
            base.paste(sh_resized, (x, y), mask=sh_resized.split()[3])

            # Badge banner under sheet
            pill_w, pill_h = int(cw * 0.88), 60
            px = x + (cw - pill_w) // 2
            py = y + ch - pill_h // 2
            pill = M.rounded((pill_w, pill_h), 30, s_def["accent"] + (255,))
            base.alpha_composite(pill, (px, py))
            draw_b = ImageDraw.Draw(base)
            draw_b.text((px + pill_w // 2, py + pill_h // 2), s_def["title"], font=M.poppins_x(28), fill=(255, 255, 255), anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def create_individual_stickers_grid(catalog: Dict, thumbs: Path, out_path: Path) -> Path:
    """Card 03: 4x5 grid of all 20 individual die-cut stickers."""
    S = M.SIZE
    base = Image.new("RGBA", (S, S), (252, 250, 255, 255))
    d = ImageDraw.Draw(base)

    ft = M.fit(d, "20 INDIVIDUAL DIE-CUT STICKERS", M.anton, S - 260, 150, 70)
    d.text((S // 2, 80), "20 INDIVIDUAL DIE-CUT STICKERS", font=ft, fill=INK, anchor="ma")
    sub = "Each sticker has a clean white bleed border  •  Transparent PNG + SVG Cut Lines"
    fs = M.fit(d, sub, M.poppins_x, S - 320, 48, 26)
    d.text((S // 2, 80 + ft.size + 14), sub, font=fs, fill=TEAL, anchor="ma")

    cols, rows = 5, 4
    top_y = 80 + ft.size + fs.size + 80
    cw = (S - 140 - (cols - 1) * 30) // cols
    ch = (S - top_y - 120 - (rows - 1) * 30) // rows

    ind_stickers = catalog.get("individual_stickers", [])
    for idx, item in enumerate(ind_stickers):
        r, c = divmod(idx, cols)
        x = 70 + c * (cw + 30)
        y = top_y + r * (ch + 30)

        # White rounded card backing
        card = M.rounded((cw, ch), 28, (255, 255, 255, 255), outline=(225, 220, 235, 255), width=2)
        M.shadowed(base, card, (x, y), blur=12, off=(0, 6), alpha=50)

        # Load thumb
        th_path = thumbs / f"{item['name']}_sticker.png"
        if th_path.exists():
            th_img = Image.open(th_path).convert("RGBA")
            th_sz = min(cw - 30, ch - 65)
            th_resized = th_img.resize((th_sz, th_sz), Image.LANCZOS)
            base.paste(th_resized, (x + (cw - th_sz) // 2, y + 16), mask=th_resized.split()[3])

        # Animal label
        label = item["display_name"].capitalize()
        d.text((x + cw // 2, y + ch - 26), label, font=M.poppins_x(26), fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def _get_diecut_sticker(files: Path, prefix: str) -> Image.Image:
    stk_dir = files / "01_Individual_Stickers" / "PNG_Transparent_300DPI"
    hits = list(stk_dir.glob(f"{prefix}_*.png"))
    if not hits:
        raise FileNotFoundError(f"Sticker matching {prefix} not found in {stk_dir}")
    return Image.open(hits[0]).convert("RGBA")


def create_mockup_laptop(files: Path, out_path: Path) -> Path:
    """Card 04: Realistic laptop lid mockup with ComfyUI photorealistic desk background."""
    S = M.SIZE
    mock_dir = Path(r"F:\WORKHORSE\workspace\etsy_mockups")
    bg_path = mock_dir / "laptop_topdown_777.png"
    if not bg_path.exists():
        bg = Image.new("RGBA", (S, S), (242, 240, 245, 255))
    else:
        bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "PERFECT FOR LAPTOPS, TABLETS & CASES", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "PERFECT FOR LAPTOPS, TABLETS & CASES", font=ft, fill=INK, anchor="ma")
    sub = "Print on vinyl sticker paper for vibrant, scratch-resistant custom tech art"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PURPLE, anchor="ma")

    # Place stickers casually on the laptop lid with subtle contact shadows
    stickers_to_place = [
        ("07_Fox", 420, 850, -12, 430),
        ("12_Panda", 980, 780, 8, 440),
        ("01_Cat", 1460, 950, -6, 420),
        ("10_Dino", 700, 1260, 10, 430),
        ("09_Frog", 1260, 1340, -9, 410)
    ]

    for prefix, sx, sy, rot, sz in stickers_to_place:
        stk = _get_diecut_sticker(files, prefix)
        w, h = stk.size
        stk_r = stk.resize((sz, int(sz * h / w)), Image.LANCZOS)
        if rot != 0:
            stk_r = stk_r.rotate(rot, expand=True, resample=Image.BICUBIC)

        sh_layer = Image.new("RGBA", (stk_r.width + 40, stk_r.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_r.split()[3].point(lambda p: int(p * 0.45))
        sh_layer.paste((20, 20, 30, 255), (12, 14), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(14))

        base.alpha_composite(sh_layer, (sx - 20, sy - 20))
        base.alpha_composite(stk_r, (sx, sy))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Instant Download  •  300 DPI Transparent PNG  •  Cricut Cut Lines",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def create_mockup_water_bottle(files: Path, out_path: Path) -> Path:
    """Card 05: Water bottle / Tumbler mockup with ComfyUI photorealistic background."""
    S = M.SIZE
    mock_dir = Path(r"F:\WORKHORSE\workspace\etsy_mockups")
    bg_path = mock_dir / "water_bottle_clean_888.png"
    if not bg_path.exists():
        bg = Image.new("RGBA", (S, S), (245, 248, 250, 255))
    else:
        bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "WATER BOTTLES & HYDROFLASKS", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "WATER BOTTLES & HYDROFLASKS", font=ft, fill=INK, anchor="ma")
    sub = "Add laminate over vinyl for 100% waterproof, dishwasher-safe tumblers"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=TEAL, anchor="ma")

    # Place stickers on the bottle with slight horizontal curvature squeeze
    bottle_stickers = [
        ("09_Frog", 820, 920, 360),
        ("11_Lion", 820, 1420, 360)
    ]
    for prefix, sx, sy, sz in bottle_stickers:
        stk = _get_diecut_sticker(files, prefix)
        w, h = stk.size
        new_w = sz
        new_h = int(sz * h / w)
        stk_r = stk.resize((new_w, new_h), Image.LANCZOS)
        sq_w = int(new_w * 0.94)
        stk_curved = stk_r.resize((sq_w, new_h), Image.LANCZOS)

        sh_layer = Image.new("RGBA", (stk_curved.width + 40, stk_curved.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_curved.split()[3].point(lambda p: int(p * 0.40))
        sh_layer.paste((20, 20, 30, 255), (10, 12), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(12))

        actual_x = 1000 - sq_w // 2
        base.alpha_composite(sh_layer, (actual_x - 20, sy - 20))
        base.alpha_composite(stk_curved, (actual_x, sy))

    # Place decorative stickers on the wooden table beside the bottle
    table_stickers = [
        ("10_Dino", 320, 1720, -15, 380),
        ("02_Bunny", 1680, 1700, 12, 380)
    ]
    for prefix, sx, sy, rot, sz in table_stickers:
        stk = _get_diecut_sticker(files, prefix)
        w, h = stk.size
        stk_r = stk.resize((sz, int(sz * h / w)), Image.LANCZOS)
        if rot != 0:
            stk_r = stk_r.rotate(rot, expand=True, resample=Image.BICUBIC)

        sh_layer = Image.new("RGBA", (stk_r.width + 40, stk_r.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_r.split()[3].point(lambda p: int(p * 0.50))
        sh_layer.paste((15, 15, 20, 255), (10, 16), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(14))

        base.alpha_composite(sh_layer, (sx - 20, sy - 20))
        base.alpha_composite(stk_r, (sx, sy))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Die-Cut Outlines  •  White Bleed Halo  •  Precision Cut Contours",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def create_mockup_journal(files: Path, out_path: Path) -> Path:
    """Card 06: Physical paper journal / bullet planner with ComfyUI photorealistic scene."""
    S = M.SIZE
    mock_dir = Path(r"F:\WORKHORSE\workspace\etsy_mockups\pure_comfy")
    bg_path = mock_dir / "notebook_journal_stickers_553.png"
    if not bg_path.exists():
        bg = Image.new("RGBA", (S, S), (250, 247, 244, 255))
    else:
        bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "PERFECT FOR JOURNALS & PLANNERS", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "PERFECT FOR JOURNALS & PLANNERS", font=ft, fill=INK, anchor="ma")
    sub = "Decorate weekly spreads, bullet journals, scrapbooks, and notebooks"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PINK, anchor="ma")

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Printable Sticker Sheets  •  Pre-Cropped Digital Planner PNGs  •  Instant Download",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def create_mockup_desk_sheet(files: Path, out_path: Path) -> Path:
    """Card 07: Print-at-home craft workspace flat-lay with ComfyUI photorealistic backdrop."""
    S = M.SIZE
    mock_dir = Path(r"F:\WORKHORSE\workspace\etsy_mockups")
    bg_path = mock_dir / "desk_craft_sheet_315.png"
    if not bg_path.exists():
        bg = Image.new("RGBA", (S, S), (248, 244, 240, 255))
    else:
        bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "PRINT AT HOME STICKER SHEETS", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "PRINT AT HOME STICKER SHEETS", font=ft, fill=INK, anchor="ma")
    sub = "Print on glossy or matte sticker paper • Cut with scissors or craft machine"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PINK, anchor="ma")

    # Place printed sheet on the cutting mat with realistic paper frame & shadow
    sheet_path = files / "02_Printable_Sheets" / "PNG_Sheets_300DPI" / "Sheet_01_kawaii_pets_US_Letter_PrintReady.png"
    if sheet_path.exists():
        sheet_im = Image.open(sheet_path).convert("RGBA")
        sh_w = 1080
        sh_h = int(sh_w * sheet_im.height / sheet_im.width)
        sheet_scaled = sheet_im.resize((sh_w, sh_h), Image.LANCZOS)

        sheet_frame = Image.new("RGBA", (sh_w + 16, sh_h + 16), (255, 255, 255, 255))
        sheet_frame.paste(sheet_scaled, (8, 8), mask=sheet_scaled.split()[3])

        rot = -3
        sheet_rot = sheet_frame.rotate(rot, expand=True, resample=Image.BICUBIC)

        sh_layer = Image.new("RGBA", (sheet_rot.width + 60, sheet_rot.height + 60), (0, 0, 0, 0))
        sh_alpha = sheet_rot.split()[3].point(lambda p: int(p * 0.45))
        sh_layer.paste((15, 15, 25, 255), (20, 24), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(18))

        place_x = (S - sheet_rot.width) // 2 + 60
        place_y = 660
        base.alpha_composite(sh_layer, (place_x - 30, place_y - 30))
        base.alpha_composite(sheet_rot, (place_x, place_y))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Ready to Print  •  US Letter & A4 Sizes  •  PDF & PNG Formats",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def create_print_then_cut_card(out_path: Path) -> Path:
    """Card 08: Visual Print-Then-Cut Guide."""
    S = M.SIZE
    base = Image.new("RGBA", (S, S), (255, 252, 248, 255))
    d = ImageDraw.Draw(base)

    ft = M.fit(d, "HOW PRINT & CUT WORKS", M.anton, S - 260, 150, 70)
    d.text((S // 2, 80), "HOW PRINT & CUT WORKS", font=ft, fill=INK, anchor="ma")
    sub = "Simple 3-step process for Cricut, Silhouette, or Scissors"
    fs = M.fit(d, sub, M.poppins_x, S - 320, 52, 28)
    d.text((S // 2, 80 + ft.size + 14), sub, font=fs, fill=TEAL, anchor="ma")

    # 3 Steps cards horizontally or stacked
    steps = [
        ("STEP 1: PRINT", "Print the sheet at 100% scale on your favorite sticker paper or printable vinyl using standard inkjet/laser printer.", SUN),
        ("STEP 2: CUT", "Load into Cricut / Silhouette with the included SVG cut lines for automated kiss-cut, OR cut with scissors using the clean white halos.", PINK),
        ("STEP 3: ENJOY", "Peel and stick to laptops, water bottles, planners, scrapbooks, phone cases, gift bags, and party favors!", GREEN)
    ]
    card_w, card_h = S - 240, 360
    top_y = 80 + ft.size + fs.size + 90

    for i, (title, desc, accent) in enumerate(steps):
        cy = top_y + i * (card_h + 50)
        card = M.rounded((card_w, card_h), 32, (255, 255, 255, 255), outline=(225, 220, 230, 255), width=3)
        M.shadowed(base, card, (120, cy), blur=16, off=(0, 8), alpha=60)
        
        # Pill badge for step number
        pill = M.rounded((360, 75), 36, accent + (255,))
        base.paste(pill, (160, cy + 40), mask=pill.split()[3])
        draw_c = ImageDraw.Draw(base)
        draw_c.text((160 + 180, cy + 77), title, font=M.poppins_x(36), fill=(255, 255, 255), anchor="mm")

        # Description text
        # Wrap desc
        words = desc.split(" ")
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if draw_c.textlength(" ".join(cur), font=M.poppins(36)) > (card_w - 120):
                cur.pop()
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))
        
        text_y = cy + 155
        for ln in lines:
            draw_c.text((160, text_y), ln, font=M.poppins(36), fill=(60, 50, 65), anchor="la")
            text_y += 50

    # Bottom compatibility badges
    badges_y = top_y + 3 * (card_h + 50) + 40
    d.text((S // 2, badges_y), "COMPATIBLE WITH:", font=M.anton(46), fill=INK, anchor="mm")
    apps = ["Cricut Design Space", "Silhouette Studio", "Brother ScanNCut", "GoodNotes", "Notability", "Hand Scissors"]
    ax = 140
    for app in apps:
        pw = int(d.textlength(app, font=M.poppins_x(28))) + 44
        pill = M.rounded((pw, 58), 26, (240, 240, 248, 255), outline=TEAL + (255,), width=2)
        base.paste(pill, (ax, badges_y + 40), mask=pill.split()[3])
        draw_a = ImageDraw.Draw(base)
        draw_a.text((ax + pw // 2, badges_y + 69), app, font=M.poppins_x(28), fill=INK, anchor="mm")
        ax += pw + 18

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def build(mockups: bool = True) -> Dict:
    dirs = listing_dirs(PK.SLUG)
    root, files, work = dirs["root"], dirs["files"], dirs["work"]
    thumbs = work / "thumbs"
    imgs = root / "images"
    imgs.mkdir(parents=True, exist_ok=True)

    catalog: Dict = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    n_animals = catalog.get("total_animals", 20)
    n_sheets = catalog.get("total_sheets", 4)

    # 1. Image 01: Top seller cover
    chips = [PINK, TEAL, SUN, PURPLE, GREEN]
    cover2.vibrant(
        catalog["individual_stickers"], thumbs, imgs / "01_cover.jpg",
        "20+", "PRINTABLE STICKER SHEETS", ["CUTE ANIMAL", "STICKER PACK"],
        "PRINTABLE PDF + PNG  *  CRICUT CUT LINES",
        RIBBONS, (40, 28, 36), VBG,
        [
            ("PNG", "300 DPI\nTransparent", chips[0]),
            ("PDF", "Print\nReady", chips[1]),
            ("CUT", "SVG Lines\nIncluded", chips[2]),
            ("SIZES", "US Letter\n& A4", chips[3]),
            ("USE", "Commercial\nIncluded", chips[4])
        ]
    )

    # 2. Image 02: Sheet overview
    create_sheet_overview_card(catalog, files, imgs / "02_sheet_overview.jpg")

    # 3. Image 03: Individual stickers
    create_individual_stickers_grid(catalog, thumbs, imgs / "03_individual_stickers.jpg")

    # 4. Image 04: Laptop Mockup
    create_mockup_laptop(files, imgs / "04_mockup_laptop.jpg")

    # 5. Image 05: Water Bottle Mockup
    create_mockup_water_bottle(files, imgs / "05_mockup_water_bottle.jpg")

    # 6. Image 06: Journal & Planner Mockup
    create_mockup_journal(files, imgs / "06_mockup_journal.jpg")

    # 7. Image 07: Sheet Flat-lay Craft Desk Scene
    create_mockup_desk_sheet(files, imgs / "07_mockup_desk_sheet.jpg")

    # 8. Image 08: Print-then-cut guide
    create_print_then_cut_card(imgs / "08_print_then_cut_guide.jpg")

    # 9. Image 09: What's included card
    M.info_card(
        imgs / "09_whats_included.jpg", "What's in your download", "instant digital download",
        [
            ("4 Sheets", "Printable Sticker Sheets in both US Letter & A4 sizes (PDF & 300 DPI PNG)"),
            ("20 Individual PNG", "High-res 300 DPI transparent PNGs with crisp white die-cut bleed borders"),
            ("20 Planner PNG", "Digital planner stickers pre-cropped with soft realistic contact shadows"),
            ("Cut Lines (SVG/DXF)", "Print-Then-Cut SVG cut contours aligned 1:1 to every sheet and sticker"),
            ("Silhouette Masks", "Solid black silhouette PNG masks for instant auto-trace in Silhouette Studio"),
            ("Print Guide & License", "Complete paper recommendations, printer setup tips, and commercial license")
        ],
        PINK, INK, BG, footer=f"{n_sheets} themed sheets • {n_animals} original animal designs • 5 zip & PDF files"
    )

    # 10. Image 10: Commercial license card
    M.info_card(
        imgs / "10_commercial_license.jpg", "Commercial use included", "small business friendly",
        [
            ("YES", "Sell physical printed sticker sheets, die-cut stickers, and labels up to 500 units"),
            ("YES", "Use on physical handmade packaging, gift bags, party decor, and craft kits"),
            ("NO CREDIT", "No credit or attribution required on your physical products"),
            ("NO RESALE", "Strictly no digital reselling, sharing, copying, or uploading to POD sites"),
            ("100% ORIGINAL", "Original vector geometry - completely brand-safe and trademark-free")
        ],
        TEAL, INK, BG, footer="Guaranteed high-resolution 300 DPI files • Questions? Message the shop anytime"
    )

    print("All 10 listing images created:")
    for p in sorted(imgs.glob("[0-9][0-9]_*.jpg")):
        print(f"  {p.name}")

    # Generate listing metadata and description
    title = TITLE
    if len(title) > 140:
        title = title[:140].rsplit(" ", 1)[0].rstrip(",")

    animal_names = ", ".join(m["display_name"].capitalize() for m in catalog.get("individual_stickers", []))

    desc = (
        f"Add adorable charm to your planners, crafts, and physical products with this pack of {n_animals} Cute Animal Sticker Sheets!\n\n"
        "Includes 4 themed printable sticker sheets (in both US Letter and A4 formats), plus 20 individual die-cut PNG stickers with smooth white bleed contours, "
        "matching Cricut / Silhouette cut lines, and digital planner files with realistic drop shadows.\n\n"
        f"FEATURED ANIMALS ({n_animals} TOTAL):\n"
        f"{animal_names}.\n\n"
        "4 THEMED STICKER SHEETS INCLUDED:\n"
        "1. Kawaii Pets & Farm: Cat, Bunny, Pig, Cow, Mouse (with mini paws & hearts)\n"
        "2. Woodland & Dino Buddies: Bear, Fox, Owl, Frog, Dino (with mini stars & acorns)\n"
        "3. Safari & Jungle Pals: Lion, Panda, Koala, Giraffe, Hippo (with tropical stars & paws)\n"
        "4. Magical Cuties & Birds: Penguin, Chick, Sheep, Elephant, Unicorn (with sparkle hearts & stars)\n\n"
        "WHAT YOU RECEIVE:\n"
        "- 4 Printable Sticker Sheets in US Letter size (300 DPI PNG & vector PDF)\n"
        "- 4 Printable Sticker Sheets in A4 size (300 DPI PNG & vector PDF)\n"
        "- 20 Individual Die-Cut PNG Stickers (300 DPI transparent with crisp white contour)\n"
        "- 20 Digital Planner PNG Stickers (with realistic contact drop shadow for GoodNotes / Notability)\n"
        "- 4 Sheet-level SVG Cut Lines for Cricut Print Then Cut\n"
        "- 20 Individual SVG & DXF Cut Lines for single die-cut machines\n"
        "- 4 Silhouette Studio Black Silhouette Mask PNGs\n"
        "- Multi-page Master Print PDFs for instant home printing\n"
        "- Comprehensive Sticker Printing & Cutting PDF Guide\n\n"
        "HOW TO USE:\n"
        "- CRICUT: Import the PNG sheet into Cricut Design Space as Print Then Cut, overlay the SVG cut line, print on sticker paper, and kiss-cut!\n"
        "- SILHOUETTE: Open the sheet PNG in Silhouette Studio, open Trace panel, select outer edge for instant cut lines.\n"
        "- BY HAND: Print the high-resolution PDF on matte or glossy sticker paper and cut out with craft scissors (the white outline makes hand-cutting super easy!).\n"
        "- DIGITAL PLANNERS: Drag and drop the pre-cropped PNGs directly into GoodNotes, Notability, or Penly on your iPad / tablet.\n\n"
        "COMMERCIAL LICENSE TERMS:\n"
        "- Small business commercial use is included up to 500 physical printed sticker units per design.\n"
        "- You may sell physical printed sticker sheets, die-cut stickers, and handmade crafts.\n"
        "- You MAY NOT resell, share, redistribute the digital files, or upload them to Print-On-Demand (POD) websites.\n\n"
        "DIGITAL DOWNLOAD - No physical product will be shipped. Files are available immediately upon purchase."
    )

    data = lst.write_listing(
        root,
        title=title,
        tags=TAGS,
        description=desc,
        price_usd=PRICE,
        sale_hint=f"list ${LIST_PRICE:.2f}, run a 60% sale to show discount",
        category="Craft Supplies & Tools > Patterns & How To > Digital",
        materials="digital files, png, svg, pdf, dxf",
        whats_in_the_files=[
            f"4 themed sticker sheets x (US Letter & A4) in PDF and 300 DPI PNG",
            f"20 individual die-cut PNGs + 20 digital planner shadow PNGs",
            f"Cricut Print-Then-Cut SVG cut lines and DXF files",
            f"Printing & cutting PDF guide + commercial license"
        ],
        notes=["All animal face geometries and sticker cut paths are original shop vectors."]
    )

    print("Listing written successfully:")
    print(json.dumps({
        "title_chars": data["title_chars"],
        "tags_count": len(data["tags"]),
        "problems": data["validation_problems"],
        "upload_files": [f.name for f in (root / "etsy_upload").glob("*")]
    }, indent=2))
    return data


if __name__ == "__main__":
    build(mockups="--no-mockups" not in sys.argv)
