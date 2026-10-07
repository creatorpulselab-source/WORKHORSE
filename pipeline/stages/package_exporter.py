import os
import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

class PackageExporter:
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/output"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

    def export_bundle(
        self,
        video_name: str,
        pose_files: List[Path],
        preview_video: Optional[Path],
        social_crops: Dict[str, Path],
        audio_data: Dict[str, Any],
        vision_data: Dict[str, Any],
        copy_kit: Dict[str, Any],
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Bundle all generated assets into a structured release directory and zip package."""
        stem = Path(video_name).stem
        pkg_dir = self.output_base / f"{stem}_PROMO_PACKAGE"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        if progress_cb:
            progress_cb("Apex Agent: Organizing bundle deliverables...", 20)

        # 1. Poses folder
        poses_folder = pkg_dir / "01_pose_screenshots"
        poses_folder.mkdir(parents=True, exist_ok=True)
        rel_poses = []
        for p in pose_files:
            if p.exists():
                dest = poses_folder / p.name
                shutil.copy2(p, dest)
                rel_poses.append(str(dest.relative_to(self.output_base)))

        # 2. Previews folder
        previews_folder = pkg_dir / "02_video_previews"
        previews_folder.mkdir(parents=True, exist_ok=True)
        rel_previews = {}
        if preview_video and preview_video.exists():
            dest = previews_folder / preview_video.name
            shutil.copy2(preview_video, dest)
            rel_previews["preview_60s"] = str(dest.relative_to(self.output_base))

        for crop_name, c_path in social_crops.items():
            if c_path.exists():
                dest = previews_folder / c_path.name
                shutil.copy2(c_path, dest)
                rel_previews[crop_name] = str(dest.relative_to(self.output_base))

        # 3. Audio & Transcript
        audio_folder = pkg_dir / "03_audio_transcript"
        audio_folder.mkdir(parents=True, exist_ok=True)
        transcript_file = audio_folder / "transcript.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(f"=== TRANSCRIPT FOR {video_name} ===\n\n")
            f.write(audio_data.get("full_text", "No speech detected.") + "\n\n")
            f.write("=== EXTRACTED SPOKEN HOOKS ===\n")
            for h in audio_data.get("hooks", []):
                f.write(f"- {h}\n")

        # 4. Copywriting & Marketing Kit
        copy_folder = pkg_dir / "04_marketing_copy"
        copy_folder.mkdir(parents=True, exist_ok=True)
        copy_json_file = copy_folder / "social_copy_kit.json"
        with open(copy_json_file, "w", encoding="utf-8") as f:
            json.dump(copy_kit, f, indent=2)

        # 5. Master Markdown summary
        md_file = pkg_dir / "PROMO_MEDIA_PACKAGE.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# WORKHORSE PROMO MEDIA PACKAGE\n\n")
            f.write(f"**Source Video:** `{video_name}`\n")
            f.write(f"**Generated:** Automatically by WORKHORSE AI Command Center\n\n")
            f.write("## 📸 Pose Screenshots\n")
            f.write(f"Generated {len(rel_poses)} high-res pose screenshots in `01_pose_screenshots/`\n\n")
            f.write("## 🎬 Video Previews\n")
            for k, v in rel_previews.items():
                f.write(f"- **{k}**: `{Path(v).name}`\n")
            f.write("\n## 📱 Platform Copy Release Kit\n\n")
            f.write("### Instagram\n")
            ig = copy_kit.get("instagram", {})
            f.write(f"{ig.get('caption', '')}\n\n")
            f.write(" ".join(ig.get("hashtags", [])) + "\n\n")
            f.write("### Twitter / X\n")
            tw = copy_kit.get("twitter_x", {})
            f.write(f"{tw.get('tweet', '')}\n\n")
            f.write(f"{tw.get('reply_cta', '')}\n\n")
            f.write("### OnlyFans / Fansly\n")
            of = copy_kit.get("onlyfans_fansly", {})
            f.write(f"{of.get('teaser_post', '')}\n\n")
            f.write(f"Suggested PPV Price: **{of.get('suggested_ppv_price', '$15')}**\n\n")
            f.write("### TikTok / Reels\n")
            tk = copy_kit.get("tiktok_reels", {})
            f.write(f"{tk.get('caption', '')}\n")
            f.write(f"Sound suggestion: *{tk.get('trending_sound_suggestion', '')}*\n\n")
            f.write("### Fiverr Delivery Note\n")
            f.write(f"{copy_kit.get('fiverr_delivery_note', '')}\n")

        # 6. Build ZIP bundle
        if progress_cb:
            progress_cb("Apex Agent: Compressing into release ZIP package...", 80)

        zip_path = self.output_base / f"{stem}_PROMO_PACKAGE.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(pkg_dir)
                    zipf.write(file_path, arcname=str(arcname))

        if progress_cb:
            progress_cb("Apex Agent: Release package finalized!", 100)

        return {
            "package_dir": str(pkg_dir),
            "zip_file": str(zip_path),
            "zip_name": zip_path.name,
            "zip_size_mb": round(zip_path.stat().st_size / (1024**2), 2),
            "poses": rel_poses,
            "previews": rel_previews
        }

if __name__ == "__main__":
    exporter = PackageExporter()
    print("Package Exporter (Apex) initialized.")
