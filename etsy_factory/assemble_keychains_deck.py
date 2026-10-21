"""Assemble 10-Card Listing Deck for Functional EDC & Fitness Keychains STL Bundle.
Replicates the high-converting visual architecture of cute_animal_pencil_cups_stl_3mf_glb:
- Warm cream canvas #FAF7F2 with dark slate ink #1F2421
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

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"

SIZE = 2400
BG_COLOR = (250, 247, 242)      # #FAF7F2 warm cream
INK = (31, 36, 42)              # #1F242A deep charcoal/slate
ACCENT = (29, 99, 184)          # #1D63B8 royal EDC blue
ORANGE = (212, 92, 36)          # #D45C24 warm terracotta
GOLD = (255, 214, 0)            # #FFD600 starburst yellow
WHITE = (255, 255, 255)
LIGHT_TINT = (242, 240, 235)

CHIP_COLS = [
    ("STL", (29, 99, 184)),       # EDC Blue
    ("3D PRINT", (212, 92, 36)),  # Terracotta
    ("NO SUP", (46, 125, 114)),   # Slate Teal
    ("TESTED", (123, 82, 148)),   # Royal Violet
    ("COMMERCIAL", (200, 140, 30))# Honey Gold
]

ITEMS = [
    {"name": "PocketSnap Phone Stand", "tag": "EDC KICKSTAND", "sub": "Dual Angles * Keyring Loop", "file": "single_01.png", "dims": "62 x 26 x 8.5 mm"},
    {"name": "IronGrip Hex Dumbbell", "tag": "GYM KEYCHAIN", "sub": "Knurled Grip * Heavy Hex", "file": "single_02.png", "dims": "27 x 23 x 51 mm"},
    {"name": "ProPlate Bumper Plate", "tag": "OLYMPIC 45LB", "sub": "Center Hub & Outer Rim Lip", "file": "single_03.png", "dims": "44 x 44 x 4.8 mm"},
    {"name": "PowerBell Kettlebell", "tag": "CAST IRON BELL", "sub": "Contoured Handle * Flat Bottom", "file": "single_04.png", "dims": "27 x 27 x 40 mm"},
    {"name": "ArmorShield EDC Case", "tag": "PILL & TOOTHPICK", "sub": "Diamond Waffle Protection", "file": "single_05.png", "dims": "48 x 48 x 9.6 mm"},
    {"name": "Barbell Dumbbell Stack", "tag": "FITNESS CHARM", "sub": "Stacked Plates & Collar Nuts", "file": "single_06.png", "dims": "24 x 24 x 55 mm"},
    {"name": "HexDriver Bit Tool", "tag": "1/4\" BIT HOLDER", "sub": "Knurled EDC Screwdriver", "file": "single_07.png", "dims": "17 x 17 x 50 mm"},
    {"name": "QuickRelease Cart Token", "tag": "DUAL EDC TOOL", "sub": "Cart Release + Bottle Opener", "file": "single_08.png", "dims": "24 x 50 x 3.2 mm"},
]

def make_contact_shadow(width: int, height: int, blur: int = 24, alpha: int = 140) -> Image.Image:
    s = Image.new("RGBA", (width + blur * 4, height + blur * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse((blur * 2, blur * 2, blur * 2 + width, blur * 2 + height), fill=(25, 28, 35, alpha))
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
# CARD 01: HERO COVER
# -----------------------------------------------------------------------------
def make_card_01() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))

    # Central white rounded card container
    cw, ch = 1920, 1720
    cx, cy = (SIZE - cw) // 2, (SIZE - ch) // 2 - 20
    card = M.rounded((cw, ch), 85, (255, 255, 255, 255), outline=INK + (255,), width=12)
    M.shadowed(base, card, (cx, cy), blur=38, off=(0, 24), alpha=130)

    d = ImageDraw.Draw(base)

    # Top ribbon pill: "COMMERCIAL USE INCLUDED"
    rb = "COMMERCIAL USE INCLUDED"
    f_rb = M.fit(d, rb, M.poppins_x, 1250, 56)
    tw = M.text_w(d, rb, f_rb)
    pill = M.rounded((tw + 110, 100), 50, ACCENT + (255,))
    base.alpha_composite(pill, (SIZE // 2 - (tw + 110) // 2, cy - 50))
    d.text((SIZE // 2, cy), rb, font=f_rb, fill=WHITE, anchor="mm")

    # Big Number "8"
    big = "8"
    fb = M.anton(280)
    bbn = d.textbbox((0, 0), big, font=fb, anchor="ma")
    ntop = cy + 65
    M.grad_fill_text(base, (SIZE // 2, ntop - bbn[1]), big, fb, (245, 175, 65), ORANGE, INK, 12)

    # Primary Title Line
    ty = ntop + (bbn[3] - bbn[1]) + 18
    t_text = "FUNCTIONAL KEYCHAIN PACK"
    fl = M.fit(d, t_text, M.anton, cw - 180, 125, 75)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "Phone Stand  *  Hex Dumbbell  *  Olympic Plate  *  EDC Tools"
    fs = M.fit(d, sub, M.pacifico, cw - 240, 66, 36)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    d.text((SIZE // 2, ty + (bb[3] - bb[1]) + 14 - bbs[1]), sub, font=fs, fill=ACCENT, anchor="ma")

    # Hero Product Showcase in center of card
    hero_y = ty + (bb[3] - bb[1]) + (bbs[3] - bbs[1]) + 35
    hero_w = cw - 140
    hero_h = 790

    p_cluster = RENDERS_DIR / "cluster_hero.png"
    if p_cluster.exists():
        im_hero = load_render_cropped(p_cluster)
        s = min((hero_w - 60) / im_hero.width, (hero_h - 100) / im_hero.height)
        nw, nh = int(im_hero.width * s), int(im_hero.height * s)
        im_scaled = im_hero.resize((nw, nh), Image.LANCZOS)

        # Grounded contact shadow
        sh = make_contact_shadow(int(nw * 0.90), 85, blur=32, alpha=160)
        base.alpha_composite(sh, (SIZE // 2 - sh.width // 2, hero_y + nh - 30))

        # Paste product
        base.alpha_composite(im_scaled, (SIZE // 2 - nw // 2, hero_y + (hero_h - nh) // 2 - 20))

    # Format Chips across bottom of card
    n_chips = len(CHIP_COLS)
    r = 88
    gap = 40
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 125
    for j, (label, col) in enumerate(CHIP_COLS):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=7)
        fc = M.fit(d, label, M.anton, 2 * r - 26, 64, 22)
        d.text((xx, cyy + 3), label, font=fc, fill=WHITE, anchor="mm")

    # Bottom machine strip
    strip = "BAMBU LAB  *  PRUSA  *  CREALITY  *  ANY SLICER"
    fs2 = M.fit(d, strip, M.poppins_x, SIZE - 260, 54, 26)
    sw = M.text_w(d, strip, fs2)
    sp = M.rounded((sw + 100, 96), 48, INK + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 100) // 2, SIZE - 150))
    d.text((SIZE // 2, SIZE - 102), strip, font=fs2, fill=WHITE, anchor="mm")

    # 40-Point Yellow Starburst Badge ("INSTANT DOWNLOAD")
    bx, by, br = SIZE - 240, 250, 210
    pts = []
    for q in range(40):
        a = math.pi * 2 * q / 40
        rr = br if q % 2 == 0 else br * 0.82
        pts.append((bx + rr * math.cos(a), by + rr * math.sin(a)))
    star = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(star).polygon(pts, fill=GOLD + (255,), outline=INK + (255,), width=8)
    base.alpha_composite(star)

    ds = ImageDraw.Draw(base)
    f_b1 = M.fit(ds, "INSTANT", M.anton, 240, 52, 28)
    f_b2 = M.fit(ds, "DOWNLOAD", M.anton, 270, 56, 30)
    ds.text((bx, by - 32), "INSTANT", font=f_b1, fill=INK, anchor="mm")
    ds.text((bx, by + 30), "DOWNLOAD", font=f_b2, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 02: ALL 8 DESIGNS GRID
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "ALL 8 KEYCHAIN DESIGNS", "Everyday carry utility, gym motivation & pocket tools")

    grid_w, grid_h = SIZE - 180, SIZE - y_start - 120
    cols, rows = 4, 2
    cell_w, cell_h = grid_w // cols, grid_h // rows
    gx0 = (SIZE - grid_w) // 2

    for i, it in enumerate(ITEMS):
        col, row = i % cols, i // cols
        cx = gx0 + col * cell_w + 14
        cy = y_start + row * cell_h + 14
        cw, ch = cell_w - 28, cell_h - 28

        c_box = M.rounded((cw, ch), 44, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, c_box, (cx, cy), blur=18, off=(0, 10), alpha=70)

        dc = ImageDraw.Draw(base)

        # Number pill top left
        np = M.rounded((80, 52), 26, ACCENT + (255,))
        base.alpha_composite(np, (cx + 20, cy + 20))
        fn = M.poppins_x(28)
        dc.text((cx + 60, cy + 46), f"{i+1:02d}", font=fn, fill=WHITE, anchor="mm")

        # Category tag
        ftag = M.fit(dc, it["tag"], M.poppins_x, cw - 140, 24, 14)
        dc.text((cx + cw - 20, cy + 46), it["tag"], font=ftag, fill=ORANGE, anchor="rm")

        # Render image
        rp = RENDERS_DIR / it["file"]
        if rp.exists():
            im_r = load_render_cropped(rp)
            max_pw, max_ph = cw - 50, ch - 190
            sc = min(max_pw / im_r.width, max_ph / im_r.height)
            rw, rh = int(im_r.width * sc), int(im_r.height * sc)
            im_s = im_r.resize((rw, rh), Image.LANCZOS)

            # Grounded shadow
            sh = make_contact_shadow(int(rw * 0.85), 45, blur=18, alpha=130)
            base.alpha_composite(sh, (cx + cw // 2 - sh.width // 2, cy + 85 + max_ph - 15))
            base.alpha_composite(im_s, (cx + cw // 2 - rw // 2, cy + 85 + (max_ph - rh) // 2))

        # Bottom Labels
        fnm = M.fit(dc, it["name"], M.anton, cw - 30, 36, 20)
        dc.text((cx + cw // 2, cy + ch - 64), it["name"], font=fnm, fill=INK, anchor="mm")

        fsub = M.fit(dc, it["dims"], M.poppins, cw - 30, 24, 15)
        dc.text((cx + cw // 2, cy + ch - 28), it["dims"], font=fsub, fill=(100, 105, 115), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 03: FEATURE SPOTLIGHT - POCKETSNAP PHONE STAND
# -----------------------------------------------------------------------------
def make_card_03() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "DUAL-SLOT PHONE KICKSTAND", "PocketSnap folds flat on your keyring and supports any smartphone")

    # Left Column: Large Hero 3D Render
    lw, lh = 1200, SIZE - y_start - 160
    lx, ly = 100, y_start + 40
    card_l = M.rounded((lw, lh), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (lx, ly), blur=32, off=(0, 18), alpha=90)

    rp = RENDERS_DIR / "single_01.png"
    if rp.exists():
        im_r = load_render_cropped(rp)
        sc = min((lw - 140) / im_r.width, (lh - 200) / im_r.height)
        rw, rh = int(im_r.width * sc), int(im_r.height * sc)
        im_s = im_r.resize((rw, rh), Image.LANCZOS)
        sh = make_contact_shadow(int(rw * 0.90), 80, blur=30, alpha=150)
        base.alpha_composite(sh, (lx + lw // 2 - sh.width // 2, ly + lh - 120))
        base.alpha_composite(im_s, (lx + lw // 2 - rw // 2, ly + (lh - rh) // 2 - 30))

    # Right Column: Feature Spec Callouts
    rx, ry = 1360, y_start + 40
    rw = SIZE - rx - 100

    features = [
        ("DUAL KICKSTAND ANGLES", "Features 22° and 20° precision tilt angles for video calls and desktop media streaming.", "01"),
        ("UNIVERSAL PHONE FIT", "Dual-width slots accommodate slim smartphones as well as devices in rugged thick cases.", "02"),
        ("COMPACT EDC PROFILE", "At only 62 x 26 x 8.5 mm, it slips seamlessly onto your keychain without adding bulk.", "03"),
        ("100% SUPPORT-FREE", "Engineered with chamfered slots that print flat on the build plate without support material.", "04"),
    ]

    box_h = (lh - 3 * 35) // 4
    for i, (title, desc, num) in enumerate(features):
        by = ry + i * (box_h + 35)
        c_b = M.rounded((rw, box_h), 40, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, c_b, (rx, by), blur=16, off=(0, 8), alpha=60)

        db = ImageDraw.Draw(base)
        # Number badge
        nb = M.rounded((68, 68), 34, ACCENT + (255,))
        base.alpha_composite(nb, (rx + 28, by + box_h // 2 - 34))
        fn = M.anton(38)
        db.text((rx + 62, by + box_h // 2 + 2), num, font=fn, fill=WHITE, anchor="mm")

        # Text
        ft = M.fit(db, title, M.anton, rw - 135, 42, 24)
        db.text((rx + 120, by + 40), title, font=ft, fill=INK, anchor="la")

        fd = M.fit(db, desc, M.poppins, rw - 135, 28, 16)
        # Multi-line wrap
        words = desc.split()
        lines = []
        cur = []
        for w in words:
            if M.text_w(db, " ".join(cur + [w]), fd) < (rw - 145):
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))

        for j, ln in enumerate(lines[:3]):
            db.text((rx + 120, by + 92 + j * 34), ln, font=fd, fill=(70, 75, 85), anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 04: FEATURE SPOTLIGHT - GYM & FITNESS TRIO
# -----------------------------------------------------------------------------
def make_card_04() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "GYM & FITNESS MOTIVATION", "Realistic 3D fitness keychains: Hex Dumbbell, Bumper Plate & Kettlebell")

    trio = [
        ("IronGrip Hex Dumbbell", "Tactile Knurled Handle * Heavy Hex Ends", "single_02.png", "27 x 23 x 51 mm"),
        ("ProPlate Olympic Plate", "Embossed 45LB / 20KG * Outer Rim Lip", "single_03.png", "44 x 44 x 4.8 mm"),
        ("PowerBell Kettlebell", "Contoured Handle * Flat Stable Bottom", "single_04.png", "27 x 27 x 40 mm"),
    ]

    card_w = (SIZE - 200 - 2 * 50) // 3
    card_h = SIZE - y_start - 160
    y_top = y_start + 40

    for i, (title, sub, fname, dims) in enumerate(trio):
        cx = 100 + i * (card_w + 50)
        c_box = M.rounded((card_w, card_h), 65, WHITE + (255,), outline=INK + (255,), width=8)
        M.shadowed(base, c_box, (cx, y_top), blur=28, off=(0, 16), alpha=85)

        dc = ImageDraw.Draw(base)

        # Ribbon badge
        rb = M.rounded((card_w - 70, 60), 30, ORANGE + (255,))
        base.alpha_composite(rb, (cx + 35, y_top + 35))
        frb = M.fit(dc, f"FITNESS EDC #{i+1:02d}", M.poppins_x, card_w - 90, 26, 16)
        dc.text((cx + card_w // 2, y_top + 65), f"FITNESS EDC #{i+1:02d}", font=frb, fill=WHITE, anchor="mm")

        # 3D Render
        rp = RENDERS_DIR / fname
        if rp.exists():
            im_r = load_render_cropped(rp)
            max_pw, max_ph = card_w - 80, card_h - 380
            sc = min(max_pw / im_r.width, max_ph / im_r.height)
            rw, rh = int(im_r.width * sc), int(im_r.height * sc)
            im_s = im_r.resize((rw, rh), Image.LANCZOS)

            sh = make_contact_shadow(int(rw * 0.90), 65, blur=24, alpha=140)
            base.alpha_composite(sh, (cx + card_w // 2 - sh.width // 2, y_top + 130 + max_ph - 25))
            base.alpha_composite(im_s, (cx + card_w // 2 - rw // 2, y_top + 130 + (max_ph - rh) // 2))

        # Bottom info card
        ft = M.fit(dc, title, M.anton, card_w - 50, 48, 26)
        dc.text((cx + card_w // 2, y_top + card_h - 180), title, font=ft, fill=INK, anchor="mm")

        fsub = M.fit(dc, sub, M.poppins, card_w - 60, 28, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 120), sub, font=fsub, fill=ACCENT, anchor="mm")

        fdim = M.fit(dc, f"Size: {dims}", M.poppins_x, card_w - 80, 26, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 70), f"Size: {dims}", font=fdim, fill=(110, 115, 125), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 05: FEATURE SPOTLIGHT - EDC DAILY CARRY TOOLS
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "EDC POCKET TOOL KEYCHAINS", "Everyday carry essentials: 1/4\" Bit Screwdriver, Armor Case & Shopping Token")

    edc_trio = [
        ("HexDriver Bit Tool", "Holds standard 1/4\" hex bits with tactile grip", "single_07.png", "17 x 17 x 50 mm"),
        ("ArmorShield Case", "Waffle texture protective case for small essentials", "single_05.png", "48 x 48 x 9.6 mm"),
        ("QuickRelease Cart Token", "Quarter/Euro shopping cart release + bottle opener", "single_08.png", "24 x 50 x 3.2 mm"),
    ]

    card_w = (SIZE - 200 - 2 * 50) // 3
    card_h = SIZE - y_start - 160
    y_top = y_start + 40

    for i, (title, sub, fname, dims) in enumerate(edc_trio):
        cx = 100 + i * (card_w + 50)
        c_box = M.rounded((card_w, card_h), 65, WHITE + (255,), outline=INK + (255,), width=8)
        M.shadowed(base, c_box, (cx, y_top), blur=28, off=(0, 16), alpha=85)

        dc = ImageDraw.Draw(base)

        rb = M.rounded((card_w - 70, 60), 30, (46, 125, 114, 255))
        base.alpha_composite(rb, (cx + 35, y_top + 35))
        frb = M.fit(dc, f"EDC ESSENTIAL #{i+1:02d}", M.poppins_x, card_w - 90, 26, 16)
        dc.text((cx + card_w // 2, y_top + 65), f"EDC ESSENTIAL #{i+1:02d}", font=frb, fill=WHITE, anchor="mm")

        rp = RENDERS_DIR / fname
        if rp.exists():
            im_r = load_render_cropped(rp)
            max_pw, max_ph = card_w - 80, card_h - 380
            sc = min(max_pw / im_r.width, max_ph / im_r.height)
            rw, rh = int(im_r.width * sc), int(im_r.height * sc)
            im_s = im_r.resize((rw, rh), Image.LANCZOS)

            sh = make_contact_shadow(int(rw * 0.90), 65, blur=24, alpha=140)
            base.alpha_composite(sh, (cx + card_w // 2 - sh.width // 2, y_top + 130 + max_ph - 25))
            base.alpha_composite(im_s, (cx + card_w // 2 - rw // 2, y_top + 130 + (max_ph - rh) // 2))

        ft = M.fit(dc, title, M.anton, card_w - 50, 48, 26)
        dc.text((cx + card_w // 2, y_top + card_h - 180), title, font=ft, fill=INK, anchor="mm")

        fsub = M.fit(dc, sub, M.poppins, card_w - 60, 28, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 120), sub, font=fsub, fill=ACCENT, anchor="mm")

        fdim = M.fit(dc, f"Size: {dims}", M.poppins_x, card_w - 80, 26, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 70), f"Size: {dims}", font=fdim, fill=(110, 115, 125), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 06: LIFESTYLE / IN-USE CONTEXT
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "ENGINEERED FOR EVERYDAY CARRY", "Lightweight, pocketable, and ready for gym bags, keys, and backpacks")

    # Center showcase card
    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 75, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    # 4 Context quadrants
    quads = [
        ("CAR & HOUSE KEYS", "Compact footprint clips neatly alongside standard key fobs without bulk.", "single_01.png"),
        ("GYM BAG CHARM", "Instant identifier for workout duffels, locker keys, and lifting accessories.", "single_02.png"),
        ("BACKPACK & EDC GEAR", "Tough reinforced 4.6mm ring loops clip to MOLLE webbing and carabiners.", "single_05.png"),
        ("POCKET TRAVEL COMPANION", "Lightweight 100% infill durability that withstands drops, coins, and keys.", "single_08.png"),
    ]

    qw, qh = (cw - 60) // 2, (ch - 60) // 2
    for i, (qtitle, qdesc, qfile) in enumerate(quads):
        qx = cx + 20 + (i % 2) * (qw + 20)
        qy = cy + 20 + (i // 2) * (qh + 20)

        qb = M.rounded((qw, qh), 45, LIGHT_TINT + (255,), outline=INK + (255,), width=5)
        base.alpha_composite(qb, (qx, qy))

        dq = ImageDraw.Draw(base)
        # 3D Render
        rp = RENDERS_DIR / qfile
        if rp.exists():
            im_r = load_render_cropped(rp)
            max_pw, max_ph = qw - 80, qh - 220
            sc = min(max_pw / im_r.width, max_ph / im_r.height)
            rw, rh = int(im_r.width * sc), int(im_r.height * sc)
            im_s = im_r.resize((rw, rh), Image.LANCZOS)
            sh = make_contact_shadow(int(rw * 0.85), 45, blur=20, alpha=130)
            base.alpha_composite(sh, (qx + qw // 2 - sh.width // 2, qy + 40 + max_ph - 15))
            base.alpha_composite(im_s, (qx + qw // 2 - rw // 2, qy + 40 + (max_ph - rh) // 2))

        # Text
        fqt = M.fit(dq, qtitle, M.anton, qw - 60, 42, 24)
        dq.text((qx + qw // 2, qy + qh - 130), qtitle, font=fqt, fill=INK, anchor="mm")

        fqd = M.fit(dq, qdesc, M.poppins, qw - 80, 24, 15)
        dq.text((qx + qw // 2, qy + qh - 65), qdesc, font=fqd, fill=(80, 85, 95), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 07: FEATURE QUALITY & PRINT DETAILS
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "PRINT QUALITY & ENGINEERING", "100% Watertight geometry, reinforced eyelets, and support-free printing")

    # Left Box: Detail Closeup
    lw, lh = 1100, SIZE - y_start - 160
    lx, ly = 120, y_start + 40
    card_l = M.rounded((lw, lh), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (lx, ly), blur=32, off=(0, 18), alpha=90)

    rp = RENDERS_DIR / "single_07.png" # HexDriver detail
    if rp.exists():
        im_r = load_render_cropped(rp)
        sc = min((lw - 140) / im_r.width, (lh - 200) / im_r.height)
        rw, rh = int(im_r.width * sc), int(im_r.height * sc)
        im_s = im_r.resize((rw, rh), Image.LANCZOS)
        sh = make_contact_shadow(int(rw * 0.90), 80, blur=30, alpha=150)
        base.alpha_composite(sh, (lx + lw // 2 - sh.width // 2, ly + lh - 120))
        base.alpha_composite(im_s, (lx + lw // 2 - rw // 2, ly + (lh - rh) // 2 - 30))

    # Right Box: Quality Spec Badges
    rx, ry = 1280, y_start + 40
    rw = SIZE - rx - 120

    badges = [
        ("ZERO SUPPORTS REQUIRED", "Every model is mathematically modeled with self-supporting draft angles that require zero slicer supports.", "check"),
        ("REINFORCED KEYRING HOLES", "Eyelet walls are at least 2.2 mm thick to prevent breakage under continuous everyday pocket strain.", "check"),
        ("100% WATERTIGHT MESHES", "Checked and verified with 0 non-manifold edges, 0 intersecting faces, and perfect FDM slicer slices.", "check"),
        ("FAST PRINTS - HIGH TURNOVER", "Each keychain prints in 15 to 45 minutes, allowing you to batch produce dozens per build plate.", "check"),
    ]

    bh = (lh - 3 * 35) // 4
    for i, (btitle, bdesc, _) in enumerate(badges):
        by = ry + i * (bh + 35)
        c_b = M.rounded((rw, bh), 40, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, c_b, (rx, by), blur=16, off=(0, 8), alpha=60)

        db = ImageDraw.Draw(base)
        # Check badge
        chk = M.rounded((68, 68), 34, ACCENT + (255,))
        base.alpha_composite(chk, (rx + 28, by + bh // 2 - 34))
        fchk = M.anton(40)
        db.text((rx + 62, by + bh // 2 + 2), "OK", font=fchk, fill=WHITE, anchor="mm")

        fbt = M.fit(db, btitle, M.anton, rw - 135, 38, 22)
        db.text((rx + 120, by + 36), btitle, font=fbt, fill=INK, anchor="la")

        fbd = M.fit(db, bdesc, M.poppins, rw - 135, 26, 16)
        words = bdesc.split()
        lines = []
        cur = []
        for w in words:
            if M.text_w(db, " ".join(cur + [w]), fbd) < (rw - 145):
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))

        for j, ln in enumerate(lines[:3]):
            db.text((rx + 120, by + 86 + j * 32), ln, font=fbd, fill=(70, 75, 85), anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 08: EXACT DIMENSIONS & SIZING CHART
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "EXACT MEASURED DIMENSIONS", "Verified millimetre dimensions measured directly from the print-ready STL files")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    dc = ImageDraw.Draw(base)

    # Header Row
    headers = ["#", "MODEL NAME", "CATEGORY", "DIMENSIONS (W x D x H)", "PRINT TIME"]
    col_w = [100, 680, 420, 520, 360]
    hx = cx + 40
    hy = cy + 40

    h_bar = M.rounded((cw - 80, 80), 30, INK + (255,))
    base.alpha_composite(h_bar, (hx, hy))

    cur_x = hx + 25
    for h_txt, w in zip(headers, col_w):
        fh = M.fit(dc, h_txt, M.poppins_x, w - 20, 28, 16)
        dc.text((cur_x, hy + 40), h_txt, font=fh, fill=WHITE, anchor="lm")
        cur_x += w

    # Table Rows
    specs_data = [
        ("01", "PocketSnap Folding Phone Stand", "EDC Kickstand", "62.0 x 26.0 x 8.5 mm", "~28 mins"),
        ("02", "IronGrip Hex Dumbbell Keychain", "Gym Motivation", "27.0 x 23.4 x 50.6 mm", "~35 mins"),
        ("03", "ProPlate Olympic Weight Plate", "45LB Bumper Plate", "44.0 x 44.0 x 4.8 mm", "~22 mins"),
        ("04", "PowerBell Cast Iron Kettlebell", "Cast Iron Fitness", "27.0 x 27.0 x 39.7 mm", "~32 mins"),
        ("05", "ArmorShield EDC Protective Case", "EDC Protection", "47.5 x 47.5 x 9.6 mm", "~42 mins"),
        ("06", "Barbell Dumbbell Weight Stack", "Gym Accessories", "24.0 x 24.0 x 54.7 mm", "~34 mins"),
        ("07", "HexDriver Pocket Bit Tool", "1/4\" Bit Screwdriver", "16.6 x 16.6 x 49.9 mm", "~30 mins"),
        ("08", "QuickRelease Cart Token & Opener", "Cart Token + Opener", "24.0 x 50.0 x 3.2 mm", "~18 mins"),
    ]

    row_h = (ch - 240) // 8
    for i, (num, name, cat, dims, ptime) in enumerate(specs_data):
        ry = hy + 95 + i * row_h
        row_bg = LIGHT_TINT if i % 2 == 0 else (255, 255, 255)
        rb = M.rounded((cw - 80, row_h - 10), 20, row_bg + (255,))
        base.alpha_composite(rb, (hx, ry))

        cur_x = hx + 25
        vals = [num, name, cat, dims, ptime]
        for j, (val, w) in enumerate(zip(vals, col_w)):
            fnt = M.poppins_x if j in (0, 1) else M.poppins
            f_sz = 26 if j == 1 else 24
            fv = M.fit(dc, val, fnt, w - 20, f_sz, 14)
            col_ink = ACCENT if j == 0 else (INK if j == 1 else (ORANGE if j == 4 else (70, 75, 85)))
            dc.text((cur_x, ry + (row_h - 10) // 2), val, font=fv, fill=col_ink, anchor="lm")
            cur_x += w

    # Bottom Footer Note
    f_ft = M.fit(dc, "* Estimated print times based on 0.20 mm layer height, 3 perimeters, and 15% infill on standard Bambu / Prusa printers.", M.poppins, cw - 100, 24, 14)
    dc.text((cx + cw // 2, cy + ch - 40), "* Estimated print times based on 0.20 mm layer height, 3 perimeters, and 15% infill on standard Bambu / Prusa printers.", font=f_ft, fill=(120, 125, 135), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 09: FORMATS & PRINTER COMPATIBILITY
# -----------------------------------------------------------------------------
def make_card_09() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "PRINTER & SLICER COMPATIBILITY", "Works with Bambu Lab, Prusa, Creality, Anycubic, Voron, and any FDM 3D printer")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    dc = ImageDraw.Draw(base)

    # 4 Machine Pillars
    pillars = [
        ("UNIVERSAL STL FORMAT", "Standardized binary STL files with millimeter scaling, compatible with Bambu Studio, PrusaSlicer, Cura, OrcaSlicer, and Simplify3D.", "STL"),
        ("MATERIAL FLEXIBILITY", "Prints flawlessly in PLA, PETG, ABS, ASA, or Tough PLA. Use PETG for outdoor weatherability and UV resistance.", "PLA"),
        ("OPTIMIZED LAYER SLICING", "Designed for standard 0.4 mm nozzles and 0.20 mm layer heights. Zero delicate overhangs or impossible bridges.", "0.2MM"),
        ("PRINTABLE PDF GUIDE & SPECS", "Comprehensive instruction guide included detailing print orientations, slicer recommendations, and commercial rights.", "PDF"),
    ]

    pw = (cw - 60 - 3 * 30) // 4
    ph = ch - 120
    for i, (title, desc, badge) in enumerate(pillars):
        px = cx + 30 + i * (pw + 30)
        py = cy + 60

        pb = M.rounded((pw, ph), 45, LIGHT_TINT + (255,), outline=INK + (255,), width=6)
        base.alpha_composite(pb, (px, py))

        dp = ImageDraw.Draw(base)

        # Big Badge
        bd = M.rounded((pw - 60, 90), 45, ACCENT + (255,))
        base.alpha_composite(bd, (px + 30, py + 45))
        f_bd = M.fit(dp, badge, M.anton, pw - 80, 52, 24)
        dp.text((px + pw // 2, py + 90), badge, font=f_bd, fill=WHITE, anchor="mm")

        # Title
        f_pt = M.fit(dp, title, M.anton, pw - 50, 42, 22)
        dp.text((px + pw // 2, py + 185), title, font=f_pt, fill=INK, anchor="mm")

        # Description
        f_pd = M.fit(dp, desc, M.poppins, pw - 50, 26, 16)
        words = desc.split()
        lines = []
        cur = []
        for w in words:
            if M.text_w(dp, " ".join(cur + [w]), f_pd) < (pw - 60):
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))

        for j, ln in enumerate(lines[:6]):
            dp.text((px + pw // 2, py + 260 + j * 38), ln, font=f_pd, fill=(70, 75, 85), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 10: COMMERCIAL LICENSE & SMALL BUSINESS PERMISSION
# -----------------------------------------------------------------------------
def make_card_10() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "COMMERCIAL PRINTING LICENSE", "Sell physical prints in your Etsy shop, local craft markets, and online stores")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    dc = ImageDraw.Draw(base)

    # Big Gold Crest
    crest_w, crest_h = 950, 130
    cx0 = cx + (cw - crest_w) // 2
    c_rib = M.rounded((crest_w, crest_h), 65, ORANGE + (255,))
    base.alpha_composite(c_rib, (cx0, cy + 50))
    f_cr = M.fit(dc, "COMMERCIAL USE PERMITTED", M.anton, crest_w - 60, 68, 32)
    dc.text((SIZE // 2, cy + 115), "COMMERCIAL USE PERMITTED", font=f_cr, fill=WHITE, anchor="mm")

    # Permissions vs Restrictions
    lw = (cw - 100) // 2
    lh = ch - 260
    ly = cy + 220

    # Allowed Box
    lx = cx + 40
    box_allow = M.rounded((lw, lh), 45, (244, 250, 245, 255), outline=(44, 120, 68, 255), width=6)
    base.alpha_composite(box_allow, (lx, ly))

    da = ImageDraw.Draw(base)
    f_at = M.anton(46)
    da.text((lx + lw // 2, ly + 50), "WHAT YOU CAN DO", font=f_at, fill=(44, 120, 68), anchor="mm")

    allows = [
        "Sell unlimited physical 3D prints made from these STL files",
        "Offer printed keychains at craft fairs, farmers markets, and Etsy",
        "Customize print filament colors, layer heights, and infill",
        "Batch print for local gyms, fitness clubs, and corporate swag",
        "Lifetime commercial rights with no recurring subscription fees",
    ]
    for k, txt in enumerate(allows):
        chk = M.rounded((42, 42), 21, (44, 120, 68, 255))
        base.alpha_composite(chk, (lx + 35, ly + 110 + k * 80))
        da.text((lx + 56, ly + 131 + k * 80), "OK", font=M.poppins_x(18), fill=WHITE, anchor="mm")
        f_tx = M.fit(da, txt, M.poppins, lw - 120, 26, 16)
        da.text((lx + 95, ly + 131 + k * 80), txt, font=f_tx, fill=INK, anchor="lm")

    # Restrictions Box
    rx = cx + lw + 60
    box_rest = M.rounded((lw, lh), 45, (253, 245, 245, 255), outline=(190, 50, 50, 255), width=6)
    base.alpha_composite(box_rest, (rx, ly))

    dr = ImageDraw.Draw(base)
    f_rt = M.anton(46)
    dr.text((rx + lw // 2, ly + 50), "WHAT IS RESTRICTED", font=f_rt, fill=(190, 50, 50), anchor="mm")

    restricts = [
        "Do NOT resell, share, or redistribute the digital STL files",
        "Do NOT upload digital models to file repositories or free sites",
        "Do NOT sell digital derivatives, meshes, or remixes",
        "Digital license is non-transferable to other digital merchants",
        "Physical finished prints only - digital files remain protected",
    ]
    for k, txt in enumerate(restricts):
        no_p = M.rounded((42, 42), 21, (190, 50, 50, 255))
        base.alpha_composite(no_p, (rx + 35, ly + 110 + k * 80))
        dr.text((rx + 56, ly + 131 + k * 80), "X", font=M.poppins_x(20), fill=WHITE, anchor="mm")
        f_tx = M.fit(dr, txt, M.poppins, lw - 120, 26, 16)
        dr.text((rx + 95, ly + 131 + k * 80), txt, font=f_tx, fill=INK, anchor="lm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# MAIN GENERATOR PIPELINE
# -----------------------------------------------------------------------------
def assemble_all_cards():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    deck = [
        ("01_cover.jpg", make_card_01),
        ("02_preview_all.jpg", make_card_02),
        ("03_feature_phonestand.jpg", make_card_03),
        ("04_feature_gym.jpg", make_card_04),
        ("05_feature_edc.jpg", make_card_05),
        ("06_lifestyle.jpg", make_card_06),
        ("07_feature_quality.jpg", make_card_07),
        ("08_specs_dimensions.jpg", make_card_08),
        ("09_formats.jpg", make_card_09),
        ("10_commercial_license.jpg", make_card_10),
    ]

    print(f"Generating all 10 cards for Keychains in {IMAGES_DIR}...")
    for fname, fn in deck:
        out_p = IMAGES_DIR / fname
        im = fn()
        im.save(out_p, "JPEG", quality=95, subsampling=0)
        print(f"  [OK] Saved {fname} ({out_p.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    assemble_all_cards()
