"""Military mom / wife sublimation designs: AI-painted elements (boots, dog tags, caps, anchors...) + camo-filled outlined branch lettering + script.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.clipart.military_pack [--elements] [--compose] [--only N,N] [--redo key,key]

--elements : generate + cut the element art (ComfyUI, needs the GPU queue free)   -> {root}/elements/{raw,cut}
--compose  : build the designs from the cut elements (CPU only)                   -> {root}/png/<NNN_branch_role_layout>.png
No flags   : both. Elements are cached; --redo regenerates only the named elements.
Original art only: no insignia, seals, logos or branch emblems - generic boots, tags, caps, anchors, helmets, jets, wheels.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from etsy_factory.clipart import comfy_gen as G
from etsy_factory.clipart import cutkey as K
from etsy_factory.clipart import matte_comfy as MC

FONTS = Path(r"F:\WORKHORSE\etsy_factory\fonts")
ROOT = Path(r"F:\WORKHORSE\workspace\etsy_clipart\military_mom_wife_sublimation_png")
SLUG = "military_mom_wife_sublimation_png"

STYLE = ("highly detailed digital painting clipart, realistic shading with clean dark outline, rich colors, polished sublimation t-shirt graphic, "
         "single isolated object centered on a plain flat pure magenta (#FF00FF) background, perfectly uniform, no gradient, the whole object fully "
         "visible with generous margin, the magenta is not used anywhere on the object, no text, no letters, no logo, no insignia, no watermark, no cast shadow")

# element key -> (prompt, branches that use it)
ELEMENTS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "boots_tags_flag": ("a pair of black leather military combat boots with laces standing together, blank metal dog tags on a ball chain draped over one boot, "
                        "and a small american flag tucked behind them", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "boots_tags_heart": ("a pair of tan desert combat boots with laces, blank silver dog tags on a ball chain, and a small red heart resting on top",
                         ("army", "marine", "military", "airforce")),
    "dogtags_flag": ("two blank silver military dog tags on a ball chain with a small rippled american flag behind them", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "dogtags_heart": ("blank silver dog tags on a ball chain forming a loop with a red heart charm hanging from it", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "flag_heart": ("a heart shaped american flag with waving stripes and a field of white stars", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "flag_waving": ("a waving american flag on a short wooden pole", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "star_gold": ("a shiny gold five pointed star with a thin dark outline and a soft metallic shine", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "helmet_army": ("a green military combat helmet with a camouflage cover and a chin strap", ("army", "marine", "military")),
    "cap_sailor": ("a white sailor dixie cup hat with a thin navy blue band, front view", ("navy",)),
    "cap_officer": ("a navy blue and white naval officer peaked cap with a gold braid band and no badge, front three quarter view", ("navy", "coastguard")),
    "anchor_rope": ("a large dark navy blue ship anchor with a coiled brown rope wrapped around the shaft", ("navy", "coastguard")),
    "wheel_ship": ("a brown wooden ship steering wheel with brass details", ("navy", "coastguard")),
    "lifering": ("a red and white lifebuoy ring with a rope", ("coastguard", "navy")),
    "jet_fighter": ("a gray fighter jet flying upward at an angle, side view, no markings", ("airforce",)),
    "wings_gold": ("a pair of gold feathered wings spread wide with a small blue star in the center, no letters", ("airforce",)),
    "aviator": ("a pair of gold framed aviator sunglasses with blue gradient lenses", ("airforce", "military")),
    "cover_field": ("a tan military field cap with a flat top and short brim, no badge", ("marine", "army", "military")),
    "binoculars": ("a pair of black military field binoculars on a strap", ("army", "military")),
    "compass": ("a brass pocket compass with an open lid and a red needle", ("navy", "army", "marine", "military", "coastguard")),
    "ribbon_bow": ("a red white and blue satin ribbon bow with long tails", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "sunflower": ("a bright yellow sunflower with green leaves", ("army", "navy", "airforce", "marine", "coastguard", "military")),
    "coffee": ("a camo patterned travel coffee cup with a lid", ("army", "marine", "military")),
}

# branch -> (display lines, camo palette, block font, ink colour for the script)
BRANCHES: Dict[str, Dict] = {
    "army": dict(word=["ARMY"], camo=[(52, 62, 38), (92, 104, 60), (150, 140, 96), (36, 36, 30)], font="BlackOpsOne-Regular.ttf", ink=(36, 48, 34)),
    "navy": dict(word=["NAVY"], camo=[(24, 44, 90), (60, 100, 160), (150, 170, 200), (22, 28, 44)], font="Bungee-Regular.ttf", ink=(22, 38, 84)),
    "airforce": dict(word=["AIR", "FORCE"], camo=[(34, 64, 120), (86, 128, 178), (170, 190, 210), (40, 48, 62)], font="BlackOpsOne-Regular.ttf", ink=(24, 46, 100)),
    "marine": dict(word=["MARINE"], camo=[(46, 56, 36), (110, 100, 62), (176, 160, 110), (30, 28, 24)], font="BlackOpsOne-Regular.ttf", ink=(60, 40, 26)),
    "coastguard": dict(word=["COAST", "GUARD"], camo=[(24, 54, 100), (70, 120, 170), (200, 210, 224), (150, 36, 44)], font="Bungee-Regular.ttf", ink=(20, 44, 92)),
    "military": dict(word=["MILITARY"], camo=[(52, 62, 38), (110, 100, 62), (176, 160, 110), (34, 36, 30)], font="BlackOpsOne-Regular.ttf", ink=(40, 50, 36)),
}
ROLES = {"mom": ("Proud", "Mom"), "wife": ("Proud", "Wife"), "momlife": ("", "Mom Life"), "wifelife": ("", "Wife Life")}
SCRIPTS = ["MrDafoe-Regular.ttf", "Norican-Regular.ttf", "OleoScript-Bold.ttf"]

W, H = 3600, 3200   # roomy canvas; the result is cropped to its content, so nothing may touch the edge


# --------------------------------------------------------------------------------------------------------- elements
def element_jobs(redo: Tuple[str, ...] = ()) -> List[Tuple[str, str, int]]:
    jobs = []
    for i, (k, (prompt, _br)) in enumerate(ELEMENTS.items()):
        for v in (1, 2):
            name = f"{k}_v{v}"
            seed = 78000 + i * 31 + v * 7 + (1000 if any(r in name for r in redo) else 0)
            jobs.append((name, f"{prompt}. {STYLE}", seed))
    return jobs


def make_elements(redo: Tuple[str, ...] = ()) -> None:
    raw, cut = ROOT / "elements" / "raw", ROOT / "elements" / "cut"
    raw.mkdir(parents=True, exist_ok=True)
    cut.mkdir(parents=True, exist_ok=True)
    for r in redo:
        for f in list(raw.glob(f"*{r}*.png")) + list(cut.glob(f"*{r}*.png")):
            f.unlink()
    jobs = element_jobs(redo)
    G.DEFAULT_ENGINE = "flux"        # richer painted detail than Z-Image for objects
    res = G.generate_many(jobs, raw, parallel=2, progress=lambda i, n, nm: print(f"  gen [{i}/{n}] {nm}", flush=True))
    for name, _p, _s in jobs:
        src = res.get(name)
        dst = cut / f"{name}.png"
        if not src or dst.exists():
            continue
        mask = MC.matte_mask(src)
        st = K.cut_key(src, dst, long_side=2000, matte=mask) if mask is not None else K.cut_key(src, dst, long_side=2000)
        print(f"  cut {name}: {st['mode'] if st else 'FAILED'}", flush=True)


# --------------------------------------------------------------------------------------------------------- textures
def camo(w: int, h: int, pal: List[Tuple[int, int, int]], seed: int) -> Image.Image:
    """Digital pixel camouflage: blob field thresholded into the palette colours, blocky edges, light grain."""
    from scipy import ndimage as ndi
    rnd = np.random.RandomState(seed)
    cell = 16
    gw, gh = w // cell + 2, h // cell + 2
    layers = []
    for sigma in (7.0, 3.2):
        n = ndi.gaussian_filter(rnd.randn(gh, gw), sigma)
        layers.append((n - n.mean()) / (n.std() + 1e-6))
    f = layers[0] * 0.75 + layers[1] * 0.45
    qs = np.quantile(f, [0.34, 0.62, 0.84])
    idx = np.digitize(f, qs)
    pal_arr = np.array(pal, dtype=np.uint8)
    small = pal_arr[idx]
    img = Image.fromarray(small, "RGB").resize((gw * cell, gh * cell), Image.NEAREST).crop((0, 0, w, h))
    grain = rnd.normal(0, 5, (h, w, 1))
    arr = np.clip(np.asarray(img).astype(np.float32) + grain, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / file), size)


def text_mask(text: str, file: str, size: int, spacing: int = 0) -> Image.Image:
    f = _font(file, size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    adv = [probe.textlength(c, font=f) for c in text]
    tw = int(sum(adv) + spacing * (len(text) - 1)) + 60
    asc, desc = f.getmetrics()
    m = Image.new("L", (tw, asc + desc + 40), 0)
    d = ImageDraw.Draw(m)
    x = 30
    for c, a in zip(text, adv):
        d.text((x, 10), c, font=f, fill=255)
        x += a + spacing
    bb = m.getbbox()
    return m.crop(bb) if bb else m


def fit_mask(text: str, file: str, max_w: int, max_h: int, spacing: int = 0) -> Image.Image:
    lo, hi = 80, 1400
    best = text_mask(text, file, lo, spacing)
    while hi - lo > 12:
        mid = (lo + hi) // 2
        m = text_mask(text, file, mid, spacing)
        if m.width <= max_w and m.height <= max_h:
            best, lo = m, mid
        else:
            hi = mid
    return best


def chunky_word(lines: List[str], font: str, pal: List[Tuple[int, int, int]], seed: int, max_w: int, max_h: int) -> Image.Image:
    """Camo-filled block lettering with a dark outline and a white halo (sticker look), like the layered sublimation references."""
    per_h = max_h // len(lines)
    masks = [fit_mask(l, font, max_w, per_h - 60, spacing=14) for l in lines]
    gap = 40
    bw = max(m.width for m in masks)
    bh = sum(m.height for m in masks) + gap * (len(masks) - 1)
    pad = 70
    mask = Image.new("L", (bw + 2 * pad, bh + 2 * pad), 0)
    y = pad
    for m in masks:
        mask.paste(m, (pad + (bw - m.width) // 2, y))
        y += m.height + gap
    tex = camo(mask.width, mask.height, pal, seed)
    layer = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    halo = mask.filter(ImageFilter.MaxFilter(2 * 26 + 1)).filter(ImageFilter.GaussianBlur(1.5))
    white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
    white.putalpha(halo)
    layer.alpha_composite(white)
    ink = mask.filter(ImageFilter.MaxFilter(2 * 11 + 1))
    black = Image.new("RGBA", mask.size, (20, 20, 26, 255))
    black.putalpha(ink)
    layer.alpha_composite(black)
    fill = tex.convert("RGBA")
    fill.putalpha(mask)
    layer.alpha_composite(fill)
    # thin light inner edge for depth
    inner = mask.filter(ImageFilter.MinFilter(7))
    edge = Image.eval(Image.composite(mask, Image.new("L", mask.size, 0), mask), lambda v: v)
    rim = Image.new("RGBA", mask.size, (255, 255, 255, 70))
    ring = Image.new("L", mask.size, 0)
    ring.paste(mask, (0, 0))
    ring = Image.fromarray(np.clip(np.asarray(ring).astype(np.int16) - np.asarray(inner).astype(np.int16), 0, 255).astype(np.uint8), "L")
    rim.putalpha(ring.point(lambda v: min(255, int(v * 0.28))))
    layer.alpha_composite(rim)
    return layer


def script_word(text: str, file: str, height: int, col: Tuple[int, int, int], outline: Optional[Tuple[int, int, int]] = (255, 255, 255), max_w: int = 2900) -> Image.Image:
    m = fit_mask(text, file, max_w, height)
    pad = 36
    big = Image.new("L", (m.width + 2 * pad, m.height + 2 * pad), 0)
    big.paste(m, (pad, pad))
    layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
    if outline:
        halo = big.filter(ImageFilter.MaxFilter(2 * 12 + 1)).filter(ImageFilter.GaussianBlur(1.2))
        o = Image.new("RGBA", big.size, outline + (255,))
        o.putalpha(halo)
        layer.alpha_composite(o)
    c = Image.new("RGBA", big.size, col + (255,))
    c.putalpha(big)
    layer.alpha_composite(c)
    return layer


def with_shadow(img: Image.Image, dx: int = 14, dy: int = 18, blur: int = 16, alpha: int = 90) -> Image.Image:
    pad = blur * 3 + max(abs(dx), abs(dy))
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
    sh.putalpha(img.getchannel("A").point(lambda v: v * alpha // 255))
    base = Image.new("RGBA", out.size, (0, 0, 0, 0))
    base.paste(sh, (pad + dx, pad + dy))
    base = base.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(base)
    out.alpha_composite(img, (pad, pad))
    return out


def load_element(name: str, height: int, flip: bool = False) -> Optional[Image.Image]:
    p = ROOT / "elements" / "cut" / f"{name}.png"
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    s = height / im.height
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(im).astype(np.int16)                    # despill: remove the magenta key tint left on edges / soft shadows
    spill = np.clip(np.minimum(a[..., 0], a[..., 2]) - a[..., 1] - 8, 0, 255)
    a[..., 0] -= spill
    a[..., 2] -= spill
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    return im


def star_img(r: int, col=(236, 190, 70), outline=(30, 34, 46)) -> Image.Image:
    S = r * 2 + 30
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [((S / 2) + (r if i % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + i * 36)),
            (S / 2) + (r if i % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + i * 36))) for i in range(10)]
    d.polygon(pts, fill=col, outline=outline, width=6)
    return im


def sparkle_img(r: int, col=(255, 255, 255)) -> Image.Image:
    S = r * 2 + 10
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    d.polygon([(c, 5), (c + r * 0.16, c - r * 0.16), (S - 5, c), (c + r * 0.16, c + r * 0.16), (c, S - 5), (c - r * 0.16, c + r * 0.16), (5, c), (c - r * 0.16, c - r * 0.16)], fill=col)
    return im


# --------------------------------------------------------------------------------------------------------- composition
def pick(rnd: random.Random, branch: str, pool_keys: Optional[List[str]] = None, exclude: Tuple[str, ...] = ()) -> str:
    keys = [k for k, (_p, brs) in ELEMENTS.items() if branch in brs and k not in exclude and (pool_keys is None or k in pool_keys)]
    keys = [k for k in keys if (ROOT / "elements" / "cut" / f"{k}_v1.png").exists()]
    return rnd.choice(keys) if keys else ""


def compose(branch: str, role: str, layout: str, idx: int, out: Path) -> Path:
    rnd = random.Random(idx * 97 + 13)
    cfg = BRANCHES[branch]
    pre, post = ROLES[role]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ink = cfg["ink"]
    script_font = SCRIPTS[idx % len(SCRIPTS)]
    one = len(cfg["word"]) == 1
    if layout in ("A", "C"):      # narrower word so the elements sit beside it instead of covering the letters
        word = chunky_word(cfg["word"], cfg["font"], cfg["camo"], idx * 7 + 3, 1900 if one else 1450, 900 if one else 1180)
    else:
        word = chunky_word(cfg["word"], cfg["font"], cfg["camo"], idx * 7 + 3, 2500 if one else 1900, 900 if one else 1180)
    word = with_shadow(word)
    hero_key = pick(rnd, branch, ["boots_tags_flag", "boots_tags_heart", "dogtags_flag", "dogtags_heart"])
    second = pick(rnd, branch, None, (hero_key,))
    third = pick(rnd, branch, ["flag_heart", "flag_waving", "star_gold", "ribbon_bow", "sunflower", "compass", "dogtags_heart"], (hero_key, second))
    ve = f"_v{1 + idx % 2}"
    wx = (W - word.width) // 2

    def place(img: Optional[Image.Image], x: int, y: int, shadow: bool = True) -> None:
        if img is None:
            return
        canvas.alpha_composite(with_shadow(img) if shadow else img, (max(0, x), max(0, y)))

    if layout == "A":          # script top-left, word left, hero element BESIDE the word (never over the letters), script under the word's right edge
        wy, wx = 760, 140
        canvas.alpha_composite(word, (wx, wy))
        right_x = wx + word.width + 40
        if pre:
            s_pre = script_word(pre, script_font, 560, ink)
            place(s_pre, wx, wy - 430, False)
        s_post = script_word(post, script_font, 700, ink, max_w=word.width + 40)
        place(s_post, max(wx, wx + word.width - s_post.width + 40), wy + word.height - 150, False)
        place(load_element(hero_key + ve, 1000) if hero_key else None, right_x, wy - 60)
        place(load_element(third + ve, 480) if third else None, right_x + 300, 120)
        place(load_element(second + ve, 560) if second else None, right_x + 60, wy + word.height - 20)
    elif layout == "B":        # word on top, big script across, elements row at the bottom
        wy = 140
        canvas.alpha_composite(word, (wx, wy))
        s_post = script_word((pre + " " + post).strip(), script_font, 660, ink)
        place(s_post, (W - s_post.width) // 2, wy + word.height - 150, False)
        base_y = wy + word.height + s_post.height - 160
        place(load_element(second + ve, 760, flip=True) if second else None, 180, base_y)
        place(load_element(hero_key + ve, 980) if hero_key else None, (W - 1000) // 2 + 120, base_y - 80)
        place(load_element(third + ve, 640) if third else None, W - 880, base_y + 40)
    else:                      # "C": mirror of A - hero column on the LEFT, word to its right, script above / under the word
        wy, lx = 760, 140
        hero_im = load_element(hero_key + ve, 1000) if hero_key else None
        wx = lx + max(hero_im.width if hero_im else 0, 700) + 40
        canvas.alpha_composite(word, (wx, wy))
        if pre:
            s_pre = script_word(pre, script_font, 560, ink)
            place(s_pre, wx, wy - 430, False)
        s_post = script_word(post, script_font, 700, ink, max_w=word.width + 40)
        place(s_post, max(wx, wx + word.width - s_post.width + 40), wy + word.height - 150, False)
        place(hero_im, lx, wy - 60)
        place(load_element(third + ve, 480) if third else None, lx + 200, 120)
        place(load_element(second + ve, 560) if second else None, lx + 60, wy + word.height - 20)
    content = canvas.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0, W, H)
    cx0, cy0, cx1, cy1 = content
    for _ in range(9):         # sparkle / star accents in empty areas INSIDE the content box (keeps the crop tight so mockups stay centred)
        r = rnd.choice([34, 46, 60])
        sp = star_img(r) if rnd.random() < 0.45 else sparkle_img(r + 10, (255, 255, 255) if rnd.random() < 0.5 else (236, 190, 70))
        x, y = rnd.randint(cx0, max(cx0 + 1, cx1 - sp.width)), rnd.randint(cy0, max(cy0 + 1, cy1 - sp.height))
        probe = canvas.crop((x, y, x + sp.width, y + sp.height)).getchannel("A")
        if max(probe.getdata()) < 8:
            canvas.alpha_composite(sp, (x, y))
    box = canvas.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    canvas = canvas.crop(box)
    pad = 40
    final = Image.new("RGBA", (canvas.width + 2 * pad, canvas.height + 2 * pad), (0, 0, 0, 0))
    final.paste(canvas, (pad, pad))
    out.parent.mkdir(parents=True, exist_ok=True)
    K.save_adaptive(final, out)
    return out


def plan() -> List[Tuple[int, str, str, str]]:
    items = []
    i = 1
    for layout in ("A", "B", "C"):
        for branch in BRANCHES:
            for role in ("mom", "wife"):
                items.append((i, branch, role, layout))
                i += 1
    for branch in BRANCHES:                           # "<Branch> Mom Life / Wife Life" variants (no 'Proud')
        for role in ("momlife", "wifelife"):
            items.append((i, branch, role, "A" if i % 2 else "C"))
            i += 1
    return items


def compose_all(only: Optional[List[int]] = None) -> None:
    png = ROOT / "png"
    for idx, branch, role, layout in plan():
        if only and idx not in only:
            continue
        name = f"{idx:03d}_{branch}_{role}_{layout}_mil"
        out = png / f"{name}.png"
        compose(branch, role, layout, idx, out)
        print("  composed", name, flush=True)


def contact(out: Path, per: int = 12) -> None:
    files = sorted((ROOT / "png").glob("*.png"))
    sheets = ROOT / "sheets"
    sheets.mkdir(exist_ok=True)
    for old in sheets.glob("*.jpg"):
        old.unlink()
    S, cols = 560, 4
    for si in range(0, len(files), per):
        chunk = files[si:si + per]
        rows = (len(chunk) + cols - 1) // cols
        sh = Image.new("RGB", (S * cols, S * rows), (250, 247, 240))
        d = ImageDraw.Draw(sh)
        for i, f in enumerate(chunk):
            im = Image.open(f).convert("RGBA")
            im.thumbnail((S - 30, S - 44))
            x, y = (i % cols) * S, (i // cols) * S
            sh.paste(im, (x + (S - im.width) // 2, y + 8 + (S - 44 - im.height) // 2), im)
            d.text((x + 8, y + S - 24), f.stem, fill=(80, 80, 80))
        sh.save(sheets / f"sheet_{si // per + 1:02d}.jpg", quality=90)


if __name__ == "__main__":
    args = sys.argv[1:]
    redo = tuple(args[args.index("--redo") + 1].split(",")) if "--redo" in args else ()
    only = [int(x) for x in args[args.index("--only") + 1].split(",")] if "--only" in args else None
    do_el = "--elements" in args or not ("--compose" in args)
    do_co = "--compose" in args or not ("--elements" in args)
    if do_el:
        make_elements(redo)
    if do_co:
        compose_all(only)
        contact(ROOT / "sheets")
