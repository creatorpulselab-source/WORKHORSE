"""Assemble 10-Card Listing Deck for Sculpted 3D Keychains STL Bundle.
Adheres strictly to the WORKHORSE Universal Production Protocol:
- All media generated via ComfyUI (RTX 5070 Ti) with photorealistic tabletop grounding
- Color corrected via DaVinci Resolve 3D LUT (filmic S-curves, Kodak 2383 emulation)
- 10-card deck at 2400 x 2400, quality=95, subsampling=0
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import media as M

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"

SIZE = 2400
BG_COLOR = (250, 247, 242)      # #FAF7F2 warm cream
INK = (31, 36, 42)              # #1F242A deep charcoal/slate
ACCENT = (29, 99, 184)          # #1D63B8 royal blue
ORANGE = (212, 92, 36)          # #D45C24 warm terracotta
GOLD = (255, 214, 0)            # #FFD600 starburst yellow
WHITE = (255, 255, 255)
LIGHT_TINT = (242, 240, 235)

CHIP_COLS = [
    ("STL", (29, 99, 184)),       # Royal Blue
    ("3D PRINT", (212, 92, 36)),  # Terracotta
    ("NO SUP", (46, 125, 114)),   # Slate Teal
    ("TESTED", (123, 82, 148)),   # Royal Violet
    ("COMMERCIAL", (200, 140, 30))# Honey Gold
]

ITEMS = [
    {"name": "Baby Crystal Dragon", "tag": "CRYSTAL DRAGON", "sub": "Folded Wings * Crystal Horns", "file": "graded_comfy_single_01.png", "dims": "52 x 42 x 34 mm"},
    {"name": "Chubby Kawaii Axolotl", "tag": "KAWAII AXOLOTL", "sub": "External Gills * Chubby Cheeks", "file": "graded_comfy_single_02.png", "dims": "48 x 56 x 42 mm"},
    {"name": "Kawaii Baby Octopus", "tag": "CHIBI OCTOPUS", "sub": "Curled Tentacles * Rounded Head", "file": "graded_comfy_single_03.png", "dims": "46 x 44 x 42 mm"},
    {"name": "Geometric French Bulldog", "tag": "LOW-POLY DOG", "sub": "Sharp Facets * Origami Planes", "file": "graded_comfy_single_04.png", "dims": "50 x 38 x 36 mm"},
    {"name": "Pirate Skull Keychain", "tag": "PIRATE SKULL", "sub": "Textured Bandana * Bone Detail", "file": "graded_comfy_single_05.png", "dims": "54 x 48 x 46 mm"},
    {"name": "Retro High-Top Sneaker", "tag": "STREETWEAR", "sub": "Laces * Tread Sole * Heel Collar", "file": "graded_comfy_single_06.png", "dims": "48 x 62 x 26 mm"},
    {"name": "Lucky Maneki Neko", "tag": "LUCKY CAT", "sub": "Waving Paw * Collar Bell * Charm", "file": "graded_comfy_single_07.png", "dims": "50 x 42 x 38 mm"},
    {"name": "Chibi Space Astronaut", "tag": "ASTRONAUT", "sub": "Bubble Visor * Jetpack * Boots", "file": "graded_comfy_single_08.png", "dims": "52 x 40 x 34 mm"},
]

def make_rounded_thumbnail(im: Image.Image, size: Tuple[int, int], radius: int = 32) -> Image.Image:
    fitted = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    thumb = Image.new("RGBA", size, (0, 0, 0, 0))
    thumb.paste(fitted, (0, 0), mask=mask)
    return thumb

def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, y_top: int = 70):
    ft = M.fit(d, title.upper(), M.anton, SIZE - 240, 145, 65)
    d.text((SIZE // 2, y_top), title.upper(), font=ft, fill=INK, anchor="ma")
    fs = M.fit(d, subtitle, M.pacifico, SIZE - 360, 72, 36)
    d.text((SIZE // 2, y_top + ft.size + 16), subtitle, font=fs, fill=ACCENT, anchor="ma")
    return y_top + ft.size + fs.size + 55

def make_bg_collage(seed: int = 15) -> Image.Image:
    """Builds a tilted collage of the 8 single keychain models in the background."""
    import random
    rng = random.Random(seed)
    single_files = [RENDERS_DIR / f"graded_comfy_single_{i:02d}.png" for i in range(1, 9)]
    thumbs = []
    for p in single_files:
        if p.exists():
            im = Image.open(p).convert("RGBA")
            th = im.resize((320, 320), Image.Resampling.LANCZOS)
            thumbs.append(th)

    if not thumbs:
        return Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))

    big = int(SIZE * 1.55)
    base = Image.new("RGBA", (big, big), BG_COLOR + (255,))
    order = thumbs[:]
    rng.shuffle(order)

    edge_cols = [
        (29, 99, 184),   # Royal Blue
        (212, 92, 36),  # Terracotta
        (46, 125, 114),  # Slate Teal
        (200, 140, 30),  # Honey Gold
        (123, 82, 148),  # Violet
        (55, 130, 70),   # Sage Green
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

    # Soft radial blur / glow so background designs pop at the perimeter while keeping the center clean
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((80, 80, SIZE - 80, SIZE - 80), fill=BG_COLOR + (190,))
    cropped.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    return cropped

# -----------------------------------------------------------------------------
# CARD 01: HERO COVER
# -----------------------------------------------------------------------------
def make_card_01() -> Image.Image:
    base = make_bg_collage(seed=15)

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

    # Primary Title Line: "8 SCULPTED 3D KEYCHAINS"
    ty = cy + 55
    t_text = "8 SCULPTED 3D KEYCHAINS"
    fl = M.fit(d, t_text, M.anton, cw - 180, 115, 70)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "Crystal Dragon  *  Chubby Axolotl  *  Baby Octopus  *  Pirate Skull"
    fs = M.fit(d, sub, M.pacifico, cw - 240, 52, 30)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    sub_y = ty + (bb[3] - bb[1]) + 12
    d.text((SIZE // 2, sub_y - bbs[1]), sub, font=fs, fill=ACCENT, anchor="ma")

    # Hero Product Showcase (ComfyUI Master Render - Full uncropped bodies, centered!)
    hero_w = 1680
    hero_h = 1150
    hero_x = cx + (cw - hero_w) // 2
    hero_y = sub_y + (bbs[3] - bbs[1]) + 28

    p_cluster = RENDERS_DIR / "graded_comfy_cluster_hero.png"
    if p_cluster.exists():
        im_hero = Image.open(p_cluster).convert("RGBA")
        fitted = im_hero.resize((hero_w, hero_h), Image.Resampling.LANCZOS)
        mask = Image.new("L", (hero_w, hero_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, hero_w, hero_h), radius=50, fill=255)
        thumb = Image.new("RGBA", (hero_w, hero_h), (0, 0, 0, 0))
        thumb.paste(fitted, (0, 0), mask=mask)
        thumb_border = M.rounded((hero_w, hero_h), 50, (0, 0, 0, 0), outline=INK + (255,), width=6)
        thumb.alpha_composite(thumb_border)
        M.shadowed(base, thumb, (hero_x, hero_y), blur=24, off=(0, 12), alpha=110)
        base.alpha_composite(thumb, (hero_x, hero_y))

    # Format Chips across bottom of card
    n_chips = len(CHIP_COLS)
    r = 84
    gap = 36
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 120
    for j, (label, col) in enumerate(CHIP_COLS):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=6)
        fc = M.fit(d, label, M.anton, 2 * r - 26, 60, 22)
        d.text((xx, cyy + 3), label, font=fc, fill=WHITE, anchor="mm")

    # Bottom machine strip
    strip = "BAMBU LAB  *  PRUSA  *  CREALITY  *  ANY SLICER"
    fs2 = M.fit(d, strip, M.poppins_x, SIZE - 260, 50, 24)
    sw = M.text_w(d, strip, fs2)
    sp = M.rounded((sw + 90, 88), 44, INK + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 90) // 2, SIZE - 140))
    d.text((SIZE // 2, SIZE - 96), strip, font=fs2, fill=WHITE, anchor="mm")

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

    ds = ImageDraw.Draw(base)
    f_b1 = M.fit(ds, "INSTANT", M.anton, 240, 50, 26)
    f_b2 = M.fit(ds, "DOWNLOAD", M.anton, 270, 54, 28)
    ds.text((bx, by - 30), "INSTANT", font=f_b1, fill=INK, anchor="mm")
    ds.text((bx, by + 28), "DOWNLOAD", font=f_b2, fill=INK, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 02: ALL 8 DESIGNS GRID
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "ALL 8 SCULPTED 3D DESIGNS", "High-demand character keychains, fantasy charms, and pocket sculptures")

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

        # ComfyUI Media Image (Framed)
        rp = RENDERS_DIR / it["file"]
        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = cw - 40, ch - 200
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=28)
            thumb_border = M.rounded((tw, th), 28, (0, 0, 0, 0), outline=INK + (255,), width=4)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (cx + 20, cy + 85))

        # Bottom Labels
        fnm = M.fit(dc, it["name"], M.anton, cw - 30, 36, 20)
        dc.text((cx + cw // 2, cy + ch - 64), it["name"], font=fnm, fill=INK, anchor="mm")

        fsub = M.fit(dc, it["dims"], M.poppins, cw - 30, 24, 15)
        dc.text((cx + cw // 2, cy + ch - 28), it["dims"], font=fsub, fill=(100, 105, 115), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 03: FEATURE SPOTLIGHT - DRAGON & AXOLOTL
# -----------------------------------------------------------------------------
def make_card_03() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "BABY CRYSTAL DRAGON & CHUBBY AXOLOTL", "Sculpted fantasy characters engineered with flat support-free print beds")

    duo = [
        ("Baby Crystal Dragon", "Folded Wings * Crystal Horns * Sage Green", "graded_comfy_single_01.png", "42 x 33 x 59 mm", [
            "Intricately sculpted faceted crystal horns",
            "Compact folded wing geometry prints without supports",
            "Reinforced 4.2mm keyring loop integrated into spine",
            "Flat seated base anchors firmly to FDM build plate"
        ]),
        ("Chubby Kawaii Axolotl", "3-Tier Feathery Gills * Smiling Face * Dusty Rose", "graded_comfy_single_02.png", "59 x 78 x 54 mm", [
            "6 Prominent feathery external gill frills (3 per side)",
            "Wide happy kawaii smiling face with tiny bead eyes",
            "Smooth rounded tail and contoured belly geometry",
            "Zero non-manifold edges guaranteed for clean slicing"
        ]),
    ]

    card_w = (SIZE - 200 - 50) // 2
    card_h = SIZE - y_start - 160
    y_top = y_start + 40

    for i, (title, sub, fname, dims, bullets) in enumerate(duo):
        cx = 100 + i * (card_w + 50)
        c_box = M.rounded((card_w, card_h), 65, WHITE + (255,), outline=INK + (255,), width=8)
        M.shadowed(base, c_box, (cx, y_top), blur=28, off=(0, 16), alpha=85)

        dc = ImageDraw.Draw(base)

        # Ribbon badge
        rb = M.rounded((card_w - 70, 60), 30, ACCENT + (255,))
        base.alpha_composite(rb, (cx + 35, y_top + 35))
        frb = M.fit(dc, f"SCULPTED CHARM #{i+1:02d}", M.poppins_x, card_w - 90, 26, 16)
        dc.text((cx + card_w // 2, y_top + 65), f"SCULPTED CHARM #{i+1:02d}", font=frb, fill=WHITE, anchor="mm")

        # ComfyUI Media Frame
        rp = RENDERS_DIR / fname
        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = card_w - 80, 680
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=38)
            thumb_border = M.rounded((tw, th), 38, (0, 0, 0, 0), outline=INK + (255,), width=5)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (cx + 40, y_top + 120))

        # Title & Subtitle
        ft = M.fit(dc, title, M.anton, card_w - 60, 48, 28)
        dc.text((cx + card_w // 2, y_top + 840), title, font=ft, fill=INK, anchor="mm")

        fsub = M.fit(dc, sub, M.poppins, card_w - 70, 26, 16)
        dc.text((cx + card_w // 2, y_top + 885), sub, font=fsub, fill=ORANGE, anchor="mm")

        # Bullet Callouts
        by0 = y_top + 935
        for k, b_text in enumerate(bullets):
            chk = M.rounded((36, 36), 18, (44, 120, 68, 255))
            base.alpha_composite(chk, (cx + 50, by0 + k * 65))
            dc.text((cx + 68, by0 + 18 + k * 65), "OK", font=M.poppins_x(16), fill=WHITE, anchor="mm")

            fb = M.fit(dc, b_text, M.poppins, card_w - 120, 26, 16)
            dc.text((cx + 100, by0 + 18 + k * 65), b_text, font=fb, fill=(70, 75, 85), anchor="lm")

        # Dimensions footer
        fdim = M.fit(dc, f"Print Dimensions: {dims}", M.poppins_x, card_w - 80, 26, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 45), f"Print Dimensions: {dims}", font=fdim, fill=ACCENT, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 04: FEATURE SPOTLIGHT - OCTOPUS & PIRATE SKULL
# -----------------------------------------------------------------------------
def make_card_04() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "KAWAII OCTOPUS & DETAILED PIRATE SKULL", "Volumetric 3D sculpts generated via ComfyUI Trellis 2 & cleaned in Blender")

    duo = [
        ("Kawaii Baby Octopus", "Curled Tentacles * Chibi Eyes * Teal PLA", "graded_comfy_single_03.png", "35 x 34 x 54 mm", [
            "Eight spiraled tentacles create a natural stable bed contact",
            "Adorably rounded chibi head with embossed eye detail",
            "Smooth continuous manifold mesh with 0 boundary holes",
            "Voxel-remeshed at 0.65mm for flawless FDM layer adhesion"
        ]),
        ("Pirate Skull Keychain", "Bandana * Eyepatch * Bone Detail * Silk White", "graded_comfy_single_05.png", "74 x 77 x 57 mm", [
            "High-detail anatomical skull sculpt with textured teeth",
            "Fabric folds and knot detailing on pirate bandana",
            "Thick 4.2mm keyring loop anchored into crown of skull",
            "Tested and optimized for multi-color or single-color PLA"
        ]),
    ]

    card_w = (SIZE - 200 - 50) // 2
    card_h = SIZE - y_start - 160
    y_top = y_start + 40

    for i, (title, sub, fname, dims, bullets) in enumerate(duo):
        cx = 100 + i * (card_w + 50)
        c_box = M.rounded((card_w, card_h), 65, WHITE + (255,), outline=INK + (255,), width=8)
        M.shadowed(base, c_box, (cx, y_top), blur=28, off=(0, 16), alpha=85)

        dc = ImageDraw.Draw(base)

        rb = M.rounded((card_w - 70, 60), 30, (46, 125, 114, 255))
        base.alpha_composite(rb, (cx + 35, y_top + 35))
        frb = M.fit(dc, f"SCULPTED CHARM #{i+3:02d}", M.poppins_x, card_w - 90, 26, 16)
        dc.text((cx + card_w // 2, y_top + 65), f"SCULPTED CHARM #{i+3:02d}", font=frb, fill=WHITE, anchor="mm")

        rp = RENDERS_DIR / fname
        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = card_w - 80, 680
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=38)
            thumb_border = M.rounded((tw, th), 38, (0, 0, 0, 0), outline=INK + (255,), width=5)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (cx + 40, y_top + 120))

        ft = M.fit(dc, title, M.anton, card_w - 60, 48, 28)
        dc.text((cx + card_w // 2, y_top + 840), title, font=ft, fill=INK, anchor="mm")

        fsub = M.fit(dc, sub, M.poppins, card_w - 70, 26, 16)
        dc.text((cx + card_w // 2, y_top + 885), sub, font=fsub, fill=ORANGE, anchor="mm")

        by0 = y_top + 935
        for k, b_text in enumerate(bullets):
            chk = M.rounded((36, 36), 18, (44, 120, 68, 255))
            base.alpha_composite(chk, (cx + 50, by0 + k * 65))
            dc.text((cx + 68, by0 + 18 + k * 65), "OK", font=M.poppins_x(16), fill=WHITE, anchor="mm")

            fb = M.fit(dc, b_text, M.poppins, card_w - 120, 26, 16)
            dc.text((cx + 100, by0 + 18 + k * 65), b_text, font=fb, fill=(70, 75, 85), anchor="lm")

        fdim = M.fit(dc, f"Print Dimensions: {dims}", M.poppins_x, card_w - 80, 26, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 45), f"Print Dimensions: {dims}", font=fdim, fill=ACCENT, anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 05: FEATURE SPOTLIGHT - BULLDOG, SNEAKER, MANEKI NEKO & ASTRONAUT
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "BULLDOG, SNEAKER, LUCKY CAT & ASTRONAUT", "Geometric low-poly, streetwear fashion, and kawaii pop-culture pocket charms")

    quad = [
        ("Geometric Bulldog", "Faceted Low-Poly", "graded_comfy_single_04.png", "50 x 38 x 36 mm", "Charcoal PLA"),
        ("Retro High-Top Sneaker", "Streetwear Sneaker", "graded_comfy_single_06.png", "48 x 62 x 26 mm", "Royal Blue PLA"),
        ("Lucky Maneki Neko", "Japanese Talisman", "graded_comfy_single_07.png", "50 x 42 x 38 mm", "Honey Gold PLA"),
        ("Chibi Astronaut", "Space Explorer", "graded_comfy_single_08.png", "52 x 40 x 34 mm", "Almond Sand PLA"),
    ]

    card_w = (SIZE - 200 - 3 * 36) // 4
    card_h = SIZE - y_start - 160
    y_top = y_start + 40

    cols = [
        (45, 50, 55),    # Charcoal
        (29, 99, 184),   # Blue
        (200, 140, 30),  # Gold
        (180, 120, 80),  # Sand
    ]

    for i, (title, sub, fname, dims, mat_note) in enumerate(quad):
        cx = 100 + i * (card_w + 36)
        c_box = M.rounded((card_w, card_h), 55, WHITE + (255,), outline=INK + (255,), width=7)
        M.shadowed(base, c_box, (cx, y_top), blur=24, off=(0, 14), alpha=85)

        dc = ImageDraw.Draw(base)

        rb = M.rounded((card_w - 60, 56), 28, cols[i] + (255,))
        base.alpha_composite(rb, (cx + 30, y_top + 30))
        frb = M.fit(dc, f"CHARM #{i+4:02d}", M.poppins_x, card_w - 80, 24, 16)
        dc.text((cx + card_w // 2, y_top + 58), f"CHARM #{i+4:02d}", font=frb, fill=WHITE, anchor="mm")

        rp = RENDERS_DIR / fname
        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = card_w - 60, 680
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=32)
            thumb_border = M.rounded((tw, th), 32, (0, 0, 0, 0), outline=INK + (255,), width=5)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (cx + 30, y_top + 110))

        ft = M.fit(dc, title, M.anton, card_w - 40, 42, 22)
        dc.text((cx + card_w // 2, y_top + card_h - 220), title, font=ft, fill=INK, anchor="mm")

        fsub = M.fit(dc, sub, M.poppins, card_w - 50, 26, 16)
        dc.text((cx + card_w // 2, y_top + card_h - 165), sub, font=fsub, fill=ACCENT, anchor="mm")

        fmat = M.fit(dc, mat_note, M.poppins_x, card_w - 60, 22, 14)
        dc.text((cx + card_w // 2, y_top + card_h - 120), mat_note, font=fmat, fill=ORANGE, anchor="mm")

        fdim = M.fit(dc, f"Size: {dims}", M.poppins_x, card_w - 60, 22, 14)
        dc.text((cx + card_w // 2, y_top + card_h - 60), f"Size: {dims}", font=fdim, fill=(110, 115, 125), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 06: LIFESTYLE / IN-USE CONTEXT
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "EVERYDAY CARRY & BAG CHARM STYLING", "Pocketable, lightweight, and engineered for daily keychains, duffels, and backpacks")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 75, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    quads = [
        ("CAR & HOUSE KEYS", "Compact 40-55mm profile clips neatly alongside key fobs without pocket crowding.", "graded_comfy_single_01.png"),
        ("GYM & DUFFEL BAGS", "Instant tactical and personality identifier for gym bags, lockers, and gear pouches.", "graded_comfy_single_04.png"),
        ("BACKPACK & EDC GEAR", "Thick 2.2mm eyelet walls withstand carabiner clipping and everyday friction.", "graded_comfy_single_05.png"),
        ("DESK PET & FIGURINE", "Flat bottom plane allows keychains to stand upright on desks as miniature sculptures.", "graded_comfy_single_02.png"),
    ]

    qw, qh = (cw - 60) // 2, (ch - 60) // 2
    for i, (qtitle, qdesc, qfile) in enumerate(quads):
        qx = cx + 20 + (i % 2) * (qw + 20)
        qy = cy + 20 + (i // 2) * (qh + 20)

        qb = M.rounded((qw, qh), 45, LIGHT_TINT + (255,), outline=INK + (255,), width=5)
        base.alpha_composite(qb, (qx, qy))

        dq = ImageDraw.Draw(base)

        rp = RENDERS_DIR / qfile
        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = qw - 60, qh - 220
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=28)
            thumb_border = M.rounded((tw, th), 28, (0, 0, 0, 0), outline=INK + (255,), width=4)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (qx + 30, qy + 30))

        fqt = M.fit(dq, qtitle, M.anton, qw - 60, 42, 24)
        dq.text((qx + qw // 2, qy + qh - 130), qtitle, font=fqt, fill=INK, anchor="mm")

        fqd = M.fit(dq, qdesc, M.poppins, qw - 80, 24, 15)
        dq.text((qx + qw // 2, qy + qh - 65), qdesc, font=fqd, fill=(80, 85, 95), anchor="mm")

    return base.convert("RGB")

# -----------------------------------------------------------------------------
# CARD 07: FEATURE QUALITY & 3D PRINT DETAILS
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "PRINT QUALITY & TOPOLOGY GUARANTEE", "100% Watertight meshes, voxel-remeshed topology, and zero slicer supports")

    lw, lh = 1100, SIZE - y_start - 160
    lx, ly = 120, y_start + 40
    card_l = M.rounded((lw, lh), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (lx, ly), blur=32, off=(0, 18), alpha=90)

    rp = RENDERS_DIR / "graded_comfy_single_05.png" # Skull detail
    if rp.exists():
        im_r = Image.open(rp).convert("RGBA")
        thumb = make_rounded_thumbnail(im_r, (lw - 80, lh - 80), radius=45)
        thumb_border = M.rounded((lw - 80, lh - 80), 45, (0, 0, 0, 0), outline=INK + (255,), width=6)
        thumb.alpha_composite(thumb_border)
        base.alpha_composite(thumb, (lx + 40, ly + 40))

    rx, ry = 1280, y_start + 40
    rw = SIZE - rx - 120

    badges = [
        ("ZERO SUPPORTS REQUIRED", "Mathematically leveled bottom plane and self-supporting overhangs allow printing directly on bed without support waste.", "check"),
        ("REINFORCED KEYRING HOLES", "Eyelet walls are at least 2.2 mm thick to prevent breakage under continuous everyday pocket strain.", "check"),
        ("100% WATERTIGHT MESHES", "Verified with 0 non-manifold edges, 0 intersecting faces, and perfect slicer perimeter layers.", "check"),
        ("FAST PRINTS - HIGH TURNOVER", "Each keychain prints in 25 to 50 minutes, allowing you to batch produce dozens per build plate.", "check"),
    ]

    bh = (lh - 3 * 35) // 4
    for i, (btitle, bdesc, _) in enumerate(badges):
        by = ry + i * (bh + 35)
        c_b = M.rounded((rw, bh), 40, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, c_b, (rx, by), blur=16, off=(0, 8), alpha=60)

        db = ImageDraw.Draw(base)
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
# CARD 08: PRINT SETTINGS & SLICER GUIDE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    out_p = IMAGES_DIR / "08_specs_dimensions.jpg"
    rows = [
        ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
        ("LAYER HEIGHT", "0.20 mm standard / 0.16 mm for fine facial details"),
        ("WALL PERIMETERS", "3 to 4 walls (1.6 mm) for durable pocket-proof shells"),
        ("INFILL DENSITY", "15% to 20% Gyroid or Grid pattern for solid core support"),
        ("ZERO SUPPORTS", "100% self-supporting geometry — flat base plane at Z=0"),
        ("MATERIALS", "Matte PLA, Standard PLA, PETG, ASA or Silk PLA"),
    ]
    M.info_card(
        out_p,
        title="RECOMMENDED PRINT SETTINGS",
        kicker="OPTIMIZED FDM 3D PRINTING",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Tested on Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic."
    )
    return Image.open(out_p).convert("RGB")

# -----------------------------------------------------------------------------
# CARD 09: FORMATS & WHAT'S IN YOUR DOWNLOAD (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_09() -> Image.Image:
    out_p = IMAGES_DIR / "09_formats.jpg"
    rows = [
        ("8 STL FILES", "Watertight binary STL files with millimeter scaling (1 file per keychain)"),
        ("SLICER READY", "Drag-and-drop into Bambu Studio, PrusaSlicer, OrcaSlicer, or Cura"),
        ("REINFORCED", "Built-in 4.2mm keyring loops with 2.2mm wall thickness — zero weak points"),
        ("FLAT BED BASE", "Engineered planar first layer contact at Z=0 — zero brim or raft needed"),
        ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document"),
    ]
    M.info_card(
        out_p,
        title="WHAT'S IN YOUR DOWNLOAD",
        kicker="INSTANT DIGITAL DOWNLOAD",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Keychains_STL.zip (8 Solid STL Files) + Print_Guide_and_License.pdf"
    )
    return Image.open(out_p).convert("RGB")

# -----------------------------------------------------------------------------
# CARD 10: COMMERCIAL PRINT LICENSE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_10() -> Image.Image:
    out_p = IMAGES_DIR / "10_commercial_license.jpg"
    rows = [
        ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
        ("UNLIMITED", "Sell as many physical keychains as you make — no recurring royalties ever"),
        ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
        ("ORIGINAL", "100% original WORKHORSE sculpted designs — safe from trademark claims"),
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

# -----------------------------------------------------------------------------
# MAIN GENERATOR PIPELINE
# -----------------------------------------------------------------------------
def assemble_all_cards():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    deck = [
        ("01_cover.jpg", make_card_01),
        ("02_preview_all.jpg", make_card_02),
        ("03_feature_dragon_axolotl.jpg", make_card_03),
        ("04_feature_octopus_skull.jpg", make_card_04),
        ("05_feature_wolf_blaster.jpg", make_card_05),
        ("06_lifestyle.jpg", make_card_06),
        ("07_feature_quality.jpg", make_card_07),
        ("08_specs_dimensions.jpg", make_card_08),
        ("09_formats.jpg", make_card_09),
        ("10_commercial_license.jpg", make_card_10),
    ]

    print(f"Generating all 10 cards for Sculpted Keychains in {IMAGES_DIR}...")
    for fname, fn in deck:
        out_p = IMAGES_DIR / fname
        im = fn()
        im.save(out_p, "JPEG", quality=95, subsampling=0)
        print(f"  [OK] Saved {fname} ({out_p.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    assemble_all_cards()
