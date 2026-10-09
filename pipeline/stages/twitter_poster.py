"""
WORKHORSE PIPELINE STAGE: TWITTER / X THREAD DISPATCHER
Handles direct API publishing of tweets and threaded sequences for:
  - @TheCreatorAsset (Studio Photography & Media Presets)
  - @creatorpulselab (The Daily Creator Pulse / Monetization)
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import tweepy

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}

class TwitterPoster:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json", secrets_path: str = "F:/WORKHORSE/secrets.json"):
        self.config_path = Path(config_path)
        self.secrets_path = Path(secrets_path)

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_credentials(self) -> Dict[str, Any]:
        """Credentials live outside config.json (gitignored secrets.json) so they never land in version control."""
        if not self.secrets_path.exists():
            return {}
        try:
            with open(self.secrets_path, "r", encoding="utf-8") as f:
                return json.load(f).get("twitter_credentials", {})
        except Exception:
            return {}

    def get_client(self, handle: str) -> Optional[tweepy.Client]:
        """
        Returns a tweepy.Client authenticated for the target handle.
        Handle can be '@TheCreatorAsset', 'TheCreatorAsset', '@creatorpulselab', or 'creatorpulselab'.
        """
        clean_handle = handle.lstrip("@").strip()
        creds_all = self._load_credentials()
        
        # Match case-insensitively
        creds = None
        for k, v in creds_all.items():
            if k.lower() == clean_handle.lower():
                creds = v
                break
                
        if not creds:
            return None

        api_key = creds.get("api_key", "").strip()
        api_secret = creds.get("api_secret", "").strip()
        access_token = creds.get("access_token", "").strip()
        access_token_secret = creds.get("access_token_secret", "").strip()
        bearer_token = creds.get("bearer_token", "").strip()

        if not (api_key and api_secret and access_token and access_token_secret):
            return None

        return tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token or None
        )

    def verify_credentials(self, handle: str) -> Dict[str, Any]:
        """Check if credentials are configured and valid for handle."""
        client = self.get_client(handle)
        if not client:
            return {
                "configured": False,
                "handle": handle,
                "error": f"Missing API credentials for {handle} in config.json."
            }
        try:
            user = client.get_me(user_auth=True)
            if user and user.data:
                return {
                    "configured": True,
                    "handle": handle,
                    "user_id": str(user.data.id),
                    "username": user.data.username,
                    "name": user.data.name
                }
            return {"configured": True, "handle": handle, "note": "Verified"}
        except Exception as e:
            return {"configured": False, "handle": handle, "error": str(e)}


    def _is_duplicate_tweet(self, text: str) -> bool:
        """Checks if identical text was posted in the last 7 days using SHA-256."""
        import hashlib
        from shared.atomic_writer import safe_read_json, atomic_write_json
        history_file = Path("F:/WORKHORSE/workspace/tweet_history.json")
        data = safe_read_json(history_file, default={"hashes": {}, "recent": []})
        
        txt_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        now = time.time()
        seven_days = 7 * 86400
        
        # Prune old hashes
        hashes = {h: ts for h, ts in data.get("hashes", {}).items() if now - ts < seven_days}
        if txt_hash in hashes:
            return True
            
        hashes[txt_hash] = now
        data["hashes"] = hashes
        atomic_write_json(history_file, data)
        return False

    def post_thread(self, handle: str, tweets: List[str], media_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publishes a list of tweets sequentially as a single connected thread.
        Optionally uploads and attaches media files (e.g. ComfyUI 5070 Ti renders) to the root tweet.
        """
        clean_handle = handle.lstrip("@").strip()
        creds_all = self._load_credentials()
        creds = None
        for k, v in creds_all.items():
            if k.lower() == clean_handle.lower():
                creds = v
                break

        client = self.get_client(handle)
        if not client:
            return {
                "success": False,
                "error": f"API keys not configured for {handle} in secrets.json. Please add your Twitter Developer API credentials under twitter_credentials.",
                "handle": handle
            }

        if not tweets:
            return {"success": False, "error": "No tweets provided in thread payload."}

        # Media upload handling
        media_ids = []
        if media_paths and creds:
            try:
                api_key = creds.get("api_key", "").strip()
                api_secret = creds.get("api_secret", "").strip()
                access_token = creds.get("access_token", "").strip()
                access_token_secret = creds.get("access_token_secret", "").strip()
                if api_key and api_secret and access_token and access_token_secret:
                    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
                    api_v1 = tweepy.API(auth)
                    for mp in media_paths:
                        p = Path(mp)
                        if not p.exists():
                            continue

                        is_video = p.suffix.lower() in VIDEO_EXTENSIONS
                        if not is_video:
                            # SCRUBBER [82 Pb] Pre-flight EXIF scrub (images only - the
                            # scrubber targets EXIF, not video container metadata)
                            try:
                                from pipeline.stages.scrubber import metadata_scrubber
                                metadata_scrubber.scrub_image(p)
                            except Exception:
                                pass

                        if is_video:
                            # X requires chunked upload + media_category=tweet_video for
                            # video, and processes it asynchronously server-side -
                            # attaching a still-processing media_id to a tweet fails, so
                            # poll STATUS until it reports succeeded/failed.
                            print(f"[TwitterPoster] Uploading video media to X (chunked): {p.name}...")
                            up_res = api_v1.media_upload(filename=str(p), chunked=True, media_category="tweet_video")
                            media_id = up_res.media_id
                            processing_info = getattr(up_res, "processing_info", None)
                            if processing_info:
                                deadline = time.time() + 180
                                state = processing_info.get("state")
                                while state not in ("succeeded", "failed") and time.time() < deadline:
                                    wait_secs = processing_info.get("check_after_secs", 3)
                                    time.sleep(wait_secs)
                                    status = api_v1.get_media_upload_status(media_id)
                                    processing_info = getattr(status, "processing_info", None) or {}
                                    state = processing_info.get("state", "succeeded")
                                if state == "failed":
                                    print(f"[TwitterPoster] X rejected video processing for {p.name}: {processing_info}")
                                    continue
                            media_ids.append(media_id)
                        else:
                            print(f"[TwitterPoster] Uploading image media to X: {p.name}...")
                            up_res = api_v1.media_upload(filename=str(p))
                            media_ids.append(up_res.media_id)
            except Exception as me:
                print(f"[TwitterPoster] Warning: Media upload failed, falling back to text: {me}")

        posted_ids = []
        try:
            # 1. Post root tweet with optional media_ids
            if media_ids:
                res = client.create_tweet(text=tweets[0], media_ids=media_ids, user_auth=True)
            else:
                res = client.create_tweet(text=tweets[0], user_auth=True)

            first_id = res.data["id"]
            posted_ids.append(first_id)
            prev_id = first_id

            # 2. Reply to previous tweet sequentially with polite 1.8s stagger
            for tweet_text in tweets[1:]:
                time.sleep(1.8)
                res = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=prev_id, user_auth=True)
                curr_id = res.data["id"]
                posted_ids.append(curr_id)
                prev_id = curr_id

            clean_handle = handle.lstrip("@")
            thread_url = f"https://x.com/{clean_handle}/status/{first_id}"
            return {
                "success": True,
                "handle": handle,
                "tweet_count": len(posted_ids),
                "first_tweet_id": first_id,
                "thread_url": thread_url,
                "tweet_ids": posted_ids,
                "media_attached": len(media_ids)
            }
        except Exception as e:
            return {
                "success": False,
                "handle": handle,
                "error": f"Twitter API error: {str(e)}",
                "posted_partial": posted_ids
            }
