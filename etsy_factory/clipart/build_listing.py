"""Media kit, zips, guide and listing copy for an illustrated clipart pack made by run_pack.py.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.clipart.build_listing <cow|xmas|boho> [--no-mockups] [--drop name,name]
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory import kit
from etsy_factory import listing as lst
from etsy_factory.common import ETSY_MAX_FILE_BYTES, ETSY_MAX_FILES
from etsy_factory.clipart import packs as P
from etsy_factory.typo import cover2
from etsy_factory.typo import media as M

ROOT = Path(r"F:\WORKHORSE\workspace\etsy_clipart")
OUT = Path(r"F:\WORKHORSE\workspace\etsy_listings")

BOXES = M.MOCKUP_BOXES

# per-pack look (ribbons = [(face, dark)] x2 for the vibrant cover; vbg = collage background; chips for sheets)
LOOK: Dict[str, Dict] = {
    "cow": dict(kicker="HIGHLAND COW", sub="WESTERN  *  FLORAL  *  SUBLIMATION", grid_sub="Western * Floral * Seasonal",
                ribbons=[((176, 104, 60), (104, 58, 28)), ((78, 128, 88), (40, 82, 52))], vbg=(72, 46, 36), bg=(255, 247, 236),
                accent=(176, 104, 60), ink=(52, 36, 30), theme="sunny",
                mock=[("tee_oat", "rose_crown"), ("tote", "sunflowers"), ("tee_black", "cowboy_hat")]),
    "xmas": dict(kicker="RETRO CHRISTMAS", sub="GROOVY  *  VINTAGE  *  SUBLIMATION", grid_sub="Groovy * Vintage * Holiday",
                 ribbons=[((196, 40, 48), (120, 18, 28)), ((30, 120, 92), (14, 72, 54))], vbg=(26, 62, 56), bg=(255, 247, 232),
                 accent=(196, 40, 48), ink=(40, 30, 28), theme="christmas",
                 mock=[("tee_black", "santa_face"), ("tee_oat", "mcm_tree"), ("tote", "gingerbread_man")]),
    "boho": dict(kicker="BOHO", sub="RETRO  *  RAINBOW  *  SUBLIMATION", grid_sub="Rainbow * Daisy * Wildflower",
                 ribbons=[((204, 108, 72), (128, 60, 36)), ((84, 124, 110), (40, 78, 66))], vbg=(88, 52, 42), bg=(255, 246, 236),
                 accent=(204, 108, 72), ink=(60, 40, 34), theme="sunny",
                 mock=[("tee_oat", "butterfly"), ("tee_black", "sun"), ("tote", "daisy")]),
    # sarcastic leopard animals: dark charcoal/navy captions, so only light garments in the mockups
    "sass": dict(kicker="SARCASTIC ANIMALS", sub="LEOPARD  *  SASSY  *  SHIRT DESIGNS", grid_sub="Leopard * Sassy * Funny Animals",
                 ribbons=[((196, 132, 52), (122, 76, 22)), ((40, 56, 96), (22, 32, 64))], vbg=(48, 40, 36), bg=(255, 248, 236),
                 accent=(196, 132, 52), ink=(40, 34, 32), theme="sunny",
                 mock=[("tee_oat", "frog_tea"), ("tote", "raccoon_purse"), ("tee_white", "sloth_sleep")]),
    # military mom / wife: dark lettering with a white halo, so only light garments in the mockups
    "military": dict(kicker="MILITARY MOM & WIFE", sub="ARMY  *  NAVY  *  AIR FORCE  *  MARINES  *  COAST GUARD", grid_sub="Proud Military Mom & Wife",
                     ribbons=[((84, 104, 60), (44, 58, 32)), ((38, 62, 120), (20, 34, 74))], vbg=(34, 40, 46), bg=(250, 247, 240),
                     accent=(52, 74, 40), ink=(30, 36, 44), theme="sunny", long_side=2200,   # composed at ~3000 px, so a larger delivery than the 1900 default is honest (2600 px forced Etsy's 5 x 20 MB limit to drop 5 designs)
                     mock=[("tee_oat", "army_mom_A"), ("tote", "navy_wife_A"), ("tee_white", "marine_mom_C")]),
    # the same baby-animal art set split into two single-style listings (plush / watercolor storybook)
    "faces_plush": dict(kicker="PLUSH ANIMALS", sub="KAWAII  *  FUZZY  *  NURSERY", grid_sub="Plush * Kawaii * Nursery",
                        ribbons=[((236, 126, 160), (170, 70, 104)), ((92, 176, 168), (48, 120, 112))], vbg=(88, 52, 74), bg=(255, 244, 248),
                        accent=(226, 112, 150), ink=(70, 44, 58), theme="sunny",
                        mock=[("tee_white", "panda"), ("tote", "fox"), ("tee_oat", "bunny")]),
    "faces_story": dict(kicker="WATERCOLOR ANIMALS", sub="STORYBOOK  *  SOFT  *  NURSERY", grid_sub="Watercolor * Storybook * Nursery",
                        ribbons=[((120, 168, 140), (66, 112, 90)), ((228, 148, 112), (168, 92, 62))], vbg=(52, 74, 70), bg=(250, 247, 238),
                        accent=(96, 150, 120), ink=(52, 66, 60), theme="sunny",
                        mock=[("tee_white", "tiger"), ("tote", "giraffe"), ("tee_oat", "elephant")]),
    # cute baby animal faces (plush + storybook)
    "faces": dict(kicker="BABY ANIMALS", sub="KAWAII  *  NURSERY  *  SUBLIMATION", grid_sub="Plush * Watercolor * Nursery",
                  ribbons=[((236, 126, 160), (170, 70, 104)), ((92, 176, 168), (48, 120, 112))], vbg=(88, 52, 74), bg=(255, 244, 248),
                  accent=(226, 112, 150), ink=(70, 44, 58), theme="sunny",
                  mock=[("tee_white", "panda"), ("tote", "fox"), ("tee_oat", "bunny")]),
}


def label(sk: str) -> str:
    return sk.replace("_", " ")


def make_meta(pack: P.Pack, png_dir: Path, drop: Tuple[str, ...]) -> List[Dict]:
    meta = []
    jobs = P.jobs(pack, styles_per_subject=2)
    for name, prompt, seed, sk, stk in jobs:
        if pack.style_only and stk != pack.style_only:
            continue
        if (png_dir / f"{name}.png").exists() and not any(d and d in name for d in drop):
            meta.append({"index": len(meta) + 1, "name": name, "text": label(sk), "subject": sk, "style": stk,
                         "file": f"{name}.png"})
    return meta


def make_thumbs(meta: List[Dict], png_dir: Path, thumbs: Path) -> None:
    if thumbs.exists():
        shutil.rmtree(thumbs)
    thumbs.mkdir(parents=True, exist_ok=True)
    for m in meta:
        im = Image.open(png_dir / m["file"]).convert("RGBA")
        im.thumbnail((520, 520), Image.LANCZOS)
        bg = Image.new("RGBA", (im.width + 24, im.height + 24), (255, 255, 255, 255))
        bg.alpha_composite(im, (12, 12))
        rgb = bg.convert("RGB")
        rgb.save(thumbs / f"{m['name']}.png")
        rgb.save(thumbs / f"{m['name']}_c.png")


def _find(meta: List[Dict], sk: str) -> Optional[Dict]:
    for m in meta:
        if m["subject"] == sk:
            return m
    return None


def mockup(kind: str, design: Path, out: Path, seed: int = 11) -> Optional[Path]:
    prompt, _ = M.MOCKUP_PROMPTS[kind]
    photo = M.comfy_photo(kind, prompt, seed=seed)
    if photo is None:
        print(f"  ! mockup {kind}: no photo")
        return None
    ph = Image.open(photo).convert("RGB").resize((M.SIZE, M.SIZE), Image.LANCZOS)
    des = Image.open(design).convert("RGBA")
    bb = des.getbbox()
    if bb:
        des = des.crop(bb)
    f = BOXES[kind]
    box = (int(f[0] * M.SIZE), int(f[1] * M.SIZE), int(f[2] * M.SIZE), int(f[3] * M.SIZE))
    return M.save_jpg(M.place_on_fabric(ph, des, box), out)


def checker(w: int, h: int, a=(255, 255, 255), b=(214, 214, 220), s: int = 44) -> Image.Image:
    im = Image.new("RGB", (w, h), a)
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=b)
    return im


def transparency_card(meta: List[Dict], png_dir: Path, out: Path, accent, ink, bg, title: str, picks: List[str]) -> Path:
    S = M.SIZE
    base = Image.new("RGBA", (S, S), bg + (255,))
    d = ImageDraw.Draw(base)
    ft = M.fit(d, title.upper(), M.anton, S - 240, 160, 70)
    d.text((S // 2, 70), title.upper(), font=ft, fill=ink, anchor="ma")
    fs = M.fit(d, "cut out and ready - works on any color", M.pacifico, S - 400, 76, 36)
    d.text((S // 2, 70 + ft.size + 14), "cut out and ready - works on any color", font=fs, fill=accent, anchor="ma")
    top = 70 + ft.size + fs.size + 90
    ph = (S - 3 * 60) // 2
    panels = [("light", checker(S - 120, (S - top - 60 - 60) // 2, (255, 255, 255), (222, 222, 228))),
              ("dark", Image.new("RGB", (S - 120, (S - top - 60 - 60) // 2), (36, 36, 44)))]
    y = top
    items = []
    for sk in picks:
        m = _find(meta, sk) or meta[len(items) % len(meta)]
        items.append(m)
    for nm, panel in panels:
        pr = panel.convert("RGBA")
        n = len(items)
        cw = (pr.width - 60) // n
        for i, m in enumerate(items):
            im = Image.open(png_dir / m["file"]).convert("RGBA")
            s = min((cw - 40) / im.width, (pr.height - 60) / im.height)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
            pr.alpha_composite(im, (30 + i * cw + (cw - im.width) // 2, (pr.height - im.height) // 2))
        mask = M.rounded(pr.size, 40, (255, 255, 255, 255)).split()[3]
        base.paste(pr, (60, y), mask)
        y += pr.height + 60
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def grid_cover(meta: List[Dict], png_dir: Path, out: Path, n: int, kicker: str, sub: str, accent, ink, bg) -> Path:
    S = M.SIZE
    base = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    d = ImageDraw.Draw(base)
    cols, rows = 5, 4
    top, pad = 600, 50
    gw, gh = (S - 2 * pad) // cols, (S - top - 150) // rows
    pool = [m for m in meta if m["subject"] not in ("easter",)]
    step = max(1, len(pool) // (cols * rows))
    pick = (pool[::step] + pool)[:cols * rows] if len(pool) >= cols * rows else pool
    pick = pool[::step][:cols * rows] if len(pool[::step]) >= cols * rows else pick
    for i, m in enumerate(pick):
        im = Image.open(png_dir / m["file"]).convert("RGBA")
        s = min((gw - 30) / im.width, (gh - 30) / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        r, c = divmod(i, cols)
        base.alpha_composite(im, (pad + c * gw + (gw - im.width) // 2, top + r * gh + (gh - im.height) // 2))
    d.rectangle((0, 0, S, 540), fill=ink)
    fk = M.fit(d, kicker + " CLIPART", M.anton, S - 300, 200, 90)
    d.text((S // 2, 60), kicker + " CLIPART", font=fk, fill=(255, 255, 255), anchor="ma")
    fn = M.fit(d, f"{n} PNG DESIGNS", M.anton, S - 400, 170, 80)
    d.text((S // 2, 60 + fk.size + 20), f"{n} PNG DESIGNS", font=fn, fill=accent if sum(accent) > 200 else (255, 214, 0), anchor="ma")
    strip = "300 DPI  *  TRANSPARENT  *  SUBLIMATION  *  COMMERCIAL USE"
    fs = M.fit(d, strip, M.poppins_x, S - 260, 62, 30)
    sw = M.text_w(d, strip, fs)
    base.alpha_composite(M.rounded((sw + 100, 110), 55, ink + (255,)), (S // 2 - (sw + 100) // 2, S - 135))
    d.text((S // 2, S - 80), strip, font=fs, fill=(255, 255, 255), anchor="mm")
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def split_zips(png_dir: Path, meta: List[Dict], extra: List[Path], out: Path, stem: str, cap: int = int(19.0 * 1024 * 1024)) -> Dict[str, float]:
    """First-fit-decreasing bin packing of PNGs (already compressed) into <= 5 zips of <= cap bytes; `extra` goes in part 1."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.zip"):
        old.unlink()
    files = sorted([(png_dir / m["file"]) for m in meta], key=lambda p: -p.stat().st_size)
    extra_sz = sum(e.stat().st_size for e in extra)
    bins: List[Tuple[int, List[Path]]] = [(extra_sz, [])]
    for f in files:
        sz = f.stat().st_size + 400
        for i, (used, lst_) in enumerate(bins):
            if used + sz <= cap:
                bins[i] = (used + sz, lst_ + [f])
                break
        else:
            bins.append((sz, [f]))
    if len(bins) > ETSY_MAX_FILES:
        raise RuntimeError(f"needs {len(bins)} zips (> {ETSY_MAX_FILES}); total {sum(b[0] for b in bins) / 1e6:.0f} MB - drop designs or downscale")
    res = {}
    for i, (used, fl) in enumerate(bins, 1):
        z = out / f"{stem}_PNG_Part{i}of{len(bins)}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            if i == 1:
                for e in extra:
                    zf.write(e, arcname=e.name)
            for f in sorted(fl, key=lambda p: p.name):
                zf.write(f, arcname=f"PNG/{f.name}")
        if z.stat().st_size > ETSY_MAX_FILE_BYTES:
            raise RuntimeError(f"{z.name} is {z.stat().st_size / 1e6:.1f} MB")
        res[z.name] = round(z.stat().st_size / 1e6, 2)
    return res


