"""Assemble 10-Card Listing Deck for Can & Drink Holders STL Bundle.
Replicates the high-converting visual architecture of cute_animal_pencil_cups_stl_3mf_glb:
- Warm cream canvas #FAF5EE with dark espresso ink #2A1E17
- Grounded contact shadows beneath all 3D products (ZERO floating)
- Giant gradient numbers, Anton headlines, Pacifico cursive accents
- Format chips (STL, 3D PRINT, NO SUPPORTS, TESTED, COMMERCIAL)
- 40-point yellow starburst badge "INSTANT DOWNLOAD"
- Full 10-card deck at 2400 x 2400, quality=95, subsampling=0
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import media as M

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\can_holders_stl")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"

SIZE = 2400
BG_COLOR = (250, 245, 238)      # #FAF5EE warm cream
INK = (42, 30, 23)              # #2A1E17 dark espresso brown
ACCENT = (44, 98, 62)           # #2C623E forest green accent
ORANGE = (212, 92, 36)          # #D45C24 warm terracotta
GOLD = (255, 214, 0)            # #FFD600 starburst yellow
WHITE = (255, 255, 255)
LIGHT_TINT = (244, 240, 232)

CHIP_COLS = [
    ("STL", (44, 98, 62)),        # Forest Green
    ("3D PRINT", (212, 92, 36)),  # Terracotta
    ("NO SUP", (46, 125, 114)),   # Slate Teal
    ("READY", (123, 82, 148)),   # Royal Violet
    ("COMMERCIAL", (200, 140, 30))# Honey Gold
]

ITEMS = [
    {"name": "QuadGrip 4-Cup Caddy", "tag": "4-CUP CARRIER", "sub": "Fits Coffee & Fast Food Cups", "file": "single_01.png", "dims": "189 x 189 x 165 mm"},
    {"name": "DuoCaddy Twin Carrier", "tag": "2-CAN CARRIER", "sub": "Ergonomic Center Handle", "file": "single_02.png", "dims": "162 x 76 x 138 mm"},
    {"name": "HexaCool Can Cooler", "tag": "STANDARD 12OZ", "sub": "Tactile Diamond Knurling", "file": "single_03.png", "dims": "79 x 79 x 98 mm"},
    {"name": "SlimGrip Can Cooler", "tag": "SLIM 12OZ", "sub": "Honeycomb Hexagonal Grip", "file": "single_04.png", "dims": "68 x 67 x 105 mm"},
    {"name": "TrailLock Holster", "tag": "ADVENTURE CLIP", "sub": "Reinforced Carabiner Loop", "file": "single_05.png", "dims": "97 x 80 x 98 mm"},
    {"name": "DualDrive Car Expander", "tag": "CAR ADAPTER", "sub": "Stepped 68mm to 88mm", "file": "single_06.png", "dims": "90 x 90 x 127 mm"},
    {"name": "Titan 16oz Chiller", "tag": "TALLBOY 16OZ", "sub": "Thermal Horizontal Ribs", "file": "single_07.png", "dims": "78 x 78 x 126 mm"},
    {"name": "FlipBase Stabilizer", "tag": "DESK DOCK", "sub": "112mm Anti-Tip Coaster", "file": "single_08.png", "dims": "112 x 112 x 42 mm"},
]

def make_contact_shadow(width: int, height: int, blur: int = 24, alpha: int = 140) -> Image.Image:
    s = Image.new("RGBA", (width + blur * 4, height + blur * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse((blur * 2, blur * 2, blur * 2 + width, blur * 2 + height), fill=(32, 24, 18, alpha))
    return s.filter(ImageFilter.GaussianBlur(blur))

def load_render_cropped(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im

def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, y_top: int = 70):
    ft = M.fit(d, title.upper(), M.anton, SIZE - 240, 145, 65)
    d.text((SIZE // 2, y_top), title.upper(), font=ft, fill=INK, anchor="ma")
    fs = M.fit(d, subtitle, M.pacifico, SIZE - 360, 72, 36)
    d.text((SIZE // 2, y_top + ft.size + 16), subtitle, font=fs, fill=ACCENT, anchor="ma")
    return y_top + ft.size + fs.size + 55

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

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# CARD 01: HERO COVER (UNIVERSAL 3D BESTSELLER LAYOUT)
# -----------------------------------------------------------------------------
def make_bg_collage(seed: int = 42) -> Image.Image:
    """Builds a tilted collage of the 8 single can holder models in the background."""
    import random
    rng = random.Random(seed)
    single_files = [RENDERS_DIR / f"single_{i:02d}.png" for i in range(1, 9)]
    thumbs = []
    for p in single_files:
        if p.exists():
            im = Image.open(p).convert("RGBA")
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)
            th = im.resize((320, 320), Image.Resampling.LANCZOS)
            thumbs.append(th)

    if not thumbs:
        return Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))

    big = int(SIZE * 1.55)
    base = Image.new("RGBA", (big, big), BG_COLOR + (255,))
    order = thumbs[:]
    rng.shuffle(order)

    edge_cols = [
        (44, 98, 62),    # Forest Green
        (212, 92, 36),   # Terracotta
        (29, 99, 184),   # Denim Blue
        (200, 140, 30),  # Honey Ochre
        (123, 82, 148),  # Violet
        (45, 50, 55),    # Charcoal
    ]

    row_h, gap = 380, 35
    y, k = -60, 0
    while y < big:
        x = -rng.randrange(0, 200)
        while x < big:
            t = order[k % len(order)]
            k += 1
            cw, ch = 360, row_h
            card = M.rounded((cw, ch), 42, (255, 255, 255, 255), outline=rng.choice(edge_cols) + (255,), width=10)
            card.alpha_composite(t, ((cw - t.width) // 2, (ch - t.height) // 2))
            base.alpha_composite(card, (x, y))
            x += cw + gap
        y += row_h + gap

    base = base.rotate(8, resample=Image.Resampling.BICUBIC, center=(big // 2, big // 2), fillcolor=BG_COLOR + (255,))
    o = (big - SIZE) // 2
    cropped = base.crop((o, o, o + SIZE, o + SIZE))

    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((80, 80, SIZE - 80, SIZE - 80), fill=BG_COLOR + (190,))
    cropped.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    return cropped


def make_card_01() -> Image.Image:
    base = make_bg_collage(seed=42)

    # Central white rounded card container - perfectly centered!
    cw, ch = 1960, 1820
    cx, cy = (SIZE - cw) // 2, (SIZE - ch) // 2
    card = M.rounded((cw, ch), 85, (255, 255, 255, 255), outline=INK + (255,), width=12)
    M.shadowed(base, card, (cx, cy), blur=38, off=(0, 24), alpha=130)

    d = ImageDraw.Draw(base)

    # Top ribbon pill: "COMMERCIAL USE INCLUDED"
    rb = "COMMERCIAL USE INCLUDED"
    f_rb = M.fit(d, rb, M.poppins_x, 1250, 52)
    tw = M.text_w(d, rb, f_rb)
    pill = M.rounded((tw + 110, 96), 48, ACCENT + (255,))
    base.alpha_composite(pill, (SIZE // 2 - (tw + 110) // 2, cy - 48))
    d.text((SIZE // 2, cy), rb, font=f_rb, fill=WHITE, anchor="mm")

    # Primary Title Line
    ty = cy + 55
    t_text = "8 CAN & DRINK HOLDERS"
    fl = M.fit(d, t_text, M.anton, cw - 180, 115, 70)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "4-Cup Caddy  *  Can Coolers  *  Car Adapter  *  Adventure Holster"
    fs = M.fit(d, sub, M.pacifico, cw - 240, 52, 30)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    sub_y = ty + (bb[3] - bb[1]) + 12
    d.text((SIZE // 2, sub_y - bbs[1]), sub, font=fs, fill=ACCENT, anchor="ma")

    # Hero Product Showcase in center of card (uncropped, centered!)
    hero_y = sub_y + (bbs[3] - bbs[1]) + 24
    hero_w = cw - 140
    hero_h = 1040

    p_cluster = RENDERS_DIR / "cluster_hero.png"
    if p_cluster.exists():
        im_hero = load_render_cropped(p_cluster)
        s = min((hero_w - 60) / im_hero.width, (hero_h - 60) / im_hero.height)
        nw, nh = int(im_hero.width * s), int(im_hero.height * s)
        im_scaled = im_hero.resize((nw, nh), Image.LANCZOS)

        # Grounded contact shadow
        sh = make_contact_shadow(int(nw * 0.90), 80, blur=30, alpha=150)
        base.alpha_composite(sh, (SIZE // 2 - sh.width // 2, hero_y + nh - 30))

        # Paste product
        base.alpha_composite(im_scaled, (SIZE // 2 - nw // 2, hero_y + (hero_h - nh) // 2 - 10))

    # Format Chips across bottom of card container
    n_chips = len(CHIP_COLS)
    r = 76
    gap = 32
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 120
    for j, (label, col) in enumerate(CHIP_COLS):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=6)
        fc = M.fit(d, label, M.anton, 2 * r - 22, 54, 20)
        d.text((xx, cyy + 3), label, font=fc, fill=WHITE, anchor="mm")

    # Bottom machine strip on beige canvas
    strip = "BAMBU LAB  *  PRUSA  *  CREALITY  *  ANY SLICER"
    fs2 = M.fit(d, strip, M.poppins_x, SIZE - 260, 48, 24)
    sw = M.text_w(d, strip, fs2)
    sp = M.rounded((sw + 90, 84), 42, INK + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 90) // 2, SIZE - 125))
    d.text((SIZE // 2, SIZE - 83), strip, font=fs2, fill=WHITE, anchor="mm")

    # 40-Point Yellow Starburst Badge ("INSTANT DOWNLOAD")
    bx, by, br = SIZE - 240, 240, 200
    pts = []
    for q in range(40):
        a = math.pi * 2 * q / 40
        rr = br if q % 2 == 0 else br * 0.82
        pts.append((bx + rr * math.cos(a), by + rr * math.sin(a)))
    star = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(star).polygon(pts, fill=GOLD + (255,), outline=INK + (255,), width=8)
    base.alpha_composite(star)

    burst_lines = ["INSTANT", "DOWNLOAD"]
    fz = M.anton(66)
    for li, l in enumerate(burst_lines):
        ImageDraw.Draw(base).text((bx, by + (li - 0.5) * 72), l, font=fz, fill=INK, anchor="mm")

    return base.convert("RGB")

# CARD 02: FULL 8-PACK OVERVIEW (Clean Rounded Cards + Grounded Shadows)
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "8 PRINT-READY DRINK HOLDERS", "Original 3D printable designs - watertight and support-free", 70)

    cols, rows = 4, 2
    pad_x = 70
    gap_x, gap_y = 40, 48
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 90 - (rows - 1) * gap_y) // rows

    for idx, item in enumerate(ITEMS):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        # White card with border and shadow
        tile = M.rounded((gw, gh), 42, (255, 255, 255, 255), outline=INK + (255,), width=6)
        M.shadowed(base, tile, (x, y), blur=24, off=(0, 14), alpha=110)

        td = ImageDraw.Draw(base)

        # Tag banner at top of card
        tag_f = M.fit(td, item["tag"], M.anton, gw - 40, 46, 26)
        td.text((x + gw // 2, y + 36), item["tag"], font=tag_f, fill=ACCENT, anchor="mm")

        # Load render
        rf = RENDERS_DIR / item["file"]
        if rf.exists():
            im = load_render_cropped(rf)
            max_w, max_h = gw - 60, gh - 180
            s = min(max_w / im.width, max_h / im.height)
            nw, nh = int(im.width * s), int(im.height * s)
            im_scaled = im.resize((nw, nh), Image.LANCZOS)

            # Grounded contact shadow
            sh = make_contact_shadow(int(nw * 0.85), 36, blur=18, alpha=150)
            base.alpha_composite(sh, (x + (gw - sh.width) // 2, y + 70 + nh - 12))

            # Product image
            base.alpha_composite(im_scaled, (x + (gw - nw) // 2, y + 70))

        # Item Name & Dimensions at bottom
        nf = M.fit(td, item["name"], M.poppins_x, gw - 30, 40, 24)
        td.text((x + gw // 2, y + gh - 65), item["name"], font=nf, fill=INK, anchor="mm")

        df = M.fit(td, item["dims"], M.poppins, gw - 40, 32, 20)
        td.text((x + gw // 2, y + gh - 28), item["dims"], font=df, fill=ORANGE, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 03: FEATURE SPOTLIGHT: 4-CUP DRINK CADDY
# -----------------------------------------------------------------------------
def make_card_03() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "QUADGRIP 4-CUP DRINK CADDY", "Ergonomic bridge handle & universal takeout cup wells", 70)

    # Left: Large render showcase card
    card_w, card_h = 1350, 1550
    cx, cy = 80, top + 30
    c_left = M.rounded((card_w, card_h), 56, (255, 255, 255, 255), outline=INK + (255,), width=8)
    M.shadowed(base, c_left, (cx, cy), blur=32, off=(0, 18), alpha=120)

    rf = RENDERS_DIR / "single_01.png"
    if rf.exists():
        im = load_render_cropped(rf)
        s = min((card_w - 120) / im.width, (card_h - 180) / im.height)
        nw, nh = int(im.width * s), int(im.height * s)
        im_s = im.resize((nw, nh), Image.LANCZOS)
        sh = make_contact_shadow(int(nw * 0.88), 65, blur=28, alpha=160)
        base.alpha_composite(sh, (cx + (card_w - sh.width) // 2, cy + (card_h - nh) // 2 + nh - 25))
        base.alpha_composite(im_s, (cx + (card_w - nw) // 2, cy + (card_h - nh) // 2 - 20))

    # Right: Feature callout pills
    rx = cx + card_w + 50
    rw = SIZE - rx - 80
    features = [
        ("UNIVERSAL FIT", "82mm cup wells fit standard fast-food, iced coffee, smoothies & reusable tumblers securely."),
        ("ERGONOMIC HANDLE", "Contoured arch handle with smooth 4-finger grip and center weight balance."),
        ("100% SUPPORT-FREE", "Engineered with 45-degree self-supporting arches. Zero supports needed."),
        ("ANTI-SLOSH TRUSS", "Reinforced bottom web base prevents tipping in cars and on outdoor picnic tables."),
        ("CONDENSATION DRAINS", "Every well includes an 8.4mm anti-vacuum drainage hole.")
    ]

    fy = cy + 10
    f_h = (card_h - (len(features) - 1) * 28) // len(features)
    for title, desc in features:
        fc = M.rounded((rw, f_h), 34, WHITE + (255,), outline=ACCENT + (255,), width=5)
        M.shadowed(base, fc, (rx, fy), blur=18, off=(0, 10), alpha=90)
        fd = ImageDraw.Draw(base)

        ft = M.fit(fd, title, M.anton, rw - 50, 48, 30)
        fd.text((rx + 30, fy + 42), title, font=ft, fill=ACCENT, anchor="la")

        fl = M.fit(fd, desc, M.poppins, rw - 50, 36, 22)
        words = desc.split()
        lines = []
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if fd.textlength(trial, font=fl) <= rw - 60:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        for li, line in enumerate(lines[:3]):
            fd.text((rx + 30, fy + 90 + li * 42), line, font=fl, fill=INK, anchor="la")

        fy += f_h + 28

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 04: FEATURE SPOTLIGHT: CAN COOLERS (Standard & Slim)
# -----------------------------------------------------------------------------
def make_card_04() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "INSULATED CAN COOLERS", "HexaCool Diamond (Standard 12oz) & SlimGrip (Slim 12oz)", 70)

    half_w = (SIZE - 220) // 2
    h = 1580
    y0 = top + 30

    # Left: Standard Knurled Cooler
    card_l = M.rounded((half_w, h), 56, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (80, y0), blur=32, off=(0, 18), alpha=120)

    # Right: Slim Honeycomb Cooler
    card_r = M.rounded((half_w, h), 56, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_r, (80 + half_w + 60, y0), blur=32, off=(0, 18), alpha=120)

    # Render Left
    rf_l = RENDERS_DIR / "single_03.png"
    if rf_l.exists():
        im = load_render_cropped(rf_l)
        s = min((half_w - 100) / im.width, 820 / im.height)
        nw, nh = int(im.width * s), int(im.height * s)
        im_s = im.resize((nw, nh), Image.LANCZOS)
        sh = make_contact_shadow(int(nw * 0.85), 55, blur=24, alpha=160)
        base.alpha_composite(sh, (80 + (half_w - sh.width) // 2, y0 + 120 + nh - 20))
        base.alpha_composite(im_s, (80 + (half_w - nw) // 2, y0 + 120))

    # Render Right
    rf_r = RENDERS_DIR / "single_04.png"
    if rf_r.exists():
        im = load_render_cropped(rf_r)
        s = min((half_w - 100) / im.width, 820 / im.height)
        nw, nh = int(im.width * s), int(im.height * s)
        im_s = im.resize((nw, nh), Image.LANCZOS)
        sh = make_contact_shadow(int(nw * 0.85), 55, blur=24, alpha=160)
        base.alpha_composite(sh, (80 + half_w + 60 + (half_w - sh.width) // 2, y0 + 120 + nh - 20))
        base.alpha_composite(im_s, (80 + half_w + 60 + (half_w - nw) // 2, y0 + 120))

    # Text descriptions on both sides
    td = ImageDraw.Draw(base)
    # Left text
    td.text((80 + half_w // 2, y0 + 60), "STANDARD 12OZ / 16OZ", font=M.anton(52), fill=ACCENT, anchor="mm")
    td.text((80 + half_w // 2, y0 + 1040), "HEXACOOL DIAMOND KNURLED", font=M.poppins_x(46), fill=INK, anchor="mm")
    td.text((80 + half_w // 2, y0 + 1100), "Double-Wall Air Gap Thermal Insulation", font=M.poppins(36), fill=ORANGE, anchor="mm")
    bullets_l = [
        "Inside diameter: 67.5 mm (fits standard 66.2 mm cans)",
        "Diamond tactile knurling prevents wet hand slips",
        "Anti-vacuum suction drain hole in base",
        "4.2mm thick walls for superior thermal retention"
    ]
    for bi, b in enumerate(bullets_l):
        td.text((120, y0 + 1180 + bi * 65), f"*  {b}", font=M.poppins(32), fill=INK, anchor="la")

    # Right text
    rx0 = 80 + half_w + 60
    td.text((rx0 + half_w // 2, y0 + 60), "SLIM 12OZ SELTZER", font=M.anton(52), fill=ACCENT, anchor="mm")
    td.text((rx0 + half_w // 2, y0 + 1040), "SLIMGRIP HONEYCOMB", font=M.poppins_x(46), fill=INK, anchor="mm")
    td.text((rx0 + half_w // 2, y0 + 1100), "18-Sided Faceted Ergonomic Sleeve", font=M.poppins(36), fill=ORANGE, anchor="mm")
    bullets_r = [
        "Inside diameter: 59.3 mm (fits White Claw, Red Bull, etc.)",
        "3 Recessed perimeter grip bands for finger placement",
        "Beveled rim allows effortless smooth insertion",
        "Compact footprint fits neatly in standard cup holders"
    ]
    for bi, b in enumerate(bullets_r):
        td.text((rx0 + 40, y0 + 1180 + bi * 65), f"*  {b}", font=M.poppins(32), fill=INK, anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 05: FEATURE SPOTLIGHT: CAR EXPANDER & ADVENTURE HOLSTER
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "CAR EXPANDER & ADVENTURE HOLSTER", "DualDrive Stepped Adapter & TrailLock Carabiner Holster", 70)

    half_w = (SIZE - 220) // 2
    h = 1580
    y0 = top + 30

    card_l = M.rounded((half_w, h), 56, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (80, y0), blur=32, off=(0, 18), alpha=120)

    card_r = M.rounded((half_w, h), 56, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_r, (80 + half_w + 60, y0), blur=32, off=(0, 18), alpha=120)

    rf_l = RENDERS_DIR / "single_06.png"
    if rf_l.exists():
        im = load_render_cropped(rf_l)
        s = min((half_w - 100) / im.width, 820 / im.height)
        nw, nh = int(im.width * s), int(im.height * s)
        im_s = im.resize((nw, nh), Image.LANCZOS)
        sh = make_contact_shadow(int(nw * 0.85), 55, blur=24, alpha=160)
        base.alpha_composite(sh, (80 + (half_w - sh.width) // 2, y0 + 120 + nh - 20))
        base.alpha_composite(im_s, (80 + (half_w - nw) // 2, y0 + 120))

    rf_r = RENDERS_DIR / "single_05.png"
    if rf_r.exists():
        im = load_render_cropped(rf_r)
        s = min((half_w - 100) / im.width, 820 / im.height)
        nw, nh = int(im.width * s), int(im.height * s)
        im_s = im.resize((nw, nh), Image.LANCZOS)
        sh = make_contact_shadow(int(nw * 0.85), 55, blur=24, alpha=160)
        base.alpha_composite(sh, (80 + half_w + 60 + (half_w - sh.width) // 2, y0 + 120 + nh - 20))
        base.alpha_composite(im_s, (80 + half_w + 60 + (half_w - nw) // 2, y0 + 120))

    td = ImageDraw.Draw(base)
    # Left text
    td.text((80 + half_w // 2, y0 + 60), "ROAD TRIP CAR EXPANDER", font=M.anton(52), fill=ACCENT, anchor="mm")
    td.text((80 + half_w // 2, y0 + 1040), "DUALDRIVE STEPPED ADAPTER", font=M.poppins_x(46), fill=INK, anchor="mm")
    td.text((80 + half_w // 2, y0 + 1100), "Converts 68mm Car Console to 88mm", font=M.poppins(36), fill=ORANGE, anchor="mm")
    bullets_l = [
        "Stepped base: 68 mm OD fits virtually all car consoles",
        "Top cup: 84 mm ID holds Hydroflask, Yeti & oversized mugs",
        "Prevents tall beverage bottles from tipping on sharp turns",
        "Sturdy solid floor with center drain hole"
    ]
    for bi, b in enumerate(bullets_l):
        td.text((120, y0 + 1180 + bi * 65), f"*  {b}", font=M.poppins(32), fill=INK, anchor="la")

    # Right text
    rx0 = 80 + half_w + 60
    td.text((rx0 + half_w // 2, y0 + 60), "OUTDOOR ADVENTURE", font=M.anton(52), fill=ACCENT, anchor="mm")
    td.text((rx0 + half_w // 2, y0 + 1040), "TRAILLOCK CARABINER HOLSTER", font=M.poppins_x(46), fill=INK, anchor="mm")
    td.text((rx0 + half_w // 2, y0 + 1100), "Clip-On Can Holder for Camping & Boats", font=M.poppins(36), fill=ORANGE, anchor="mm")
    bullets_r = [
        "Reinforced 10mm carabiner eyelet near top rim",
        "Attach to backpacks, camping chairs, belts & boat rails",
        "Vertical perimeter traction flutes for secure grip",
        "Heavy-duty impact-resistant 3.8mm shell wall"
    ]
    for bi, b in enumerate(bullets_r):
        td.text((rx0 + 40, y0 + 1180 + bi * 65), f"*  {b}", font=M.poppins(32), fill=INK, anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 06: LIFESTYLE / PRODUCT IN USE
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "OUTDOORS • HOME • ROAD TRIPS", "Designed for real-world everyday utility", 70)

    # Large centerpiece card
    cw, ch = SIZE - 160, 1550
    cx, cy = 80, top + 30
    c_card = M.rounded((cw, ch), 64, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, c_card, (cx, cy), blur=34, off=(0, 20), alpha=120)

    # Place 3 key products in a lifestyle trio layout
    picks = [("single_01.png", "QuadGrip Caddy", -420, 1.05),
             ("single_03.png", "Diamond Can Cooler", 360, 0.95),
             ("single_06.png", "Car Adapter", -40, 0.90)]

    for f_name, label, off_x, scale in picks:
        rf = RENDERS_DIR / f_name
        if rf.exists():
            im = load_render_cropped(rf)
            s = (680 / im.height) * scale
            nw, nh = int(im.width * s), int(im.height * s)
            im_s = im.resize((nw, nh), Image.LANCZOS)
            px = SIZE // 2 + off_x - nw // 2
            py = cy + 180 + (680 - nh) // 2

            sh = make_contact_shadow(int(nw * 0.88), 65, blur=28, alpha=160)
            base.alpha_composite(sh, (px + (nw - sh.width) // 2, py + nh - 25))
            base.alpha_composite(im_s, (px, py))

    # Banner text at bottom
    td = ImageDraw.Draw(base)
    td.text((SIZE // 2, cy + ch - 480), "FUNCTIONAL DESIGNS BUILT FOR DAILY USE", font=M.anton(58), fill=ACCENT, anchor="mm")

    pills = [
        ("TAILGATES & PICNICS", "Carry 4 coffees, beers, or sodas at once with zero spills"),
        ("DAILY COMMUTE", "Expand narrow cup holders to hold large Hydroflasks & Yetis"),
        ("CAMPING & BOATING", "Clip your drink directly to your pack, boat rail, or deck chair")
    ]
    pw = (cw - 120) // 3
    for pi, (pt, pd) in enumerate(pills):
        px = cx + 40 + pi * (pw + 20)
        py = cy + ch - 380
        p_box = M.rounded((pw, 300), 32, LIGHT_TINT + (255,), outline=INK + (255,), width=4)
        base.alpha_composite(p_box, (px, py))
        p_draw = ImageDraw.Draw(base)
        p_draw.text((px + pw // 2, py + 45), pt, font=M.anton(38), fill=ORANGE, anchor="mm")

        words = pd.split()
        lines = []
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if p_draw.textlength(trial, font=M.poppins(28)) <= pw - 40:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        for li, line in enumerate(lines[:3]):
            p_draw.text((px + pw // 2, py + 120 + li * 40), line, font=M.poppins(28), fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 07: 100% SUPPORT-FREE 3D PRINTING & QUALITY GUARANTEE
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "EASY TO PRINT • 100% SUPPORT-FREE", "Engineered for flawless FDM printing on any machine", 70)

    cw, ch = SIZE - 160, 1550
    cx, cy = 80, top + 30
    c_card = M.rounded((cw, ch), 64, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, c_card, (cx, cy), blur=34, off=(0, 20), alpha=120)

    td = ImageDraw.Draw(base)

    sections = [
        ("ZERO SUPPORTS NEEDED", "Every single model prints 100% upright in its exported orientation. Zero supports, zero overhang droop, zero wasted plastic. Remove from build plate and enjoy immediately.", ACCENT),
        ("WATERTIGHT MANIFOLD MESHES", "Checked and validated with manifold geometry inspection. Zero non-manifold edges, zero holes, zero flipped normals. Clean, instant slicing in Bambu Studio, OrcaSlicer, PrusaSlicer & Cura.", ORANGE),
        ("OPTIMIZED WALL THICKNESS", "Heavy-duty 2.4mm to 4.2mm outer walls provide rugged drop protection, rigid structural integrity, and exceptional thermal insulation for chilled beverages.", ACCENT),
        ("FITS STANDARD 220 x 220 MM BEDS", "Even the largest 4-Cup Caddy is engineered within a 189 x 189 mm footprint - comfortably fitting standard Ender 3, Bambu Lab A1 / P1 / X1, and Prusa MK3 / MK4 build plates.", ORANGE),
        ("PLA & PETG COMPATIBLE", "Print in durable PETG for hot cars, direct summer sunlight, and outdoor adventure use. Standard PLA is perfect for indoor desks, workshops, and offices.", ACCENT)
    ]

    sec_h = (ch - 80 - (len(sections) - 1) * 25) // len(sections)
    for si, (st, sd, sc) in enumerate(sections):
        sy = cy + 40 + si * (sec_h + 25)
        panel = M.rounded((cw - 80, sec_h), 28, LIGHT_TINT + (255,), outline=sc + (255,), width=5)
        base.alpha_composite(panel, (cx + 40, sy))

        pd = ImageDraw.Draw(base)
        # Checkmark icon
        chk_pts = [(cx + 80, sy + sec_h // 2), (cx + 95, sy + sec_h // 2 + 18), (cx + 125, sy + sec_h // 2 - 18)]
        pd.line(chk_pts, fill=sc, width=7, joint="curve")

        pd.text((cx + 160, sy + 38), st, font=M.anton(44), fill=sc, anchor="la")

        words = sd.split()
        lines = []
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if pd.textlength(trial, font=M.poppins(30)) <= cw - 260:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        for li, line in enumerate(lines[:2]):
            pd.text((cx + 160, sy + 92 + li * 40), line, font=M.poppins(30), fill=INK, anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# CARD 08: PRINT SETTINGS & SLICER GUIDE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    out_p = IMAGES_DIR / "08_specs_dimensions.jpg"
    rows = [
        ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
        ("LAYER HEIGHT", "0.20 mm standard / 0.28 mm draft for rapid prints"),
        ("WALL LOOPS", "4 to 6 perimeters (2.4mm) for rugged structural rigidity"),
        ("INFILL DENSITY", "15% to 20% Gyroid pattern for balanced strength and speed"),
        ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar bed contact at Z=0"),
        ("MATERIALS", "PETG recommended for car consoles; PLA for indoor desks and gifts"),
    ]
    M.info_card(
        out_p,
        title="RECOMMENDED PRINT SETTINGS",
        kicker="OPTIMIZED FDM 3D PRINTING",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic."
    )
    return Image.open(out_p).convert("RGB")

# CARD 09: WHAT'S IN YOUR DOWNLOAD (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_09() -> Image.Image:
    out_p = IMAGES_DIR / "09_formats.jpg"
    rows = [
        ("8 STL FILES", "Universal binary STL files with precise millimeter scaling"),
        ("SLICER READY", "Drag-and-drop into Bambu Studio, OrcaSlicer, PrusaSlicer, or Cura"),
        ("SNUG CAN FIT", "Stepped inner shoulders fit standard 12oz cans and 12oz slim cans"),
        ("ZERO SUPPORTS", "Self-supporting overhangs and planar bases print with zero support waste"),
        ("PDF GUIDE", "Complete print guide, dimension table, slicer tips and commercial license"),
    ]
    M.info_card(
        out_p,
        title="WHAT'S IN YOUR DOWNLOAD",
        kicker="INSTANT DIGITAL DOWNLOAD",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Can_Holders_STL.zip (8 Solid STL Files) + Print_Guide_and_License.pdf"
    )
    return Image.open(out_p).convert("RGB")

# -----------------------------------------------------------------------------
# CARD 10: COMMERCIAL LICENSE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_10() -> Image.Image:
    out_p = IMAGES_DIR / "10_license.jpg"
    rows = [
        ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
        ("UNLIMITED", "Sell as many physical can holders as you make — no recurring royalties ever"),
        ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
        ("ORIGINAL", "100% original WORKHORSE functional designs — watertight guaranteed"),
        ("HELP", "Message the shop anytime if you need assistance with slicing or printing"),
    ]
    M.info_card(
        out_p,
        title="COMMERCIAL USE INCLUDED",
        kicker="PHYSICAL PRINT PERMISSION",
        rows=rows,
        accent=ORANGE,
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
        ("03_feature_caddy.jpg", make_card_03),
        ("04_feature_coolers.jpg", make_card_04),
        ("05_feature_adapter_holster.jpg", make_card_05),
        ("06_lifestyle.jpg", make_card_06),
        ("07_feature_quality.jpg", make_card_07),
        ("08_specs_dimensions.jpg", make_card_08),
        ("09_formats.jpg", make_card_09),
        ("10_commercial_license.jpg", make_card_10),
    ]
    print(f"Generating all 10 cards for Can & Drink Holders in {IMAGES_DIR}...")
    for fname, fn in cards:
        out_p = IMAGES_DIR / fname
        img = fn()
        img.save(out_p, quality=95, subsampling=0)
        print(f"  [OK] Saved {fname} ({out_p.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    build_all_cards()
