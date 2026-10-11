"""Pro color-correction + retouch engine for WORKHORSE (pure numpy/cv2, no file I/O).

Why this exists: the legacy `apply_color_grade` presets multiply fixed per-channel
constants onto every photo regardless of its content, so already-warm photos got
pushed further orange, skin went off-hue, shadows crushed and highlights were never
touched. This engine instead MEASURES each image and applies bounded corrections:

  1. Adaptive skin model (LAB prior + robust Mahalanobis refinement) -> soft skin mask
  2. Linear-light exposure: white-point gain, filmic highlight shoulder, local-adaptive
     shadow lift, skin shine compression (all luminance-ratio based, hue preserving)
  3. Skin-anchored colour-cast correction in LAB a/b (bounded; coloured stage gels,
     tattoos and clothing are protected by chroma attenuation)
  4. Masked retouch at reduced resolution (blemish healing + tone evening) re-applied
     to the full-res image so pore texture is never touched
  5. Gentle L*-only contrast curve and luminance-only, skin-aware sharpening

Input : uint8 BGR (OpenCV convention).  Output: float32 BGR in 0..1 (sRGB encoded) +
a report dict.  Callers quantize (with dither) when writing.
"""
from typing import Dict, Any, Optional, Tuple

import cv2
import numpy as np

PROXY_LONG_EDGE = 1024
SKIN_HUE_BAND = (36.0, 54.0)       # target LAB hue angle (deg) for healthy, neutral skin
SKIN_CHROMA_BAND = (12.0, 34.0)    # LAB chroma clamp for skin


# ----------------------------------------------------------------------------- utils
def _smoothstep(lo: float, hi: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _srgb_to_linear(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def _linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def _luma_lin(bgr_lin: np.ndarray) -> np.ndarray:
    return (0.0722 * bgr_lin[..., 0] + 0.7152 * bgr_lin[..., 1] + 0.2126 * bgr_lin[..., 2]).astype(np.float32)


def _resize_to_long_edge(img: np.ndarray, long_edge: int) -> Tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    s = min(1.0, long_edge / float(max(h, w)))
    if s >= 1.0:
        return img, 1.0
    return cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA), s


def _up(small: np.ndarray, hw: Tuple[int, int]) -> np.ndarray:
    return cv2.resize(small, (hw[1], hw[0]), interpolation=cv2.INTER_CUBIC)


# ----------------------------------------------------------------------- skin model
def estimate_skin(lab: np.ndarray) -> Tuple[np.ndarray, Optional[Dict[str, float]]]:
    """Adaptive skin mask from a float32 LAB image (L 0..100). Returns (soft mask 0..1,
    stats). Walls/gels/clothing that share skin hue are limited by chroma + the
    per-image Gaussian fit; lips/tattoos fall outside the fitted cluster."""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    chroma = np.hypot(a, b)
    hue = np.degrees(np.arctan2(b, a))
    prior = ((a > 6) & (a < 30) & (b > 7) & (b < 36) & (L > 18) & (L < 92)
             & (hue > 28) & (hue < 68) & (chroma < 38))
    n = int(prior.sum())
    if n < 0.002 * L.size:
        return np.zeros_like(L), None

    feats = lab[prior]
    mu = np.median(feats, axis=0)
    cov = np.cov(feats.T) + np.eye(3) * 1.0
    flat = lab.reshape(-1, 3)
    for _ in range(3):
        diff = flat - mu
        d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(cov), diff).reshape(L.shape)
        inl = prior & (d2 < 5.0)
        if int(inl.sum()) < 0.001 * L.size:
            break
        f = lab[inl]
        mu = f.mean(axis=0)
        cov = np.cov(f.T) + np.eye(3) * 1.0
    diff = flat - mu
    d2 = np.einsum("ij,jk,ik->i", diff, np.linalg.inv(cov), diff).reshape(L.shape)
    soft = np.clip(1.0 - (d2 - 3.0) / 7.0, 0.0, 1.0)
    prior_soft = cv2.GaussianBlur(prior.astype(np.float32), (0, 0), 1.0)
    mask = (soft * prior_soft).astype(np.float32)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    mask = cv2.GaussianBlur(mask, (0, 0), 1.5)
    core = mask > 0.6
    if int(core.sum()) < 0.001 * L.size:
        return np.zeros_like(L), None
    sa, sb, sL = a[core], b[core], L[core]
    stats = {
        "coverage_pct": float(100.0 * core.mean()),
        "L": float(np.median(sL)),
        "a": float(np.median(sa)),
        "b": float(np.median(sb)),
        "chroma": float(np.median(np.hypot(sa, sb))),
        "hue_deg": float(np.degrees(np.arctan2(np.median(sb), np.median(sa)))),
    }
    return mask, stats


