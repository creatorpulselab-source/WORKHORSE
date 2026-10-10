import os
import json
import datetime
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import zipfile

# Named edit-style profiles bundling a color grade preset, retouch-pass settings, and
# delivery conventions (watermark on/off) for a given use case - lets callers (Synapse's
# aura_retouch tool, the dashboard's manual retouch panel) pick ONE style name instead of
# having to hand-tune half a dozen individual parameters. "glamour"/"boudoir" keeps the
# original heavy-retouch behavior; the newer styles cover the other work the Commander
# actually shoots (plain/everyday photos, live performers on stage, family/event candids).
STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "glamour": {
        "preset": "moody_boudoir",
        "smooth_strength": 0.55,
        "heal": True, "skin_tone": True, "mattify": True, "portrait_volumes": True,
        "eye_vessels": True,
        "watermark": True
    },
    "natural": {
        "preset": "natural_true_to_life",
        "smooth_strength": 0.2,
        "heal": True, "skin_tone": False, "mattify": False, "portrait_volumes": False,
        "eye_vessels": False,
        "watermark": False
    },
    "concert_stage": {
        "preset": "concert_stage",
        "smooth_strength": 0.15,
        # Mostly noise/blemish cleanup only - stage lighting mood and performer energy
        # should read as shot, not studio-polished.
        "heal": True, "skin_tone": False, "mattify": False, "portrait_volumes": False,
        "eye_vessels": False,
        "watermark": False
    },
    "family_event": {
        "preset": "family_event",
        "smooth_strength": 0.25,
        "heal": True, "skin_tone": True, "mattify": False, "portrait_volumes": False,
        "eye_vessels": True,
        "watermark": False
    }
}

