"""Media kit, zips, guide and listing copy for the seamless tumbler-wrap pattern pack made by pack.py.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.patterns.build_listing [--no-mockups] [--samples 96]
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory import kit
from etsy_factory import listing as lst
from etsy_factory.common import ETSY_MAX_FILE_BYTES, ETSY_MAX_FILES
from etsy_factory.patterns import engine as E
from etsy_factory.patterns import mock_tumbler as MT
from etsy_factory.patterns import pack as PK
from etsy_factory.typo import cover2
from etsy_factory.typo import media as M

BASE = PK.ROOT / PK.SLUG
OUT = Path(r"F:\WORKHORSE\workspace\etsy_listings") / PK.SLUG

TITLE = ("Seamless Tumbler Wrap Patterns PNG, {n} Retro Boho Seamless Patterns, 20oz Skinny Tumbler Sublimation Template, "
         "Digital Paper, Commercial Use")
TAGS = ["seamless pattern", "tumbler wrap png", "sublimation design", "digital paper", "20oz skinny tumbler", "boho seamless",
        "retro pattern png", "tumbler sublimation", "seamless png", "tumbler template", "leopard print png", "daisy pattern",
        "commercial use"]
PRICE, LIST_PRICE = 4.99, 12.99

INK = (40, 30, 34)
ACCENT = (204, 108, 72)
ACCENT2 = (84, 124, 110)
BG = (255, 246, 236)
VBG = (88, 52, 42)
RIBBONS = [((204, 108, 72), (128, 60, 36)), ((84, 124, 110), (40, 78, 66))]


def make_thumbs(meta: List[Dict], thumbs: Path) -> None:
    if thumbs.exists():
        shutil.rmtree(thumbs)
    thumbs.mkdir(parents=True, exist_ok=True)
    for m in meta:
        t = Image.open(BASE / "tiles" / f"{m['name']}.png").convert("RGB")
        # 2 x 2 repeat so the thumbnail reads as a pattern, not a single motif
        r = E.tile_to(t, 560, 560, 280)
        bg = Image.new("RGB", (r.width + 24, r.height + 24), (255, 255, 255))
        bg.paste(r, (12, 12))
        bg.save(thumbs / f"{m['name']}.png")
        bg.save(thumbs / f"{m['name']}_c.png")


def wrap_card(meta: List[Dict], out: Path) -> Path:
    S = M.SIZE
    base = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(base)
    ft = M.fit(d, "TUMBLER WRAP TEMPLATE", M.anton, S - 240, 170, 70)
    d.text((S // 2, 70), "TUMBLER WRAP TEMPLATE", font=ft, fill=INK, anchor="ma")
    fs = M.fit(d, "20 oz skinny straight - 9.3 x 8.2 in - 2790 x 2460 px", M.pacifico, S - 300, 76, 36)
    d.text((S // 2, 70 + ft.size + 16), "20 oz skinny straight - 9.3 x 8.2 in - 2790 x 2460 px", font=fs, fill=ACCENT, anchor="ma")
    top = 70 + ft.size + fs.size + 110
    pick = [m for m in meta if m["kind"] in ("daisies", "arches")][:2]
    panel_w = S - 240
    ph = (S - top - 120 - 60) // 2
    y = top
    for m in pick:
        w = Image.open(BASE / "wraps" / f"{m['name']}.png").convert("RGB")
        s = min(panel_w / w.width, (ph - 70) / w.height)
        w = w.resize((int(w.width * s), int(w.height * s)), Image.LANCZOS)
        x = (S - w.width) // 2
        M.shadowed(base.convert("RGBA"), M.rounded((w.width + 16, w.height + 16), 14, (255, 255, 255, 255)), (x - 8, y - 8), blur=10, off=(0, 8), alpha=80)
        base.paste(w, (x, y))
        d.rectangle((x - 3, y - 3, x + w.width + 2, y + w.height + 2), outline=INK, width=4)
        d.text((S // 2, y + w.height + 14), "9.3 in  x  8.2 in", font=M.poppins(44), fill=INK, anchor="ma")
        y += ph + 60
    base.save(out, quality=94, subsampling=0)
    return out


def seamless_card(meta: List[Dict], out: Path) -> Path:
    S = M.SIZE
    base = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(base)
    ft = M.fit(d, "TRULY SEAMLESS", M.anton, S - 240, 190, 70)
    d.text((S // 2, 70), "TRULY SEAMLESS", font=ft, fill=INK, anchor="ma")
    sub = "every tile repeats with no visible seam - resize freely"
    fs = M.fit(d, sub, M.pacifico, S - 300, 76, 36)
    d.text((S // 2, 70 + ft.size + 16), sub, font=fs, fill=ACCENT, anchor="ma")
    m = next(x for x in meta if x["kind"] == "rings")
    tile = Image.open(BASE / "tiles" / f"{m['name']}.png").convert("RGB")
    top = 70 + ft.size + fs.size + 120
    side = S - top - 150
    n = 3
    cell = side // n
    side = cell * n
    rep = E.tile_to(tile, side, side, cell)
    x0 = (S - side) // 2
    M.shadowed(base.convert("RGBA"), M.rounded((side + 20, side + 20), 18, (255, 255, 255, 255)), (x0 - 10, top - 10), blur=14, off=(0, 10), alpha=90)
    base.paste(rep, (x0, top))
    # outline ONE tile (centre) so the repeat is obvious
    cx, cy = x0 + cell, top + cell
    d.rectangle((cx, cy, cx + cell, cy + cell), outline=(255, 255, 255), width=14)
    d.rectangle((cx, cy, cx + cell, cy + cell), outline=INK, width=5)
    d.text((S // 2, top + side + 30), "outlined square = one tile  -  12 x 12 in papers included", font=M.poppins(46), fill=INK, anchor="ma")
    base.save(out, quality=94, subsampling=0)
    return out


def pick_wrap(meta: List[Dict], kind: str, nth: int = 0) -> Path:
    c = [m for m in meta if m["kind"] == kind]
    return BASE / "wraps" / f"{c[min(nth, len(c) - 1)]['name']}.png"


def render_mockups(meta: List[Dict], imgs: Path, start: int, samples: int) -> int:
    work = OUT / "_work" / "tumb"
    W = lambda k, n=0: str(pick_wrap(meta, k, n))
    cream, charcoal, blush = [0.96, 0.95, 0.93], [0.2, 0.2, 0.22], [0.95, 0.8, 0.82]
    scenes = [
        dict(out=str(work / "m1.png"), res=[2400, 2400], samples=samples, spread=18, tumblers=[
            dict(x=-10, wrap=W("daisies", 2), lid=cream, straw=[0.9, 0.5, 0.55], rot=90),
            dict(x=0, wrap=W("arches", 0), lid=charcoal, straw=[0.2, 0.6, 0.55], rot=90),
            dict(x=10, wrap=W("hearts", 1), lid=blush, straw=[0.85, 0.2, 0.35], rot=90)], camera=dict(dist=112, el=8)),
        dict(out=str(work / "m2.png"), res=[2400, 2400], samples=samples, tumblers=[
            dict(x=0, wrap=W("leopard", 0), lid=cream, straw=[0.85, 0.3, 0.45], rot=90)], camera=dict(dist=86, el=7)),
        dict(out=str(work / "m3.png"), res=[2400, 2400], samples=samples, spread=18, tumblers=[
            dict(x=-10, wrap=W("gingham", 0), lid=blush, straw=[0.9, 0.5, 0.55], rot=90),
            dict(x=0, wrap=W("stars", 3), lid=charcoal, straw=[0.3, 0.45, 0.25], rot=90),
            dict(x=10, wrap=W("waves", 2), lid=cream, straw=[0.85, 0.2, 0.35], rot=90)], camera=dict(dist=112, el=8)),
    ]
    work.mkdir(parents=True, exist_ok=True)
    res = MT.render(scenes, work)
    print("  blender:", {k: res[k] for k in ("seconds", "returncode", "rendered", "expected")})
    n = start
    for s, nm in zip(scenes, ("trio", "single", "trio2")):
        p = Path(s["out"])
        if p.exists() and p.stat().st_size > 20_000:
            Image.open(p).convert("RGB").save(imgs / f"{n:02d}_mockup_{nm}.jpg", quality=94, subsampling=0)
            n += 1
    return n


def split_zips(meta: List[Dict], extra: List[Path], out: Path, stem: str, cap: int = int(19.0 * 1024 * 1024)) -> Dict[str, float]:
    """Keep each pattern's wrap + paper + tile together in the same zip when possible: bin-pack whole patterns (first-fit-decreasing)."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.zip"):
        old.unlink()
    items = []
    for m in meta:
        files = [(BASE / sub / f"{m['name']}.png", f"{sub}/{m['name']}.png") for sub in ("wraps", "papers", "tiles")]
        items.append((sum(f.stat().st_size + 400 for f, _ in files), files))
    items.sort(key=lambda t: -t[0])
    bins: List[Tuple[int, List]] = [(sum(e.stat().st_size for e in extra), [])]
    for sz, files in items:
        for i, (used, lst_) in enumerate(bins):
            if used + sz <= cap:
                bins[i] = (used + sz, lst_ + files)
                break
        else:
            bins.append((sz, list(files)))
    if len(bins) > ETSY_MAX_FILES:
        raise RuntimeError(f"needs {len(bins)} zips (> {ETSY_MAX_FILES}); total {sum(b[0] for b in bins) / 1e6:.0f} MB")
    res = {}
    for i, (used, fl) in enumerate(bins, 1):
        z = out / f"{stem}_Part{i}of{len(bins)}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            if i == 1:
                for e in extra:
                    zf.write(e, arcname=e.name)
            for f, arc in sorted(fl, key=lambda t: t[1]):
                zf.write(f, arcname=arc)
        if z.stat().st_size > ETSY_MAX_FILE_BYTES:
            raise RuntimeError(f"{z.name} is {z.stat().st_size / 1e6:.1f} MB")
        res[z.name] = round(z.stat().st_size / 1e6, 2)
    return res


