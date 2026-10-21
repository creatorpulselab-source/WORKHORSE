"""
CraftyMyia Official Etsy Brand Generator
Creates:
1. Shop Icon / Avatar: 1000x1000 px (circle-safe)
2. Big Banner: 3360x840 px (Etsy standard 4:1)
3. Standard Banner: 1200x300 px (compact)
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = r"F:\WORKHORSE\workspace\brand_assets"
FONTS_DIR = r"F:\WORKHORSE\etsy_factory\fonts"
LISTINGS_DIR = r"F:\WORKHORSE\workspace\etsy_listings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Color Palette: Warm Modern Maker
BG_WARM = (255, 252, 248)       # #FFFCF8 - Creamy warm linen
INK_DARK = (34, 32, 30)          # #22201E - Rich charcoal black
ACCENT_CORAL = (226, 104, 79)    # #E2684F - Warm terracotta coral
ACCENT_TEAL = (52, 143, 140)     # #348F8C - Deep artisan teal
ACCENT_GOLD = (235, 175, 71)     # #EBAF47 - Warm honey maker gold
PILL_BG = (245, 240, 232)        # Soft paper pill background

def get_font(name, size):
    path = os.path.join(FONTS_DIR, name)
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_rounded_pill(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def draw_sparkle(draw, center, size, color):
    cx, cy = center
    r = size
    # Draw diamond/sparkle star
    pts = [
        (cx, cy - r),
        (cx + r * 0.28, cy - r * 0.28),
        (cx + r, cy),
        (cx + r * 0.28, cy + r * 0.28),
        (cx, cy + r),
        (cx - r * 0.28, cy + r * 0.28),
        (cx - r, cy),
        (cx - r * 0.28, cy - r * 0.28)
    ]
    draw.polygon(pts, fill=color)

# ==========================================
# 1. GENERATE SHOP ICON (1000 x 1000 px)
# ==========================================
def generate_shop_icon():
    print("Generating CraftyMyia Shop Icon (1000x1000)...")
    size = 1000
    img = Image.new("RGBA", (size, size), BG_WARM)
    draw = ImageDraw.Draw(img)

    # Subtle decorative circular border (circle-safe guide)
    center = (size // 2, size // 2)
    border_radius = 460
    draw.ellipse(
        [center[0] - border_radius, center[1] - border_radius, center[0] + border_radius, center[1] + border_radius],
        outline=(238, 230, 218),
        width=4
    )

    # Modern Stylized Monogram Badge in center
    badge_r = 180
    badge_box = [center[0] - badge_r, 160, center[0] + badge_r, 160 + 2 * badge_r]
    draw_rounded_pill(draw, badge_box, radius=badge_r, fill=ACCENT_CORAL)

    # Monogram letters "CM"
    f_mono = get_font("Anton-Regular.ttf", 190)
    mono_txt = "CM"
    mb = f_mono.getbbox(mono_txt)
    mw = mb[2] - mb[0]
    mh = mb[3] - mb[1]
    draw.text((center[0] - mw // 2, 160 + (2 * badge_r - mh) // 2 - 25), mono_txt, font=f_mono, fill=(255, 255, 255))

    # Sparkle accents on badge
    draw_sparkle(draw, (center[0] + badge_r - 20, 180), 30, ACCENT_GOLD)
    draw_sparkle(draw, (center[0] - badge_r + 25, 160 + 2 * badge_r - 20), 22, ACCENT_TEAL)

    # Main Brand Name: "CraftyMyia"
    f_brand = get_font("Anton-Regular.ttf", 115)
    brand_txt = "CRAFTYMYIA"
    bb = f_brand.getbbox(brand_txt)
    bw = bb[2] - bb[0]
    draw.text((center[0] - bw // 2, 570), brand_txt, font=f_brand, fill=INK_DARK)

    # Script Kicker: "Handcrafted Digital Goods"
    f_script = get_font("Pacifico-Regular.ttf", 46)
    if not hasattr(f_script, "getbbox"):
        f_script = get_font("AlexBrush-Regular.ttf", 52)
    script_txt = "Handcrafted Digital Goods"
    sb = f_script.getbbox(script_txt)
    sw = sb[2] - sb[0]
    draw.text((center[0] - sw // 2, 695), script_txt, font=f_script, fill=ACCENT_CORAL)

    # Bottom Maker Pill: "STL • SVG • 3MF"
    f_sub = get_font("BebasNeue-Regular.ttf", 36)
    sub_txt = "3D PRINTABLES  •  DIGITAL CRAFTS"
    sub_b = f_sub.getbbox(sub_txt)
    sub_w = sub_b[2] - sub_b[0]
    pill_w = sub_w + 60
    pill_h = 50
    pill_x = center[0] - pill_w // 2
    pill_y = 780
    draw_rounded_pill(draw, [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=25, fill=PILL_BG, outline=ACCENT_TEAL, width=2)
    draw.text((center[0] - sub_w // 2, pill_y + 8), sub_txt, font=f_sub, fill=INK_DARK)

    # Save Shop Icon
    out_path = os.path.join(OUTPUT_DIR, "craftymyia_shop_icon.png")
    img.convert("RGB").save(out_path, quality=95)
    print("Saved Shop Icon:", out_path)

# ==========================================
# 2. GENERATE BIG BANNER (3360 x 840 px)
# ==========================================
def generate_shop_banner():
    print("Generating CraftyMyia Big Banner (3360x840)...")
    W, H = 3360, 840
    img = Image.new("RGBA", (W, H), BG_WARM)
    draw = ImageDraw.Draw(img)

    # Subtle top & bottom decorative trim
    draw.rectangle([0, 0, W, 14], fill=ACCENT_CORAL)
    draw.rectangle([0, H - 14, W, H], fill=ACCENT_TEAL)

    # Load 4 Showcase Product Cards (2 on Left, 2 on Right)
    # Left Side: 3D Printing (Cookie Cutters & Desk Organizers)
    # Right Side: Digital Crafts (Laser Keychains & Highland Cow Sublimation)
    showcase_items = [
        (os.path.join(LISTINGS_DIR, "christmas_cookie_cutters_stl", "images", "01_cover.jpg"), 80, 110, 620),
        (os.path.join(LISTINGS_DIR, "can_holders_stl", "images", "01_cover.jpg"), 740, 110, 620),
        (os.path.join(LISTINGS_DIR, "highland_cow_sublimation_clipart_png", "images", "01_cover.jpg"), 2000, 110, 620),
        (os.path.join(LISTINGS_DIR, "cute_laser_cut_keychains_and_earrings_svg_bundle", "images", "01_cover.jpg"), 2660, 110, 620),
    ]

    for p, x, y, size in showcase_items:
        if os.path.exists(p):
            try:
                card = Image.open(p).convert("RGBA")
                card = card.resize((size, size), Image.Resampling.LANCZOS)
                
                # Make rounded corners
                mask = Image.new("L", (size, size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, size, size], radius=32, fill=255)
                
                # Shadow
                shadow = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
                sh_draw = ImageDraw.Draw(shadow)
                sh_draw.rounded_rectangle([15, 20, size + 25, size + 30], radius=36, fill=(0, 0, 0, 45))
                shadow = shadow.filter(ImageFilter.GaussianBlur(14))
                img.alpha_composite(shadow, (x - 20, y - 10))
                
                # Composite Card
                img.paste(card, (x, y), mask)
                # Subtle border
                border_im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                b_draw = ImageDraw.Draw(border_im)
                b_draw.rounded_rectangle([0, 0, size, size], radius=32, outline=(255, 255, 255, 220), width=4)
                img.alpha_composite(border_im, (x, y))
            except Exception as e:
                print(f"Error loading {p}: {e}")

    # ================= CENTER BRANDING =================
    center_x = W // 2  # 1680

    # Top Kicker: "WELCOME TO"
    f_kicker = get_font("BebasNeue-Regular.ttf", 44)
    k_txt = "W E L C O M E   T O"
    kb = f_kicker.getbbox(k_txt)
    kw = kb[2] - kb[0]
    draw.text((center_x - kw // 2, 110), k_txt, font=f_kicker, fill=ACCENT_CORAL)

    # Hero Brand Headline: "CRAFTYMYIA"
    f_hero = get_font("Anton-Regular.ttf", 168)
    h_txt = "CRAFTYMYIA"
    hb = f_hero.getbbox(h_txt)
    hw = hb[2] - hb[0]
    draw.text((center_x - hw // 2, 160), h_txt, font=f_hero, fill=INK_DARK)

    # Sparkles framing the brand
    draw_sparkle(draw, (center_x - hw // 2 - 50, 240), 38, ACCENT_GOLD)
    draw_sparkle(draw, (center_x + hw // 2 + 50, 240), 38, ACCENT_GOLD)

    # Cursive Subtitle
    f_script = get_font("Pacifico-Regular.ttf", 52)
    if not hasattr(f_script, "getbbox"):
        f_script = get_font("AlexBrush-Regular.ttf", 58)
    sub_txt = "Handcrafted 3D Printables & Digital Crafts"
    sb = f_script.getbbox(sub_txt)
    sw = sb[2] - sb[0]
    draw.text((center_x - sw // 2, 350), sub_txt, font=f_script, fill=ACCENT_TEAL)

    # Tagline Strip
    f_tag = get_font("BebasNeue-Regular.ttf", 40)
    tag_txt = "STLs  •  3MF  •  SVGs  •  LASER  •  SUBLIMATION"
    tb = f_tag.getbbox(tag_txt)
    tw = tb[2] - tb[0]
    draw.text((center_x - tw // 2, 445), tag_txt, font=f_tag, fill=INK_DARK)

    # 3 Trust Pills at Bottom of Center
    # Pill 1: "INSTANT DOWNLOAD"
    # Pill 2: "COMMERCIAL LICENSE INCLUDED"
    # Pill 3: "100% PRINT TESTED"
    pills = [
        ("INSTANT DIGITAL DOWNLOAD", ACCENT_TEAL),
        ("COMMERCIAL USE INCLUDED", ACCENT_CORAL),
        ("WATERTIGHT PRINT TESTED", (60, 130, 80))
    ]
    
    f_pill = get_font("BebasNeue-Regular.ttf", 34)
    total_pills_w = 0
    pill_dims = []
    for ptext, pcol in pills:
        pb = f_pill.getbbox(ptext)
        pw = pb[2] - pb[0] + 50
        ph = 56
        pill_dims.append((ptext, pcol, pw, ph, pb[2] - pb[0]))
        total_pills_w += pw + 20
    total_pills_w -= 20

    px = center_x - total_pills_w // 2
    py = 530
    for ptext, pcol, pw, ph, text_w in pill_dims:
        draw_rounded_pill(draw, [px, py, px + pw, py + ph], radius=28, fill=pcol)
        draw.text((px + (pw - text_w) // 2, py + 11), ptext, font=f_pill, fill=(255, 255, 255))
        px += pw + 20

    # Save Big Banner (3360 x 840)
    out_big = os.path.join(OUTPUT_DIR, "craftymyia_etsy_big_banner_3360x840.png")
    final_rgb = img.convert("RGB")
    final_rgb.save(out_big, quality=95)
    print("Saved Big Banner:", out_big)

    # Save Compact Banner (1200 x 300)
    out_comp = os.path.join(OUTPUT_DIR, "craftymyia_etsy_banner_1200x300.png")
    compact_im = final_rgb.resize((1200, 300), Image.Resampling.LANCZOS)
    compact_im.save(out_comp, quality=95)
    print("Saved Compact Banner:", out_comp)

if __name__ == "__main__":
    generate_shop_icon()
    generate_shop_banner()
