"""
Single source of truth for WORKHORSE's generated-output directories, shared
between dashboard/server.py (the gallery/download endpoints) and ai_operator.py
(which tags each tool result with a media entry pointing at these same
categories). Kept in one place so the two can never drift out of sync.

Deliberately NOT served via the public /static/ mount (which has zero auth) -
output can include adult-brand content and client-specific deliverables, so
every file read goes through dashboard/server.py's authenticated
/api/outputs/file endpoint instead.

Every category is tagged with a "group" - one of the Commander's 4 real business
lines - so the "Completed Work" gallery can show them as fully separate sections
instead of one mixed pile:
  - "fiverr":  automated gig-order fulfillment (pipeline/stages/fiverr_service_bot.py
               via dropzone_fulfiller.py) - workspace/fiverr_deliveries
  - "etsy":    digital product store bundles (pipeline/stages/etsy_digital_store.py)
               - workspace/etsy_bundles
  - "social":  Herald's scheduled Twitter/Pinterest post visuals - these already land
               in their own per-brand folders (brand_target), genuinely separate from
               ad-hoc Synapse chat renders, not just re-labeled copies of the same files
  - "synapse": everything requested directly in chat or via a manual dashboard bay
               (image/video/3D generation, retouching, banners, tip menus, client
               character tests, manual delivery packaging) - i.e. anything NOT
               produced by an automated Fiverr/Etsy/social pipeline
"""
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse
from shared.output_preview import preview_format

BASE_DIR = Path("F:/WORKHORSE")

OUTPUT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    # --- SYNAPSE: ad-hoc chat/bay-requested generations ---
    "marketing_images": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_renders",
        "media_type": "image", "label": "🎨 Synapse Image", "recursive": False,
        "group": "synapse",
        # CPL_/CML_-prefixed files here are mirrored copies of a brand-targeted social
        # render (see comfyui_bridge.generate_and_audit's brand_target mirroring) - the
        # canonical copy already lives under the "social" group's own brand folder, so
        # excluding these prevents the same image showing up twice under two groups.
        "exclude_prefixes": ("CPL_", "CML_")
    },
    "marketing_videos": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders",
        "media_type": "video", "label": "🎥 Synapse Video", "recursive": False,
        "group": "synapse"
    },
    "marketing_3d_models": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_3d_pbr_renders",
        "media_type": "model_3d", "label": "🧊 3D Model", "recursive": False,
        "group": "synapse"
    },
    "banners": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "banners",
        "media_type": "image", "label": "🪧 Banner", "recursive": False,
        "group": "synapse"
    },
    "cam_templates": {
        "dir": BASE_DIR / "workspace" / "cam_templates",
        "media_type": "archive", "label": "🛍️ Tip Menu / Bio Kit", "recursive": False,
        "extensions": (".zip",), "group": "synapse"
    },
    "client_character_renders": {
        "dir": BASE_DIR / "workspace" / "client_character_renders",
        "media_type": "image", "label": "🎭 Client Character Test", "recursive": True,
        "group": "synapse"
    },
    "client_photo_packages": {
        "dir": BASE_DIR / "workspace" / "photos_output",
        "media_type": "archive", "label": "📦 Client Retouch Package", "recursive": False,
        "extensions": (".zip",), "group": "synapse"
    },
    "client_deliveries": {
        "dir": BASE_DIR / "workspace" / "client_deliveries",
        "media_type": "archive", "label": "📦 Client Delivery", "recursive": False,
        "extensions": (".zip",), "group": "synapse"
    },

    # --- SOCIAL MEDIA: Herald's scheduled Twitter/Pinterest post visuals ---
    "social_images_mainstream": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "creator_media_lab",
        "media_type": "image", "label": "📱 Social Post (Main Brand)", "recursive": False,
        "group": "social"
    },
    "social_images_pulse": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "creator_pulse_lab",
        "media_type": "image", "label": "📱 Social Post (Pulse/Adult)", "recursive": False,
        "group": "social"
    },
    "social_videos_mainstream": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders" / "creator_media_lab",
        "media_type": "video", "label": "📱 Social Video (Main Brand)", "recursive": False,
        "group": "social"
    },
    "social_videos_pulse": {
        "dir": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders" / "creator_pulse_lab",
        "media_type": "video", "label": "📱 Social Video (Pulse/Adult)", "recursive": False,
        "group": "social"
    },

    # --- FIVERR: automated gig-order fulfillment ---
    "fiverr_deliveries": {
        "dir": BASE_DIR / "workspace" / "fiverr_deliveries",
        "media_type": "archive", "label": "💼 Fiverr Order Delivery", "recursive": False,
        "extensions": (".zip",), "group": "fiverr"
    },

    # --- ETSY: digital product store bundles ---
    "etsy_bundles": {
        "dir": BASE_DIR / "workspace" / "etsy_bundles",
        "media_type": "archive", "label": "🛒 Etsy Product Bundle", "recursive": False,
        "extensions": (".zip",), "group": "etsy"
    },
}

GROUP_LABELS = {
    "fiverr": "💼 Fiverr",
    "etsy": "🛒 Etsy",
    "social": "📱 Social Media",
    "synapse": "🤖 Synapse",
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
    """Auto-detects which output category a given absolute file path belongs to.

    Several categories now intentionally nest under each other's parent directory
    (e.g. comfy_video_renders/creator_pulse_lab/ sits inside comfy_video_renders/
    itself) so that a dedicated per-brand social-video folder can live right next to
    the general-purpose Synapse video folder. To resolve that unambiguously:
      - Categories are checked most-specific-(deepest)-directory first.
      - A non-recursive category only matches files that live DIRECTLY inside its
        directory (not in a subfolder another, more specific category already owns).
      - A recursive category matches anything anywhere underneath it.
    Returns None if the path isn't under any known output directory, or if it matches
    a category's own exclude_prefixes (a mirrored copy that's canonically owned by a
    different category/group).
    """
    resolved = Path(abs_path).resolve()
    filename = resolved.name
    candidates = sorted(
        OUTPUT_CATEGORIES.items(),
        key=lambda kv: len(kv[1]["dir"].resolve().parts),
        reverse=True
    )
    for cat_key, cat in candidates:
        cat_dir = cat["dir"].resolve()
        if cat.get("recursive"):
            try:
                resolved.relative_to(cat_dir)
            except ValueError:
                continue
        else:
            if resolved.parent != cat_dir:
                continue
        exclude_prefixes = cat.get("exclude_prefixes")
        if exclude_prefixes and filename.startswith(tuple(exclude_prefixes)):
            continue
        return cat_key
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
        "download_url": url,
        "preview_url": url.replace("/api/outputs/file?", "/api/outputs/preview?", 1),
        "preview_type": "archive" if Path(abs_path).suffix.lower() == ".zip" else (
            preview_format(Path(abs_path).name) or (None, None)
        )[0],
        "filename": Path(abs_path).name,
        "title": title or Path(abs_path).name,
        "category_label": cat["label"],
        "group": cat["group"]
    }
