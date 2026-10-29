"""
WORKHORSE ManyVids Vault Ingestion Pipeline
Streams Charlette Webb's legacy 700+ ManyVids catalog directly into Bunny.net Edge Storage.
Author: Antigravity / WORKHORSE Pipeline
"""

import os
import sys
import json
import time
import glob
import logging
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_secrets() -> Dict[str, Any]:
    """Resolves secrets.json across Windows WORKHORSE root and Linux VPS paths."""
    candidates = [
        Path("F:/WORKHORSE/secrets.json"),
        Path(__file__).resolve().parents[2] / "secrets.json",
        Path("/opt/charlette-daemon/secrets.json")
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("manyvids_vault_sync")


def find_latest_vault_manifest() -> Optional[str]:
    """Scans User Downloads and workspace for the exported ManyVids catalog JSON."""
    user_home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    downloads_dir = os.path.join(user_home, "Downloads")
    patterns = [
        os.path.join(downloads_dir, "*manyvids*.json"),
        os.path.join(downloads_dir, "*charlette*.json"),
        os.path.join(downloads_dir, "*vault*.json"),
        os.path.join("F:\\WORKHORSE", "*manyvids*.json")
    ]
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(pat))
    if not candidates:
        return None
    # Sort by modification time descending
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


async def stream_video_to_bunny(
    client: httpx.AsyncClient,
    video_title: str,
    source_url: str,
    bunny_upload_url: str,
    bunny_headers: Dict[str, str]
) -> bool:
    """Streams video chunks directly from source CDN to Bunny.net storage without large RAM allocation."""
    try:
        async with client.stream("GET", source_url, timeout=300.0) as source_resp:
            if source_resp.status_code != 200:
                logger.error(f"Failed to fetch source video '{video_title}': HTTP {source_resp.status_code}")
                return False
            
            # Use streaming upload to Bunny Storage with explicit Content-Length
            req_headers = dict(bunny_headers)
            content_len = source_resp.headers.get("content-length")
            if content_len:
                req_headers["Content-Length"] = str(content_len)

            upload_resp = await client.put(
                bunny_upload_url,
                headers=req_headers,
                content=source_resp.aiter_bytes(),
                timeout=600.0
            )
            if upload_resp.status_code in (200, 201):
                logger.info(f"✅ Successfully ingested '{video_title}' to Bunny Storage.")
                return True
            else:
                logger.error(f"Failed to upload '{video_title}' to Bunny: HTTP {upload_resp.status_code} - {upload_resp.text}")
                return False
    except Exception as e:
        logger.error(f"Exception while streaming '{video_title}': {e}")
        return False


async def ingest_catalog(manifest_path: str, max_concurrent: int = 3, max_videos: Optional[int] = None):
    """Parses manifest and uploads videos to Bunny.net under /workhorse-vault/charlette_webb/legacy_vault/"""
    sec = get_secrets()
    vault_cfg = sec.get("creator_vault", {})
    storage_pwd = vault_cfg.get("bunny_storage_password", "")
    zone = vault_cfg.get("bunny_storage_zone", "workhorse-vault")
    endpoint = vault_cfg.get("bunny_storage_endpoint", "https://ny.storage.bunnycdn.com").rstrip("/")
    cdn_host = vault_cfg.get("bunny_cdn_host", "charlette-vault.b-cdn.net")

    if not storage_pwd:
        logger.error("bunny_storage_password not configured in secrets.json!")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} videos from manifest: {manifest_path}")

    # Prepare download list
    queue = []
    for item in catalog:
        vid_id = item.get("id")
        title = item.get("title", f"video_{vid_id}")
        dl_info = item.get("download") or {}
        orig = dl_info.get("original") or {}
        trans = dl_info.get("transcoded") or {}
        
        # Prioritize transcoded MP4 for instant web streaming and 50% storage footprint
        file_url = trans.get("file_url") or orig.get("file_url")
        file_ext = trans.get("file_ext") or orig.get("file_ext") or "mp4"
        file_size = trans.get("file_size") or orig.get("file_size") or "unknown"
        
        if not file_url:
            continue
            
        # Clean title for filesystem/CDN path
        clean_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title).strip()
        filename = f"{vid_id}_{clean_title[:60]}.{file_ext}"
        bunny_upload_url = f"{endpoint}/{zone}/charlette_webb/legacy_vault/{filename}"
        bunny_cdn_url = f"https://{cdn_host}/charlette_webb/legacy_vault/{filename}"

        queue.append({
            "id": vid_id,
            "title": title,
            "filename": filename,
            "source_url": file_url,
            "bunny_upload_url": bunny_upload_url,
            "bunny_cdn_url": bunny_cdn_url,
            "size": file_size
        })

    if max_videos:
        queue = queue[:max_videos]

    logger.info(f"Ready to ingest {len(queue)} videos to Bunny Storage zone '{zone}'...")
    bunny_headers = {"AccessKey": storage_pwd, "Content-Type": "application/octet-stream"}

    sem = asyncio.Semaphore(max_concurrent)
    results = []

    async with httpx.AsyncClient() as client:
        async def worker(item):
            async with sem:
                success = await stream_video_to_bunny(
                    client=client,
                    video_title=item["title"],
                    source_url=item["source_url"],
                    bunny_upload_url=item["bunny_upload_url"],
                    bunny_headers=bunny_headers
                )
                results.append({**item, "synced": success})

        tasks = [worker(item) for item in queue]
        await asyncio.gather(*tasks)

    # Save synced manifest
    output_manifest = os.path.splitext(manifest_path)[0] + "_synced_bunny.json"
    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    success_count = sum(1 for r in results if r.get("synced"))
    logger.info(f"🎉 Ingestion Complete! Synced {success_count}/{len(results)} videos to Bunny.net.")
    logger.info(f"Master CDN Manifest saved to: {output_manifest}")


if __name__ == "__main__":
    manifest = find_latest_vault_manifest()
    if not manifest:
        print("No manifest found yet in Downloads or WORKHORSE directory.")
        print("Please run the browser console harvester script on ManyVids first.")
    else:
        print(f"Found manifest: {manifest}")
        asyncio.run(ingest_catalog(manifest))
