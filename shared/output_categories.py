"""
Single source of truth for WORKHORSE's generated-output directories, shared
between dashboard/server.py (the gallery/download endpoints) and ai_operator.py
(which tags each tool result with a media entry pointing at these same
categories). Kept in one place so the two can never drift out of sync.

Deliberately NOT served via the public /static/ mount (which has zero auth) -
output can include adult-brand content and client-specific deliverables, so
every file read goes through dashboard/server.py's authenticated
/api/outputs/file endpoint instead.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse

BASE_DIR = Path("F:/WORKHORSE")

OUTPUT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "marketing_images": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_renders",
        "media_type": "image", "label": "🎨 Marketing Image", "recursive": False
    },
    "marketing_videos": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders",
        "media_type": "video", "label": "🎥 Marketing Video", "recursive": False
    },
    "marketing_3d_models": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_3d_pbr_renders",
        "media_type": "model_3d", "label": "🧊 3D Model", "recursive": False
    },
    "banners": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "banners",
        "media_type": "image", "label": "🪧 Banner", "recursive": False
    },
    "client_character_renders": {
        "dir": BASE_DIR / "workspace" / "client_character_renders",
        "media_type": "image", "label": "🎭 Client Character Test", "recursive": True
    },
    "client_photo_packages": {
        "dir": BASE_DIR / "workspace" / "photos_output",
        "media_type": "archive", "label": "📦 Client Retouch Package", "recursive": False,
        "extensions": (".zip",)
    },
    "client_deliveries": {
        "dir": BASE_DIR / "workspace" / "client_deliveries",
        "media_type": "archive", "label": "📦 Client Delivery", "recursive": False,
        "extensions": (".zip",)
    },
}

DEFAULT_MEDIA_EXTENSIONS = {
    "image": (".png", ".jpg", ".jpeg", ".webp"),
    "video": (".mp4", ".mov", ".webm"),
    "model_3d": (".glb", ".gltf"),
    "archive": (".zip",)
}


def build_download_url(category: str, abs_path: Path) -> Optional[str]:
    """Builds the authenticated download URL for a file, given which output
    category it belongs to. Returns None if the file isn't actually inside that
    category's registered directory (so a caller can never accidentally tag a
    file under the wrong category's download link)."""
    cat = OUTPUT_CATEGORIES.get(category)
    if not cat:
        return None
    try:
        rel_path = Path(abs_path).resolve().relative_to(cat["dir"].resolve())
    except ValueError:
        return None
    return f"/api/outputs/file?category={urllib.parse.quote(category)}&path={urllib.parse.quote(str(rel_path))}"


def categorize_path(abs_path: Path) -> Optional[str]:
    """Auto-detects which output category a given absolute file path belongs to,
    by checking which registered directory contains it. Returns None if the path
    isn't under any known output directory."""
    resolved = Path(abs_path).resolve()
    for cat_key, cat in OUTPUT_CATEGORIES.items():
        try:
            resolved.relative_to(cat["dir"].resolve())
            return cat_key
        except ValueError:
            continue
    return None


def build_media_entry(abs_path: Path, title: str = "") -> Optional[Dict[str, Any]]:
    """Convenience: auto-detects the category for a file and builds a complete
    media entry dict ({type, url, filename, title}) ready to attach to a Synapse
    tool result, or None if the path isn't under any known output directory."""
    category = categorize_path(abs_path)
    if not category:
        return None
    url = build_download_url(category, abs_path)
    if not url:
        return None
    cat = OUTPUT_CATEGORIES[category]
    return {
        "type": cat["media_type"],
        "url": url,
        "filename": Path(abs_path).name,
        "title": title or Path(abs_path).name,
        "category_label": cat["label"]
    }
