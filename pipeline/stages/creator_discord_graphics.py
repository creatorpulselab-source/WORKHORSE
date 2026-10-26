import pathlib
import re
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance


def _clean_text(s: str) -> str:
    # Strip Astral-plane Unicode emojis that standard TrueType fonts render as tofu boxes
    cleaned = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]", "", s).strip()
    return re.sub(r"\s{2,}", " ", cleaned)


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\impact.ttf" if bold and size >= 52 else "",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        if c and pathlib.Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _get_ui_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        if pathlib.Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _smart_crop_portrait(img_path: pathlib.Path, target_w: int, target_h: int, top_bias: float = 0.15) -> Image.Image:
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        src_w, src_h = im.size
        target_ratio = target_w / target_h
        src_ratio = src_w / src_h
        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            im = im.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            top = int((src_h - new_h) * top_bias)
            im = im.crop((0, top, src_w, top + new_h))
        im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
        im = ImageEnhance.Contrast(im).enhance(1.06)
        im = ImageEnhance.Color(im).enhance(1.08)
        return im


def _create_luxury_banner(
    photo_path: pathlib.Path,
    eyebrow: str,
    title_line1: str,
    title_line2: str,
    subtitle: str,
    pills: List[str],
    accent_rgb: Tuple[int, int, int] = (236, 72, 153),
    secondary_rgb: Tuple[int, int, int] = (0, 242, 254),
    width: int = 1920,
    height: int = 720,
    top_bias: float = 0.12,
) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (11, 7, 20, 255))

    bg_photo = _smart_crop_portrait(photo_path, width, height, top_bias=0.25)
    bg_blur = bg_photo.filter(ImageFilter.GaussianBlur(radius=42))
    bg_dark = ImageEnhance.Brightness(bg_blur).enhance(0.28)
    canvas.paste(bg_dark.convert("RGBA"), (0, 0))

    portrait_w = int(width * 0.46)
    portrait = _smart_crop_portrait(photo_path, portrait_w, height, top_bias=top_bias).convert("RGBA")
    mask = Image.new("L", (portrait_w, height), 255)
    mask_draw = ImageDraw.Draw(mask)
    fade_w = int(portrait_w * 0.42)
    for x in range(fade_w):
        alpha = int(255 * (x / fade_w) ** 1.4)
        mask_draw.line([(x, 0), (x, height)], fill=alpha)
    canvas.paste(portrait, (width - portrait_w, 0), mask)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((-180, -180, 720, 620), fill=(*accent_rgb, 55))
    gdraw.ellipse((int(width * 0.35), height - 320, int(width * 0.75), height + 220), fill=(*secondary_rgb, 45))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=65))
    canvas = Image.alpha_composite(canvas, glow)

    draw = ImageDraw.Draw(canvas)

    draw.rectangle([0, 0, width, 6], fill=(*accent_rgb, 255))
    draw.rectangle([0, height - 6, width, height], fill=(*secondary_rgb, 255))
    draw.rounded_rectangle(
        [28, 28, width - 28, height - 28],
        radius=22,
        outline=(*accent_rgb, 110),
        width=2,
    )

    left_x = 84
    y = 86

    eyebrow_clean = "•  " + _clean_text(eyebrow) + "  •"
    f_eye = _get_ui_font(22, bold=True)
    eye_bbox = draw.textbbox((0, 0), eyebrow_clean, font=f_eye)
    eye_w = (eye_bbox[2] - eye_bbox[0]) + 44
    eye_h = 48
    draw.rounded_rectangle(
        [left_x, y, left_x + eye_w, y + eye_h],
        radius=24,
        fill=(*accent_rgb, 58),
        outline=(*accent_rgb, 230),
        width=2,
    )
    draw.text((left_x + 22, y + 10), eyebrow_clean, font=f_eye, fill=(255, 255, 255, 255))
    y += eye_h + 28

    f_h1 = _get_font(78, bold=True)
    draw.text((left_x + 3, y + 4), title_line1, font=f_h1, fill=(0, 0, 0, 190))
    draw.text((left_x, y), title_line1, font=f_h1, fill=(255, 255, 255, 255))
    y += 90

    draw.text((left_x + 3, y + 4), title_line2, font=f_h1, fill=(0, 0, 0, 190))
    draw.text((left_x, y), title_line2, font=f_h1, fill=(*secondary_rgb, 255))
    y += 98

    f_sub = _get_ui_font(27, bold=False)
    draw.text((left_x, y), _clean_text(subtitle), font=f_sub, fill=(230, 220, 245, 255))
    y += 64

    f_pill = _get_ui_font(21, bold=True)
    px = left_x
    for p_raw in pills:
        p_text = "• " + _clean_text(p_raw)
        pb = draw.textbbox((0, 0), p_text, font=f_pill)
        pw = (pb[2] - pb[0]) + 36
        ph = 46
        if px + pw > int(width * 0.62):
            px = left_x
            y += ph + 14
        draw.rounded_rectangle(
            [px, y, px + pw, y + ph],
            radius=12,
            fill=(22, 14, 38, 230),
            outline=(*secondary_rgb, 195),
            width=2,
        )
        draw.text((px + 18, y + 9), p_text, font=f_pill, fill=(255, 255, 255, 255))
        px += pw + 14

    return canvas.convert("RGB")