LICENSE_LINES = [
    "# Commercial small-business license (included)",
    "You MAY use these illustrations on physical products you make and sell - T-shirts, sweatshirts, mugs, tumblers, tote bags, ornaments, "
    "stickers, cards - up to 500 units per design. No credit needed.",
    "You MAY NOT resell, share, give away, upload or redistribute the digital files (original or edited), include them in another bundle "
    "or digital product, upload them to print-on-demand sites that let others reuse them, or use them as a logo or trademark.",
    "Need more than 500 units per design? Message the shop for an extended license.",
    "# AI disclosure",
    "These illustrations were created with AI image-generation tools, then selected, cleaned up, cut out on transparent backgrounds and "
    "prepared by the shop. They contain no licensed characters, brands or logos.",
    "Digital download - no physical item is shipped. If anything is wrong with a file, contact the shop and it will be fixed.",
]


def guide_pages(name: str, n: int, size_line: str, parts: int) -> List[Tuple[str, List[str]]]:
    return [(f"{name} - Quick Start", [
        f"Thank you for your purchase! This bundle has {n} illustrated PNG designs with transparent backgrounds.",
        "# What is inside",
        f"- {parts} zip files. Each holds PNG files named by design. Unzip them all into one folder.",
        f"- {size_line}",
        "- Every PNG is saved at 300 dpi, so the pixel size converts directly to print size in inches.",
        "# Using the files",
        "- Sublimation: open the PNG in your print software, mirror it, print on sublimation paper and press on polyester or coated blanks. "
        "White areas will not print on dark polyester - sublimation works best on white or light blanks.",
        "- DTF / print-then-cut / stickers: use the PNG as is; the background is already transparent.",
        "- Design Space / Silhouette: Upload Image and choose the PNG, then use Print Then Cut.",
        "- Screen colors vary a little from printed colors - do a test print first.",
    ]), ("Commercial license and AI disclosure", LICENSE_LINES)]