# ------------------------------------------------------------------------- stages
def _tone_curve_luma(y_lin: np.ndarray, y_base_lin: np.ndarray, skin_p: Optional[float],
                     skin_mask: np.ndarray, p: Dict[str, float]) -> np.ndarray:
    """Maps linear luminance -> corrected linear luminance (hue preserved by ratio scaling)."""
    ev = p["exposure_ev"]
    y = y_lin * np.float32(2.0 ** ev)

    # Shadows: lift driven by a heavily blurred base so it is halo-free and
    # fades toward true black (no noise amplification, no raised black point).
    base_d = np.power(np.clip(y_base_lin * 2.0 ** ev, 1e-6, 1.0), 1 / 2.2)
    sh_amt = p["shadow_ev"] * (1.0 - _smoothstep(0.10, 0.55, base_d)) * _smoothstep(0.0, 0.06, base_d)
    y = y * np.exp2(sh_amt).astype(np.float32)

    yd = np.power(np.clip(y, 0.0, None), 1 / 2.2)

    # Skin shine compression: pull hotspots toward the skin's own highlight level
    if skin_p is not None and p["shine"] > 0:
        excess = np.clip(yd - (skin_p + 0.03), 0.0, None)
        yd = yd - p["shine"] * skin_mask * excess

    # Filmic shoulder: preserves highlight gradation instead of clipping
    k = p["knee"]
    over = np.clip(yd - k, 0.0, None)
    yd = np.where(yd > k, k + (1.0 - k) * (1.0 - np.exp(-over / (1.0 - k))) * p["shoulder_gain"], yd)
    return np.power(np.clip(yd, 0.0, 1.0), 2.2).astype(np.float32)


