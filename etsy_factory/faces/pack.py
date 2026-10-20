"""Cute Animal Faces layered cut-file pack: 20 animals x 3 versions (Layered colour, one-piece Stencil, Solid silhouette).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.faces.pack      then      -m etsy_factory.faces.build_listing

Per animal and version: SVG (real size in inches, one compound path per colour layer), DXF (one DXF layer per colour) and a 300 dpi
transparent PNG. Every file is generated from the 2D geometry in animals.py, so layers are exactly aligned and welded.
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, r"F:\WORKHORSE")

from shapely.geometry.base import BaseGeometry

from etsy_factory import kit
from etsy_factory.common import ETSY_MAX_FILE_BYTES, RunReport, listing_dirs
from etsy_factory.faces import animals as AN
from etsy_factory.typo import export as X
from etsy_factory.typo.text import polys

SLUG = "cute_animal_faces_layered_svg_cut_files"
MAX_IN = 5.0           # the longest side of every design is this many inches in the SVG

LICENSE_LINES = [
    "# Commercial small-business license (included)",
    "You MAY use these designs on physical products you make and sell - cards, stickers, paper crafts, shirts (HTV), mugs, tumblers, "
    "totes, signs, party decor - up to 500 units per design. No credit needed.",
    "You MAY NOT resell, share, give away, upload or redistribute the digital files (original or edited), include them in another "
    "bundle or digital product, upload them to print-on-demand sites that let others reuse them, or use them as a logo or trademark.",
    "Need more than 500 units per design? Message the shop for an extended license.",
    "All designs are original geometric animal faces. No licensed characters, brands or logos. Digital download - no physical item is "
    "shipped; if anything is wrong with a file contact the shop and it will be fixed.",
]


def rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))      # type: ignore[return-value]


def write_dxf_layers(path: Path, layers: List[Tuple[str, BaseGeometry, str]]) -> None:
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    allg = AN.U(*[g for _, g, _ in layers])
    x0, y0, _, _ = allg.bounds
    k = MAX_IN * 25.4 / max(allg.bounds[2] - x0, allg.bounds[3] - y0)
    for i, (name, g, _hx) in enumerate(layers, 1):
        lname = name[:30]
        doc.layers.add(lname, color=(i % 7) + 1)
        for p in polys(g):
            for r in [p.exterior, *p.interiors]:
                pts = [((x - x0) * k, (y - y0) * k) for x, y in list(r.coords)[:-1]]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": lname})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(path))


def write_dxf_scaled(path: Path, g: BaseGeometry) -> None:
    write_dxf_layers(path, [("CUT", g, "#000000")])


def width_in(g: BaseGeometry) -> Tuple[float, float]:
    x0, y0, x1, y1 = g.bounds
    s = MAX_IN / max(x1 - x0, y1 - y0)
    return round((x1 - x0) * s, 2), round((y1 - y0) * s, 2)


def build_animal(idx: int, key: str, files: Path, thumbs: Path) -> Dict:
    a = AN.A[key]
    name = f"{idx:02d}_{a.name}"
    outline = a.outline()
    wi, hi = width_in(outline)
    layers = a.svg_layers()
    # --- layered
    X.write_svg(files / "Layered" / "SVG" / f"{name}_Layered.svg", [(lid, g, hx) for lid, g, hx in layers], width_in=wi, title=f"{a.name} layered face")
    write_dxf_layers(files / "Layered" / "DXF" / f"{name}_Layered.dxf", layers)
    px = int(round(wi * 300))
    X.write_png(files / "Layered" / "PNG" / f"{name}_Layered_300dpi.png", [(g, rgb(hx)) for _, g, hx in layers], px)
    # --- one-piece stencil (face parts cut out)
    st = a.stencil()
    X.write_svg(files / "Stencil" / "SVG" / f"{name}_Stencil.svg", [("Cut", st, "#000000")], width_in=wi, title=f"{a.name} stencil")
    write_dxf_scaled(files / "Stencil" / "DXF" / f"{name}_Stencil.dxf", st)
    X.write_png(files / "Stencil" / "PNG" / f"{name}_Stencil_300dpi.png", [(st, (0, 0, 0))], px)
    # --- solid silhouette
    X.write_svg(files / "Solid" / "SVG" / f"{name}_Solid.svg", [("Cut", outline, "#000000")], width_in=wi, title=f"{a.name} silhouette")
    write_dxf_scaled(files / "Solid" / "DXF" / f"{name}_Solid.dxf", outline)
    X.write_png(files / "Solid" / "PNG" / f"{name}_Solid_300dpi.png", [(outline, (0, 0, 0))], px)
    thumbs.mkdir(parents=True, exist_ok=True)
    X.thumb(outline, 520, pad=0.04).save(thumbs / f"{name}.png")
    X.thumb_layers([(g, rgb(hx)) for _, g, hx in layers], 520, pad=0.04).save(thumbs / f"{name}_c.png")
    return {"index": idx, "name": name, "text": a.name, "key": key, "width_in": wi, "height_in": hi, "layers": len(layers),
            "colors": [hx for _, _, hx in layers], "nodes": sum(X.count_nodes(g) for _, g, _ in layers)}


def make_zips(files: Path, out: Path) -> Dict[str, float]:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.zip"):
        old.unlink()
    res = {}
    for zname, sub in [("Layered_Color_SVG_DXF_PNG.zip", "Layered"), ("Stencil_One_Piece_SVG_DXF_PNG.zip", "Stencil"), ("Solid_Silhouette_SVG_DXF_PNG.zip", "Solid")]:
        z = out / zname
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for f in sorted((files / sub).rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=str(f.relative_to(files / sub)))
        if z.stat().st_size > ETSY_MAX_FILE_BYTES:
            raise RuntimeError(f"{zname} is {z.stat().st_size / 1e6:.1f} MB (>20 MB)")
        res[zname] = round(z.stat().st_size / 1e6, 2)
    return res


def guide_pages(n: int, sizes: str) -> List[Tuple[str, List[str]]]:
    return [("Cute Animal Faces - Quick Start", [
        f"Thank you for your purchase! This pack has {n} cute animal faces, each in 3 versions - {n * 3} designs in total.",
        "# What is inside the download",
        f"- Layered_Color_SVG_DXF_PNG.zip - the full-colour face split into one layer per colour (body, ears, muzzle, eyes, blush ...). "
        "Cut each layer from a different colour of cardstock, vinyl or felt and stack them. Folders: SVG, DXF, PNG.",
        "- Stencil_One_Piece_SVG_DXF_PNG.zip - ONE connected piece: the silhouette with the eyes, nose and mouth cut out. For stencils, "
        "single-colour vinyl, wood and laser projects. Folders: SVG, DXF, PNG.",
        "- Solid_Silhouette_SVG_DXF_PNG.zip - the plain outline shape for bases, stickers, tags, keychains and cake toppers.",
        "- This guide and the license.",
        "# Sizes", sizes + " Every SVG is saved at its real size in inches - scale it in your software to fit your project.",
    ]), ("Using the layered files", [
        "# Cricut Design Space",
        "Upload > Upload Image > Browse > pick a _Layered.svg > Save. The colours arrive as separate layers - each colour is its own mat. "
        "Cut every colour on its own mat, then glue the layers in order (Layer_01 at the bottom).",
        "# Silhouette Studio (Designer Edition or higher for SVG)",
        "File > Open the SVG. Without Designer Edition use the DXF - each colour is a separate DXF layer.",
        "# Paper-cut and shadow-box look",
        "Glue the layers with foam tape or dots of glue so each colour sits slightly above the one below it.",
        "# Heat transfer vinyl and felt",
        "Mirror the design before cutting HTV. Weed, then press layer by layer from the bottom up.",
        "# Tips",
        "Layer names carry the colour code (for example Layer_03_Detail_F7B5C4) so you can match paper colours. The colours are suggestions - recolour freely.",
    ]), ("Commercial license", LICENSE_LINES)]


def build() -> Dict:
    rep = RunReport(SLUG)
    dirs = listing_dirs(SLUG)
    files, thumbs = dirs["files"], dirs["work"] / "thumbs"
    for p in (files, thumbs):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    with rep.stage(f"build {len(AN.ORDER)} animals x 3 versions x 3 formats"):
        meta = [build_animal(i, k, files, thumbs) for i, k in enumerate(AN.ORDER, 1)]
    (dirs["root"] / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with rep.stage("zip deliverables"):
        zips = make_zips(files, dirs["root"] / "etsy_upload")
    n = len(meta)
    sizes = f"Designs are {min(m['width_in'] for m in meta):.1f} to {max(m['width_in'] for m in meta):.1f} inches wide (longest side {MAX_IN:.0f} inches)."
    with rep.stage("guide PDF"):
        kit.pdf_guide(dirs["root"] / "etsy_upload" / "Guide_and_Commercial_License.pdf", guide_pages(n, sizes), "sunny")
    rep.facts.update({"animals": n, "svg_files": len(list(files.rglob("*.svg"))), "dxf_files": len(list(files.rglob("*.dxf"))),
                      "png_files": len(list(files.rglob("*.png"))), "zips": zips, "max_layers": max(m["layers"] for m in meta)})
    rep.save(dirs["root"])
    return rep.facts


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
