"""
WORKHORSE Cloud Vault Ingestion Engine (Kamatera VPS Edition - High-Performance cURL)
Streams Charlette Webb's 747 ManyVids videos, generates 3 stills + 15s teaser,
and uploads full video + teasers directly to Bunny.net Edge Storage.
"""

import os
import sys
import json
import time
import subprocess
import shutil
from pathlib import Path
import urllib.request
import urllib.error

SECRETS_FILE = Path("/opt/charlette-daemon/secrets.json")
CATALOG_FILE = Path("/opt/charlette-daemon/manyvids_charlette_vault_747_videos.json")
PROGRESS_FILE = Path("/opt/charlette-daemon/synced_vault_progress.json")
LOG_FILE = Path("/opt/charlette-daemon/vault_sync.log")
TEMP_DIR = Path("/tmp/vault_worker")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

MANYVIDS_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://www.manyvids.com",
    "referer": "https://www.manyvids.com/",
    "sec-ch-ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Cookie": (
        "_ga=GA1.1.1847604545.1769012677; "
        "XSRF-TOKEN=eyJpdiI6IndiSW5YRFJFUDliUWlzQU9qTldBQkE9PSIsInZhbHVlIjoiQkROeWZHblJRVHZFU0pnemppdG9YSFJKMlJ2WWtoNEY3RFhBdzl5WVhuMG9LMmg4OStHUVg1SkJZQ2d3WFRtYyIsIm1hYyI6ImRjMjFiYTYwYWQ4MzIwYzcyMjFlOTYzMGUzZThkNjhhZjJiZDMzN2E2YzNlN2VkNDg1Yjk3MjEwZjlkN2E3OTQifQ%3D%3D; "
        "_ga_HCX6BHQYHQ=GS2.1.s1785278013$o2$g1$t1785279505$j60$l0$h0$d8IcKqilO6JL5VRLbCoRck87zsYEKWA0m6g; "
        "PHPSESSID=CC65ead5649328e7b46111dc2850e8a5de8a324f; "
        "API_KEY=y14vTv8rHVXR5vO95YUPzpSWMQxaqnckJu9Q3TikKxhJThPvZZkULhEMJRebB1a7; "
        "MSG_LEG_TKN=t1Ui7k0%2BE2ISxTxbJdyuqA%3D%3D; "
        "aws-waf-token=e437eb27-ded6-4bbc-b206-d140e70aa018:EQoAi7eTkkoHMwAA:iwYh2D92ejcrFMqcOZ65EdpHsKKN6qKhez0AfB/GKTLRxZvIwAh6zl/AlBzFhHgLLlX1bYA6IkWUutaTckDY26EhvQoIixvsOT3eUZ8GBZ0jQA8511zbeRLEQBPB+q7pAsSCGiJQ7/j3dV7DmCVUnYRYFyjP/xU5sAWHy/9szj22kM5Fdo2zisP9KzcdEHNN/SgHQfKB7de81Iccsp9/kzXXBxwv94s58OushlLV6R7lz1raA6kXPkgGjwSOQR6bKQyJyOnoL0wxKQoIGny5ID0OEeVFMUYgT7aHlVsn+Xeb7zuFkAT3LYMtvkzCK+DFfrBgoPeilqivjZ+We6DqbHg+Zamb; "
        "mv.access-token=v4.public.eyJleHAiOiIyMDI2LTEwLTI4VDIyOjAzOjE4LjAwMFoiLCJhciI6IkFRIiwic3ViIjoiMTAwMzQyNjg5MSIsInR5cGUiOiJNVl9TVEFSIiwidmVyaWYiOjEsImlhdCI6IjIwMjYtMTAtMjhUMjE6MzM6MTguNzU2WiJ9-hBgkp1D-5G2A19Gd_jq8zxgV_E_uV7GwRDl7MUIhmV8_k9h62_B3eFCb-G3hWoFhyv39TNtbNJO6Tdn4o_3DA.eyJraWQiOiJrNC5waWQuRThkbGpmc19TbWxnbkJObVNQRDdBN3JIbkYzZEoxQXRqRXB3VWdNWUtPczkifQ"
    )
}


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_secrets():
    with open(SECRETS_FILE, "r") as f:
        return json.load(f)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"synced_ids": [], "synced_titles": [], "total_mb": 0}


def save_progress(prog):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f, indent=2)


def fetch_fresh_video_download(video_id: int):
    """Requests fresh signed CloudFront download URL for a video ID."""
    url = f"https://api.manyvids.com/store/videos/{video_id}/download"
    req = urllib.request.Request(url, headers=MANYVIDS_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"Error fetching download for {video_id}: {e}")
    return None


def upload_via_curl(local_path: Path, remote_url: str, storage_pwd: str) -> bool:
    """Uses curl for zero-overhead streaming upload directly to Bunny.net."""
    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", "PUT", remote_url,
        "-H", f"AccessKey: {storage_pwd}",
        "-H", "Content-Type: application/octet-stream",
        "--data-binary", f"@{local_path}"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        lines = res.stdout.strip().split("\n")
        code = lines[-1].strip() if lines else ""
        if code in ("200", "201"):
            return True
        else:
            log(f"Upload failed: HTTP {code} - Output: {res.stdout[:200]}")
            return False
    except Exception as e:
        log(f"cURL upload error: {e}")
        return False


