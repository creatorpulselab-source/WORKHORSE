import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import zipfile

class PhotoRetoucher:
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/photos_output"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

    def apply_skin_smoothing(self, img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """True frequency separation retouch: splits the image into a low-frequency
        (tone/blemish) layer and a high-frequency (pore/texture/hair) layer, smooths
        only the low layer, then recombines - avoids the waxy/plastic look of a
        simple blurred blend while still removing blemishes and uneven skin tone."""
        try:
            img_f = img.astype(np.float32)

            # Low frequency: heavy gaussian blur captures tone/blemishes, not fine detail
            low_freq = cv2.GaussianBlur(img_f, (0, 0), sigmaX=8)
            # High frequency: original minus low = pores, hair, fine texture detail
            high_freq = img_f - low_freq

            # Smooth blemishes/tone in the low layer only (edge-aware, preserves contours)
            low_smoothed = cv2.bilateralFilter(low_freq.astype(np.uint8), d=15, sigmaColor=60, sigmaSpace=60).astype(np.float32)

            # Recombine: smoothed tone + original fine detail, blended by strength
            recombined = np.clip(low_smoothed + high_freq, 0, 255)
            result = cv2.addWeighted(img_f, 1.0 - strength, recombined, strength, 0)
            return np.clip(result, 0, 255).astype(np.uint8)
        except Exception:
            return img

    def apply_clarity_sharpen(self, img: np.ndarray, amount: float = 0.35) -> np.ndarray:
        """Unsharp-mask clarity pass: restores crisp detail (eyes, hair, fabric) lost to
        skin smoothing, the finishing step professional retouchers apply before export."""
        try:
            blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
            sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
            return sharpened
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

        return img

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
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Process batch of photos with retouching, crops, and export bundle."""
        pkg_dir = self.output_base / f"{shoot_name}_RETOUCHED_PACKAGE"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        fullres_dir = pkg_dir / "01_master_fullres"
        teasers_dir = pkg_dir / "02_social_teasers"
        crops_4x5_dir = pkg_dir / "03_instagram_4x5"
        crops_9x16_dir = pkg_dir / "04_stories_9x16"

        for d in [fullres_dir, teasers_dir, crops_4x5_dir, crops_9x16_dir]:
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
            retouched = self.apply_skin_smoothing(img, strength=smooth_strength)
            # 2. Color grading
            graded_raw = self.apply_color_grade(retouched, preset=preset)
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

            # Save watermarked teaser
            teaser_img = self.add_watermark(crop_4x5, watermark_text=watermark_text)
            out_teaser = teasers_dir / f"{stem}_teaser_preview.jpg"
            cv2.imwrite(str(out_teaser), teaser_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

            processed_photos.append({
                "original": img_path.name,
                "master": str(out_master.relative_to(self.output_base)),
                "teaser": str(out_teaser.relative_to(self.output_base)),
                "crop_4x5": str(out_4x5.relative_to(self.output_base)),
                "crop_9x16": str(out_9x16.relative_to(self.output_base))
            })

        # Compress bundle into ZIP
        if progress_cb:
            progress_cb("Compressing retouched photo bundle into ZIP...", 90)

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
            "photos": processed_photos
        }

if __name__ == "__main__":
    retoucher = PhotoRetoucher()
    print("Photo Retoucher Stage initialized.")
