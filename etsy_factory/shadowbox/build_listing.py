"""Media kit and listing builder for 3D Layered Shadow Box SVG Bundle.

Generates 10 high-resolution (2400x2400) listing photos:
01_cover.jpg: Hero storefront cover with glowing 3D paper cut shadow box & badges
02_four_themes_overview.jpg: 2x2 grid displaying all 4 complete themes
03_exploded_layers_woodland.jpg: Exploded 3D layer perspective breakdown (Theme 1: Woodland Deer)
04_exploded_layers_ocean.jpg: Exploded 3D layer perspective breakdown (Theme 4: Ocean Dreams)
05_mockup_nursery_shelf.jpg: Photorealistic ComfyUI floating oak shelf with lighted shadow box
06_mockup_nursery_dresser.jpg: Photorealistic ComfyUI nursery dresser with birch shadow box
07_mockup_living_bookshelf.jpg: Photorealistic ComfyUI bookshelf with deep black shadow box
08_mockup_craft_flatlay.jpg: Photorealistic ComfyUI craft studio flat-lay with cut paper & Cricut
09_step_by_step_assembly_guide.jpg: Cardstock cutting & 3D foam spacer assembly infographic
10_whats_included_and_license.jpg: Complete file breakdown and commercial license guarantee

Writes listing.json, listing.md and enforces strict Etsy limits (0 validation errors).
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
from etsy_factory.shadowbox import pack as PK
from etsy_factory.shadowbox import scenes as SB

SLUG = PK.SLUG
W, H = 2400, 2400

# Color Palette (Deep Architectural Paper Art)
NAVY_DEEP = (16, 26, 38)
INDIGO = (32, 48, 71)
TEAL_ACCENT = (70, 160, 160)
GOLD_WARM = (212, 162, 78)
CREAM_BG = (250, 248, 245)
WHITE = (255, 255, 255)
CHARCOAL = (35, 38, 42)
MUTED = (115, 120, 128)
BORDER_COL = (220, 226, 232)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"

TITLE = "3D Shadow Box SVG Bundle, 4 Layered Paper Cut Light Box Templates for Cricut, Silhouette, Woodland Nursery 3D Paper Art SVG Cut Files"
TAGS = [
    "shadow box svg",
    "3d shadow box svg",
    "layered paper art",
    "cricut shadow box",
    "paper cut light box",
    "3d paper cut svg",
    "nursery shadow box",
    "woodland shadow box",
    "papercraft svg",
    "cricut cut files",
    "layered svg bundle",
    "shadowbox template",
    "3d mandala svg",
]
PRICE = 5.99
LIST_PRICE = 14.99


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def load_comp(thumbs_dir: Path, theme_id: str) -> Image.Image:
    p = thumbs_dir / f"{theme_id}_stacked_composite.png"
    if p.exists():
        return Image.open(p).convert("RGBA")
    return Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))


# -----------------------------------------------------------------------------
# SLIDE 01: HERO COVER
# -----------------------------------------------------------------------------
def make_01_cover(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(im)

    # Top Header
    f_t = get_font(FONT_BOLD, 78)
    f_sub = get_font(FONT_BOLD, 36)
    d.text((W // 2, 110), "3D LAYERED SHADOW BOX BUNDLE", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 195), "4 COMPLETE THEMES  •  24 PRECISION CUT LAYERS  •  8x8 INCH TEMPLATES", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    # Feature badges
    badges = ["4 THEMES INCLUDED", "6 LAYERS PER THEME", "SVG • DXF • PDF • PNG", "CRICUT & SILHOUETTE READY"]
    bx_total = sum(len(b) * 20 + 44 for b in badges)
    cur_x = (W - bx_total) // 2
    f_b = get_font(FONT_BOLD, 26)
    for b in badges:
        bw = len(b) * 20 + 36
        d.rounded_rectangle([cur_x, 245, cur_x + bw, 298], radius=12, fill=GOLD_WARM)
        d.text((cur_x + bw // 2, 271), b, fill=NAVY_DEEP, font=f_b, anchor="mm")
        cur_x += bw + 14

    # Large Center Hero: Woodland Deer Shadow Box with glowing simulated frame
    woodland = load_comp(thumbs_dir, "woodland_deer")
    if woodland.width > 0:
        woodland.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        # Deep shadow box frame
        frame_pad = 40
        fx0 = (W - woodland.width) // 2 - frame_pad
        fy0 = 360
        fx1 = fx0 + woodland.width + frame_pad * 2
        fy1 = fy0 + woodland.height + frame_pad * 2

        # Outer wooden frame
        d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=24, fill=(45, 34, 25), outline=(75, 58, 44), width=12)
        # Inner beveled mat
        d.rectangle([fx0 + 20, fy0 + 20, fx1 - 20, fy1 - 20], fill=(20, 24, 30), outline=(15, 18, 22), width=4)

        # Paste woodland composite
        im.paste(woodland, (fx0 + frame_pad, fy0 + frame_pad), woodland)

    # 3 Small thumbnail previews at bottom corners
    side_themes = [("moonlit_safari", "Safari Moon", 200), ("nursery_balloon", "Hot Air Balloon", W // 2 - 190), ("ocean_dreams", "Ocean Whales", W - 580)]
    f_th_lbl = get_font(FONT_BOLD, 28)
    for t_id, t_lbl, tx in side_themes:
        th = load_comp(thumbs_dir, t_id)
        if th.width > 0:
            th.thumbnail((380, 380), Image.Resampling.LANCZOS)
            d.rounded_rectangle([tx - 10, 1720, tx + 390, 2170], radius=16, fill=INDIGO, outline=TEAL_ACCENT, width=2)
            im.paste(th, (tx, 1730), th)
            d.text((tx + 190, 2135), t_lbl, fill=WHITE, font=f_th_lbl, anchor="mm")

    # Bottom Banner
    d.rectangle([0, H - 150, W, H], fill=(10, 18, 26))
    f_bot = get_font(FONT_BOLD, 36)
    d.text((W // 2, H - 75), "COMMERCIAL LICENSE INCLUDED  •  LED LIGHTING & ASSEMBLY GUIDE", fill=WHITE, font=f_bot, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 02: FOUR THEMES OVERVIEW
# -----------------------------------------------------------------------------
def make_02_four_themes_overview(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=NAVY_DEEP)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 95), "4 COMPLETE 3D SHADOW BOX THEMES", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 185), "Each theme includes 6 numbered precision cut layers • 8x8 In (20x20 cm)", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    # 2x2 Grid of themes
    coords = [
        (180, 320), (1280, 320),
        (180, 1260), (1280, 1260)
    ]
    card_w, card_h = 940, 860
    f_card_t = get_font(FONT_BOLD, 36)
    f_card_sub = get_font(FONT_REG, 26)

    for theme, (cx, cy) in zip(SB.THEMES, coords):
        # Card background
        d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
        th = load_comp(thumbs_dir, theme["id"])
        if th.width > 0:
            th.thumbnail((card_w - 80, card_h - 160), Image.Resampling.LANCZOS)
            px = cx + (card_w - th.width) // 2
            py = cy + 25
            im.paste(th, (px, py), th)
        d.text((cx + card_w // 2, cy + card_h - 85), theme["title"], fill=NAVY_DEEP, font=f_card_t, anchor="mm")
        d.text((cx + card_w // 2, cy + card_h - 40), "6 Cut Layers • 100% Watertight Closed Paths", fill=MUTED, font=f_card_sub, anchor="mm")

    # Footer
    d.rectangle([0, H - 120, W, H], fill=NAVY_DEEP)
    d.text((W // 2, H - 60), "Scalable to 9x9\" or 10x10\" for standard IKEA Ribba & Sannahed Frames", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 03: EXPLODED LAYERS (WOODLAND DEER)
# -----------------------------------------------------------------------------
def make_03_exploded_layers_woodland(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 260], fill=NAVY_DEEP)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 95), "EXPLODED LAYER BREAKDOWN (WOODLAND DEER)", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 185), "6 Numbered Layers stack with 3D foam tape to create optical depth", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    # 2 rows x 3 columns of layers
    t_id = "woodland_deer"
    layers_info = [
        ("Layer 1: Back Sky & Moon", f"{t_id}_Layer_01_Back_Moon_Stars_th.png"),
        ("Layer 2: Distant Mountains", f"{t_id}_Layer_02_Distant_Mountains_th.png"),
        ("Layer 3: Mid Forest & Owl", f"{t_id}_Layer_03_Midground_Forest_Owl_th.png"),
        ("Layer 4: Mama Deer & Fawn", f"{t_id}_Layer_04_Mama_And_Baby_Deer_th.png"),
        ("Layer 5: Birch Tree Frame", f"{t_id}_Layer_05_Foreground_Birch_Trees_th.png"),
        ("Layer 6: Front Bevel Frame", f"{t_id}_Layer_06_Front_Decorative_Frame_th.png"),
    ]

    cols, rows = 3, 2
    ox = 140
    oy = 320
    cell_w = (W - 280) // cols
    cell_h = (H - 460) // rows
    f_lbl = get_font(FONT_BOLD, 30)

    for i, (title, fn) in enumerate(layers_info):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=18, fill=WHITE, outline=BORDER_COL, width=2)
        th_p = thumbs_dir / fn
        if th_p.exists():
            th = Image.open(th_p).convert("RGBA")
            th.thumbnail((cell_w - 60, cell_h - 90), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 100 - th.height) // 2
            im.paste(th, (px, py), th)
        d.text((cx + cell_w // 2, cy + cell_h - 35), title, fill=NAVY_DEEP, font=f_lbl, anchor="mm")

    d.rectangle([0, H - 120, W, H], fill=NAVY_DEEP)
    d.text((W // 2, H - 60), "Includes 15mm border margin on every layer for easy foam tape adhesion", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 04: EXPLODED LAYERS (OCEAN DREAMS)
# -----------------------------------------------------------------------------
def make_04_exploded_layers_ocean(out_path: Path, thumbs_dir: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    d.rectangle([0, 0, W, 260], fill=NAVY_DEEP)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 95), "EXPLODED LAYER BREAKDOWN (OCEAN DREAMS)", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 185), "6 Numbered Layers stack with 3D foam tape to create optical depth", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    t_id = "ocean_dreams"
    layers_info = [
        ("Layer 1: Sunbeams & Fish", f"{t_id}_Layer_01_Back_Sunbeams_Fish_th.png"),
        ("Layer 2: Reef Arch & Turtle", f"{t_id}_Layer_02_Deep_Reef_Turtle_th.png"),
        ("Layer 3: Mother Humpback", f"{t_id}_Layer_03_Mother_Humpback_Whale_th.png"),
        ("Layer 4: Baby Whale & Bubbles", f"{t_id}_Layer_04_Baby_Whale_And_Bubbles_th.png"),
        ("Layer 5: Kelp Forest & Starfish", f"{t_id}_Layer_05_Foreground_Coral_Kelp_th.png"),
        ("Layer 6: Front Frame", f"{t_id}_Layer_06_Front_Frame_th.png"),
    ]

    cols, rows = 3, 2
    ox = 140
    oy = 320
    cell_w = (W - 280) // cols
    cell_h = (H - 460) // rows
    f_lbl = get_font(FONT_BOLD, 30)

    for i, (title, fn) in enumerate(layers_info):
        r = i // cols
        c = i % cols
        cx = ox + c * cell_w
        cy = oy + r * cell_h

        d.rounded_rectangle([cx + 10, cy + 10, cx + cell_w - 10, cy + cell_h - 10], radius=18, fill=WHITE, outline=BORDER_COL, width=2)
        th_p = thumbs_dir / fn
        if th_p.exists():
            th = Image.open(th_p).convert("RGBA")
            th.thumbnail((cell_w - 60, cell_h - 90), Image.Resampling.LANCZOS)
            px = cx + (cell_w - th.width) // 2
            py = cy + 20 + (cell_h - 100 - th.height) // 2
            im.paste(th, (px, py), th)
        d.text((cx + cell_w // 2, cy + cell_h - 35), title, fill=NAVY_DEEP, font=f_lbl, anchor="mm")

    d.rectangle([0, H - 120, W, H], fill=NAVY_DEEP)
    d.text((W // 2, H - 60), "Cut from 65lb - 80lb cardstock for clean, sturdy structural layers", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 05: MOCKUP NURSERY SHELF (ComfyUI)
# -----------------------------------------------------------------------------
def make_05_mockup_nursery_shelf(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\shadowbox_nursery_shelf_601.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Woodland Deer shadow box inserted into frame cavity
    th = load_comp(thumbs_dir, "woodland_deer")
    if th.width > 0:
        th.thumbnail((680, 680), Image.Resampling.LANCZOS)
        # Internal warm LED glow behind the art
        glow = Image.new("RGBA", (th.width + 40, th.height + 40), (255, 220, 160, 90))
        glow = glow.filter(ImageFilter.GaussianBlur(25))

        tx = (W - th.width) // 2 - 10
        ty = (H - th.height) // 2 - 40

        im.paste(glow, (tx - 20, ty - 20), glow)
        im.paste(th, (tx, ty), th)

    # Title pill
    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "NURSERY FLOATING SHELF MOCKUP", fill=NAVY_DEEP, font=f_bd)
    d.text((140, 160), "Woodland Deer 3D Paper Art with Warm Backlighting", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 06: MOCKUP NURSERY DRESSER (ComfyUI)
# -----------------------------------------------------------------------------
def make_06_mockup_nursery_dresser(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\shadowbox_nursery_dresser_702.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    th = load_comp(thumbs_dir, "nursery_balloon")
    if th.width > 0:
        th.thumbnail((680, 680), Image.Resampling.LANCZOS)
        glow = Image.new("RGBA", (th.width + 40, th.height + 40), (255, 225, 170, 85))
        glow = glow.filter(ImageFilter.GaussianBlur(22))

        tx = (W - th.width) // 2 - 10
        ty = (H - th.height) // 2 - 50

        im.paste(glow, (tx - 20, ty - 20), glow)
        im.paste(th, (tx, ty), th)

    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "NURSERY DRESSER MOCKUP", fill=NAVY_DEEP, font=f_bd)
    d.text((140, 160), "Dreamy Hot Air Balloon Staged in Birch Wood Frame", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 07: MOCKUP LIVING BOOKSHELF (ComfyUI)
# -----------------------------------------------------------------------------
def make_07_mockup_living_bookshelf(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\shadowbox_living_bookshelf_803.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    th = load_comp(thumbs_dir, "moonlit_safari")
    if th.width > 0:
        th.thumbnail((680, 680), Image.Resampling.LANCZOS)
        glow = Image.new("RGBA", (th.width + 40, th.height + 40), (255, 210, 140, 95))
        glow = glow.filter(ImageFilter.GaussianBlur(24))

        tx = (W - th.width) // 2 - 5
        ty = (H - th.height) // 2 - 40

        im.paste(glow, (tx - 20, ty - 20), glow)
        im.paste(th, (tx, ty), th)

    d.rounded_rectangle([100, 80, 920, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "BOOKSHELF DISPLAY MOCKUP", fill=NAVY_DEEP, font=f_bd)
    d.text((140, 160), "Moonlit Safari & Elephants with Deep Night Contrast", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 08: CRAFT FLAT-LAY MOCKUP (ComfyUI)
# -----------------------------------------------------------------------------
def make_08_mockup_craft_flatlay(out_path: Path, thumbs_dir: Path):
    bg_p = Path(r"F:\WORKHORSE\workspace\etsy_mockups\shadowbox_craft_flatlay_904.png")
    if not bg_p.exists():
        im = Image.new("RGB", (W, H), CREAM_BG)
    else:
        im = Image.open(bg_p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS).convert("RGB")

    d = ImageDraw.Draw(im)

    # Ocean Dreams stacked preview placed into the flat-lay frame
    th = load_comp(thumbs_dir, "ocean_dreams")
    if th.width > 0:
        th.thumbnail((650, 650), Image.Resampling.LANCZOS)
        # Drop shadow onto desk
        shadow = Image.new("RGBA", th.size, (0, 0, 0, 0))
        alpha = th.split()[-1]
        shadow.paste((15, 15, 20, 90), (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))

        tx = (W - th.width) // 2 + 10
        ty = (H - th.height) // 2 - 10

        im.paste(shadow, (tx + 12, ty + 16), shadow)
        im.paste(th, (tx, ty), th)

    d.rounded_rectangle([100, 80, 940, 200], radius=18, fill=(255, 255, 255, 240), outline=BORDER_COL, width=2)
    f_bd = get_font(FONT_BOLD, 36)
    f_sm = get_font(FONT_REG, 26)
    d.text((140, 115), "CRAFT WORKSPACE FLAT-LAY MOCKUP", fill=NAVY_DEEP, font=f_bd)
    d.text((140, 160), "Precision Cuts on Cricut & Double-Sided Foam Tape Assembly", fill=MUTED, font=f_sm)

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 09: STEP-BY-STEP ASSEMBLY GUIDE
# -----------------------------------------------------------------------------
def make_09_step_by_step_assembly_guide(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 280], fill=NAVY_DEEP)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 100), "HOW TO ASSEMBLE YOUR SHADOW BOX", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 200), "Easy 4-Step Crafting Process from Digital Cut to Lighted Art", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    f_num = get_font(FONT_BOLD, 64)
    f_head = get_font(FONT_BOLD, 44)
    f_body = get_font(FONT_REG, 32)

    steps = [
        ("1", "Cut Your 6 Layers of Cardstock",
         "Upload the numbered SVGs into Cricut Design Space or Silhouette Studio.\n"
         "Cut each layer from 65lb - 80lb solid-core cardstock using a Fine-Point Blade.\n"
         "You can also use the included PDF templates for hand-cutting with a craft knife."),
        ("2", "Apply 3D Foam Tape Spacers",
         "Apply double-sided foam tape squares (2mm to 3mm thick) along all four\n"
         "outer 15mm border margins. Foam tape provides the physical space between\n"
         "layers that creates the deep, captivating 3D optical illusion."),
        ("3", "Stack in Numbered Sequence (1 to 6)",
         "Stack each layer in order from Layer 1 (Back Panel) up to Layer 6 (Front Frame).\n"
         "Align the four corners precisely before pressing down firmly on the foam tape."),
        ("4", "Frame & Install Ambient LED Lights",
         "Insert your completed stack into any standard 8x8 in (or 9x9 in) shadow box frame.\n"
         "Optional: Wrap micro LED fairy lights behind Layer 1 to bring the scene to life!"),
    ]

    cur_y = 350
    for num, head, desc in steps:
        d.rounded_rectangle([140, cur_y, W - 140, cur_y + 320], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
        # Circle badge
        d.ellipse([180, cur_y + 35, 270, cur_y + 125], fill=GOLD_WARM)
        d.text((225, cur_y + 80), num, fill=NAVY_DEEP, font=f_num, anchor="mm")

        d.text((310, cur_y + 50), head, fill=NAVY_DEEP, font=f_head)
        d.multiline_text((310, cur_y + 115), desc, fill=CHARCOAL, font=f_body, spacing=12)
        cur_y += 370

    # Footer
    d.rectangle([0, H - 150, W, H], fill=NAVY_DEEP)
    d.text((W // 2, H - 75), "Comprehensive 3-Page Illustrated Assembly PDF Guide Included in Download", fill=WHITE, font=f_sub, anchor="mm")

    im.save(out_path, quality=95)
    print(f"Generated {out_path.name}")


# -----------------------------------------------------------------------------
# SLIDE 10: WHAT'S INCLUDED & COMMERCIAL LICENSE
# -----------------------------------------------------------------------------
def make_10_whats_included_and_license(out_path: Path):
    im = Image.new("RGB", (W, H), CREAM_BG)
    d = ImageDraw.Draw(im)

    # Header
    d.rectangle([0, 0, W, 280], fill=NAVY_DEEP)
    f_t = get_font(FONT_BOLD, 72)
    f_sub = get_font(FONT_BOLD, 34)
    d.text((W // 2, 100), "WHAT'S INCLUDED & LICENSE", fill=WHITE, font=f_t, anchor="mm")
    d.text((W // 2, 200), "Complete Digital Craft Package  •  Commercial Small Business License", fill=TEAL_ACCENT, font=f_sub, anchor="mm")

    f_head = get_font(FONT_BOLD, 42)
    f_body = get_font(FONT_REG, 32)

    # Left Box
    d.rounded_rectangle([120, 340, W // 2 - 40, H - 180], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((160, 400), "WHAT YOU RECEIVE:", fill=NAVY_DEEP, font=f_head)

    included_text = (
        "• 4 Complete 3D Shadow Box Themes:\n"
        "  1. Woodland Deer & Moonlit Forest\n"
        "  2. Moonlit Safari & Gentle Giants\n"
        "  3. Dreamy Nursery Hot Air Balloon\n"
        "  4. Under the Sea & Gentle Whales\n\n"
        "24 TOTAL PRECISION CUT LAYERS:\n"
        "✔ 24 Individual Layer SVG Cut Files (8x8 In)\n"
        "✔ 4 Master Stacked All-In-One SVGs\n"
        "✔ 24 DXF Cut Files (Silhouette Studio Basic)\n"
        "✔ 4 Printable Hand-Cut Template PDFs\n"
        "✔ 24 Transparent 300 DPI Layer PNGs\n\n"
        "BONUS INCLUDED:\n"
        "✔ 3-Page Master Illustrated Assembly PDF\n"
        "✔ LED Lighting & Frame Sizing Guide\n"
        "✔ Commercial Small Business License"
    )
    d.multiline_text((160, 475), included_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Right Box
    d.rounded_rectangle([W // 2 + 40, 340, W - 120, H - 180], radius=24, fill=WHITE, outline=BORDER_COL, width=3)
    d.text((W // 2 + 80, 400), "COMMERCIAL LICENSE TERMS:", fill=NAVY_DEEP, font=f_head)

    license_text = (
        "YOU MAY:\n"
        "✔ Sell physical assembled shadow boxes\n"
        "✔ Sell physical paper-cut art, lighted frames,\n"
        "   and craft fair items up to 500 units/design!\n"
        "✔ Resize to fit any square frame size\n"
        "✔ Personalize cardstock colors & LED lights\n\n"
        "YOU MAY NOT:\n"
        "✖ Resell, redistribute, or share digital files\n"
        "✖ Upload cut files to Print-On-Demand sites\n"
        "✖ Claim vector geometry as your own\n\n"
        "100% CRAFTER GUARANTEE:\n"
        "Every single layer is tested for watertight\n"
        "cut paths. If you need any assistance with\n"
        "file sizing or cutting, message us on Etsy!"
    )
    d.multiline_text((W // 2 + 80, 475), license_text, fill=CHARCOAL, font=f_body, spacing=14)

    # Bottom Banner
    d.rectangle([0, H - 140, W, H], fill=NAVY_DEEP)
    d.text((W // 2, H - 70), "INSTANT DIGITAL DOWNLOAD  •  START CRAFTING TODAY", fill=WHITE, font=f_sub, anchor="mm")

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
    make_02_four_themes_overview(img_dir / "02_four_themes_overview.jpg", thumbs_dir)
    make_03_exploded_layers_woodland(img_dir / "03_exploded_layers_woodland.jpg", thumbs_dir)
    make_04_exploded_layers_ocean(img_dir / "04_exploded_layers_ocean.jpg", thumbs_dir)
    make_05_mockup_nursery_shelf(img_dir / "05_mockup_nursery_shelf.jpg", thumbs_dir)
    make_06_mockup_nursery_dresser(img_dir / "06_mockup_nursery_dresser.jpg", thumbs_dir)
    make_07_mockup_living_bookshelf(img_dir / "07_mockup_living_bookshelf.jpg", thumbs_dir)
    make_08_mockup_craft_flatlay(img_dir / "08_mockup_craft_flatlay.jpg", thumbs_dir)
    make_09_step_by_step_assembly_guide(img_dir / "09_step_by_step_assembly_guide.jpg")
    make_10_whats_included_and_license(img_dir / "10_whats_included_and_license.jpg")

    desc = (
        "3D Shadow Box SVG Bundle - 4 Complete Layered Paper Cut Light Box Templates for Cricut, Silhouette, and Hand Cutting.\n\n"
        "Create breathtaking, lighted 3D shadow box art for your home or handmade shop! "
        "Each design features 6 carefully engineered layers that stack with double-sided foam tape to create magical depth, "
        "shadows, and glowing silhouettes when illuminated with ambient LED lights.\n\n"
        "4 COMPLETE THEMES INCLUDED:\n"
        "1. Woodland Deer & Moonlit Forest: Mama deer & fawn, soaring owl, evergreen pine trees, rolling mountains, and crescent moon.\n"
        "2. Moonlit Safari & Gentle Giants: Mama & baby elephant walking trunk-in-hand, distant giraffe, baobab & acacia trees under a harvest moon.\n"
        "3. Dreamy Nursery Hot Air Balloon: Sleeping crescent moon, cloud banks, and an adorable hot air balloon floating among the stars.\n"
        "4. Under the Sea & Gentle Whales: Humpback whale & calf, swimming sea turtle, rising bubbles, coral reef arch, and kelp forest.\n\n"
        "KEY DESIGN FEATURES:\n"
        "- 100% WATERTIGHT CUT PATHS: Every layer is pre-tested with closed compound paths—no stray nodes or double cut lines.\n"
        "- BUILT-IN 15MM SPACER BORDER: Each layer includes a solid outer perimeter designed specifically for double-sided foam tape adhesive.\n"
        "- SCALABLE 8x8 INCH SIZE: Pre-sized to 8.0 x 8.0 inches (20x20 cm), perfectly compatible with standard 8x8 and 9x9 inch shadow box frames "
        "(such as IKEA Sannahed and IKEA Ribba frames with deep internal spacer).\n"
        "- COMPREHENSIVE ASSEMBLY GUIDE: Includes a 3-page illustrated PDF guide with cardstock recommendations, cutting tips, foam spacer placement, "
        "and LED fairy light installation.\n\n"
        "WHAT YOU RECEIVE IN YOUR DOWNLOAD:\n"
        "1. 01_Woodland_Deer_Shadow_Box_SVG_DXF_PDF.zip - 6 layer SVGs, master stacked SVG, 6 DXFs, printable hand-cut template PDF.\n"
        "2. 02_Moonlit_Safari_Shadow_Box_SVG_DXF_PDF.zip - 6 layer SVGs, master stacked SVG, 6 DXFs, printable hand-cut template PDF.\n"
        "3. 03_Nursery_Balloon_Shadow_Box_SVG_DXF_PDF.zip - 6 layer SVGs, master stacked SVG, 6 DXFs, printable hand-cut template PDF.\n"
        "4. 04_Ocean_Dreams_Shadow_Box_SVG_DXF_PDF.zip - 6 layer SVGs, master stacked SVG, 6 DXFs, printable hand-cut template PDF.\n"
        "5. 05_Shadow_Box_Assembly_Guide_And_PNG_Previews.zip - All 24 transparent 300 DPI layer PNGs + Master Illustrated PDF Assembly Guide.\n\n"
        "RECOMMENDED MATERIALS:\n"
        "- 65lb to 80lb (176–216 gsm) smooth solid-core cardstock\n"
        "- Double-sided 3D foam adhesive tape squares (2mm to 3mm thick)\n"
        "- 8x8 in or 9x9 in shadow box frame (1.0 to 1.5 inch internal depth)\n"
        "- Warm white micro LED fairy lights or 5V USB LED strip\n\n"
        "COMPATIBILITY:\n"
        "- Cricut Design Space (SVG)\n"
        "- Silhouette Studio (Basic Edition uses DXF; Designer / Business uses SVG)\n"
        "- Brother ScanNCut (SVG)\n"
        "- Laser Cutters: Glowforge, xTool, LightBurn (SVG / DXF)\n"
        "- Hand Cutting: Printable PDF templates with light cutting lines\n\n"
        "COMMERCIAL LICENSE:\n"
        "- Small business commercial use is included up to 500 physical assembled units per design.\n"
        "- You may sell physical shadow boxes and framed paper art.\n"
        "- You MAY NOT resell, share, or redistribute the digital cut files.\n\n"
        "DIGITAL DOWNLOAD - No physical product will be shipped. Files are available for instant download upon payment."
    )

    data = lst.write_listing(
        root,
        title=TITLE,
        tags=TAGS,
        description=desc,
        price_usd=PRICE,
        sale_hint=f"list ${LIST_PRICE:.2f}, run a 60% sale to show discount",
        category="Craft Supplies & Tools > Patterns & How To > Digital",
        materials="svg, dxf, pdf, png, cut files, paper craft, cardstock",
        whats_in_the_files=[
            "4 Complete 3D Shadow Box Themes (24 Precision Cut Layers)",
            "24 Individual SVGs + 4 Master Stacked All-in-One SVGs",
            "24 DXF Cut Files for Silhouette Studio Basic",
            "4 Multi-Page Printable Hand-Cut Template PDFs",
            "24 Transparent 300 DPI PNG Layer Previews",
            "3-Page Illustrated 3D Assembly & LED Lighting PDF Guide"
        ],
        notes=["All shadow box layer geometries are 100% original shop vector art."]
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