def _heal_delta(lab_small: np.ndarray, core: np.ndarray) -> np.ndarray:
    """Blemish delta (LAB units, small-res): replaces isolated spots with the local
    median. Restricted to confident skin and small compact blobs so tattoos, jewellery,
    lace and other large structures are left alone."""
    enc = np.empty(lab_small.shape, np.uint8)
    enc[..., 0] = np.clip(lab_small[..., 0] * 2.55, 0, 255)
    enc[..., 1] = np.clip(lab_small[..., 1] + 128, 0, 255)
    enc[..., 2] = np.clip(lab_small[..., 2] + 128, 0, 255)
    med = cv2.medianBlur(enc, 9)
    med_lab = np.empty_like(lab_small)
    med_lab[..., 0] = med[..., 0] / 2.55
    med_lab[..., 1] = med[..., 1].astype(np.float32) - 128
    med_lab[..., 2] = med[..., 2].astype(np.float32) - 128
    dev_l = lab_small[..., 0] - med_lab[..., 0]
    dev_a = lab_small[..., 1] - med_lab[..., 1]
    cand = (((dev_l < -2.5) | (dev_a > 3.5)) & (dev_l > -14) & core).astype(np.uint8)
    n, labels, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    keep = np.zeros_like(cand)
    for i in range(1, n):
        area = st[i, cv2.CC_STAT_AREA]
        w, h = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        if 2 <= area <= 40 and max(w, h) <= 3 * max(1, min(w, h)) + 2:
            keep[labels == i] = 1
    if not keep.any():
        return np.zeros_like(lab_small)
    m = cv2.GaussianBlur(cv2.dilate(keep, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)
    return (med_lab - lab_small) * np.clip(m * 1.6, 0, 1)[..., None]


def process_image(img_bgr: np.ndarray, smooth_strength: float = 0.35,
                  overrides: Optional[Dict[str, float]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Full pro pass. Returns (float32 BGR 0..1 sRGB-encoded, report)."""
    p = {
        "target_white": 0.93,       # display level the P99.7 highlight is nudged toward
        "max_ev": 0.35,             # cap on white-point gain
        "ev_strength": 0.6,         # partial: scenes are intentionally moody
        "shadow_ev": 0.30,          # max local shadow lift
        "knee": 0.78, "shoulder_gain": 1.0,
        "shine": 0.45,
        "cast_max": 7.0,            # max LAB a/b shift
        "contrast": 0.10,
        "sharpen": 0.35,
        "heal": 1.0,
        "tone_even": 0.5,
    }
    if overrides:
        p.update(overrides)
    report: Dict[str, Any] = {}

    src = img_bgr.astype(np.float32) / 255.0
    hw = src.shape[:2]
    long_edge = max(hw)

    # ---------- analysis on proxy ----------
    proxy, _ = _resize_to_long_edge(src, PROXY_LONG_EDGE)
    proxy_lab = cv2.cvtColor(proxy, cv2.COLOR_BGR2LAB)
    skin_px, skin_stats = estimate_skin(proxy_lab)
    report["skin_before"] = skin_stats

    proxy_lin = _srgb_to_linear(proxy)
    py = _luma_lin(proxy_lin)
    p997 = float(np.percentile(np.power(py, 1 / 2.2), 99.7))
    gain_ev = 0.0
    if p997 < p["target_white"]:
        full = 2.2 * np.log2(p["target_white"] / max(p997, 1e-3))
        gain_ev = float(min(max(full, 0.0) * p["ev_strength"], p["max_ev"]))
    p["exposure_ev"] = gain_ev
    report.update({"p99_7_before": round(p997, 4), "exposure_ev": round(gain_ev, 3)})

    skin_p = None
    if skin_stats is not None:
        sel = skin_px > 0.6
        skin_p = float(np.percentile(np.power(np.clip(py[sel] * 2.0 ** gain_ev, 0, 1), 1 / 2.2), 88))

    # ---------- full-res tone ----------
    lin = _srgb_to_linear(src)
    del src
    y = _luma_lin(lin)
    base = cv2.GaussianBlur(cv2.resize(y, (proxy.shape[1], proxy.shape[0]), interpolation=cv2.INTER_AREA), (0, 0), 6)
    base_full = _up(base, hw)
    skin_full = np.clip(_up(skin_px, hw), 0, 1) if skin_stats is not None else np.zeros(hw, np.float32)
    y_new = _tone_curve_luma(y, base_full, skin_p, skin_full, p)
    ratio = np.clip(y_new / np.maximum(y, 1e-4), 0.0, 4.0)
    ratio = np.where(y < 1e-3, 1.0, ratio).astype(np.float32)
    lin *= ratio[..., None]
    del ratio, y, y_new, base_full, skin_full
    disp = _linear_to_srgb(lin)
    del lin

    # ---------- colour (LAB) ----------
    lab = cv2.cvtColor(disp, cv2.COLOR_BGR2LAB)
    del disp
    plab, _ = _resize_to_long_edge(lab, PROXY_LONG_EDGE)
    skin_px2, st2 = estimate_skin(plab)
    sk_full = None

    if st2 is not None:
        h = st2["hue_deg"]
        lo, hi = SKIN_HUE_BAND
        target_h = float(np.clip(h, lo, hi))
        target_c = float(np.clip(st2["chroma"], *SKIN_CHROMA_BAND))
        ta, tb = target_c * np.cos(np.radians(target_h)), target_c * np.sin(np.radians(target_h))
        skin_shift = np.array([ta - st2["a"], tb - st2["b"]], np.float32)
        # Neutral anchor: bright low-chroma pixels should sit near a=b=0 (whites/teeth/eyes)
        pL, pa, pb = plab[..., 0], plab[..., 1], plab[..., 2]
        neut = (pL > 70) & (np.hypot(pa, pb) < 14) & (skin_px2 < 0.1)
        neutral_shift = None
        if neut.sum() > 0.003 * pL.size:
            neutral_shift = np.array([-float(np.median(pa[neut])), -float(np.median(pb[neut]))], np.float32) * 0.5
        shift = skin_shift if neutral_shift is None else 0.6 * skin_shift + 0.4 * neutral_shift
        mag = float(np.hypot(*shift))
        if mag > p["cast_max"]:
            shift = shift * (p["cast_max"] / mag)
        report["cast_shift_ab"] = [round(float(shift[0]), 2), round(float(shift[1]), 2)]

        sk_full = np.clip(_up(skin_px2, hw), 0, 1)
        chroma_full = np.hypot(lab[..., 1], lab[..., 2])
        # Protect strongly saturated pixels (gels, tattoos, clothing): attenuate shift
        w = (0.55 + 0.45 * sk_full) / (1.0 + (chroma_full / 48.0) ** 2)
        lab[..., 1] += shift[0] * w
        lab[..., 2] += shift[1] * w
        del chroma_full, w

        # ---- masked retouch at reduced res, applied as a delta onto full-res ----
        if smooth_strength > 0 or p["heal"] > 0:
            q = 0.25 if long_edge > 2400 else 0.5
            small = cv2.resize(lab, None, fx=q, fy=q, interpolation=cv2.INTER_AREA)
            sk_small = cv2.resize(sk_full, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
            delta = np.zeros_like(small)
            if smooth_strength > 0:
                bil = cv2.bilateralFilter(small, d=9, sigmaColor=8.4, sigmaSpace=5)
                d_t = bil - small
                # even chroma toward the LOCAL skin mean (not a global mean)
                m = cv2.GaussianBlur(sk_small, (0, 0), 6) + 1e-4
                lm_a = cv2.GaussianBlur(small[..., 1] * sk_small, (0, 0), 6) / m
                lm_b = cv2.GaussianBlur(small[..., 2] * sk_small, (0, 0), 6) / m
                d_t[..., 1] += p["tone_even"] * (lm_a - small[..., 1])
                d_t[..., 2] += p["tone_even"] * (lm_b - small[..., 2])
                np.clip(d_t, -4.0, 4.0, out=d_t)
                delta += d_t * (smooth_strength * sk_small)[..., None]
            if p["heal"] > 0:
                delta += _heal_delta(small, sk_small > 0.6) * p["heal"]
            lab += _up(delta, hw)
            del small, delta

        # soft chroma ceiling on skin (keeps retouched skin out of orange extremes)
        ca, cb = lab[..., 1], lab[..., 2]
        cc = np.hypot(ca, cb)
        over = np.clip(cc - SKIN_CHROMA_BAND[1] - 4.0, 0.0, None)
        fac = 1.0 - np.minimum(over * 0.5 / np.maximum(cc, 1e-3), 0.3) * sk_full
        lab[..., 1] = ca * fac
        lab[..., 2] = cb * fac
        report["skin_mask_cov_pct"] = round(st2["coverage_pct"], 2)

    # ---------- contrast (L only; mild S-curve) ----------
    if p["contrast"] > 0:
        t = np.clip(lab[..., 0] / 100.0, 0, 1)
        lab[..., 0] = np.clip(t + p["contrast"] * 2.0 * t * (1 - t) * (2 * t - 1), 0, 1) * 100.0

    # ---------- sharpen (luminance only, skin-aware) ----------
    if p["sharpen"] > 0:
        sig = max(0.8, long_edge / 2600.0)
        Lc = lab[..., 0]
        blur = cv2.GaussianBlur(Lc, (0, 0), sig)
        amt = np.full(hw, p["sharpen"], np.float32)
        if sk_full is not None:
            amt = amt * (1.0 - 0.5 * sk_full)
        lab[..., 0] = np.clip(Lc + (Lc - blur) * amt, 0, 100)

    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    np.clip(out, 0.0, 1.0, out=out)

    # ---------- after-report on proxy ----------
    oproxy, _ = _resize_to_long_edge(out, PROXY_LONG_EDGE)
    _, after = estimate_skin(cv2.cvtColor(oproxy, cv2.COLOR_BGR2LAB))
    report["skin_before"] = skin_stats
    report["skin_after"] = after
    oy = _luma_lin(_srgb_to_linear(oproxy))
    report["p99_7_after"] = round(float(np.percentile(np.power(oy, 1 / 2.2), 99.7)), 4)
    return out, report


def to_uint8_dithered(img_f: np.ndarray, seed: int = 7) -> np.ndarray:
    """float 0..1 -> uint8 with triangular dither to avoid banding in smooth gradients."""
    rng = np.random.default_rng(seed)
    out = np.empty(img_f.shape, np.uint8)
    rows = 256
    for y0 in range(0, img_f.shape[0], rows):
        blk = img_f[y0:y0 + rows] * 255.0
        noise = rng.random(blk.shape, dtype=np.float32) + rng.random(blk.shape, dtype=np.float32) - 1.0
        out[y0:y0 + rows] = np.clip(blk + noise * 0.75, 0, 255).round().astype(np.uint8)
    return out
