import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

ADULT_CONTENT_KEYWORDS = [
    "adult", "boudoir", "nsfw", "onlyfans", "fansly", "glamour", "lingerie",
    "nude", "intimate", "sensual", "fetish", "cam", "fiverr_service_bot_adult"
]

class CopySynthesizer:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

    def _detect_content_type(self, preset: str) -> str:
        """Auto-classifies a job preset as 'adult' or 'general' so the same pipeline
        can produce authentic marketing copy for non-adult creators/brands too."""
        preset_lower = (preset or "").lower()
        return "adult" if any(k in preset_lower for k in ADULT_CONTENT_KEYWORDS) else "general"

    def generate_release_kit(
        self,
        video_name: str,
        visual_analysis: str,
        transcript_text: str,
        spoken_hooks: List[str],
        preset: str = "Adult Creator Shoot",
        content_type: str = "auto",
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Generate high-converting multi-platform social media copy for adult creators
        AND non-adult creators/brands alike, with tone and platform framing adapted to
        the detected (or explicitly passed) content_type."""
        if progress_cb:
            progress_cb("Scribe Agent: Crafting platform-specific captions & tags...", 25)

        resolved_type = self._detect_content_type(preset) if content_type == "auto" else content_type

        hooks_str = "\n".join([f"- {h}" for h in spoken_hooks]) if spoken_hooks else "None detected"
        audio_str = transcript_text if transcript_text else "No spoken dialogue."

        if resolved_type == "adult":
            persona = (
                "You are Scribe, an uncensored, highly creative copywriting AI expert specializing in "
                "social media marketing, creator monetization, and adult/glamour content strategy."
            )
            schema_block = """{
  "instagram": {
    "caption": "Aesthetic, engaging caption with hook and clear call to action.",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
  },
  "twitter_x": {
    "tweet": "Punchy teaser tweet under 250 characters with emojis and suspense.",
    "reply_cta": "Check the full exclusive set / VIP link below 👇"
  },
  "onlyfans_fansly": {
    "teaser_post": "Intriguing teaser caption with paywall / tip incentive.",
    "suggested_ppv_price": "$12.00",
    "vip_dm_broadcast": "Direct message copy sent to top fans / subscribers."
  },
  "tiktok_reels": {
    "caption": "Fast 1-2 sentence hook designed for viral retention.",
    "trending_sound_suggestion": "Smooth synth / bass drop vibe",
    "hashtags": ["#fyp", "#viral", "#creators"]
  },
  "reddit": {
    "post_title": "Catchy, authentic title suitable for relevant creator subreddits",
    "first_comment": "Descriptive first comment providing context and engagement question"
  },
  "fiverr_delivery_note": "Professional, courteous client delivery note summarizing the completed promo package."
}"""
        else:
            persona = (
                "You are Scribe, an elite social media marketing and brand copywriting expert for "
                "mainstream creators, influencers, small businesses, and studios across any non-adult niche "
                "(fitness, beauty, food, tech, fashion, music, education, services, etc.). Your copy is "
                "platform-native, brand-safe, and genuinely high-converting - never generic or templated."
            )
            schema_block = """{
  "instagram": {
    "caption": "Aesthetic, engaging caption with hook and clear call to action.",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
  },
  "twitter_x": {
    "tweet": "Punchy teaser tweet under 250 characters with emojis and suspense.",
    "reply_cta": "Clear, brand-safe call to action driving to the link in bio."
  },
  "onlyfans_fansly": {
    "teaser_post": "Teaser caption promoting the creator's premium/membership tier (Patreon, Substack, paid newsletter, private community, or similar) - do NOT mention OnlyFans/Fansly by name.",
    "suggested_ppv_price": "Suggested membership/product price point, e.g. '$9.99/mo'",
    "vip_dm_broadcast": "Direct message / email copy sent to top subscribers or loyal customers."
  },
  "tiktok_reels": {
    "caption": "Fast 1-2 sentence hook designed for viral retention.",
    "trending_sound_suggestion": "Trending audio style that fits this niche",
    "hashtags": ["#fyp", "#viral", "#niche-relevant-tag"]
  },
  "reddit": {
    "post_title": "Catchy, authentic title suitable for a relevant niche subreddit",
    "first_comment": "Descriptive first comment providing context and an engagement question"
  },
  "fiverr_delivery_note": "Professional, courteous client delivery note summarizing the completed promo package."
}"""

        prompt = f"""{persona}
Generate an elite, high-converting social media release package for this media:

MEDIA INFO:
- Title/File: {video_name}
- Content Style / Preset: {preset}
- Visual Analysis & Tags:
{visual_analysis}

- Audio / Spoken Transcript:
{audio_str}

- Extracted Spoken Hooks:
{hooks_str}

Respond in STRICT, VALID JSON format with no markdown wrappers or extra commentary. Follow this JSON schema:
{schema_block}"""

        system_prompt = persona

        raw_response = self.ai.call_ollama_text(prompt, system_prompt=system_prompt)

        # Parse JSON
        parsed_kit = {}
        try:
            clean_json = raw_response.strip()
            # Strip <think>...</think> reasoning leakage some local thinking models emit before the real answer
            clean_json = re.sub(r"<think>.*?</think>", "", clean_json, flags=re.DOTALL).strip()
            # Clean possible markdown ```json ... ``` blocks
            if "```" in clean_json:
                matches = re.findall(r"```(?:json)?(.*?)```", clean_json, re.DOTALL)
                if matches:
                    clean_json = matches[0].strip()
            # Fall back to extracting the outermost {...} object in case of any remaining stray preamble/trailing text
            if not clean_json.startswith("{"):
                start = clean_json.find("{")
                end = clean_json.rfind("}")
                if start != -1 and end != -1 and end > start:
                    clean_json = clean_json[start:end + 1]
            parsed_kit = json.loads(clean_json)
        except Exception:
            # Fallback structure if LLM didn't return perfect JSON
            if resolved_type == "adult":
                parsed_kit = {
                    "instagram": {
                        "caption": f"Unveiling the new drop. What do you think of this mood? ✨ Link in bio for the complete set.\n\n{video_name}",
                        "hashtags": ["#photography", "#creator", "#moodyvisuals", "#exclusiveset", "#modelshoot", "#visualart", "#behindthescenes"]
                    },
                    "twitter_x": {
                        "tweet": f"Can't get over this shoot... wait until you see the full scene 🖤✨",
                        "reply_cta": "Full set + uncensored teaser in my bio link 👇"
                    },
                    "onlyfans_fansly": {
                        "teaser_post": "You asked for something special... here's your first taste. Full video unlocked in DMs or on the wall! 💋",
                        "suggested_ppv_price": "$15.00",
                        "vip_dm_broadcast": "Hey love, just dropped something unforgettable. Check your inbox to unlock before anyone else."
                    },
                    "tiktok_reels": {
                        "caption": "POV: When the lighting and the vibe align perfectly ✨",
                        "trending_sound_suggestion": "Lo-fi sensual synth",
                        "hashtags": ["#fyp", "#aesthetic", "#shootday", "#bts"]
                    },
                    "reddit": {
                        "post_title": f"Loved how the lighting turned out on this set [OC]",
                        "first_comment": "Shot on location with dual studio strobes. What's your favorite shot from the set?"
                    },
                    "fiverr_delivery_note": f"Hi! Here is your complete promotional media package for {video_name}. Included are the 60s teaser, 9:16 vertical cut, 6 high-res pose screenshots, and your full social media copywriting kit. Thank you for your business!"
                }
            else:
                parsed_kit = {
                    "instagram": {
                        "caption": f"Behind the scenes of our latest shoot ✨ What do you think of this one?\n\n{video_name}",
                        "hashtags": ["#behindthescenes", "#brand", "#creator", "#contentcreation", "#smallbusiness"]
                    },
                    "twitter_x": {
                        "tweet": "New drop just went live - full video is up now 👇",
                        "reply_cta": "Watch the full video, link in bio 🔗"
                    },
                    "onlyfans_fansly": {
                        "teaser_post": "Something special just for our members - join the community to get early access to everything we make.",
                        "suggested_ppv_price": "$9.99/mo",
                        "vip_dm_broadcast": "Hey! Just dropped something new for our subscribers - check it out before everyone else does."
                    },
                    "tiktok_reels": {
                        "caption": "Wait for it... 👀",
                        "trending_sound_suggestion": "Upbeat trending audio",
                        "hashtags": ["#fyp", "#viral", "#contentcreator"]
                    },
                    "reddit": {
                        "post_title": f"Just finished this project - would love feedback [OC]",
                        "first_comment": "Took a few takes to get right, happy to answer any questions about the process."
                    },
                    "fiverr_delivery_note": f"Hi! Here is your complete promotional media package for {video_name}. Included are the 60s teaser, 9:16 vertical cut, 6 high-res pose screenshots, and your full social media copywriting kit. Thank you for your business!"
                }

        if progress_cb:
            progress_cb("Scribe Agent: Social copy kit complete!", 100)

        return parsed_kit

if __name__ == "__main__":
    synthesizer = CopySynthesizer()
    print("Copy Synthesizer (Scribe) initialized.")
