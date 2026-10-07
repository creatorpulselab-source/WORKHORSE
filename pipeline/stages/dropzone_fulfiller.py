"""
WORKHORSE AUTONOMOUS DROPZONE FULFILLMENT WATCHER (AGENT: VANGUARD & IRIS)
Monitors F:\WORKHORSE\dropzone for incoming client photo batches.
When files or ZIPs are dropped:
  1. Auto-extracts images (JPEG, PNG, RAW).
  2. Runs 32-bit bilateral frequency separation on Dual RTX 3060 GPUs.
  3. Generates 5 signature color grades (Portra, Golden, Moody, Noir, Clean).
  4. Generates 4:5 Instagram Portrait and 9:16 vertical social crops.
  5. Packages the final high-res delivery into a ready-to-upload ZIP.
  6. Generates a 5-star review request delivery note ready to paste into Fiverr.
Zero manual Photoshop. Zero slider tweaking. Hands-off fulfillment.
"""

import os
import sys
import time
import zipfile
import shutil
import cv2
from pathlib import Path
from typing import Dict, Any, List

DROPZONE_DIR = Path(r"F:\WORKHORSE\dropzone")
OUTPUT_DIR = Path(r"F:\WORKHORSE\workspace\fiverr_deliveries")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.photo_retoucher import PhotoRetoucher
from pipeline.stages.fiverr_service_bot import FiverrServiceBot