def generate_stills_and_teaser(video_path: Path, output_dir: Path):
    """Extracts 3 stills and 15s teaser using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
    try:
        duration = float(subprocess.check_output(probe_cmd, timeout=10).decode().strip())
    except Exception:
        duration = 600.0

    stills = []
    for i, ratio in enumerate([0.25, 0.50, 0.75]):
        still_file = output_dir / f"still_{i+1}.jpg"
        ts = max(5.0, duration * ratio)
        cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(still_file)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        if still_file.exists():
            stills.append(still_file)

    teaser_file = output_dir / "teaser_15s.mp4"
    teaser_start = max(10.0, duration * 0.35)
    t_cmd = [
        "ffmpeg", "-y", "-ss", str(teaser_start), "-i", str(video_path), "-t", "15",
        "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", str(teaser_file)
    ]
    subprocess.run(t_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)

    return stills, teaser_file if teaser_file.exists() else None


def run_sync():
    sec = load_secrets()
    vault = sec.get("creator_vault", {})
    storage_pwd = vault.get("bunny_storage_password")
    zone = vault.get("bunny_storage_zone", "workhorse-vault")
    endpoint = vault.get("bunny_storage_endpoint", "https://ny.storage.bunnycdn.com").rstrip("/")

    if not storage_pwd:
        log("Error: bunny_storage_password missing!")
        return

    with open(CATALOG_FILE, "r") as f:
        catalog = json.load(f)

    progress = load_progress()
    synced_set = set(progress.get("synced_ids", []))

    log(f"🚀 Starting Cloud Vault Sync for {len(catalog)} videos...")
    log(f"Already synced: {len(synced_set)} / {len(catalog)}")

    for idx, item in enumerate(catalog, 1):
        vid_id = item["id"]
        title = item["title"]

        if vid_id in synced_set:
            continue

        clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).strip("_")
        while "__" in clean_title:
            clean_title = clean_title.replace("__", "_")
        log(f"[{idx}/{len(catalog)}] Fetching fresh link for: [{vid_id}] {title}...")

        dl_data = fetch_fresh_video_download(vid_id)
        if not dl_data:
            log(f"  ⚠️ Skipping {vid_id}: Could not resolve download URL.")
            time.sleep(2)
            continue

        trans = dl_data.get("transcoded") or {}
        orig = dl_data.get("original") or {}

        source_info = trans if trans.get("file_url") else orig
        file_url = source_info.get("file_url")
        file_ext = source_info.get("file_ext", "mp4")
        file_size_str = source_info.get("file_size", "unknown")

        if not file_url:
            log(f"  ⚠️ No file_url for {vid_id}.")
            continue

        local_video = TEMP_DIR / f"{vid_id}.{file_ext}"
        log(f"  ⬇️ Downloading {file_size_str} to VPS scratch...")
        
        # Download from ManyVids CDN
        try:
            req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as resp, open(local_video, "wb") as out:
                shutil.copyfileobj(resp, out)
        except Exception as e:
            log(f"  ❌ Download failed: {e}")
            if local_video.exists():
                local_video.unlink()
            time.sleep(2)
            continue

        size_mb = round(local_video.stat().st_size / (1024 * 1024), 2)

        # Extract 3 stills + 15s teaser
        log("  🎬 Generating 3 stills & 15s teaser via FFmpeg...")
        teaser_dir = TEMP_DIR / f"teasers_{vid_id}"
        stills, teaser = generate_stills_and_teaser(local_video, teaser_dir)

        # Upload full video to Bunny via cURL
        filename = f"{vid_id}_{clean_title[:60]}.{file_ext}"
        bunny_vid_url = f"{endpoint}/{zone}/charlette_webb/legacy_vault/{filename}"
        log(f"  ⬆️ Uploading full video ({size_mb} MB) to Bunny: {filename}...")
        
        success = upload_via_curl(local_video, bunny_vid_url, storage_pwd)
        if not success:
            log(f"  ❌ Failed to upload {filename} to Bunny.")
            continue

        # Upload stills and teaser
        for still_p in stills:
            b_url = f"{endpoint}/{zone}/charlette_webb/teasers/{vid_id}/{still_p.name}"
            upload_via_curl(still_p, b_url, storage_pwd)

        if teaser and teaser.exists():
            b_url = f"{endpoint}/{zone}/charlette_webb/teasers/{vid_id}/teaser_15s.mp4"
            upload_via_curl(teaser, b_url, storage_pwd)

        # Cleanup local scratch files
        local_video.unlink(missing_ok=True)
        shutil.rmtree(teaser_dir, ignore_errors=True)

        synced_set.add(vid_id)
        progress["synced_ids"] = list(synced_set)
        progress["synced_titles"].append({"id": vid_id, "title": title, "filename": filename, "mb": size_mb})
        progress["total_mb"] += size_mb
        save_progress(progress)
        log(f"  ✅ [SUCCESS] Ingested [{vid_id}] {title} ({size_mb} MB) + 3 stills + teaser! (Total Synced: {len(synced_set)}/{len(catalog)})")
        time.sleep(1)

    log("\n🎉 ALL 747 VIDEOS & TEASERS SYNCED TO BUNNY.NET STORAGE!")


if __name__ == "__main__":
    run_sync()
