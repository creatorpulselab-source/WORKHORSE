"""Cut-out for illustrations generated on a flat key-colour background.

Two stages: (1) rembg/isnet matte - on a saturated key background it no longer swallows white or cream parts of the art
(on white it erased Santa's beard and cream stripes); (2) a colour-key ramp along the matte edge plus spill removal so no
coloured halo is left, even on dark mockups.
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


def _border_color(rgb: np.ndarray) -> np.ndarray:
    ring = np.concatenate([rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3), rgb[:, :8].reshape(-1, 3), rgb[:, -8:].reshape(-1, 3)])
    return np.median(ring, axis=0)


def cut_key(src: Path, dst: Path, long_side: int = 2400, pad_frac: float = 0.03, t_lo: float = 40.0, t_hi: float = 100.0,
            matte: Optional[Image.Image] = None, hole_frac: float = 0.0) -> Optional[dict]:
    """Returns stats, or None when nothing usable is left."""
    from rembg import remove
    from scipy import ndimage as ndi

    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    key = _border_color(rgb)
    m = matte if matte is not None else remove(im, session=_session(), post_process_mask=True).getchannel("A")
    if m.size != im.size:
        m = m.resize(im.size, Image.LANCZOS)
    a = np.asarray(m).astype(np.float32) / 255.0

    # edge band: refine alpha with the key-colour distance so the rim carries no key colour
    d = np.sqrt(((rgb - key) ** 2).sum(-1))
    solid = a > 0.5
    rim = 2 if matte is not None else 4          # a supplied (BiRefNet) matte is trusted: only trim a thin rim
    band = ndi.binary_dilation(solid, iterations=rim) & ~ndi.binary_erosion(solid, iterations=rim)
    ramp = np.clip((d - t_lo) / (t_hi - t_lo), 0, 1)
    a = np.where(band, np.minimum(a, ramp), a)
    # key-coloured area that rembg kept inside a hole-free region next to the outside (shadows, gaps): drop big bg-like blobs
    keylike = d < t_lo
    lab, n = ndi.label(keylike)
    if n and matte is None:                      # skipped for a supplied matte: art can legitimately be key-coloured
        sizes = ndi.sum(np.ones_like(d), lab, index=np.arange(1, n + 1))
        kill = np.zeros(n + 1, bool)
        kill[1:] = sizes >= 400
        a = np.where(kill[lab], 0.0, a)

    # speckles
    lab2, n2 = ndi.label(a > 0.15)
    if n2 == 0:
        return None
    s2 = ndi.sum(np.ones_like(d), lab2, index=np.arange(1, n2 + 1))
    k2 = np.zeros(n2 + 1, bool)
    k2[1:] = s2 >= max(80, s2.max() * 0.004)
    a = a * k2[lab2]
    # small pinholes inside the art (rembg sometimes punches highlights): fill if not key-coloured
    inner = ndi.binary_fill_holes(a > 0.5) & (a < 0.5) & (d >= t_lo)
    il, ni = ndi.label(inner)
    if ni:
        isz = ndi.sum(np.ones_like(d), il, index=np.arange(1, ni + 1))
        small = np.zeros(ni + 1, bool)
        small[1:] = isz < max(d.size * 0.003, hole_frac * float((a > 0.5).sum()))
        a = np.where(small[il] & inner, 1.0, a)

    a3 = np.clip(a, 0, 1)[..., None]
    fg = np.where(a3 > 0.03, (rgb - (1 - a3) * key) / np.maximum(a3, 0.03), rgb)
    fg = np.clip(fg, 0, 255)
    out = np.dstack([fg, a3[..., 0] * 255.0]).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bb:
        return None
    img = img.crop(bb)
    w, h = img.size
    sc = long_side / max(w, h)
    pad = int(long_side * pad_frac)
    big = img.resize((max(1, round(w * sc)), max(1, round(h * sc))), Image.LANCZOS)
    big = Image.merge("RGBA", [*big.split()[:3], big.getchannel("A").filter(ImageFilter.GaussianBlur(0.5))])
    canvas = Image.new("RGBA", (big.width + 2 * pad, big.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(big, (pad, pad))
    dst.parent.mkdir(parents=True, exist_ok=True)
    mode = save_adaptive(canvas, dst)
    return {"w": canvas.width, "h": canvas.height, "coverage": float((a > 0.5).mean()), "bytes": dst.stat().st_size,
            "key": [int(x) for x in key], "mode": mode}


def save_adaptive(img: Image.Image, dst: Path, max_err: float = 2.2) -> str:
    """Palette PNG if its mean error on opaque pixels is <= max_err (of 255), else full RGBA PNG. Returns 'palette' or 'rgba'."""
    arr = np.asarray(img).astype(np.float32)
    q = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    back = np.asarray(q.convert("RGBA")).astype(np.float32)
    solid = arr[..., 3] > 200
    err = float(np.abs(arr[..., :3] - back[..., :3])[solid].mean()) if solid.any() else 0.0
    aerr = float(np.abs(arr[..., 3] - back[..., 3]).mean())
    if err <= max_err and aerr <= 1.0:
        q.save(dst, "PNG", dpi=(300, 300), optimize=True)
        return "palette"
    img.save(dst, "PNG", dpi=(300, 300), optimize=True, compress_level=9)
    return "rgba"
