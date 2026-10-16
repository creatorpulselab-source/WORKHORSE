from shared.atomic_writer import atomic_write_json, safe_read_json
"""
WORKHORSE CIPHER: MARKET SCOUT & REAL-TIME TREND INTELLIGENCE AGENT
Autonomous daily web research, URL scraping, and dynamic content synthesis
for @TheCreatorAsset & @creatorpulselab tweets and daily newsletters.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

sys.path.insert(0, "F:/WORKHORSE")
from shared.ai_providers import AIProviderService

VAULT_FILE = Path("F:/WORKHORSE/workspace/daily_trends_vault.json")
OPPORTUNITIES_VAULT = Path("F:/WORKHORSE/workspace/market_opportunities_vault.json")
CACHE_DIR = Path("F:/WORKHORSE/workspace/research_vault")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)


class TextExtractor(HTMLParser):
    """Robust HTML text stripper for web articles, blogs, and news."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_ignored = False
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header", "noscript", "aside", "form"):
            self.in_ignored = True
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "noscript", "aside", "form"):
            self.in_ignored = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif not self.in_ignored:
            cleaned = data.strip()
            if cleaned and len(cleaned) > 2:
                self.text.append(cleaned)


class TrendResearchAgent:
    """Cipher: Market Scout & Creator Trend Intelligence Agent."""
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.config_path = Path(config_path)
        self.ai = AIProviderService(str(self.config_path))
        self.cache_dir = CACHE_DIR
        self.vault_file = VAULT_FILE

    def search_live_trends(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Fast, zero-rate-limit Google News RSS search for breaking creator economy,
        photography, and monetization news.
        """
        encoded = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        results = []
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                root = ET.fromstring(resp.read())
                items = root.findall(".//item")
                import html as _html
                cur_month = date.today().month
                for it in items:
                    if len(results) >= max_results:
                        break
                    title = _html.unescape(it.find("title").text).strip() if it.find("title") is not None and it.find("title").text else ""
                    link = it.find("link").text if it.find("link") is not None else ""
                    pub = it.find("pubDate").text if it.find("pubDate") is not None else ""
                    desc = it.find("description").text if it.find("description") is not None else ""
                    # Filter off-season holiday noise (e.g., Valentine's Day in October)
                    if cur_month not in (1, 2) and "valentine" in title.lower():
                        continue
                    # Strip any HTML tags from RSS description to extract readable snippet
                    clean_desc = _html.unescape(re.sub(r"<[^>]+>", "", desc)).replace("\xa0", " ").strip() if desc else ""
                    clean_title = title.split(" - ")[0].strip() if " - " in title else title
                    if clean_desc.startswith(clean_title):
                        clean_desc = clean_desc[len(clean_title):].strip(" -–—")
                    results.append({
                        "title": clean_title,
                        "snippet": clean_desc or clean_title,
                        "url": link,
                        "published": pub,
                        "raw_title": title
                    })
        except Exception as e:
            print(f"[TrendAgent] Search error for '{query}': {e}")
        return results

    def fetch_url_content(self, url: str) -> Dict[str, Any]:
        """Scrapes web page text and title, stripping out boilerplate."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                parser = TextExtractor()
                parser.feed(html)
                title = parser.title.strip() or "Untitled Web Resource"
                body = " ".join(parser.text[:450])
                return {
                    "status": "ok",
                    "title": title,
                    "url": url,
                    "text": body[:4000]
                }
        except Exception as e:
            return {
                "status": "error",
                "title": "Error Fetching Link",
                "url": url,
                "text": f"Could not retrieve webpage content: {e}"
            }

    def ingest_user_link(self, url: str, user_notes: str = "") -> Dict[str, Any]:
        """
        User drops a link into Synapse.
        Synapse scrapes the page, extracts key insights, and automatically generates:
          1. Core Takeaways
          2. Twitter Thread draft for @TheCreatorAsset
          3. Twitter Thread draft for @creatorpulselab
          4. Newsletter Section Feature
        Saves into daily_trends_vault.json.
        """
        print(f"[TrendAgent] Ingesting dropped link: {url}")
        content = self.fetch_url_content(url)
        if content.get("status") == "error":
            return {
                "success": False,
                "message": content.get("text"),
                "url": url
            }

        title = content.get("title", "")
        text = content.get("text", "")

        prompt = f"""You are SYNAPSE [100 Fm], Master AI Operator for Creator Media Lab.
A human operator dropped this interesting web link into the Studio Vault:

URL: {url}
TITLE: {title}
USER NOTES: {user_notes or 'None'}
ARTICLE EXCERPT:
{text[:2500]}

Analyze this article and output a high-impact JSON payload with:
1. "summary": A crisp 2-sentence summary of the core thesis.
2. "takeaways": Exactly 3 tactical, punchy bullet points.
3. "tweet_thread_creator_asset": A 3-tweet educational thread for @TheCreatorAsset (focusing on photography, color grading, media flywheel, or creative workflow).
4. "tweet_thread_creator_pulse": A 3-tweet tactical thread for @creatorpulselab (focusing on creator earnings, subscriber retention, PPV strategies, or cam tech).
5. "newsletter_blurb": A 120-word deep-dive paragraph ready to insert into today's newsletter.

Respond ONLY with valid JSON.
"""
        system_prompt = "You are an elite creator monetization, photography, and digital product strategist. Output valid JSON only."

        try:
            raw_response = self.ai.call_ollama_text(prompt, system_prompt=system_prompt)
            # Clean JSON markdown fences
            clean_json = raw_response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            parsed = json.loads(clean_json)
        except Exception as e:
            # Fallback heuristic if local model returned non-JSON
            parsed = {
                "summary": f"Analyzed article: {title}",
                "takeaways": [
                    "High relevance to creator monetization and workflow optimization.",
                    "Provides actionable strategies for modern content creators.",
                    "Directly applicable to our studio and subscriber base."
                ],
                "tweet_thread_creator_asset": [
                    f"1/3 📸 Deep dive from today's studio research: {title} 🧵👇 @TheCreatorAsset",
                    f"2/3 The biggest takeaway for photographers and editors: Work smarter with automated presets and structured workflows.\n\nRead full: {url}",
                    "3/3 Get our full studio presets and workflow teardown in our bio link. 🎨✨"
                ],
                "tweet_thread_creator_pulse": [
                    f"1/3 💋 What top creators are doing differently this week based on {title} 🧵👇 @creatorpulselab",
                    f"2/3 If you want to increase your average tip volume and subscriber retention, focus on personalizing your VIP rewards.\n\nLink: {url}",
                    "3/3 Tap our bio for daily creator formulas and uncensored tip menu templates. 💎🔥"
                ],
                "newsletter_blurb": f"In today's feature breakdown, we examine {title}. The key finding highlights how creators who proactively systematize their asset delivery and subscriber communication outperform average accounts by over 35%."
            }

        ingest_record = {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "url": url,
            "title": title,
            "user_notes": user_notes,
            "synthesis": parsed
        }

        # Update Vault
        vault = self.load_vault()
        vault.setdefault("user_curated_links", []).insert(0, ingest_record)
        # Keep latest 30 links
        vault["user_curated_links"] = vault["user_curated_links"][:30]
        vault["last_updated"] = datetime.now().isoformat()
        self.save_vault(vault)

        return {
            "success": True,
            "title": title,
            "url": url,
            "ingest_record": ingest_record
        }

    def run_daily_radar_sweep(self) -> Dict[str, Any]:
        """
        Runs an autonomous morning web search across photography and creator monetization,
        synthesizes fresh daily topics, and generates today's 5-slot tweets and newsletter briefs.
        """
        print("[TrendAgent] Running autonomous daily trend radar sweep...")
        today_str = date.today().isoformat()

        # 1. Gather live news for Niche A (Photography & Studio)
        photo_queries = [
            "Lightroom photography presets editing trends 2026",
            "Professional studio photography lighting posing tips"
        ]
        photo_articles = []
        for q in photo_queries:
            photo_articles.extend(self.search_live_trends(q, max_results=3))

        # 2. Gather live news for Niche B (Digital Creators & Monetization - 100% SFW)
        creator_queries = [
            "digital creator monetization strategies revenue trends 2026",
            "creator economy newsletter podcast subscriber growth tactics"
        ]
        creator_articles = []
        for q in creator_queries:
            creator_articles.extend(self.search_live_trends(q, max_results=3))

        # 3. Gather live news for Niche C (Digital Business / Media Automation - powers
        # The Creator Blueprint newsletter's sections, which previously had no real
        # research grounding at all)
        business_queries = [
            "digital creator business automation tools 2026",
            "passive income digital products side hustle trends"
        ]
        business_articles = []
        for q in business_queries:
            business_articles.extend(self.search_live_trends(q, max_results=3))

        # 4. Build synthesis prompt with article summaries & strict editorial rules
        photo_summary = [{"title": a["title"], "summary": a.get("snippet", "")} for a in photo_articles]
        creator_summary = [{"title": a["title"], "summary": a.get("snippet", "")} for a in creator_articles]

        prompt = f"""You are SYNAPSE [100 Fm] & HERALD [33 As], Expert Social Media Director & Editor for Creator Media Lab.
Today is {today_str}. Here are verified breaking articles discovered in our daily radar:

PHOTOGRAPHY & STUDIO NEWS (with article summaries):
{json.dumps(photo_summary, indent=2)}

CREATOR ECONOMY & MONETIZATION NEWS (with article summaries):
{json.dumps(creator_summary, indent=2)}

STRICT EDITORIAL RULES (CRITICAL):
1. NO UNANSWERED QUESTIONS / CLIFFHANGERS: If you pose a question (e.g. "Which platform pays the most in 2026?"), you MUST provide the direct answer, comparison numbers, and takeaway in that tweet/thread.
2. NO PHANTOM LISTS: NEVER write "Top 5" or "Top 7" or "3 secrets" unless you explicitly list every single item/name/step directly in the tweet strings.
3. STANDALONE ACTIONABLE VALUE: Every post must give concrete value: exact slider settings, proven script quotes, payout breakdown percentages, or specific posing cues.
4. EXPERT TONE: High-authority, concise, native to X/Twitter (under 280 chars per tweet, threads formatted 1/N, 2/N, etc.).
5. STRATEGIC HASHTAGS: Every standalone tweet and the final closing tweet of every thread MUST include 2 to 3 targeted, high-exposure niche hashtags (#CreatorEconomy #CreatorGrowth #Monetization #ContentStrategy #DigitalProducts for @creatorpulselab; #StudioPhotography #LightroomPresets #ColorGrading for @TheCreatorAsset) to maximize search discoverability and algorithmic reach.
6. STRICT 100% SFW ENFORCEMENT (NON-NEGOTIABLE): All content across BOTH @TheCreatorAsset AND @creatorpulselab MUST be 100% Safe For Work (SFW). Absolutely NO adult content, nudity, boudoir, lingerie, sex work, OnlyFans, Fansly, cam/webcam streaming, sextortion, or suggestive themes. All external content published across all platforms must be 100% professional and SFW.

Generate today's dynamic content drop payload in valid JSON with:
1. "top_themes_today": Exactly 3 high-impact industry themes for today.
2. "daily_slots": A dictionary with keys "slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight".
   For EACH slot, provide:
   - "creatorpulselab": List of 2 to 4 tweet strings for @creatorpulselab (Creator Business, Monetization Systems, Audience Growth, Digital Products).
   - "TheCreatorAsset": List of 2 to 4 tweet strings for @TheCreatorAsset (Studio Photographers, Color Grading, Presets).
3. "newsletter_topics":
   - "creator_pulse": A punchy topic title & 2-sentence teaser for today's creator newsletter.
   - "creator_asset": A punchy topic title & 2-sentence teaser for today's photography digest.

Respond ONLY with valid JSON.
"""
        system_prompt = "You are an expert social media and newsletter director for creator brands. Return valid JSON only. All content must be 100% SFW."

        try:
            synth = None
            last_error = None
            # Retry the LLM synthesis call before giving up - a single transient Ollama
            # hiccup or malformed-JSON response used to immediately drop to the static
            # fallback (which only covers slot_1_morning), silently leaving slots 2-5 on
            # repeated static content for the rest of the day.
            for attempt in range(2):
                try:
                    raw = self.ai.call_ollama_text(prompt, system_prompt=system_prompt)
                    clean = raw.strip()
                    if clean.startswith("```json"):
                        clean = clean[7:]
                    if clean.startswith("```"):
                        clean = clean[3:]
                    if clean.endswith("```"):
                        clean = clean[:-3]
                    clean = clean.strip()
                    parsed = json.loads(clean)
                    EXPECTED_SLOTS = {"slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight"}
                    got_slots = set(parsed.get("daily_slots", {}).keys())
                    if not EXPECTED_SLOTS.issubset(got_slots):
                        raise ValueError(f"LLM returned incomplete daily_slots (got {sorted(got_slots)}, need all 5)")
                    synth = parsed
                    synth["used_fallback"] = False
                    break
                except Exception as inner_e:
                    last_error = inner_e
                    print(f"[TrendAgent] Synthesis attempt {attempt + 1}/2 failed: {inner_e}")
            if synth is None:
                raise last_error
        except Exception as e:
            print(f"[TrendAgent] LLM synthesis fallback due to: {e}")
            synth = {
                "used_fallback": True,
                "top_themes_today": [
                    "AI-Assisted Workflow & Faster Turnarounds in Studio Photography",
                    "Subscriber Retention Formulas & Digital Asset Storefronts",
                    "Automated Multi-Channel Distribution & Creator Media Flywheels"
                ],
                "daily_slots": {
                    "slot_1_morning": {
                        "creatorpulselab": [
                            f"1/4 ⚡ 3 digital product offer structures that converted 20%+ higher this week for independent creators 🧵👇 @creatorpulselab #CreatorEconomy #Monetization",
                            "2/4 Structure 1: The 'Micro-Asset' Entry Point.\n\nDon't launch a $300 course first. Launch a $19 actionable template or preset bundle that solves one painful bottleneck in under 10 minutes.",
                            "3/4 Structure 2: The 3-Tier Value Ladder.\n\nTier 1 ($19): Core template.\nTier 2 ($49): Template + video walkthrough + raw asset project files.\nTier 3 ($149): All templates + 1-on-1 async review.",
                            "4/4 Structure 3: The Educational Email Engine.\n\nDeliver free tactical value 5 days a week, with a frictionless checkout link at the bottom. Check our bio for today's full monetization breakdown! 📈✨ #CreatorGrowth"
                        ],
                        "TheCreatorAsset": [
                            f"1/4 📸 Why top editorial photographers spend 15 minutes color grading instead of 4 hours 🧵👇 @TheCreatorAsset #StudioPhotography #ColorGrading",
                            "2/4 The secret of commercial studios: Consistency over perfection.\n\nLock in 1 baseline curve, 1 split-tone anchor, and apply it in batches of 100 across the session.",
                            "3/4 Master the Tone Curve: Drop shadows slightly (-4), lift black point to +6 for a clean matte floor, and warm highlights to +3 for luminous skin values.",
                            "4/4 Stop wasting evenings in Lightroom. Explore our calibrated Studio Portrait Presets (.XMP) and full editorial suite in our bio link. 🎨✨ #LightroomPresets"
                        ]
                    }
                },
                "newsletter_topics": {
                    "creator_pulse": {
                        "title": "The Digital Asset Storefront Blueprint: 3 Structures That Maximize Creator Revenue",
                        "teaser": "How modern creators build repeatable, high-margin revenue with automated digital products and structured email value loops."
                    },
                    "creator_asset": {
                        "title": "Mastering the Studio Tone Curve: Clean Editorial Skin Tones in Minutes",
                        "teaser": "Eliminate digital color cast in studio portraits using calibrated .XMP curves and HSL split toning."
                    }
                }
            }

        # SFW Sanitation Gate on all synthesized tweets
        blocked_sfw_tokens = [
            "boudoir", "nude", "naked", "nsfw", "topless", "lingerie", "underwear",
            "bra", "panties", "porn", "explicit", "erotic", "bikini", "swimwear",
            "sheer", "provocative", "seductive", "charlette", "margo", "melissa",
            "onlyfans", "fansly", "chaturbate", "myfreecams", "mfc", "camgirl", "cam girl",
            "webcam", "sextortion", "sex work", "xxx", "banned angle", "uncensored"
        ]
        slots = synth.get("daily_slots", {})
        for slot_k, slot_val in slots.items():
            if isinstance(slot_val, dict):
                for hdl, tw_list in slot_val.items():
                    if isinstance(tw_list, list):
                        clean_list = []
                        for tw in tw_list:
                            tw_str = re.sub(r"\*\*|__", "", str(tw)).strip()
                            if any(b in tw_str.lower() for b in blocked_sfw_tokens):
                                print(f"[TrendAgent Safety Alert] Purged non-SFW tweet from synthesized {slot_k} for @{hdl}: {tw_str[:50]}...")
                                continue
                            clean_list.append(tw_str)
                        if clean_list:
                            slot_val[hdl] = clean_list

        vault = self.load_vault()
        vault["today_date"] = today_str
        vault["last_radar_sweep"] = datetime.now().isoformat()
        vault["photo_articles"] = photo_articles
        vault["creator_articles"] = creator_articles
        vault["business_articles"] = business_articles
        vault["daily_synthesis"] = synth
        self.save_vault(vault)

        print(f"[TrendAgent] Daily radar sweep complete! Saved to {self.vault_file}")
        return vault

    def get_research_articles_for_pub(self, pub_id: str) -> List[Dict[str, str]]:
        """Returns today's real researched article headlines relevant to one
        publication, so its daily editorial content can be grounded in actual current
        news instead of pure free-form AI invention. Returns an empty list (never
        raises) if the vault is stale/missing/doesn't cover this publication's niche."""
        vault = self.load_vault()
        if vault.get("today_date") != date.today().isoformat():
            return []
        mapping = {
            "creator_pulse": "creator_articles",
            "studio_wire": "photo_articles",
            "creator_blueprint": "business_articles",
        }
        key = mapping.get(pub_id)
        return vault.get(key, []) if key else []

    def load_vault(self) -> Dict[str, Any]:
        """Loads daily trends vault JSON from disk."""
        if self.vault_file.exists():
            try:
                with open(self.vault_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "today_date": date.today().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "user_curated_links": [],
            "daily_synthesis": {}
        }

    def save_vault(self, data: Dict[str, Any]):
        """Persists daily trends vault JSON to disk."""
        try:
            with open(self.vault_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TrendAgent] Error saving vault: {e}")

    def get_static_trend_matrix(self) -> Dict[str, Any]:
        """Comprehensive foundational market intelligence matrix."""
        return {
            "photo_retouching": {
                "title": "📸 Photo Shoot & Retouching Trends",
                "aesthetic_trends": [
                    {"name": "Warm Chocolate Boudoir", "vibe": "Moody shadows, warm skin undertones, velvety blacks."},
                    {"name": "Golden Hour Glow", "vibe": "Amber rim lighting, sun-kissed luminous skin."},
                    {"name": "Cyber Neon Noir", "vibe": "Deep cyan and magenta contrast, futuristic editorial."},
                    {"name": "35mm Analog Film Grain", "vibe": "Subtle organic grain, muted greens, nostalgic warmth."}
                ]
            },
            "creator_monetization": {
                "title": "💎 Live Cam & Creator Monetization Trends",
                "token_pricing_sweet_spots": [
                    {"tier": "Micro-Tips (15-35 tks)", "purpose": "Low barrier activation."},
                    {"tier": "Core Actions (50-150 tks)", "purpose": "High volume stream revenue."},
                    {"tier": "Show Teasers (250-500 tks)", "purpose": "Milestone rewards."},
                    {"tier": "VIP / Whale Tiers (1000-2500 tks)", "purpose": "High margin unlocks."}
                ]
            }
        }

    def get_daily_summary_prompt_context(self) -> str:
        """
        Returns a compact, high-signal markdown summary of today's market trends,
        newsletter topics, and user-curated links for prompt context injection.
        """
        vault = self.load_vault()
        today = vault.get("today_date", str(date.today()))
        daily_synth = vault.get("daily_synthesis", {})
        themes = daily_synth.get("top_themes_today", [])
        nl_topics = daily_synth.get("newsletter_topics", {})
        links = vault.get("user_curated_links", [])

        lines = [f"### [DAILY MARKET RADAR & TOPIC VAULT - {today}]"]
        if themes:
            lines.append("TOP TRENDING THEMES TODAY:")
            for t in themes:
                lines.append(f"- {t}")

        if nl_topics:
            lines.append("DAILY NEWSLETTER ANGLES:")
            cp = nl_topics.get("creator_pulse", {})
            ca = nl_topics.get("creator_asset", {})
            if cp:
                lines.append(f"- Adult Creator Pulse: {cp.get('title', '')} ('{cp.get('teaser', '')}')")
            if ca:
                lines.append(f"- Shutter & Studio Wire: {ca.get('title', '')} ('{ca.get('teaser', '')}')")

        if links:
            lines.append(f"RECENT USER-CURATED LINKS INGESTED ({len(links)} total):")
            for item in links[:4]:
                s = item.get("synthesis", {})
                title = item.get("title", "Resource")
                url = item.get("url", "")
                summary = s.get("summary", "")
                lines.append(f"- [{title}]({url}): {summary}")

        lines.append("### [END MARKET RADAR]")
        return "\n".join(lines)

    def scout_market_and_revenue_ideas(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Autonomous Market Scout & Revenue Strategist (Cipher [36 Cp] & Mercury [80 Hg]):
        Scouts live web trends, high-ticket automated digital services, and viral creator
        growth loops. Synthesizes concrete automated money-making ideas with pricing models,
        execution blueprints, and WORKHORSE bot automation mappings.
        """
        today_str = date.today().isoformat()
        if not force_refresh and OPPORTUNITIES_VAULT.exists():
            try:
                data = safe_read_json(OPPORTUNITIES_VAULT, default={})
                if data and data.get("date") == today_str and data.get("opportunities"):
                    return data
            except Exception:
                pass

        print("[Cipher Market Scout] Scouting live web for automated revenue opportunities and marketing strategies...")

        queries = [
            "trending high ticket digital products fiverr etsy 2026",
            "automated AI agency services video photo retainer 2026",
            "viral creator marketing growth loops organic monetization 2026",
            "best selling digital assets templates presets passive income 2026"
        ]

        live_articles = []
        for q in queries:
            try:
                live_articles.extend(self.search_live_trends(q, max_results=3))
            except Exception as e:
                print(f"[Cipher Market Scout] Query warning for '{q}': {e}")

        articles_summary = [{"title": a["title"], "snippet": a.get("snippet", "")} for a in live_articles]

        prompt = f"""You are CIPHER [36 Cp] (Market Scout & Trend Intelligence) and MERCURY [80 Hg] (Omni-Channel Marketing Maestro & Service Strategist).
Today is {today_str}. Here are verified live search signals on market demand, digital products, and creator monetization:
{json.dumps(articles_summary, indent=2)}

Synthesize 4 concrete, highly profitable, automated money-making and marketing opportunities that WORKHORSE can build, market, and execute.
WORKHORSE hardware & software capabilities:
- Dual NVIDIA RTX 3060 (24GB VRAM) & RTX 5070 Ti (16GB VRAM)
- ComfyUI LTX 2.3 & Wan 2.1 (photo-to-video, dynamic camera motion)
- NVENC 60fps hardware video encoder (Forge)
- Editorial frequency separation & DaVinci film color grading (Aura)
- 3D photogrammetry & turntable spinning GLB/PBR generation
- Automated Dropzone packaging & ZIP delivery (Apex)
- Etsy Digital Store & Fiverr Service Bot integrations
- Automated email newsletter dispatch & Twitter/Pinterest marketing (Herald)

Return a valid JSON object with:
"opportunities": A list of 4 items. Each item must have:
- "id": string slug (e.g. "fiverr_ai_photo_to_video", "etsy_cinematic_lut_vault")
- "title": Catchy, high-converting commercial title
- "platform": "Fiverr" | "Etsy" | "Direct Storefront" | "Social Funnel"
- "category": "Automated Service" | "Digital Product Pack" | "Viral Growth Loop" | "High-Ticket Retainer"
- "potential_revenue": Pricing & revenue model (e.g. "$45-$120 per automated order", "$19-$49 instant passive download")
- "market_trend": Why buyers are actively looking for this right now based on live trends
- "workhorse_automation": Which WORKHORSE agents fulfill it automatically and how
- "marketing_hook": A viral hook or buyer pitch to attract orders
- "action_steps": List of 3 concrete next steps to launch it today

Respond ONLY with valid JSON.
"""
        system_prompt = "You are a world-class creator economy strategist and autonomous revenue scout. Return valid JSON only. All ideas must be 100% SFW and automated."

        opportunities = []
        try:
            raw = self.ai.call_ollama_text(prompt, system_prompt=system_prompt)
            clean = raw.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            clean = clean.strip()
            parsed = json.loads(clean)
            opportunities = parsed.get("opportunities", [])
        except Exception as e:
            print(f"[Cipher Market Scout] LLM synthesis note ({e}), using curated high-yield opportunity models.")

        if not opportunities:
            opportunities = [
                {
                    "id": "fiverr_dynamic_video_motion",
                    "title": "🎬 4K 60fps AI Photo-to-Video & Dynamic Motion Teasers",
                    "platform": "Fiverr",
                    "category": "Automated Service",
                    "potential_revenue": "$45 – $120 per client delivery",
                    "market_trend": "Creators and e-commerce brands desperately need vertical video reels and moving product teasers from static photos without paying $1,000+ for film crews.",
                    "workhorse_automation": "Synapse & ComfyUI (LTX 2.3 on RTX 5070 Ti) generate cinematic motion in 40s; Forge encodes NVENC 60fps; Apex auto-delivers via Dropzone.",
                    "marketing_hook": "Stop posting dead photos. Watch static images come alive with cinematic camera motion in 24 hours.",
                    "action_steps": [
                        "Activate gig_photo_to_video showcase preview on Fiverr profile",
                        "Post 15s before/after split-screen reel to @TheCreatorAsset with order link",
                        "Drop incoming client photos into F:\\WORKHORSE\\dropzone for zero-touch delivery"
                    ]
                },
                {
                    "id": "etsy_film_emulation_lut_pack",
                    "title": "📦 Master Kodak Portra & Cinestill Editorial Preset & LUT Vault",
                    "platform": "Etsy",
                    "category": "Digital Product Pack",
                    "potential_revenue": "$19 – $47 per sale (100% passive digital delivery)",
                    "market_trend": "Vintage analog film aesthetics (Portra 400, Cinestill 800T, Fuji 400H) have 280%+ YoY search demand among mobile creators and wedding photographers.",
                    "workhorse_automation": "Aura exports .XMP/.CUBE presets; Scribe writes high-converting Etsy listing copy; Apex packages ZIP with PDF installation guides.",
                    "marketing_hook": "The exact film color curves used in $5,000 fashion shoots — one click in Lightroom & Premiere.",
                    "action_steps": [
                        "Review auto-bundled ZIP in F:\\WORKHORSE\\workspace\\etsy_bundles",
                        "Publish generated listing title and 13 search tags to Etsy shop",
                        "Let Gumroad / Etsy deliver instant digital download automatically"
                    ]
                },
                {
                    "id": "fiverr_3d_product_turntable",
                    "title": "🧊 Interactive 3D Product Turntables & AR Photogrammetry",
                    "platform": "Fiverr",
                    "category": "Automated Service",
                    "potential_revenue": "$60 – $150 per product model",
                    "market_trend": "Shopify and Amazon sellers are rapidly adopting interactive 3D and GLB models; 3D listings show a 44% higher conversion rate than 2D photos.",
                    "workhorse_automation": "ComfyUI on Main PC synthesizes 3D PBR meshes; Forge packages 360 turntable video; Dropzone fulfills GLB model and HTML preview.",
                    "marketing_hook": "Transform flat product photography into interactive 3D models for Shopify & Amazon in 24 hours.",
                    "action_steps": [
                        "Offer 3D turntable add-on to existing retouching clients",
                        "Showcase interactive GLB viewer in portfolio",
                        "Process incoming multi-angle shots directly through WORKHORSE 3D pipeline"
                    ]
                },
                {
                    "id": "creator_micro_asset_flywheel",
                    "title": "📱 Micro-Asset Value Ladder & Daily Educational Email Funnel",
                    "platform": "Direct Storefront",
                    "category": "Viral Growth Loop",
                    "potential_revenue": "$19 Entry -> $49 Pro -> $149 VIP Retainer ($2,400+/mo MRR)",
                    "market_trend": "Creators buying $300+ courses has cratered by 60%; fast-action $19 templates backed by daily tactical newsletters convert at over 22%.",
                    "workhorse_automation": "Herald delivers daily educational newsletter at 08:30; Scribe includes frictionless bottom-of-email checkout link; Radar monitors Stripe/Gumroad sales.",
                    "marketing_hook": "One actionable system a day. Solve a bottleneck in 10 minutes. Level up to full pro assets when ready.",
                    "action_steps": [
                        "Keep Herald's Studio Wire & Creator Pulse daily dispatches running",
                        "Confirm Gumroad/Stripe checkout links on newsletter templates",
                        "Review daily sales notifications on Order Radar"
                    ]
                }
            ]

        vault_data = {
            "date": today_str,
            "scouted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_opportunities": len(opportunities),
            "opportunities": opportunities
        }
        try:
            atomic_write_json(OPPORTUNITIES_VAULT, vault_data)
        except Exception as e:
            print(f"[Cipher Market Scout] Vault save error: {e}")

        return vault_data


# Global singleton
trend_researcher = TrendResearchAgent()
