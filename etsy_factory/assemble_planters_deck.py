"""Assemble 10-Card Listing Deck for Geometric Planters STL + 3MF + GLB Bundle.
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

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\geometric_planters_stl_3mf_glb")
RENDERS_DIR = LISTING_DIR / "work_renders"
IMAGES_DIR = LISTING_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 2400
BG_COLOR = (250, 247, 242)      # #FAF7F2 warm cream
INK = (31, 36, 42)              # #1F242A deep charcoal/slate
ACCENT = (46, 125, 80)          # #2E7D50 forest sage green
TERRACOTTA = (194, 90, 48)      # #C25A30 warm terracotta
GOLD = (255, 214, 0)            # #FFD600 starburst yellow
WHITE = (255, 255, 255)
LIGHT_TINT = (242, 240, 235)

CHIP_COLS = [
    ("STL + 3MF + GLB", (46, 125, 80)),
    ("8 PLANTERS + 8 SAUCERS", (194, 90, 48)),
    ("7MM DRAIN HOLE", (29, 99, 184)),
    ("ZERO SUPPORTS", (123, 82, 148)),
    ("COMMERCIAL USE", (200, 140, 30))
]

PLANTERS = [
    {
        "name": "Hex Taper Planter + Saucer",
        "tag": "HEX TAPER",
        "sub": "Terracotta Matte PLA * 7mm Drain",
        "file": "graded_comfy_single_01.png",
        "dims": "Planter: 90 x 78 x 75 mm | Saucer: 98 x 85 x 14 mm"
    },
    {
        "name": "Octagon Taper Planter + Saucer",
        "tag": "OCTAGON TAPER",
        "sub": "Forest Sage Green * 8-Facet Wall",
        "file": "graded_comfy_single_02.png",
        "dims": "Planter: 85 x 85 x 75 mm | Saucer: 94 x 94 x 14 mm"
    },
    {
        "name": "Twisted Hex Planter + Saucer",
        "tag": "TWISTED HEX",
        "sub": "Desert Almond Sand * Helical Twist",
        "file": "graded_comfy_single_03.png",
        "dims": "Planter: 86 x 80 x 80 mm | Saucer: 95 x 88 x 14 mm"
    },
    {
        "name": "Twisted Square Planter + Saucer",
        "tag": "TWISTED SQUARE",
        "sub": "Stealth Charcoal * 45° Spiral Wall",
        "file": "graded_comfy_single_04.png",
        "dims": "Planter: 82 x 82 x 80 mm | Saucer: 92 x 92 x 14 mm"
    },
    {
        "name": "Twisted Triangle Planter + Saucer",
        "tag": "TWISTED TRIANGLE",
        "sub": "Denim Slate Blue * 3-Sided Helix",
        "file": "graded_comfy_single_05.png",
        "dims": "Planter: 88 x 84 x 75 mm | Saucer: 96 x 92 x 14 mm"
    },
    {
        "name": "Faceted Round Planter + Saucer",
        "tag": "FACETED ROUND",
        "sub": "Warm Honey Ochre * Diamond Facets",
        "file": "graded_comfy_single_06.png",
        "dims": "Planter: 85 x 85 x 72 mm | Saucer: 94 x 94 x 14 mm"
    },
    {
        "name": "Tall Hex Vase Planter + Saucer",
        "tag": "TALL HEX VASE",
        "sub": "Dusty Rose Clay * Slender Accent",
        "file": "graded_comfy_single_07.png",
        "dims": "Planter: 75 x 65 x 96 mm | Saucer: 84 x 73 x 14 mm"
    },
    {
        "name": "Wide Faceted Bowl + Saucer",
        "tag": "WIDE BOWL",
        "sub": "Bone White Silk * Rock Garden Bowl",
        "file": "graded_comfy_single_08.png",
        "dims": "Planter: 120 x 120 x 58 mm | Saucer: 130 x 130 x 14 mm"
    },
]


def make_rounded_thumbnail(im: Image.Image, size: Tuple[int, int], radius: int = 32) -> Image.Image:
    fitted = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    thumb = Image.new("RGBA", size, (0, 0, 0, 0))
    thumb.paste(fitted, (0, 0), mask=mask)
    return thumb


def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, y_top: int = 70):
    kicker = "WORKHORSE 3D * BOTANICAL ARCHITECTURE COLLECTION"
    fk = M.anton(26)
    d.text((120, y_top), kicker, font=fk, fill=ACCENT, anchor="la")

    ft = M.anton(70)
    d.text((120, y_top + 40), title, font=ft, fill=INK, anchor="la")

    fs = M.poppins(32)
    d.text((120, y_top + 130), subtitle, font=fs, fill=(80, 85, 95), anchor="la")

    d.line([(120, y_top + 185), (SIZE - 120, y_top + 185)], fill=(215, 210, 200), width=3)
    return y_top + 205


def draw_chips(base: Image.Image, x: int, y: int, chips: List[Tuple[str, Tuple[int, int, int]]]):
    cx = x
    for label, col in chips:
        f = M.anton(26)
        dummy_d = ImageDraw.Draw(base)
        bbox = dummy_d.textbbox((0, 0), label, font=f)
        tw = bbox[2] - bbox[0]
        pad_x, pad_y = 30, 16
        pill_w, pill_h = tw + pad_x * 2, 54

        pill = M.rounded((pill_w, pill_h), pill_h // 2, col + (255,))
        base.alpha_composite(pill, (cx, y))

        d = ImageDraw.Draw(base)
        d.text((cx + pill_w // 2, y + pill_h // 2 + 1), label, font=f, fill=WHITE, anchor="mm")
        cx += pill_w + 18


# -----------------------------------------------------------------------------
# CARD 01: HERO COVER (UNIVERSAL 3D BESTSELLER LAYOUT)
# -----------------------------------------------------------------------------
def make_bg_collage(seed: int = 22) -> Image.Image:
    """Builds a tilted collage of the 8 single planter models in the background."""
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
        (46, 125, 80),   # Sage Green
        (194, 90, 48),  # Terracotta
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
    base = make_bg_collage(seed=22)

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

    # Primary Title Line: "8 GEOMETRIC PLANTERS"
    ty = cy + 55
    t_text = "8 GEOMETRIC PLANTERS"
    fl = M.fit(d, t_text, M.anton, cw - 180, 115, 70)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "Matching Nesting Saucers  *  7mm Built-in Drainage  *  STL + 3MF + GLB"
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
    if not p_cluster.exists():
        p_cluster = RENDERS_DIR / "comfy_cluster_hero.png"

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
    chips = [
        ("STL+3MF", (46, 125, 80)),      # Sage Green
        ("8 PLANTERS", (194, 90, 48)),   # Terracotta
        ("8 SAUCERS", (29, 99, 184)),    # Denim Blue
        ("7MM DRAIN", (46, 125, 114)),   # Teal
        ("NO SUP", (123, 82, 148)),      # Violet
        ("COMMERCIAL", (200, 140, 30))   # Honey Gold
    ]
    n_chips = len(chips)
    r = 76
    gap = 28
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 120
    for j, (label, col) in enumerate(chips):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=6)
        fc = M.fit(d, label, M.anton, 2 * r - 22, 54, 20)
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
# CARD 02: HERO TABLETOP CLUSTER
# -----------------------------------------------------------------------------
def make_card_02() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "MODERN GEOMETRIC PLANTER COLLECTION", "8 Original Architectural Planters & Nesting Saucers Engineered for 3D Printing")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 75, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    rp = RENDERS_DIR / "graded_comfy_cluster_hero.png"
    if not rp.exists():
        rp = RENDERS_DIR / "comfy_cluster_hero.png"

    if rp.exists():
        im_hero = Image.open(rp).convert("RGBA")
        thumb = make_rounded_thumbnail(im_hero, (cw - 60, ch - 220), radius=50)
        thumb_border = M.rounded((cw - 60, ch - 220), 50, (0, 0, 0, 0), outline=INK + (255,), width=5)
        thumb.alpha_composite(thumb_border)
        base.alpha_composite(thumb, (cx + 30, cy + 30))

    dc = ImageDraw.Draw(base)
    dc.text((cx + 50, cy + ch - 145), "ENGINEERED FOR HOME, OFFICE & BOTANICAL DECOR", font=M.anton(44), fill=INK)
    dc.text((cx + 50, cy + ch - 75), "Each planter features faceted light-catching geometry, integrated drainage holes, and matching drip saucers.", font=M.poppins(26), fill=(80, 85, 95))

    return base.convert("RGB")


# -----------------------------------------------------------------------------
# CARD 03: GRID PART 1 (PLANTERS 1 - 4)
# -----------------------------------------------------------------------------
def make_card_03() -> Image.Image:
    return make_planter_grid_card(
        PLANTERS[:4],
        title="ARCHITECTURAL SERIES: TAPER & SPIRAL DUOS",
        subtitle="Hexagonal, octagonal, and dynamic spiral twist geometries with matching drip saucers"
    )


# -----------------------------------------------------------------------------
# CARD 04: GRID PART 2 (PLANTERS 5 - 8)
# -----------------------------------------------------------------------------
def make_card_04() -> Image.Image:
    return make_planter_grid_card(
        PLANTERS[4:],
        title="FACETED SERIES: TRIANGLE, DIAMOND & BOWL",
        subtitle="Helical triangles, multifaceted spheres, slender tall vases, and wide desktop rock gardens"
    )


def make_planter_grid_card(items: List[Dict], title: str, subtitle: str) -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, title, subtitle)

    cols, rows = 2, 2
    margin_x, margin_y = 120, y_start + 30
    total_w, total_h = SIZE - 240, SIZE - margin_y - 120
    gap_x, gap_y = 40, 40
    card_w = (total_w - gap_x) // cols
    card_h = (total_h - gap_y) // rows

    for idx, item in enumerate(items):
        r = idx // cols
        c = idx % cols
        cx = margin_x + c * (card_w + gap_x)
        cy = margin_y + r * (card_h + gap_y)

        box = M.rounded((card_w, card_h), 50, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, box, (cx, cy), blur=24, off=(0, 14), alpha=85)

        img_h = card_h - 220
        img_w = card_w - 50
        rp = RENDERS_DIR / item["file"]
        if not rp.exists():
            rp = RENDERS_DIR / item["file"].replace("graded_", "")

        if rp.exists():
            im_item = Image.open(rp).convert("RGBA")
            thumb = make_rounded_thumbnail(im_item, (img_w, img_h), radius=35)
            thumb_border = M.rounded((img_w, img_h), 35, (0, 0, 0, 0), outline=INK + (255,), width=4)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (cx + 25, cy + 25))

        dc = ImageDraw.Draw(base)
        y_text = cy + img_h + 38
        dc.text((cx + 35, y_text), item["tag"], font=M.anton(24), fill=ACCENT)
        dc.text((cx + 35, y_text + 34), item["name"], font=M.anton(38), fill=INK)
        dc.text((cx + 35, y_text + 82), item["sub"], font=M.poppins(22), fill=(100, 105, 115))
        dc.text((cx + 35, y_text + 118), item["dims"], font=M.poppins_x(20), fill=TERRACOTTA)

    return base.convert("RGB")


# -----------------------------------------------------------------------------
# CARD 05: LIFESTYLE & PLACEMENT CONTEXT
# -----------------------------------------------------------------------------
def make_card_05() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "BOTANICAL STYLING & HOME CONTEXT", "Modern plant styling for home offices, creative studios, living spaces, and shelves")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 75, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    quads = [
        ("DESK & MONITOR WORKSPACE", "Compact 85mm footprint adds vibrant organic life beside monitors and laptop stands.", "graded_comfy_single_01.png"),
        ("SUNLIT WINDOWSILL GARDEN", "Faceted edges create striking dynamic light and shadow contrasts in natural sun.", "graded_comfy_single_02.png"),
        ("COFFEE TABLE SCULPTURAL ACCENT", "Geometric elegance that complements ceramic, mid-century modern, and Scandinavian decor.", "graded_comfy_single_03.png"),
        ("MINI SUCCULENT ROCK GARDEN", "Wide bowl format accommodates multiple miniature sedums, stones, and top dressing.", "graded_comfy_single_08.png"),
    ]

    qw, qh = (cw - 60) // 2, (ch - 60) // 2
    for i, (qtitle, qdesc, qfile) in enumerate(quads):
        qx = cx + 20 + (i % 2) * (qw + 20)
        qy = cy + 20 + (i // 2) * (qh + 20)

        qb = M.rounded((qw, qh), 45, LIGHT_TINT + (255,), outline=INK + (255,), width=5)
        base.alpha_composite(qb, (qx, qy))

        rp = RENDERS_DIR / qfile
        if not rp.exists():
            rp = RENDERS_DIR / qfile.replace("graded_", "")

        if rp.exists():
            im_r = Image.open(rp).convert("RGBA")
            tw, th = qw - 60, qh - 220
            thumb = make_rounded_thumbnail(im_r, (tw, th), radius=28)
            thumb_border = M.rounded((tw, th), 28, (0, 0, 0, 0), outline=INK + (255,), width=4)
            thumb.alpha_composite(thumb_border)
            base.alpha_composite(thumb, (qx + 30, qy + 30))

        dq = ImageDraw.Draw(base)
        fqt = M.fit(dq, qtitle, M.anton, qw - 60, 42, 24)
        dq.text((qx + qw // 2, qy + qh - 130), qtitle, font=fqt, fill=INK, anchor="mm")

        fqd = M.fit(dq, qdesc, M.poppins, qw - 80, 24, 15)
        dq.text((qx + qw // 2, qy + qh - 65), qdesc, font=fqd, fill=(80, 85, 95), anchor="mm")

    return base.convert("RGB")


# -----------------------------------------------------------------------------
# CARD 06: DRAINAGE & NESTING SAUCER ENGINEERING
# -----------------------------------------------------------------------------
def make_card_06() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "DRAINAGE & SAUCER ENGINEERING", "Thoughtful horticultural engineering prevents root rot and protects your furniture")

    lw, lh = 1050, SIZE - y_start - 160
    lx, ly = 120, y_start + 40
    card_l = M.rounded((lw, lh), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card_l, (lx, ly), blur=32, off=(0, 18), alpha=90)

    rp = RENDERS_DIR / "graded_comfy_single_04.png"
    if not rp.exists():
        rp = RENDERS_DIR / "comfy_single_04.png"

    if rp.exists():
        im_r = Image.open(rp).convert("RGBA")
        thumb = make_rounded_thumbnail(im_r, (lw - 80, lh - 80), radius=45)
        thumb_border = M.rounded((lw - 80, lh - 80), 45, (0, 0, 0, 0), outline=INK + (255,), width=6)
        thumb.alpha_composite(thumb_border)
        base.alpha_composite(thumb, (lx + 40, ly + 40))

    rx, ry = 1240, y_start + 40
    rw = SIZE - rx - 120

    features = [
        ("7MM CENTER DRAINAGE HOLE", "Ensures excess water drains freely into the tray, preventing soil saturation and succulent root rot.", "OK"),
        ("MATCHING NESTING SAUCER INCLUDED", "Every single planter model comes with its own custom-contoured saucer that locks cleanly underneath.", "OK"),
        ("WATER-TIGHT 2.4MM WALL THICKNESS", "Optimized 6-perimeter solid walls prevent moisture seepage through layer lines.", "OK"),
        ("FLAT BED CONTACT AT Z=0", "100% planar base adhesion guarantees flawless first-layer printing with ZERO brim or raft needed.", "OK"),
    ]

    bh = (lh - 3 * 35) // 4
    for i, (btitle, bdesc, _) in enumerate(features):
        by = ry + i * (bh + 35)
        c_b = M.rounded((rw, bh), 40, WHITE + (255,), outline=INK + (255,), width=6)
        M.shadowed(base, c_b, (rx, by), blur=16, off=(0, 8), alpha=60)

        db = ImageDraw.Draw(base)
        chk = M.rounded((68, 68), 34, ACCENT + (255,))
        base.alpha_composite(chk, (rx + 28, by + bh // 2 - 34))
        fchk = M.anton(38)
        db.text((rx + 62, by + bh // 2 + 2), "OK", font=fchk, fill=WHITE, anchor="mm")

        fbt = M.fit(db, btitle, M.anton, rw - 135, 38, 22)
        db.text((rx + 120, by + 36), btitle, font=fbt, fill=INK, anchor="la")

        fbd = M.fit(db, bdesc, M.poppins, rw - 135, 23, 15)
        db.text((rx + 120, by + 90), bdesc, font=fbd, fill=(90, 95, 105), anchor="la")

    return base.convert("RGB")


# -----------------------------------------------------------------------------
# CARD 07: SIZES & SPECS TABLE
# -----------------------------------------------------------------------------
def make_card_07() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))
    d = ImageDraw.Draw(base)
    y_start = draw_header(d, "EXACT MEASUREMENTS & SPECIFICATIONS", "Direct measurements taken from 3D models — easily rescalable in your slicer")

    cw, ch = SIZE - 240, SIZE - y_start - 160
    cx, cy = 120, y_start + 40
    card = M.rounded((cw, ch), 65, WHITE + (255,), outline=INK + (255,), width=8)
    M.shadowed(base, card, (cx, cy), blur=32, off=(0, 20), alpha=90)

    dc = ImageDraw.Draw(base)

    # Table Header
    hy = cy + 40
    dc.rectangle([(cx + 40, hy), (cx + cw - 40, hy + 75)], fill=INK)
    dc.text((cx + 70, hy + 38), "MODEL NAME", font=M.anton(28), fill=WHITE, anchor="lm")
    dc.text((cx + 640, hy + 38), "STYLE & GEOMETRY", font=M.anton(28), fill=WHITE, anchor="lm")
    dc.text((cx + 1250, hy + 38), "PLANTER SIZE (MM)", font=M.anton(28), fill=WHITE, anchor="lm")
    dc.text((cx + 1720, hy + 38), "SAUCER SIZE (MM)", font=M.anton(28), fill=WHITE, anchor="lm")

    rows = [
        ("01. Hex Taper Planter", "Tapered 6-Sided Hexagon", "90 x 78 x 75 mm", "98 x 85 x 14 mm"),
        ("02. Octagon Taper Planter", "Tapered 8-Sided Octagon", "85 x 85 x 75 mm", "94 x 94 x 14 mm"),
        ("03. Twisted Hex Planter", "Helical Spiral Hexagon", "86 x 80 x 80 mm", "95 x 88 x 14 mm"),
        ("04. Twisted Square Planter", "Contemporary Spiral Cube", "82 x 82 x 80 mm", "92 x 92 x 14 mm"),
        ("05. Twisted Triangle Planter", "Modern 3-Sided Helical Twist", "88 x 84 x 75 mm", "96 x 92 x 14 mm"),
        ("06. Faceted Round Planter", "Multifaceted Diamond Sphere", "85 x 85 x 72 mm", "94 x 94 x 14 mm"),
        ("07. Tall Hex Vase Planter", "Slender Architectural Accent", "75 x 65 x 96 mm", "84 x 73 x 14 mm"),
        ("08. Wide Faceted Bowl", "Low Profile Desktop Rock Garden", "120 x 120 x 58 mm", "130 x 130 x 14 mm"),
    ]

    row_h = (ch - 240) // 8
    for i, (mname, mstyle, psize, ssize) in enumerate(rows):
        ry = hy + 75 + i * row_h
        bg_row = WHITE if i % 2 == 0 else LIGHT_TINT
        dc.rectangle([(cx + 40, ry), (cx + cw - 40, ry + row_h)], fill=bg_row)

        dc.text((cx + 70, ry + row_h // 2), mname, font=M.anton(26), fill=INK, anchor="lm")
        dc.text((cx + 640, ry + row_h // 2), mstyle, font=M.poppins(24), fill=(80, 85, 95), anchor="lm")
        dc.text((cx + 1250, ry + row_h // 2), psize, font=M.poppins_x(24), fill=ACCENT, anchor="lm")
        dc.text((cx + 1720, ry + row_h // 2), ssize, font=M.poppins_x(24), fill=TERRACOTTA, anchor="lm")

    # Bottom note
    fy = cy + ch - 85
    dc.text((cx + cw // 2, fy), "* All models scale flawlessly from 50% up to 250% on standard 220x220mm and 256x256mm build plates.", font=M.poppins(24), fill=(100, 105, 115), anchor="mm")

    return base.convert("RGB")


# -----------------------------------------------------------------------------
# CARD 08: 3D PRINT SETTINGS & NO-SUPPORTS GUIDE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    out_p = IMAGES_DIR / "08_print_guide.jpg"
    rows = [
        ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle (or 0.6 mm)"),
        ("LAYER HEIGHT", "0.20 mm standard / 0.16 mm for silky smooth faceted curves"),
        ("WALL PERIMETERS", "4 to 6 walls (2.4 mm) for watertight planter shells"),
        ("INFILL DENSITY", "15% Gyroid or Grid pattern for solid rigidity"),
        ("ZERO SUPPORTS", "100% self-supporting overhangs — print upright as exported"),
        ("DRAINAGE HOLE", "Built-in 7mm center drainage hole in every planter floor"),
    ]
    M.info_card(
        out_p,
        title="RECOMMENDED PRINT SETTINGS",
        kicker="OPTIMIZED FDM 3D PRINTING",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Compatible with Bambu Lab, Prusa, Creality Ender, and Anycubic FDM printers."
    )
    return Image.open(out_p).convert("RGB")


# -----------------------------------------------------------------------------
# CARD 09: MULTI-FORMAT DELIVERY (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_09() -> Image.Image:
    out_p = IMAGES_DIR / "09_file_formats.jpg"
    rows = [
        ("16 STL FILES", "8 individual geometric planters + 8 matching drip saucers"),
        ("8 3MF PLATES", "Pre-arranged Bambu Studio & Prusa plates — one click print"),
        ("8 GLB MODELS", "Full-color 3D models for 3D web preview, AR, or Blender scenes"),
        ("MATCHING SAUCERS", "Custom-contoured nesting drip trays for all 8 planters"),
        ("PDF PRINT GUIDE", "Detailed sizing table, print settings, and commercial license"),
    ]
    M.info_card(
        out_p,
        title="WHAT'S IN YOUR DOWNLOAD",
        kicker="INSTANT DIGITAL DOWNLOAD",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Geometric_Planters_STL.zip + 3MF.zip + GLB.zip + PDF Guide — Instant Download"
    )
    return Image.open(out_p).convert("RGB")


# -----------------------------------------------------------------------------
# CARD 10: COMMERCIAL PRINT LICENSE & GUARANTEE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_10() -> Image.Image:
    out_p = IMAGES_DIR / "10_license.jpg"
    rows = [
        ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
        ("UNLIMITED", "Sell as many physical planters as you make — no recurring royalties ever"),
        ("NO", "Reselling, sharing, or redistributing digital STL/3MF/GLB files"),
        ("ORIGINAL", "100% original WORKHORSE architectural designs — watertight guaranteed"),
        ("HELP", "Message the shop anytime if you need assistance with slicing or files"),
    ]
    M.info_card(
        out_p,
        title="COMMERCIAL USE INCLUDED",
        kicker="PHYSICAL PRINT PERMISSION",
        rows=rows,
        accent=TERRACOTTA,
        ink=INK,
        bg=BG_COLOR,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE."
    )
    return Image.open(out_p).convert("RGB")


# -----------------------------------------------------------------------------
# MAIN BUILD DISPATCHER
# -----------------------------------------------------------------------------
def build_deck():
    cards = [
        ("01_cover.jpg", make_card_01),
        ("02_hero.jpg", make_card_02),
        ("03_grid_part1.jpg", make_card_03),
        ("04_grid_part2.jpg", make_card_04),
        ("05_lifestyle.jpg", make_card_05),
        ("06_drainage_and_saucers.jpg", make_card_06),
        ("07_sizes.jpg", make_card_07),
        ("08_print_guide.jpg", make_card_08),
        ("09_file_formats.jpg", make_card_09),
        ("10_license.jpg", make_card_10),
    ]

    print(f"Building 10-Card Deck for Geometric Planters at {SIZE}x{SIZE}...")
    for idx, (filename, fn) in enumerate(cards, 1):
        out_path = IMAGES_DIR / filename
        im = fn()
        im.save(out_path, "JPEG", quality=95, subsampling=0)
        print(f"  [{idx:02d}/10] Saved {filename} ({out_path.stat().st_size / 1024:.0f} KB)")

    print("\n10-Card Planter Listing Deck Assembly Complete!")


if __name__ == "__main__":
    build_deck()
