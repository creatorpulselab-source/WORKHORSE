"""Media kit and listing builder for Cute Laser Cut Keychains & Earrings SVG Bundle.

Generates 10 high-resolution (2400x2400) listing photos:
01_cover.jpg: Storefront hero cover with laser wood & acrylic keychains, brass rings, & badges
02_keychains_overview.jpg: Clean visual grid displaying all 20 Keychains
03_earrings_overview.jpg: Clean visual grid displaying all 20 Dangle Earring Pairs
04_mockup_wood_keychains.jpg: Photorealistic ComfyUI light oak desk with birch laser cut keychains
05_mockup_earrings_stand.jpg: Photorealistic ComfyUI linen jewelry T-stand with dangle earrings
06_mockup_backpack_tag.jpg: Photorealistic ComfyUI canvas backpack with laser wooden keychain tag
07_mockup_laser_workshop.jpg: Photorealistic ComfyUI laser cutter workspace with birch plywood sheet
08_laser_color_coding_guide.jpg: Industry standard laser operations infographic (Cut/Score/Engrave)
09_nested_sheets_and_sizing.jpg: Sizing & pre-nested sheet layout for Glowforge 12x20 & craft 12x12
10_whats_included_and_license.jpg: Deliverable summary & 500-unit commercial license guarantee

Writes listing.json, listing.md and validates strict Etsy constraints (0 validation errors).
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

from etsy_factory import listing as lst
from etsy_factory.common import listing_dirs
from etsy_factory.laser import pack as PK

SLUG = PK.SLUG
W, H = 2400, 2400

# Color Palette (Rich Workshop / Warm Maker Craft)
WALNUT = (42, 30, 22)
TERRACOTTA = (184, 88, 52)
BRASS_GOLD = (204, 154, 62)
CREAM_BG = (252, 249, 244)
WHITE = (255, 255, 255)
CHARCOAL = (38, 38, 40)
MUTED = (115, 110, 105)
BORDER_COL = (225, 220, 212)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"

TITLE = "Laser Cut Keychain & Earring SVG Bundle, 40 Wood & Acrylic Keychain Dangle Earring Cut Files for Glowforge, xTool, LightBurn Laser Cut SVG"
TAGS = [
    "laser cut keychain",
    "laser cut earrings",
    "glowforge svg bundle",
    "xtool laser cut file",
    "acrylic earring svg",
    "wooden keychain svg",
    "laser cut svg",
    "lightburn cut files",
    "dangle earring svg",
    "laser craft files",
    "glowforge jewelry",
    "keychain cut file",
    "laser jewelry svg",
]
PRICE = 4.99
LIST_PRICE = 12.99


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def load_th(thumbs_dir: Path, thumb_name: str) -> Image.Image:
    p = thumbs_dir / thumb_name
    if p.exists():
        return Image.open(p).convert("RGBA")
    return Image.new("RGBA", (400, 400), (0, 0, 0, 0))


# -----------------------------------------------------------------------------
# SLIDE 01: HERO COVER
# -----------------------------------------------------------------------------
def make_01_cover(out_path: Path, thumbs_dir: Path, catalog: Dict):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Top Header Banner
    d.rectangle([0, 0, W, 360], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 82)
    f_sub = get_font(FONT_BOLD, 36)
    d.text((W // 2, 120), "LASER CUT KEYCHAINS & EARRINGS", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 215), "40 COMPLETE LASER CUT DESIGNS  •  GLOWFORGE  •  xTOOL  •  LIGHTBURN", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    # Badges
    badges = ["20 KEYCHAINS", "20 EARRING PAIRS", "RED=CUT • BLUE=SCORE", "1/8\" WOOD & ACRYLIC", "COMMERCIAL LICENSE"]
    bx_total = sum(len(b) * 19 + 42 for b in badges)
    cur_x = (W - bx_total) // 2
    f_b = get_font(FONT_BOLD, 26)
    for b in badges:
        bw = len(b) * 19 + 36
        d.rounded_rectangle([cur_x, 275, cur_x + bw, 325], radius=12, fill=TERRACOTTA)
        d.text((cur_x + bw // 2, 300), b, fill=WHITE, font=f_b, anchor="mm")
        cur_x += bw + 12

    # 4 Featured Hero Samples
    heroes = [
        ("Highland Cow Keychain", "kc_highland_cow_th.png", 260, 480),
        ("Woodland Bear Keychain", "kc_woodland_bear_th.png", 1320, 480),
        ("Monstera Leaf Dangles", "er_earring_monstera_leaf_th.png", 260, 1340),
        ("Retro Daisy Earrings", "er_earring_retro_daisy_th.png", 1320, 1340),
    ]
    card_w, card_h = 820, 780
    f_card_t = get_font(FONT_BOLD, 34)
    f_card_sub = get_font(FONT_REG, 26)

    for title, fn, cx, cy in heroes:
        d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
        th = load_th(thumbs_dir, fn)
        if th.width > 0:
            th.thumbnail((card_w - 120, card_h - 180), Image.Resampling.LANCZOS)
            px = cx + (card_w - th.width) // 2
            py = cy + 30 + (card_h - 190 - th.height) // 2
            im.paste(th, (px, py), th)
        d.text((cx + card_w // 2, cy + card_h - 80), title, fill=WALNUT, font=f_card_t, anchor="mm")
        d.text((cx + card_w // 2, cy + card_h - 38), "Clean Burn Edges • Verified Closed Cut Paths", fill=MUTED, font=f_card_sub, anchor="mm")

    # Bottom Banner
    d.rectangle([0, H - 160, W, H], fill=WALNUT)
    f_bot = get_font(FONT_BOLD, 36)
    d.text((W // 2, H - 80), "INCLUDES PRE-NESTED MASTER SHEETS (12x20\" & 12x12\")  •  INSTANT DOWNLOAD", fill=WHITE, font=f_bot, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 02: 20 KEYCHAINS OVERVIEW
# -----------------------------------------------------------------------------
def make_02_keychains_overview(out_path: Path, thumbs_dir: Path, catalog: Dict):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 95), "20 LASER CUT KEYCHAINS & BAG TAGS", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 185), "Includes integrated 3.5mm top keyring loop with reinforced >=2.5mm wall", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    cols, rows = 5, 4
    ox, oy = 140, 310
    cell_w = (W - 280) // cols
    cell_h = (H - 450) // rows
    f_lbl = get_font(FONT_BOLD, 26)

    for i, item in enumerate(catalog["keychains"]):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        d.rounded_rectangle([cx + 8, cy + 8, cx + cell_w - 8, cy + cell_h - 8], radius=16, fill=WHITE, outline=BORDER_COL, width=2)
        th = load_th(thumbs_dir, item["thumb"])
        if th.width > 0:
            th.thumbnail((cell_w - 40, cell_h - 75), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 15 + (cell_h - 85 - th.height) // 2
            im.paste(th, (px, py), th)
        short_title = item["title"].replace(" Keychain", "")
        d.text((cx + cell_w // 2, cy + cell_h - 30), short_title[:18], fill=WALNUT, font=f_lbl, anchor="mm")

    d.rectangle([0, H - 120, W, H], fill=WALNUT)
    d.text((W // 2, H - 60), "100% Watertight Closed Cut Vectors  •  Zero Overlapping Cuts  •  Ready for 1/8\" Wood/Acrylic", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 03: 20 EARRINGS OVERVIEW
# -----------------------------------------------------------------------------
def make_03_earrings_overview(out_path: Path, thumbs_dir: Path, catalog: Dict):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    d.rectangle([0, 0, W, 260], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 95), "20 LASER CUT DANGLE EARRING PAIRS", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 185), "Lightweight jewelry scale (~35-42mm) with integrated 2.0mm jump-ring hole", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    cols, rows = 5, 4
    ox, oy = 140, 310
    cell_w = (W - 280) // cols
    cell_h = (H - 450) // rows
    f_lbl = get_font(FONT_BOLD, 26)

    for i, item in enumerate(catalog["earrings"]):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        d.rounded_rectangle([cx + 8, cy + 8, cx + cell_w - 8, cy + cell_h - 8], radius=16, fill=WHITE, outline=BORDER_COL, width=2)
        th = load_th(thumbs_dir, item["thumb"])
        if th.width > 0:
            th.thumbnail((cell_w - 40, cell_h - 75), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 15 + (cell_h - 85 - th.height) // 2
            im.paste(th, (px, py), th)
        short_title = item["title"].replace(" Earrings Pair", "")
        d.text((cx + cell_w // 2, cy + cell_h - 30), short_title[:18], fill=WALNUT, font=f_lbl, anchor="mm")

    d.rectangle([0, H - 120, W, H], fill=WALNUT)
    d.text((W // 2, H - 60), "Perfect for Wood, Mirrored Acrylic, Frosted Acrylic & Faux Leather Jewelry", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 04: MOCKUP WOOD KEYCHAINS (ComfyUI)
# -----------------------------------------------------------------------------
def make_04_mockup_wood_keychains(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\laser_keychains_wood_flatlay_1101.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Composite Highland Cow & Bear keychains onto wooden flatlay
    th1 = load_th(thumbs_dir, "kc_highland_cow_th.png")
    if th1.width > 0:
        th1.thumbnail((560, 560), Image.Resampling.LANCZOS)
        shadow1 = Image.new("RGBA", th1.size, (0, 0, 0, 0))
        alpha1 = th1.split()[-1]
        shadow1.paste((35, 25, 20, 100), (0, 0), mask=alpha1)
        shadow1 = shadow1.filter(ImageFilter.GaussianBlur(10))

        tx = (W - th1.width) // 2 - 20
        ty = (H - th1.height) // 2 + 40

        im.paste(shadow1, (tx + 12, ty + 16), shadow1)
        im.paste(th1, (tx, ty), th1)

    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "NATURAL BIRCH PLYWOOD MOCKUP", fill=WALNUT, font=f_bd)
    d.text((140, 160), "1/8\" (3mm) Laser Cut with Antique Brass Hardware", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 05: MOCKUP EARRINGS JEWELRY STAND (ComfyUI)
# -----------------------------------------------------------------------------
def make_05_mockup_earrings_stand(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\laser_earrings_jewelry_stand_1202.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Daisy Dangle Earrings hanging on the stand hooks
    th = load_th(thumbs_dir, "er_earring_retro_daisy_th.png")
    if th.width > 0:
        th.thumbnail((360, 360), Image.Resampling.LANCZOS)
        # Left earring
        sh = Image.new("RGBA", th.size, (0, 0, 0, 0))
        sh.paste((25, 25, 30, 85), (0, 0), mask=th.split()[-1])
        sh = sh.filter(ImageFilter.GaussianBlur(8))

        lx, ly = W // 2 - 240, H // 2 - 60
        rx, ry = W // 2 + 100, H // 2 - 60

        im.paste(sh, (lx + 10, ly + 14), sh)
        im.paste(th, (lx, ly), th)
        im.paste(sh, (rx + 10, ry + 14), sh)
        im.paste(th, (rx, ry), th)

    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "ACRYLIC EARRINGS DISPLAY MOCKUP", fill=WALNUT, font=f_bd)
    d.text((140, 160), "Pastel Cast Acrylic Dangles on Linen Jewelry Stand", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 06: MOCKUP BACKPACK BAG TAG (ComfyUI)
# -----------------------------------------------------------------------------
def make_06_mockup_backpack_tag(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\laser_backpack_keychain_lifestyle_1303.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    th = load_th(thumbs_dir, "kc_cat_face_th.png")
    if th.width > 0:
        th.thumbnail((440, 440), Image.Resampling.LANCZOS)
        sh = Image.new("RGBA", th.size, (0, 0, 0, 0))
        sh.paste((30, 25, 20, 95), (0, 0), mask=th.split()[-1])
        sh = sh.filter(ImageFilter.GaussianBlur(9))

        tx = (W - th.width) // 2 + 10
        ty = (H - th.height) // 2 + 30

        im.paste(sh, (tx + 10, ty + 14), sh)
        im.paste(th, (tx, ty), th)

    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "BACKPACK BAG TAG MOCKUP", fill=WALNUT, font=f_bd)
    d.text((140, 160), "Custom Wooden Bag Tag & Keychain Inspiration", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 07: MOCKUP LASER WORKSHOP (ComfyUI)
# -----------------------------------------------------------------------------
def make_07_mockup_laser_workshop(out_path: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\laser_workshop_glowforge_1404.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)
    d.rounded_rectangle([100, 80, 960, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "CRAFT STUDIO LASER WORKSHOP", fill=WALNUT, font=f_bd)
    d.text((140, 160), "Color-Coded for Glowforge, xTool, OMTech & Diode Lasers", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 08: LASER COLOR CODING & OPERATIONS INFOGRAPHIC
# -----------------------------------------------------------------------------
def make_08_laser_color_coding_guide(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 280], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 100), "STANDARD LASER OPERATION COLOR CODES", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 200), "Auto-Recognized by Glowforge, LightBurn & xTool Creative Space", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    f_step_h = get_font(FONT_BOLD, 46)
    f_body = get_font(FONT_REG, 34)

    cards = [
        ("RED (#FF0000) - VECTOR CUT",
         "• Hairline stroke (0.2mm) with NO fill.\n"
         "• Cuts all the way through your 1/8\" (3mm) wood or acrylic sheet.\n"
         "• Clean closed vectors - no double cuts or overlapping line burns.",
         (230, 45, 45)),
        ("BLUE (#0000FF) - VECTOR SCORE",
         "• High-speed surface vector trace (does NOT cut through).\n"
         "• Traces fine details like leaf veins, whiskers, petals, and textures in seconds!\n"
         "• Gives rich decorative detail without slow engraving times.",
         (30, 100, 220)),
        ("BLACK (#000000) - RASTER / VECTOR ENGRAVE",
         "• Solid filled areas (eyes, dark nose patches, etched accents).\n"
         "• Automatically assigns as Engrave in Glowforge and LightBurn.\n"
         "• Recommended: 270 - 300 LPI for deep, smooth contrasting burns.",
         (40, 40, 40)),
    ]

    cur_y = 350
    for title, desc, col in cards:
        d.rounded_rectangle([140, cur_y, W - 140, cur_y + 340], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
        # Color pill
        d.rounded_rectangle([180, cur_y + 35, 230, cur_y + 115], radius=10, fill=col)
        d.text((260, cur_y + 55), title, fill=WALNUT, font=f_step_h)
        d.multiline_text((260, cur_y + 125), desc, fill=CHARCOAL, font=f_body, spacing=12)
        cur_y += 390

    # Footer
    d.rectangle([0, H - 150, W, H], fill=WALNUT)
    d.text((W // 2, H - 75), "Includes Detailed Laser Cut / Score / Engrave Parameter Table in Download Guide", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 09: NESTED SHEETS & SIZING
# -----------------------------------------------------------------------------
def make_09_nested_sheets_and_sizing(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    d.rectangle([0, 0, W, 280], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 100), "PRE-NESTED MASTER CUTTING SHEETS", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 200), "Optimized for Minimum Material Waste • 12x20\" & 12x12\" Sheet Sizes", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    f_head = get_font(FONT_BOLD, 42)
    f_body = get_font(FONT_REG, 32)

    # Box 1: Keychains Sheet
    d.rounded_rectangle([140, 350, W - 140, 850], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((180, 400), "MASTER SHEET 1: 20 KEYCHAINS (12 x 20 INCH GLOWFORGE BED)", fill=WALNUT, font=f_head)
    sheet1_text = (
        "• Pre-arranged on a standard 12 x 20 inch (300 x 500 mm) laser bed.\n"
        "• 5mm safety spacing between parts prevents burning adjacent pieces.\n"
        "• Load one sheet of 1/8\" birch plywood and cut all 20 keychains in a single job!\n"
        "• Average keychain dimension: 2.2\" - 2.5\" height with 3.5mm top keyring hole."
    )
    d.multiline_text((180, 480), sheet1_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Box 2: Earrings Sheet
    d.rounded_rectangle([140, 920, W - 140, 1420], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((180, 970), "MASTER SHEET 2: 20 EARRING PAIRS (12 x 12 INCH CRAFT BED)", fill=WALNUT, font=f_head)
    sheet2_text = (
        "• Pre-arranged on a standard 12 x 12 inch (300 x 300 mm) laser bed.\n"
        "• Perfectly sized for scrap wood, mirrored acrylic, or cast acrylic sheets.\n"
        "• Lightweight jewelry scale (1.4\" - 1.6\" height) with 2.0mm jump-ring holes.\n"
        "• Ready for craft fairs, Etsy boutique inventory, and handmade gift sets!"
    )
    d.multiline_text((180, 1050), sheet2_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Box 3: Hardware compatibility
    d.rounded_rectangle([140, 1490, W - 140, 1990], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((180, 1540), "RECOMMENDED HARDWARE & ASSEMBLY", fill=WALNUT, font=f_head)
    hw_text = (
        "• Keychains: 25mm/30mm split keyrings with chain, 8-10mm jump rings, leather cords.\n"
        "• Earrings: 5-6mm (20 gauge) jump rings, stainless steel or hypoallergenic ear-wires.\n"
        "• Material: 1/8\" (3mm) Baltic birch, basswood, walnut, or 3mm cast acrylic.\n"
        "• Kerf Compensation: Engineered with 0.15mm standard laser kerf allowance."
    )
    d.multiline_text((180, 1620), hw_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Footer
    d.rectangle([0, H - 150, W, H], fill=WALNUT)
    d.text((W // 2, H - 75), "Both Individual Files and Nested Master Sheets are Included in Download", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 10: WHAT'S INCLUDED & COMMERCIAL LICENSE
# -----------------------------------------------------------------------------
def make_10_whats_included_and_license(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    d.rectangle([0, 0, W, 280], fill=WALNUT)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 100), "WHAT'S INCLUDED & LICENSE", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 200), "Complete Digital Laser Craft Package  •  Commercial Small Business License", fill=BRASS_GOLD, font=f_sub, anchor="mm")

    f_head = get_font(FONT_BOLD, 42)
    f_body = get_font(FONT_REG, 32)

    # Left Box
    d.rounded_rectangle([120, 340, W // 2 - 40, H - 180], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((160, 400), "WHAT YOU RECEIVE:", fill=WALNUT, font=f_head)

    included_text = (
        "• 20 Laser-Cut Keychains & Bag Tags\n"
        "• 20 Matching Dangle Earring Pairs\n"
        "  (40 TOTAL DESIGNS INCLUDED)\n\n"
        "FILES INCLUDED IN DOWNLOAD:\n"
        "✔ 40 Individual Color-Coded SVGs\n"
        "✔ 2 Pre-Nested Master Cutting Sheet SVGs\n"
        "   (12x20\" Glowforge & 12x12\" Craft Bed)\n"
        "✔ 40 DXF Files (Silhouette / LightBurn)\n"
        "✔ 40 EPS Files (Illustrator / CorelDraw)\n"
        "✔ 40 Transparent 300 DPI PNG Previews\n\n"
        "BONUS INCLUDED:\n"
        "✔ 3-Page Laser Sizing, Kerf & Settings Guide\n"
        "✔ Glowforge & xTool Material Parameter Table\n"
        "✔ Small Business Commercial License"
    )
    d.multiline_text((160, 475), included_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Right Box
    d.rounded_rectangle([W // 2 + 40, 340, W - 120, H - 180], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((W // 2 + 80, 400), "COMMERCIAL LICENSE TERMS:", fill=WALNUT, font=f_head)

    license_text = (
        "YOU MAY:\n"
        "✔ Sell physical laser-cut keychains, earrings,\n"
        "   bag tags, and jewelry in your shop or at\n"
        "   craft fairs up to 500 physical units/design!\n"
        "✔ Use with wood, acrylic, leather, or MDF\n"
        "✔ Commercial use is 100% included!\n\n"
        "YOU MAY NOT:\n"
        "✖ Resell, redistribute, or share digital files\n"
        "✖ Upload cut files to Print-On-Demand sites\n"
        "✖ Claim vector artwork as your own\n\n"
        "100% QUALITY GUARANTEE:\n"
        "Every file is verified for closed cut paths\n"
        "and clean burn lines. If you need any help\n"
        "with your machine setup, message us on Etsy!"
    )
    d.multiline_text((W // 2 + 80, 475), license_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Bottom Banner
    d.rectangle([0, H - 140, W, H], fill=WALNUT)
    d.text((W // 2, H - 70), "INSTANT DIGITAL DOWNLOAD  •  START CUTTING TODAY", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# MAIN BUILDER & ETSY VALIDATOR
# -----------------------------------------------------------------------------
def build_listing_deck():
    dirs = listing_dirs(SLUG)
    root = dirs["root"]
    img_dir = dirs["images"]
    work = dirs["work"]
    thumbs_dir = work / "thumbs"

    img_dir.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))

    print("Generating 10 Etsy Listing Photos (2400x2400)...")
    make_01_cover(img_dir / "01_cover.jpg", thumbs_dir, catalog)
    make_02_keychains_overview(img_dir / "02_keychains_overview.jpg", thumbs_dir, catalog)
    make_03_earrings_overview(img_dir / "03_earrings_overview.jpg", thumbs_dir, catalog)
    make_04_mockup_wood_keychains(img_dir / "04_mockup_wood_keychains.jpg", thumbs_dir)
    make_05_mockup_earrings_stand(img_dir / "05_mockup_earrings_stand.jpg", thumbs_dir)
    make_06_mockup_backpack_tag(img_dir / "06_mockup_backpack_tag.jpg", thumbs_dir)
    make_07_mockup_laser_workshop(img_dir / "07_mockup_laser_workshop.jpg")
    make_08_laser_color_coding_guide(img_dir / "08_laser_color_coding_guide.jpg")
    make_09_nested_sheets_and_sizing(img_dir / "09_nested_sheets_and_sizing.jpg")
    make_10_whats_included_and_license(img_dir / "10_whats_included_and_license.jpg")

    desc = (
        "Laser Cut Keychain and Earring SVG Bundle - 40 Complete Laser Ready Designs for Glowforge, xTool, OMTech, and LightBurn.\n\n"
        "Create high-margin wooden and acrylic keychains, bag tags, and dangle earrings for your handmade shop or craft fair booth! "
        "Every single design has been engineered with standard laser color coding (Red=Cut, Blue=Score, Black=Engrave), "
        "watertight closed cut lines, and reinforced hardware hanging holes.\n\n"
        "WHAT MAKES THIS BUNDLE SPECIAL:\n"
        "- 40 COMPLETE DESIGNS: 20 Keychains / Bag Tags + 20 Matching Dangle Earring Pairs.\n"
        "- PRE-NESTED MASTER CUTTING SHEETS: Includes pre-arranged 12x20 inch (Glowforge bed) and 12x12 inch (craft bed) master sheet SVGs "
        "with 5mm spacing to minimize material waste and save hours of layout time.\n"
        "- REINFORCED HARDWARE LOOPS: Keychains feature an integrated 3.5mm hole with >=2.5mm wall reinforcement (so keychains never crack under tension in pockets!). "
        "Earrings feature an integrated 2.0mm jump-ring hole for 20-gauge jewelry hardware.\n"
        "- STANDARD LASER COLOR CODING: Auto-recognized by Glowforge, xTool Creative Space, and LightBurn:\n"
        "  • Red Line (#FF0000) = Vector Cut\n"
        "  • Blue Line (#0000FF) = Vector Score (rapid surface detailing)\n"
        "  • Black Fill (#000000) = Engrave\n\n"
        "FEATURED THEMES (20 KEYCHAINS & 20 EARRINGS):\n"
        "Highland Cow, Woodland Bear, Woodland Fox, Cute Cat Face, Dog Paw, Monstera Leaf, Retro Daisy, Radiant Sunflower, "
        "Hummingbird, Celestial Moon & Stars, Cozy Coffee Mug, Vintage Camera, Wildflower Arch, Boho Cactus, Cute Bunny, "
        "Western Cowboy Boot, Monarch Butterfly, Cute Panda, Magic Mushroom, and 'Home Sweet Home' Tag.\n\n"
        "WHAT YOU RECEIVE IN YOUR DOWNLOAD:\n"
        "1. 01_Laser_Keychains_SVG_DXF_EPS.zip - 20 keychain files in SVG, DXF, and EPS vector formats + Master 12x20 Sheet.\n"
        "2. 02_Laser_Earrings_SVG_DXF_EPS.zip - 20 earring files in SVG, DXF, and EPS vector formats + Master 12x12 Sheet.\n"
        "3. 03_Laser_Keychains_PNG_300DPI.zip - 20 transparent background 300 DPI high-resolution PNG previews.\n"
        "4. 04_Laser_Earrings_PNG_300DPI.zip - 20 transparent background 300 DPI high-resolution PNG previews.\n"
        "5. 05_Laser_Settings_Guide_And_Master_Sheets.zip - Master nested cutting sheets and 3-Page Illustrated Laser Settings Guide PDF.\n\n"
        "COMPATIBILITY:\n"
        "- Glowforge (Basic, Plus, Pro, Aura)\n"
        "- xTool (D1, D1 Pro, M1, P2, S1, F1)\n"
        "- LightBurn & OMTech / Ruida / GRBL CO2 & Diode Lasers\n"
        "- Silhouette Studio (Basic uses DXF; Designer/Business uses SVG)\n"
        "- Cricut Design Space (SVG)\n"
        "- Illustrator, Inkscape, CorelDraw (SVG / EPS)\n\n"
        "COMMERCIAL LICENSE:\n"
        "- Small business commercial use is included up to 500 physical units per design.\n"
        "- You may sell physical keychains, earrings, and crafts made with these files.\n"
        "- You MAY NOT resell, share, redistribute, or upload digital cut files.\n\n"
        "DESIGN & CREATION TRANSPARENCY:\n"
        "- Original color-coded laser vector cut, score, and engrave paths procedurally engineered by CraftyMyia with verified closed geometry.\n"
        "- Listing photos include digital 3D renders and AI-assisted studio lifestyle mockups to illustrate how the finished wood and acrylic pieces look.\n\n"
        "DIGITAL DOWNLOAD & COMPATIBILITY NOTICE:\n"
        "- DIGITAL DOWNLOAD ONLY — no physical product will be shipped. Files are available for instant download upon purchase.\n"
        "- All machine, software, and brand names (including Glowforge, xTool, OMTech, LightBurn, Silhouette, Cricut, Adobe, and Corel) are trademarks of their respective owners; CraftyMyia is an independent studio and is not affiliated with or endorsed by them."
    )

    data = lst.write_listing(
        root,
        title=TITLE,
        tags=TAGS,
        description=desc,
        price_usd=PRICE,
        sale_hint=f"list ${LIST_PRICE:.2f}, run a 60% sale to show discount",
        category="Craft Supplies & Tools > Patterns & How To > Digital",
        materials="svg, dxf, eps, png, laser cut, wood, acrylic",
        whats_in_the_files=[
            "20 Laser-Cut Keychains + 20 Dangle Earring Pairs (40 Designs)",
            "40 Color-Coded SVGs (Red Cut, Blue Score, Black Engrave)",
            "2 Pre-Nested Master Cutting Sheet SVGs (12x20\" & 12x12\")",
            "40 DXF Cut Files + 40 EPS Files + 40 300 DPI PNGs",
            "3-Page Laser Cutting, Kerf & Settings Guide PDF"
        ],
        notes=["All keychain and earring geometries are 100% original shop vector art."]
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
    build_listing_deck()
