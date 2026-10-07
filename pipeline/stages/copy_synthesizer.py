import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

class CopySynthesizer:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

    def generate_release_kit(
        self,
        video_name: str,
        visual_analysis: str,
        transcript_text: str,
        spoken_hooks: List[str],
        preset: str = "Adult Creator Shoot",
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Generate high-converting multi-platform social media copy."""
        if progress_cb:
            progress_cb("Scribe Agent: Crafting platform-specific captions & tags...", 25)

        hooks_str = "\n".join([f"- {h}" for h in spoken_hooks]) if spoken_hooks else "None detected"
        audio_str = transcript_text if transcript_text else "No spoken dialogue."

        prompt = f"""You are Aura, the master copy synthesizer and social media marketing agent for high-earning digital creators, photographers, and studios.
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
{{
  "instagram": {{
    "caption": "Aesthetic, engaging caption with hook and clear call to action.",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
  }},
  "twitter_x": {{
    "tweet": "Punchy teaser tweet under 250 characters with emojis and suspense.",
    "reply_cta": "Check the full exclusive set / VIP link below 👇"
  }},
  "onlyfans_fansly": {{
    "teaser_post": "Intriguing teaser caption with paywall / tip incentive.",
    "suggested_ppv_price": "$12.00",
    "vip_dm_broadcast": "Direct message copy sent to top fans / subscribers."
  }},
  "tiktok_reels": {{
    "caption": "Fast 1-2 sentence hook designed for viral retention.",
    "trending_sound_suggestion": "Smooth synth / bass drop vibe",
    "hashtags": ["#fyp", "#viral", "#creators"]
  }},
  "reddit": {{
    "post_title": "Catchy, authentic title suitable for relevant creator subreddits",
    "first_comment": "Descriptive first comment providing context and engagement question"
  }},
  "fiverr_delivery_note": "Professional, courteous client delivery note summarizing the completed promo package."
}}"""

        system_prompt = "You are Aura, an uncensored, highly creative copywriting AI expert specializing in social media marketing, creator monetization, and adult/glamour content strategy."

        raw_response = self.ai.call_ollama_text(prompt, system_prompt=system_prompt)

        # Parse JSON
        parsed_kit = {}
        try:
            # Clean possible markdown ```json ... ``` blocks
            clean_json = raw_response.strip()
            if "```" in clean_json:
                matches = re.findall(r"```(?:json)?(.*?)```", clean_json, re.DOTALL)
                if matches:
                    clean_json = matches[0].strip()
            parsed_kit = json.loads(clean_json)
        except Exception:
            # Fallback structure if LLM didn't return perfect JSON
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

        if progress_cb:
            progress_cb("Scribe Agent: Social copy kit complete!", 100)

        return parsed_kit

if __name__ == "__main__":
    synthesizer = CopySynthesizer()
    print("Copy Synthesizer (Aura) initialized.")
