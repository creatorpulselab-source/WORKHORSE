"""Assemble 10-Card Listing Deck for Pack 2: Cute Animal Pencil Cups STL.
Replicates the exact visual language of coffee_lover_quotes_svg_png_bundle:
- 01_cover.jpg: Tiled preview + floating central white card with dark ink border, drop shadow,
  top ribbon "COMMERCIAL USE INCLUDED", giant gradient Anton "8", bold title, cursive Pacifico subtitle,
  featured hero lifestyle photo of the cups on oak desk, circular format chips (STL, 3MF, GLB, NO SUPPORTS, TESTED),
  16-point yellow starburst badge "INSTANT DOWNLOAD", bottom slicer pill "BAMBU LAB • PRUSA • CREALITY • ANY SLICER".
- 02_preview_all.jpg: Exact replica of 03_preview_1.jpg: warm cream canvas, Anton + Pacifico header,
  4x2 grid of white rounded cards with drop shadows, each containing an animal cup with grounded contact shadows.
- 03_preview_singles_1.jpg: 2x2 grid of large cards for Cat, Bear, Bunny, Panda with ComfyUI lifestyle photos & full specs.
- 04_preview_singles_2.jpg: 2x2 grid of large cards for Pig, Owl, Chick, Dino with ComfyUI lifestyle photos & full specs.
- 05_lifestyle_trio.jpg: Cozy lifestyle desk showcase (Cat with scissors, Panda, Dino in craft room) + feature cards.
- 06_feature_vanity.jpg: Multi-purpose desk & vanity organizer (Cat pencils & Owl makeup brushes).
- 07_feature_quality.jpg: 100% support-free upright printing, 3.2mm walls, smooth rim, multi-color 3MF.
- 08_specs_dimensions.jpg: Dimensions diagram, slicer settings table, material compatibility & pro tips.
- 09_formats.jpg: What's in your download (info_card layout).
- 10_commercial_license.jpg: Commercial license terms (info_card layout).
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import media as M

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\cute_animal_pencil_cups_stl_3mf_glb")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"
FONT_DIR = Path(r"F:\WORKHORSE\etsy_factory\fonts")

SIZE = 2400
BG_COLOR = (250, 245, 238)      # #FAF5EE warm cream
INK = (42, 30, 23)              # #2A1E17 dark espresso brown
ACCENT = (204, 88, 36)          # #CC5824 warm terracotta
GOLD = (255, 214, 0)            # #FFD600 starburst yellow
WHITE = (255, 255, 255)
CARD_BG = (255, 255, 255)
LIGHT_TINT = (246, 242, 236)    # subtle beige card section fill

CHIP_COLS = [
    ("STL", (200, 90, 46)),       # Terracotta
    ("3MF", (46, 125, 114)),      # Slate Teal
    ("GLB", (217, 148, 38)),      # Honey Gold
    ("NO SUP", (123, 82, 148)),   # Royal Violet
    ("TESTED", (46, 125, 50))     # Forest Green
]

ANIMALS = [
    {"name": "Cat", "tag": "TERRACOTTA CAT", "color": "Warm Terracotta", "sub": "No Supports • Weighted Base", "single": "single_cat.png", "photo": "comfy_flux_FLUX_KLEIN_CUTE_CAT_00001_.png"},
    {"name": "Bear", "tag": "HONEY BEAR", "color": "Honey Caramel", "sub": "No Supports • Weighted Base", "single": "single_bear.png", "photo": "COMFY_SINGLE_BEAR.png"},
    {"name": "Bunny", "tag": "ROSE BUNNY", "color": "Rose Pink", "sub": "No Supports • Tall Ears", "single": "single_bunny.png", "photo": "COMFY_SINGLE_BUNNY.png"},
    {"name": "Panda", "tag": "IVORY PANDA", "color": "Silk Ivory", "sub": "No Supports • Slate Eye Patches", "single": "single_panda.png", "photo": "COMFY_SINGLE_PANDA.png"},
    {"name": "Pig", "tag": "BLOSSOM PIG", "color": "Blossom Pink", "sub": "No Supports • Cute Snout", "single": "single_pig.png", "photo": "COMFY_SINGLE_PIG.png"},
    {"name": "Owl", "tag": "DENIM OWL", "color": "Denim Blue", "sub": "No Supports • Eye Rings", "single": "single_owl.png", "photo": "COMFY_OWL_VANITY.png"},
    {"name": "Chick", "tag": "GOLDEN CHICK", "color": "Dandelion Yellow", "sub": "No Supports • Cute Crest", "single": "single_chick.png", "photo": "COMFY_SINGLE_CHICK.png"},
    {"name": "Dino", "tag": "FOREST DINO", "color": "Forest Mint", "sub": "No Supports • Dorsal Spines", "single": "single_dino.png", "photo": "COMFY_SINGLE_DINO.png"},
]

def make_contact_shadow(width: int, height: int, blur: int = 24, alpha: int = 140) -> Image.Image:
    s = Image.new("RGBA", (width + blur * 4, height + blur * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse((blur * 2, blur * 2, blur * 2 + width, blur * 2 + height), fill=(35, 24, 18, alpha))
    return s.filter(ImageFilter.GaussianBlur(blur))

def load_render_cropped(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im

def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, y_top: int = 70):
    ft = M.fit(d, title.upper(), M.anton, SIZE - 240, 150, 70)
    d.text((SIZE // 2, y_top), title.upper(), font=ft, fill=INK, anchor="ma")
    fs = M.fit(d, subtitle, M.pacifico, SIZE - 360, 74, 38)
    d.text((SIZE // 2, y_top + ft.size + 16), subtitle, font=fs, fill=ACCENT, anchor="ma")
    return y_top + ft.size + fs.size + 60

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
# CARD 01: HERO COVER (Exact 02_cover_grid.jpg architecture + Hero Product Pop)
# -----------------------------------------------------------------------------
def draw_check(d: ImageDraw.ImageDraw, x: int, y: int, size: int = 24, color: Tuple[int, int, int] = ACCENT, width: int = 4):
    pts = [
        (x, y + int(size * 0.48)),
        (x + int(size * 0.36), y + int(size * 0.84)),
        (x + int(size * 0.92), y + int(size * 0.12))
    ]
    d.line(pts, fill=color, width=width, joint="curve")

def make_card_01() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    
    # Subtle tiled background of the cups
    row_h = 320
    y = -30
    k = 0
    while y < SIZE:
        x = -40
        while x < SIZE:
            an = ANIMALS[k % len(ANIMALS)]
            k += 1
            t_path = RENDERS_DIR / an["single"]
            if t_path.exists():
                t = load_render_cropped(t_path)
                s = row_h / t.height
                tw = int(t.width * s)
                tt = t.resize((max(20, tw), row_h), Image.LANCZOS)
                faint = tt.copy()
                faint.putalpha(faint.getchannel("A").point(lambda a: int(a * 0.25)))
                base.alpha_composite(faint, (x, y))
                x += tw + 45
            else:
                x += 300
        y += row_h + 30

    # Soft warm white haze in center
    haze = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    hd = ImageDraw.Draw(haze)
    hd.ellipse((140, 260, SIZE - 140, SIZE - 260), fill=(255, 255, 255, 185))
    base.alpha_composite(haze.filter(ImageFilter.GaussianBlur(130)))

    # Central white rounded card container
    cw, ch = 1860, 1680
    cx, cy = (SIZE - cw) // 2, (SIZE - ch) // 2 - 20
    card = M.rounded((cw, ch), 85, (255, 255, 255, 255), outline=INK + (255,), width=12)
    M.shadowed(base, card, (cx, cy), blur=38, off=(0, 24), alpha=140)

    d = ImageDraw.Draw(base)

    # Top ribbon pill: "COMMERCIAL USE INCLUDED"
    rb = "COMMERCIAL USE INCLUDED"
    f_rb = M.fit(d, rb, M.poppins_x, 1250, 56)
    tw = M.text_w(d, rb, f_rb)
    pill = M.rounded((tw + 110, 100), 50, ACCENT + (255,))
    base.alpha_composite(pill, (SIZE // 2 - (tw + 110) // 2, cy - 50))
    d.text((SIZE // 2, cy), rb, font=f_rb, fill=WHITE, anchor="mm")

    # Big Number "8" in warm gradient fill with dark stroke
    big = "8"
    fb = M.anton(290)
    bbn = d.textbbox((0, 0), big, font=fb, anchor="ma")
    ntop = cy + 70
    M.grad_fill_text(base, (SIZE // 2, ntop - bbn[1]), big, fb, (245, 165, 65), ACCENT, INK, 12)

    # Primary Title Line: "CUTE ANIMAL PENCIL CUPS"
    ty = ntop + (bbn[3] - bbn[1]) + 20
    t_text = "CUTE ANIMAL PENCIL CUPS"
    fl = M.fit(d, t_text, M.anton, cw - 180, 130, 80)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "Cat  *  Bear  *  Bunny  *  Panda  *  Pig  *  Owl  *  Chick  *  Dino"
    fs = M.fit(d, sub, M.pacifico, cw - 260, 68, 38)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    d.text((SIZE // 2, ty + (bb[3] - bb[1]) + 14 - bbs[1]), sub, font=fs, fill=ACCENT, anchor="ma")

    # Hero Product Showcase in center of white card:
    # Rich photorealistic lifestyle preview showing Cat, Panda, Dino on warm desk
    hero_y = ty + (bb[3] - bb[1]) + (bbs[3] - bbs[1]) + 40
    hero_w = cw - 140
    hero_h = 750
    hero_x = cx + 70

    p_trio = RENDERS_DIR / "COMFY_TRIO_LIFESTYLE.png"
    if p_trio.exists():
        im_hero = Image.open(p_trio).convert("RGBA")
        # Crop to keep pencils, cups, and desk surface perfectly framed
        im_crop = im_hero.crop((0, 200, 1024, 880))
        im_fit = ImageOps_fit(im_crop, (hero_w, hero_h))
        card_mask = M.rounded((hero_w, hero_h), 34, (255, 255, 255, 255))
        base.paste(im_fit, (hero_x, hero_y), card_mask)
        # Crisp outline around photo
        ImageDraw.Draw(base).rounded_rectangle([hero_x, hero_y, hero_x + hero_w, hero_y + hero_h], radius=34, outline=INK, width=5)

    # Format Chips across bottom of white card
    n_chips = len(CHIP_COLS)
    r = 90
    gap = 40
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 130
    for j, (label, col) in enumerate(CHIP_COLS):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=7)
        fc = M.fit(d, label, M.anton, 2 * r - 30, 68, 24)
        d.text((xx, cyy + 3), label, font=fc, fill=WHITE, anchor="mm")

    # Bottom machine strip on beige canvas
    strip = "BAMBU LAB  *  PRUSA  *  CREALITY  *  ANY SLICER"
    fs2 = M.fit(d, strip, M.poppins_x, SIZE - 260, 56, 28)
    sw = M.text_w(d, strip, fs2)
    sp = M.rounded((sw + 100, 100), 50, INK + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 100) // 2, SIZE - 160))
    d.text((SIZE // 2, SIZE - 110), strip, font=fs2, fill=WHITE, anchor="mm")

    # 40-Point Yellow Starburst Badge ("INSTANT DOWNLOAD")
    bx, by, br = SIZE - 250, 255, 215
    pts = []
    for q in range(40):
        a = math.pi * 2 * q / 40
        rr = br if q % 2 == 0 else br * 0.82
        pts.append((bx + rr * math.cos(a), by + rr * math.sin(a)))
    star = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(star).polygon(pts, fill=GOLD + (255,), outline=INK + (255,), width=8)
    ImageDraw.Draw(star).polygon([(bx + (p[0] - bx) * 0.85, by + (p[1] - by) * 0.85) for p in pts], outline=INK + (255,), width=4)
    base.alpha_composite(star)

    burst_lines = ["INSTANT", "DOWNLOAD"]
    fz = M.anton(72)
    for li, l in enumerate(burst_lines):
        ImageDraw.Draw(base).text((bx, by + (li - 0.5) * 78), l, font=fz, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 02: FULL 8-PACK OVERVIEW (Clean Cards + Grounded Shadows)
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "8 ADORABLE ANIMAL COMPANIONS", "3D printable desk organizers - a peek inside", 70)

    cols, rows = 4, 2
    pad_x = 70
    gap_x, gap_y = 40, 48
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 90 - (rows - 1) * gap_y) // rows

    for idx, an in enumerate(ANIMALS):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        # White rounded card container
        card = M.rounded((gw, gh), 40, (255, 255, 255, 255), outline=INK + (60,), width=3)
        M.shadowed(base, card, (x, y), blur=16, off=(0, 10), alpha=80)

        # Render cropped cup
        t_path = RENDERS_DIR / an["single"]
        if t_path.exists():
            t = load_render_cropped(t_path)
            avail_h = gh - 190
            s = min((gw - 70) / t.width, avail_h / t.height)
            tw, th = int(t.width * s), int(t.height * s)
            tt = t.resize((tw, th), Image.LANCZOS)
            
            cup_x = x + (gw - tw) // 2
            cup_y = y + 25 + (avail_h - th) // 2
            cup_bottom = cup_y + th
            
            # Ground contact shadow positioned precisely at the base
            sh = make_contact_shadow(int(tw * 0.75), 32, blur=16, alpha=130)
            sh_x = x + (gw - sh.width) // 2
            sh_y = cup_bottom - sh.height // 2 - 4
            base.alpha_composite(sh, (sh_x, sh_y))
            base.alpha_composite(tt, (cup_x, cup_y))

        # Animal label and feature badge
        d_card = ImageDraw.Draw(base)
        fn_tag = M.fit(d_card, an["tag"], M.anton, gw - 40, 48, 26)
        d_card.text((x + gw // 2, y + gh - 95), an["tag"], font=fn_tag, fill=INK, anchor="mm")

        fn_sub = M.fit(d_card, an["sub"], M.poppins_x, gw - 50, 30, 20)
        d_card.text((x + gw // 2, y + gh - 46), an["sub"], font=fn_sub, fill=ACCENT, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 03: CLOSE-UP SINGLES PART 1 (Cat, Bear, Bunny, Panda)
# -----------------------------------------------------------------------------
def make_card_03() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "DESK BUDDIES: CAT * BEAR * BUNNY * PANDA", "Sculpted kawaii details with sturdy anti-tip weighted base", 70)

    group = [
        {
            "an": ANIMALS[0],
            "bullets": [
                "Rich Terracotta Rust PLA texture",
                "Holds 15+ standard pens & pencils",
                "Wide pocket fits craft scissors & tools",
                "Weighted base prevents tipping"
            ]
        },
        {
            "an": ANIMALS[1],
            "bullets": [
                "Honey Caramel PLA filament color",
                "Sculpted round bear ears & snout",
                "Deep 40mm cylindrical pen cavity",
                "Zero support material required"
            ]
        },
        {
            "an": ANIMALS[2],
            "bullets": [
                "Rose Coral Pink PLA aesthetic",
                "Tall upright bunny ears geometry",
                "Embossed buck-teeth smile detail",
                "Smooth chamfered entry comfort rim"
            ]
        },
        {
            "an": ANIMALS[3],
            "bullets": [
                "Silk Ivory body + Slate Black ears",
                "Pre-painted Bambu AMS multi-color",
                "Smooth interior wipes clean easily",
                "Tested upright 100mm height"
            ]
        }
    ]

    cols, rows = 2, 2
    pad_x = 90
    gap_x, gap_y = 50, 50
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 80 - (rows - 1) * gap_y) // rows

    for idx, item in enumerate(group):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        # White card container
        card = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Photo on Left side: width 480, height gh - 60
        p_path = RENDERS_DIR / item["an"]["photo"]
        iw = 480
        ih = gh - 60
        if p_path.exists():
            im = Image.open(p_path).convert("RGBA")
            im_fit = ImageOps_fit(im, (iw, ih))
            card_img = M.rounded((iw, ih), 30, (255, 255, 255, 255))
            base.paste(im_fit, (x + 30, y + 30), card_img)
            ImageDraw.Draw(base).rounded_rectangle([x + 30, y + 30, x + 30 + iw, y + 30 + ih], radius=30, outline=INK, width=3)

        # Text on Right side: tx = x + 540, width available = gw - 570 (~515px)
        tx = x + 540
        avail_tw = gw - 570
        d_card = ImageDraw.Draw(base)

        # Tag Title
        fn_title = M.fit(d_card, item["an"]["tag"], M.anton, avail_tw, 56, 32)
        d_card.text((tx, y + 42), item["an"]["tag"], font=fn_title, fill=INK, anchor="la")

        # Color & Specs Subtitle
        fn_sub = M.fit(d_card, f"{item['an']['color']} • 0 Supports", M.poppins_x, avail_tw, 30, 18)
        d_card.text((tx, y + 106), f"{item['an']['color']} • 0 Supports", font=fn_sub, fill=ACCENT, anchor="la")

        # Thin accent rule
        d_card.line([(tx, y + 155), (tx + avail_tw - 10, y + 155)], fill=ACCENT + (140,), width=3)

        # 4 Bullet points
        f_bullet = M.poppins(32)
        by = y + 185
        for b_text in item["bullets"]:
            # Small circle bullet
            d_card.ellipse((tx, by + 10, tx + 12, by + 22), fill=ACCENT)
            wrapped = M._wrap(d_card, b_text, f_bullet, avail_tw - 28)
            for w_ln in wrapped:
                d_card.text((tx + 26, by), w_ln, font=f_bullet, fill=INK, anchor="la")
                by += 44
            by += 12

        # Bottom spec chip
        chip_y = y + gh - 90
        chip_w = avail_tw - 20
        chip_bg = M.rounded((chip_w, 60), 30, LIGHT_TINT + (255,), outline=INK + (70,), width=2)
        base.paste(chip_bg, (tx, chip_y), chip_bg)
        f_chip = M.fit(d_card, "100mm H • 3.2mm Walls • Any Slicer", M.poppins_x, chip_w - 30, 24, 16)
        d_card.text((tx + chip_w // 2, chip_y + 30), "100mm H • 3.2mm Walls • Any Slicer", font=f_chip, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 04: CLOSE-UP SINGLES PART 2 (Pig, Owl, Chick, Dino)
# -----------------------------------------------------------------------------
def make_card_04() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "DESK BUDDIES: PIG * OWL * CHICK * DINO", "Tested and optimized for zero-support 3D printing", 70)

    group = [
        {
            "an": ANIMALS[4],
            "bullets": [
                "Blossom Pink PLA filament shade",
                "Embossed pig snout & folded ears",
                "Thick 3.2mm drop-tested walls",
                "Smooth interior wipes clean in seconds"
            ]
        },
        {
            "an": ANIMALS[5],
            "bullets": [
                "Denim Blue PLA with ivory accents",
                "Sculpted feather scales & eye rings",
                "Holds colored pens or makeup brushes",
                "Multi-purpose desk & vanity organizer"
            ]
        },
        {
            "an": ANIMALS[6],
            "bullets": [
                "Sunny Dandelion Yellow PLA color",
                "Cute head tuft crest & beak detail",
                "Flat anti-wobble build plate base",
                "Sturdy balance with 15+ pens inside"
            ]
        },
        {
            "an": ANIMALS[7],
            "bullets": [
                "Forest Mint Green PLA finish",
                "Embossed dorsal plates & cheerful grin",
                "Generous opening for scissors & stylus",
                "100% support-free print geometry"
            ]
        }
    ]

    cols, rows = 2, 2
    pad_x = 90
    gap_x, gap_y = 50, 50
    gw = (SIZE - pad_x * 2 - (cols - 1) * gap_x) // cols
    gh = (SIZE - top - 80 - (rows - 1) * gap_y) // rows

    for idx, item in enumerate(group):
        r, c = divmod(idx, cols)
        x = pad_x + c * (gw + gap_x)
        y = top + r * (gh + gap_y)

        card = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Photo on Left side: width 480, height gh - 60
        p_path = RENDERS_DIR / item["an"]["photo"]
        iw = 480
        ih = gh - 60
        if p_path.exists():
            im = Image.open(p_path).convert("RGBA")
            im_fit = ImageOps_fit(im, (iw, ih))
            card_img = M.rounded((iw, ih), 30, (255, 255, 255, 255))
            base.paste(im_fit, (x + 30, y + 30), card_img)
            ImageDraw.Draw(base).rounded_rectangle([x + 30, y + 30, x + 30 + iw, y + 30 + ih], radius=30, outline=INK, width=3)

        # Text on Right side
        tx = x + 540
        avail_tw = gw - 570
        d_card = ImageDraw.Draw(base)

        fn_title = M.fit(d_card, item["an"]["tag"], M.anton, avail_tw, 56, 32)
        d_card.text((tx, y + 42), item["an"]["tag"], font=fn_title, fill=INK, anchor="la")

        fn_sub = M.fit(d_card, f"{item['an']['color']} • 0 Supports", M.poppins_x, avail_tw, 30, 18)
        d_card.text((tx, y + 106), f"{item['an']['color']} • 0 Supports", font=fn_sub, fill=ACCENT, anchor="la")

        d_card.line([(tx, y + 155), (tx + avail_tw - 10, y + 155)], fill=ACCENT + (140,), width=3)

        f_bullet = M.poppins(32)
        by = y + 185
        for b_text in item["bullets"]:
            d_card.ellipse((tx, by + 10, tx + 12, by + 22), fill=ACCENT)
            wrapped = M._wrap(d_card, b_text, f_bullet, avail_tw - 28)
            for w_ln in wrapped:
                d_card.text((tx + 26, by), w_ln, font=f_bullet, fill=INK, anchor="la")
                by += 44
            by += 12

        chip_y = y + gh - 90
        chip_w = avail_tw - 20
        chip_bg = M.rounded((chip_w, 60), 30, LIGHT_TINT + (255,), outline=INK + (70,), width=2)
        base.paste(chip_bg, (tx, chip_y), chip_bg)
        f_chip = M.fit(d_card, "100mm H • 3.2mm Walls • Any Slicer", M.poppins_x, chip_w - 30, 24, 16)
        d_card.text((tx + chip_w // 2, chip_y + 30), "100mm H • 3.2mm Walls • Any Slicer", font=f_chip, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 05: LIFESTYLE TRIO (Cat, Panda, Dino Setup + Feature Bar)
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "COZY LIFESTYLE DESK COMPANIONS", "Organize colored pencils, fine-liners, scissors & tools", 70)

    # Big hero lifestyle image container in center
    iw, ih = SIZE - 180, 1420
    p_path = RENDERS_DIR / "COMFY_TRIO_LIFESTYLE.png"
    if p_path.exists():
        im = Image.open(p_path).convert("RGBA")
        im_fit = ImageOps_fit(im, (iw, ih))
        card_hero = M.rounded((iw, ih), 44, (255, 255, 255, 255), outline=INK + (255,), width=6)
        M.shadowed(base, card_hero, ((SIZE - iw)//2, top + 15), blur=26, off=(0, 16), alpha=110)
        base.paste(im_fit, ((SIZE - iw)//2, top + 15), card_hero)
        ImageDraw.Draw(base).rounded_rectangle([(SIZE - iw)//2, top + 15, (SIZE + iw)//2, top + 15 + ih], radius=44, outline=INK, width=6)

    # Row 1 of pills directly under hero photo
    pills = ["WEIGHTED ANTI-TIP BASE", "FITS PENS & SCISSORS", "SMOOTH INTERIOR", "PRINT AT HOME"]
    total_w = SIZE - 180
    n = len(pills)
    gap = 24
    pw = (total_w - (n - 1) * gap) // n
    py = top + 15 + ih + 40
    f_p = M.poppins_x(34)

    for i, p_text in enumerate(pills):
        px = 90 + i * (pw + gap)
        pill_img = M.rounded((pw, 94), 47, (255, 255, 255, 255), outline=INK + (255,), width=4)
        M.shadowed(base, pill_img, (px, py), blur=12, off=(0, 6), alpha=70)
        d.text((px + pw // 2, py + 47), p_text, font=f_p, fill=INK, anchor="mm")

    # Bottom Highlight Card: Eliminates dead whitespace with key selling points
    by2 = py + 94 + 35
    bh2 = SIZE - by2 - 60
    card_bot = M.rounded((total_w, bh2), 36, (255, 255, 255, 255), outline=INK + (120,), width=3)
    M.shadowed(base, card_bot, (90, by2), blur=16, off=(0, 8), alpha=70)

    # Content inside bottom card
    d.text((140, by2 + bh2 // 2 - 28), "100% ORIGINAL HAND-SCULPTED DESIGNS", font=M.anton(46), fill=ACCENT, anchor="la")
    d.text((140, by2 + bh2 // 2 + 26), "Engineered specifically for FDM 3D printers with clean bridges and zero support waste.", font=M.poppins(32), fill=INK, anchor="la")

    # 3 mini badges on right
    badges = ["NO SUPPORTS", "MULTI-COLOR 3MF", "COMMERCIAL USE"]
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
# CARD 06: MULTI-PURPOSE / VANITY FEATURE (Owl Brushes & Cat Pens)
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "VERSATILE DESK & VANITY STORAGE", "Perfect for artist pencils, office supplies, or cosmetic brushes", 70)

    cols = 2
    pad_x = 90
    gw = (SIZE - pad_x * 2 - 50) // cols
    gh = SIZE - top - 110

    panels = [
        {
            "title": "DESK & ART STUDIO",
            "sub": "Colored Pencils, Pens & Craft Scissors",
            "photo": "comfy_flux_FLUX_KLEIN_CUTE_CAT_00001_.png",
            "bullets": [
                "Fits 15+ standard pencils, Sharpies & fine-liners",
                "Wide 40mm opening accommodates craft scissors",
                "Solid weighted base prevents accidental tipping",
                "Keeps creative workstations cheerful and clutter-free"
            ],
            "box_title": "IDEAL WORKSTATION COMPANION",
            "box_desc": "Great for artists, students, architects, and bullet journalers."
        },
        {
            "title": "VANITY & MAKEUP TABLE",
            "sub": "Fluffy Brushes, Eyeliner & Tweezers",
            "photo": "COMFY_OWL_VANITY.png",
            "bullets": [
                "Deep 40mm cylindrical pocket holds brushes upright",
                "Smooth beveled rim protects soft cosmetic bristles",
                "Moisture-resistant PLA plastic wipes clean effortlessly",
                "Charming aesthetic addition for bedrooms and vanities"
            ],
            "box_title": "IDEAL COSMETIC ORGANIZER",
            "box_desc": "Perfect for foundation brushes, mascara wands, eyeliner & grooming tools."
        }
    ]

    for idx, p in enumerate(panels):
        x = pad_x + idx * (gw + 50)
        y = top + 15

        card = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
        M.shadowed(base, card, (x, y), blur=18, off=(0, 10), alpha=80)

        # Image top half
        p_path = RENDERS_DIR / p["photo"]
        iw = gw - 60
        ih = int(gh * 0.52)
        if p_path.exists():
            im = Image.open(p_path).convert("RGBA")
            im_fit = ImageOps_fit(im, (iw, ih))
            card_img = M.rounded((iw, ih), 32, (255, 255, 255, 255))
            base.paste(im_fit, (x + 30, y + 30), card_img)
            ImageDraw.Draw(base).rounded_rectangle([x + 30, y + 30, x + 30 + iw, y + 30 + ih], radius=32, outline=INK, width=2)

        # Content bottom half
        ty = y + ih + 55
        d_card = ImageDraw.Draw(base)
        ft = M.fit(d_card, p["title"], M.anton, gw - 60, 56, 32)
        d_card.text((x + gw // 2, ty), p["title"], font=ft, fill=INK, anchor="ma")

        fs = M.fit(d_card, p["sub"], M.poppins_x, gw - 80, 30, 20)
        d_card.text((x + gw // 2, ty + 62), p["sub"], font=fs, fill=ACCENT, anchor="ma")

        # Divider
        d_card.line([(x + 50, ty + 112), (x + gw - 50, ty + 112)], fill=ACCENT + (140,), width=2)

        # Bullets
        fb = M.poppins(34)
        by = ty + 135
        for b_text in p["bullets"]:
            d_card.ellipse((x + 50, by + 10, x + 62, by + 22), fill=ACCENT)
            d_card.text((x + 78, by), b_text, font=fb, fill=INK, anchor="la")
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
# CARD 07: PRINT QUALITY & ZERO SUPPORTS (Complete Cards with Benefit Checkpoints)
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "ENGINEERED FOR 3D PRINTING", "Clean CAD geometry, zero support waste, and drop-tested durability", 70)

    features = [
        {
            "num": "01",
            "title": "100% SUPPORT-FREE",
            "kicker": "Zero wasted filament & zero post-processing",
            "desc": "Prints standing upright directly on your build plate. Overhang angles are calibrated under 45 degrees so you never waste filament or deal with ugly support scarring.",
            "checks": ["0g support filament waste", "No support marks to scrape or sand", "Flat, warp-resistant bed contact"]
        },
        {
            "num": "02",
            "title": "3.2MM REINFORCED WALLS",
            "kicker": "Substantial durability & drop resistance",
            "desc": "Thick, robust perimeter walls ensure rugged structure. Sturdy against accidental desk knocks and drops; prints with a satisfying, premium heavy feel in hand.",
            "checks": ["3 perimeter loops (1.2mm shell)", "Optimized for 15-20% gyroid infill", "Drop-tested anti-tip stability"]
        },
        {
            "num": "03",
            "title": "BEVELED COMFORT RIM",
            "kicker": "Smooth pencil insertion & retrieval",
            "desc": "The top lip features a generous 2mm chamfered comfort profile. Pencils, scissors, stylus pens, and delicate makeup brushes slide in and out effortlessly without catching.",
            "checks": ["Smooth chamfered entry lip", "Protects soft cosmetic bristles", "Prevents pencil tip breakage"]
        },
        {
            "num": "04",
            "title": "PRE-COLORED 3MF PLATES",
            "kicker": "1-click multi-color printing",
            "desc": "Includes ready-to-print 3MF plates for Bambu Studio and PrusaSlicer with multi-color painted eye patches, snouts, ears, and accents. Single-color STLs also included.",
            "checks": ["Bambu Lab AMS 1-click ready", "Prusa MMU color assignments", "Individual STL meshes for single-color"]
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

        card = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
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
            pill = M.rounded((c_box_w - 40, row_h), 20, (255, 255, 255, 255), outline=INK + (35,), width=2)
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
            d_card.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=LIGHT_TINT + (255,), outline=ACCENT + (160,), width=2)
            draw_check(d_card, badge_cx - 13, badge_cy - 13, size=26, color=ACCENT, width=4)
            d_card.text((x + 165, badge_cy), chk, font=fc, fill=INK, anchor="lm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 08: TECHNICAL SPECS & SLICER GUIDE (Full Content + Pro Tips)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)

    top = draw_header(d, "TECHNICAL SPECS & SLICER GUIDE", "Optimized print settings for Bambu Lab, Prusa, Creality & Any Slicer", 70)

    pad_x = 90
    gw = (SIZE - pad_x * 2 - 50) // 2
    gh = SIZE - top - 110

    # Left Card: Dimensions & Capacity
    x_l = pad_x
    card_l = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
    M.shadowed(base, card_l, (x_l, top + 15), blur=18, off=(0, 10), alpha=80)

    # Right Card: Slicer Recommendations
    x_r = pad_x + gw + 50
    card_r = M.rounded((gw, gh), 44, (255, 255, 255, 255), outline=INK + (70,), width=3)
    M.shadowed(base, card_r, (x_r, top + 15), blur=18, off=(0, 10), alpha=80)

    # Bottom Boxes Geometry (Symmetrical on Left & Right)
    box_y = top + 1030
    box_w = gw - 100
    box_h = gh - (box_y - top - 15) - 45

    # Paste Left Box Background
    mat_bg = M.rounded((box_w, box_h), 32, LIGHT_TINT + (255,), outline=ACCENT + (140,), width=3)
    base.paste(mat_bg, (x_l + 50, box_y), mat_bg)

    # Paste Right Box Background
    tip_bg = M.rounded((box_w, box_h), 32, LIGHT_TINT + (255,), outline=ACCENT + (140,), width=3)
    base.paste(tip_bg, (x_r + 50, box_y), tip_bg)

    # Paste Left & Right Pills for Bottom Guides
    pill_h = 115
    pill_gap = 24
    for i in range(5):
        ry = box_y + 145 + i * (pill_h + pill_gap)
        m_pill = M.rounded((box_w - 40, pill_h), 20, (255, 255, 255, 255), outline=INK + (35,), width=2)
        base.paste(m_pill, (x_l + 70, ry), m_pill)
        base.paste(m_pill, (x_r + 70, ry), m_pill)

    # ------------------ LEFT CARD DRAWING ------------------
    d_l = ImageDraw.Draw(base)
    d_l.text((x_l + gw // 2, top + 75), "PHYSICAL DIMENSIONS", font=M.anton(56), fill=INK, anchor="ma")
    d_l.text((x_l + gw // 2, top + 140), "Universal desk organizer scale for all 8 animals", font=M.poppins_x(28), fill=ACCENT, anchor="ma")
    d_l.line([(x_l + 50, top + 195), (x_l + gw - 50, top + 195)], fill=ACCENT + (140,), width=3)

    specs = [
        ("Height", "100 mm  (3.94 in)"),
        ("Width", "85 - 95 mm  (3.35 - 3.74 in)"),
        ("Depth", "52 mm  (2.05 in)"),
        ("Pocket Opening", "40 mm x 38 mm  (1.57 x 1.50 in)"),
        ("Wall Thickness", "3.2 mm reinforced solid shell"),
        ("Desk Capacity", "15 - 20 Pens, Pencils, Scissors"),
        ("Filament Usage", "~125 - 140g PLA per animal cup"),
        ("Print Time", "~3.5 hrs (at 0.20mm standard speed)")
    ]

    sy = top + 230
    f_sh = M.anton(38)
    f_sb = M.poppins(34)
    for idx, (k, v) in enumerate(specs):
        d_l.text((x_l + 50, sy), k, font=f_sh, fill=ACCENT, anchor="la")
        d_l.text((x_l + gw - 50, sy), v, font=f_sb, fill=INK, anchor="ra")
        if idx < len(specs) - 1:
            d_l.line([(x_l + 50, sy + 70), (x_l + gw - 50, sy + 70)], fill=INK + (30,), width=1)
        sy += 95

    # Left Bottom Box Content
    d_l.text((x_l + gw // 2, box_y + 45), "FILAMENT & SCALING FLEXIBILITY", font=M.anton(40), fill=ACCENT, anchor="mm")
    d_l.text((x_l + gw // 2, box_y + 90), "Tested across standard materials & scale ranges", font=M.poppins_x(26), fill=INK + (200,), anchor="mm")
    d_l.line([(x_l + 80, box_y + 125), (x_l + gw - 80, box_y + 125)], fill=ACCENT + (100,), width=2)

    mat_items = [
        ("Matte PLA (Recommended)", "Velvety ceramic appearance with virtually invisible layer lines"),
        ("Standard PLA, PETG & ABS", "Fully compatible; PETG adds extra impact strength and water resistance"),
        ("Mini Desk Token Scale (75%)", "Scales down cleanly for paperclips, pushpins, and micro accessories"),
        ("Giant Caddy Scale (130%)", "Scales up smoothly to hold thick art markers, paintbrushes, and tools"),
        ("Resin / SLA 3D Printing", "Watertight manifold meshes print cleanly on monochrome MSLA printers")
    ]

    for i, (m_title, m_desc) in enumerate(mat_items):
        ry = box_y + 145 + i * (pill_h + pill_gap)
        badge_cx = x_l + 120
        badge_cy = ry + pill_h // 2
        badge_r = 24
        d_l.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=LIGHT_TINT + (255,), outline=ACCENT + (160,), width=2)
        draw_check(d_l, badge_cx - 13, badge_cy - 13, size=26, color=ACCENT, width=4)
        d_l.text((x_l + 165, ry + 24), m_title, font=M.anton(30), fill=ACCENT, anchor="la")
        f_desc = M.fit(d_l, m_desc, M.poppins, box_w - 180, 21, 16)
        d_l.text((x_l + 165, ry + 68), m_desc, font=f_desc, fill=INK, anchor="la")

    # ------------------ RIGHT CARD DRAWING ------------------
    d_r = ImageDraw.Draw(base)
    d_r.text((x_r + gw // 2, top + 75), "RECOMMENDED SLICER SETTINGS", font=M.anton(56), fill=INK, anchor="ma")
    d_r.text((x_r + gw // 2, top + 140), "Works out of the box with zero supports", font=M.poppins_x(28), fill=ACCENT, anchor="ma")
    d_r.line([(x_r + 50, top + 195), (x_r + gw - 50, top + 195)], fill=ACCENT + (140,), width=3)

    settings = [
        ("Print Orientation", "Upright on build plate (flat base down)"),
        ("Layer Height", "0.20 mm standard (0.12 - 0.16 mm for ultra-fine)"),
        ("Perimeters / Walls", "3 wall loops (1.2 mm solid shell for durability)"),
        ("Infill Density", "15% - 20% (Gyroid or Grid recommended)"),
        ("Top / Bottom Layers", "4 top solid layers, 3 bottom solid layers"),
        ("Support Material", "NONE (0% supports needed - prints 100% clean)"),
        ("Build Plate Adhesion", "Skirt only (Textured PEI bed, no brim needed)"),
        ("Tested Slicers", "Bambu Studio, PrusaSlicer, Orca, Cura, Creality")
    ]

    sy = top + 230
    for idx, (k, v) in enumerate(settings):
        d_r.text((x_r + 50, sy), k, font=M.anton(34), fill=ACCENT, anchor="la")
        d_r.text((x_r + 50, sy + 38), v, font=M.poppins(28), fill=INK, anchor="la")
        if idx < len(settings) - 1:
            d_r.line([(x_r + 50, sy + 76), (x_r + gw - 50, sy + 76)], fill=INK + (30,), width=1)
        sy += 95

    # Right Bottom Box Content
    d_r.text((x_r + gw // 2, box_y + 45), "PRO 3D PRINTING & FINISHING TIPS", font=M.anton(40), fill=ACCENT, anchor="mm")
    d_r.text((x_r + gw // 2, box_y + 90), "Field-tested recommendations for flawless first prints", font=M.poppins_x(26), fill=INK + (200,), anchor="mm")
    d_r.line([(x_r + 80, box_y + 125), (x_r + gw - 80, box_y + 125)], fill=ACCENT + (100,), width=2)

    tip_items = [
        ("Bed Temperature & Adhesion", "55°C - 60°C on textured PEI. Wipe with IPA for solid first-layer grip"),
        ("Print Speed & Perimeters", "150-250 mm/s on CoreXY printers; keep outer perimeters under 60 mm/s"),
        ("Part Fan Cooling (100%)", "Run 100% cooling fan after layer 3 for crisp embossed facial details"),
        ("Seam Alignment Placement", "Set seam position to 'Rear' or 'Aligned' to keep front faces seamless"),
        ("Bambu AMS Pre-Painted 3MF", "Open included 3MF plates to automatically print multi-color eye & ear layers")
    ]

    for i, (t_title, t_desc) in enumerate(tip_items):
        ry = box_y + 145 + i * (pill_h + pill_gap)
        badge_cx = x_r + 120
        badge_cy = ry + pill_h // 2
        badge_r = 24
        d_r.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=LIGHT_TINT + (255,), outline=ACCENT + (160,), width=2)
        draw_check(d_r, badge_cx - 13, badge_cy - 13, size=26, color=ACCENT, width=4)
        d_r.text((x_r + 165, ry + 24), t_title, font=M.anton(30), fill=ACCENT, anchor="la")
        f_tdesc = M.fit(d_r, t_desc, M.poppins, box_w - 180, 21, 16)
        d_r.text((x_r + 165, ry + 68), t_desc, font=f_tdesc, fill=INK, anchor="la")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 09: WHAT'S IN YOUR DOWNLOAD (Exact M.info_card layout)
# -----------------------------------------------------------------------------
def make_card_09() -> Image.Image:
    out_tmp = RENDERS_DIR / "temp_09.jpg"
    rows = [
        ("8 STL Meshes", "Watertight, manifold-free 3D printable files for all 8 animal cups. Ready for any slicer."),
        ("8 3MF Plates", "Pre-oriented project plates for Bambu Studio and PrusaSlicer with multi-color painted layers."),
        ("8 GLB Models", "Full-color 3D preview assets for web display, digital catalogs, Blender, or AR viewing."),
        ("PDF Print Guide", "Step-by-step printing handbook: temperature tips, infill choices, and finishing suggestions."),
        ("Commercial License", "Authorized lifetime commercial license certificate permitting physical product sales.")
    ]
    M.info_card(
        out=out_tmp,
        title="What's in your download",
        kicker="instant digital download",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="8 original sculpted animal pencil cups  *  3 file types each  *  instant access"
    )
    return Image.open(out_tmp).convert("RGB")

# -----------------------------------------------------------------------------
# CARD 10: COMMERCIAL USE INCLUDED (Exact M.info_card layout)
# -----------------------------------------------------------------------------
def make_card_10() -> Image.Image:
    out_tmp = RENDERS_DIR / "temp_10.jpg"
    rows = [
        ("YES", "Sell physical 3D printed cups at craft fairs, local markets, and your own shop"),
        ("500 units", "per design per year included with this purchase — zero additional royalties"),
        ("NO Resale", "Re-selling, sharing, sublicensing, or distributing the digital files is strictly prohibited"),
        ("100% Original", "Hand-sculpted CAD geometry — zero copied characters, brands, or trademarked logos"),
        ("Help & Support", "Direct designer support if you ever need slicer adjustments or custom tolerances")
    ]
    M.info_card(
        out=out_tmp,
        title="Commercial use included",
        kicker="small business friendly",
        rows=rows,
        accent=CHIP_COLS[1][1],  # Slate Teal
        ink=INK,
        bg=BG_COLOR,
        footer="Sell 3D prints legally and confidently with full commercial rights"
    )
    return Image.open(out_tmp).convert("RGB")

# -----------------------------------------------------------------------------
# MASTER BUILDER
# -----------------------------------------------------------------------------
def build_all_cards():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cards = [
        ("01_cover.jpg", make_card_01),
        ("02_preview_all.jpg", make_card_02),
        ("03_preview_singles_1.jpg", make_card_03),
        ("04_preview_singles_2.jpg", make_card_04),
        ("05_lifestyle_trio.jpg", make_card_05),
        ("06_feature_vanity.jpg", make_card_06),
        ("07_feature_quality.jpg", make_card_07),
        ("08_specs_dimensions.jpg", make_card_08),
        ("09_formats.jpg", make_card_09),
        ("10_commercial_license.jpg", make_card_10)
    ]

    print(f"Assembling {len(cards)} listing cards at {SIZE}x{SIZE}...")
    for filename, fn in cards:
        out_path = IMAGES_DIR / filename
        print(f"  -> Building {filename}...")
        img = fn()
        img.save(out_path, quality=95, subsampling=0)
        print(f"     Saved {filename} ({out_path.stat().st_size / 1024:.1f} KB)")

    print("\nALL 10 LISTING CARDS ASSEMBLED SUCCESSFULLY!")

if __name__ == "__main__":
    build_all_cards()