LICENSE_LINES = [
    "# Commercial small-business license (included)",
    "You MAY use these patterns on physical products you make and sell - tumblers, mugs, shirts, tote bags, phone cases, wrapping, cards - "
    "up to 500 units per design. No credit needed.",
    "You MAY NOT resell, share, give away, upload or redistribute the digital files (original or edited) as patterns, digital paper or templates, "
    "include them in another bundle or digital product, or use them as a logo or trademark.",
    "Need more than 500 units per design? Message the shop for an extended license.",
    "# Originality",
    "Every pattern is built from original geometric shapes by the shop - no AI-generated art, characters, brands or logos.",
    "Digital download - no physical item is shipped. If anything is wrong with a file, contact the shop and it will be fixed.",
]


def guide_pages(n: int, parts: int) -> List[Tuple[str, List[str]]]:
    return [("Seamless Tumbler Wrap Patterns - Quick Start", [
        f"Thank you for your purchase! This bundle has {n} seamless patterns, each delivered three ways.",
        "# What is inside",
        f"- {parts} zip files. Unzip them all into one folder - each pattern keeps the same number in every sub-folder.",
        "- wraps/  : 20 oz skinny straight tumbler wrap, 9.3 x 8.2 in (2790 x 2460 px, 300 dpi). Print as is.",
        "- papers/ : 12 x 12 in seamless digital paper (3600 x 3600 px, 300 dpi) - for mugs, shirts, scrapbooking, backgrounds.",
        "- tiles/  : the single repeating tile (1200 x 1200 px). Tile it at any scale in Photoshop, Canva, Procreate or Affinity.",
        "# Printing a tumbler wrap",
        "- Open the wrap PNG in your print software, mirror it, print on sublimation paper at 100% scale (no 'fit to page').",
        "- Tape the print to a white, sublimation-coated 20 oz skinny straight tumbler and press or oven-wrap per your blank's instructions.",
        "- Other tumbler sizes: open a tile in your design tool, repeat it to fill your template, then export.",
        "- The patterns start at the top-left corner, so you can crop or trim the wrap freely - the repeat is seamless on all four sides.",
        "- Screen colors vary a little from printed colors - do a test print first.",
    ]), ("Commercial license", LICENSE_LINES)]


