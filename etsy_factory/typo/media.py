"""Media kit for quote packs: dense-collage cover (like the top sellers), contact sheets, info cards, and photo mockups
(shirt / mug / tote / sign) composited onto ComfyUI blank-product photos with fabric shading + displacement."""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import comfy_backgrounds as cb

FONT_DIR = Path(r"F:\WORKHORSE\etsy_factory\fonts")
SIZE = 2400
RGB = Tuple[int, int, int]
MOCK_DIR = Path(r"F:\WORKHORSE\workspace\etsy_mockups")


def F(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def anton(s): return F("Anton-Regular.ttf", s)
def lilita(s): return F("LilitaOne-Regular.ttf", s)
def pacifico(s): return F("Pacifico-Regular.ttf", s)
def poppins(s): return F("Poppins-Bold.ttf", s)
def poppins_x(s): return F("Poppins-ExtraBold.ttf", s)


def text_w(d: ImageDraw.ImageDraw, t: str, f) -> int:
    b = d.textbbox((0, 0), t, font=f)
    return b[2] - b[0]


def fit(d, t: str, fn, max_w: int, start: int, min_size: int = 30):
    s = start
    while s > min_size and text_w(d, t, fn(s)) > max_w:
        s -= 4
    return fn(s)


def outlined(img: Image.Image, xy, t: str, f, fill: RGB, stroke: RGB, sw: int, anchor: str = "ma", shadow: int = 0) -> None:
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((xy[0] + shadow, xy[1] + shadow), t, font=f, fill=(0, 0, 0, 90), anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0, 90))
    d.text(xy, t, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke)


def grad_fill_text(img: Image.Image, xy, t: str, f, top: RGB, bottom: RGB, stroke: RGB, sw: int, anchor: str = "ma") -> None:
    d = ImageDraw.Draw(img)
    bb = d.textbbox(xy, t, font=f, anchor=anchor, stroke_width=sw)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    m = Image.new("L", (w + 4, h + 4), 0)
    ImageDraw.Draw(m).text((2 - 0, 2 - 0), t, font=f, fill=255, anchor="la", stroke_width=0)
    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(base).text(xy, t, font=f, fill=stroke + (255,), anchor=anchor, stroke_width=sw, stroke_fill=stroke + (255,))
    img.alpha_composite(base)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(xy, t, font=f, fill=(255, 255, 255, 255), anchor=anchor)
    g = Image.new("RGBA", img.size)
    gd = ImageDraw.Draw(g)
    y0, y1 = bb[1], bb[3]
    for y in range(max(0, y0), min(img.size[1], y1)):
        k = (y - y0) / max(1, y1 - y0)
        gd.line([(0, y), (img.size[0], y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)) + (255,))
    g.putalpha(lay.split()[3])
    img.alpha_composite(g)


def ink_crop(im: Image.Image, bg=(255, 255, 255), pad: int = 6) -> Image.Image:
    diff = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, bg))
    bb = diff.getbbox()
    if not bb:
        return im
    return im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)))


def rounded(size, r, fill, outline=None, width=0) -> Image.Image:
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=r, fill=fill, outline=outline, width=width)
    return im


def shadowed(base: Image.Image, layer: Image.Image, xy, blur=30, off=(0, 18), alpha=110) -> None:
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    a = layer.split()[3].point(lambda p: int(p * alpha / 255))
    sh.paste((0, 0, 0, 255), (xy[0] + off[0], xy[1] + off[1]), a)
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    base.alpha_composite(layer, xy)


# ----------------------------------------------------------------------------- thumbnails
def load_thumbs(thumbs_dir: Path, meta: Sequence[Dict], colored: bool = False) -> List[Image.Image]:
    out = []
    for m in meta:
        p = thumbs_dir / (m["name"] + ("_c" if colored else "") + ".png")
        if p.exists():
            out.append(ink_crop(Image.open(p).convert("RGB")))
    return out