def generate_charlette_webb_graphics(
    downloads_dir: str = r"C:\Users\User\Downloads",
    output_dir: str = r"F:\WORKHORSE\workspace\client_deliveries\charlette_webb_community_kit",
) -> Dict[str, str]:
    dl = pathlib.Path(downloads_dir)
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    p_blue1 = dl / "Charlette_Webb_Blue_1.jpg"
    p_blue2 = dl / "Charlette_Webb_Blue_2.jpg"
    p_green1 = dl / "Charlette_Webb_Green_1.jpg"
    p_school1 = dl / "Charlette_Webb_SchoolGirl_1.jpg"
    p_school2 = dl / "Charlette_Webb_SchoolGirl_2.jpg"
    p_teaser = dl / "JT2A6127_teaser_preview.jpg"

    generated = {}
    avatar_src = p_teaser if p_teaser.exists() else p_school1

    # 1. Circular Server & Telegram Avatar (1000x1000)
    av_crop = _smart_crop_portrait(avatar_src, 1000, 1000, top_bias=0.05).convert("RGBA")
    av_draw = ImageDraw.Draw(av_crop)
    av_draw.ellipse([8, 8, 992, 992], outline=(255, 30, 142, 255), width=16)
    av_draw.ellipse([24, 24, 976, 976], outline=(0, 242, 254, 230), width=6)
    av_draw.rounded_rectangle([140, 820, 860, 935], radius=55, fill=(18, 8, 32, 240), outline=(255, 30, 142, 255), width=5)
    f_av = _get_ui_font(46, bold=True)
    txt = "CHARLETTE WEBB VIP"
    tb = av_draw.textbbox((0, 0), txt, font=f_av)
    av_draw.text(((1000 - (tb[2] - tb[0])) // 2, 846), txt, font=f_av, fill=(255, 255, 255, 255))
    av_path = out / "01_Server_And_Telegram_Avatar.png"
    av_crop.save(av_path, "PNG", optimize=True)
    generated["avatar"] = str(av_path)

    # 2. Welcome & Official Links Banner
    b_welcome = _create_luxury_banner(
        photo_path=p_blue1 if p_blue1.exists() else avatar_src,
        eyebrow="OFFICIAL VIP DISCORD & TELEGRAM HUB",
        title_line1="CHARLETTE WEBB",
        title_line2="VIP LOUNGE & LIVE CLUB",
        subtitle="8+ Years Industry Queen • Live Nightly 8PM–3AM EST • 700+ Exclusive Videos",
        pills=["Chaturbate Live", "Stripchat Live", "MyFreeCams", "CamSoda", "OnlyFans + Snap", "ManyVids 700+"],
        accent_rgb=(236, 72, 153),
        secondary_rgb=(0, 242, 254),
        top_bias=0.10,
    )
    p2 = out / "02_Welcome_And_Links_Banner.jpg"
    b_welcome.save(p2, "JPEG", quality=92, optimize=True)
    generated["welcome_banner"] = str(p2)

    # 3. 18+ Verification & Community Rules Banner
    b_rules = _create_luxury_banner(
        photo_path=p_school1 if p_school1.exists() else avatar_src,
        eyebrow="MANDATORY 18+ ENTRY GATE & VIP PROTECTION",
        title_line1="VERIFY 18+ TO UNLOCK",
        title_line2="THE FULL VIP SERVER",
        subtitle="Click the [Verify 18+] button below to unlock all chat lounges, cam alerts & drops.",
        pills=["1. Strictly 18+ Adults Only", "2. Zero Unsolicited DMs", "3. No Link/Leak Spam", "4. Respect The Queen & VIPs"],
        accent_rgb=(0, 229, 255),
        secondary_rgb=(255, 46, 147),
        top_bias=0.06,
    )
    p3 = out / "03_Verify_18Plus_And_Rules_Banner.jpg"
    b_rules.save(p3, "JPEG", quality=92, optimize=True)
    generated["rules_banner"] = str(p3)

    # 4. LIVE ON CAM NOW Alert Banner
    b_live = _create_luxury_banner(
        photo_path=p_blue2 if p_blue2.exists() else avatar_src,
        eyebrow="LIVE STREAMING RIGHT NOW • 8:00 PM – 3:00 AM EST",
        title_line1="CHARLETTE IS LIVE",
        title_line2="JOIN THE CAM ROOM NOW!",
        subtitle="Click your favorite cam platform button below to jump straight into the show:",
        pills=["Chaturbate Live", "Stripchat Live", "MFC Room", "CamSoda Live", "ManyVids Live"],
        accent_rgb=(255, 25, 100),
        secondary_rgb=(255, 214, 0),
        top_bias=0.08,
    )
    p4 = out / "04_Live_On_Cam_Alert_Banner.jpg"
    b_live.save(p4, "JPEG", quality=92, optimize=True)
    generated["live_banner"] = str(p4)

    # 5. Nightly Cam Schedule Banner
    b_sched = _create_luxury_banner(
        photo_path=p_green1 if p_green1.exists() else avatar_src,
        eyebrow="OFFICIAL NIGHTLY BROADCAST SCHEDULE",
        title_line1="LIVE EVERY NIGHT",
        title_line2="8:00 PM – 3:00 AM EST",
        subtitle="Turn on @Cam Live Alerts in #verify-18-plus so you never miss a show or outfit poll!",
        pills=["8:00 PM EST Warmup & Polls", "10:00 PM EST Main Show", "12:00 AM EST Late Night VIP & Privates"],
        accent_rgb=(16, 185, 129),
        secondary_rgb=(250, 204, 21),
        top_bias=0.08,
    )
    p5 = out / "05_Nightly_Cam_Schedule_Banner.jpg"
    b_sched.save(p5, "JPEG", quality=92, optimize=True)
    generated["schedule_banner"] = str(p5)

    # 6. VIP Menu, Vault & Custom Video Flyer (1200x1500)
    menu_w, menu_h = 1200, 1500
    menu_canvas = Image.new("RGBA", (menu_w, menu_h), (12, 8, 22, 255))
    bg_m = _smart_crop_portrait(p_school2 if p_school2.exists() else avatar_src, menu_w, menu_h, top_bias=0.1)
    bg_m = ImageEnhance.Brightness(bg_m.filter(ImageFilter.GaussianBlur(radius=36))).enhance(0.24)
    menu_canvas.paste(bg_m.convert("RGBA"), (0, 0))

    mdraw = ImageDraw.Draw(menu_canvas)
    mdraw.rounded_rectangle([28, 28, menu_w - 28, menu_h - 28], radius=28, outline=(236, 72, 153, 220), width=4)
    mdraw.rounded_rectangle([42, 42, menu_w - 42, menu_h - 42], radius=22, outline=(0, 242, 254, 120), width=2)

    top_av = _smart_crop_portrait(avatar_src, 220, 220, top_bias=0.05).convert("RGBA")
    circle_mask = Image.new("L", (220, 220), 0)
    ImageDraw.Draw(circle_mask).ellipse([0, 0, 220, 220], fill=255)
    menu_canvas.paste(top_av, ((menu_w - 220) // 2, 66), circle_mask)
    mdraw.ellipse([(menu_w - 220) // 2, 66, (menu_w + 220) // 2, 286], outline=(255, 30, 142, 255), width=5)

    f_mt = _get_font(62, bold=True)
    f_ms = _get_ui_font(25, bold=True)
    t1 = "CHARLETTE WEBB VIP MENU"
    tb1 = mdraw.textbbox((0, 0), t1, font=f_mt)
    mdraw.text(((menu_w - (tb1[2] - tb1[0])) // 2, 308), t1, font=f_mt, fill=(255, 255, 255, 255))

    t2 = "•  OFFICIAL SERVICES, VAULT PACKAGES & CAM PERKS  •"
    tb2 = mdraw.textbbox((0, 0), t2, font=f_ms)
    mdraw.text(((menu_w - (tb2[2] - tb2[0])) // 2, 386), t2, font=f_ms, fill=(0, 242, 254, 255))

    menu_items = [
        ("• 700+ VIDEO MEGA-VAULT UNLOCK", "$350 CashApp ($CharletteWebb)", "Full lifetime access to over 700+ full-length videos"),
        ("• ONLYFANS VIP + SNAPCHAT INCLUDED", "onlyfans.com/charlette_webb", "3-Hour full videos, daily feed drops & private Snapchat"),
        ("• CUSTOM PERSONALIZED VIDEO", "manyvids.com/Custom-vid/35990", "Your name, your script, your outfit & scenario choice"),
        ("• WORN STORE ITEMS & TROPHIES", "ManyVids Official Store", "Authentic personal items shipped discreetly to you"),
        ("• DISCORD DIAMOND WHALE ROLE", "$50+ Tip or Throne Gift", "Unlocks Private #vip-lounge, #uncensored-vault & Voice"),
        ("• LIVE NIGHTLY CAM SHOWS (8PM–3AM)", "CB • Stripchat • MFC • CamSoda", "Interactive toy control, tip menus, wheel spins & privates"),
        ("• THRONE VIP WISHLIST", "throne.com/charlettewebb", "Spoil the Queen & get instant Hall-of-Fame recognition"),
    ]

    row_y = 452
    f_item_title = _get_ui_font(26, bold=True)
    f_item_price = _get_ui_font(23, bold=True)
    f_item_desc = _get_ui_font(21, bold=False)

    for title, price, desc in menu_items:
        mdraw.rounded_rectangle(
            [74, row_y, menu_w - 74, row_y + 118],
            radius=18,
            fill=(24, 14, 42, 232),
            outline=(236, 72, 153, 140),
            width=2,
        )
        mdraw.text((100, row_y + 18), title, font=f_item_title, fill=(255, 255, 255, 255))
        pb = mdraw.textbbox((0, 0), price, font=f_item_price)
        pw = pb[2] - pb[0]
        mdraw.rounded_rectangle(
            [menu_w - 104 - pw - 28, row_y + 16, menu_w - 96, row_y + 58],
            radius=10,
            fill=(236, 72, 153, 58),
            outline=(0, 242, 254, 215),
            width=2,
        )
        mdraw.text((menu_w - 100 - pw - 14, row_y + 21), price, font=f_item_price, fill=(0, 242, 254, 255))
        mdraw.text((100, row_y + 66), desc, font=f_item_desc, fill=(210, 195, 230, 255))
        row_y += 133

    footer_txt = "CashApp: $CharletteWebb   •   All Links: linktr.ee/charlettewebb   •   Booking: Charlettewebbbooking@gmail.com"
    f_foot = _get_ui_font(20, bold=True)
    fb = mdraw.textbbox((0, 0), footer_txt, font=f_foot)
    mdraw.text(((menu_w - (fb[2] - fb[0])) // 2, menu_h - 76), footer_txt, font=f_foot, fill=(255, 185, 225, 255))

    p6 = out / "06_VIP_Tip_And_Services_Menu.jpg"
    menu_canvas.convert("RGB").save(p6, "JPEG", quality=92, optimize=True)
    generated["tip_menu"] = str(p6)

    # 7. VIP Whale Club Banner
    b_vip = _create_luxury_banner(
        photo_path=p_school2 if p_school2.exists() else avatar_src,
        eyebrow="EXCLUSIVE INNER CIRCLE • ROLE-LOCKED ACCESS",
        title_line1="CHARLETTE'S VIP",
        title_line2="& DIAMOND WHALE CLUB",
        subtitle="Tip via CashApp ($CharletteWebb), buy a Throne gift, or subscribe on OF to unlock VIP roles!",
        pills=["#vip-lounge-chat", "#vip-uncensored-vault", "Priority Customs & Privates", "VIP Voice Hangout"],
        accent_rgb=(234, 179, 8),
        secondary_rgb=(236, 72, 153),
        top_bias=0.08,
    )
    p7 = out / "07_VIP_Whale_Club_Banner.jpg"
    b_vip.save(p7, "JPEG", quality=92, optimize=True)
    generated["vip_banner"] = str(p7)

    return generated


if __name__ == "__main__":
    res = generate_charlette_webb_graphics()
    for k, v in res.items():
        print(f"Generated {k}: {v}")
