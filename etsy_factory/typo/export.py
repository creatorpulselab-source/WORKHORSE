"""Exporters for welded vector geometry (shapely, y-UP, units = millimetres): SVG (Cricut/Silhouette), PNG (300 dpi, alpha),
DXF, EPS, plus fast thumbnails.  SVG width/height are written in real inches so the file imports at the stated size."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw
from shapely.geometry.base import BaseGeometry

from .text import polys

MM_PER_IN = 25.4


def _flip(g: BaseGeometry) -> Tuple[float, float, float, float]:
    return g.bounds


def _ring_d(coords, ox, oy, h) -> str:
    pts = list(coords)[:-1]
    s = f"M{pts[0][0] - ox:.2f} {h - (pts[0][1] - oy):.2f}"
    for x, y in pts[1:]:
        s += f"L{x - ox:.2f} {h - (y - oy):.2f}"
    return s + "Z"


def path_d(geom: BaseGeometry, ox: float, oy: float, h: float) -> str:
    out = []
    for p in polys(geom):
        out.append(_ring_d(p.exterior.coords, ox, oy, h))
        for r in p.interiors:
            out.append(_ring_d(r.coords, ox, oy, h))
    return "".join(out)


def count_nodes(geom: BaseGeometry) -> int:
    n = 0
    for p in polys(geom):
        n += len(p.exterior.coords) - 1 + sum(len(r.coords) - 1 for r in p.interiors)
    return n


def write_svg(path: Path, layers: Sequence[Tuple[str, BaseGeometry, str]], width_in: Optional[float] = None, title: str = "",
              margin_mm: float = 0.0) -> Dict:
    """layers: [(id, geometry, fill_hex)] bottom->top. Single compound path per layer, fill-rule evenodd, no strokes."""
    from shapely.ops import unary_union
    allg = unary_union([g for _, g, _ in layers if not g.is_empty])
    x0, y0, x1, y1 = allg.bounds
    x0 -= margin_mm; y0 -= margin_mm; x1 += margin_mm; y1 += margin_mm
    w, h = x1 - x0, y1 - y0
    wi = (w / MM_PER_IN) if width_in is None else width_in
    hi = wi * h / w
    body = []
    for lid, g, fill in layers:
        if g.is_empty:
            continue
        body.append(f'<g id="{lid}"><path fill="{fill}" fill-rule="evenodd" d="{path_d(g, x0, y0, h)}"/></g>')
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{wi:.3f}in" height="{hi:.3f}in" viewBox="0 0 {w:.2f} {h:.2f}">\n'
           f'<title>{title}</title>\n' + "\n".join(body) + "\n</svg>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return {"width_in": round(wi, 2), "height_in": round(hi, 2), "nodes": sum(count_nodes(g) for _, g, _ in layers)}


def write_dxf(path: Path, geom: BaseGeometry) -> None:
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=7)
    msp = doc.modelspace()
    x0, y0, _, _ = geom.bounds
    for p in polys(geom):
        for ring in [p.exterior, *p.interiors]:
            pts = [(x - x0, y - y0) for x, y in list(ring.coords)[:-1]]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(path))


def write_eps(path: Path, geom: BaseGeometry) -> None:
    k = 72.0 / MM_PER_IN
    x0, y0, x1, y1 = geom.bounds
    lines = ["%!PS-Adobe-3.0 EPSF-3.0", f"%%BoundingBox: 0 0 {int((x1 - x0) * k) + 1} {int((y1 - y0) * k) + 1}",
             f"%%HiResBoundingBox: 0 0 {(x1 - x0) * k:.3f} {(y1 - y0) * k:.3f}", "%%Pages: 1", "%%EndComments", "newpath", "0 setgray"]
    for p in polys(geom):
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)[:-1]
            lines.append(f"{(pts[0][0] - x0) * k:.2f} {(pts[0][1] - y0) * k:.2f} moveto")
            lines += [f"{(x - x0) * k:.2f} {(y - y0) * k:.2f} lineto" for x, y in pts[1:]]
            lines.append("closepath")
    lines += ["eofill", "showpage", "%%EOF"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def mask(geom: BaseGeometry, width_px: int, pad_px: int = 0, supersample: int = 2,
         bounds: Optional[Tuple[float, float, float, float]] = None) -> Image.Image:
    """Antialiased L mask of the geometry, width_px wide (+pad). Big polygons first so islands inside holes survive."""
    x0, y0, x1, y1 = bounds or geom.bounds
    w, h = x1 - x0, y1 - y0
    s = width_px * supersample / w
    W, H = int(round(w * s)) + 2 * pad_px * supersample, int(round(h * s)) + 2 * pad_px * supersample
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    off = pad_px * supersample
    ps = polys(geom)
    if len(ps) > 1:
        from shapely.geometry import Polygon as _P
        from shapely.strtree import STRtree
        ext = [_P(p.exterior) for p in ps]
        tree = STRtree(ext)
        depth = []
        for i, p in enumerate(ps):
            hits = tree.query(p.representative_point(), predicate="within")
            depth.append(sum(1 for j in hits if j != i))
        order = sorted(range(len(ps)), key=lambda i: (depth[i], -ps[i].area))
        ps = [ps[i] for i in order]
    for p in ps:
        d.polygon([((x - x0) * s + off, (y1 - y) * s + off) for x, y in p.exterior.coords], fill=255)
        for r in p.interiors:
            d.polygon([((x - x0) * s + off, (y1 - y) * s + off) for x, y in r.coords], fill=0)
    if supersample > 1:
        im = im.resize((W // supersample, H // supersample), Image.LANCZOS)
    return im


def write_png(path: Path, layers: Sequence[Tuple[BaseGeometry, Tuple[int, int, int]]], width_px: int = 3600,
              dpi: int = 300, palette: bool = True) -> None:
    """Transparent RGBA PNG. layers: [(geometry, rgb)] bottom->top, all rendered in one shared frame."""
    from shapely.ops import unary_union
    allg = unary_union([g for g, _ in layers if not g.is_empty])
    b = allg.bounds
    canvas = None
    for g, rgb in layers:
        if g.is_empty:
            continue
        m = mask(g, width_px, bounds=b)
        if canvas is None:
            canvas = Image.new("RGBA", m.size, (0, 0, 0, 0))
        col = Image.new("RGBA", m.size, rgb + (255,))
        col.putalpha(m)
        canvas.alpha_composite(col)
    path.parent.mkdir(parents=True, exist_ok=True)
    if palette:
        ncol = 40 if len([1 for g, _ in layers if not g.is_empty]) == 1 else 128
        canvas = canvas.quantize(colors=ncol, method=Image.Quantize.FASTOCTREE)
    canvas.save(path, dpi=(dpi, dpi), optimize=True)


def thumb(geom: BaseGeometry, px: int, ink=(0, 0, 0), bg=(255, 255, 255), pad: float = 0.08) -> Image.Image:
    """Square thumbnail of a design (ink on bg), geometry fitted and centred."""
    x0, y0, x1, y1 = geom.bounds
    w, h = x1 - x0, y1 - y0
    side = max(w, h) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
    m = mask(geom, px, bounds=b, supersample=2)
    out = Image.new("RGB", m.size, bg)
    out.paste(Image.new("RGB", m.size, ink), mask=m)
    return out


def thumb_layers(layers, px: int, bg=(255, 255, 255), pad: float = 0.08) -> Image.Image:
    """Square thumbnail of a multi-colour design: layers = [(geometry, rgb)] bottom->top."""
    from shapely.ops import unary_union
    allg = unary_union([g for g, _ in layers if not g.is_empty])
    x0, y0, x1, y1 = allg.bounds
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
    out = Image.new("RGB", (px, px), bg)
    for g, rgb in layers:
        if g.is_empty:
            continue
        m = mask(g, px, bounds=b, supersample=2)
        out.paste(Image.new("RGB", m.size, rgb), mask=m)
    return out
