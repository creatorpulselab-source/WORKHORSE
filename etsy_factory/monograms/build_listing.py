"""Media kit and listing builder for Cute Floral Split Monogram SVG Bundle.

Generates 10 Etsy listing photos (2400x2400 high-res):
01_cover.jpg: High-converting storefront cover with sample personalized letters & badges
02_split_alphabet_showcase.jpg: Clean grid of all 26 Split Letters A-Z with full margins
03_botanical_initials_showcase.jpg: Clean grid of all 26 Full Botanical Monogram Letters A-Z
04_numbers_ampersand_showcase.jpg: Split & Full Numbers 0-9 and Ampersands
05_mockup_tote_bag.jpg: Photorealistic ComfyUI canvas tote bag with HTV vinyl monogram
06_mockup_nursery_plaque.jpg: Photorealistic ComfyUI round wooden plaque with nursery monogram
07_mockup_ceramic_mug.jpg: Photorealistic ComfyUI ceramic coffee mug with vinyl decal
08_mockup_acrylic_keychain.jpg: Photorealistic ComfyUI clear acrylic keychain with floral initial
09_how_to_personalize_guide.jpg: Cricut Design Space step-by-step personalization tutorial
10_whats_included_and_license.jpg: Complete file breakdown and commercial license guarantee

Also writes listing.json, listing.md, and validates strict Etsy constraints.
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
from etsy_factory.monograms import shapes as MS

SLUG = "cute_floral_monogram_alphabet_svg_cut_files"
W, H = 2400, 2400

# Color Palette (Elegant Floral Craft Niche)
FOREST = (42, 60, 48)
SAGE = (74, 107, 83)
GOLD = (196, 142, 58)
CREAM = (252, 250, 246)
WARM_WHITE = (255, 255, 255)
CHARCOAL = (38, 38, 38)
MUTED_GRAY = (110, 110, 110)
SOFT_BORDER = (225, 230, 226)

FONT_SERIF = str(MS.FONT_PATH)
FONT_SANS = r"C:\Windows\Fonts\arial.ttf"
FONT_SANS_BOLD = r"C:\Windows\Fonts\arialbd.ttf"

TITLE = "Floral Split Monogram SVG Bundle, Alphabet Letters A-Z Numbers Font Cut Files for Cricut, Silhouette, Wedding Nursery Monograms"
TAGS = [
    "split monogram svg",
    "alphabet monogram",
    "floral monogram svg",
    "alphabet svg bundle",
    "cricut letters svg",
    "botanical monogram",
    "wedding monogram svg",
    "nursery monogram svg",
    "monogram font svg",
    "initial letters cut",
    "cricut monogram svg",
    "split letters svg",
    "cut files for cricut",
]
PRICE = 4.99
LIST_PRICE = 12.49


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def load_thumb(thumbs_dir: Path, slug: str, style: str) -> Image.Image:
    p = thumbs_dir / f"{slug}_{style}_th.png"
    if p.exists():
        return Image.open(p).convert("RGBA")
    return Image.new("RGBA", (400, 400), (0, 0, 0, 0))


def composite_name_in_split(split_img: Image.Image, name: str, font_size: int = 58) -> Image.Image:
    """Renders a personalized name inside the split space of the monogram."""
    out = split_img.copy()
    d = ImageDraw.Draw(out)
    f = get_font(FONT_SANS_BOLD, font_size)
    cx = out.width // 2
    cy = int(out.height * 0.48)
    d.text((cx, cy), name.upper(), fill=CHARCOAL, font=f, anchor="mm")
    return out


# -----------------------------------------------------------------------------
# SLIDE 01: HERO COVER
# -----------------------------------------------------------------------------
def make_01_cover(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Decorative header
    d.rectangle([0, 0, W, 380], fill=FOREST)
    f_title = get_font(FONT_SERIF, 86)
    f_sub = get_font(FONT_SANS_BOLD, 38)
    d.text((W // 2, 130), "FLORAL SPLIT MONOGRAM BUNDLE", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 230), "COMPLETE ALPHABET A - Z  •  NUMBERS 0 - 9  •  AMPERSAND &", fill=(215, 235, 220), font=f_sub, anchor="mm")

    # Feature badges under header
    badges = ["74 CUT FILES", "SPLIT + FULL BOTANICAL", "SVG • DXF • EPS • 300 DPI PNG", "CRICUT & SILHOUETTE READY"]
    bx_total = sum(len(b) * 20 + 50 for b in badges)
    cur_bx = (W - bx_total) // 2
    f_badge = get_font(FONT_SANS_BOLD, 28)
    for b in badges:
        bw = len(b) * 20 + 40
        d.rounded_rectangle([cur_bx, 290, cur_bx + bw, 345], radius=12, fill=GOLD)
        d.text((cur_bx + bw // 2, 317), b, fill=WARM_WHITE, font=f_badge, anchor="mm")
        cur_bx += bw + 15

    # Featured 4 large split monograms: M, B, S, A with sample personalized names
    samples = [
        ("Letter_M", "split", "MILLER", (280, 500)),
        ("Letter_B", "split", "BELLA", (1300, 500)),
        ("Letter_S", "split", "SOPHIA", (280, 1350)),
        ("Letter_A", "split", "ALEXANDER", (1300, 1350)),
    ]
    card_w, card_h = 820, 780
    f_card_sub = get_font(FONT_SANS, 30)

    for slug, style, name, (cx, cy) in samples:
        # Card background
        d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=28, fill=WARM_WHITE, outline=SOFT_BORDER, width=3)
        th = load_thumb(thumbs_dir, slug, style)
        if th.width > 0:
            th_personalized = composite_name_in_split(th, name, font_size=52)
            th_personalized.thumbnail((card_w - 120, card_h - 160), Image.Resampling.LANCZOS)
            px = cx + (card_w - th_personalized.width) // 2
            py = cy + 40 + (card_h - 180 - th_personalized.height) // 2
            im.paste(th_personalized, (px, py), th_personalized)
        d.text((cx + card_w // 2, cy + card_h - 60), f"Split {name.upper()}", fill=MUTED_GRAY, font=f_card_sub, anchor="mm")

    # Bottom Banner
    d.rectangle([0, H - 180, W, H], fill=FOREST)
    f_bot = get_font(FONT_SANS_BOLD, 36)
    d.text((W // 2, H - 90), "COMMERCIAL LICENSE INCLUDED  •  INSTANT DIGITAL DOWNLOAD", fill=WARM_WHITE, font=f_bot, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 02: SPLIT ALPHABET SHOWCASE (A-Z)
# -----------------------------------------------------------------------------
def make_02_split_alphabet(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=FOREST)
    f_title = get_font(FONT_SERIF, 72)
    f_sub = get_font(FONT_SANS_BOLD, 34)
    d.text((W // 2, 100), "COMPLETE SPLIT ALPHABET (A - Z)", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 190), "Every letter includes dual split bars ready for custom name insertion", fill=(215, 235, 220), font=f_sub, anchor="mm")

    # 5 rows x 6 cols (or 6 cols: 5 rows x 5 = 25 + 1 = 26)
    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    cols, rows = 6, 5
    ox = 140
    oy = 310
    cell_w = (W - 280) // cols
    cell_h = (H - 450) // rows
    f_lbl = get_font(FONT_SANS_BOLD, 32)

    for i, char in enumerate(letters):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        # Clean letter box
        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=16, fill=WARM_WHITE, outline=SOFT_BORDER, width=2)
        th = load_thumb(thumbs_dir, f"Letter_{char}", "split")
        if th.width > 0:
            th.thumbnail((cell_w - 60, cell_h - 90), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 100 - th.height) // 2
            im.paste(th, (px, py), th)
        d.text((cx + cell_w // 2, cy + cell_h - 35), f"Split {char}", fill=FOREST, font=f_lbl, anchor="mm")

    # Footer callout
    d.rectangle([0, H - 120, W, H], fill=FOREST)
    d.text((W // 2, H - 60), "100% Welded Compound Paths  •  Zero Overlapping Cuts  •  Instant Weeding", fill=WARM_WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 03: FULL BOTANICAL INITIALS SHOWCASE (A-Z)
# -----------------------------------------------------------------------------
def make_03_botanical_initials(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=FOREST)
    f_title = get_font(FONT_SERIF, 72)
    f_sub = get_font(FONT_SANS_BOLD, 34)
    d.text((W // 2, 100), "FULL BOTANICAL INITIAL LETTERS (A - Z)", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 190), "Intact letters intertwined with delicate floral vines & blossoms", fill=(215, 235, 220), font=f_sub, anchor="mm")

    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    cols, rows = 6, 5
    ox = 140
    oy = 310
    cell_w = (W - 280) // cols
    cell_h = (H - 450) // rows
    f_lbl = get_font(FONT_SANS_BOLD, 32)

    for i, char in enumerate(letters):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=16, fill=WARM_WHITE, outline=SOFT_BORDER, width=2)
        th = load_thumb(thumbs_dir, f"Letter_{char}", "botanical")
        if th.width > 0:
            th.thumbnail((cell_w - 60, cell_h - 90), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 100 - th.height) // 2
            im.paste(th, (px, py), th)
        d.text((cx + cell_w // 2, cy + cell_h - 35), f"Initial {char}", fill=FOREST, font=f_lbl, anchor="mm")

    d.rectangle([0, H - 120, W, H], fill=FOREST)
    d.text((W // 2, H - 60), "Ideal for Nursery Signs, Monogram Totes, Drinkware & Keychains", fill=WARM_WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 04: NUMBERS & AMPERSAND SHOWCASE
# -----------------------------------------------------------------------------
def make_04_numbers_ampersand(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=FOREST)
    f_title = get_font(FONT_SERIF, 72)
    f_sub = get_font(FONT_SANS_BOLD, 34)
    d.text((W // 2, 100), "NUMBERS 0 - 9 & AMPERSAND (&)", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 190), "Both Split & Full Botanical versions for wedding dates & milestones", fill=(215, 235, 220), font=f_sub, anchor="mm")

    chars = [str(i) for i in range(10)] + ["&"]
    # Section 1: Split Numbers (Top half)
    f_sec = get_font(FONT_SANS_BOLD, 42)
    d.text((120, 310), "SPLIT NUMBERS & AMPERSAND (Insert dates, years, or family names)", fill=FOREST, font=f_sec)

    cols = 6
    cell_w = (W - 240) // cols
    cell_h = 420
    for i, char in enumerate(chars):
        r = i // cols
        c = i % cols
        cx = 120 + c * cell_w
        cy = 380 + r * cell_h

        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=16, fill=WARM_WHITE, outline=SOFT_BORDER, width=2)
        slug = f"Number_{char}" if char.isdigit() else "Ampersand"
        th = load_thumb(thumbs_dir, slug, "split")
        if th.width > 0:
            th.thumbnail((cell_w - 50, cell_h - 80), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 90 - th.height) // 2
            im.paste(th, (px, py), th)

    # Section 2: Full Botanical Numbers (Bottom half)
    sec2_y = 1280
    d.text((120, sec2_y), "FULL BOTANICAL NUMBERS & AMPERSAND", fill=FOREST, font=f_sec)
    for i, char in enumerate(chars):
        r = i // cols
        c = i % cols
        cx = 120 + c * cell_w
        cy = sec2_y + 70 + r * cell_h

        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=16, fill=WARM_WHITE, outline=SOFT_BORDER, width=2)
        slug = f"Number_{char}" if char.isdigit() else "Ampersand"
        th = load_thumb(thumbs_dir, slug, "botanical")
        if th.width > 0:
            th.thumbnail((cell_w - 50, cell_h - 80), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 90 - th.height) // 2
            im.paste(th, (px, py), th)

    d.rectangle([0, H - 120, W, H], fill=FOREST)
    d.text((W // 2, H - 60), "Wedding Table Numbers  •  Birth Announcements  •  Graduation 2027", fill=WARM_WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 05: TOTE BAG LIFESTYLE MOCKUP (ComfyUI)
# -----------------------------------------------------------------------------
def make_05_mockup_tote_bag(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\tote_bag_lifestyle_101.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM)
    else:
        bg = Image.open(bg_p).convert("RGBA")
        im = bg.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Monogram "M" with name "MILLER" on canvas tote
    th = load_thumb(thumbs_dir, "Letter_M", "split")
    if th.width > 0:
        personalized = composite_name_in_split(th, "MILLER", font_size=56)
        # Resize to fit naturally on tote
        personalized.thumbnail((820, 820), Image.Resampling.LANCZOS)

        # Contact shadow (matching morning window lighting from top-left)
        shadow = Image.new("RGBA", personalized.size, (0, 0, 0, 0))
        alpha = personalized.split()[-1]
        shadow.paste((30, 25, 20, 90), (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))

        # Position centered on tote body
        tx = (W - personalized.width) // 2
        ty = (H - personalized.height) // 2 + 60

        # Paste shadow slightly offset
        im.paste(shadow, (tx + 12, ty + 16), shadow)
        # Paste decal with slight warm-charcoal HTV vinyl look
        im.paste(personalized, (tx, ty), personalized)

    # Header badge & footer info
    d.rounded_rectangle([100, 80, 840, 200], radius=18, fill=(255, 255, 255, 240), outline=SOFT_BORDER, width=2)
    f_bd = get_font(FONT_SANS_BOLD, 36)
    f_sm = get_font(FONT_SANS, 26)
    d.text((140, 115), "CANVAS TOTE BAG MOCKUP", fill=FOREST, font=f_bd)
    d.text((140, 160), "Heat Transfer Vinyl (HTV) Project Inspiration", fill=MUTED_GRAY, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 06: NURSERY WOODEN PLAQUE MOCKUP (ComfyUI)
# -----------------------------------------------------------------------------
def make_06_mockup_nursery_plaque(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\nursery_wooden_plaque_202.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM)
    else:
        bg = Image.open(bg_p).convert("RGBA")
        im = bg.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Monogram "E" with name "EMMA" on round wooden plaque
    th = load_thumb(thumbs_dir, "Letter_E", "split")
    if th.width > 0:
        personalized = composite_name_in_split(th, "EMMA", font_size=56)
        personalized.thumbnail((720, 720), Image.Resampling.LANCZOS)

        # Realistic 3D laser-cut shadow
        shadow = Image.new("RGBA", personalized.size, (0, 0, 0, 0))
        alpha = personalized.split()[-1]
        shadow.paste((20, 15, 10, 110), (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))

        tx = (W - personalized.width) // 2
        ty = (H - personalized.height) // 2 + 10

        im.paste(shadow, (tx + 14, ty + 18), shadow)
        im.paste(personalized, (tx, ty), personalized)

    d.rounded_rectangle([100, 80, 880, 200], radius=18, fill=(255, 255, 255, 240), outline=SOFT_BORDER, width=2)
    f_bd = get_font(FONT_SANS_BOLD, 36)
    f_sm = get_font(FONT_SANS, 26)
    d.text((140, 115), "NURSERY WOOD SIGN MOCKUP", fill=FOREST, font=f_bd)
    d.text((140, 160), "Laser-Cut Wood or Adhesive Vinyl Nursery Sign", fill=MUTED_GRAY, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 07: CERAMIC COFFEE MUG MOCKUP (ComfyUI)
# -----------------------------------------------------------------------------
def make_07_mockup_ceramic_mug(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\ceramic_mug_lifestyle_303.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM)
    else:
        bg = Image.open(bg_p).convert("RGBA")
        im = bg.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Monogram "C" with name "CHARLOTTE" on mug with cylindrical warp
    th = load_thumb(thumbs_dir, "Letter_C", "split")
    if th.width > 0:
        personalized = composite_name_in_split(th, "CHARLOTTE", font_size=56)
        personalized.thumbnail((540, 540), Image.Resampling.LANCZOS)

        # Apply slight cylindrical horizontal perspective squeeze (0.92)
        sq_w = int(personalized.width * 0.92)
        sq_h = personalized.height
        warped = personalized.resize((sq_w, sq_h), Image.Resampling.LANCZOS)

        shadow = Image.new("RGBA", warped.size, (0, 0, 0, 0))
        alpha = warped.split()[-1]
        shadow.paste((15, 15, 20, 80), (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(6))

        tx = (W - warped.width) // 2 - 20
        ty = (H - warped.height) // 2 + 70

        im.paste(shadow, (tx + 10, ty + 12), shadow)
        im.paste(warped, (tx, ty), warped)

    d.rounded_rectangle([100, 80, 880, 200], radius=18, fill=(255, 255, 255, 240), outline=SOFT_BORDER, width=2)
    f_bd = get_font(FONT_SANS_BOLD, 36)
    f_sm = get_font(FONT_SANS, 26)
    d.text((140, 115), "CERAMIC COFFEE MUG MOCKUP", fill=FOREST, font=f_bd)
    d.text((140, 160), "Permanent Adhesive Vinyl Decal or Sublimation", fill=MUTED_GRAY, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 08: ACRYLIC KEYCHAIN MOCKUP (ComfyUI)
# -----------------------------------------------------------------------------
def make_08_mockup_acrylic_keychain(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\acrylic_keychain_flatlay_404.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM)
    else:
        bg = Image.open(bg_p).convert("RGBA")
        im = bg.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Initial letter "S" botanical monogram on clear acrylic
    th = load_thumb(thumbs_dir, "Letter_S", "botanical")
    if th.width > 0:
        th.thumbnail((480, 480), Image.Resampling.LANCZOS)

        shadow = Image.new("RGBA", th.size, (0, 0, 0, 0))
        alpha = th.split()[-1]
        shadow.paste((30, 25, 20, 85), (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(7))

        tx = (W - th.width) // 2
        ty = (H - th.height) // 2 + 20

        im.paste(shadow, (tx + 8, ty + 10), shadow)
        im.paste(th, (tx, ty), th)

    d.rounded_rectangle([100, 80, 880, 200], radius=18, fill=(255, 255, 255, 240), outline=SOFT_BORDER, width=2)
    f_bd = get_font(FONT_SANS_BOLD, 36)
    f_sm = get_font(FONT_SANS, 26)
    d.text((140, 115), "ACRYLIC KEYCHAIN MOCKUP", fill=FOREST, font=f_bd)
    d.text((140, 160), "Custom Initial Keychain & Bag Tag Inspiration", fill=MUTED_GRAY, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 09: HOW TO PERSONALIZE GUIDE (Cricut Design Space Infographic)
# -----------------------------------------------------------------------------
def make_09_how_to_personalize_guide(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 280], fill=FOREST)
    f_title = get_font(FONT_SERIF, 72)
    f_sub = get_font(FONT_SANS_BOLD, 34)
    d.text((W // 2, 100), "HOW TO PERSONALIZE IN CRICUT", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 200), "Easy 3-Step Process in Cricut Design Space & Silhouette Studio", fill=(215, 235, 220), font=f_sub, anchor="mm")

    f_step_num = get_font(FONT_SERIF, 64)
    f_step_head = get_font(FONT_SANS_BOLD, 46)
    f_body = get_font(FONT_SANS, 34)

    steps = [
        ("1", "Upload & Ungroup the SVG",
         "Import your letter's SVG file into Cricut Design Space.\n"
         "The monogram imports pre-sized to 6 inches with 100% welded geometry\n"
         "so you never have to deal with missing pieces or overlapping cuts."),
        ("2", "Type Your Custom Name",
         "Select the Text tool (T) and type your name, surname, or date.\n"
         "Use ALL CAPS (like Montserrat) or a romantic script font.\n"
         "Place the text inside the open center split ribbon between the two bars."),
        ("3", "Center Align & Click 'Weld'",
         "Select both your Monogram and the Text.\n"
         "Click 'Align' -> 'Center Horizontally' on the top bar.\n"
         "Then click 'Combine' -> 'Weld' in the bottom right.\n"
         "Your custom monogram will cut as one seamless, perfect piece!"),
    ]

    cur_y = 350
    for num, head, desc in steps:
        # Step card
        d.rounded_rectangle([140, cur_y, W - 140, cur_y + 360], radius=24, fill=WARM_WHITE, outline=SOFT_BORDER, width=3)
        # Number pill
        d.ellipse([180, cur_y + 40, 280, cur_y + 140], fill=GOLD)
        d.text((230, cur_y + 90), num, fill=WARM_WHITE, font=f_step_num, anchor="mm")

        d.text((320, cur_y + 60), head, fill=FOREST, font=f_step_head)
        d.multiline_text((320, cur_y + 130), desc, fill=CHARCOAL, font=f_body, spacing=14)
        cur_y += 420

    # Software Compatibility Icons / Footer
    d.rectangle([0, H - 240, W, H], fill=FOREST)
    d.text((W // 2, H - 150), "COMPATIBLE WITH ALL MAJOR CUTTING MACHINES & SOFTWARE", fill=WARM_WHITE, font=f_sub, anchor="mm")
    f_soft = get_font(FONT_SANS, 30)
    d.text((W // 2, H - 90), "Cricut Design Space  •  Silhouette Studio  •  Glowforge  •  Brother ScanNCut  •  Illustrator", fill=(215, 235, 220), font=f_soft, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 10: WHAT'S INCLUDED & COMMERCIAL LICENSE
# -----------------------------------------------------------------------------
def make_10_whats_included_and_license(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 280], fill=FOREST)
    f_title = get_font(FONT_SERIF, 72)
    f_sub = get_font(FONT_SANS_BOLD, 34)
    d.text((W // 2, 100), "WHAT'S INCLUDED & LICENSE", fill=WARM_WHITE, font=f_title, anchor="mm")
    d.text((W // 2, 200), "Complete Digital Craft Package  •  Commercial Small Business License", fill=(215, 235, 220), font=f_sub, anchor="mm")

    f_head = get_font(FONT_SANS_BOLD, 44)
    f_body = get_font(FONT_SANS, 34)

    # Left Box: What You Receive
    d.rounded_rectangle([120, 340, W // 2 - 40, H - 180], radius=24, fill=WARM_WHITE, outline=SOFT_BORDER, width=3)
    d.text((160, 400), "WHAT YOU RECEIVE:", fill=FOREST, font=f_head)

    included_text = (
        "• 26 Split Monograms (Letters A - Z)\n"
        "• 26 Full Botanical Monograms (A - Z)\n"
        "• 10 Split Numbers (0 - 9)\n"
        "• 10 Full Botanical Numbers (0 - 9)\n"
        "• 2 Ampersands (&)\n\n"
        "74 TOTAL DESIGNS IN 4 FORMATS:\n"
        "✔ SVG Files (Clean welded compound paths)\n"
        "✔ SVG 2-Layer Files (Multi-color vinyl)\n"
        "✔ DXF Files (Silhouette Studio Basic)\n"
        "✔ EPS Files (Illustrator / CorelDraw)\n"
        "✔ 300 DPI Transparent PNGs (3600px+)\n\n"
        "BONUS INCLUDED:\n"
        "✔ Multi-Page Master PDF Visual Index\n"
        "✔ Step-by-Step Cricut & Silhouette Tutorial\n"
        "✔ Free Curated Font Pairing Guide"
    )
    d.multiline_text((160, 480), included_text, fill=CHARCOAL, font=f_body, spacing=16)

    # Right Box: Commercial License Terms
    d.rounded_rectangle([W // 2 + 40, 340, W - 120, H - 180], radius=24, fill=WARM_WHITE, outline=SOFT_BORDER, width=3)
    d.text((W // 2 + 80, 400), "COMMERCIAL LICENSE TERMS:", fill=FOREST, font=f_head)

    license_text = (
        "YOU MAY:\n"
        "✔ Sell physical products made with these files\n"
        "   (Shirts, mugs, tote bags, nursery signs,\n"
        "   decals, wedding decor, keychains)\n"
        "✔ Commercial use up to 500 physical units\n"
        "   per design included at no extra cost!\n"
        "✔ Personalize with custom names & text\n\n"
        "YOU MAY NOT:\n"
        "✖ Resell, share, or redistribute digital files\n"
        "✖ Upload to Print-on-Demand (POD) sites\n"
        "✖ Claim vector artwork as your own\n\n"
        "100% CRAFTER GUARANTEE:\n"
        "Every file is thoroughly tested on Cricut &\n"
        "Silhouette. If you need any assistance, we\n"
        "are here to help promptly!"
    )
    d.multiline_text((W // 2 + 80, 480), license_text, fill=CHARCOAL, font=f_body, spacing=16)

    # Bottom Banner
    d.rectangle([0, H - 140, W, H], fill=FOREST)
    d.text((W // 2, H - 70), "INSTANT DOWNLOAD  •  NO WAITING  •  START CRAFTING TODAY", fill=WARM_WHITE, font=f_sub, anchor="mm")

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

    print("Generating 10 Etsy Listing Photos (2400x2400)...")
    make_01_cover(img_dir / "01_cover.jpg", thumbs_dir)
    make_02_split_alphabet(img_dir / "02_split_alphabet_showcase.jpg", thumbs_dir)
    make_03_botanical_initials(img_dir / "03_botanical_initials_showcase.jpg", thumbs_dir)
    make_04_numbers_ampersand(img_dir / "04_numbers_ampersand_showcase.jpg", thumbs_dir)
    make_05_mockup_tote_bag(img_dir / "05_mockup_tote_bag.jpg", thumbs_dir)
    make_06_mockup_nursery_plaque(img_dir / "06_mockup_nursery_plaque.jpg", thumbs_dir)
    make_07_mockup_ceramic_mug(img_dir / "07_mockup_ceramic_mug.jpg", thumbs_dir)
    make_08_mockup_acrylic_keychain(img_dir / "08_mockup_acrylic_keychain.jpg", thumbs_dir)
    make_09_how_to_personalize_guide(img_dir / "09_how_to_personalize_guide.jpg")
    make_10_whats_included_and_license(img_dir / "10_whats_included_and_license.jpg")

    desc = (
        "Floral Split Monogram SVG Bundle - Complete Alphabet Letters A to Z, Numbers 0 to 9, and Ampersand &.\n\n"
        "Designed specifically for Cricut, Silhouette Studio, Glowforge laser cutting, and craft projects. "
        "Every single letter, number, and ampersand is 100% pre-welded with clean, smooth compound paths—no overlapping lines, "
        "no loose disjointed pieces, and zero weeding headaches!\n\n"
        "WHAT MAKES THIS BUNDLE SPECIAL:\n"
        "- TWO COMPLETE VERSIONS: You receive both Split Monograms (with open horizontal ribbons for custom name insertion) "
        "AND Full Botanical Initial Monograms (intact decorative letters perfect for single initial signs, mugs, and keychains).\n"
        "- 74 TOTAL DESIGNS: 26 Split Letters, 26 Botanical Letters, 10 Split Numbers, 10 Botanical Numbers, and 2 Ampersands.\n"
        "- MULTI-COLOR READY: Also includes 2-Layer SVG files for all split letters (allowing you to cut contrasting vinyl colors "
        "for the letter body vs. the delicate botanical leaves).\n"
        "- COMPREHENSIVE PDF TUTORIAL: Includes a 3-page guide with a full visual letter index, step-by-step Cricut Design Space instructions, "
        "and curated free Google Font pairing recommendations.\n\n"
        "WHAT YOU RECEIVE IN YOUR DOWNLOAD:\n"
        "1. 01_Split_Monograms_SVG_DXF_EPS.zip - All 37 split designs in SVG, 2-layer SVG, DXF, and EPS vector formats.\n"
        "2. 02_Full_Botanical_Monograms_SVG_DXF_EPS.zip - All 37 full botanical designs in SVG, DXF, and EPS vector formats.\n"
        "3. 03_Split_Monograms_PNG_300DPI.zip - 37 transparent background 300 DPI high-resolution PNG files.\n"
        "4. 04_Full_Botanical_Monograms_PNG_300DPI.zip - 37 transparent background 300 DPI high-resolution PNG files.\n"
        "5. Monogram_Crafting_Guide_And_Font_Pairings.pdf - Step-by-step Cricut & Silhouette tutorial, font pairings, and commercial license.\n\n"
        "PERFECT FOR CREATING:\n"
        "- Personalized canvas tote bags, bridal party gifts, and wedding robes\n"
        "- Custom round wooden nursery signs, door hangers, and wall plaques\n"
        "- Monogram ceramic coffee mugs, insulated tumblers, and water bottles\n"
        "- Clear acrylic keychains, bag tags, and luggage identifiers\n"
        "- Family surname doormats, porch signs, and holiday pillows\n"
        "- Birthday milestone shirts, anniversary decor, and graduation 2027 gifts\n\n"
        "COMPATIBILITY:\n"
        "- Cricut Design Space (SVG)\n"
        "- Silhouette Studio (Basic Edition uses DXF; Designer / Business Edition uses SVG)\n"
        "- Glowforge & Laser Cutters (SVG / DXF)\n"
        "- Brother ScanNCut (SVG)\n"
        "- Adobe Illustrator, Inkscape, CorelDraw (SVG / EPS)\n"
        "- Sublimation & Direct-To-Film (PNG)\n\n"
        "COMMERCIAL LICENSE:\n"
        "- Small business commercial use is included up to 500 physical units per design.\n"
        "- You may sell physical items created with these cut files.\n"
        "- You MAY NOT resell, share, redistribute, or upload the raw digital files to Print-On-Demand sites.\n\n"
        "DIGITAL DOWNLOAD - No physical product will be shipped. Your files will be available for instant download upon payment confirmation."
    )

    data = lst.write_listing(
        root,
        title=TITLE,
        tags=TAGS,
        description=desc,
        price_usd=PRICE,
        sale_hint=f"list ${LIST_PRICE:.2f}, run a 60% sale to show discount",
        category="Craft Supplies & Tools > Patterns & How To > Digital",
        materials="svg, dxf, eps, png, cut files, digital download",
        whats_in_the_files=[
            "26 Split Monograms + 26 Full Botanical Monograms (Letters A-Z)",
            "10 Split Numbers + 10 Full Botanical Numbers (0-9) + 2 Ampersands",
            "74 SVGs + 37 2-Layer SVGs + 74 DXFs + 74 EPSs",
            "74 High-Resolution 300 DPI Transparent PNGs (3600px+)",
            "3-Page Cricut Personalization Guide & Font Pairings PDF"
        ],
        notes=["All monogram letters and botanical geometries are 100% original shop vectors."]
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