LONG_SIDE = 1900          # delivered PNG long side in px (about 6.3 in at 300 dpi); the sources are generated at 1328 px
PALETTE_MAX_ERR = 3.3     # mean per-channel error (of 255) below which a 256-colour palette PNG is used (flat art)


def make_deliver(png_dir: Path, meta: List[Dict], out: Path, long_side: int) -> List[Tuple[int, int]]:
    """Resize each cut PNG to `long_side` and save it adaptively (palette when visually safe). Returns the sizes."""
    from etsy_factory.clipart import cutkey as K
    import numpy as np  # noqa: F401
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    sizes = []
    for m in meta:
        im = Image.open(png_dir / m["file"]).convert("RGBA")
        s = long_side / max(im.size)
        if s < 1:
            im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        mode = K.save_adaptive(im, out / m["file"], max_err=PALETTE_MAX_ERR)
        m["delivery_mode"] = mode
        sizes.append(im.size)
    return sizes


def fit_delivery(png_dir: Path, meta: List[Dict], deliver: Path, long_side: int, root: Path, up: Path, pack, look) -> Tuple[List[Dict], str]:
    """Trim designs from the tail until the delivery set packs into <= 5 Etsy files. Returns (meta, size_line)."""
    pdf = root / "_work" / "Guide_and_Commercial_License.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    stem = pack.name.replace(" ", "_")
    while True:
        sizes = make_deliver(png_dir, meta, deliver, long_side)
        longest = max(max(s) for s in sizes)
        size_line = f"Size: longest side up to {longest} px (about {longest / 300:.1f} in at 300 dpi)."
        kit.pdf_guide(pdf, guide_pages(pack.name, len(meta), size_line, 5), look["theme"])
        try:
            split_zips(deliver, meta, [pdf], up, stem)
            pal = sum(1 for m in meta if m.get("delivery_mode") == "palette")
            print(f"  delivery fits: {len(meta)} designs ({pal} palette PNG), longest side {longest}px")
            return meta, size_line
        except RuntimeError as e:
            if len(meta) <= 30:
                raise
            dropped = meta.pop()
            for i, m in enumerate(meta, 1):
                m["index"] = i
            print(f"  trim ({e}); dropped {dropped['name']}")