def build(mockups: bool = True, samples: int = 96) -> Dict:
    meta = json.loads((BASE / "catalog.json").read_text(encoding="utf-8"))
    n = len(meta)
    root = OUT
    thumbs, imgs, up = root / "_work" / "thumbs", root / "images", root / "etsy_upload"
    for p in (root, imgs, up):
        p.mkdir(parents=True, exist_ok=True)
    (root / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    make_thumbs(meta, thumbs)
    for old in imgs.glob("*.jpg"):
        old.unlink()
    chips = [ACCENT, ACCENT2, (232, 160, 40), (120, 84, 150), (46, 150, 96)]

    cover2.vibrant(meta, thumbs, imgs / "01_cover.jpg", str(n), "SEAMLESS PATTERNS", ["TUMBLER WRAP PNG", "SUBLIMATION DESIGNS"],
                   "20 OZ SKINNY  *  DIGITAL PAPER  *  BOHO", RIBBONS, (26, 26, 34), VBG,
                   [("PNG", "Seamless\nrepeat", chips[0]), ("20OZ", "Skinny\ntumbler wrap", chips[1]), ("300", "DPI\nprint ready", chips[2]),
                    ("USE", "Commercial\nincluded", chips[3]), ("ZIP", "Instant\ndownload", chips[4])])
    nxt = 2
    if mockups:
        nxt = render_mockups(meta, imgs, nxt, samples)
    for fn, title, sub, a, items in (("preview_1", "Retro Boho Patterns", f"{n} seamless patterns - a peek inside", ACCENT, meta[0::2]),
                                     ("preview_2", "Mix and Match Colors", "13 pattern styles in 4 palettes each", ACCENT2, meta[1::2])):
        M.sheet(items, thumbs, imgs / f"{nxt:02d}_{fn}.jpg", title, sub, a, INK, BG, 0, 20)
        nxt += 1
    wrap_card(meta, imgs / f"{nxt:02d}_wrap_template.jpg")
    nxt += 1
    seamless_card(meta, imgs / f"{nxt:02d}_seamless.jpg")
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_whats_included.jpg", "What's in your download", "instant digital download",
                [(f"{n} wraps", "20 oz skinny straight tumbler wrap PNG, 9.3 x 8.2 in at 300 dpi - print as is"),
                 (f"{n} papers", "12 x 12 in seamless digital paper, 3600 px at 300 dpi"),
                 (f"{n} tiles", "Single repeating tile PNG - resize to any tumbler, mug or shirt"),
                 ("Sublimation", "Mirror, print on sublimation paper, press on polyester or coated blanks"),
                 ("PDF guide", "Quick-start and the commercial license, inside zip part 1")],
                ACCENT, INK, BG, footer=f"{n} patterns  -  3 files each  -  300 dpi")
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_license.jpg", "Commercial use included", "small business friendly",
                [("YES", "Sell tumblers, mugs, shirts, totes and cases you make"),
                 ("500 units", "per design - no credit required"),
                 ("NO", "Reselling or sharing the digital files, or adding them to other bundles"),
                 ("Original", "Built from original shapes - no characters, brands or logos"),
                 ("Help", "Message the shop if any file needs fixing")], ACCENT2, INK, BG)
    print("images:", [p.name for p in sorted(imgs.glob("[0-9][0-9]_*.jpg"))])

    stem = "Seamless_Tumbler_Wrap_Patterns"
    pdf = root / "_work" / "Guide_and_Commercial_License.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    kit.pdf_guide(pdf, guide_pages(n, 5), "sunny")
    parts = len(split_zips(meta, [pdf], up, stem))
    kit.pdf_guide(pdf, guide_pages(n, parts), "sunny")
    zips = split_zips(meta, [pdf], up, stem)
    print("zips:", zips)

    title = TITLE.format(n=n)
    if len(title) > 140:
        title = title[:140].rsplit(" ", 1)[0].rstrip(",")
    desc = (f"{n} seamless retro boho patterns, each ready to print as a 20 oz skinny straight tumbler wrap, a 12 x 12 in digital paper and a repeating tile - "
            "daisies, rainbows, leopard, hearts, stars, gingham, groovy waves and more in four colorways each.\n\n"
            f"WHAT YOU GET\n- {n} tumbler wrap PNGs, 9.3 x 8.2 in (2790 x 2460 px, 300 dpi)\n"
            f"- {n} seamless digital papers, 12 x 12 in (3600 x 3600 px, 300 dpi)\n- {n} single seamless tiles (1200 x 1200 px) to resize for any product\n"
            "- PDF quick-start guide and commercial license\n\n"
            "PERFECT FOR\nSublimation tumblers, mugs, shirts, tote bags, phone cases, wrapping paper, scrapbooking, planners, backgrounds and social media graphics.\n\n"
            "HOW IT WORKS\nThe files arrive as zip parts - download and unzip them all into one folder. For sublimation, mirror the wrap in your print software, "
            "print at 100% scale on sublimation paper and press on white polyester or coated blanks.\n\n"
            "COMMERCIAL USE\nUse the patterns on physical products you sell, up to 500 units per design, no credit needed. You may not resell or share the digital files.\n\n"
            "DIGITAL DOWNLOAD - nothing is shipped. Files are available instantly after purchase. Colors on screen may vary slightly from print. "
            "Tumbler mockup photos are 3D renders for illustration only; the tumbler is not included.")
    data = lst.write_listing(root, title=title, tags=TAGS, description=desc, price_usd=PRICE,
                             sale_hint=f"list ${LIST_PRICE:.2f}, run a sale to show the discount",
                             category="Craft Supplies & Tools > Patterns & How To > Digital (or Art & Collectibles > Prints > Digital Prints)",
                             materials="digital files",
                             whats_in_the_files=[f"{n} wrap PNGs (9.3 x 8.2 in) + {n} 12 x 12 in papers + {n} tiles", f"{len(zips)} zip parts, guide + license in part 1"],
                             notes=["Patterns are generated by the shop's own script from geometric shapes (no AI art); the mockup photos are 3D renders - "
                                    "say so in the 'how it was made' field if asked."])
    print(json.dumps({"title_chars": data["title_chars"], "problems": data["validation_problems"]}, indent=2))
    return data


if __name__ == "__main__":
    s = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 96
    build(mockups="--no-mockups" not in sys.argv, samples=s)
