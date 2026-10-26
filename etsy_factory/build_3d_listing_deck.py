"""Universal 3D Listing Deck Builder replicating the exact proven architecture of:
F:\\WORKHORSE\\workspace\\etsy_listings\\highland_cow_sublimation_clipart_png
and etsy_factory.clipart.build_listing.

Cards Layout (10 Cards Exactly):
01_cover.jpg             : cover2.vibrant (tilted colorful card collage, 3D ribbons, 3D gold number, 3D title, starburst, 5 badges)
02_cover_grid.jpg        : grid_cover (solid 540px dark ink header, giant white Anton, bold accent sub, full pack grid, bottom machine strip)
03_preview_1.jpg         : M.sheet (part 1 preview, big Anton title + Pacifico subtitle, white rounded cards with drop shadows)
04_preview_2.jpg         : M.sheet (part 2 preview, big Anton title + Pacifico subtitle, white rounded cards with drop shadows)
05_mockup_cluster.jpg    : Full-bleed ComfyUI photorealistic hero cluster
06_mockup_feature_1.jpg  : Full-bleed ComfyUI photorealistic lifestyle showcase #1
07_mockup_feature_2.jpg  : Full-bleed ComfyUI photorealistic lifestyle showcase #2
08_specs_settings.jpg    : M.info_card (Print settings & Slicer guide: solid dark header, vibrant 520px pills, 78pt Anton, 52pt Poppins)
09_whats_included.jpg    : M.info_card (What's in your download: solid dark header, vibrant 520px pills, 78pt Anton, 52pt Poppins)
10_license.jpg           : M.info_card (Commercial license: solid dark header, vibrant 520px pills, 78pt Anton, 52pt Poppins)
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import cover2, media as M

SIZE = M.SIZE


def make_thumbs_from_renders(meta: List[Dict], renders_dir: Path, thumbs_dir: Path) -> None:
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    for m in meta:
        file_key = m["file"]
        # Try graded comfy, comfy, then raw
        candidates = [
            renders_dir / f"graded_comfy_{file_key}",
            renders_dir / f"comfy_{file_key}",
            renders_dir / file_key
        ]
        src = next((c for c in candidates if c.exists()), None)
        if src:
            im = Image.open(src).convert("RGBA")
            bb = im.getbbox()
            if bb:
                im = im.crop(bb)
            im.thumbnail((540, 540), Image.LANCZOS)
            bg = Image.new("RGBA", (im.width + 30, im.height + 30), (255, 255, 255, 255))
            bg.alpha_composite(im, (15, 15))
            rgb = bg.convert("RGB")
            rgb.save(thumbs_dir / f"{m['name']}.png")
            rgb.save(thumbs_dir / f"{m['name']}_c.png")


def grid_cover_3d(meta: List[Dict], thumbs_dir: Path, out: Path, n: int, kicker: str, sub: str, accent, ink, bg,
                  strip_text: str = "100% WATERTIGHT  *  ZERO SUPPORTS  *  SLICER READY  *  COMMERCIAL USE",
                  cols: int = 5, rows: int = 2) -> Path:
    S = SIZE
    base = Image.new("RGBA", (S, S), bg + (255,))
    d = ImageDraw.Draw(base)

    top, pad = 620, 60
    gw = (S - 2 * pad - (cols - 1) * 35) // cols
    gh = (S - top - 180 - (rows - 1) * 35) // rows

    for i, m in enumerate(meta[:cols * rows]):
        r, c = divmod(i, cols)
        x = pad + c * (gw + 35)
        y = top + r * (gh + 35)

        card = M.rounded((gw, gh), 36, (255, 255, 255, 255), outline=ink + (50,), width=3)
        M.shadowed(base, card, (x, y), blur=14, off=(0, 8), alpha=70)

        tp = thumbs_dir / f"{m['name']}_c.png"
        if not tp.exists():
            tp = thumbs_dir / f"{m['name']}.png"
        if tp.exists():
            im = Image.open(tp).convert("RGBA")
            s = min((gw - 40) / im.width, (gh - 40) / im.height)
            tw, th = max(1, int(im.width * s)), max(1, int(im.height * s))
            im_s = im.resize((tw, th), Image.LANCZOS)
            base.paste(im_s, (x + (gw - tw) // 2, y + (gh - th) // 2), im_s)

    # Top solid dark ink header block
    d.rectangle((0, 0, S, 540), fill=ink)
    fk = M.fit(d, kicker.upper() + " 3D PACK", M.anton, S - 260, 180, 80)
    d.text((S // 2, 65), kicker.upper() + " 3D PACK", font=fk, fill=(255, 255, 255), anchor="ma")
    fn = M.fit(d, f"{n} PRINT-READY STL DESIGNS", M.anton, S - 320, 150, 70)
    d.text((S // 2, 65 + fk.size + 18), f"{n} PRINT-READY STL DESIGNS", font=fn, fill=accent if sum(accent) > 200 else (255, 214, 0), anchor="ma")
    fsub = M.fit(d, sub, M.pacifico, S - 400, 68, 32)
    d.text((S // 2, 65 + fk.size + fn.size + 30), sub, font=fsub, fill=(255, 255, 255, 220), anchor="ma")

    # Bottom machine strip
    fs = M.fit(d, strip_text, M.poppins_x, S - 260, 56, 26)
    sw = M.text_w(d, strip_text, fs)
    base.alpha_composite(M.rounded((sw + 100, 100), 50, ink + (255,)), (S // 2 - (sw + 100) // 2, S - 145))
    d.text((S // 2, S - 95), strip_text, font=fs, fill=(255, 255, 255), anchor="mm")

    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def preview_sheet_3d(meta: List[Dict], thumbs_dir: Path, out: Path, title: str, subtitle: str,
                     accent, ink, bg, start: int = 0, count: int = 5) -> Path:
    S = SIZE
    base = Image.new("RGBA", (S, S), bg + (255,))
    d = ImageDraw.Draw(base)

    # Title Block matching M.sheet exactly
    ft = M.fit(d, title.upper(), M.anton, S - 240, 150, 70)
    d.text((S // 2, 70), title.upper(), font=ft, fill=ink, anchor="ma")
    fs = M.fit(d, subtitle, M.pacifico, S - 400, 74, 36)
    d.text((S // 2, 70 + ft.size + 18), subtitle, font=fs, fill=accent, anchor="ma")

    top = 70 + ft.size + fs.size + 80
    gw, gh = 680, 840
    gap = 45

    sub_items = meta[start:start + count]
    row1 = sub_items[:3]
    row2 = sub_items[3:5]

    for row_idx, r_items in enumerate([row1, row2]):
        if not r_items:
            continue
        w_row = len(r_items) * gw + (len(r_items) - 1) * gap
        start_x = (S - w_row) // 2
        y = top + 20 + row_idx * (gh + gap)

        for c, m in enumerate(r_items):
            x = start_x + c * (gw + gap)
            card = M.rounded((gw, gh), 40, (255, 255, 255, 255), outline=ink + (50,), width=3)
            M.shadowed(base, card, (x, y), blur=16, off=(0, 10), alpha=75)

            tp = thumbs_dir / f"{m['name']}_c.png"
            if not tp.exists():
                tp = thumbs_dir / f"{m['name']}.png"
            if tp.exists():
                im = Image.open(tp).convert("RGBA")
                s = min((gw - 60) / im.width, 600 / im.height)
                tw, th = max(1, int(im.width * s)), max(1, int(im.height * s))
                im_s = im.resize((tw, th), Image.LANCZOS)
                base.paste(im_s, (x + (gw - tw) // 2, y + 30 + (600 - th) // 2), im_s)

            dc = ImageDraw.Draw(base)
            fn_t = M.fit(dc, m["title"].upper(), M.anton, gw - 60, 48, 26)
            dc.text((x + gw // 2, y + gh - 95), m["title"].upper(), font=fn_t, fill=ink, anchor="mm")
            fn_d = M.fit(dc, m.get("dims", ""), M.poppins_x, gw - 60, 30, 18)
            dc.text((x + gw // 2, y + gh - 45), m.get("dims", ""), font=fn_d, fill=accent, anchor="mm")

    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def build_desk_organizers_exact():
    root = Path(r"F:\WORKHORSE\workspace\etsy_listings\desk_organizers_stl")
    renders = root / "work_renders"
    thumbs = root / "_work" / "thumbs"
    imgs = root / "images"
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()

    items = [
        {"name": "01_Round_Pen_Cup", "title": "Round Pen Cup", "dims": "80 x 80 x 95 mm", "file": "single_01.png"},
        {"name": "02_Hex_Pen_Cup", "title": "Hex Pen Cup", "dims": "94 x 82 x 95 mm", "file": "single_02.png"},
        {"name": "03_Square_Pencil_Holder", "title": "Square Pencil Holder", "dims": "80 x 80 x 100 mm", "file": "single_03.png"},
        {"name": "04_Phone_Stand", "title": "Phone Stand", "dims": "100 x 70 x 94 mm", "file": "single_04.png"},
        {"name": "05_Cable_Clips_x4", "title": "Cable Clips x4", "dims": "142 x 25 x 14 mm", "file": "single_05.png"},
        {"name": "06_Business_Card_Holder", "title": "Card Holder", "dims": "98 x 38 x 20 mm", "file": "single_06.png"},
        {"name": "07_Sticky_Note_Tray", "title": "Sticky Note Tray", "dims": "86 x 86 x 22 mm", "file": "single_07.png"},
        {"name": "08_4-Compartment_Desk_Tray", "title": "4-Compartment Tray", "dims": "184 x 124 x 42 mm", "file": "single_08.png"},
        {"name": "09_Pen_and_Pencil_Tray", "title": "Pen & Pencil Tray", "dims": "196 x 46 x 24 mm", "file": "single_09.png"},
        {"name": "10_Desk_Dish", "title": "Desk Valet Dish", "dims": "80 x 80 x 16 mm", "file": "single_10.png"},
    ]
    n = len(items)

    print("Step 1: Preparing thumbs...")
    make_thumbs_from_renders(items, renders, thumbs)

    # Color Palette matching highland cow / sarcasm high-contrast vibrancy
    ribbon_cols = [
        ((255, 90, 45), (170, 45, 15)),   # Vibrant Terracotta / Coral
        ((0, 168, 180), (0, 100, 110))    # Electric Teal
    ]
    vbg = (24, 32, 54)                    # Deep midnight navy
    bg = (255, 248, 238)                  # Warm sunny cream
    ink = (22, 26, 34)                    # Deep midnight ink
    accent = (255, 90, 45)                # Coral
    r1 = (0, 168, 180)                    # Teal
    hot_pink = (255, 64, 129)

    multi_pill_colors = [
        (255, 90, 45),   # Coral
        (0, 168, 180),   # Electric Teal
        (255, 64, 129),  # Hot Pink
        (46, 160, 90),   # Emerald Green
        (255, 183, 3),   # Warm Honey Gold
        (123, 82, 180),  # Royal Purple
    ]

    badges = [
        ("STL", "100% Watertight\nZero Errors", (0, 168, 180)),
        ("PRINT", "100% Support-Free\nFlat Bed Base", (255, 90, 45)),
        ("CAD", "Millimeter\nAccurate Fit", (123, 82, 180)),
        ("SLICER", "Bambu Prusa\nCreality Ready", (46, 160, 90)),
        ("COMM", "Commercial License\nIncluded", (255, 183, 3))
    ]

    print("Step 2: Building 01_cover.jpg via cover2.vibrant...")
    cover2.vibrant(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "01_cover.jpg",
        big="10",
        kicker="MODERN WORKSPACE SUITE",
        title_lines=["DESK ORGANIZERS", "3D PRINT STL BUNDLE"],
        sub="PHONE STAND * PEN CUPS * CABLE CLIPS * DESK TRAYS",
        ribbon_cols=ribbon_cols,
        ink=ink,
        bg=vbg,
        badges=badges,
        burst=("INSTANT", "DOWNLOAD"),
        seed=12
    )

    print("Step 3: Building 02_cover_grid.jpg via grid_cover_3d...")
    grid_cover_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "02_cover_grid.jpg",
        n=n,
        kicker="10 DESK ORGANIZERS",
        sub="Modular Office Organization Suite * Slicer Ready",
        accent=accent,
        ink=ink,
        bg=bg,
        strip_text="BAMBU LAB * PRUSA * CREALITY * ANY SLICER",
        cols=5,
        rows=2
    )

    print("Step 4: Building 03_preview_1.jpg & 04_preview_2.jpg via preview_sheet_3d...")
    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "03_preview_1.jpg",
        title="Desk Cups & Phone Dock",
        subtitle="organize pens, styluses & phone at 65-degrees",
        accent=accent,
        ink=ink,
        bg=bg,
        start=0,
        count=5
    )

    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "04_preview_2.jpg",
        title="Cable Clips & Modular Trays",
        subtitle="cord management, Post-it pad dock & catchall dishes",
        accent=r1,
        ink=ink,
        bg=bg,
        start=5,
        count=5
    )

    print("Step 5: Building ComfyUI Photorealistic Mockup Cards (05, 06, 07)...")
    # 05: Hero Cluster Full-Bleed
    p_hero = renders / "graded_comfy_cluster_hero.png"
    if not p_hero.exists(): p_hero = renders / "comfy_cluster_hero.png"
    if p_hero.exists():
        im = Image.open(p_hero).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "05_mockup_cluster.jpg", quality=94, subsampling=0)

    # 06: Phone Stand Lifestyle
    p_phone = renders / "graded_comfy_single_04.png"
    if not p_phone.exists(): p_phone = renders / "comfy_single_04.png"
    if p_phone.exists():
        im = Image.open(p_phone).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "06_mockup_phone_stand.jpg", quality=94, subsampling=0)

    # 07: Hex & Round Cups Lifestyle
    p_cups = renders / "graded_comfy_single_02.png"
    if not p_cups.exists(): p_cups = renders / "comfy_single_02.png"
    if p_cups.exists():
        im = Image.open(p_cups).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "07_mockup_pen_cups.jpg", quality=94, subsampling=0)

    print("Step 6: Building Large-Font M.info_card Pages (08, 09, 10)...")
    # 08: Slicer & Print Settings
    M.info_card(
        out=imgs / "08_specs_settings.jpg",
        title="Recommended Print Settings",
        kicker="optimized fdm 3d printing",
        rows=[
            ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
            ("LAYER HEIGHT", "0.20 mm standard / 0.28 mm draft for rapid prints"),
            ("WALL LOOPS", "4 to 6 perimeters (2.4mm) for rigid, sturdy sidewalls"),
            ("INFILL", "15% to 20% Gyroid pattern for balanced strength and speed"),
            ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar bed contact at Z=0"),
            ("MATERIALS", "Matte PLA recommended for desk aesthetics; PETG for extra toughness")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic.",
        pill_colors=multi_pill_colors
    )

    # 09: What's in Your Download
    M.info_card(
        out=imgs / "09_whats_included.jpg",
        title="What's in your download",
        kicker="instant digital download",
        rows=[
            ("10 STL FILES", "Watertight binary STL files with millimeter scaling (1 file per organizer)"),
            ("SLICER READY", "Drag-and-drop into Bambu Studio, OrcaSlicer, PrusaSlicer, or Cura"),
            ("MODULAR FIT", "Coordinated heights and depths create neat, nesting desktop grids"),
            ("FLAT BED BASE", "Engineered planar first layer contact at Z=0 - zero brim or raft needed"),
            ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document")
        ],
        accent=r1,
        ink=ink,
        bg=bg,
        footer="Desk_Organizers_STL.zip (10 Solid STL Files) + Print_Guide_and_License.pdf",
        pill_colors=multi_pill_colors
    )

    # 10: Commercial License
    M.info_card(
        out=imgs / "10_license.jpg",
        title="Commercial use included",
        kicker="small business friendly",
        rows=[
            ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
            ("UNLIMITED", "Sell as many physical organizers as you make - no recurring royalties ever"),
            ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
            ("ORIGINAL", "100% original WORKHORSE functional designs - watertight guaranteed"),
            ("HELP", "Message the shop anytime if you need assistance with slicing or printing")
        ],
        accent=hot_pink,
        ink=ink,
        bg=bg,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE.",
        pill_colors=multi_pill_colors
    )

    made = sorted(imgs.glob("[0-9][0-9]_*.jpg"))
    print("Generated all 10 cards for Desk Organizers:", [p.name for p in made])


def build_can_holders_exact():
    root = Path(r"F:\WORKHORSE\workspace\etsy_listings\can_holders_stl")
    renders = root / "work_renders"
    thumbs = root / "_work" / "thumbs"
    imgs = root / "images"
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()

    items = [
        {"name": "01_QuadGrip_4-Cup_Drink_Caddy", "title": "QuadGrip 4-Cup Caddy", "dims": "189 x 189 x 165 mm", "file": "single_01.png"},
        {"name": "02_DuoCaddy_2-Can_Carrier_with_Handle", "title": "DuoCaddy 2-Can Carrier", "dims": "162 x 76 x 138 mm", "file": "single_02.png"},
        {"name": "03_HexaCool_Diamond_Insulated_Can_Cooler", "title": "HexaCool Diamond Cooler", "dims": "79 x 79 x 98 mm", "file": "single_03.png"},
        {"name": "04_SlimGrip_Honeycomb_Can_Cooler", "title": "SlimGrip Honeycomb Cooler", "dims": "68 x 67 x 105 mm", "file": "single_04.png"},
        {"name": "05_TrailLock_Carabiner_Adventure_Holster", "title": "TrailLock Adventure Holster", "dims": "97 x 80 x 98 mm", "file": "single_05.png"},
        {"name": "06_DualDrive_Stepped_Car_Cupholder_Expander", "title": "DualDrive Cup Expander", "dims": "90 x 90 x 127 mm", "file": "single_06.png"},
        {"name": "07_Titan_16oz_Tallboy_Can_Chiller", "title": "Titan 16oz Tallboy Chiller", "dims": "78 x 78 x 126 mm", "file": "single_07.png"},
        {"name": "08_FlipBase_Anti-Tip_Beverage_Stabilizer", "title": "FlipBase Anti-Tip Stabilizer", "dims": "112 x 112 x 42 mm", "file": "single_08.png"},
    ]
    n = len(items)

    print("Step 1: Preparing thumbs for Can Holders...")
    make_thumbs_from_renders(items, renders, thumbs)

    ribbon_cols = [
        ((0, 168, 230), (0, 95, 150)),   # Vibrant Electric Cyan
        ((255, 110, 40), (160, 50, 15))   # Flame Orange
    ]
    vbg = (18, 30, 48)                    # Deep midnight blue
    bg = (255, 248, 238)                  # Warm sunny cream
    ink = (20, 26, 36)                    # Deep ink
    accent = (255, 110, 40)               # Flame orange
    r1 = (0, 168, 230)                    # Cyan

    multi_pill_colors = [
        (255, 110, 40),  # Flame Orange
        (0, 168, 230),   # Electric Cyan
        (255, 64, 129),  # Hot Pink
        (46, 160, 90),   # Emerald Green
        (255, 183, 3),   # Warm Honey Gold
        (123, 82, 180),  # Royal Purple
    ]

    badges = [
        ("STL", "100% Watertight\nZero Errors", (0, 168, 230)),
        ("PRINT", "100% Support-Free\nFlat Bed Base", (255, 110, 40)),
        ("FIT", "Standard & Slim Cans\n12oz & 16oz", (123, 82, 180)),
        ("SLICER", "Bambu Prusa\nCreality Ready", (46, 160, 90)),
        ("COMM", "Commercial License\nIncluded", (255, 183, 3))
    ]

    print("Step 2: Building 01_cover.jpg via cover2.vibrant...")
    cover2.vibrant(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "01_cover.jpg",
        big="8",
        kicker="MODERN BEVERAGE UTILITY",
        title_lines=["CAN HOLDERS & CADDIES", "3D PRINT STL BUNDLE"],
        sub="4-CUP CADDY * INSULATED COOLERS * CAR EXPANDER * CARABINER HOLSTER",
        ribbon_cols=ribbon_cols,
        ink=ink,
        bg=vbg,
        badges=badges,
        burst=("INSTANT", "DOWNLOAD"),
        seed=15
    )

    print("Step 3: Building 02_cover_grid.jpg via grid_cover_3d...")
    grid_cover_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "02_cover_grid.jpg",
        n=n,
        kicker="8 CAN HOLDERS & CADDIES",
        sub="Modular Beverage Utility Suite * Slicer Ready",
        accent=accent,
        ink=ink,
        bg=bg,
        strip_text="BAMBU LAB * PRUSA * CREALITY * ANY SLICER",
        cols=4,
        rows=2
    )

    print("Step 4: Building 03_preview_1.jpg & 04_preview_2.jpg via preview_sheet_3d...")
    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "03_preview_1.jpg",
        title="Drink Caddies & Can Coolers",
        subtitle="quad caddy, twin carrier & tactile insulated sleeves",
        accent=accent,
        ink=ink,
        bg=bg,
        start=0,
        count=4
    )

    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "04_preview_2.jpg",
        title="Adapters & Adventure Holsters",
        subtitle="car cupholder expander, carabiner holster & tallboy chiller",
        accent=r1,
        ink=ink,
        bg=bg,
        start=4,
        count=4
    )

    print("Step 5: Building Lifestyle Mockup Cards (05, 06, 07)...")
    p_hero = renders / "cluster_hero.png"
    if p_hero.exists():
        im = Image.open(p_hero).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "05_mockup_cluster.jpg", quality=94, subsampling=0)

    p_coolers = renders / "single_03.png"
    if p_coolers.exists():
        im = Image.open(p_coolers).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "06_mockup_coolers.jpg", quality=94, subsampling=0)

    p_caddy = renders / "single_01.png"
    if p_caddy.exists():
        im = Image.open(p_caddy).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "07_mockup_caddy.jpg", quality=94, subsampling=0)

    print("Step 6: Building Large-Font M.info_card Pages (08, 09, 10)...")
    M.info_card(
        out=imgs / "08_specs_settings.jpg",
        title="Recommended Print Settings",
        kicker="optimized fdm 3d printing",
        rows=[
            ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
            ("LAYER HEIGHT", "0.20 mm standard / 0.28 mm draft for rapid prints"),
            ("WALL LOOPS", "4 to 6 perimeters (2.4mm) for rugged structural durability"),
            ("INFILL", "15% to 20% Gyroid pattern for maximum impact resistance"),
            ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar bed contact at Z=0"),
            ("MATERIALS", "PETG recommended for automotive/outdoor heat; PLA for desk use")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic.",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "09_whats_included.jpg",
        title="What's in your download",
        kicker="instant digital download",
        rows=[
            ("8 STL FILES", "Watertight binary STL files with millimeter scaling (1 file per design)"),
            ("SLICER READY", "Drag-and-drop into Bambu Studio, OrcaSlicer, PrusaSlicer, or Cura"),
            ("UNIVERSAL FIT", "Fits standard 12oz cans, 12oz slim cans, 16oz tallboys, and travel cups"),
            ("FLAT BED BASE", "Engineered planar first layer contact at Z=0 - zero brim or raft needed"),
            ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document")
        ],
        accent=r1,
        ink=ink,
        bg=bg,
        footer="Can_Holders_STL.zip (8 Solid STL Files) + Print_Guide_and_License.pdf",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "10_license.jpg",
        title="Commercial use included",
        kicker="small business friendly",
        rows=[
            ("YES", "Sell physical 3D prints in your Etsy shop, craft markets and retail stores"),
            ("UNLIMITED", "Sell as many physical holders as you make - no recurring royalties ever"),
            ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
            ("ORIGINAL", "100% original WORKHORSE functional designs - watertight guaranteed"),
            ("HELP", "Message the shop anytime if you need assistance with slicing or printing")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE.",
        pill_colors=multi_pill_colors
    )

    made = sorted(imgs.glob("[0-9][0-9]_*.jpg"))
    print("Generated all 10 cards for Can Holders:", [p.name for p in made])


def build_keychains_exact():
    root = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl")
    renders = root / "work_renders"
    thumbs = root / "_work" / "thumbs"
    imgs = root / "images"
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()

    items = [
        {"name": "01_Baby_Crystal_Dragon_Keychain", "title": "Baby Crystal Dragon", "dims": "52 x 42 x 34 mm", "file": "single_01.png"},
        {"name": "02_Chubby_Kawaii_Axolotl_Keychain", "title": "Kawaii Axolotl", "dims": "48 x 56 x 42 mm", "file": "single_02.png"},
        {"name": "03_Kawaii_Baby_Octopus_Keychain", "title": "Kawaii Baby Octopus", "dims": "46 x 44 x 42 mm", "file": "single_03.png"},
        {"name": "04_Geometric_French_Bulldog_Keychain", "title": "Geometric Frenchie", "dims": "50 x 38 x 36 mm", "file": "single_04.png"},
        {"name": "05_Pirate_Skull_Keychain", "title": "Pirate Captain Skull", "dims": "54 x 48 x 46 mm", "file": "single_05.png"},
        {"name": "06_Retro_HighTop_Sneaker_Keychain", "title": "Retro High-Top Sneaker", "dims": "48 x 62 x 26 mm", "file": "single_06.png"},
        {"name": "07_Lucky_Maneki_Neko_Keychain", "title": "Lucky Maneki Neko", "dims": "50 x 42 x 38 mm", "file": "single_07.png"},
        {"name": "08_Chibi_Astronaut_Keychain", "title": "Chibi Space Astronaut", "dims": "52 x 40 x 34 mm", "file": "single_08.png"},
    ]
    n = len(items)

    print("Step 1: Preparing thumbs for Keychains...")
    make_thumbs_from_renders(items, renders, thumbs)

    ribbon_cols = [
        ((255, 64, 129), (160, 20, 80)),  # Hot Pink / Magenta
        ((0, 168, 180), (0, 100, 110))    # Electric Teal
    ]
    vbg = (46, 14, 84)                    # Deep royal purple
    bg = (255, 248, 238)                  # Warm sunny cream
    ink = (22, 26, 34)                    # Deep ink
    accent = (255, 64, 129)               # Hot pink
    r1 = (0, 168, 180)                    # Teal

    multi_pill_colors = [
        (255, 64, 129),  # Hot Pink
        (0, 168, 180),   # Electric Teal
        (255, 183, 3),   # Warm Honey Gold
        (46, 160, 90),   # Emerald Green
        (123, 82, 180),  # Royal Purple
        (255, 90, 45),   # Coral
    ]

    badges = [
        ("STL", "100% Watertight\nZero Errors", (0, 168, 180)),
        ("PRINT", "Built-In Eyelet\nFlat Bed Base", (255, 64, 129)),
        ("FDM", "Bambu Prusa\nCreality Ready", (123, 82, 180)),
        ("SMOOTH", "Ultra Clean Mesh\nZero Artifacts", (46, 160, 90)),
        ("COMM", "Commercial License\nIncluded", (255, 183, 3))
    ]

    print("Step 2: Building 01_cover.jpg via cover2.vibrant...")
    cover2.vibrant(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "01_cover.jpg",
        big="8",
        kicker="CUTE & SCULPTED 3D PACK",
        title_lines=["SCULPTED KEYCHAINS", "3D PRINT STL BUNDLE"],
        sub="BABY DRAGON * AXOLOTL * OCTOPUS * FRENCHIE * PIRATE SKULL",
        ribbon_cols=ribbon_cols,
        ink=ink,
        bg=vbg,
        badges=badges,
        burst=("INSTANT", "DOWNLOAD"),
        seed=14
    )

    print("Step 3: Building 02_cover_grid.jpg via grid_cover_3d...")
    grid_cover_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "02_cover_grid.jpg",
        n=n,
        kicker="8 SCULPTED KEYCHAINS",
        sub="Cute Animal & Character Keyrings * Slicer Ready",
        accent=accent,
        ink=ink,
        bg=bg,
        strip_text="BAMBU LAB * PRUSA * CREALITY * ANY SLICER",
        cols=4,
        rows=2
    )

    print("Step 4: Building 03_preview_1.jpg & 04_preview_2.jpg via preview_sheet_3d...")
    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "03_preview_1.jpg",
        title="Kawaii Animals & Creatures",
        subtitle="crystal dragon, chubby axolotl, baby octopus & faceted frenchie",
        accent=accent,
        ink=ink,
        bg=bg,
        start=0,
        count=4
    )

    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "04_preview_2.jpg",
        title="Sculpted Characters & Icons",
        subtitle="pirate captain skull, retro sneaker, lucky cat & space astronaut",
        accent=r1,
        ink=ink,
        bg=bg,
        start=4,
        count=4
    )

    print("Step 5: Building ComfyUI Photorealistic Mockup Cards (05, 06, 07)...")
    p_hero = renders / "graded_comfy_cluster_hero.png"
    if not p_hero.exists(): p_hero = renders / "comfy_cluster_hero.png"
    if p_hero.exists():
        im = Image.open(p_hero).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "05_mockup_cluster.jpg", quality=94, subsampling=0)

    p_dragon = renders / "graded_comfy_single_01.png"
    if not p_dragon.exists(): p_dragon = renders / "comfy_single_01.png"
    if p_dragon.exists():
        im = Image.open(p_dragon).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "06_mockup_dragon.jpg", quality=94, subsampling=0)

    p_octopus = renders / "graded_comfy_single_03.png"
    if not p_octopus.exists(): p_octopus = renders / "comfy_single_03.png"
    if p_octopus.exists():
        im = Image.open(p_octopus).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "07_mockup_octopus.jpg", quality=94, subsampling=0)

    print("Step 6: Building Large-Font M.info_card Pages (08, 09, 10)...")
    M.info_card(
        out=imgs / "08_specs_settings.jpg",
        title="Recommended Print Settings",
        kicker="optimized fdm 3d printing",
        rows=[
            ("NOZZLE", "0.4 mm standard (0.2 mm nozzle for ultra micro detail)"),
            ("LAYER HEIGHT", "0.12 mm fine / 0.16 mm standard for silky curved surfaces"),
            ("WALL LOOPS", "3 to 4 perimeters (1.6mm) for rigid keychain drop strength"),
            ("INFILL", "20% to 30% Gyroid infill ensures rugged everyday durability"),
            ("KEYRING EYELET", "Solid 4mm integrated loop engineered for standard keyrings"),
            ("MATERIALS", "Silk PLA, Matte PLA, or PETG for vibrant pocket durability")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic.",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "09_whats_included.jpg",
        title="What's in your download",
        kicker="instant digital download",
        rows=[
            ("8 STL FILES", "Watertight high-density binary STL files with millimeter scaling"),
            ("SLICER READY", "Drag-and-drop into Bambu Studio, OrcaSlicer, PrusaSlicer, or Cura"),
            ("1:1 MATCH", "100% exact match between listing imagery and download files"),
            ("BUILT-IN LOOP", "Reinforced 4mm keyring eyelet integrated directly into the mesh"),
            ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document")
        ],
        accent=r1,
        ink=ink,
        bg=bg,
        footer="Keychains_STL.zip (8 Solid STL Files) + Print_Guide_and_License.pdf",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "10_license.jpg",
        title="Commercial use included",
        kicker="small business friendly",
        rows=[
            ("YES", "Sell physical 3D printed keychains in your Etsy shop and craft fairs"),
            ("UNLIMITED", "Sell as many physical keychains as you print - no recurring royalties"),
            ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
            ("ORIGINAL", "100% original WORKHORSE sculpted designs - watertight guaranteed"),
            ("HELP", "Message the shop anytime if you need assistance with slicing or printing")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE.",
        pill_colors=multi_pill_colors
    )

    made = sorted(imgs.glob("[0-9][0-9]_*.jpg"))
    print("Generated all 10 cards for Keychains:", [p.name for p in made])


def build_christmas_cookie_cutters_exact():
    root = Path(r"F:\WORKHORSE\workspace\etsy_listings\christmas_cookie_cutters_stl")
    renders = root / "work_renders"
    thumbs = root / "_work" / "thumbs"
    imgs = root / "images"
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()

    items = [
        {"name": "01_Christmas_Tree_Cutter", "title": "Christmas Tree", "dims": "60mm & 80mm + Press Plate", "file": "single_01.png"},
        {"name": "02_Star_Cutter", "title": "Golden Star", "dims": "60mm & 80mm + Press Plate", "file": "single_02.png"},
        {"name": "03_Snowflake_Cutter", "title": "Intricate Snowflake", "dims": "60mm & 80mm + Press Plate", "file": "single_03.png"},
        {"name": "04_Gingerbread_Man_Cutter", "title": "Gingerbread Man", "dims": "60mm & 80mm + Press Plate", "file": "single_04.png"},
        {"name": "05_Candy_Cane_Cutter", "title": "Holiday Candy Cane", "dims": "60mm & 80mm + Press Plate", "file": "single_05.png"},
        {"name": "06_Bauble_Ornament_Cutter", "title": "Bauble Ornament", "dims": "60mm & 80mm + Press Plate", "file": "single_06.png"},
        {"name": "07_Mitten_Cutter", "title": "Cozy Mitten", "dims": "60mm & 80mm + Press Plate", "file": "single_07.png"},
        {"name": "08_Stocking_Cutter", "title": "Holiday Stocking", "dims": "60mm & 80mm + Press Plate", "file": "single_08.png"},
        {"name": "09_Jingle_Bell_Cutter", "title": "Jingle Bell", "dims": "60mm & 80mm + Press Plate", "file": "single_09.png"},
        {"name": "10_Snowman_Cutter", "title": "Winter Snowman", "dims": "60mm & 80mm + Press Plate", "file": "single_10.png"},
    ]
    n = len(items)

    print("Step 1: Preparing thumbs for Christmas Cookie Cutters...")
    make_thumbs_from_renders(items, renders, thumbs)

    ribbon_cols = [
        ((196, 40, 48), (120, 18, 28)),   # Crimson Holiday Red
        ((30, 120, 92), (14, 72, 54))     # Forest Pine Green
    ]
    vbg = (26, 62, 56)                    # Deep pine forest background
    bg = (255, 248, 236)                  # Warm sunny cream
    ink = (36, 28, 26)                    # Deep warm ink
    accent = (196, 40, 48)                # Holiday Red
    r1 = (30, 120, 92)                    # Pine Green

    multi_pill_colors = [
        (196, 40, 48),   # Crimson Holiday Red
        (30, 120, 92),   # Pine Green
        (255, 183, 3),   # Warm Honey Gold
        (123, 82, 180),  # Royal Purple
        (255, 90, 45),   # Terracotta
        (0, 168, 180),   # Electric Teal
    ]

    badges = [
        ("STL", "100% Watertight\nZero Errors", (30, 120, 92)),
        ("PRINT", "Clean Cutting Edge\nComfort Flange", (196, 40, 48)),
        ("PRESS", "Includes Matching\nPress Plates", (255, 183, 3)),
        ("SIZES", "2 Sizes Included\n60mm & 80mm", (123, 82, 180)),
        ("COMM", "Commercial License\nIncluded", (46, 160, 90))
    ]

    print("Step 2: Building 01_cover.jpg via cover2.vibrant...")
    cover2.vibrant(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "01_cover.jpg",
        big="10",
        kicker="HOLIDAY BAKING & CLAY",
        title_lines=["CHRISTMAS COOKIE CUTTERS", "3D PRINT STL & 3MF BUNDLE"],
        sub="TREE * STAR * SNOWFLAKE * GINGERBREAD * CANDY CANE * SNOWMAN",
        ribbon_cols=ribbon_cols,
        ink=ink,
        bg=vbg,
        badges=badges,
        burst=("2 SIZES", "EACH"),
        seed=25
    )

    print("Step 3: Building 02_cover_grid.jpg via grid_cover_3d...")
    grid_cover_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "02_cover_grid.jpg",
        n=n,
        kicker="10 CHRISTMAS COOKIE CUTTERS",
        sub="10 Designs * 2 Sizes (60mm & 80mm) + Matching Press Plates",
        accent=accent,
        ink=ink,
        bg=bg,
        strip_text="BAMBU LAB * PRUSA * CREALITY * ANY SLICER",
        cols=5,
        rows=2
    )

    print("Step 4: Building 03_preview_1.jpg & 04_preview_2.jpg via preview_sheet_3d...")
    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "03_preview_1.jpg",
        title="Holiday Shapes & Characters",
        subtitle="tree, star, snowflake, gingerbread man & candy cane",
        accent=accent,
        ink=ink,
        bg=bg,
        start=0,
        count=5
    )

    preview_sheet_3d(
        meta=items,
        thumbs_dir=thumbs,
        out=imgs / "04_preview_2.jpg",
        title="Winter Ornaments & Icons",
        subtitle="bauble ornament, cozy mitten, stocking, bell & snowman",
        accent=r1,
        ink=ink,
        bg=bg,
        start=5,
        count=5
    )

    print("Step 5: Building ComfyUI Photorealistic Mockup Cards (05, 06, 07)...")
    p_hero = renders / "graded_comfy_hero_baking_cluster.png"
    if not p_hero.exists(): p_hero = renders / "comfy_hero_baking_cluster.png"
    if not p_hero.exists(): p_hero = renders / "cluster_hero.png"
    if p_hero.exists():
        im = Image.open(p_hero).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "05_mockup_cluster.jpg", quality=94, subsampling=0)

    p_press = renders / "graded_comfy_cutter_and_press_action.png"
    if not p_press.exists(): p_press = renders / "comfy_cutter_and_press_action.png"
    if p_press.exists():
        im = Image.open(p_press).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "06_mockup_press_action.jpg", quality=94, subsampling=0)

    p_sizes = renders / "graded_comfy_two_sizes_snowflake.png"
    if not p_sizes.exists(): p_sizes = renders / "comfy_two_sizes_snowflake.png"
    if p_sizes.exists():
        im = Image.open(p_sizes).convert("RGB")
        im = ImageOps.fit(im, (SIZE, SIZE))
        im.save(imgs / "07_mockup_two_sizes.jpg", quality=94, subsampling=0)

    print("Step 6: Building Large-Font M.info_card Pages (08, 09, 10)...")
    M.info_card(
        out=imgs / "08_specs_settings.jpg",
        title="Recommended Print Settings",
        kicker="optimized fdm 3d printing",
        rows=[
            ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
            ("LAYER HEIGHT", "0.20 mm standard / 0.16 mm fine for razor cutting taper"),
            ("WALL LOOPS", "3 to 4 perimeters (1.2 - 1.6mm) for rigid cutting pressure"),
            ("INFILL", "15% to 20% Gyroid infill - wide base flange carries all load"),
            ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar flange at Z=0"),
            ("FOOD CONTACT", "Print with food-grade PLA/PETG; ideal for dough, clay & fondant")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Compatible with Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic.",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "09_whats_included.jpg",
        title="What's in your download",
        kicker="instant digital download",
        rows=[
            ("30 STL FILES", "10 designs x 2 sizes (60mm & 80mm) + 10 matching press plates"),
            ("10 3MF PLATES", "Pre-arranged Bambu Studio & OrcaSlicer multi-part print plates"),
            ("COMFORT FLANGE", "Ergonomic 5mm rounded top lip protects hands while pressing"),
            ("0.8MM BLADE", "Engineered tapered cutting edge slices cleanly through dough"),
            ("PDF GUIDE", "Complete visual print guide, dimension table, and commercial license document")
        ],
        accent=r1,
        ink=ink,
        bg=bg,
        footer="Christmas_Cookie_Cutters_STL.zip + Christmas_Cookie_Cutters_3MF.zip + Guide.pdf",
        pill_colors=multi_pill_colors
    )

    M.info_card(
        out=imgs / "10_license.jpg",
        title="Commercial use included",
        kicker="small business friendly",
        rows=[
            ("YES", "Sell physical 3D printed cutters & stamps in your Etsy shop and craft fairs"),
            ("UNLIMITED", "Sell as many physical cutters as you print - no recurring royalties"),
            ("NO", "Reselling, sharing, or redistributing the digital STL files or bundles"),
            ("ORIGINAL", "100% original WORKHORSE functional designs - watertight guaranteed"),
            ("HELP", "Message the shop anytime if you need assistance with slicing or printing")
        ],
        accent=accent,
        ink=ink,
        bg=bg,
        footer="Sell physical prints freely. All digital files remain copyright WORKHORSE.",
        pill_colors=multi_pill_colors
    )

    made = sorted(imgs.glob("[0-9][0-9]_*.jpg"))
    print("Generated all 10 cards for Christmas Cookie Cutters:", [p.name for p in made])


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "desk_organizers"
    if target in ("desk_organizers", "all"):
        build_desk_organizers_exact()
    if target in ("can_holders", "all"):
        build_can_holders_exact()
    if target in ("keychains", "all"):
        build_keychains_exact()
    if target in ("cookie_cutters", "all"):
        build_christmas_cookie_cutters_exact()
