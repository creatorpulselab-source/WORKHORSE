"""Quote-pack builder: corpus -> designs (SVG/DXF/EPS/PNG black/white/colour) -> zips -> PDF guide -> listing copy.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.typo.pack sarcasm [count]
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory import kit, listing as lst
from etsy_factory.common import ETSY_MAX_FILE_BYTES, RunReport, listing_dirs
from etsy_factory.typo import engine as E
from etsy_factory.typo import export as X

BLOCK = re.compile(r"bluey|disney|mickey|keep calm|big deal|she said|take the wheel|nike|coca|starbucks|barbie|taylor|pokemon|marvel|"
                   r"harry potter|stanley|yeti|minnie|tinker|pixar|epcot|dole whip|fast ?pass|lightning lane|magic kingdom|happiest place|small world|"
                   r"wish upon|park hopper|mouse ears|cinderella|army strong|be all you can be|semper|oorah|hooah|hoorah|devil dog|aim high|"
                   r"global force|usmc|usaf|uscg|united states|u\.s\. ?(army|navy|marine|air)|anchors aweigh", re.I)

LICENSE_PDF_LINES = [
    "# Commercial small-business license (included)",
    "You MAY use these designs on physical products you make and sell - T-shirts, mugs, tumblers, tote bags, signs, stickers, "
    "decals - up to 500 units per design. No credit needed.",
    "You MAY NOT resell, share, give away, upload or redistribute the digital files (original or edited), include them in "
    "another bundle or digital product, upload them to print-on-demand sites that let others reuse them, or use them as a logo "
    "or trademark.",
    "Need more than 500 units per design? Message the shop for an extended license.",
    "All designs are original typography. No licensed characters, brands or logos. Digital download - no physical item is "
    "shipped; files cannot be returned, but if anything is wrong with a file contact the shop and it will be fixed.",
]


@dataclass
class Niche:
    key: str
    slug: str
    name: str                    # "Funny Sarcastic Quotes"
    short: str                   # "Sarcastic"
    quotes: Sequence[str]
    style: E.Style
    palettes: List[Dict[str, Tuple[int, int, int]]]
    theme: str
    title: str
    tags: List[str]
    price: float
    list_price: float
    intro: str
    uses: str
    seo: List[str] = field(default_factory=list)


def _slug_text(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text.replace("*", "")).strip("_")
    return s[:46].strip("_")


def clean_quotes(quotes: Sequence[str]) -> List[str]:
    seen, out = set(), []
    for q in quotes:
        q = q.strip()
        if not q or BLOCK.search(q):
            continue
        k = re.sub(r"[^a-z]", "", q.lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out


def _build_one(args) -> Dict:
    idx, q, niche_key, seed, files_dir, thumbs_dir, recent = args
    niche = get_niche(niche_key)
    h = int(hashlib.md5(f"{seed}:{q}".encode()).hexdigest()[:8], 16)
    rng = random.Random(h)
    uid = f"{idx:03d}"
    d = E.make(q, uid, niche.style, rng, recent=recent)
    name = f"{idx:03d}_{_slug_text(q)}"
    root = Path(files_dir)
    svg_meta = X.write_svg(root / "Vector" / "SVG" / f"{name}.svg", [("Design", d.cut, "#000000")], width_in=round(d.width_in, 3), title=q.replace("*", ""))
    X.write_dxf(root / "Vector" / "DXF" / f"{name}.dxf", d.cut)
    X.write_eps(root / "Vector" / "EPS" / f"{name}.eps", d.cut)
    px = max(900, int(round(d.width_in * 300)))
    X.write_png(root / "PNG_Black" / f"{name}_black.png", [(d.cut, (0, 0, 0))], px)
    X.write_png(root / "PNG_White" / f"{name}_white.png", [(d.cut, (255, 255, 255))], px)
    pal = niche.palettes[idx % len(niche.palettes)]
    order = ["frame", "orn", "accent", "main"]
    layers = [(d.layers[k], pal.get(k, pal["main"])) for k in order if k in d.layers]
    X.write_png(root / "PNG_Color" / f"{name}_color.png", layers, px)
    Path(thumbs_dir).mkdir(parents=True, exist_ok=True)
    X.thumb(d.cut, 520, pad=0.04).save(Path(thumbs_dir) / f"{name}.png")
    colored = X.thumb_layers([(g, pal.get(k, pal["main"])) for k, g in [(k, d.layers[k]) for k in order if k in d.layers]], 520, bg=(255, 255, 255))
    colored.save(Path(thumbs_dir) / f"{name}_c.png")
    return {"index": idx, "name": name, "text": q.replace("*", ""), "template": d.template, "fonts": d.fonts,
            "width_in": svg_meta["width_in"], "height_in": svg_meta["height_in"], "nodes": d.nodes, "warnings": d.warnings}


def make_zips(files: Path, out: Path) -> Dict[str, float]:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.zip"):
        old.unlink()
    res = {}
    for zname, sub in [("SVG_DXF_EPS_Vector_Files.zip", "Vector"), ("PNG_Black_300dpi.zip", "PNG_Black"), ("PNG_White_300dpi.zip", "PNG_White"),
                       ("PNG_Color_Sublimation_300dpi.zip", "PNG_Color")]:
        z = out / zname
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for f in sorted((files / sub).rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=str(f.relative_to(files / sub)))
        mb = z.stat().st_size / 1e6
        if z.stat().st_size > ETSY_MAX_FILE_BYTES:
            raise RuntimeError(f"{zname} is {mb:.1f} MB (>20 MB)")
        res[zname] = round(mb, 2)
    return res


def guide_pages(niche: Niche, n: int, sizes: str) -> List[Tuple[str, List[str]]]:
    return [(f"{niche.name} Bundle - Quick Start", [
        f"Thank you for your purchase! This bundle has {n} original typography designs. Every design comes in 6 file types so it works with any cutting machine, heat press or sublimation printer.",
        "# What is inside the download",
        "- SVG_DXF_EPS_Vector_Files.zip - three folders: SVG (one-layer welded cut file for Cricut Design Space, Silhouette Studio, Glowforge, xTool, Brother ScanNCut), DXF and EPS (laser cutters, Inkscape, Illustrator, CorelDRAW).",
        "- PNG_Black_300dpi.zip - transparent solid-black PNG, 300 dpi, for light shirts, print-then-cut and sublimation.",
        "- PNG_White_300dpi.zip - transparent solid-white PNG for dark shirts.",
        "- PNG_Color_Sublimation_300dpi.zip - multi-colour transparent PNG for sublimation and print-then-cut.",
        "- This guide and the license.",
        "# Sizes",
        f"{sizes} Every SVG is saved at its real size in inches - scale it in your software to fit the item (shirts 8-11 in wide, mugs 3-4 in).",
    ]), ("Using the files", [
        "# Cricut Design Space",
        "Upload > Upload Image > Browse > pick an SVG > Save. Select the design on the canvas and use Size to set the width. Each design is one welded shape, so letters and flourishes stay together and cut cleanly.",
        "# Silhouette Studio (Designer Edition or higher for SVG)",
        "File > Open > choose the SVG. If you have Basic Edition use the DXF instead.",
        "# Heat transfer vinyl (HTV)",
        "Mirror the design before cutting. Weed the excess, press at the temperature on your vinyl's instruction sheet.",
        "# Sublimation",
        "Use the colour PNG. Print mirrored on sublimation paper and press onto a polyester (or poly-coated) blank.",
        "# Dark shirts",
        "Use the WHITE PNG, or cut the SVG in a light vinyl colour.",
    ]), ("Commercial license", LICENSE_PDF_LINES)]


def _title_ok(t: str) -> str:
    return t if len(t) <= 140 else t[:137].rsplit(" ", 1)[0]


def build(key: str, count: Optional[int] = None, seed: int = 2026, workers: int = 6) -> Dict:
    niche = get_niche(key)
    rep = RunReport(niche.slug)
    dirs = listing_dirs(niche.slug)
    files, thumbs = dirs["files"], dirs["work"] / "thumbs"
    for p in (files, thumbs):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    quotes = clean_quotes(niche.quotes)
    if count:
        quotes = quotes[:count]
    with rep.stage(f"generate {len(quotes)} designs x 6 formats"):
        jobs = [(i + 1, q, key, seed, str(files), str(thumbs), None) for i, q in enumerate(quotes)]
        with ProcessPoolExecutor(max_workers=workers) as ex:
            meta = list(ex.map(_build_one, jobs, chunksize=2))
    meta.sort(key=lambda m: m["index"])
    (dirs["root"] / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with rep.stage("zip deliverables"):
        zips = make_zips(files, dirs["root"] / "etsy_upload")
    n = len(meta)
    ws = [m["width_in"] for m in meta]
    sizes = f"Designs range from {min(ws):.1f} to {max(ws):.1f} inches wide at 300 dpi."
    with rep.stage("guide PDF"):
        kit.pdf_guide(dirs["root"] / "etsy_upload" / "Guide_and_Commercial_License.pdf", guide_pages(niche, n, sizes), niche.theme)
    rep.facts.update({"designs": n, "zips": zips, "templates": {t: sum(1 for m in meta if m["template"] == t) for t in {m["template"] for m in meta}},
                      "max_nodes": max(m["nodes"] for m in meta)})
    return {"niche": niche, "meta": meta, "dirs": dirs, "report": rep, "zips": zips}


# ----------------------------------------------------------------------------- niche registry
def get_niche(key: str) -> Niche:
    from .niche_defs import NICHES
    return NICHES[key]


if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 else "sarcasm"
    c = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out = build(k, c)
    print(json.dumps({"designs": len(out["meta"]), "zips": out["zips"]}, indent=2))
