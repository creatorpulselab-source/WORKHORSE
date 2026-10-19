"""PIL toolkit for Etsy listing images (covers, info cards, PDF guide). Pure Pillow - no network, no AI generation.

Style target: vibrant marketplace look - saturated colour, huge gradient numbers with thick outlines, ribbons, starbursts and
icon chips. All cards are 2000 x 2000. Every number placed on a card must be passed in by the caller from measured data -
this module never invents facts.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_DIR = Path(r"C:\Windows\Fonts")
LOCAL_FONTS = Path(__file__).parent / "fonts"
SIZE = 2000
RGB = Tuple[int, int, int]

THEMES: Dict[str, Dict[str, RGB]] = {
    "valentine": {"bg": (214, 30, 88), "bg2": (92, 14, 70), "accent": (255, 214, 64), "accent2": (255, 120, 170),
                  "text": (255, 250, 248), "muted": (255, 224, 236), "panel": (255, 255, 255), "dark": (36, 8, 28),
                  "sheet_colors": [(255, 110, 160), (200, 20, 70), (255, 150, 20), (150, 40, 120), (240, 70, 110)]},
    "christmas": {"bg": (150, 12, 32), "bg2": (8, 70, 44), "accent": (255, 204, 38), "accent2": (226, 36, 52),
                  "text": (255, 250, 238), "muted": (255, 226, 190), "panel": (255, 255, 255), "dark": (14, 10, 24)},
    "tech": {"bg": (44, 30, 150), "bg2": (8, 8, 52), "accent": (255, 196, 34), "accent2": (0, 196, 214),
             "text": (255, 255, 255), "muted": (200, 210, 255), "panel": (255, 255, 255), "dark": (8, 8, 30)},
    "sunny": {"bg": (255, 120, 40), "bg2": (150, 20, 90), "accent": (255, 232, 70), "accent2": (30, 170, 220),
              "text": (255, 255, 255), "muted": (255, 236, 210), "panel": (255, 255, 255), "dark": (40, 10, 40)},
    "forest": {"bg": (0, 130, 110), "bg2": (4, 40, 60), "accent": (255, 214, 60), "accent2": (255, 96, 60),
               "text": (255, 255, 255), "muted": (200, 245, 235), "panel": (255, 255, 255), "dark": (4, 24, 36)},
}
THEMES["slate"] = THEMES["tech"]


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    if weight == "anton":
        try:
            return ImageFont.truetype(str(LOCAL_FONTS / "Anton-Regular.ttf"), size)
        except OSError:
            weight = "black"
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


# ----------------------------------------------------------------------------- colour / gradient helpers
def lerp(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def vgrad(w: int, h: int, top: RGB, bottom: RGB) -> Image.Image:
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        px[0, y] = lerp(top, bottom, y / max(h - 1, 1))
    return col.resize((w, h))


def radial_glow(size: int, centre: Tuple[float, float], radius: float, colour: RGB, strength: float = 0.9) -> Image.Image:
    """RGBA layer with a soft radial glow (used behind text and in card backgrounds)."""
    g = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(g)
    cx, cy = centre
    steps = 36
    for i in range(steps, 0, -1):
        r = radius * i / steps
        v = int(255 * strength * (1 - i / steps) ** 1.6)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=v)
    g = g.filter(ImageFilter.GaussianBlur(radius / 12))
    layer = Image.new("RGBA", (size, size), colour + (0,))
    layer.putalpha(g)
    return layer


def grade(img: Image.Image, colour: float = 1.28, contrast: float = 1.10, vignette: float = 0.30) -> Image.Image:
    """Final pop for 3D renders: saturation + contrast + soft vignette."""
    img = img.convert("RGB")
    img = ImageEnhance.Color(img).enhance(colour)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    if vignette:
        w, h = img.size
        v = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(v)
        d.ellipse((-w * 0.18, -h * 0.18, w * 1.18, h * 1.18), fill=255)
        v = v.filter(ImageFilter.GaussianBlur(w / 6))
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        img = Image.composite(img, Image.blend(img, dark, vignette * 1.8), v)
    return img


def square_crop(img: Image.Image, size: int = SIZE) -> Image.Image:
    img = img.convert("RGB")
    s = min(img.size)
    left, top = (img.width - s) // 2, (img.height - s) // 2
    return img.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)


def _place(img: Image.Image, scale: float, dy: int, fill) -> Image.Image:
    """Scale an image about the frame centre and shift it down by dy (canvas stays SIZE x SIZE)."""
    if scale == 1.0 and not dy:
        return img
    s = int(SIZE * scale)
    canvas = Image.new(img.mode, (SIZE, SIZE), fill)
    canvas.paste(img.resize((s, s), Image.LANCZOS), ((SIZE - s) // 2, (SIZE - s) // 2 + dy))
    return canvas


def composite(cutout: Path, bg: Image.Image, out: Path, shadow_strength: float = 0.85, scale: float = 1.0,
              dy: int = 0, bg_dim: float = 0.0) -> Path:
    """Place a transparent Blender render on a (ComfyUI) backdrop with its real shadow.

    `cutout` is the RGBA product render; `<stem>_shadow.png` (white ground lit with the same lights, objects invisible to the
    camera) provides the shadow shape. If it is missing, a soft blurred alpha shadow is used instead.
    """
    import numpy as np
    bgc = bg.convert("RGBA").resize((SIZE, SIZE))
    if bg_dim:
        bgc = Image.blend(bgc, Image.new("RGBA", bgc.size, (0, 0, 0, 255)), bg_dim)
    fg = _place(Image.open(cutout).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS), scale, dy, (0, 0, 0, 0))
    sh_path = cutout.with_name(cutout.stem + "_shadow.png")
    if sh_path.exists():
        lum = _place(Image.open(sh_path).convert("L").resize((SIZE, SIZE), Image.LANCZOS), scale, dy, 255)
        arr = np.asarray(lum, dtype=np.float32)
        lit = float(np.percentile(arr, 90)) or 255.0
        a = np.clip((lit - arr) / lit, 0, 1) ** 0.85 * 255 * shadow_strength
        sh = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sh.putalpha(Image.fromarray(a.astype("uint8")).filter(ImageFilter.GaussianBlur(3)))
    else:
        a = fg.split()[3].point(lambda p: 255 if p > 200 else 0)
        sh = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sh.putalpha(a.filter(ImageFilter.GaussianBlur(26)).point(lambda p: int(p * 0.55)))
        sh = ImageChops.offset(sh, 16, 30)
    bgc.alpha_composite(sh)
    bgc.alpha_composite(fg)
    out.parent.mkdir(parents=True, exist_ok=True)
    bgc.convert("RGB").save(out, quality=95)
    return out

# ----------------------------------------------------------------------------- text drawing
def grad_text(base: Image.Image, x_center: float, y: float, text: str, f: ImageFont.FreeTypeFont, top: RGB, bottom: RGB,
              stroke: int = 12, stroke_fill: RGB = (20, 10, 10), shadow: bool = True) -> int:
    """Gradient-filled text with thick outline and drop shadow, centred on x_center. Returns bottom y."""
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = int(tmp.textlength(text, font=f))
    bbox = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke)
    pad = stroke + 30
    cw, ch = w + pad * 2, (bbox[3] - bbox[1]) + pad * 2
    ox, oy = pad, pad - bbox[1]
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).text((ox, oy), text, font=f, fill=255)
    outline = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(outline).text((ox, oy), text, font=f, fill=255, stroke_width=stroke)
    gtop = bbox[1] + oy
    grad = vgrad(cw, ch, top, bottom)
    layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        sh.putalpha(outline.filter(ImageFilter.GaussianBlur(10)).point(lambda p: int(p * 0.75)))
        layer.alpha_composite(sh, (0, 0))
        layer = ImageChops.offset(layer, 0, 10)
    st = Image.new("RGBA", (cw, ch), stroke_fill + (255,))
    st.putalpha(outline)
    layer.alpha_composite(st)
    fill = grad.convert("RGBA")
    fill.putalpha(mask)
    layer.alpha_composite(fill)
    x0 = int(x_center - cw / 2)
    y0 = int(y - pad - 0)
    base.alpha_composite(layer, (x0, y0)) if base.mode == "RGBA" else base.paste(layer, (x0, y0), layer)
    return int(y0 + oy + bbox[3])


def pill(draw, cx: int, cy: int, text: str, f, fill, text_fill, pad_x: int = 38, pad_y: int = 20) -> Tuple[int, int, int, int]:
    w = draw.textlength(text, font=f)
    h = f.size
    box = (cx - w / 2 - pad_x, cy - h / 2 - pad_y, cx + w / 2 + pad_x, cy + h / 2 + pad_y + 4)
    draw.rounded_rectangle(box, radius=int((box[3] - box[1]) / 2), fill=fill)
    draw.text((cx - w / 2, cy - h / 2 - 4), text, font=f, fill=text_fill)
    return box


def centered(draw, y: int, text: str, f, fill, width: int = SIZE, shadow: bool = False) -> int:
    w = draw.textlength(text, font=f)
    x = (width - w) / 2
    if shadow:
        draw.text((x + 4, y + 5), text, font=f, fill=(0, 0, 0, 150))
    draw.text((x, y), text, font=f, fill=fill)
    return draw.textbbox((x, y), text, font=f)[3]


# ----------------------------------------------------------------------------- shapes & icons
def ribbon(base: Image.Image, cx: int, cy: int, w: int, h: int, colour: RGB, text: str, f, text_fill=(255, 255, 255)) -> None:
    d = ImageDraw.Draw(base)
    tail = int(h * 0.55)
    dark = lerp(colour, (0, 0, 0), 0.38)
    x0, x1, y0, y1 = cx - w // 2, cx + w // 2, cy - h // 2, cy + h // 2
    d.polygon([(x0 - tail, y0 + h * 0.22), (x0 + 6, y0 + h * 0.22), (x0 + 6, y1 + h * 0.22), (x0 - tail, y1 + h * 0.22),
               (x0 - tail + h * 0.28, cy + h * 0.22)], fill=dark)
    d.polygon([(x1 + tail, y0 + h * 0.22), (x1 - 6, y0 + h * 0.22), (x1 - 6, y1 + h * 0.22), (x1 + tail, y1 + h * 0.22),
               (x1 + tail - h * 0.28, cy + h * 0.22)], fill=dark)
    d.rounded_rectangle((x0, y0, x1, y1), radius=10, fill=colour)
    d.rectangle((x0, y0, x1, y0 + h * 0.08), fill=lerp(colour, (255, 255, 255), 0.35))
    tw = d.textlength(text, font=f)
    ImageDraw.Draw(base).text((cx - tw / 2 + 3, cy - f.size * 0.56 + 5), text, font=f, fill=(0, 0, 0))
    ImageDraw.Draw(base).text((cx - tw / 2, cy - f.size * 0.56), text, font=f, fill=text_fill)


def starburst(base: Image.Image, cx: int, cy: int, r: int, colour: RGB, lines: Sequence[str], spikes: int = 18,
              text_fill=(255, 255, 255)) -> None:
    pts = []
    for i in range(spikes * 2):
        a = math.pi * i / spikes - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.80
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 8, y + 12) for x, y in pts], fill=(0, 0, 0, 160))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(base)
    d.polygon(pts, fill=(255, 255, 255))
    inner = [(cx + (x - cx) * 0.93, cy + (y - cy) * 0.93) for x, y in pts]
    d.polygon(inner, fill=colour)
    n = len(lines)
    sizes = [int(r * (0.46 if n == 1 else 0.40)) if k == 0 else int(r * 0.26) for k in range(n)]
    total = sum(sizes) + 8 * (n - 1)
    y = cy - total / 2 - 8
    for line, s in zip(lines, sizes):
        f = fit_font(d, line, "anton", int(r * 1.35), s, 20)
        w = d.textlength(line, font=f)
        d.text((cx - w / 2 + 3, y + 4), line, font=f, fill=(0, 0, 0))
        d.text((cx - w / 2, y), line, font=f, fill=text_fill)
        y += f.size + 8


def icon(d: ImageDraw.ImageDraw, kind: str, cx: int, cy: int, r: int, col: RGB) -> None:
    w = max(6, r // 7)
    if kind == "download":
        d.line([(cx, cy - r * 0.55), (cx, cy + r * 0.25)], fill=col, width=w)
        d.polygon([(cx - r * 0.42, cy + r * 0.0), (cx + r * 0.42, cy + r * 0.0), (cx, cy + r * 0.48)], fill=col)
        d.line([(cx - r * 0.55, cy + r * 0.62), (cx + r * 0.55, cy + r * 0.62)], fill=col, width=w)
    elif kind == "check":
        d.line([(cx - r * 0.5, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.42), (cx + r * 0.55, cy - r * 0.4)], fill=col,
               width=w + 4, joint="curve")
    elif kind == "cube":
        pts = [(cx, cy - r * .62), (cx + r * .54, cy - r * .31), (cx + r * .54, cy + r * .31), (cx, cy + r * .62),
               (cx - r * .54, cy + r * .31), (cx - r * .54, cy - r * .31)]
        d.polygon(pts, outline=col, width=w)
        d.line([(cx - r * .54, cy - r * .31), (cx, cy), (cx + r * .54, cy - r * .31)], fill=col, width=w)
        d.line([(cx, cy), (cx, cy + r * .62)], fill=col, width=w)
    elif kind == "file":
        d.polygon([(cx - r * .42, cy - r * .62), (cx + r * .12, cy - r * .62), (cx + r * .42, cy - r * .3),
                   (cx + r * .42, cy + r * .62), (cx - r * .42, cy + r * .62)], outline=col, width=w)
        d.line([(cx + r * .12, cy - r * .62), (cx + r * .12, cy - r * .3), (cx + r * .42, cy - r * .3)], fill=col, width=w)
    elif kind == "star":
        pts = []
        for i in range(10):
            a = math.pi * i / 5 - math.pi / 2
            rr = r * 0.62 if i % 2 == 0 else r * 0.26
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=col)
    elif kind == "layers":
        for k in range(3):
            yy = cy + (k - 1) * r * 0.36
            d.polygon([(cx, yy - r * .3), (cx + r * .62, yy), (cx, yy + r * .3), (cx - r * .62, yy)], outline=col, width=w - 1)
    elif kind == "shield":
        d.polygon([(cx - r * .5, cy - r * .5), (cx + r * .5, cy - r * .5), (cx + r * .5, cy + r * .1), (cx, cy + r * .66),
                   (cx - r * .5, cy + r * .1)], outline=col, width=w)
        d.line([(cx - r * .22, cy + r * .02), (cx - r * .04, cy + r * .24), (cx + r * .28, cy - r * .2)], fill=col, width=w)
    elif kind == "printer":
        d.rectangle((cx - r * .55, cy - r * .1, cx + r * .55, cy + r * .42), outline=col, width=w)
        d.rectangle((cx - r * .32, cy - r * .62, cx + r * .32, cy - r * .1), outline=col, width=w)
        d.rectangle((cx - r * .32, cy + r * .2, cx + r * .32, cy + r * .66), outline=col, width=w)
    elif kind == "infinity":
        d.ellipse((cx - r * .62, cy - r * .28, cx - r * .02, cy + r * .28), outline=col, width=w)
        d.ellipse((cx + r * .02, cy - r * .28, cx + r * .62, cy + r * .28), outline=col, width=w)
    elif kind == "heart":
        d.ellipse((cx - r * .55, cy - r * .5, cx, cy + r * .1), fill=col)
        d.ellipse((cx, cy - r * .5, cx + r * .55, cy + r * .1), fill=col)
        d.polygon([(cx - r * .53, cy - r * .1), (cx + r * .53, cy - r * .1), (cx, cy + r * .6)], fill=col)


ICON_KEYWORDS = [("download", "download"), ("print", "printer"), ("stl", "cube"), ("3mf", "cube"), ("glb", "cube"),
                 ("svg", "file"), ("png", "file"), ("license", "shield"), ("commercial", "shield"), ("plate", "layers"),
                 ("size", "layers"), ("press", "layers"), ("lifetime", "infinity"), ("designs", "star"), ("files", "file"),
                 ("cricut", "check"), ("ready", "check")]


def _icon_for(label: str) -> str:
    low = label.lower()
    for key, ic in ICON_KEYWORDS:
        if key in low:
            return ic
    return "check"


def chip(base: Image.Image, x: int, y: int, w: int, h: int, label: str, th: Dict[str, RGB], kind: str | None = None) -> None:
    kind = kind or _icon_for(label)
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x + 4, y + 10, x + w + 4, y + h + 10), radius=26, fill=(0, 0, 0, 150))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((x, y, x + w, y + h), radius=26, fill=lerp(th["dark"], (255, 255, 255), 0.10) + (235,),
                        outline=th["accent"], width=4)
    icon(d, kind, x + w // 2, y + int(h * 0.27), int(h * 0.24), th["accent"])
    words = label.upper().split(" ")
    if len(label) > 11 and len(words) > 1:
        best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    else:
        lines = [label.upper()]
    fs = 34
    f = font("bold", fs)
    while max(d.textlength(l, font=f) for l in lines) > w - 22 and fs > 18:
        fs -= 2
        f = font("bold", fs)
    block = len(lines) * (fs + 2)
    ty = y + int(h * 0.50) + (h * 0.46 - block) / 2
    for l in lines:
        tw = d.textlength(l, font=f)
        d.text((x + (w - tw) / 2, ty), l, font=f, fill=th["text"])
        ty += fs + 2


# ----------------------------------------------------------------------------- product images
def cover(raw: Path, out: Path, big: str, line1: str, line2: str, badges: Sequence[str], theme: str = "christmas",
          caption: str = "", burst: Sequence[str] = ()) -> Path:
    """Marketplace-style cover: dense product collage, huge gradient count, outlined title, ribbon, icon chips, starburst."""
    th = THEMES[theme]
    base = grade(square_crop(Image.open(raw))).convert("RGBA")
    # frosted panel behind the text block so the title always reads, products stay visible above/below
    panel_box = (90, 420, SIZE - 90, 1270)
    blur = base.filter(ImageFilter.GaussianBlur(40))
    blur = Image.blend(blur, Image.new("RGBA", base.size, th["dark"] + (255,)), 0.70)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(panel_box, radius=70, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    base = Image.composite(blur, base, mask)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(panel_box, radius=70, outline=th["accent"], width=7)
    glow = radial_glow(SIZE, (SIZE / 2, 700), 620, th["accent"], 0.42)
    base.alpha_composite(glow)

    y = 395
    y = grad_text(base, SIZE / 2, y, big, font("anton", 520), (255, 244, 120), (255, 150, 10), stroke=20,
                  stroke_fill=(70, 12, 6)) - 10
    f1 = fit_font(d, line1.upper(), "anton", 1700, 200)
    y = grad_text(base, SIZE / 2, y + 12, line1.upper(), f1, (255, 255, 255), (210, 225, 255), stroke=12,
                  stroke_fill=th["dark"]) + 16
    f2 = fit_font(d, line2.upper(), "anton", 1380, 98)
    ribbon(base, SIZE // 2, int(y + 78), min(1560, int(d.textlength(line2.upper(), font=f2) + 150)), 118, th["accent2"],
           line2.upper(), f2)
    if caption:
        centered(ImageDraw.Draw(base), int(y + 176), caption, font("bold", 54), th["muted"], shadow=True)
    if burst:
        starburst(base, 1760, 215, 188, th["accent2"], list(burst))

    chips = list(badges[:6])
    if chips:
        n = len(chips)
        gap = 22
        cw = int((SIZE - 160 - gap * (n - 1)) / n)
        cw = min(cw, 300)
        total = cw * n + gap * (n - 1)
        x0 = (SIZE - total) // 2
        for i, c in enumerate(chips):
            chip(base, x0 + i * (cw + gap), 1740, cw, 205, c, th)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def cover_open(raw: Path, out: Path, big: str, line1: str, line2: str, badges: Sequence[str], theme: str = "christmas",
               burst: Sequence[str] = (), vignette: float = 0.62) -> Path:
    """Like cover(), but NO opaque panel: the product collage runs edge to edge and only a soft radial darkening sits behind
    the headline, so every product stays visible (the marketplace top-seller look)."""
    import numpy as np
    th = THEMES[theme]
    base = grade(square_crop(Image.open(raw))).convert("RGBA")
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    dist = np.sqrt(((xx - SIZE / 2) / 1.05) ** 2 + ((yy - 640) / 0.78) ** 2) / 1000.0
    a = np.clip(1.0 - dist, 0, 1) ** 1.3 * vignette
    shade = Image.new("RGBA", base.size, th["dark"] + (255,))
    shade.putalpha(Image.fromarray((a * 255).astype("uint8")))
    base.alpha_composite(shade)
    d = ImageDraw.Draw(base)
    y = 80
    y = grad_text(base, SIZE / 2, y, big, font("anton", 430), (255, 244, 120), (255, 150, 10), stroke=18, stroke_fill=(70, 12, 6)) - 6
    f1 = fit_font(d, line1.upper(), "anton", 1760, 210)
    y = grad_text(base, SIZE / 2, y + 8, line1.upper(), f1, (255, 255, 255), (255, 214, 232), stroke=13, stroke_fill=th["dark"]) + 14
    f2 = fit_font(d, line2.upper(), "anton", 1380, 92)
    ribbon(base, SIZE // 2, int(y + 76), min(1560, int(d.textlength(line2.upper(), font=f2) + 150)), 112, th["accent2"], line2.upper(), f2)
    if burst:
        starburst(base, 1790, 190, 170, th["accent2"], list(burst))
    chips = list(badges[:6])
    if chips:
        n = len(chips)
        gap = 22
        cw = min(int((SIZE - 160 - gap * (n - 1)) / n), 300)
        x0 = (SIZE - (cw * n + gap * (n - 1))) // 2
        for i, c in enumerate(chips):
            chip(base, x0 + i * (cw + gap), 1740, cw, 205, c, th)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def captioned(raw: Path, out: Path, caption: str, sub: str = "", theme: str = "christmas") -> Path:
    """Product photo with a bold outlined caption over a colour gradient band."""
    th = THEMES[theme]
    base = grade(square_crop(Image.open(raw))).convert("RGBA")
    band_h = 330 if sub else 250
    band = Image.new("RGBA", (SIZE, band_h + 140), (0, 0, 0, 0))
    gradient = vgrad(SIZE, band_h + 140, th["bg2"], th["dark"]).convert("RGBA")
    gm = Image.linear_gradient("L").resize((SIZE, band_h + 140))
    gradient.putalpha(gm.point(lambda p: int(min(255, p * 1.15))))
    base.alpha_composite(gradient, (0, SIZE - band_h - 140))
    d = ImageDraw.Draw(base)
    d.rectangle((0, SIZE - band_h + 8, SIZE, SIZE - band_h + 22), fill=th["accent"])
    f = fit_font(d, caption.upper(), "anton", 1780, 150)
    y = grad_text(base, SIZE / 2, SIZE - band_h + 44, caption.upper(), f, (255, 255, 255), (255, 226, 120), stroke=9,
                  stroke_fill=th["dark"])
    if sub:
        centered(ImageDraw.Draw(base), y + 14, sub, fit_font(d, sub, "bold", 1760, 66), th["muted"], shadow=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def _card_bg(th: Dict[str, RGB]) -> Image.Image:
    img = vgrad(SIZE, SIZE, th["bg"], th["bg2"]).convert("RGBA")
    img.alpha_composite(radial_glow(SIZE, (SIZE * 0.2, SIZE * 0.1), 900, th["accent"], 0.28))
    img.alpha_composite(radial_glow(SIZE, (SIZE * 0.9, SIZE * 0.95), 900, th["accent2"], 0.34))
    d = ImageDraw.Draw(img)
    for gx in range(60, SIZE, 120):                       # faint dot pattern
        for gy in range(60, SIZE, 120):
            d.ellipse((gx - 3, gy - 3, gx + 3, gy + 3), fill=(255, 255, 255, 22))
    return img


def card(out: Path, title: str, bullets: Sequence[str], theme: str = "christmas", footer: str = "",
         kicker: str = "") -> Path:
    """Vibrant info card: gradient background, outlined title, glass rows. Bullets may be 'Label|value'."""
    th = THEMES[theme]
    img = _card_bg(th)
    d = ImageDraw.Draw(img)
    y = 90
    if kicker:
        kf = fit_font(d, kicker.upper(), "bold", 1500, 56)
        kw = d.textlength(kicker.upper(), font=kf)
        d.rounded_rectangle((SIZE / 2 - kw / 2 - 44, y, SIZE / 2 + kw / 2 + 44, y + 92), radius=46, fill=th["accent2"])
        d.text((SIZE / 2 - kw / 2, y + 12), kicker.upper(), font=kf, fill=(255, 255, 255))
        y += 130
    ft = fit_font(d, title.upper(), "anton", 1800, 230)
    y = grad_text(img, SIZE / 2, y, title.upper(), ft, (255, 244, 130), (255, 160, 20), stroke=14,
                  stroke_fill=th["dark"]) + 40
    d = ImageDraw.Draw(img)
    fb, fv = font("bold", 66), font("black", 70)
    n_rows = len(bullets)
    room = SIZE - 270 - y
    row_h = int(max(80, min(190, room / max(n_rows, 1))))
    if row_h < 122:
        fb, fv = font("bold", 54), font("black", 56)
    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    for i, item in enumerate(bullets):
        top = y + i * row_h
        pd.rounded_rectangle((130, top, SIZE - 130, top + row_h - 20), radius=34, fill=(255, 255, 255, 40),
                             outline=(255, 255, 255, 110), width=3)
        pd.rounded_rectangle((130, top, 152, top + row_h - 20), radius=11, fill=th["accent"] + (255,))
    img.alpha_composite(panel)
    d = ImageDraw.Draw(img)
    for i, item in enumerate(bullets):
        top = y + i * row_h
        mid = top + (row_h - 20) / 2
        if "|" in item:
            label, value = (s.strip() for s in item.split("|", 1))
            d.text((196, mid - fb.size * 0.62), label, font=fb, fill=th["muted"])
            vf = fit_font(d, value, "black", int(SIZE - 400 - d.textlength(label, font=fb) - 40), fv.size, 34)
            vw = d.textlength(value, font=vf)
            d.text((SIZE - 190 - vw, mid - vf.size * 0.62), value, font=vf, fill=th["text"])
        else:
            lines = wrap(d, item, fv, SIZE - 460)
            for k, line in enumerate(lines[:2]):
                d.text((196, mid - fv.size * 0.62 + k * (fv.size + 4) - (fv.size * 0.3 if len(lines) > 1 else 0)), line,
                       font=fv, fill=th["text"])
    if footer:
        ff = font("semi", 46)
        for k, line in enumerate(wrap(d, footer, ff, 1740)[:3]):
            centered(d, SIZE - 200 + k * 58, line, ff, th["muted"], shadow=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def silhouette_sheet(out: Path, items: Sequence[Tuple[str, Sequence[Sequence[Tuple[float, float]]]]], title: str,
                     theme: str = "christmas", cols: int = 5, footer: str = "") -> Path:
    """Contact sheet of 2D silhouettes on white tiles. items = [(label, [ring, ring, ...])]; first ring is the outline."""
    th = THEMES[theme]
    img = _card_bg(th)
    d = ImageDraw.Draw(img)
    y = grad_text(img, SIZE / 2, 80, title.upper(), fit_font(d, title.upper(), "anton", 1800, 210), (255, 244, 130),
                  (255, 160, 20), stroke=13, stroke_fill=th["dark"]) + 40
    d = ImageDraw.Draw(img)
    rows = (len(items) + cols - 1) // cols
    gap = 26
    tile_w = (SIZE - 140 - gap * (cols - 1)) / cols
    area_h = SIZE - y - (190 if footer else 110)
    tile_h = (area_h - gap * (rows - 1)) / rows
    S = 4
    palette = th.get("sheet_colors") or [th["accent2"], th["bg2"], (255, 150, 20), (30, 150, 90), (120, 60, 190)]
    for i, (label, rings) in enumerate(items):
        c, r = i % cols, i // cols
        x0, y0 = 70 + c * (tile_w + gap), y + r * (tile_h + gap)
        d.rounded_rectangle((x0 + 6, y0 + 12, x0 + tile_w + 6, y0 + tile_h + 12), radius=32, fill=(0, 0, 0, 90))
        d.rounded_rectangle((x0, y0, x0 + tile_w, y0 + tile_h), radius=32, fill=(255, 252, 244), outline=th["accent"], width=5)
        box = int(min(tile_w, tile_h - 110) * 0.74)
        xs = [p[0] for p in rings[0]]
        ys = [p[1] for p in rings[0]]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        k = box / max(w, h)
        mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        tile = Image.new("L", (box * S, box * S), 0)
        td = ImageDraw.Draw(tile)

        def tx(p):
            return ((p[0] - mx) * k + box / 2) * S, (box / 2 - (p[1] - my) * k) * S

        for j, ring in enumerate(rings):
            td.polygon([tx(p) for p in ring], fill=255 if j == 0 else 0)
        tile = tile.resize((box, box), Image.LANCZOS)
        img.paste(Image.new("RGB", (box, box), palette[i % len(palette)]),
                  (int(x0 + (tile_w - box) / 2), int(y0 + 24 + (tile_h - 80 - box) / 2)), tile)
        f = fit_font(d, label, "bold", int(tile_w - 24), 54, 28)
        wl = d.textlength(label, font=f)
        d.text((x0 + (tile_w - wl) / 2, y0 + tile_h - 66), label, font=f, fill=(40, 24, 24))
    if footer:
        centered(d, SIZE - 160, footer, font("bold", 56), th["text"], shadow=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def pdf_guide(out: Path, pages: Sequence[Tuple[str, Sequence[str]]], theme: str = "christmas") -> Path:
    """Simple multi-page A4-ish PDF (Pillow) - one (title, paragraphs) tuple per page."""
    th = THEMES[theme]
    W, H = 1654, 2339  # A4 @ 200 dpi
    imgs: List[Image.Image] = []
    for title, paras in pages:
        im = Image.new("RGB", (W, H), (255, 252, 246))
        im.paste(vgrad(W, 230, th["bg"], th["bg2"]), (0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 230, W, 246), fill=th["accent"])
        d.text((90, 62), title, font=fit_font(d, title, "anton", W - 180, 110), fill=(255, 255, 255))
        y = 320
        fb = font("regular", 40)
        for p in paras:
            if p.startswith("# "):
                y += 14
                d.text((90, y), p[2:], font=font("bold", 52), fill=th["accent2"])
                y += 80
                continue
            for line in wrap(d, p, fb, W - 180):
                d.text((90, y), line, font=fb, fill=(40, 40, 45))
                y += 56
            y += 22
        imgs.append(im)
    out.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(out, "PDF", save_all=True, append_images=imgs[1:], resolution=200.0)
    return out