class DropzoneFulfiller:
    def __init__(self):
        self.retoucher = PhotoRetoucher(output_base=str(OUTPUT_DIR / "temp_retouched"))
        self.bot = FiverrServiceBot(output_base=str(OUTPUT_DIR))

    def process_dropzone(self) -> List[Dict[str, Any]]:
        """Scan dropzone and automatically process all unfulfilled client folders or ZIPs."""
        results = []
        if not DROPZONE_DIR.exists():
            DROPZONE_DIR.mkdir(parents=True, exist_ok=True)
            return results

        items = list(DROPZONE_DIR.iterdir())
        if not items:
            return results

        for item in items:
            if item.name.startswith(".") or item.name.startswith("PROCESSED_"):
                continue

            order_name = item.stem
            print(f"[AUTO-FULFILL] Detected incoming batch: {item.name}")

            # 1. Collect all image files
            temp_input = DROPZONE_DIR / f"_extracting_{order_name}"
            temp_input.mkdir(exist_ok=True)

            if item.is_file() and item.suffix.lower() == ".zip":
                with zipfile.ZipFile(item, "r") as zf:
                    zf.extractall(temp_input)
            elif item.is_dir():
                for f in item.rglob("*"):
                    if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".dng"]:
                        shutil.copy(f, temp_input / f.name)
            elif item.is_file() and item.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".dng"]:
                shutil.copy(item, temp_input / item.name)

            # Find all extracted images
            images = [f for f in temp_input.rglob("*") if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".dng"]]

            if not images:
                print(f"[AUTO-FULFILL] No supported images found in {item.name}")
                shutil.rmtree(temp_input, ignore_errors=True)
                continue

            print(f"[AUTO-FULFILL] Processing {len(images)} photos with Dual-GPU Bilateral Smoothing & Color Grading...")

            order_out_dir = OUTPUT_DIR / f"{order_name}_RETRO_DELIVERY"
            order_out_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if client explicitly asked for cropping in folder name or order notes
            explicitly_requested_crops = any(k in order_name.lower() for k in ["crop", "4x5", "9x16", "instagram_crop", "story_crop"])

            # Subdirectories for clean client delivery - ALWAYS preserve original uncropped framing by default
            (order_out_dir / "01_Master_Retouched_FullRes").mkdir(exist_ok=True)
            (order_out_dir / "02_Color_Grades_FullRes").mkdir(exist_ok=True)

            if explicitly_requested_crops:
                (order_out_dir / "03_Requested_Social_Crops").mkdir(exist_ok=True)

            processed_files = []

            for idx, img_path in enumerate(images):
                img = cv2.imread(str(img_path))
                if img is None:
                    continue

                base_stem = f"photo_{idx+1:02d}_{img_path.stem}"

                # Step A: Bilateral Frequency Separation (Retain Pores, Remove Blemishes - 100% ORIGINAL FRAMING & RESOLUTION)
                smoothed = self.retoucher.apply_skin_smoothing(img, strength=0.55)
                master_path = order_out_dir / "01_Master_Retouched_FullRes" / f"{base_stem}_retouched_full_frame.jpg"
                cv2.imwrite(str(master_path), smoothed, [cv2.IMWRITE_JPEG_QUALITY, 98])
                processed_files.append(str(master_path))

                # Step B: 5 Color Grades (100% ORIGINAL FRAMING & RESOLUTION)
                for grade in ["golden_hour", "moody_boudoir", "vintage_35mm", "cyber_neon", "monochrome_noir"]:
                    graded = self.retoucher.apply_color_grade(smoothed, preset=grade)
                    grade_path = order_out_dir / "02_Color_Grades_FullRes" / f"{base_stem}_{grade}.jpg"
                    cv2.imwrite(str(grade_path), graded, [cv2.IMWRITE_JPEG_QUALITY, 96])
                    processed_files.append(str(grade_path))

                # Step C: Only crop if EXPLICITLY requested by the client
                if explicitly_requested_crops:
                    crop_4_5 = self.retoucher.crop_aspect_ratio(smoothed, 4, 5)
                    crop_4_5_path = order_out_dir / "03_Requested_Social_Crops" / f"{base_stem}_crop_4x5.jpg"
                    cv2.imwrite(str(crop_4_5_path), crop_4_5, [cv2.IMWRITE_JPEG_QUALITY, 98])
                    processed_files.append(str(crop_4_5_path))

                    crop_9_16 = self.retoucher.crop_aspect_ratio(smoothed, 9, 16)
                    crop_9_16_path = order_out_dir / "03_Requested_Social_Crops" / f"{base_stem}_crop_9x16.jpg"
                    cv2.imwrite(str(crop_9_16_path), crop_9_16, [cv2.IMWRITE_JPEG_QUALITY, 98])
                    processed_files.append(str(crop_9_16_path))

            # Step D: Generate Delivery Note
            delivery_note = self.bot.generate_delivery_note("gig_retouch", client_name=order_name)
            (order_out_dir / "DELIVERY_NOTE_AND_INSTRUCTIONS.txt").write_text(delivery_note, encoding="utf-8")

            # Step E: Zip everything into final delivery package
            final_zip = OUTPUT_DIR / f"{order_name}_FINAL_DELIVERY_PACKAGE.zip"
            with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(order_out_dir):
                    for file in files:
                        fp = Path(root) / file
                        zf.write(fp, arcname=str(fp.relative_to(order_out_dir)))

            # Mark item as processed in dropzone
            shutil.rmtree(temp_input, ignore_errors=True)
            if item.is_file():
                item.rename(DROPZONE_DIR / f"PROCESSED_{item.name}")
            elif item.is_dir():
                item.rename(DROPZONE_DIR / f"PROCESSED_{item.name}")

            ready_card = f"""=====================================================
FIVERR ORDER READY FOR 1-CLICK DELIVERY: {order_name}
=====================================================
ZIP FILE TO ATTACH:
{final_zip} ({round(final_zip.stat().st_size / (1024*1024), 2)} MB)

DELIVERY NOTE TO PASTE:
-----------------------------------------------------
{delivery_note}
=====================================================
"""
            ready_card_path = OUTPUT_DIR / f"{order_name}_READY_TO_DELIVER.txt"
            ready_card_path.write_text(ready_card, encoding="utf-8")
            print(f"[AUTO-FULFILL] SUCCESS! Delivery package created: {final_zip.name}")
            print(f"[AUTO-FULFILL] Note saved to: {ready_card_path.name}")

            results.append({
                "order_name": order_name,
                "photos_processed": len(images),
                "total_deliverables": len(processed_files),
                "zip_path": str(final_zip),
                "zip_size_mb": round(final_zip.stat().st_size / (1024*1024), 2),
                "ready_text_file": str(ready_card_path)
            })

        return results

if __name__ == "__main__":
    fulfiller = DropzoneFulfiller()
    res = fulfiller.process_dropzone()
    print("Dropzone scan complete. Processed batches:", len(res))