class PhotoRetoucher:
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/photos_output"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

    def apply_skin_smoothing(self, img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """True frequency separation retouch: splits the image into a low-frequency
        (tone/blemish) layer and a high-frequency (pore/texture/hair) layer, smooths
        only the low layer, then recombines - avoids the waxy/plastic look of a
        simple blurred blend while still removing blemishes and uneven skin tone.

        Runs entirely in float32 end-to-end (including the bilateral smoothing pass,
        which OpenCV supports natively on 32-bit buffers) and only quantizes to uint8
        once, at the final return - eliminates an extra 8-bit round-trip that used to
        happen mid-pipeline and introduced avoidable banding/precision loss."""
        try:
            img_f = img.astype(np.float32)

            # Low frequency: heavy gaussian blur captures tone/blemishes, not fine detail
            low_freq = cv2.GaussianBlur(img_f, (0, 0), sigmaX=8)
            # High frequency: original minus low = pores, hair, fine texture detail
            high_freq = img_f - low_freq

            # Smooth blemishes/tone in the low layer only (edge-aware, preserves contours).
            # Kept in float32 (OpenCV's bilateralFilter supports CV_32F directly) instead
            # of round-tripping through uint8, which used to quantize/clip this layer
            # before recombination.
            low_smoothed = cv2.bilateralFilter(low_freq, d=15, sigmaColor=60, sigmaSpace=60)

            # Recombine: smoothed tone + original fine detail, blended by strength
            recombined = np.clip(low_smoothed + high_freq, 0, 255)
            result = cv2.addWeighted(img_f, 1.0 - strength, recombined, strength, 0)
            return np.clip(result, 0, 255).astype(np.uint8)
        except Exception:
            return img

    def apply_clarity_sharpen(self, img: np.ndarray, amount: float = 0.35) -> np.ndarray:
        """Unsharp-mask clarity pass: restores crisp detail (eyes, hair, fabric) lost to
        skin smoothing, the finishing step professional retouchers apply before export.

        Math runs in float32 and only quantizes once at the return, instead of
        addWeighted saturating intermediate values at 8-bit, which avoided one source
        of highlight/shadow clipping on high-contrast source photos."""
        try:
            img_f = img.astype(np.float32)
            blurred = cv2.GaussianBlur(img_f, (0, 0), sigmaX=3)
            sharpened = img_f * (1.0 + amount) - blurred * amount
            return np.clip(sharpened, 0, 255).astype(np.uint8)
        except Exception:
            return img

    def apply_color_grade(self, img: np.ndarray, preset: str = "moody_boudoir") -> np.ndarray:
        """Apply cinematic creator color grades using matrix transforms and curves."""
        img_float = img.astype(np.float32) / 255.0

        if preset == "moody_boudoir":
            # Boost warm shadow tones, increase contrast, deep rich blacks
            b, g, r = cv2.split(img_float)
            r = np.clip(r * 1.08 + 0.02, 0, 1)
            b = np.clip(b * 0.92 - 0.02, 0, 1)
            merged = cv2.merge([b, g, r])
            # Contrast curve
            graded = np.clip(merged ** 1.15 * 1.05, 0, 1)
            return (graded * 255.0).astype(np.uint8)

        elif preset == "golden_hour":
            # Warm amber glow
            b, g, r = cv2.split(img_float)
            r = np.clip(r * 1.15, 0, 1)
            g = np.clip(g * 1.05, 0, 1)
            b = np.clip(b * 0.85, 0, 1)
            graded = cv2.merge([b, g, r])
            return (graded * 255.0).astype(np.uint8)

        elif preset == "cyber_neon":
            # Cyan & Magenta split tone
            b, g, r = cv2.split(img_float)
            b = np.clip(b * 1.25, 0, 1)
            r = np.clip(r * 1.12, 0, 1)
            g = np.clip(g * 0.90, 0, 1)
            graded = cv2.merge([b, g, r])
            return (graded * 255.0).astype(np.uint8)

        elif preset == "monochrome_noir":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # High-contrast curve
            gray_norm = gray.astype(np.float32) / 255.0
            curved = np.clip(gray_norm ** 1.3 * 1.2, 0, 1)
            res_gray = (curved * 255.0).astype(np.uint8)
            return cv2.cvtColor(res_gray, cv2.COLOR_GRAY2BGR)

        elif preset == "vintage_35mm":
            # Matte blacks, gentle film lift
            b, g, r = cv2.split(img_float)
            r = np.clip(r * 1.05 + 0.04, 0, 1)
            g = np.clip(g * 1.02 + 0.02, 0, 1)
            b = np.clip(b * 0.95 + 0.04, 0, 1)
            graded = cv2.merge([b, g, r])
            return (graded * 255.0).astype(np.uint8)

        elif preset == "clean_editorial":
            # Neutral true-to-life tones with gentle lifted shadows - for business/brand clients
            b, g, r = cv2.split(img_float)
            lifted = np.clip(np.stack([b, g, r], axis=-1) * 1.03 + 0.015, 0, 1)
            graded = np.clip(lifted ** 1.05, 0, 1)
            return (graded * 255.0).astype(np.uint8)

        elif preset == "natural_true_to_life":
            # Deliberately the lightest-touch grade in the set: a hair of lifted shadow
            # and a near-neutral white balance nudge, nothing that reads as "edited" -
            # for regular/everyday photos where accuracy matters more than mood.
            b, g, r = cv2.split(img_float)
            r = np.clip(r * 1.015, 0, 1)
            b = np.clip(b * 0.99, 0, 1)
            graded = cv2.merge([b, g, r])
            graded = np.clip(graded ** 1.02 * 1.01, 0, 1)
            return (graded * 255.0).astype(np.uint8)

        elif preset == "concert_stage":
            # Live stage/concert photography is usually lit with heavily colored LED
            # washes (magenta, cyan, deep blue, green) that a venue's lighting designer
            # intends - the goal here is NOT to flatten that mood like a studio grade
            # would, but to pull just enough of the color cast off the performer's skin
            # tone (a gentle gray-world style correction) while keeping the stage's
            # background color and contrast dramatic, plus a mild lift on crushed
            # shadows and a highlight rolloff to tame blown-out spotlight hotspots.
            b, g, r = cv2.split(img_float)
            # Gentle gray-world correction toward the image's own mean (undoes some
            # color cast without fully neutralizing the venue's lighting design)
            means = [np.mean(ch) for ch in (b, g, r)]
            gray_mean = float(np.mean(means))
            b = np.clip(b * np.clip(gray_mean / (means[0] + 1e-6), 0.85, 1.15), 0, 1)
            g = np.clip(g * np.clip(gray_mean / (means[1] + 1e-6), 0.85, 1.15), 0, 1)
            r = np.clip(r * np.clip(gray_mean / (means[2] + 1e-6), 0.85, 1.15), 0, 1)
            merged = cv2.merge([b, g, r])
            # Shadow lift (recover detail crushed by harsh contre-jour stage lighting)
            lifted = np.clip(merged + 0.03 * (1.0 - merged), 0, 1)
            # Soft highlight rolloff to tame blown-out spotlight hotspots
            rolled_off = np.where(lifted > 0.85, 0.85 + (lifted - 0.85) * 0.6, lifted)
            # Punchy contrast to keep the dramatic live-show feel
            graded = np.clip(((rolled_off - 0.5) * 1.12 + 0.5), 0, 1)
            return (graded * 255.0).astype(np.uint8)

        elif preset == "family_event":
            # Warm, inviting, authentic - weddings/birthdays/family gatherings. Gentle
            # warmth and a soft highlight lift, deliberately NOT a heavy stylized grade,
            # so skin tones and the room's actual atmosphere stay true to the memory.
            b, g, r = cv2.split(img_float)
            r = np.clip(r * 1.05 + 0.015, 0, 1)
            g = np.clip(g * 1.02 + 0.01, 0, 1)
            b = np.clip(b * 0.97, 0, 1)
            merged = cv2.merge([b, g, r])
            graded = np.clip(merged ** 1.03, 0, 1)
            return (graded * 255.0).astype(np.uint8)

        return img

    @staticmethod
    def _skin_mask(img: np.ndarray) -> np.ndarray:
        """Lightweight non-ML skin-region detector (YCrCb threshold), used to scope the
        skin-targeted retouch passes below (skin tone, mattify/shine, portrait volumes)
        so they act on skin and not on hair, eyes, teeth, fabric, or background. Returns
        a single-channel float32 mask in 0..1, feathered so edits blend smoothly instead
        of showing a hard cutout edge."""
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, (0, 135, 85), (255, 180, 135)).astype(np.float32) / 255.0
        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=6)
        return mask

    def heal_blemishes(self, img: np.ndarray, strength: float = 0.7) -> np.ndarray:
        """Retouch4me "Heal"-equivalent: automatically finds small, high-contrast spot
        blemishes (acne, stray marks, sensor dust) via a local-anomaly test - pixels
        that differ sharply from their median-filtered neighborhood in a small radius -
        then removes only those small regions with OpenCV's Telea inpainting, leaving
        the surrounding skin texture completely untouched. Unlike blanket smoothing,
        this targets just the defects, so it causes essentially no broader image
        degradation."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            median = cv2.medianBlur(gray, 9)
            diff = cv2.absdiff(gray, median)
            thresh_val = max(10, int(28 - strength * 10))
            _, spot_mask = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
            # Only tiny blemish-sized blobs - large edges (jewelry, hair strands, fabric
            # seams) are deliberately excluded so this never eats real detail.
            spot_mask = cv2.morphologyEx(spot_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            spot_mask = cv2.dilate(spot_mask, np.ones((3, 3), np.uint8), iterations=1)
            if cv2.countNonZero(spot_mask) == 0:
                return img
            healed = cv2.inpaint(img, spot_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
            return healed
        except Exception:
            return img

    def correct_skin_tone(self, img: np.ndarray, strength: float = 0.4) -> np.ndarray:
        """Retouch4me "Skin Tone"-equivalent: nudges skin-region color in LAB space
        toward an even, healthy tone (neutralizing blotchy red/yellow patches) without
        touching hue/luminance outside the skin mask - clothing, background, and hair
        color are left completely alone."""
        try:
            mask = self._skin_mask(img)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
            l_ch, a_ch, b_ch = cv2.split(lab)
            skin_a_mean = float(np.average(a_ch, weights=mask + 1e-6))
            skin_b_mean = float(np.average(b_ch, weights=mask + 1e-6))
            # Pull each skin pixel's a/b channel partway toward the skin region's own
            # mean - evens out blotches while preserving the subject's actual tone.
            a_corrected = a_ch + (skin_a_mean - a_ch) * (mask * strength)
            b_corrected = b_ch + (skin_b_mean - b_ch) * (mask * strength)
            lab_corrected = cv2.merge([l_ch, a_corrected, b_corrected])
            result = cv2.cvtColor(np.clip(lab_corrected, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
            return result
        except Exception:
            return img

    def reduce_shine(self, img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """Retouch4me "Mattifier"-equivalent: detects oily/specular highlight hotspots
        on skin (very bright, low-saturation pixels within the skin mask) and locally
        compresses their luminance, instead of a global highlight reduction that would
        flatten contrast everywhere."""
        try:
            skin_mask = self._skin_mask(img)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            h_ch, s_ch, v_ch = cv2.split(hsv)
            shine_mask = np.clip((v_ch / 255.0 - 0.78) * 4.0, 0, 1) * np.clip((1.0 - s_ch / 255.0 - 0.35) * 2.0, 0, 1)
            shine_mask = cv2.GaussianBlur(shine_mask * skin_mask, (0, 0), sigmaX=4)
            v_reduced = v_ch - (v_ch * 0.18 * strength * shine_mask)
            hsv_corrected = cv2.merge([h_ch, s_ch, np.clip(v_reduced, 0, 255)])
            result = cv2.cvtColor(hsv_corrected.astype(np.uint8), cv2.COLOR_HSV2BGR)
            return result
        except Exception:
            return img

    def enhance_portrait_volumes(self, img: np.ndarray, strength: float = 0.4) -> np.ndarray:
        """Retouch4me "Portrait Volumes"-equivalent: subtle luminosity dodge & burn that
        adds dimensional shaping (lifting cheekbones/brow highlights, deepening natural
        hollows) using CLAHE-driven local contrast on the L channel only, so color is
        completely unaffected - a non-destructive sculpting pass, not a filter."""
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_ch, a_ch, b_ch = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.4 + strength * 1.2, tileGridSize=(8, 8))
            l_shaped = clahe.apply(l_ch)
            l_blended = cv2.addWeighted(l_ch, 1.0 - strength, l_shaped, strength, 0)
            result = cv2.cvtColor(cv2.merge([l_blended, a_ch, b_ch]), cv2.COLOR_LAB2BGR)
            return result
        except Exception:
            return img

    def reduce_eye_redness(self, img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """Retouch4me "Eye Vessels"-equivalent (best-effort, non-ML approximation): finds
        small, bright, reddish regions (the kind caused by tired/irritated sclera) and
        desaturates the red channel locally within just those tiny regions, leaving iris
        color, skin tone, and everything else untouched."""
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            h_ch, s_ch, v_ch = cv2.split(hsv)
            # Red hue wraps around 0/180 in OpenCV's HSV - catch both ends
            redness = (((h_ch < 10) | (h_ch > 170)) & (v_ch > 140) & (s_ch > 40) & (s_ch < 160)).astype(np.float32)
            redness = cv2.GaussianBlur(redness, (0, 0), sigmaX=2)
            s_reduced = s_ch - (s_ch * 0.6 * strength * redness)
            hsv_corrected = cv2.merge([h_ch, np.clip(s_reduced, 0, 255), v_ch])
            return cv2.cvtColor(hsv_corrected.astype(np.uint8), cv2.COLOR_HSV2BGR)
        except Exception:
            return img

    def match_color_to_reference(self, img: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Retouch4me "Color Match"-equivalent: Reinhard LAB mean/std color transfer -
        matches this image's overall color/tone statistics to a reference image, so an
        entire shoot (different lighting setups, times of day, or cameras) reads as one
        visually consistent, professionally color-matched batch."""
        try:
            src_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
            ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)
            result_channels = []
            for i in range(3):
                src_ch, ref_ch = src_lab[:, :, i], ref_lab[:, :, i]
                src_mean, src_std = src_ch.mean(), src_ch.std() + 1e-6
                ref_mean, ref_std = ref_ch.mean(), ref_ch.std() + 1e-6
                matched = (src_ch - src_mean) * (ref_std / src_std) + ref_mean
                result_channels.append(np.clip(matched, 0, 255))
            matched_lab = cv2.merge(result_channels).astype(np.uint8)
            return cv2.cvtColor(matched_lab, cv2.COLOR_LAB2BGR)
        except Exception:
            return img

    def export_print_master(self, img: np.ndarray, out_path: Path, dpi: int = 300) -> Optional[Path]:
        """Writes a print-ready 16-bit-per-channel TIFF with an embedded sRGB ICC color
        profile and a real DPI tag, using lossless LZW compression - zero additional
        compression artifacts versus the processed buffer, and the format/metadata a
        professional print lab's RIP software expects. (8-bit source photos don't gain
        new information by widening to 16-bit, but storing the delivery master this way
        avoids the receiving lab's own color conversion introducing a second round of
        8-bit rounding on top of ours.)"""
        try:
            import tifffile
            from PIL import ImageCms
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            # Scale 8-bit (0-255) up to the full 16-bit (0-65535) range
            rgb_16 = (rgb.astype(np.uint16) * 257)
            srgb_profile = ImageCms.createProfile("sRGB")
            icc_bytes = ImageCms.ImageCmsProfile(srgb_profile).tobytes()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # tifffile handles true 16-bit-per-channel RGB TIFFs (Pillow's fromarray only
            # supports 8-bit "RGB" mode), and lets us embed the ICC profile + DPI
            # resolution tag directly in one write - the combination print labs expect.
            tifffile.imwrite(
                str(out_path),
                rgb_16,
                photometric="rgb",
                compression="lzw",
                resolution=(dpi, dpi),
                resolutionunit="inch",
                extratags=[(34675, "B", len(icc_bytes), icc_bytes, True)]  # 34675 = ICC Profile tag
            )
            return out_path
        except Exception as e:
            print(f"[PhotoRetoucher] Print master export failed for {out_path}: {e}")
            return None

    def crop_aspect_ratio(self, img: np.ndarray, ratio_w: int, ratio_h: int) -> np.ndarray:
        """Center crop image to exact aspect ratio (e.g. 4:5 or 9:16)."""
        h, w = img.shape[:2]
        target_aspect = ratio_w / ratio_h
        current_aspect = w / h

        if current_aspect > target_aspect:
            # Too wide, crop sides
            new_w = int(h * target_aspect)
            offset = (w - new_w) // 2
            return img[:, offset:offset + new_w]
        else:
            # Too tall, crop top/bottom with slight bias towards upper half (head room)
            new_h = int(w / target_aspect)
            offset = int((h - new_h) * 0.35) # 35% from top preserves heads
            return img[offset:offset + new_h, :]

    def add_watermark(self, img: np.ndarray, watermark_text: str = "@ExclusiveDrop") -> np.ndarray:
        """Add sleek modern watermark banner on corner."""
        out = img.copy()
        h, w = out.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.5, w / 1600.0)
        thickness = max(1, int(font_scale * 2))

        # Bottom right placement
        text_size = cv2.getTextSize(watermark_text, font, font_scale, thickness)[0]
        tx = w - text_size[0] - 25
        ty = h - 25

        # Subtle dark translucent backing
        cv2.putText(out, watermark_text, (tx+2, ty+2), font, font_scale, (0, 0, 0), thickness+2, cv2.LINE_AA)
        cv2.putText(out, watermark_text, (tx, ty), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        return out

    def process_photo_batch(
        self,
        image_paths: List[Path],
        shoot_name: str = "boudoir_shoot",
        preset: str = "moody_boudoir",
        smooth_strength: float = 0.5,
        watermark_text: str = "@ExclusiveDrop",
        progress_cb: Optional[Callable[[str, int], None]] = None,
        source_batch: Optional[str] = None,
        edit_style: Optional[str] = None,
        print_master: bool = True
    ) -> Dict[str, Any]:
        """Process batch of photos with retouching, crops, and export bundle.

        edit_style: optional named profile from STYLE_PROFILES ("glamour", "natural",
        "concert_stage", "family_event") that selects the color grade, retouch-pass
        settings, and watermark convention all at once. When given, it OVERRIDES the
        individual preset/smooth_strength/watermark_text args below with that profile's
        settings (watermark_text is still honored verbatim if the profile calls for a
        watermark). When omitted, behaves exactly as before - just the raw preset/
        smooth_strength/watermark_text args, for full backward compatibility with
        existing callers.

        print_master: also export a lossless 16-bit TIFF (sRGB ICC + 300 DPI) of every
        processed photo into 05_print_master_16bit/, for print-lab-ready delivery with
        no extra JPEG-compression generation loss.

        source_batch: the isolated client_inbox/batch_.../ folder name these source
        photos came from, if known. Recorded in the package's manifest.json so this
        CLIENT deliverable is unambiguously tagged by its origin and can never be
        mistaken for marketing/postable content or mixed up with a different client's
        package."""
        profile = STYLE_PROFILES.get(edit_style, {}) if edit_style else {}
        active_preset = profile.get("preset", preset)
        active_smooth_strength = profile.get("smooth_strength", smooth_strength)
        apply_watermark = profile.get("watermark", True) if edit_style else True

        pkg_dir = self.output_base / f"{shoot_name}_RETOUCHED_PACKAGE"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        fullres_dir = pkg_dir / "01_master_fullres"
        teasers_dir = pkg_dir / "02_social_teasers"
        crops_4x5_dir = pkg_dir / "03_instagram_4x5"
        crops_9x16_dir = pkg_dir / "04_stories_9x16"
        print_master_dir = pkg_dir / "05_print_master_16bit"

        dirs_to_make = [fullres_dir, teasers_dir, crops_4x5_dir, crops_9x16_dir]
        if print_master:
            dirs_to_make.append(print_master_dir)
        for d in dirs_to_make:
            d.mkdir(parents=True, exist_ok=True)

        processed_photos = []
        total = len(image_paths)

        for idx, img_path in enumerate(image_paths):
            if progress_cb:
                pct = int((idx / max(1, total)) * 80)
                progress_cb(f"Retouching & color grading photo {idx + 1}/{total}...", pct)

            img = cv2.imread(str(img_path))
            if img is None:
                continue

            # 1. Skin smoothing (true frequency separation)
            retouched = self.apply_skin_smoothing(img, strength=active_smooth_strength)

            # 1b. Professional retouch suite passes - only those this edit_style profile
            # calls for (glamour runs the full suite; natural/concert/family run a much
            # lighter subset, or none, to stay true-to-life rather than "polished").
            if profile.get("heal"):
                retouched = self.heal_blemishes(retouched)
            if profile.get("skin_tone"):
                retouched = self.correct_skin_tone(retouched)
            if profile.get("mattify"):
                retouched = self.reduce_shine(retouched)
            if profile.get("portrait_volumes"):
                retouched = self.enhance_portrait_volumes(retouched)
            if profile.get("eye_vessels"):
                retouched = self.reduce_eye_redness(retouched)

            # 2. Color grading
            graded_raw = self.apply_color_grade(retouched, preset=active_preset)
            # 3. Clarity/sharpen finishing pass
            graded = self.apply_clarity_sharpen(graded_raw)

            stem = img_path.stem
            # Save master fullres
            out_master = fullres_dir / f"{stem}_retouched.jpg"
            cv2.imwrite(str(out_master), graded, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            # Save social crops
            crop_4x5 = self.crop_aspect_ratio(graded, 4, 5)
            out_4x5 = crops_4x5_dir / f"{stem}_4x5.jpg"
            cv2.imwrite(str(out_4x5), crop_4x5, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            crop_9x16 = self.crop_aspect_ratio(graded, 9, 16)
            out_9x16 = crops_9x16_dir / f"{stem}_9x16.jpg"
            cv2.imwrite(str(out_9x16), crop_9x16, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            photo_entry = {
                "original": img_path.name,
                "master": str(out_master.relative_to(self.output_base)),
                "crop_4x5": str(out_4x5.relative_to(self.output_base)),
                "crop_9x16": str(out_9x16.relative_to(self.output_base))
            }

            if apply_watermark:
                teaser_img = self.add_watermark(crop_4x5, watermark_text=watermark_text)
                out_teaser = teasers_dir / f"{stem}_teaser_preview.jpg"
                cv2.imwrite(str(out_teaser), teaser_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                photo_entry["teaser"] = str(out_teaser.relative_to(self.output_base))

            if print_master:
                out_print = print_master_dir / f"{stem}_print_master.tiff"
                if self.export_print_master(graded, out_print):
                    photo_entry["print_master"] = str(out_print.relative_to(self.output_base))

            processed_photos.append(photo_entry)

        if not processed_photos:
            # Every input path failed cv2.imread() (e.g. a .zip archive or other
            # non-image file got passed in instead of actual photos) - previously
            # this fell through to "completed" with an empty package, which let a
            # whole client job silently produce a finished-looking but unedited
            # delivery. Fail loudly instead so the caller (and the Commander) knows
            # nothing was actually retouched.
            return {
                "status": "failed",
                "error": f"None of the {total} input file(s) could be read as images "
                         f"(unsupported format, corrupt file, or a .zip/archive was "
                         f"passed in instead of individual photos) - zero photos were retouched.",
                "total_processed": 0,
                "source_batch": source_batch,
                "edit_style": edit_style,
            }

        # Compress bundle into ZIP
        if progress_cb:
            progress_cb("Compressing retouched photo bundle into ZIP...", 90)

        # Tag this package unambiguously as a CLIENT DELIVERABLE, with its source batch
        # and original filenames recorded, so it's never confused with marketing/postable
        # content or a different client's package - addresses "tag what each character
        # is calling to be made so there's no confusion" directly for client work.
        manifest = {
            "package_type": "CLIENT_DELIVERABLE",
            "shoot_name": shoot_name,
            "preset": active_preset,
            "edit_style": edit_style,
            "source_batch": source_batch,
            "created_at": datetime.datetime.now().isoformat(),
            "source_filenames": [p["original"] for p in processed_photos],
            "warning": "This package contains client-sourced photos. Do not post, repurpose, "
                       "or mix with any other client's files or marketing/brand content."
        }
        with open(pkg_dir / "manifest.json", "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        zip_path = self.output_base / f"{shoot_name}_PHOTO_PACKAGE.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(pkg_dir)
                    zipf.write(file_path, arcname=str(arcname))

        if progress_cb:
            progress_cb("Photo Shoot Retouching Complete!", 100)

        return {
            "status": "completed",
            "package_dir": str(pkg_dir),
            "zip_file": str(zip_path),
            "zip_name": zip_path.name,
            "zip_size_mb": round(zip_path.stat().st_size / (1024**2), 2),
            "total_processed": len(processed_photos),
            "source_batch": source_batch,
            "edit_style": edit_style,
            "photos": processed_photos
        }

if __name__ == "__main__":
    retoucher = PhotoRetoucher()
    print("Photo Retoucher Stage initialized.")
