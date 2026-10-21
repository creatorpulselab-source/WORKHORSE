"""DaVinci Resolve 3D LUT Color Correction for Listing Media.
Applies signature 33x33x33 .cube LUTs with filmic S-curves, Kodak 2383 color science,
and warm editorial highlight roll-off to harmonize all ComfyUI-generated product media.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.davinci_resolve_bridge import davinci_resolve_bridge


def get_or_create_lut() -> Path:
    lut_p = Path(r"F:\WORKHORSE\workspace\luts\Workhorse_Cinematic_Filmic_Matte.cube")
    if not lut_p.exists():
        lut_p = davinci_resolve_bridge.generate_cinematic_cube_lut(
            lut_name="Workhorse_Cinematic_Filmic_Matte.cube",
            size=33
        )
    return lut_p


def grade_image(
    input_path: Path,
    output_path: Optional[Path] = None,
    lut_path: Optional[Path] = None,
    blend_factor: float = 0.75
) -> Path:
    """
    Applies DaVinci Resolve 3D LUT color correction to an image.
    blend_factor allows blending original with graded image (0.75 = 75% graded, 25% original).
    """
    out_p = output_path or input_path
    lut_p = lut_path or get_or_create_lut()
    lut_table = davinci_resolve_bridge.load_cube_lut_table(lut_p)

    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {input_path}")

    # Separate alpha channel if present
    has_alpha = len(img.shape) == 3 and img.shape[2] == 4
    if has_alpha:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
    else:
        bgr = img
        alpha = None

    graded_bgr = davinci_resolve_bridge.apply_cube_lut_to_bgr_frame(bgr, lut_table)

    if blend_factor < 1.0:
        graded_bgr = cv2.addWeighted(graded_bgr, blend_factor, bgr, 1.0 - blend_factor, 0)

    if has_alpha:
        out_img = np.dstack((graded_bgr, alpha))
    else:
        out_img = graded_bgr

    out_p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_p), out_img)
    return out_p


def batch_grade_directory(dir_path: Path, pattern: str = "comfy_*.png"):
    lut_p = get_or_create_lut()
    files = list(dir_path.glob(pattern))
    print(f"[DaVinci Resolve] Color correcting {len(files)} media images with {lut_p.name}...")
    for f in sorted(files):
        out_f = f.parent / f"graded_{f.name}"
        grade_image(f, out_f, lut_p)
        print(f"  [Grade OK] {f.name} -> {out_f.name}")


if __name__ == "__main__":
    lut = get_or_create_lut()
    print("DaVinci Resolve Color Grade Engine Ready with LUT:", lut)
