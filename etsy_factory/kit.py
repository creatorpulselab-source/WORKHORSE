"""PIL toolkit for Etsy listing images (covers, info cards, PDF guide). Pure Pillow - no network, no AI generation.

All cards are 2000 x 2000 (Etsy recommends >= 2000 px on the short side). Every number placed on a card must be passed in
by the caller from measured data - this module never invents facts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path(r"C:\Windows\Fonts")
SIZE = 2000

THEMES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "christmas": {"bg": (14, 52, 38), "bg2": (9, 33, 25), "accent": (200, 40, 55), "text": (250, 245, 232), "muted": (190, 205, 195)},
    "slate": {"bg": (22, 28, 40), "bg2": (13, 17, 26), "accent": (240, 170, 60), "text": (245, 247, 250), "muted": (170, 180, 195)},
}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    files = {"black": "seguibl.ttf", "bold": "segoeuib.ttf", "semi": "seguisb.ttf", "regular": "segoeui.ttf"}
    for name in (files[weight], "arialbd.ttf" if weight in ("black", "bold") else "arial.ttf"):
        try:
            return ImageFont.truetype(str(FONT_DIR / name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_font(draw: ImageDraw.ImageDraw, text: str, weight: str, max_w: int, start: int, min_size: int = 40):
    s = start
    while s > min_size:
        f = font(weight, s)
        if draw.textlength(text, font=f) <= max_w:
            return f
        s -= 4
    return font(weight, min_size)


def centered(draw, y: int, text: str, f, fill, width: int = SIZE, shadow: bool = False) -> int:
    w = draw.textlength(text, font=f)
    x = (width - w) / 2
    if shadow:
        draw.text((x + 5, y + 6), text, font=f, fill=(0, 0, 0, 150))
    draw.text((x, y), text, font=f, fill=fill)
    box = draw.textbbox((x, y), text, font=f)
    return box[3]


def wrap(draw, text: str, f, max_w: int) -> List[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def pill(draw, cx: int, cy: int, text: str, f, fill, text_fill, pad_x: int = 38, pad_y: int = 20) -> Tuple[int, int, int, int]:
    w = draw.textlength(text, font=f)
    h = f.size
    box = (cx - w / 2 - pad_x, cy - h / 2 - pad_y, cx + w / 2 + pad_x, cy + h / 2 + pad_y + 4)
    draw.rounded_rectangle(box, radius=int((box[3] - box[1]) / 2), fill=fill)
    draw.text((cx - w / 2, cy - h / 2 - 4), text, font=f, fill=text_fill)
    return box


def _vertical_gradient(w: int, h: int, top: Tuple[int, int, int, int], bottom: Tuple[int, int, int, int]) -> Image.Image:
    g = Image.new("RGBA", (w, h))
    px = g.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4))
        for x in range(w):
            px[x, y] = c
    return g


def square_crop(img: Image.Image, size: int = SIZE) -> Image.Image:
    img = img.convert("RGB")
    s = min(img.size)
    left, top = (img.width - s) // 2, (img.height - s) // 2
    return img.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)


def cover(raw: Path, out: Path, big: str, line1: str, line2: str, badges: Sequence[str], theme: str = "christmas",
          caption: str = "") -> Path:
    """Marketplace-style cover: huge count, bold title, feature pills. Count/badges are supplied by the caller."""
    th = THEMES[theme]
    base = square_crop(Image.open(raw)).convert("RGBA")
    top_h, bot_h = 760, 330
    top = _vertical_gradient(SIZE, top_h, th["bg2"] + (245,), th["bg2"] + (0,))
    bot = _vertical_gradient(SIZE, bot_h, th["bg2"] + (0,), th["bg2"] + (250,))
    base.alpha_composite(top, (0, 0))
    base.alpha_composite(bot, (0, SIZE - bot_h))
    d = ImageDraw.Draw(base)
    fbig = font("black", 300)
    y = centered(d, 20, big, fbig, th["accent"], shadow=True) + 22
    f1 = fit_font(d, line1.upper(), "black", 1740, 150)
    y = centered(d, y, line1.upper(), f1, th["text"], shadow=True) + 14
    f2 = fit_font(d, line2.upper(), "bold", 1500, 84)
    centered(d, y, line2.upper(), f2, th["muted"], shadow=True)
    # badges: sequential layout by measured width so pills never overlap
    fb = font("bold", 54)
    pad, gap = 34, 26
    rows = [list(badges[:3]), list(badges[3:6])]
    cy = SIZE - 205
    for row in rows:
        if not row:
            continue
        widths = [d.textlength(b, font=fb) + 2 * pad for b in row]
        x = (SIZE - (sum(widths) + gap * (len(row) - 1))) / 2
        for i, (b, w) in enumerate(zip(row, widths)):
            pill(d, int(x + w / 2), cy, b, fb, th["accent"] if i % 2 == 0 else th["text"],
                 th["text"] if i % 2 == 0 else th["bg2"], pad_x=pad)
            x += w + gap
        cy += 112
    if caption:
        centered(d, SIZE - 330, caption, font("semi", 54), th["muted"], shadow=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=93)
    return out


def captioned(raw: Path, out: Path, caption: str, sub: str = "", theme: str = "christmas") -> Path:
    """A product photo with a slim caption ribbon along the bottom."""
    th = THEMES[theme]
    base = square_crop(Image.open(raw)).convert("RGBA")
    h = 300 if sub else 220
    base.alpha_composite(_vertical_gradient(SIZE, h + 120, th["bg2"] + (0,), th["bg2"] + (235,)), (0, SIZE - h - 120))
    d = ImageDraw.Draw(base)
    f = fit_font(d, caption, "black", 1800, 120)
    y = SIZE - h + 10
    y = centered(d, y, caption, f, th["text"], shadow=True)
    if sub:
        centered(d, y + 16, sub, fit_font(d, sub, "semi", 1750, 66), th["muted"], shadow=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=93)
    return out


def card(out: Path, title: str, bullets: Sequence[str], theme: str = "christmas", footer: str = "",
         kicker: str = "") -> Path:
    """Dark info card: title + bullet rows. Bullets may be 'Label|value' for a two-column row."""
    th = THEMES[theme]
    img = _vertical_gradient(SIZE, SIZE, th["bg"] + (255,), th["bg2"] + (255,)).convert("RGB")
    d = ImageDraw.Draw(img)
    y = 110
    if kicker:
        y = centered(d, y, kicker.upper(), font("bold", 58), th["accent"]) + 20
    ft = fit_font(d, title, "black", 1760, 150)
    y = centered(d, y, title, ft, th["text"]) + 40
    d.rounded_rectangle((SIZE / 2 - 120, y, SIZE / 2 + 120, y + 12), radius=6, fill=th["accent"])
    y += 80
    fb, fv = font("semi", 66), font("bold", 66)
    avail = SIZE - 2 * 170
    n_rows = len(bullets)
    room = SIZE - 260 - y
    row_h = int(max(78, min(176, room / max(n_rows, 1))))
    if row_h < 118:
        fb, fv = font("semi", 56), font("bold", 56)
    for item in bullets:
        if "|" in item:
            label, value = item.split("|", 1)
            d.rounded_rectangle((170, y, SIZE - 170, y + row_h - 18), radius=26, fill=(255, 255, 255, 18) if False else tuple(min(255, c + 14) for c in th["bg"]))
            d.text((220, y + (row_h - 18 - fb.size) / 2 - 4), label.strip(), font=fb, fill=th["muted"])
            vw = d.textlength(value.strip(), font=fv)
            d.text((SIZE - 220 - vw, y + (row_h - 18 - fv.size) / 2 - 4), value.strip(), font=fv, fill=th["text"])
        else:
            d.ellipse((190, y + row_h / 2 - 22, 230, y + row_h / 2 + 18), fill=th["accent"])
            lines = wrap(d, item, fv, avail - 90)
            for k, line in enumerate(lines[:2]):
                d.text((270, y + (row_h - 18 - fv.size) / 2 - 4 + k * (fv.size + 6)), line, font=fv, fill=th["text"])
        y += row_h
    if footer:
        for k, line in enumerate(wrap(d, footer, font("regular", 46), 1700)[:3]):
            centered(d, SIZE - 190 + k * 58, line, font("regular", 46), th["muted"])
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=93)
    return out


def silhouette_sheet(out: Path, items: Sequence[Tuple[str, Sequence[Sequence[Tuple[float, float]]]]], title: str,
                     theme: str = "christmas", cols: int = 5, footer: str = "") -> Path:
    """Contact sheet of 2D silhouettes. items = [(label, [ring, ring, ...])]; first ring is the outline, the rest are holes."""
    th = THEMES[theme]
    img = _vertical_gradient(SIZE, SIZE, th["bg"] + (255,), th["bg2"] + (255,)).convert("RGB")
    d = ImageDraw.Draw(img)
    y = centered(d, 90, title, fit_font(d, title, "black", 1760, 140), th["text"]) + 50
    rows = (len(items) + cols - 1) // cols
    cell_w = (SIZE - 160) / cols
    area_h = SIZE - y - (170 if footer else 90)
    cell_h = area_h / rows
    S = 4  # supersample
    for i, (label, rings) in enumerate(items):
        c, r = i % cols, i // cols
        cx, cy = 80 + cell_w * (c + 0.5), y + cell_h * (r + 0.42)
        box = int(min(cell_w, cell_h) * 0.66)
        xs = [p[0] for ring in rings[:1] for p in ring]
        ys = [p[1] for ring in rings[:1] for p in ring]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        k = box / max(w, h)
        tile = Image.new("L", (box * S, box * S), 0)
        td = ImageDraw.Draw(tile)
        mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

        def tx(p):
            return ((p[0] - mx) * k + box / 2) * S, (box / 2 - (p[1] - my) * k) * S

        for j, ring in enumerate(rings):
            td.polygon([tx(p) for p in ring], fill=255 if j == 0 else 0)
        tile = tile.resize((box, box), Image.LANCZOS)
        colour = th["accent"] if i % 2 == 0 else th["text"]
        img.paste(Image.new("RGB", (box, box), colour), (int(cx - box / 2), int(cy - box / 2)), tile)
        f = fit_font(d, label, "semi", int(cell_w - 20), 54, 30)
        wl = d.textlength(label, font=f)
        d.text((cx - wl / 2, cy + box / 2 + 16), label, font=f, fill=th["text"])
    if footer:
        centered(d, SIZE - 150, footer, font("semi", 52), th["muted"])
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=93)
    return out


def pdf_guide(out: Path, pages: Sequence[Tuple[str, Sequence[str]]], theme: str = "christmas") -> Path:
    """Simple multi-page A4-ish PDF (Pillow) - one (title, paragraphs) tuple per page."""
    th = THEMES[theme]
    W, H = 1654, 2339  # A4 @ 200 dpi
    imgs: List[Image.Image] = []
    for title, paras in pages:
        im = Image.new("RGB", (W, H), (252, 250, 245))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 210), fill=th["bg"])
        d.text((90, 62), title, font=fit_font(d, title, "black", W - 180, 92), fill=th["text"])
        y = 290
        fb = font("regular", 40)
        for p in paras:
            if p.startswith("# "):
                y += 14
                d.text((90, y), p[2:], font=font("bold", 50), fill=th["accent"])
                y += 78
                continue
            for line in wrap(d, p, fb, W - 180):
                d.text((90, y), line, font=fb, fill=(40, 40, 45))
                y += 56
            y += 22
        imgs.append(im)
    out.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(out, "PDF", save_all=True, append_images=imgs[1:], resolution=200.0)
    return out
