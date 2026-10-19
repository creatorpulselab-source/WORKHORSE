"""Turn a raw white-background illustration into a clean transparent 300-dpi PNG.

rembg (isnet-general-use) for the matte, white-halo decontamination for soft edges, speck removal, tight crop, Lanczos upscale.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

_SESSION = None


def _session():
    global _SESSION
    if _SESSION is None:
        from rembg import new_session
        _SESSION = new_session("isnet-general-use")
    return _SESSION


def cut(src: Path, dst: Path, long_side: int = 2400, pad_frac: float = 0.03) -> Optional[dict]:
    """Returns stats dict, or None if no usable subject was found."""
    from rembg import remove
    from scipy import ndimage as ndi

    im = Image.open(src).convert("RGB")
    cut_ = remove(im, session=_session(), post_process_mask=True)  # RGBA
    a = np.asarray(cut_.split()[-1]).astype(np.float32) / 255.0
    rgb = np.asarray(im).astype(np.float32)

    # drop tiny disconnected specks (keep anything >= 0.4% of the largest piece)
    lab, n = ndi.label(a > 0.12)
    if n == 0:
        return None
    sizes = ndi.sum(np.ones_like(a), lab, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= max(60, sizes.max() * 0.004)
    a = a * keep[lab]
    # fill pinholes inside the subject that rembg may have punched (e.g. white cow fur / ornament highlights)
    solid = ndi.binary_fill_holes(a > 0.5)
    inner = solid & (a < 0.5)
    inner_lab, ni = ndi.label(inner)
    if ni:
        isz = ndi.sum(np.ones_like(a), inner_lab, index=np.arange(1, ni + 1))
        small = np.zeros(ni + 1, bool)
        small[1:] = isz < a.size * 0.004  # only small holes; big holes (wreath centres) stay transparent
        a = np.where(small[inner_lab] & inner, 1.0, a)

    # decontaminate the white halo: C = a*F + (1-a)*255  ->  F = (C - (1-a)*255) / a
    al = np.clip(a, 0.0, 1.0)[..., None]
    fg = np.where(al > 0.02, (rgb - (1 - al) * 255.0) / np.maximum(al, 0.02), rgb)
    fg = np.clip(fg, 0, 255)
    # pull the semi-transparent rim in a hair so no light fringe survives on dark backgrounds
    a2 = np.clip((al[..., 0] - 0.08) / 0.92, 0, 1)
    out = np.dstack([fg, a2 * 255.0]).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")

    bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bb:
        return None
    img = img.crop(bb)
    w, h = img.size
    scale = long_side / max(w, h)
    pad = int(long_side * pad_frac)
    big = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    big = Image.merge("RGBA", [*big.split()[:3], big.getchannel("A").filter(ImageFilter.GaussianBlur(0.6))])
    canvas = Image.new("RGBA", (big.width + 2 * pad, big.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(big, (pad, pad))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, "PNG", dpi=(300, 300), optimize=True, compress_level=9)
    cov = float((a > 0.5).sum()) / a.size
    return {"w": canvas.width, "h": canvas.height, "coverage": cov, "bytes": dst.stat().st_size}
