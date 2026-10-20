"""Media kit + listing copy for the Cute Animal Faces layered cut-file pack made by faces/pack.py.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.faces.build_listing [--no-mockups]

Images: vibrant cover, grid cover, 2 preview sheets, 3 shirt/tote mockups (ComfyUI blank-product photos + the real layered PNGs),
a "how the layers stack" card (drawn from the real layer geometry), formats card and license card.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory import listing as lst
from etsy_factory.common import listing_dirs
from etsy_factory.faces import animals as AN
from etsy_factory.faces import pack as PK
from etsy_factory.typo import cover2
from etsy_factory.typo import export as X
from etsy_factory.typo import media as M

PINK, TEAL, SUN, PURPLE, GREEN = (240, 98, 146), (0, 160, 170), (255, 183, 3), (126, 87, 194), (46, 160, 90)
INK = (52, 36, 44)
BG = (255, 247, 238)
VBG = (255, 226, 214)
RIBBONS = [((240, 98, 146), (150, 36, 84)), ((0, 160, 170), (0, 92, 106))]

TITLE = ("Cute Animal Faces SVG Bundle, {n} Layered Animal Face Cut Files for Cricut, Silhouette, Kawaii Animal SVG PNG DXF, Commercial Use")
TAGS = ["animal face svg", "cute animal svg", "layered svg", "cricut svg bundle", "kawaii animal svg", "animal svg bundle",
        "baby animal svg", "nursery svg", "cut file", "silhouette cut file", "paper craft svg", "dxf laser file", "commercial use svg"]
PRICE, LIST_PRICE = 5.99, 14.99

# (kind, animal key) - colourful designs that read well on each fabric
MOCKS = [("tee_oat", "fox"), ("tote", "frog"), ("tee_black", "lion")]


def _catalog_idx(meta: List[Dict], key: str) -> int:
    return next(m["index"] for m in meta if m["key"] == key)


def _layered_png(files: Path, meta: List[Dict], key: str) -> Optional[Path]:
    hits = sorted((files / "Layered" / "PNG").glob(f"{_catalog_idx(meta, key):02d}_*_Layered_300dpi.png"))
    return hits[0] if hits else None


def render_mockups(meta: List[Dict], files: Path, imgs: Path, start: int) -> int:
    n = start
    for kind, key in MOCKS:
        src = _layered_png(files, meta, key)
        photo = M.comfy_photo(kind, M.MOCKUP_PROMPTS[kind][0], seed=11)
        if src is None or photo is None:
            print(f"  ! mockup {kind}/{key} skipped (design={src}, photo={photo})")
            continue
        ph = Image.open(photo).convert("RGB").resize((M.SIZE, M.SIZE), Image.LANCZOS)
        des = Image.open(src).convert("RGBA")
        bb = des.getbbox()
        if bb:
            des = des.crop(bb)
        f = M.MOCKUP_BOXES[kind]
        box = tuple(int(v * M.SIZE) for v in f)
        M.save_jpg(M.place_on_fabric(ph, des, box), imgs / f"{n:02d}_mockup_{kind}.jpg")
        n += 1
    return n


def layers_card(out: Path, meta_layers: List[Dict], key: str = "fox") -> Path:
    """Draws the real layers of one animal being stacked, step by step."""
    S = M.SIZE
    a = AN.A[key]
    layers = a.svg_layers()
    base = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(base)
    ft = M.fit(d, "LAYERED FOR CRAFTING", M.anton, S - 240, 170, 70)
    d.text((S // 2, 70), "LAYERED FOR CRAFTING", font=ft, fill=INK, anchor="ma")
    sub = "each colour is its own layer - cut, stack, glue"
    fs = M.fit(d, sub, M.pacifico, S - 300, 76, 36)
    d.text((S // 2, 70 + ft.size + 14), sub, font=fs, fill=PINK, anchor="ma")
    top = 70 + ft.size + fs.size + 110
    steps = sorted({min(s, len(layers)) for s in (1, 3, 5, len(layers))})
    cols, gap = 2, 50
    cw = (S - 160 - gap) // cols
    ch = 760
    frame = [(AN.U(*[g for _, g, _ in layers]), (255, 255, 255))]
    for i, k in enumerate(steps):
        r, c = divmod(i, cols)
        x, y0 = 80 + c * (cw + gap), top + r * (ch + gap)
        card = M.rounded((cw, ch), 44, (255, 255, 255, 255), outline=INK + (60,), width=3)
        M.shadowed(base, card, (x, y0), blur=14, off=(0, 8), alpha=70)
        # a white copy of the full extent goes underneath so every step has identical framing
        th = X.thumb_layers(frame + [(g, PK.rgb(hx)) for _, g, hx in layers[:k]], 600, pad=0.05).convert("RGBA")
        base.paste(th, (x + (cw - th.width) // 2, y0 + 20))
        label = "Layer 1 - the base" if k == 1 else (f"Layers 1-{k}" if k < len(layers) else f"All {k} layers stacked")
        d.text((x + cw // 2, y0 + ch - 60), label, font=M.poppins(52), fill=INK, anchor="mm")
    counts = [m["layers"] for m in meta_layers]
    rng = f"{min(counts)}-{max(counts)}"
    foot = [(f"{rng} layers", "per animal - SVG layers and DXF layers match every colour"),
            ("3 versions", "Layered color, one-piece stencil, solid silhouette")]
    y = top + 2 * ch + gap + 50
    for head, body in foot:
        pill = M.rounded((520, 110), 36, TEAL + (255,))
        base.alpha_composite(pill, (110, y))
        d.text((110 + 260, y + 55), head, font=M.fit(d, head, M.anton, 440, 70, 30), fill=(255, 255, 255), anchor="mm")
        d.text((700, y + 55), body, font=M.poppins(44), fill=INK, anchor="lm")
        y += 135
    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, quality=94, subsampling=0)
    return out


def build(mockups: bool = True) -> Dict:
    dirs = listing_dirs(PK.SLUG)
    root, files, thumbs = dirs["root"], dirs["files"], dirs["work"] / "thumbs"
    imgs = root / "images"
    meta: List[Dict] = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    n = len(meta)
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()
    chips = [PINK, TEAL, SUN, PURPLE, GREEN]

    cover2.vibrant(meta, thumbs, imgs / "01_cover.jpg", str(n), "CUTE ANIMAL FACES", ["LAYERED SVG", "CUT FILES"], "CRICUT  *  SILHOUETTE  *  DXF  *  PNG",
                   RIBBONS, (40, 28, 36), VBG,
                   [("SVG", "Layered\nby color", chips[0]), ("DXF", "Laser\nready", chips[1]), ("PNG", "300 DPI\ntransparent", chips[2]),
                    ("3 WAYS", "Layered\nStencil Solid", chips[3]), ("USE", "Commercial\nincluded", chips[4])])
    M.cover(meta, thumbs, imgs / "02_cover_grid.jpg", str(n), ["CUTE ANIMAL FACES", "LAYERED SVG BUNDLE"], "Kawaii * Nursery * Paper Craft",
            PINK, INK, [("SVG", chips[0]), ("DXF", chips[1]), ("PNG", chips[2]), ("3 VERSIONS", chips[3]), ("300DPI", INK)])
    M.sheet(meta, thumbs, imgs / "03_preview_1.jpg", "Kawaii Animal Faces", f"{n} original layered faces - a peek inside", PINK, INK, BG, 0, 20)
    nxt = 4
    if mockups:
        nxt = render_mockups(meta, files, imgs, nxt)
    layers_card(imgs / f"{nxt:02d}_layers.jpg", meta)
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_whats_included.jpg", "What's in your download", "instant digital download",
                [("Layered", "Full-colour face, one layer per colour - SVG, DXF (one layer per colour) and PNG"),
                 ("Stencil", "ONE connected piece with eyes, nose and mouth cut out - SVG, DXF, PNG"),
                 ("Solid", "Plain silhouette for bases, tags, stickers, toppers - SVG, DXF, PNG"),
                 ("Real size", "Every SVG saved at true size in inches - scale to fit"),
                 ("PDF guide", "Cricut and Silhouette quick-start plus the commercial license")],
                PINK, INK, BG, footer=f"{n} animals x 3 versions x 3 formats = {n * 9} files")
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_license.jpg", "Commercial use included", "small business friendly",
                [("YES", "Sell shirts, mugs, cards, stickers, signs, party decor you make"),
                 ("500 units", "per design - no credit required"),
                 ("NO", "Reselling or sharing the digital files, or adding them to other bundles"),
                 ("Original", "Original geometric animals - no characters, brands or logos"),
                 ("Help", "Message the shop if any file needs fixing")], TEAL, INK, BG)
    print("images:", [p.name for p in sorted(imgs.glob("[0-9][0-9]_*.jpg"))])

    title = TITLE.format(n=n)
    if len(title) > 140:
        title = title[:140].rsplit(" ", 1)[0].rstrip(",")
    names = ", ".join(m["text"].lower() for m in meta)
    desc = (f"{n} cute animal faces as layered cut files - each in 3 versions ({n * 3} designs) and 3 formats (SVG, DXF, PNG).\n\n"
            f"ANIMALS\n{names}.\n\n"
            "WHAT YOU GET\n"
            f"- {n} layered colour faces: one SVG/DXF layer per colour (body, ears, muzzle, eyes, blush) - cut each from its own paper, vinyl or felt and stack\n"
            f"- {n} one-piece stencils: the silhouette with the eyes, nose and mouth cut out\n"
            f"- {n} solid silhouettes for bases, tags, keychains, stickers and cake toppers\n"
            "- Every design as SVG (true size in inches), DXF and 300 dpi transparent PNG\n"
            "- PDF quick-start guide and commercial license\n\n"
            "PERFECT FOR\nNursery decor, kids birthday party, cake toppers, greeting cards, paper crafts, shadow boxes, shirts (HTV), "
            "tumblers, mugs, totes, felt crafts, laser-cut keychains and ornaments.\n\n"
            "WORKS WITH\nCricut Design Space, Silhouette Studio (SVG needs Designer Edition - use the DXF otherwise), Glowforge, xTool, "
            "Brother ScanNCut, Inkscape, Illustrator and CorelDRAW.\n\n"
            "COMMERCIAL USE\nUse the designs on physical products you sell, up to 500 units per design, no credit needed. "
            "You may not resell or share the digital files.\n\n"
            "DIGITAL DOWNLOAD - nothing is shipped. Files are available instantly after purchase. Colors on screen may vary slightly from cut materials. "
            "Shirt and tote photos are mockups for illustration only.")
    up = sorted((root / "etsy_upload").glob("*"))
    data = lst.write_listing(root, title=title, tags=TAGS, description=desc, price_usd=PRICE,
                             sale_hint=f"list ${LIST_PRICE:.2f}, run a sale to show the discount",
                             category="Craft Supplies & Tools > Patterns & How To > Digital",
                             materials="digital files",
                             whats_in_the_files=[f"{n} animals x 3 versions x (SVG, DXF, PNG)", "3 zips + PDF guide and license"],
                             notes=["All shapes are generated by the shop's own script from geometry (no AI art); the shirt/tote backgrounds are "
                                    "AI-made blank-product photos - mention it in 'how it was made' if asked."])
    print(json.dumps({"title_chars": data["title_chars"], "problems": data["validation_problems"], "upload_files": [p.name for p in up]}, indent=2))
    return data


if __name__ == "__main__":
    build(mockups="--no-mockups" not in sys.argv)
