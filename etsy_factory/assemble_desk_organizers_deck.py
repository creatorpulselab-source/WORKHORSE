"""Assemble 10-Card Listing Deck for Desk Organizers STL Bundle.
Adheres strictly to the proven, high-converting visual architecture of:
- cover2.vibrant (from sarcastic_funny_quotes_svg_png_bundle / 01_cover.jpg)
- M.info_card with solid dark header & vibrant alternating pills (from 08_formats.jpg / 09_license.jpg)
- assemble_cups_deck.py (large bold fonts, 130pt Anton numbers, checkmark boxes, zero tiny unformatted text)
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import cover2, media as M

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\desk_organizers_stl")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"
THUMBS_DIR = LISTING_DIR / "_work" / "thumbs"
THUMBS_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 2400
BG_COLOR = (255, 248, 238)      # Warm cream canvas
INK = (22, 26, 34)              # Deep midnight charcoal ink
ACCENT = (255, 90, 45)          # Vibrant warm terracotta / coral
TEAL = (0, 168, 180)            # Electric vibrant teal
GOLD = (255, 214, 0)            # Vibrant yellow gold
GREEN = (46, 160, 90)           # Emerald green
PURPLE = (123, 82, 180)         # Royal purple
WHITE = (255, 255, 255)
LIGHT_TINT = (246, 242, 236)
VBG = (24, 32, 54)              # Deep rich midnight navy for cover collage

ITEMS = [
    {"name": "01_Round_Pen_Cup", "title": "Round Pen Cup", "tag": "ROUND PEN CUP", "sub": "Fluted Lip * Heavy Base", "dims": "80 x 80 x 95 mm",
     "bullets": ["Fluted comfort lip guides pens effortlessly", "Holds 20+ pens, pencils & drafting tools", "Solid 4mm weighted base prevents tipping", "Prints 100% upright with zero supports"]},
    {"name": "02_Hex_Pen_Cup", "title": "Hex Pen Cup", "tag": "HEXAGONAL PEN CUP", "sub": "Faceted Geometric Body", "dims": "94 x 82 x 95 mm",
     "bullets": ["6 faceted planar faces catch ambient light", "Spacious interior for markers & scissors", "Modern low-poly architectural aesthetic", "Rigid 60-degree self-supporting walls"]},
    {"name": "03_Square_Pencil_Holder", "title": "Square Pencil Holder", "tag": "SQUARE PENCIL HOLDER", "sub": "Minimalist Architectural Block", "dims": "80 x 80 x 100 mm",
     "bullets": ["100mm deep cavity holds tall paintbrushes", "Clean square profile nests against monitors", "Rounded inner corners for easy wipe-down", "Sturdy 2.8mm reinforced solid perimeter"]},
    {"name": "04_Phone_Stand", "title": "Ergonomic Phone Stand", "tag": "DESK PHONE STAND", "sub": "Case-Friendly 65-Degree Dock", "dims": "100 x 70 x 94 mm",
     "bullets": ["18mm wide slot holds thick phone cases", "Optimal 65-deg angle for Zoom & FaceTime", "Pass-thru cable cut allows charging in dock", "Anti-tip angled rear kickstand geometry"]},
    {"name": "05_Cable_Clips_x4", "title": "Cable Clips x4 Pack", "tag": "CABLE CLIPS X4 PACK", "sub": "Snap-In Wire Retainers", "dims": "142 x 25 x 14 mm",
     "bullets": ["4 connected clips print together in one go", "13mm loop with 6mm snap-in cable slot", "Flat base for double-sided tape mounting", "Stops charging cords falling behind desks"]},
    {"name": "06_Business_Card_Holder", "title": "Business Card Holder", "tag": "BUSINESS CARD DISPLAY", "sub": "Slanted Presentation Slot", "dims": "98 x 38 x 20 mm",
     "bullets": ["Holds 40+ standard 89x51mm business cards", "Slight backward cant keeps cards readable", "Low-profile executive reception styling", "Fast 35-minute print time on modern FDM"]},
    {"name": "07_Sticky_Note_Tray", "title": "Sticky Note Tray", "tag": "STICKY NOTE TRAY", "sub": "Precision 3x3in Post-It Pad", "dims": "86 x 86 x 22 mm",
     "bullets": ["Precision 81mm square fits 3x3in Post-its", "Beveled front finger notch for easy grab", "Low-profile 22mm height fits any desktop", "Weighted flat base stays put during note pull"]},
    {"name": "08_4-Compartment_Desk_Tray", "title": "4-Compartment Tray", "tag": "4-COMPARTMENT CADDY", "sub": "Modular Desktop Organizer", "dims": "184 x 124 x 42 mm",
     "bullets": ["4 divided wells for paperclips & thumb drives", "Generous 184x124mm footprint organizes clutter", "Curved bottom corners allow effortless pickup", "Nests neatly alongside modular pen trays"]},
    {"name": "09_Pen_and_Pencil_Tray", "title": "Pen & Pencil Tray", "tag": "HORIZONTAL PEN TRAY", "sub": "196mm Stylus & Apple Pencil", "dims": "196 x 46 x 24 mm",
     "bullets": ["196mm long trough holds Apple Pencils & pens", "Low front scoop lip for instant grab-and-go", "Fits seamlessly in shallow drawers & monitor base", "Clean rounded bevels match all modular pieces"]},
    {"name": "10_Desk_Dish", "title": "Desk Valet Dish", "tag": "DESK VALET DISH", "sub": "Catchall Bowl for Keys & Coins", "dims": "80 x 80 x 16 mm",
     "bullets": ["Smooth concave catchall bowl geometry", "Holds car keys, coins, rings & paperclips", "Compact 80x80mm desk valet footprint", "Silky smooth interior wipes clean effortlessly"]},
]

def get_render(filename_key: str) -> Path:
    # Try graded comfy first, then comfy, then raw
    candidates = [
        RENDERS_DIR / f"graded_comfy_{filename_key}",
        RENDERS_DIR / f"comfy_{filename_key}",
        RENDERS_DIR / filename_key
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[-1]

def make_contact_shadow(width: int, height: int, blur: int = 24, alpha: int = 140) -> Image.Image:
    s = Image.new("RGBA", (width + blur * 4, height + blur * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse((blur * 2, blur * 2, blur * 2 + width, blur * 2 + height), fill=(22, 26, 34, alpha))
    return s.filter(ImageFilter.GaussianBlur(blur))

def load_render_cropped(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im

def ImageOps_fit(im: Image.Image, size: Tuple[int, int]) -> Image.Image:
    w, h = size
    aspect = w / h
    im_aspect = im.width / im.height
    if im_aspect > aspect:
        nw = int(im.height * aspect)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width / aspect)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    return im.resize(size, Image.LANCZOS)

def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, y_top: int = 70):
    ft = M.fit(d, title.upper(), M.anton, SIZE - 240, 150, 70)
    d.text((SIZE // 2, y_top), title.upper(), font=ft, fill=INK, anchor="ma")
    fs = M.fit(d, subtitle, M.pacifico, SIZE - 360, 74, 38)
    d.text((SIZE // 2, y_top + ft.size + 16), subtitle, font=fs, fill=ACCENT, anchor="ma")
    return y_top + ft.size + fs.size + 60

def draw_check(d: ImageDraw.ImageDraw, x: int, y: int, size: int = 26, color: Tuple[int, int, int] = GREEN, width: int = 4):
    pts = [
        (x, y + int(size * 0.48)),
        (x + int(size * 0.36), y + int(size * 0.84)),
        (x + int(size * 0.92), y + int(size * 0.12))
    ]
    d.line(pts, fill=color, width=width, joint="curve")

# -----------------------------------------------------------------------------
# CARD 01: HERO COVER (EXACT cover2.vibrant ARCHITECTURE)
# -----------------------------------------------------------------------------
def make_card_01() -> Image.Image:
    out_p = IMAGES_DIR / "01_cover.jpg"
    meta = [{"name": it["name"]} for it in ITEMS]

    # Populate thumbs directory with cropped transparent / clean renders
    for i, it in enumerate(ITEMS, 1):
        src = get_render(f"single_{i:02d}.png")
        if src.exists():
            im = Image.open(src).convert("RGBA")
            bb = im.getbbox()
            if bb: im = im.crop(bb)
            im.save(THUMBS_DIR / f"{it['name']}_c.png")
            im.save(THUMBS_DIR / f"{it['name']}.png")

    ribbon_cols = [
        ((255, 90, 45), (170, 45, 15)),   # Vibrant Terracotta / Coral
        ((0, 168, 180), (0, 100, 110))    # Electric Teal
    ]

    badges = [
        ("STL", "100% Watertight\nZero Errors", TEAL),
        ("PRINT", "100% Support-Free\nFlat Bed Base", ACCENT),
        ("CAD", "Millimeter\nAccurate Fit", PURPLE),
        ("SLICER", "Bambu Prusa\nCreality Ready", GREEN),
        ("COMM", "Commercial License\nIncluded", (255, 183, 3))
    ]

    cover2.vibrant(
        meta=meta,
        thumbs_dir=THUMBS_DIR,
        out=out_p,
        big="10",
        kicker="MODERN WORKSPACE SUITE",
        title_lines=["DESK ORGANIZERS", "3D PRINT STL BUNDLE"],
        sub="PHONE STAND * PEN CUPS * CABLE CLIPS * DESK TRAYS",
        ribbon_cols=ribbon_cols,
        ink=INK,
        bg=VBG,
        badges=badges,
        burst=("INSTANT", "DOWNLOAD"),
        seed=12
    )
    return Image.open(out_p).convert("RGB")

# -----------------------------------------------------------------------------
# CARD 02: FULL 10-PACK OVERVIEW (Clean Rounded Cards + Grounded Shadows)
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "10 PRINT-READY DESK ORGANIZERS", "Complete modular office suite - 100% support-free and watertight", 70)

    cols, rows = 5, 2
    pad_x = 70
    gap_x, gap_y = 35, 42
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 90 - (rows - 1) * gap_y) // rows

    for idx, item in enumerate(ITEMS):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        # White card container with dark outline and drop shadow
        card = M.rounded((gw, gh), 40, WHITE + (255,), outline=INK + (60,), width=3)
        M.shadowed(base, card, (x, y), blur=16, off=(0, 10), alpha=80)

        # Render cropped item
        rf = get_render(f"single_{idx+1:02d}.png")
        if rf.exists():
            im = load_render_cropped(rf)
            avail_h = gh - 190
            s = min((gw - 50) / im.width, avail_h / im.height)
            nw, nh = int(im.width * s), int(im.height * s)
            im_s = im.resize((nw, nh), Image.LANCZOS)
            
            cx_item = x + (gw - nw) // 2
            cy_item = y + 25 + (avail_h - nh) // 2
            item_bottom = cy_item + nh
            
            sh = make_contact_shadow(int(nw * 0.85), 32, blur=16, alpha=130)
            sh_x = x + (gw - sh.width) // 2
            sh_y = item_bottom - sh.height // 2 - 4
            base.alpha_composite(sh, (sh_x, sh_y))
            base.alpha_composite(im_s, (cx_item, cy_item))

        # Typography
        dc = ImageDraw.Draw(base)
        fn_tag = M.fit(dc, item["tag"], M.anton, gw - 30, 42, 22)
        dc.text((x + gw // 2, y + gh - 98), item["tag"], font=fn_tag, fill=INK, anchor="mm")

        fn_sub = M.fit(dc, item["sub"], M.poppins_x, gw - 40, 24, 14)
        dc.text((x + gw // 2, y + gh - 54), item["sub"], font=fn_sub, fill=ACCENT, anchor="mm")

        fn_dims = M.fit(dc, item["dims"], M.poppins, gw - 40, 22, 12)
        dc.text((x + gw // 2, y + gh - 22), item["dims"], font=fn_dims, fill=TEAL, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARDS 03 & 04: 2x2 FEATURE SPOTLIGHTS (Large Cards, Big Fonts, Photo Left)
# -----------------------------------------------------------------------------
def make_feature_grid_card(title: str, subtitle: str, group_items: List[Dict]) -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, title, subtitle, 70)

    cols, rows = 2, 2
    pad_x = 90
    gap_x, gap_y = 50, 50
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 80 - (rows - 1) * gap_y) // rows

    for idx, item in enumerate(group_items):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        # White card container with shadow
        card = M.rounded((gw, gh), 44, WHITE + (255,), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Photo on Left side: width 480, height gh - 60
        item_idx = ITEMS.index(item) + 1
        p_path = get_render(f"single_{item_idx:02d}.png")
        iw = 480
        ih = gh - 60
        if p_path.exists():
            im = Image.open(p_path).convert("RGBA")
            im_fit = ImageOps_fit(im, (iw, ih))
            card_img = M.rounded((iw, ih), 30, WHITE + (255,))
            base.paste(im_fit, (x + 30, y + 30), card_img)
            ImageDraw.Draw(base).rounded_rectangle([x + 30, y + 30, x + 30 + iw, y + 30 + ih], radius=30, outline=INK, width=3)

        # Text on Right side
        tx = x + 540
        avail_tw = gw - 570
        d_card = ImageDraw.Draw(base)

        fn_title = M.fit(d_card, item["tag"], M.anton, avail_tw, 56, 32)
        d_card.text((tx, y + 42), item["tag"], font=fn_title, fill=INK, anchor="la")

        fn_sub = M.fit(d_card, f"{item['dims']} * 0 Supports", M.poppins_x, avail_tw, 30, 18)
        d_card.text((tx, y + 106), f"{item['dims']} * 0 Supports", font=fn_sub, fill=ACCENT, anchor="la")

        d_card.line([(tx, y + 155), (tx + avail_tw - 10, y + 155)], fill=ACCENT + (140,), width=3)

        # Bullet points with bold colored circle badges
        f_bullet = M.poppins(32)
        by = y + 185
        for b_text in item["bullets"]:
            d_card.ellipse((tx, by + 10, tx + 14, by + 24), fill=TEAL)
            wrapped = M._wrap(d_card, b_text, f_bullet, avail_tw - 30)
            for w_ln in wrapped:
                d_card.text((tx + 30, by), w_ln, font=f_bullet, fill=INK, anchor="la")
                by += 44
            by += 12

        # Bottom spec chip
        chip_y = y + gh - 90
        chip_w = avail_tw - 20
        chip_bg = M.rounded((chip_w, 60), 30, LIGHT_TINT + (255,), outline=INK + (70,), width=2)
        base.paste(chip_bg, (tx, chip_y), chip_bg)
        f_chip = M.fit(d_card, f"{item['sub']} * 100% Watertight", M.poppins_x, chip_w - 30, 24, 16)
        d_card.text((tx + chip_w // 2, chip_y + 30), f"{item['sub']} * 100% Watertight", font=f_chip, fill=INK, anchor="mm")

    return base.convert("RGB")

def make_card_03() -> Image.Image:
    # Round Cup, Hex Cup, Square Holder, Phone Stand
    return make_feature_grid_card(
        "DESK CUPS & ERGONOMIC PHONE DOCK",
        "Weighted anti-tip bases, chamfered rims & video-call phone stand",
        ITEMS[0:4]
    )

def make_card_04() -> Image.Image:
    # Cable Clips, Business Card Holder, Sticky Note Tray, 4-Compartment Tray
    return make_feature_grid_card(
        "CABLE CLIPS, CARDS & MODULAR TRAYS",
        "Snap wire retainers, Post-it pad dock & multi-compartment sorting caddy",
        ITEMS[4:8]
    )

# -----------------------------------------------------------------------------
# CARD 05: LIFESTYLE SHOWCASE (Centerpiece ComfyUI Hero + Feature Pills)
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "COZY LIFESTYLE DESK SETUP", "Harmonious Scandinavian desk suite in matte PLA finishes", 70)

    # Big hero lifestyle image container in center
    iw, ih = SIZE - 180, 1420
    p_path = get_render("cluster_hero.png")
    if p_path.exists():
        im = Image.open(p_path).convert("RGBA")
        im_fit = ImageOps_fit(im, (iw, ih))
        card_hero = M.rounded((iw, ih), 44, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, card_hero, ((SIZE - iw)//2, top + 15), blur=26, off=(0, 16), alpha=110)
        base.paste(im_fit, ((SIZE - iw)//2, top + 15), card_hero)
        ImageDraw.Draw(base).rounded_rectangle([(SIZE - iw)//2, top + 15, (SIZE + iw)//2, top + 15 + ih], radius=44, outline=INK, width=6)

    # Row 1 of pills directly under hero photo
    pills = ["ANTI-TIP WEIGHTED BASES", "FITS STANDARD CABLES", "SMOOTH EASY-CLEAN SURFACE", "PRINT AT HOME"]
    total_w = SIZE - 180
    n = len(pills)
    gap = 24
    pw = (total_w - (n - 1) * gap) // n
    py = top + 15 + ih + 40
    f_p = M.poppins_x(32)

    for i, p_text in enumerate(pills):
        px = 90 + i * (pw + gap)
        pill_img = M.rounded((pw, 94), 47, WHITE + (255,), outline=INK + (255,), width=4)
        M.shadowed(base, pill_img, (px, py), blur=12, off=(0, 6), alpha=70)
        d.text((px + pw // 2, py + 47), p_text, font=f_p, fill=INK, anchor="mm")

    # Bottom Highlight Card: Eliminates dead whitespace with key selling points
    by2 = py + 94 + 35
    bh2 = SIZE - by2 - 60
    card_bot = M.rounded((total_w, bh2), 36, WHITE + (255,), outline=INK + (120,), width=3)
    M.shadowed(base, card_bot, (90, by2), blur=16, off=(0, 8), alpha=70)

    # Content inside bottom card
    d.text((140, by2 + bh2 // 2 - 28), "100% ORIGINAL WORKHORSE DESIGNS", font=M.anton(46), fill=ACCENT, anchor="la")
    d.text((140, by2 + bh2 // 2 + 26), "Engineered specifically for FDM 3D printers with zero support waste & watertight meshes.", font=M.poppins(32), fill=INK, anchor="la")

    # 3 mini badges on right
    badges = ["NO SUPPORTS", "WATERTIGHT STL", "COMMERCIAL USE"]
    bx_right = SIZE - 140
    for b_idx, b_txt in enumerate(reversed(badges)):
        f_b = M.anton(26)
        tw = M.text_w(d, b_txt, f_b)
        bw = tw + 40
        b_box = M.rounded((bw, 54), 27, INK + (255,))
        base.paste(b_box, (bx_right - bw, by2 + (bh2 - 54) // 2), b_box)
        d.text((bx_right - bw // 2, by2 + bh2 // 2), b_txt, font=f_b, fill=WHITE, anchor="mm")
        bx_right -= bw + 18

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 06: DUAL-FOCUS FEATURE (Pen & Pencil Tray + Desk Valet Dish)
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "HORIZONTAL PEN TRAY & DESK DISH", "Long stylus presentation & rounded catchall valet bowl", 70)

    cols = 2
    pad_x = 90
    gw = (SIZE - pad_x * 2 - 50) // cols
    gh = SIZE - top - 110

    panels = [
        {
            "item": ITEMS[8], # Pen & Pencil Tray
            "img_idx": 9,
            "bullets": [
                "196mm extra-long trough holds full-length pencils & Apple Pencils",
                "Low front scoop lip allows effortless single-finger pickup",
                "Fits seamlessly under computer monitors or inside desk drawers",
                "Clean rounded perimeter bevels match entire modular organizer line"
            ],
            "box_title": "IDEAL STYLUS & PEN COMPANION",
            "box_desc": "Great for digital artists, iPad creators, architects, and fountain pen collectors."
        },
        {
            "item": ITEMS[9], # Desk Dish
            "img_idx": 10,
            "bullets": [
                "Generous concave curved dish collects keys, coins, rings & AirPods",
                "Smooth beveled inner basin allows effortless scoop-out",
                "Compact 80x80mm footprint fits on nightstands, entryway & desk corners",
                "Moisture-resistant PLA plastic wipes clean in seconds with a damp cloth"
            ],
            "box_title": "IDEAL EVERYDAY CATCHALL VALET",
            "box_desc": "Perfect for pocket EDC items, USB keys, paperclips, jewelry & guitar picks."
        }
    ]

    for idx, p in enumerate(panels):
        x = pad_x + idx * (gw + 50)
        y = top + 15

        card = M.rounded((gw, gh), 44, WHITE + (255,), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Image top half
        p_path = get_render(f"single_{p['img_idx']:02d}.png")
        iw = gw - 60
        ih = int(gh * 0.52)
        if p_path.exists():
            im = Image.open(p_path).convert("RGBA")
            im_fit = ImageOps_fit(im, (iw, ih))
            card_img = M.rounded((iw, ih), 32, WHITE + (255,))
            base.paste(im_fit, (x + 30, y + 30), card_img)
            ImageDraw.Draw(base).rounded_rectangle([x + 30, y + 30, x + 30 + iw, y + 30 + ih], radius=32, outline=INK, width=2)

        # Content bottom half
        ty = y + ih + 55
        d_card = ImageDraw.Draw(base)
        ft = M.fit(d_card, p["item"]["tag"], M.anton, gw - 60, 56, 32)
        d_card.text((x + gw // 2, ty), p["item"]["tag"], font=ft, fill=INK, anchor="ma")

        fs = M.fit(d_card, f"{p['item']['dims']} * 0 Supports", M.poppins_x, gw - 80, 30, 20)
        d_card.text((x + gw // 2, ty + 62), f"{p['item']['dims']} * 0 Supports", font=fs, fill=ACCENT, anchor="ma")

        # Divider
        d_card.line([(x + 50, ty + 112), (x + gw - 50, ty + 112)], fill=ACCENT + (140,), width=2)

        # Bullets
        fb = M.poppins(34)
        by = ty + 135
        for b_text in p["bullets"]:
            d_card.ellipse((x + 50, by + 10, x + 64, by + 24), fill=TEAL)
            d_card.text((x + 80, by), b_text, font=fb, fill=INK, anchor="la")
            by += 54

        # Bottom Highlight Pill Box (Fills bottom void)
        box_y = y + gh - 150
        box_w = gw - 80
        box_h = 115
        box_bg = M.rounded((box_w, box_h), 28, LIGHT_TINT + (255,), outline=ACCENT + (120,), width=2)
        base.paste(box_bg, (x + 40, box_y), box_bg)
        d_card.text((x + gw // 2, box_y + 32), p["box_title"], font=M.anton(34), fill=ACCENT, anchor="mm")
        f_bdesc = M.fit(d_card, p["box_desc"], M.poppins, box_w - 40, 30, 18)
        d_card.text((x + gw // 2, box_y + 78), p["box_desc"], font=f_bdesc, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 07: 100% SUPPORT-FREE PRINT QUALITY GUARANTEE (130pt Numbers + Checkmarks)
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "EASY TO PRINT * 100% SUPPORT-FREE", "Engineered for flawless FDM printing on any machine", 70)

    features = [
        {
            "num": "01",
            "title": "ZERO SUPPORTS NEEDED",
            "kicker": "100% self-supporting geometry",
            "desc": "Every single model prints upright in its exported orientation. Zero supports, zero overhang droop, zero wasted plastic. Remove from build plate and organize immediately.",
            "checks": ["Zero support waste or clean-up", "No scarring on visible surfaces", "Prints upright flat on build plate"]
        },
        {
            "num": "02",
            "title": "WATERTIGHT MANIFOLD MESHES",
            "kicker": "Validated in Blender & 3D Print Tool",
            "desc": "Checked and validated with manifold geometry inspection. Zero non-manifold edges, zero holes, zero flipped normals. Clean, instant slicing in Bambu Studio, OrcaSlicer, PrusaSlicer & Cura.",
            "checks": ["100% closed watertight solids", "Zero non-manifold edge errors", "Instant 1-click slicer import"]
        },
        {
            "num": "03",
            "title": "OPTIMIZED WALL RIGIDITY",
            "kicker": "Heavy-duty 2.4mm to 3.2mm perimeters",
            "desc": "Thick outer walls provide rugged structural integrity, impact protection, and weighted desktop presence. Models will never feel flimsy or crush under daily office use.",
            "checks": ["Solid 4-6 perimeter wall shell", "Reinforced wall durability", "Substantial weighted feel"]
        },
        {
            "num": "04",
            "title": "FITS STANDARD 220MM BEDS",
            "kicker": "Universal build plate compatibility",
            "desc": "Even the largest 196mm Pen Tray fits comfortably inside a standard 220 x 220 mm build plate. Compatible with Ender 3, Bambu Lab A1 / P1 / X1, Prusa MK3 / MK4, and Anycubic.",
            "checks": ["196mm max footprint fits 220x220 beds", "Bambu Lab & Prusa compatible", "Standard 0.4mm nozzle optimized"]
        }
    ]

    cols, rows = 2, 2
    pad_x = 90
    gap_x, gap_y = 50, 50
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 80 - (rows - 1) * gap_y) // rows

    for idx, f in enumerate(features):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        card = M.rounded((gw, gh), 44, WHITE + (255,), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Checkpoints Box (Fills bottom card half)
        c_box_y = y + 460
        c_box_w = gw - 100
        c_box_h = gh - 460 - 45
        c_bg = M.rounded((c_box_w, c_box_h), 28, LIGHT_TINT + (255,), outline=INK + (60,), width=2)
        base.paste(c_bg, (x + 50, c_box_y), c_bg)

        # Paste white pill backgrounds for each check item
        row_h = 100
        row_gap = 32
        for i in range(len(f["checks"])):
            ry = c_box_y + 36 + i * (row_h + row_gap)
            pill = M.rounded((c_box_w - 40, row_h), 20, WHITE + (255,), outline=INK + (35,), width=2)
            base.paste(pill, (x + 70, ry), pill)

        d_card = ImageDraw.Draw(base)

        # Giant badge number
        fn = M.anton(130)
        d_card.text((x + 50, y + 40), f["num"], font=fn, fill=ACCENT, anchor="la")

        # Title & Kicker
        ft = M.fit(d_card, f["title"], M.anton, gw - 240, 52, 30)
        d_card.text((x + 220, y + 55), f["title"], font=ft, fill=INK, anchor="la")

        fk = M.fit(d_card, f["kicker"], M.poppins_x, gw - 240, 28, 18)
        d_card.text((x + 220, y + 118), f["kicker"], font=fk, fill=ACCENT, anchor="la")

        # Divider line
        d_card.line([(x + 50, y + 190), (x + gw - 50, y + 190)], fill=ACCENT + (140,), width=3)

        # Description text
        fb = M.poppins(36)
        lines = M._wrap(d_card, f["desc"], fb, gw - 100)
        ly = y + 225
        for ln in lines:
            d_card.text((x + 50, ly), ln, font=fb, fill=INK, anchor="la")
            ly += 50

        # Draw check badges & text
        fc = M.poppins_x(30)
        for i, chk in enumerate(f["checks"]):
            ry = c_box_y + 36 + i * (row_h + row_gap)
            badge_cx = x + 120
            badge_cy = ry + row_h // 2
            badge_r = 24
            d_card.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=LIGHT_TINT + (255,), outline=GREEN + (160,), width=2)
            draw_check(d_card, badge_cx - 13, badge_cy - 13, size=26, color=GREEN, width=4)
            d_card.text((x + 165, badge_cy), chk, font=fc, fill=INK, anchor="lm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARDS 08, 09, 10: BIG-FONT COLORFUL M.info_card PAGES (From 08_formats & 09_license)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    out_p = IMAGES_DIR / "08_print_settings.jpg"
    rows = [
        ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
        ("LAYER HEIGHT", "0.20 mm standard / 0.28 mm draft for rapid prints"),
        ("WALL LOOPS", "4 to 6 perimeters (2.4mm) for rugged structural rigidity"),
        ("INFILL DENSITY", "15% to 20% Gyroid pattern for balanced strength and speed"),
        ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar bed contact at Z=0"),
        ("MATERIALS", "Matte PLA recommended for desk aesthetics; PETG for extra toughness")
    ]
    M.info_card(
        out=out_p,
        title="RECOMMENDED PRINT SETTINGS",
        kicker="OPTIMIZED FDM 3D PRINTING",
        rows=rows,
        accent=ACCENT,       # Vibrant Warm Terracotta / Coral
        ink=INK,             # Deep Midnight Ink
        bg=BG_COLOR,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic."
    )
    return Image.open(out_p).convert("RGB")

def make_card_09() -> Image.Image:
    out_p = IMAGES_DIR / "09_formats.jpg"
    rows = [
        ("10 STL FILES", "Watertight binary STL files with millimeter scaling (1 file per organizer)"),
        ("SLICER READY", "Drag-and-drop into Bambu Studio, OrcaSlicer, PrusaSlicer, or Cura"),
        ("MODULAR FIT", "Coordinated heights and depths create neat, nesting desktop grids"),
        ("FLAT BED BASE", "Engineered planar first layer contact at Z=0 - zero brim or raft needed"),
        ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document")
    ]
    M.info_card(
        out=out_p,
        title="WHAT'S IN YOUR DOWNLOAD",
        kicker="INSTANT DIGITAL DOWNLOAD",
        rows=rows,
        accent=TEAL,         # Electric Vibrant Teal
        ink=INK,
        bg=BG_COLOR,
        footer="Desk_Organizers_STL.zip (10 Solid STL Files) + Print_Guide_and_License.pdf"
    )
    return Image.open(out_p).convert("RGB")

def make_card_10() -> Image.Image:
    out_p = IMAGES_DIR / "10_commercial_license.jpg"
    rows = [
        ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
        ("UNLIMITED", "Sell as many physical organizers as you make - no recurring royalties ever"),
        ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
        ("ORIGINAL", "100% original WORKHORSE functional designs - watertight guaranteed"),
        ("HELP", "Message the shop anytime if you need assistance with slicing or printing")
    ]
    M.info_card(
        out=out_p,
        title="COMMERCIAL USE INCLUDED",
        kicker="PHYSICAL PRINT PERMISSION",
        rows=rows,
        accent=(255, 64, 129), # Hot Pink / Magenta from sarcastic quotes!
        ink=INK,
        bg=BG_COLOR,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE."
    )
    return Image.open(out_p).convert("RGB")

def build_all_cards():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cards = [
        ("01_cover.jpg", make_card_01),
        ("02_preview_all.jpg", make_card_02),
        ("03_feature_cups.jpg", make_card_03),
        ("04_feature_trays_clips.jpg", make_card_04),
        ("05_lifestyle_showcase.jpg", make_card_05),
        ("06_feature_pen_tray_dish.jpg", make_card_06),
        ("07_feature_quality.jpg", make_card_07),
        ("08_print_settings.jpg", make_card_08),
        ("09_formats.jpg", make_card_09),
        ("10_commercial_license.jpg", make_card_10),
    ]

    print(f"Generating all 10 cards for Desk Organizers in {IMAGES_DIR}...")
    for fname, fn in cards:
        out_path = IMAGES_DIR / fname
        img = fn()
        img.save(out_path, quality=95, subsampling=0)
        print(f"  [OK] Saved {fname} ({out_path.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    build_all_cards()