def build(key: str, mockups: bool = True, drop: Tuple[str, ...] = ()) -> Dict:
    pack, look = P.PACKS[key], LOOK[key]
    png_dir = ROOT / (pack.png_slug or pack.slug) / "png"
    root = OUT / pack.slug
    thumbs, imgs, up = root / "_work" / "thumbs", root / "images", root / "etsy_upload"
    meta = make_meta(pack, png_dir, drop)
    for p in (root, imgs, up):
        p.mkdir(parents=True, exist_ok=True)
    deliver = ROOT / pack.slug / "png_deliver"
    meta, size_line = fit_delivery(png_dir, meta, deliver, look.get("long_side", LONG_SIDE), root, up, pack, look)
    n = len(meta)
    (root / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    make_thumbs(meta, png_dir, thumbs)
    for old in imgs.glob("*.jpg"):
        old.unlink()
    accent, ink, bg = look["accent"], look["ink"], look["bg"]
    r0, r1 = look["ribbons"][0][0], look["ribbons"][1][0]
    chips = [r0, r1, (232, 160, 40), (120, 84, 150), (46, 150, 96)]

    cover2.vibrant(meta, thumbs, imgs / "01_cover.jpg", str(n), look["kicker"], ["CLIPART PNG BUNDLE", "SUBLIMATION DESIGNS"], look["sub"],
                   look["ribbons"], (26, 26, 34), look["vbg"],
                   [("PNG", "Transparent\nbackground", chips[0]), ("300", "DPI\nprint ready", chips[1]), ("SUB", "Sublimation\nready", chips[2]),
                    ("USE", "Commercial\nincluded", chips[3]), ("ZIP", "Instant\ndownload", chips[4])])
    grid_cover(meta, png_dir, imgs / "02_cover_grid.jpg", n, look["kicker"], look["grid_sub"], accent, ink, bg)
    half = min(20, n)
    M.sheet(meta, thumbs, imgs / "03_preview_1.jpg", f"{pack.short.title()} Designs", f"{n} illustrations - a peek inside", accent, ink, bg, 0, half)
    M.sheet(meta, thumbs, imgs / "04_preview_2.jpg", "More Designs Inside", "every one on a transparent background", r1, ink, bg, half, 20)
    nxt = 5
    if mockups:
        for kind, sk in look["mock"]:
            m = _find(meta, sk) or meta[nxt % n]
            if mockup(kind, png_dir / m["file"], imgs / f"{nxt:02d}_mockup_{kind}.jpg"):
                nxt += 1
    transparency_card(meta, png_dir, imgs / f"{nxt:02d}_transparent.jpg", accent, ink, bg, "Transparent PNG", [look["mock"][0][1], look["mock"][1][1], look["mock"][2][1]])
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_whats_included.jpg", "What's in your download", "instant digital download",
                [("PNG x " + str(n), "Transparent background, 300 dpi, " + size_line.replace("Size: l", "l").rstrip(".")),
                 ("Sublimation", "Mirror, print on sublimation paper, press on polyester or coated blanks"),
                 ("Also for", "DTF transfers, stickers, print-then-cut, scrapbooking, cards and planners"),
                 ("PDF guide", "Quick-start and the commercial license, inside zip part 1"),
                 ("AI-assisted", "Illustrations made with AI image tools and prepared by the shop")],
                accent, ink, bg, footer=f"{n} designs  -  PNG  -  300 dpi")
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_license.jpg", "Commercial use included", "small business friendly",
                [("YES", "Sell shirts, mugs, tumblers, totes, stickers and cards you make"),
                 ("500 units", "per design - no credit required"),
                 ("NO", "Reselling or sharing the digital files, or adding them to other bundles"),
                 ("Original", "No characters, brands or logos - AI-assisted art disclosed"),
                 ("Help", "Message the shop if any file needs fixing")], r1, ink, bg)
    print("images:", [p.name for p in sorted(imgs.glob("[0-9][0-9]_*.jpg"))])

    stem = pack.name.replace(" ", "_")
    pdf = root / "_work" / "Guide_and_Commercial_License.pdf"
    kit.pdf_guide(pdf, guide_pages(pack.name, n, size_line, 5), look["theme"])
    parts = len(split_zips(deliver, meta, [pdf], up, stem))
    kit.pdf_guide(pdf, guide_pages(pack.name, n, size_line, parts), look["theme"])
    zips = split_zips(deliver, meta, [pdf], up, stem)
    print("zips:", zips, "designs:", n)

    title = pack.title.format(n=n)
    if len(title) > 140:
        title = title[:140].rsplit(" ", 1)[0].rstrip(",")
    desc = (f"{pack.intro}\n\nWHAT YOU GET\n- {n} illustrated {pack.short} PNG designs, each on a transparent background\n"
            f"- 300 dpi, longest side up to {max(max(Image.open(deliver / m['file']).size) for m in meta)} px - ready for sublimation, DTF, stickers and print-then-cut\n"
            "- PDF quick-start guide and commercial license\n\n"
            f"PERFECT FOR\n{pack.uses}\n\nHOW IT WORKS\nThe files arrive as zip parts - download and unzip them all into one folder. "
            "For sublimation, mirror the design in your print software and press on polyester or coated blanks (white or light colors work best).\n\n"
            "COMMERCIAL USE\nUse the designs on physical products you sell, up to 500 units per design, no credit needed. "
            "You may not resell or share the digital files.\n\n"
            "DESIGN & CREATION TRANSPARENCY\n"
            "- Original designs created by CraftyMyia using AI-assisted illustration tools (ComfyUI) combined with custom selection, background removal, edge refinement, and 300 DPI print preparation.\n"
            "- Listing photos show digital lifestyle mockups to illustrate how the artwork looks on physical blanks.\n\n"
            "DIGITAL DOWNLOAD & COMPATIBILITY NOTICE\n"
            "- DIGITAL DOWNLOAD ONLY — no physical product will be shipped. Files are available instantly after purchase. Colors on screen may vary slightly from print.\n"
            "- Compatible with Cricut Design Space, Silhouette Studio, and standard sublimation/DTF software. All machine and software names are trademarks of their respective owners; CraftyMyia is an independent studio and is not affiliated with or endorsed by them.")
    data = lst.write_listing(root, title=title, tags=pack.tags, description=desc, price_usd=pack.price,
                             sale_hint=f"list ${pack.list_price:.2f}, run a sale to show the discount",
                             category="Art & Collectibles > Drawing & Illustration > Digital (or the closest digital clipart category)",
                             materials="digital files",
                             whats_in_the_files=[f"{n} PNG designs (transparent, 300 dpi)", f"{len(zips)} zip parts, guide + license in part 1"],
                             notes=["Etsy creation-process question: choose 'AI generated' (these are AI-generated illustrations) and describe the tool in the "
                                    "'how it was made' field."])
    print(json.dumps({"title_chars": data["title_chars"], "problems": data["validation_problems"]}, indent=2))
    return data


if __name__ == "__main__":
    k = sys.argv[1]
    dr = tuple(sys.argv[sys.argv.index("--drop") + 1].split(",")) if "--drop" in sys.argv else ()
    build(k, mockups="--no-mockups" not in sys.argv, drop=dr)
