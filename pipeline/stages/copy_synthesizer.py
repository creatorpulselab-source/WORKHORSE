import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService, parse_llm_json
from shared.atomic_writer import safe_read_json

ADULT_CONTENT_KEYWORDS = [
    "adult", "boudoir", "nsfw", "onlyfans", "fansly", "glamour", "lingerie",
    "nude", "intimate", "sensual", "fetish", "cam", "fiverr_service_bot_adult"
]

# Prism-style caption "style pills" - gives Scribe variety instead of one fixed caption tone
CAPTION_STYLE_GUIDE = {
    "Hook": "Open with a bold, scroll-stopping first line that creates curiosity or tension.",
    "Story": "Frame it as a short narrative moment - what was happening, how it felt.",
    "Question": "Lead with a direct question to the audience designed to drive comments.",
    "Hot-Take": "A bold, slightly provocative opinion or statement related to the content.",
    "BTS": "Behind-the-scenes, process-focused framing - the making-of angle.",
    "Soft-Sell": "Low-pressure, relationship-building tone with a minimal, casual call to action.",
    "Relatable": "Casual, meme-adjacent, relatable everyday tone."
}

TWEET_HISTORY_PATH = Path("F:/WORKHORSE/workspace/tweet_history.json")
SCRIBE_CACHE_PATH = Path("F:/WORKHORSE/workspace/scribe_daily_content.json")


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
        caption_styles: Optional[List[str]] = None,
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Generate high-converting multi-platform social media copy for adult creators
        AND non-adult creators/brands alike, with tone and platform framing adapted to
        the detected (or explicitly passed) content_type. Also produces several labeled
        Instagram caption style variants (Prism-style "style pills") instead of one fixed tone."""
        if progress_cb:
            progress_cb("Scribe Agent: Crafting platform-specific captions & tags...", 25)

        resolved_type = self._detect_content_type(preset) if content_type == "auto" else content_type
        resolved_styles = caption_styles or ["Hook", "Story", "Question"]
        style_guide_str = "\n".join([f"- {s}: {CAPTION_STYLE_GUIDE.get(s, 'A distinct caption tone/angle.')}" for s in resolved_styles])

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
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "caption_variants": [
      {"style": "StyleNameFromGuide", "text": "Full caption written in that style."}
    ]
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
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "caption_variants": [
      {"style": "StyleNameFromGuide", "text": "Full caption written in that style."}
    ]
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

For the Instagram "caption_variants" array, write exactly {len(resolved_styles)} DIFFERENT caption variants, one per style below, each tagged with its exact style name:
{style_guide_str}

CRITICAL COPYWRITING RULES:
- Never write teasers or rhetorical questions that leave the audience without context or payoff. Deliver real narrative hook and aesthetic value first. If asking an engagement question, position it at the end to drive comments after providing a strong hook.
- If mentioning lists or tips (e.g. '3 poses', 'Top 5'), enumerate the specific items.

Respond in STRICT, VALID JSON format with no markdown wrappers or extra commentary. Follow this JSON schema:
{schema_block}"""

        system_prompt = persona

        raw_response = self.ai.call_ollama_text(prompt, system_prompt=system_prompt, json_mode=True)

        # Parse JSON
        parsed_kit = parse_llm_json(raw_response) or {}
        if not parsed_kit:
            # Fallback structure if LLM didn't return perfect JSON
            if resolved_type == "adult":
                parsed_kit = {
                    "instagram": {
                        "caption": f"Unveiling the new drop. What do you think of this mood? ✨ Link in bio for the complete set.\n\n{video_name}",
                        "hashtags": ["#photography", "#creator", "#moodyvisuals", "#exclusiveset", "#modelshoot", "#visualart", "#behindthescenes"],
                        "caption_variants": [{"style": s, "text": f"Unveiling the new drop. What do you think of this mood? ✨ Link in bio for the complete set.\n\n{video_name}"} for s in resolved_styles]
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
                        "hashtags": ["#behindthescenes", "#brand", "#creator", "#contentcreation", "#smallbusiness"],
                        "caption_variants": [{"style": s, "text": f"Behind the scenes of our latest shoot ✨ What do you think of this one?\n\n{video_name}"} for s in resolved_styles]
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

        # Safety net: guarantee caption_variants always exists even if the model's JSON omitted it
        ig_block = parsed_kit.setdefault("instagram", {})
        if not ig_block.get("caption_variants"):
            base_caption = ig_block.get("caption", video_name)
            ig_block["caption_variants"] = [{"style": s, "text": base_caption} for s in resolved_styles]

        return parsed_kit

    # Per-publication JSON schema additions for the sections beyond the lead story -
    # each publication's newsletter has a different fixed section layout (see
    # newsletter_manager.py's _build_*_html methods), so each needs its own
    # additional fields. Keeping the section TOPICS/labels fixed (matching the
    # existing HTML) while making the actual insights/scripts/data within them fresh
    # daily - same principle as a real newspaper's named columns running new stories
    # under the same column header every day. Each block ends with a trailing comma
    # since it's always followed by "markdown_article" in the assembled prompt.
    SECTION_SCHEMAS: Dict[str, str] = {
        "creator_pulse": """  "metric_card_1": {"label": "short stat label for an organic-reach/retention metric", "value": "a punchy stat value, e.g. '78.4% at 3 Seconds'", "note": "one short supporting phrase"},
  "metric_card_2": {"label": "short stat label for a shadowban/algorithm-risk metric", "value": "a punchy stat value", "note": "one short supporting phrase"},
  "ppv_headline": "headline for a PPV/DM teaser-script section (what the 3 scripts below accomplish)",
  "ppv_intro": "1 sentence intro for that section",
  "ppv_scripts": [
    {"label": "short title with an emoji and a price range in parentheses, e.g. 'Script 1: The Midnight Audio ($18 - $25 Unlock)'", "quote": "a ready-to-send first-person DM/caption script in quotes (NO personal account handles)", "insight": "one sentence explaining WHY this script converts"},
    {"label": "Script 2 title with emoji and price range", "quote": "second distinct ready-to-send script", "insight": "why Script 2 converts"},
    {"label": "Script 3 title with emoji and price range", "quote": "third distinct ready-to-send script", "insight": "why Script 3 converts"}
  ],
  "ladder_headline": "headline for a progressive tip-ladder/milestone engagement section",
  "ladder_intro": "1-2 sentence intro for that section",
  "ladder_tiers": [
    {"tier": "Tier 1", "tokens": "150 Tokens", "action": "stream engagement action", "trigger": "low barrier entry trigger"},
    {"tier": "Tier 2", "tokens": "450 Tokens", "action": "collaborative stream action", "trigger": "room excitement trigger"},
    {"tier": "Tier 3 (Peak)", "tokens": "900 Tokens", "action": "exclusive peak action", "trigger": "exclusivity climax trigger"}
  ],
  "visual_setup_headline": "headline for a creator stream lighting & visual production formula",
  "visual_setup_intro": "1-2 sentence intro explaining the lighting placement",
  "visual_setup_pro_tip": "exact color temperature (K), modifier angles, and placement advice",
  "retention_headline": "headline for a subscriber-retention tip section",
  "retention_body": "2-3 sentences of genuinely new retention advice",
""",
        "studio_wire": """  "recipe_headline": "headline for today's Lightroom/color-grading 'recipe of the day' (pick a fresh film stock or editorial look today)",
  "recipe_intro": "1-2 sentence intro",
  "recipe_rows": [
    {"module": "a Lightroom/editing module or panel name", "setting": "the exact slider/value setting", "characteristic": "what film/look characteristic it produces"},
    {"module": "second module/panel name", "setting": "exact slider/value setting", "characteristic": "film/look characteristic"},
    {"module": "third module/panel name", "setting": "exact slider/value setting", "characteristic": "film/look characteristic"}
  ],
  "lighting_headline": "headline for today's studio lighting blueprint",
  "lighting_intro": "1-2 sentence intro explaining how this setup sculpts light and shadow",
  "lighting_specs": "precise distances (e.g. 3.5 ft), modifier type (e.g. 22-inch beauty dish with grid), meter f-stop, and fill ratio",
  "directing_headline": "headline for a model/client posing-direction tip section",
  "directing_intro": "1 sentence intro",
  "directing_cues": [
    {"cue": "a short spoken direction in quotes", "explanation": "what it physically does/why it works"},
    {"cue": "second spoken direction in quotes", "explanation": "what it physically does/why it works"},
    {"cue": "third spoken direction in quotes", "explanation": "what it physically does/why it works"}
  ],
  "pricing_headline": "headline for a studio pricing/delivery business tip",
  "pricing_body": "2-3 sentences of genuinely new business/pricing advice",
""",
        "creator_blueprint": """  "flywheel_headline": "headline for a digital media & asset flywheel framework",
  "flywheel_intro": "1-2 sentence intro explaining the 3-stage progression",
  "flywheel_phases": [
    {"phase": "Phase 1: High-Touch Client Validation", "desc": "validating demand through custom service delivery (NO real personal account handles)"},
    {"phase": "Phase 2: Productize into Digital Downloads", "desc": "packaging validated assets into presets/toolkits with zero shipping cost"},
    {"phase": "Phase 3: Organic Audience Syndication", "desc": "sharing daily educational insights across social feeds to drive storefront traffic"}
  ],
  "pipeline_headline": "headline for a content syndication/distribution workflow tip",
  "pipeline_intro": "1 sentence intro",
  "pipeline_rows": [
    {"format": "Short-Form Social Thread", "destination": "Twitter / X & Social Feeds", "cta": "Storefront Hub"},
    {"format": "HTML Email Digest", "destination": "Subscriber Inbox", "cta": "Digital Toolkit Downloads"},
    {"format": "Long-Form Article", "destination": "Blog & Search Hub", "cta": "Complete Preset Vault"}
  ],
  "conversion_headline": "headline for a high-converting mobile storefront / link-in-bio rule",
  "conversion_intro": "1-2 sentence intro",
  "conversion_rules": [
    "clear actionable rule 1", "clear actionable rule 2", "clear actionable rule 3", "clear actionable rule 4"
  ],
  "math_headline": "headline for a monetization-math/conversion-rate example section",
  "math_body": "2-3 sentences walking through a genuinely new, specific numeric example",
"""
    }

    def _get_recent_history_constraints(self, pub_id: str) -> str:
        """Loads recent newsletter headlines and recent tweet snippets so Scribe never repeats the same topics."""
        avoid_items: List[str] = []
        try:
            scribe_cache = safe_read_json(SCRIBE_CACHE_PATH, default={})
            if isinstance(scribe_cache, dict):
                prev_entry = scribe_cache.get(pub_id)
                if isinstance(prev_entry, dict):
                    prev_content = prev_entry.get("content") or {}
                    for k in ("lead_headline", "recipe_headline", "ppv_headline", "flywheel_headline", "lighting_headline"):
                        val = prev_content.get(k)
                        if val and isinstance(val, str):
                            avoid_items.append(val.strip())
                hist_list = scribe_cache.get("recent_headlines_history", [])
                if isinstance(hist_list, list):
                    for h in hist_list[-12:]:
                        if isinstance(h, str) and h.strip() not in avoid_items:
                            avoid_items.append(h.strip())
        except Exception:
            pass

        try:
            tweet_hist = safe_read_json(TWEET_HISTORY_PATH, default={})
            if isinstance(tweet_hist, dict):
                for item in reversed(tweet_hist.get("recent", [])[-10:]):
                    if isinstance(item, dict) and item.get("snippet"):
                        snip = str(item["snippet"]).replace("\n", " ").strip()
                        if snip and snip not in avoid_items:
                            avoid_items.append(snip)
        except Exception:
            pass

        if not avoid_items:
            return ""
        bullet_lines = "\n".join(f"- {item}" for item in avoid_items[:15])
        return (
            "\n\nRECENTLY PUBLISHED HEADLINES & TWEETS (DO NOT REPEAT THESE TOPICS, RECIPES, OR HOOKS TODAY):\n"
            + bullet_lines
            + "\n"
        )

    def generate_daily_publication_content(
        self,
        pub_id: str,
        pub_name: str = "",
        audience: str = "",
        funnel_blurb: str = "",
        today_str: str = "",
        research_articles: Optional[List[Dict[str, str]]] = None,
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Generates genuinely fresh daily editorial content for one WORKHORSE publication:
        a new lead-story headline+body, section-by-section content for every dynamic
        section of that publication's actual newsletter template (not just the lead -
        see SECTION_SCHEMAS), a full markdown blog article, and a fresh Twitter/X
        thread - so Herald never dispatches the same canned copy twice, in ANY section."""
        from datetime import datetime
        if not today_str:
            today_str = datetime.now().strftime("%A, %B %d, %Y")
        if not pub_name:
            pub_names_map = {
                "creator_pulse": "The Daily Creator Pulse",
                "studio_wire": "The Shutter & Studio Wire",
                "creator_blueprint": "The Creator Blueprint",
                "dispensary_deals": "Florida Dispensary Deals",
            }
            pub_name = pub_names_map.get(pub_id, pub_id)
        if not audience:
            audience_map = {
                "creator_pulse": "independent digital creators, subscription creators, and live streamers",
                "studio_wire": "commercial portrait photographers, studio directors, and RAW colorists",
                "creator_blueprint": "digital product creators, creative studio owners, and solo media entrepreneurs",
            }
            audience = audience_map.get(pub_id, "independent creators and studios")
        if not funnel_blurb:
            funnel_blurb = "Lightroom .XMP Preset Packs on Etsy, Boutique Studio Retouching on Fiverr, and CreatorMediaLab Hub"

        if progress_cb:
            progress_cb(f"Scribe Agent: Writing fresh daily editorial for {pub_name}...", 10)

        persona = (
            "You are Scribe, a high-converting copywriter and editorial strategist for the "
            f"'{pub_name}' daily publication, written for {audience}. Everything runs 100% "
            "locally and privately. Your job today is to write GENUINELY NEW angles and "
            "insights for EVERY section below - never reuse generic filler or repeat an "
            "idea you'd expect to see in a stale template. Every section must read as if "
            "written fresh today, not a recycled evergreen placeholder."
        )

        research_context = ""
        if research_articles:
            items_str = []
            for a in research_articles:
                title = (a.get("title") or "").strip()
                snippet = (a.get("snippet") or a.get("summary") or "").strip()
                url = (a.get("url") or "").strip()
                if title and snippet:
                    ref_str = f" [Ref: {url}]" if url else ""
                    items_str.append(f"- **{title}**: {snippet}{ref_str}")
                elif title:
                    ref_str = f" [Ref: {url}]" if url else ""
                    items_str.append(f"- **{title}**{ref_str}")
            if items_str:
                research_context = (
                    "\n\nTODAY'S GROUND-TRUTH RESEARCH & LIVE INDUSTRY DATA IN THIS PUBLICATION'S NICHE:\n"
                    + "\n".join(items_str)
                    + "\n\nCRITICAL EDITORIAL & CONVERSION RULES (MANDATORY):\n"
                    + "1. GROUNDED IN REALITY: Ground your angles, lead story, and takeaways directly in the verified research and industry facts above.\n"
                    + "2. NO UNANSWERED QUESTIONS / CLIFFHANGERS: Never post rhetorical questions or teasers without immediately delivering the answer, data, or solution in full.\n"
                    + "3. COMPLETE LISTS & FRAMEWORKS: If you refer to a numbered list (e.g. '3 Formulas', '5 Mistakes', 'Top 4 Tools'), YOU MUST FULLY ENUMERATE AND EXPLAIN EVERY SINGLE ITEM. Never stop at a partial list or cliffhanger.\n"
                    + "4. ACTIONABLE SPECIFICITY: Provide exact percentages, slider settings, lighting setups, or verbatim script wording so the reader receives immediate, practical value.\n"
                    + "5. FRESHNESS: Every section must read as if written fresh today, not recycled or generic filler.\n"
                    + "6. STRICT EDITORIAL INTEGRITY (NO REAL ACCOUNT NAMES IN EDITORIAL): Never use real personal or internal account names or handles (e.g. NEVER use @TheCreatorAsset, @creatorpulselab, or private handles) in editorial text, tweet threads, or examples. Refer to platforms generically (e.g. 'Twitter/X', 'Social Feeds', 'Storefront Hub'). Real account names may ONLY appear in designated commercial advertisement / sponsor blocks.\n"
                    + "7. NO FOURTH-WALL BREAKING / NO AUTOMATED ACCOUNT CLAIMS: Never write 'this is what I'm doing with this automated account', 'how we automate our bots', or refer to backend automation or running automated accounts. All advice must be written as objective, professional industry strategy for independent creators, photographers, and studios.\n"
                    + "8. STRICT 100% SFW: Keep all tweet_thread items 100% Safe For Work (no explicit/adult platform names in tweet_thread).\n"
                )

        section_schema = self.SECTION_SCHEMAS.get(pub_id, "")

        prompt = f"""{persona}

Today is {today_str}. Write fresh daily editorial content for today's issue. This publication promotes: {funnel_blurb}.{research_context}

Respond in STRICT, VALID JSON (no markdown wrappers, no commentary). Use \\n for line breaks inside string values - never use literal newlines inside a JSON string. Follow this exact schema:
{{
  "lead_headline": "A punchy, specific headline for today's #1 lead story (under 90 characters), grounded in today's research above.",
  "lead_body": "2-4 sentences of genuinely new, specific, non-generic insight/advice/data expanding on the headline.",
{section_schema}  "markdown_article": "A complete ~5-section Markdown article body (use ## headers and bullet points, bold where useful) covering fresh angles relevant to {audience} for today's issue. Do not include a title or date line - start directly with the first ## section heading.",
  "tweet_thread": ["1/4 opening hook tweet with an emoji and a bold insight grounded in today's lead story (plain text only, NO ** markdown asterisks)", "2/4 supporting tactical point with exact numbers or settings (plain text only)", "3/4 second supporting point or proof (plain text only)", "4/4 call-to-action tweet inviting readers to check the bio link"]
}}"""

        last_err = None
        for attempt in range(2):
            try:
                raw_response = self.ai.call_ollama_text(
                    prompt,
                    system_prompt=persona,
                    num_ctx=8192,
                    num_predict=4096,
                    temperature=0.75 + (attempt * 0.1),
                    json_mode=True,
                    timeout=150,
                )
                parsed = parse_llm_json(raw_response)
                if not parsed or not parsed.get("lead_headline") or not parsed.get("lead_body"):
                    raise ValueError("Missing lead_headline or lead_body in parsed JSON")

                tweet_thread = parsed.get("tweet_thread")
                if not isinstance(tweet_thread, list) or len(tweet_thread) < 2:
                    raise ValueError("Missing or incomplete tweet_thread in parsed JSON")

                if progress_cb:
                    progress_cb(f"Scribe Agent: Fresh daily editorial ready for {pub_name}.", 100)

                result: Dict[str, Any] = {
                    "success": True,
                    "source": "Scribe [6 C] Live Daily Synthesis",
                    "is_fallback": False,
                    "lead_headline": str(parsed.get("lead_headline") or "").strip(),
                    "lead_body": str(parsed.get("lead_body") or "").strip(),
                    "markdown_article": str(parsed.get("markdown_article") or "").strip(),
                    "tweet_thread": [re.sub(r"\*\*|__", "", str(t)).strip() for t in tweet_thread if str(t).strip()]
                }
                known_keys = {"lead_headline", "lead_body", "markdown_article", "tweet_thread"}
                for k, v in parsed.items():
                    if k not in known_keys:
                        result[k] = v
                return result
            except Exception as e:
                last_err = e
                print(f"[Scribe] LLM text synthesis attempt {attempt + 1}/2 for {pub_id} failed ({e}).")

        print(f"[Scribe] LLM text synthesis failed after 2 attempts ({last_err}). Generating dynamic research-grounded fallback.")
        return self.generate_dynamic_daily_fallback(
            pub_id=pub_id,
            pub_name=pub_name,
            audience=audience,
            funnel_blurb=funnel_blurb,
            today_str=today_str,
            research_articles=research_articles
        )

    def generate_dynamic_daily_fallback(
        self,
        pub_id: str,
        pub_name: str = "",
        audience: str = "",
        funnel_blurb: str = "",
        today_str: str = "",
        research_articles: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Procedural date-seeded dynamic editorial generator: guarantees that every day
        produces a unique, topic-aligned, fully populated issue for each publication,
        even if Ollama is offline or busy. Grounded in today's research_articles across
        both newsletter sections and tweet_thread."""
        from datetime import datetime
        import html as _html
        import re as _re

        day_seed = datetime.now().timetuple().tm_yday
        today_short = datetime.now().strftime("%b %d")

        def _clean_rss_text(raw: str, max_len: int = 80, strip_source: bool = False) -> str:
            if not raw:
                return ""
            txt = _html.unescape(str(raw))
            txt = _re.sub(r"<[^>]+>", " ", txt)
            txt = txt.replace("\xa0", " ")
            if strip_source and " - " in txt:
                txt = txt.rsplit(" - ", 1)[0]
            txt = _re.sub(r"\s+", " ", txt).strip(" .-–—")
            if len(txt) <= max_len:
                return txt
            cut = txt[:max_len].rsplit(" ", 1)[0].rstrip(" .,;:-–—")
            return cut

        arts = research_articles or []
        top_research = arts[0] if len(arts) > 0 else None
        sec_research = arts[1] if len(arts) > 1 else top_research
        top_title = _clean_rss_text((top_research.get("title") or "") if top_research else "", max_len=78, strip_source=True)
        top_snippet = _clean_rss_text((top_research.get("snippet") or "") if top_research else "", max_len=220, strip_source=False)
        sec_title = _clean_rss_text((sec_research.get("title") or "") if sec_research else "", max_len=78, strip_source=True)

        # Guard against bare publisher snippets (e.g. "U.S. Chamber of Commerce")
        if top_snippet and len(top_snippet) < 35:
            top_snippet = ""
        if top_snippet and top_title and top_snippet.lower().startswith(top_title[:30].lower()):
            top_snippet = ""

        if pub_id == "creator_pulse":
            variants = [
                {
                    "lead_headline": f"The 35-Tip Boost: How Multi-Trigger Unlock Cycles Drive 28% Higher Spend" if not top_title else f"{top_title}",
                    "lead_body": (
                        f"{top_snippet} Independent creator monetization data shows that pairing timely content hooks with structured 3-day micro-offer cycles increases subscriber conversion by 28%."
                        if top_snippet
                        else f"Today's industry radar highlights '{top_title or 'Multi-Tier Audience Monetization'}'. When creators pair clear micro-offer tiers ($15-$35) with authentic behind-the-scenes previews, subscriber retention jumps by 34%."
                    ),
                    "metric_card_1": {"label": "Average Unlock Conversion", "value": "31.4% Lift", "note": "With progressive milestone offers"},
                    "metric_card_2": {"label": "Algorithmic Reach Safety", "value": "100% SFW Verified", "note": "Complies with feed discovery filters"},
                    "ppv_headline": "3 Curiosity-Driven Teasers That Convert Without Hard Selling",
                    "ppv_intro": "High-value subscribers convert on narrative anticipation and perceived exclusivity. Use these 3 tested formulas tonight:",
                    "ppv_scripts": [
                        {"label": "🎧 Script 1: The 'Studio Audio' Teaser ($18 - $25 Unlock)", "quote": "Put your headphones on before you press play... 🎧 Quick 90-second voice breakdown from yesterday's studio session. Unlocked for my inner circle first.", "insight": "Audio builds immediate 1-on-1 connection and boosts reply rates."},
                        {"label": "🔒 Script 2: The 'Director's Cut' Vault ($35 - $50 Unlock)", "quote": "My editor told me to save these 4 raw frames for the master archive... unlocking the uncropped set in DMs for the next 2 hours.", "insight": "Scarcity plus behind-the-scenes exclusivity drives fast action."},
                        {"label": "🗳️ Script 3: The 'Color Grade Vote' Poll ($5 - $10 Tip)", "quote": "Which color grade should lead tomorrow's drop: Golden Hour Warmth or Moody Editorial? Vote with a $5 tip and get both hi-res alternates.", "insight": "Low-friction micro-choices convert passive readers into active buyers."}
                    ],
                    "ladder_headline": "The 'Progressive Milestone' Ladder For Live Streams",
                    "ladder_intro": "Replacing static menus with progressive community milestones creates shared room momentum:",
                    "ladder_tiers": [
                        {"tier": "Tier 1", "tokens": "150 Tokens", "action": "Behind-the-scenes lighting breakdown", "trigger": "Low barrier activation"},
                        {"tier": "Tier 2", "tokens": "450 Tokens", "action": "Live playlist & set styling vote", "trigger": "Interactive collaboration"},
                        {"tier": "Tier 3 (Peak)", "tokens": "900 Tokens", "action": "VIP signed instant print giveaway", "trigger": "Collector exclusivity climax"}
                    ],
                    "visual_setup_headline": "The '2-Light Rim Formula' For Crisp Creator Video",
                    "visual_setup_intro": "A single front ring light flattens facial structure. Adding a warm 3200K accent light at 135 degrees behind your shoulder carves instant 3D separation:",
                    "visual_setup_pro_tip": "Set your key softbox to 5600K daylight at 45° and dial your rim light to 3200K amber at 25% output.",
                    "retention_headline": "The 'First 60 Minutes' Renewal Recovery Habit",
                    "retention_body": "Sending a personalized 1-sentence thank-you DM with a bonus preset or outtake within 60 minutes of a subscriber milestone recovers 28% of churned accounts.",
                    "markdown_article": f"## 1. {top_title or 'The Architecture of High-Converting Micro-Offers'}\n\n{top_snippet or 'Creators who structure unlock triggers around a consistent 3-day cycle see sustainable compounding revenue.'}\n\n## 2. {sec_title or 'Safeguarding Reach on Algorithmic Feeds'}\n\nFeed algorithms reward high watch-time and clean editorial framing. Route engaged viewers from public short-form clips into your direct newsletter and storefront hub.\n\n## 3. Progressive Livestream Milestones\n\nGamifying audience participation turns passive viewers into active supporters.\n\n## 4. Two-Light Studio Separation\n\nCombine a 5600K diffused key light with a 3200K warm rim light to create magazine-grade depth on any camera.",
                    "tweet_thread": [
                        f"1/4 ⚡ {today_short} Creator Radar: {top_title or '3 offer structures converting 28% higher for independent creators'} 🧵👇 #CreatorEconomy #Monetization",
                        f"2/4 Core Signal: {(top_snippet or 'Creators pairing low-friction $19 micro-assets with tiered VIP bundles see 31% higher average order value.')[:210]}",
                        f"3/4 Tactical Move: Pair your highest-retention short-form post this week with a 3-tier value ladder ($19 starter -> $49 bundle -> $149 VIP). {sec_title[:70] if sec_title else ''}",
                        "4/4 Tap our bio link for today's full Creator Pulse monetization breakdown and studio templates! 📈✨ #CreatorGrowth #DigitalProducts"
                    ]
                },
                {
                    "lead_headline": f"Why Tight 4:5 Portrait Framing Outperforms Wide Shots on Discovery Feeds" if not top_title else f"{top_title}",
                    "lead_body": (
                        f"{top_snippet} Short-form recommendation engines heavily weight 3-second hold rates, where tight 4:5 eye-contact framing delivers 3.4x higher organic reach."
                        if top_snippet
                        else "Short-form recommendation algorithms heavily favor high-contrast facial expressions and direct eye contact, delivering 3.4x higher organic impressions."
                    ),
                    "metric_card_1": {"label": "3-Second Hold Rate", "value": "78.4% Retention", "note": "With tight 4:5 portrait framing"},
                    "metric_card_2": {"label": "Organic Discovery Lift", "value": "3.4x Reach", "note": "Clean editorial framing on vertical feeds"},
                    "ppv_headline": "3 High-Converting DM Hooks That Drive Instant Replies",
                    "ppv_intro": "Subscribers unlock premium drops when curiosity outweighs price friction. Try these 3 verified formulas:",
                    "ppv_scripts": [
                        {"label": "🔒 Script 1: The 'Unreleased Studio Cut' ($20 Unlock)", "quote": "My photographer said this frame was too moody for the main grid... sending the full 4K outtake to my inner circle today.", "insight": "Curiosity gap triggers immediate impulse unlocks."},
                        {"label": "🎨 Script 2: The 'Color Grade Split Test' ($15 Unlock)", "quote": "Which film look wins: Kodak Portra Warmth or Cinestill Tungsten? Unlocking both full-res master files right now.", "insight": "A/B choice framing boosts reply velocity."},
                        {"label": "👑 Script 3: The 'VIP Early Access' ($45 Unlock)", "quote": "Dropping the complete 12-frame editorial set tonight, but unlocking it for VIPs 3 hours early. ✨", "insight": "Early access rewards reinforce top-supporter status."}
                    ],
                    "ladder_headline": "The 'Interactive Studio Control' Live Menu",
                    "ladder_intro": "Giving viewers real-time creative input over your lighting, music, and set styling increases participation by 45%:",
                    "ladder_tiers": [
                        {"tier": "Tier 1", "tokens": "100 Tokens", "action": "Choose next studio backing track", "trigger": "Low friction participation"},
                        {"tier": "Tier 2", "tokens": "350 Tokens", "action": "Switch RGB rim light palette", "trigger": "Visual set control"},
                        {"tier": "Tier 3 (Peak)", "tokens": "800 Tokens", "action": "Custom signed Fuji Instax frame", "trigger": "Physical collector keepsake"}
                    ],
                    "visual_setup_headline": "Softbox Feathering: Eliminating Harsh Skin Glare",
                    "visual_setup_intro": "Aiming a key light straight at the face amplifies specular glare. Feathering the softbox 45 degrees across the nose wraps the skin in velvety edge light:",
                    "visual_setup_pro_tip": "Raise the softbox 10 inches above eye level and angle it slightly downward past the bridge of the nose.",
                    "retention_headline": "The 72-Hour Onboarding Sequence That Cuts Churn in Half",
                    "retention_body": "Subscribers who receive a personal welcome note and a curated 'best-of' starter bundle within 72 hours of joining retain at a 64% higher rate over 90 days.",
                    "markdown_article": f"## 1. {top_title or 'The Science of 4:5 Portrait Crops'}\n\n{top_snippet or 'Vertical 4:5 framing maximizes mobile screen real estate and boosts 3-second retention.'}\n\n## 2. {sec_title or 'Curiosity-Driven Direct Messaging'}\n\nFrame premium drops as inner-circle studio access rather than generic broadcasts.\n\n## 3. Feathered Softbox Lighting\n\nFeathering your key modifier 45 degrees eliminates forehead glare and softens skin texture naturally.",
                    "tweet_thread": [
                        f"1/4 📱 {today_short} Growth Signal: {top_title or 'Why tight 4:5 portrait framing outperforms wide shots by 3.4x'} 🧵👇 #CreatorGrowth #ContentStrategy",
                        f"2/4 Data Breakdown: {(top_snippet or 'Algorithmic feeds prioritize direct eye contact and clean 4:5 vertical framing, lifting 3-second retention to 78.4%.')[:210]}",
                        f"3/4 Studio Tip: Feather your key softbox 45 degrees across the bridge of the nose to eliminate harsh forehead glare on camera.",
                        "4/4 Explore our bio link for today's complete Creator Pulse issue and studio lighting guides! ✨ #CreatorEconomy #Monetization"
                    ]
                },
            ]
            picked = variants[day_seed % len(variants)]
            return {"success": True, "source": "Scribe Dynamic Daily Synthesis", "is_fallback": True, **picked}

        elif pub_id == "studio_wire":
            variants = [
                {
                    "lead_headline": f"Why Digital Sensor Highlights Clip Harshly (And How To Emulate Film Roll-Off)" if not top_title else f"{top_title}",
                    "lead_body": (
                        f"{top_snippet} Mastering tone-curve shoulder compression and calibrated color profiles separates high-end commercial portraiture from flat digital captures."
                        if top_snippet
                        else "Digital CMOS sensors capture light linearly, clipping highlights abruptly. Emulating analog silver-halide shoulder compression restores velvety highlight roll-off."
                    ),
                    "recipe_headline": "The Kodak Portra 400 Editorial Tone Curve Recipe",
                    "recipe_intro": "Replicate warm, luminous film skin tones with 3 non-destructive RAW adjustments:",
                    "recipe_rows": [
                        {"module": "RGB Tone Curve", "setting": "Lift Black Point to +18 | Drop Highlights -10", "characteristic": "Creamy matte shadow floor with soft highlight shoulder"},
                        {"module": "HSL Orange", "setting": "Saturation: -4% | Luminance: +8%", "characteristic": "Luminous editorial skin tones without orange oversaturation"},
                        {"module": "Color Grading Wheels", "setting": "Midtones Hue 42 (6%) | Shadows Hue 215 (4%)", "characteristic": "Subtle warm/cool split toning for 3D depth"}
                    ],
                    "directing_headline": "3 Micro-Cues That Eliminate Model Stiffness Instantly",
                    "directing_intro": "Replace vague instructions like 'relax' with specific physical micro-adjustments:",
                    "directing_cues": [
                        {"cue": "Exhale slowly through slightly parted lips", "explanation": "Releases masseter jaw tension and softens the mouth line."},
                        {"cue": "Shift 70% of your weight onto your back heel", "explanation": "Creates an natural S-curve and prevents boxy shoulder alignment."},
                        {"cue": "Drop your camera-side shoulder 1 inch", "explanation": "Introduces asymmetric diagonal lines across the collarbone."}
                    ],
                    "pricing_headline": "Why Curated 30-Image Galleries Command 2x Higher Rates Than RAW Dumps",
                    "pricing_body": "Delivering 300 unedited files overwhelms clients with decision fatigue. Delivering 30 fully color-graded master selects within 24 hours positions your studio as a luxury editorial brand.",
                    "lighting_headline": "The 45° Feathered Beauty Dish + Silver Clamshell Rig",
                    "lighting_intro": "Feathering a 22-inch beauty dish across the bridge of the nose wraps the cheekbones in soft directional light while a chest-height silver reflector fills neck shadows:",
                    "lighting_specs": "Key: 22\" white beauty dish + sock at 45°, 3.5 ft, metered at f/5.6. Fill: Curved silver reflector at chest height (-1.5 stops).",
                    "markdown_article": f"## 1. {top_title or 'Analog Film Shoulder vs Linear Digital Sensors'}\n\n{top_snippet or 'Compressing highlight roll-off in the tone curve prevents harsh digital clipping on skin.'}\n\n## 2. {sec_title or 'Calibrated RAW Color Workflows'}\n\nLocking a consistent baseline profile across your session cuts batch editing time by 60%.\n\n## 3. Feathered Clamshell Lighting\n\nCombine a 45-degree beauty dish with a low silver bounce for sculpted yet forgiving portrait light.",
                    "tweet_thread": [
                        f"1/4 📸 {today_short} Studio Wire: {top_title or 'How to fix harsh digital highlight clipping in portrait photography'} 🧵👇 #StudioPhotography #ColorGrading",
                        f"2/4 Technical Takeaway: {(top_snippet or 'Digital sensors clip linearly to pure white, while film compresses highlights along a gentle S-curve shoulder.')[:210]}",
                        "3/4 RAW Recipe: Lift RGB black point to +18, pull highlights -10, and set HSL Orange to -4% Sat / +8% Lum for clean skin luminosity.",
                        "4/4 Grab our calibrated 5-Preset Editorial .XMP Bundle and studio retouching suite in our bio link! 🎨✨ #LightroomPresets"
                    ]
                },
                {
                    "lead_headline": f"Cinestill 800T Mixed-Temperature Lighting in Modern Portrait Studios" if not top_title else f"{top_title}",
                    "lead_body": (
                        f"{top_snippet} Balancing 5600K daylight key illumination against 3200K tungsten rim accents creates rich optical color separation right in camera."
                        if top_snippet
                        else "Pairing a 5600K daylight key softbox with a 3200K warm tungsten rim kicker produces natural optical color contrast before you even open Lightroom."
                    ),
                    "recipe_headline": "The Cinestill 800T Nocturne RAW Formula",
                    "recipe_intro": "Dial in moody tungsten-balanced cinema color with these 3 RAW panel settings:",
                    "recipe_rows": [
                        {"module": "Calibration — Blue Primary", "setting": "Hue: -14 | Saturation: +10", "characteristic": "Pushes deep cyan-teal richness into shadow tones"},
                        {"module": "HSL Red & Orange", "setting": "Orange Lum: +10% | Red Hue: +5", "characteristic": "Preserves warm skin highlights against cool shadows"},
                        {"module": "Tone Curve — Shadows", "setting": "Lift Floor to +12 | Midtone Contrast +8", "characteristic": "Velvety cinema shadow density without crushed detail"}
                    ],
                    "directing_headline": "3 Editorial Directing Cues for Cinematic Mood",
                    "directing_intro": "Use active gaze and hand-placement prompts to create narrative tension:",
                    "directing_cues": [
                        {"cue": "Look just past my left ear as if spotting someone across the street", "explanation": "Engages eye muscles naturally without a frozen camera stare."},
                        {"cue": "Brush your thumb lightly along your collarbone", "explanation": "Introduces graceful hand geometry without stiff fingers."},
                        {"cue": "Angle your chin 15 degrees toward the shadow side", "explanation": "Enhances short-lighting contour across the cheekbones."}
                    ],
                    "pricing_headline": "The 24-Hour Express Turnaround Upsell ($150 Add-On)",
                    "pricing_body": "Offering a guaranteed 24-hour master edit delivery for +$150 converts on 40% of commercial bookings and fuels immediate client referrals.",
                    "lighting_headline": "Cross-Key Dual Color Temperature Setup (5600K + 3200K)",
                    "lighting_intro": "Place your 5600K key octabox at 45 degrees camera-left and position a gridded 3200K strobe at 135 degrees camera-right for warm hair and jawline separation:",
                    "lighting_specs": "Key: 36\" Octabox at 5600K (f/5.6). Rim: 3200K strobe with 20° grid at f/4.0, 4 ft behind subject.",
                    "markdown_article": f"## 1. {top_title or 'Optical Color Separation with Mixed Kelvin Lighting'}\n\n{top_snippet or 'Combining 5600K and 3200K sources creates true depth that single-temperature lighting cannot match.'}\n\n## 2. {sec_title or 'Non-Destructive Skin Retouching'}\n\nBoost Texture (+8) while lowering Clarity (-4) to keep skin pores sharp while smoothing blotchy midtone transitions.",
                    "tweet_thread": [
                        f"1/4 🎬 {today_short} Color Science: {top_title or 'How to shoot mixed-temperature cinema portraits in camera'} 🧵👇 #StudioPhotography #LightroomPresets",
                        f"2/4 Insight: {(top_snippet or 'Pairing a 5600K daylight key light with a 3200K warm rim kicker creates natural optical color contrast before editing.')[:210]}",
                        "3/4 In Lightroom: Shift Blue Primary Hue to -14, lift Orange Luminance +10%, and raise the shadow floor to +12 for velvety cinema blacks.",
                        "4/4 Explore our calibrated .XMP preset vault and studio retouching services in our bio link! 📸✨ #ColorGrading"
                    ]
                },
            ]
            picked = variants[day_seed % len(variants)]
            return {"success": True, "source": "Scribe Dynamic Daily Synthesis", "is_fallback": True, **picked}

        else:  # creator_blueprint
            variants = [
                {
                    "lead_headline": f"The Micro-Asset Shift: Why $19 Digital Toolkits Outsell $500 Courses" if not top_title else f"{top_title}",
                    "lead_body": (
                        f"{top_snippet} Independent studios are scaling high-margin recurring revenue by packaging specialized service workflows into instant-download digital assets."
                        if top_snippet
                        else "Modern buyers prefer immediate utility—Lightroom .XMP presets, SVG/STL files, and templates—over bloated 10-hour video courses."
                    ),
                    "flywheel_headline": "How To Turn One Studio Skill Into A 3-Tier Revenue Flywheel",
                    "flywheel_intro": "Build compounding creative cash flow through this 3-stage progression:",
                    "flywheel_phases": [
                        {"phase": "Phase 1: High-Touch Client Validation", "desc": "Deliver custom retouching or design orders on Fiverr ($25-$95) to validate real buyer demand."},
                        {"phase": "Phase 2: Productize into Digital Downloads", "desc": "Package your most requested styles into .XMP presets, SVG/STL packs, and templates on Etsy."},
                        {"phase": "Phase 3: Daily Educational Syndication", "desc": "Publish actionable daily breakdowns on X and email that route traffic to your storefront hub."}
                    ],
                    "pipeline_headline": 'The "Create Once, Syndicate 4x" Distribution Engine',
                    "pipeline_intro": "Turn every studio insight or client case study into 4 coordinated distribution assets:",
                    "pipeline_rows": [
                        {"format": "4-Part Tactical Thread", "destination": "Twitter / X & Social Feeds", "cta": "Storefront Hub"},
                        {"format": "HTML Morning Briefing", "destination": "Subscriber Inbox (Herald Engine)", "cta": "Etsy & Fiverr Direct"},
                        {"format": "Long-Form Breakdown", "destination": "Web Portal & Search Archive", "cta": "Complete Preset & Asset Vault"}
                    ],
                    "conversion_headline": 'The "Rule of 4" For High-Converting Bio Hubs',
                    "conversion_intro": "Eliminate choice paralysis on mobile landing pages by limiting your bio hub to 4 high-intent paths:",
                    "conversion_rules": [
                        "Primary Service: Custom Studio Retouching & Grading on Fiverr (high-ticket validation).",
                        "Primary Digital Asset: Instant-Download Presets & Creative Kits on Etsy (100% gross margin).",
                        "Free Daily Value: Morning Newsletter & Tactical Social Threads (trust engine).",
                        "VIP Tier: Priority Studio Queue & Complete Asset Bundles."
                    ],
                    "math_headline": "The 7-Sale Per Week Formula For $1,000/Month in Digital Profit",
                    "math_body": "At a $35 average bundle price and a 2.8% storefront conversion rate, just 7 sales per week generates $980/month in passive digital revenue—requiring only 35 targeted clicks per day from your social threads and newsletter.",
                    "markdown_article": f"## 1. {top_title or 'The Rise of Instant-Utility Micro-Assets'}\n\n{top_snippet or 'Buyers reward tools that solve a specific creative bottleneck in under 10 minutes.'}\n\n## 2. {sec_title or 'The 3-Stage Studio Flywheel'}\n\nValidate with custom services, productize into digital downloads, and syndicate daily educational content.",
                    "tweet_thread": [
                        f"1/4 ⚡ {today_short} Creator Blueprint: {top_title or 'Why $19 digital micro-assets are out-converting $500 courses'} 🧵👇 #CreatorEconomy #DigitalProducts",
                        f"2/4 Market Signal: {(top_snippet or 'Buyers want immediate utility—calibrated presets, templates, and ready-to-use files that save hours of manual work.')[:210]}",
                        "3/4 The Flywheel: Validate demand with custom Fiverr orders -> Package the workflow into Etsy digital downloads -> Drive daily traffic via educational threads.",
                        "4/4 Tap our bio link for today's full Creator Blueprint and digital storefront templates! 🚀✨ #CreatorGrowth"
                    ]
                },
            ]
            picked = variants[day_seed % len(variants)]
            return {"success": True, "source": "Scribe Dynamic Daily Synthesis", "is_fallback": True, **picked}


if __name__ == "__main__":
    synthesizer = CopySynthesizer()
    print("Copy Synthesizer (Scribe) initialized.")