# ----------------------------------------------------------------------------- cover
def cover(meta, thumbs_dir: Path, out: Path, big: str, title_lines: Sequence[str], sub: str, accent: RGB, ink: RGB,
          chips: Sequence[Tuple[str, RGB]], seed: int = 3, burst: str = "INSTANT\nDOWNLOAD") -> Path:
    rng = random.Random(seed)
    th = load_thumbs(thumbs_dir, meta, colored=False)
    base = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    # masonry rows of the real designs, edge to edge
    row_h = 300
    y = -40
    i = rng.randrange(len(th))
    order = th[:]
    rng.shuffle(order)
    k = 0
    while y < SIZE:
        x = -rng.randrange(0, 150)
        while x < SIZE:
            t = order[k % len(order)]
            k += 1
            s = row_h / t.height
            w = int(t.width * s)
            w = min(w, 900)
            tt = t.resize((max(40, int(t.width * s)), row_h), Image.LANCZOS)
            base.paste(tt.convert("RGBA"), (x, y))
            x += tt.width + 36
        y += row_h + 26
    base = ImageEnhance.Contrast(base.convert("RGB")).enhance(1.0).convert("RGBA")
    # soft white haze so the card pops
    haze = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    hd = ImageDraw.Draw(haze)
    hd.ellipse((200, 330, SIZE - 200, SIZE - 330), fill=(255, 255, 255, 120))
    base.alpha_composite(haze.filter(ImageFilter.GaussianBlur(120)))
    # centre card
    cw, ch = 1820, 1620
    cx, cy = (SIZE - cw) // 2, (SIZE - ch) // 2 + 10
    card = rounded((cw, ch), 90, (255, 255, 255, 255), outline=ink + (255,), width=12)
    shadowed(base, card, (cx, cy), blur=36, off=(0, 26), alpha=140)
    d = ImageDraw.Draw(base)
    # top ribbon
    rb = "COMMERCIAL USE INCLUDED"
    f = fit(d, rb, poppins_x, 1300, 60)
    tw = text_w(d, rb, f)
    pill = rounded((tw + 120, 108), 54, accent + (255,))
    base.alpha_composite(pill, (SIZE // 2 - (tw + 120) // 2, cy - 54))
    d.text((SIZE // 2, cy), rb, font=f, fill=(255, 255, 255), anchor="mm")
    # big number (laid out from measured glyph boxes so nothing overlaps)
    fb = anton(540)
    bbn = d.textbbox((0, 0), big, font=fb, anchor="ma")
    ntop = cy + 120
    grad_fill_text(base, (SIZE // 2, ntop - bbn[1]), big, fb, tuple(min(255, int(c * 1.15 + 20)) for c in accent), tuple(int(c * 0.78) for c in accent), ink, 16)
    ty = ntop + (bbn[3] - bbn[1]) + 70
    for ln in title_lines:
        fl = fit(d, ln, anton, cw - 200, 180, 80)
        bb = d.textbbox((0, 0), ln, font=fl, anchor="ma")
        d.text((SIZE // 2, ty - bb[1]), ln, font=fl, fill=ink, anchor="ma")
        ty += (bb[3] - bb[1]) + 36
    fs = fit(d, sub, pacifico, cw - 400, 110, 50)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    d.text((SIZE // 2, ty + 10 - bbs[1]), sub, font=fs, fill=accent, anchor="ma")
    sub_bottom = ty + 10 + (bbs[3] - bbs[1])
    # format chips
    n = len(chips)
    r = 100
    gap = 44
    total = n * 2 * r + (n - 1) * gap
    x0 = SIZE // 2 - total // 2 + r
    cyy = cy + ch - 150
    assert sub_bottom < cyy - r - 10, f"cover layout overlap: subtitle ends {sub_bottom}, chips start {cyy - r}"
    for j, (label, col) in enumerate(chips):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=ink, width=8)
        fc = fit(d, label, anton, 2 * r - 40, 80, 30)
        d.text((xx, cyy + 4), label, font=fc, fill=(255, 255, 255), anchor="mm")
    # bottom machine strip
    strip = "CRICUT  *  SILHOUETTE  *  SUBLIMATION  *  GLOWFORGE"
    fs2 = fit(d, strip, poppins_x, SIZE - 260, 62, 30)
    sw = text_w(d, strip, fs2)
    sp = rounded((sw + 100, 110), 55, ink + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 100) // 2, SIZE - 170))
    d.text((SIZE // 2, SIZE - 115), strip, font=fs2, fill=(255, 255, 255), anchor="mm")
    # starburst
    bx, by, br = SIZE - 270, 280, 215
    pts = []
    for q in range(40):
        a = math.pi * 2 * q / 40
        rr = br if q % 2 == 0 else br * 0.8
        pts.append((bx + rr * math.cos(a), by + rr * math.sin(a)))
    star = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(star).polygon(pts, fill=(255, 214, 0, 255), outline=ink + (255,), width=8)
    ImageDraw.Draw(star).polygon([(bx + (p[0] - bx) * 0.84, by + (p[1] - by) * 0.84) for p in pts], outline=ink + (255,), width=4)
    base.alpha_composite(star.filter(ImageFilter.GaussianBlur(0)))
    lines = burst.split("\n")
    fz = anton(76)
    for li, l in enumerate(lines):
        ImageDraw.Draw(base).text((bx, by + (li - (len(lines) - 1) / 2) * 84), l, font=fz, fill=ink, anchor="mm")
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


# ----------------------------------------------------------------------------- contact sheets
def sheet(meta, thumbs_dir: Path, out: Path, title: str, subtitle: str, accent: RGB, ink: RGB, bg: RGB, start: int, count: int,
          cols: int = 4, rows: int = 5, colored: bool = True) -> Path:
    items = meta[start:start + count]
    th = load_thumbs(thumbs_dir, items, colored=colored)
    base = Image.new("RGBA", (SIZE, SIZE), bg + (255,))
    d = ImageDraw.Draw(base)
    # title block
    ft = fit(d, title.upper(), anton, SIZE - 240, 150, 70)
    d.text((SIZE // 2, 70), title.upper(), font=ft, fill=ink, anchor="ma")
    fs = fit(d, subtitle, pacifico, SIZE - 400, 74, 36)
    d.text((SIZE // 2, 70 + ft.size + 18), subtitle, font=fs, fill=accent, anchor="ma")
    top = 70 + ft.size + fs.size + 80
    pad = 56
    gw = (SIZE - pad * 2 - (cols - 1) * 36) // cols
    gh = (SIZE - top - pad - (rows - 1) * 36) // rows
    for i, t in enumerate(th[:cols * rows]):
        r, c = divmod(i, cols)
        x = pad + c * (gw + 36)
        y = top + r * (gh + 36)
        card = rounded((gw, gh), 40, (255, 255, 255, 255), outline=ink + (60,), width=3)
        shadowed(base, card, (x, y), blur=14, off=(0, 8), alpha=70)
        s = min((gw - 64) / t.width, (gh - 64) / t.height)
        tt = t.resize((max(1, int(t.width * s)), max(1, int(t.height * s))), Image.LANCZOS)
        base.paste(tt.convert("RGBA"), (x + (gw - tt.width) // 2, y + (gh - tt.height) // 2))
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


# ----------------------------------------------------------------------------- info cards
def info_card(out: Path, title: str, kicker: str, rows: Sequence[Tuple[str, str]], accent: RGB, ink: RGB, bg: RGB,
              preview: Optional[Image.Image] = None, footer: str = "", pill_colors: Optional[Sequence[RGB]] = None) -> Path:
    base = Image.new("RGBA", (SIZE, SIZE), bg + (255,))
    d = ImageDraw.Draw(base)
    d.rectangle((0, 0, SIZE, 430), fill=ink)
    d.text((SIZE // 2, 70), kicker.upper(), font=poppins_x(58), fill=accent, anchor="ma")
    ft = fit(d, title.upper(), anton, SIZE - 240, 170, 80)
    d.text((SIZE // 2, 200), title.upper(), font=ft, fill=(255, 255, 255), anchor="ma")
    y = 520
    h = int((SIZE - y - (260 if footer else 120)) / max(len(rows), 1))
    h = min(h, 290)
    for i, (head, body) in enumerate(rows):
        col = pill_colors[i % len(pill_colors)] if pill_colors else (accent if i % 2 == 0 else ink)
        pill = rounded((520, h - 40), 36, col + (255,))
        base.alpha_composite(pill, (110, y))
        fh = fit(d, head, anton, 440, 78, 34)
        d.text((110 + 260, y + (h - 40) // 2), head, font=fh, fill=(255, 255, 255), anchor="mm")
        fb = poppins(52)
        lines = _wrap(d, body, fb, SIZE - 780 - 110)
        ly = y + (h - 40) // 2 - (len(lines) * 62) // 2
        for ln in lines:
            d.text((700, ly), ln, font=fb, fill=ink, anchor="la")
            ly += 62
        y += h
    if footer:
        ff = fit(d, footer, poppins, SIZE - 240, 50, 28)
        d.text((SIZE // 2, SIZE - 170), footer, font=ff, fill=ink, anchor="ma")
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def _wrap(d, text: str, f, max_w: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(d, t, f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------- mockups
def comfy_photo(name: str, prompt: str, seed: int = 11, w: int = 1344, h: int = 1344, neg: Optional[str] = None) -> Optional[Path]:
    """Generate (cached) a blank-product photo with ComfyUI SDXL."""
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    out = MOCK_DIR / f"{name}_{seed}.png"
    if out.exists():
        return out
    if not cb.available():
        return None
    import uuid, time, urllib.parse
    wf = cb._workflow(prompt, seed, w, h, steps=32, cfg=6.0)
    wf["3"]["inputs"]["text"] = neg or ("text, letters, logo, print, graphic, pattern, watermark, people, hands, faces, wrinkled mess, "
                                         "cartoon, illustration, deformed, extra objects")
    pid = cb._post("/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 420:
        hist = json.loads(cb._get(f"/history/{pid}"))
        if pid in hist and hist[pid].get("outputs"):
            img = hist[pid]["outputs"]["7"]["images"][0]
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img["type"]})
            out.write_bytes(cb._get("/view?" + q, timeout=60))
            return out
        time.sleep(1.5)
    return None


def place_on_fabric(photo: Image.Image, design: Image.Image, box: Tuple[int, int, int, int], opacity: float = 0.96,
                    disp: float = 6.0, texture: float = 0.55) -> Image.Image:
    """Composite an RGBA design into `box` of `photo`, following the fabric shading and folds (displacement from luminance)."""
    import cv2
    ph = np.asarray(photo.convert("RGB")).astype(np.float32)
    H, W = ph.shape[:2]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    s = min(bw / design.width, bh / design.height)
    dw, dh = max(1, int(design.width * s)), max(1, int(design.height * s))
    ds = design.resize((dw, dh), Image.LANCZOS).convert("RGBA")
    ox, oy = x0 + (bw - dw) // 2, y0 + (bh - dh) // 2
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(ds, (ox, oy))
    lay = np.asarray(layer).astype(np.float32) / 255.0
    lum = cv2.cvtColor(ph.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(lum, (0, 0), 9)
    # displacement from the smoothed luminance gradient (folds push the print around)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    nrm = 1.0 / (np.abs(blur).mean() + 1e-3)
    mapx, mapy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    mapx += gx * nrm * disp * 6
    mapy += gy * nrm * disp * 6
    lay = cv2.remap(lay, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    med = float(np.median(blur[max(0, oy):oy + dh, max(0, ox):ox + dw])) or 1.0
    shade = np.clip(blur / med, 0.55, 1.35)
    hf = np.clip(lum - cv2.GaussianBlur(lum, (0, 0), 2.2), -40, 40) / 255.0
    tex = 1.0 + hf * texture * 2.2
    a = lay[..., 3:4] * opacity
    col = lay[..., :3] * 255.0 * (shade[..., None] ** 0.9) * tex[..., None]
    light = lay[..., :3].mean() > 0.6
    if light:
        col = np.minimum(col, 255.0)
    out = ph * (1 - a) + col * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


MOCKUP_PROMPTS = {
    "tee_black": ("professional product photo, a plain blank black cotton t-shirt laid flat on a light oak wooden table, front view, centered, "
                  "soft natural window light, subtle fabric texture, high detail, no print, no text, no logo", (0.08, 0.20, 0.92, 0.80)),
    "tee_oat": ("professional product photo, a plain blank oatmeal beige cotton t-shirt laid flat on a white wooden table, front view, centered, "
                "soft natural window light, subtle fabric texture, high detail, no print, no text, no logo", (0.08, 0.20, 0.92, 0.80)),
    "tee_sage": ("professional product photo, a plain blank sage green cotton sweatshirt laid flat on a light wooden table, front view, centered, "
                 "soft natural window light, subtle fabric texture, high detail, no print, no text, no logo", (0.08, 0.20, 0.92, 0.80)),
    "tee_white": ("professional product photo, a plain blank white cotton t-shirt laid flat on a dark walnut wooden table, front view, centered, "
                  "soft natural light, subtle fabric texture, high detail, no print, no text, no logo", (0.08, 0.20, 0.92, 0.80)),
    "tote": ("professional product photo, a plain blank natural cream canvas tote bag with black handles hanging against a white painted brick "
             "wall, front view, centered, soft light, no print, no text, no logo", (0.08, 0.20, 0.92, 0.80)),
    "sign": ("professional product photo, a plain blank rustic whitewashed wooden plank sign hanging on a white shiplap wall with a jute rope, "
             "front view, centered, soft light, nothing written on it, no text", (0.08, 0.20, 0.92, 0.80)),
}


# Print areas (x0, y0, x1, y1 as fractions of the photo) for the cached blank-product photos (seed 11). Centres were measured from the
# BiRefNet matte of each photo (garment/bag body mid-line), NOT assumed to be 0.50: oat tee chest centre x=0.46, tote body centre x=0.455,
# black tee x=0.495. The tote box sits on the front panel below the open top (the bag front spans y=0.45-0.94). Re-measure if a photo/seed changes.
MOCKUP_BOXES = {
    "tee_black": (0.305, 0.31, 0.685, 0.57),
    "tee_oat": (0.27, 0.32, 0.65, 0.58),
    "tee_sage": (0.31, 0.30, 0.69, 0.56),
    "tee_white": (0.31, 0.30, 0.69, 0.56),
    "tote": (0.275, 0.50, 0.635, 0.80),
    "sign": (0.20, 0.30, 0.80, 0.70),
}


def save_jpg(img: Image.Image, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=94, subsampling=0)
    return out
