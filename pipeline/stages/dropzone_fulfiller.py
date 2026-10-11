r"""
WORKHORSE AUTONOMOUS DROPZONE FULFILLMENT WATCHER (AGENT: VANGUARD & IRIS)
Monitors F:\WORKHORSE\dropzone for incoming client photo batches.
When files or ZIPs are dropped:
  1. Auto-extracts images (JPEG, PNG, RAW container formats are accepted by extension,
     though RAW decoding depends entirely on what the installed OpenCV build supports -
     unsupported files are skipped, not silently miscounted as processed).
  2. Runs CPU-based bilateral frequency separation (the same OpenCV engine
     pipeline/stages/photo_retoucher.py uses elsewhere in WORKHORSE - this does not
     use CUDA/GPU acceleration and is not Dual-RTX-3060-specific, despite this
     module's prior docstring/log messages claiming otherwise).
  3. Generates 5 signature color grades (Golden Hour, Moody Boudoir, Vintage 35mm,
     Cyber Neon, Monochrome Noir) - deliberately a different, Fiverr-gig-specific
     "5 looks to choose from" behavior rather than photo_retoucher.py's single-preset
     process_photo_batch() flow, so this module intentionally does not just delegate
     to it.
  4. Generates 4:5 Instagram Portrait and 9:16 vertical social crops ONLY when the
     dropped folder/file name explicitly requests them.
  5. Packages the final high-res delivery into a ready-to-upload
     {order_name}_DELIVERY_PACKAGE.zip - matching the exact naming
     /api/download/fiverr/{order_number} expects (a prior "_FINAL_DELIVERY_PACKAGE"
     name silently did not match that route).
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

# An item must not have been modified for at least this long before being treated as a
# complete drop - without this, a ZIP/folder still being copied in (e.g. from a slow
# network share or USB drive) could be opened mid-write and processed as corrupt/
# incomplete. Skipped items are simply retried on the next scan.
STABILITY_SECONDS = 10
# Prefixes that mean "not a new incoming order" - PROCESSED_ marks completed items,
# and _extracting_ is this module's OWN temp-extraction working directory. Previously
# only PROCESSED_ was excluded, so a leftover _extracting_<name>/ directory from a
# crash mid-run would be picked up again on the next scan as if it were a brand-new
# client order (with a mangled "_extracting_<name>" order name).
SKIP_PREFIXES = (".", "PROCESSED_", "_extracting_")
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".dng"]

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.photo_retoucher import PhotoRetoucher
from pipeline.stages.fiverr_service_bot import FiverrServiceBot

class DropzoneFulfiller:
    def __init__(self):
        self.retoucher = PhotoRetoucher(output_base=str(OUTPUT_DIR / "temp_retouched"))
        self.bot = FiverrServiceBot(output_base=str(OUTPUT_DIR))

    def _copy_image_flattened(self, source: Path, dest_dir: Path) -> Path:
        """Copies one source image into dest_dir, renaming on a filename collision
        instead of silently overwriting (and thereby losing) an earlier photo that
        happened to share the same filename from a different subfolder."""
        dest = dest_dir / source.name
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        shutil.copy(source, dest)
        return dest

    def process_dropzone(self) -> List[Dict[str, Any]]:
        """Scan dropzone and automatically process all unfulfilled client folders or zips.

        Each item is handled independently (its own try/except) so one corrupt/failing
        drop can never block or crash processing of the others in the same scan - it
        is simply reported as failed and left in place (not renamed PROCESSED_) so it
        can be inspected or retried."""
        results = []
        if not DROPZONE_DIR.exists():
            DROPZONE_DIR.mkdir(parents=True, exist_ok=True)
            return results

        items = list(DROPZONE_DIR.iterdir())
        if not items:
            return results

        for item in items:
            if item.name.startswith(SKIP_PREFIXES):
                continue

            # File-stability check: skip anything still being written/copied in (its
            # mtime is too recent) - it will simply be picked up again on a later
            # scan once it stops changing, rather than being opened mid-write and
            # processed as corrupt/incomplete.
            try:
                newest_mtime = item.stat().st_mtime
                if item.is_dir():
                    child_mtimes = [f.stat().st_mtime for f in item.rglob("*") if f.is_file()]
                    if child_mtimes:
                        newest_mtime = max(newest_mtime, max(child_mtimes))
                if time.time() - newest_mtime < STABILITY_SECONDS:
                    print(f"[AUTO-FULFILL] Skipping '{item.name}' this cycle - still changing (not yet stable).")
                    continue
            except Exception:
                continue  # item disappeared mid-check (e.g. still being moved) - retry next cycle

            order_name = item.stem
            print(f"[AUTO-FULFILL] Detected incoming batch: {item.name}")

            # 1. Collect all image files
            temp_input = DROPZONE_DIR / f"_extracting_{order_name}"
            temp_input.mkdir(exist_ok=True)

            try:
                if item.is_file() and item.suffix.lower() == ".zip":
                    with zipfile.ZipFile(item, "r") as zf:
                        zf.extractall(temp_input)
                elif item.is_dir():
                    for f in item.rglob("*"):
                        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                            self._copy_image_flattened(f, temp_input)
                elif item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
                    self._copy_image_flattened(item, temp_input)

                # Find all extracted images
                images = [f for f in temp_input.rglob("*") if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]

                if not images:
                    print(f"[AUTO-FULFILL] No supported images found in {item.name}")
                    shutil.rmtree(temp_input, ignore_errors=True)
                    results.append({"order_name": order_name, "status": "skipped", "reason": "no_supported_images_found"})
                    continue

                print(f"[AUTO-FULFILL] Processing {len(images)} photos with CPU bilateral smoothing & color grading...")

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
                photos_actually_processed = 0
                unreadable_files = []

                for idx, img_path in enumerate(images):
                    img = cv2.imread(str(img_path))
                    if img is None:
                        # Unsupported/corrupt file (e.g. a RAW variant this OpenCV build
                        # can't decode) - must not be silently counted as "processed".
                        unreadable_files.append(img_path.name)
                        continue
                    photos_actually_processed += 1

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

                if photos_actually_processed == 0:
                    # Every discovered "image" failed to decode - previously this still
                    # built and delivered an empty ZIP as if the job had succeeded.
                    shutil.rmtree(temp_input, ignore_errors=True)
                    shutil.rmtree(order_out_dir, ignore_errors=True)
                    print(f"[AUTO-FULFILL] FAILED: none of the {len(images)} file(s) in {item.name} could be decoded as images: {unreadable_files}")
                    results.append({
                        "order_name": order_name, "status": "failed",
                        "error": f"None of {len(images)} file(s) could be read as images: {unreadable_files}",
                    })
                    continue

                # Step D: Generate Delivery Note
                delivery_note = self.bot.generate_delivery_note("gig_retouch", client_name=order_name)
                (order_out_dir / "DELIVERY_NOTE_AND_INSTRUCTIONS.txt").write_text(delivery_note, encoding="utf-8")

                # Step E: Zip everything into final delivery package - named to match
                # exactly what /api/download/fiverr/{order_number} expects
                # ("{order_number}_DELIVERY_PACKAGE.zip"); a prior "_FINAL_DELIVERY_PACKAGE"
                # name silently didn't match that route at all.
                final_zip = OUTPUT_DIR / f"{order_name}_DELIVERY_PACKAGE.zip"
                with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(order_out_dir):
                        for file in files:
                            fp = Path(root) / file
                            zf.write(fp, arcname=str(fp.relative_to(order_out_dir)))

                # Mark item as processed in dropzone - only ever reached on success, so
                # a failed item is left in place (not renamed) for retry/inspection.
                shutil.rmtree(temp_input, ignore_errors=True)
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
                    "status": "completed",
                    "photos_processed": photos_actually_processed,
                    "photos_skipped_unreadable": unreadable_files,
                    "total_deliverables": len(processed_files),
                    "zip_path": str(final_zip),
                    "zip_size_mb": round(final_zip.stat().st_size / (1024*1024), 2),
                    "ready_text_file": str(ready_card_path)
                })
            except Exception as e:
                # One bad drop (corrupt zip, permission error, mid-processing failure)
                # must never crash the whole scan or block the other items in it. The
                # failing item is left in place (not renamed PROCESSED_) so it can be
                # retried once fixed, or inspected manually.
                shutil.rmtree(temp_input, ignore_errors=True)
                print(f"[AUTO-FULFILL] FAILED processing '{item.name}': {e}")
                results.append({"order_name": order_name, "status": "failed", "error": str(e)})
                continue

        return results

if __name__ == "__main__":
    fulfiller = DropzoneFulfiller()
    res = fulfiller.process_dropzone()
    print("Dropzone scan complete. Processed batches:", len(res))
