"""Build and test expert-level photorealistic mockups for Pack 8 using ComfyUI backdrops.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import sys

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory.typo import media as M

DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\cute_animal_sticker_sheets_printable_cut_files")
FILES = DIR / "files"
MOCK_DIR = Path(r"F:\WORKHORSE\workspace\etsy_mockups")
OUT_DIR = DIR / "images"

S = M.SIZE
INK = (35, 30, 45)
PURPLE = (120, 70, 180)
TEAL = (30, 140, 140)
PINK = (210, 80, 130)


def get_sticker(prefix: str) -> Image.Image:
    stk_dir = FILES / "01_Individual_Stickers" / "PNG_Transparent_300DPI"
    hits = list(stk_dir.glob(f"{prefix}_*.png"))
    if not hits:
        raise FileNotFoundError(f"Could not find sticker matching {prefix} in {stk_dir}")
    return Image.open(hits[0]).convert("RGBA")


def build_laptop_mockup():
    bg_path = MOCK_DIR / "laptop_topdown_777.png"
    bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "PERFECT FOR LAPTOPS, TABLETS & CASES", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "PERFECT FOR LAPTOPS, TABLETS & CASES", font=ft, fill=INK, anchor="ma")
    sub = "Print on vinyl sticker paper for vibrant, scratch-resistant custom tech art"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PURPLE, anchor="ma")

    # In laptop_topdown_777.png, the laptop lid is roughly:
    # x: 160 to 1960 (width ~ 1800), y: 580 to 1820 (height ~ 1240)
    # Let's place 4 cute stickers casually arranged across the lid with slight rotations and shadows
    stickers_to_place = [
        ("07_Fox", 420, 850, -12, 430),
        ("12_Panda", 980, 780, 8, 440),
        ("01_Cat", 1460, 950, -6, 420),
        ("10_Dino", 700, 1260, 10, 430),
        ("09_Frog", 1260, 1340, -9, 410)
    ]

    for prefix, sx, sy, rot, sz in stickers_to_place:
        stk = get_sticker(prefix)
        w, h = stk.size
        new_w = sz
        new_h = int(sz * h / w)
        stk_r = stk.resize((new_w, new_h), Image.LANCZOS)
        if rot != 0:
            stk_r = stk_r.rotate(rot, expand=True, resample=Image.BICUBIC)

        # Realistic contact drop shadow
        sh_layer = Image.new("RGBA", (stk_r.width + 40, stk_r.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_r.split()[3].point(lambda p: int(p * 0.45))
        sh_layer.paste((20, 20, 30, 255), (12, 14), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(14))

        base.alpha_composite(sh_layer, (sx - 20, sy - 20))
        base.alpha_composite(stk_r, (sx, sy))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Instant Download  •  300 DPI Transparent PNG  •  Cricut Cut Lines",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path = OUT_DIR / "04_mockup_laptop.jpg"
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    print("Saved:", out_path)
    return out_path


def build_water_bottle_mockup():
    bg_path = MOCK_DIR / "water_bottle_clean_888.png"
    bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "WATER BOTTLES & HYDROFLASKS", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "WATER BOTTLES & HYDROFLASKS", font=ft, fill=INK, anchor="ma")
    sub = "Add laminate over vinyl for 100% waterproof, dishwasher-safe tumblers"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=TEAL, anchor="ma")

    # In water_bottle_clean_888.png, the bottle body is centered:
    # x: roughly 780 to 1220 (width ~ 440)
    # y: roughly 700 to 1950
    # Let's place 2 stickers on the bottle: Frog & Lion
    bottle_stickers = [
        ("09_Frog", 820, 920, 360),
        ("11_Lion", 820, 1420, 360)
    ]

    for prefix, sx, sy, sz in bottle_stickers:
        stk = get_sticker(prefix)
        w, h = stk.size
        new_w = sz
        new_h = int(sz * h / w)
        stk_r = stk.resize((new_w, new_h), Image.LANCZOS)

        # Subtle cylindrical perspective squeeze (horizontal curvature)
        # We can apply a slight squeeze or curvature
        sq_w = int(new_w * 0.94)
        stk_curved = stk_r.resize((sq_w, new_h), Image.LANCZOS)

        # Realistic contact drop shadow
        sh_layer = Image.new("RGBA", (stk_curved.width + 40, stk_curved.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_curved.split()[3].point(lambda p: int(p * 0.40))
        sh_layer.paste((20, 20, 30, 255), (10, 12), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(12))

        # Adjust sx to center on bottle
        actual_x = 1000 - sq_w // 2
        base.alpha_composite(sh_layer, (actual_x - 20, sy - 20))
        base.alpha_composite(stk_curved, (actual_x, sy))

    # Also place 2 decorative stickers on the wooden table beside the bottle!
    # Left table: Dino, Right table: Cat
    table_stickers = [
        ("10_Dino", 320, 1720, -15, 380),
        ("02_Bunny", 1680, 1700, 12, 380)
    ]
    for prefix, sx, sy, rot, sz in table_stickers:
        stk = get_sticker(prefix)
        w, h = stk.size
        stk_r = stk.resize((sz, int(sz * h / w)), Image.LANCZOS)
        if rot != 0:
            stk_r = stk_r.rotate(rot, expand=True, resample=Image.BICUBIC)

        sh_layer = Image.new("RGBA", (stk_r.width + 40, stk_r.height + 40), (0, 0, 0, 0))
        sh_alpha = stk_r.split()[3].point(lambda p: int(p * 0.50))
        sh_layer.paste((15, 15, 20, 255), (10, 16), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(14))

        base.alpha_composite(sh_layer, (sx - 20, sy - 20))
        base.alpha_composite(stk_r, (sx, sy))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Die-Cut Outlines  •  White Bleed Halo  •  Precision Cut Contours",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path = OUT_DIR / "05_mockup_water_bottle.jpg"
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    print("Saved:", out_path)
    return out_path


def build_planner_mockup():
    bg_path = MOCK_DIR / "ipad_planner_clean_999.png"
    bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "DIGITAL PLANNERS & GOODNOTES", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "DIGITAL PLANNERS & GOODNOTES", font=ft, fill=INK, anchor="ma")
    sub = "Pre-cropped individual PNG stickers with soft realistic iPad drop shadows"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PINK, anchor="ma")

    # The iPad screen is angled roughly ~23 degrees.
    # We can place 4 digital planner stickers with soft iPad shadows right on the screen area
    # In ipad_planner_clean_999.png, the screen center is roughly (1150, 1300)
    screen_stickers = [
        ("02_Bunny", 880, 950, -18, 320),
        ("04_Cow", 1250, 920, 12, 330),
        ("12_Panda", 900, 1350, 8, 340),
        ("20_Unicorn", 1280, 1400, -14, 340)
    ]
    for prefix, sx, sy, rot, sz in screen_stickers:
        stk = get_sticker(prefix)
        w, h = stk.size
        stk_r = stk.resize((sz, int(sz * h / w)), Image.LANCZOS)
        if rot != 0:
            stk_r = stk_r.rotate(rot, expand=True, resample=Image.BICUBIC)

        sh_layer = Image.new("RGBA", (stk_r.width + 30, stk_r.height + 30), (0, 0, 0, 0))
        sh_alpha = stk_r.split()[3].point(lambda p: int(p * 0.35))
        sh_layer.paste((10, 15, 25, 255), (8, 10), mask=sh_alpha)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(10))

        base.alpha_composite(sh_layer, (sx - 15, sy - 15))
        base.alpha_composite(stk_r, (sx, sy))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "GoodNotes  •  Notability  •  Noteshelf  •  iPad & Android Compatible",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path = OUT_DIR / "06_mockup_planner.jpg"
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    print("Saved:", out_path)
    return out_path


def build_craft_sheet_mockup():
    bg_path = MOCK_DIR / "desk_craft_sheet_315.png"
    bg = Image.open(bg_path).convert("RGB").resize((S, S), Image.LANCZOS)
    base = bg.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Header Card
    pill = M.rounded((1800, 220), 40, (255, 255, 255, 230), outline=(210, 210, 225, 255), width=3)
    M.shadowed(base, pill, ((S - 1800) // 2, 70), blur=20, off=(0, 10), alpha=80)
    ft = M.fit(d, "PRINT AT HOME STICKER SHEETS", M.anton, 1700, 100, 50)
    d.text((S // 2, 110), "PRINT AT HOME STICKER SHEETS", font=ft, fill=INK, anchor="ma")
    sub = "Print on glossy or matte sticker paper • Cut with scissors or craft machine"
    fs = M.fit(d, sub, M.poppins_x, 1650, 42, 24)
    d.text((S // 2, 110 + ft.size + 10), sub, font=fs, fill=PINK, anchor="ma")

    # In desk_craft_sheet_315.png, the center craft area has a large empty pink/beige mat
    # We place a printed sheet (e.g. Sheet 1: Kawaii Pets & Farm) slightly rotated (-3 degrees)
    sheet_path = FILES / "02_Printable_Sheets" / "PNG_Sheets_300DPI" / "Sheet_01_kawaii_pets_US_Letter_PrintReady.png"
    sheet_im = Image.open(sheet_path).convert("RGBA")
    
    # Target size on the desk: width ~ 1100 px, height ~ 1420 px
    sh_w = 1080
    sh_h = int(sh_w * sheet_im.height / sheet_im.width)
    sheet_scaled = sheet_im.resize((sh_w, sh_h), Image.LANCZOS)
    
    # White border around printed sheet + realistic paper shadow
    sheet_frame = Image.new("RGBA", (sh_w + 16, sh_h + 16), (255, 255, 255, 255))
    sheet_frame.paste(sheet_scaled, (8, 8), mask=sheet_scaled.split()[3])
    
    rot = -3
    sheet_rot = sheet_frame.rotate(rot, expand=True, resample=Image.BICUBIC)

    # Paper drop shadow
    sh_layer = Image.new("RGBA", (sheet_rot.width + 60, sheet_rot.height + 60), (0, 0, 0, 0))
    sh_alpha = sheet_rot.split()[3].point(lambda p: int(p * 0.45))
    sh_layer.paste((15, 15, 25, 255), (20, 24), mask=sh_alpha)
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(18))

    place_x = (S - sheet_rot.width) // 2 + 60
    place_y = 660
    base.alpha_composite(sh_layer, (place_x - 30, place_y - 30))
    base.alpha_composite(sheet_rot, (place_x, place_y))

    # Footer banner
    footer_pill = M.rounded((1400, 86), 43, (255, 255, 255, 235), outline=(210, 210, 225, 255), width=2)
    M.shadowed(base, footer_pill, ((S - 1400) // 2, S - 150), blur=14, off=(0, 8), alpha=70)
    d.text((S // 2, S - 108), "Ready to Print  •  US Letter & A4 Sizes  •  PDF & PNG Formats",
           font=M.poppins_x(32), fill=INK, anchor="mm")

    out_path = OUT_DIR / "07_mockup_desk_sheet.jpg"
    base.convert("RGB").save(out_path, quality=94, subsampling=0)
    print("Saved:", out_path)
    return out_path


if __name__ == "__main__":
    build_laptop_mockup()
    build_water_bottle_mockup()
    build_planner_mockup()
    build_craft_sheet_mockup()
