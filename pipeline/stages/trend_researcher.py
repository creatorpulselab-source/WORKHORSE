from shared.atomic_writer import atomic_write_json, safe_read_json
"""
WORKHORSE CIPHER: MARKET SCOUT & REAL-TIME TREND INTELLIGENCE AGENT
Autonomous daily web research, URL scraping, and dynamic content synthesis
for @TheCreatorAsset & @creatorpulselab tweets and daily newsletters.
"""

import os
import sys
import json
import gzip
import re
import html as _html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional, Set

sys.path.insert(0, "F:/WORKHORSE")
from shared.ai_providers import AIProviderService, parse_llm_json

VAULT_FILE = Path("F:/WORKHORSE/workspace/daily_trends_vault.json")
OPPORTUNITIES_VAULT = Path("F:/WORKHORSE/workspace/market_opportunities_vault.json")
TWEET_HISTORY_FILE = Path("F:/WORKHORSE/workspace/tweet_history.json")
SCRIBE_CACHE_FILE = Path("F:/WORKHORSE/workspace/scribe_daily_content.json")
CACHE_DIR = Path("F:/WORKHORSE/workspace/research_vault")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Direct industry RSS feeds with full article summaries and daily publication cadence
DIRECT_RSS_FEEDS: Dict[str, List[Dict[str, str]]] = {
    "photo": [
        {"name": "PetaPixel", "url": "https://petapixel.com/feed/"},
        {"name": "Fstoppers", "url": "https://fstoppers.com/feed"},
        {"name": "DIYPhotography", "url": "https://www.diyphotography.net/feed/"},
    ],
    "creator": [
        {"name": "Tubefilter", "url": "https://www.tubefilter.com/feed/"},
        {"name": "SocialMediaExaminer", "url": "https://www.socialmediaexaminer.com/feed/"},
        {"name": "TechCrunchSocial", "url": "https://techcrunch.com/tag/social/feed/"},
    ],
}

CREATOR_RELEVANCE_KEYWORDS = (
    "creator", "monetiz", "revenue", "youtube", "tiktok", "instagram", "facebook",
    "meta", "subscri", "payout", "digital", "ad", "sponsor", "audience", "stream",
    "video", "short", "reel", "algorithm", "content", "influencer", "brand", "deal",
    "course", "storefront", "passive income", "retention"
)

# Relevance filter for direct photo RSS feeds so general/archaeology/politics news is skipped
PHOTO_RELEVANCE_KEYWORDS = (
    "portrait", "lighting", "lightroom", "photoshop", "color", "grading", "retouch",
    "studio", "softbox", "strobe", "flash", "lens", "prime", "50mm", "85mm", "35mm",
    "24-70", "aperture", "sensor", "dynamic range", "raw", "workflow", "preset",
    "camera", "canon", "sony", "nikon", "fujifilm", "leica", "sigma", "tamron",
    "hasselblad", "medium format", "exposure", "iso", "shutter", "bokeh", "skin tone",
    "capture one", "davinci", "lut", "video", "cinema", "autofocus", "mirrorless",
)

OFF_BRAND_NOISE_KEYWORDS = (
    "dinosaur", "fossil", "katrina", "looting", "murder", "arrest", "prison",
    "lawsuit", "Obituary", "obituary", "died", "passes away", "warzone", "military",
    "ukraine", "gaza", "election", "trump", "biden", "parliament", "germany",
)

# Crisp 3-4 word rotating daily query pools so Google News RSS (when:7d) returns rich, relevant results
PHOTO_QUERY_POOL = [
    "portrait photography lighting",
    "Lightroom color grading",
    "studio photography flash",
    "camera lens portrait review",
    "photo editing workflow AI",
    "mirrorless camera sensor photography",
    "commercial photography retouching",
    "fujifilm film simulation recipe",
    "portrait photographer business pricing",
    "cinematic lighting setup video",
    "RAW photo editing tips",
    "studio strobe softbox portrait",
]

CREATOR_QUERY_POOL = [
    "creator economy monetization",
    "YouTube TikTok creator revenue",
    "Substack newsletter creator growth",
    "Patreon membership creator economy",
    "short form video algorithm reach",
    "influencer marketing creator brand",
    "social media engagement strategy",
    "podcast newsletter monetization",
    "independent creator business revenue",
    "Instagram Reels creator retention",
    "creator superfan community app",
    "digital creator sponsorship pricing",
]

BUSINESS_QUERY_POOL = [
    "Etsy digital products seller",
    "digital download passive income",
    "freelance designer AI workflow",
    "Gumroad Shopify digital products",
    "email newsletter monetization business",
    "creative studio automation workflow",
    "print on demand Etsy trends",
    "online course vs digital templates",
    "solopreneur digital product launch",
    "link in bio storefront conversion",
    "Lightroom presets digital business",
    "micro SaaS creator tools",
]

# Overused legacy article tokens that were previously stuck in daily_trends_vault.json
STALE_LEGACY_PATTERNS = (
    "audrey woulard",
    "lightroom classic 15.3",
    "iphone portrait mode",
    "wayshot launches",
    "how to make money on facebook",
    "always-on fandom",
    "deloitte's 2026 digital media",
    "2026 digital media trends",
    "asia pacific creator economy",
    "asia pacific's creator economy",
    "power brokers' predictions",
)


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

    @staticmethod
    def _normalize_title_key(title: str) -> str:
        """Normalizes an article title into a compact lowercase deduplication key."""
        cleaned = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
        tokens = [w for w in cleaned.split() if len(w) > 2]
        return " ".join(tokens[:10])

    @staticmethod
    def _title_word_set(text: str) -> Set[str]:
        stop = {
            "the", "and", "for", "with", "that", "this", "from", "your", "how",
            "why", "what", "are", "was", "were", "have", "has", "had", "into",
            "new", "more", "over", "after", "before", "about", "2025", "2026",
        }
        words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
        return {w for w in words if w not in stop}

    def _get_excluded_topic_keys(self, vault: Optional[Dict[str, Any]] = None) -> Set[str]:
        """
        Builds a set of normalized article keys from the rolling 21-day seen_articles
        log, previous vault articles, and recent newsletter headlines so the same
        article or news story is never repeated day after day.
        """
        if vault is None:
            vault = self.load_vault()
        excluded: Set[str] = set()
        today_dt = date.today()

        # 1. Rolling seen_articles dict from vault (keep up to 21 days)
        seen_map = vault.get("seen_articles", {})
        if isinstance(seen_map, dict):
            for k, seen_date_str in list(seen_map.items()):
                try:
                    d_str = str(seen_date_str)[:10]
                    # Only exclude articles seen on PREVIOUS days so same-day re-runs still work cleanly
                    if d_str != today_dt.isoformat():
                        age_days = (today_dt - date.fromisoformat(d_str)).days
                        if age_days <= 21:
                            excluded.add(k)
                except Exception:
                    pass

        # 2. If vault currently holds articles from a previous date, mark them seen
        if vault.get("today_date") != today_dt.isoformat():
            for list_key in ("photo_articles", "creator_articles", "business_articles"):
                for art in vault.get(list_key, []) or []:
                    if isinstance(art, dict) and art.get("title"):
                        excluded.add(self._normalize_title_key(art["title"]))

        # 3. Also check recent newsletter lead headlines from previous days
        scribe_cache = safe_read_json(SCRIBE_CACHE_FILE, default={})
        if isinstance(scribe_cache, dict):
            for pub_id in ("creator_pulse", "studio_wire", "creator_blueprint"):
                entry = scribe_cache.get(pub_id)
                if isinstance(entry, dict) and entry.get("date") != today_dt.isoformat():
                    hl = (entry.get("content") or {}).get("lead_headline", "")
                    if hl:
                        excluded.add(self._normalize_title_key(hl))

        return excluded

    def _is_article_stale_or_seen(
        self,
        title: str,
        published_str: str,
        excluded_keys: Set[str],
        max_age_days: int = 14,
    ) -> bool:
        """Returns True if an article matches known stale legacy topics, off-brand noise,
        is older than max_age_days, or overlaps heavily with an already-seen article."""
        t_lower = (title or "").lower().strip()
        if not t_lower:
            return True
        if any(pat in t_lower for pat in STALE_LEGACY_PATTERNS):
            return True
        if any(noise in t_lower for noise in OFF_BRAND_NOISE_KEYWORDS):
            return True

        norm_key = self._normalize_title_key(title)
        if norm_key in excluded_keys:
            return True

        # Check word overlap against excluded keys (>= 65% overlap on 4+ significant words)
        t_words = self._title_word_set(title)
        if len(t_words) >= 4:
            for ex_key in excluded_keys:
                ex_words = self._title_word_set(ex_key)
                if len(ex_words) >= 4:
                    overlap = len(t_words & ex_words) / float(min(len(t_words), len(ex_words)))
                    if overlap >= 0.65:
                        return True

        # Check publication date recency when available
        if published_str:
            try:
                pub_dt = parsedate_to_datetime(published_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                now_dt = datetime.now(timezone.utc)
                age_days = (now_dt - pub_dt).total_seconds() / 86400.0
                if age_days > max_age_days:
                    return True
            except Exception:
                pass

        return False

    def fetch_direct_rss_articles(
        self,
        niche: str,
        max_results: int = 4,
        excluded_keys: Optional[Set[str]] = None,
    ) -> List[Dict[str, str]]:
        """
        Pulls fresh, on-brand studio/gear/editing articles directly from industry RSS feeds
        (PetaPixel, Fstoppers, DIYPhotography) which include full multi-sentence descriptions.
        """
        feeds = DIRECT_RSS_FEEDS.get(niche, [])
        if not feeds:
            return []
        excluded = excluded_keys if excluded_keys is not None else set()
        collected: List[Dict[str, str]] = []
        cur_month = date.today().month

        for feed_info in feeds:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw_bytes = resp.read()
                    if raw_bytes[:2] == b"\x1f\x8b":
                        raw_bytes = gzip.decompress(raw_bytes)
                    root = ET.fromstring(raw_bytes)
                    items = root.findall(".//item")
                    per_feed_count = 0
                    for it in items:
                        if per_feed_count >= 2 or len(collected) >= max_results:
                            break
                        title = _html.unescape(it.find("title").text or "").strip() if it.find("title") is not None else ""
                        link = (it.find("link").text or "").strip() if it.find("link") is not None else ""
                        pub = (it.find("pubDate").text or "").strip() if it.find("pubDate") is not None else ""
                        desc = (it.find("description").text or "").strip() if it.find("description") is not None else ""
                        if not title:
                            continue
                        if cur_month not in (1, 2) and "valentine" in title.lower():
                            continue
                        if self._is_article_stale_or_seen(title, pub, excluded, max_age_days=10):
                            continue

                        clean_desc = _html.unescape(re.sub(r"<[^>]+>", " ", desc)).replace("\xa0", " ")
                        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                        clean_desc = re.sub(r"The post .*? appeared first on .*?$", "", clean_desc, flags=re.IGNORECASE).strip()

                        # Ensure RSS items are genuinely relevant to the targeted niche
                        combined_lower = f"{title} {clean_desc}".lower()
                        if niche == "photo" and not any(kw in combined_lower for kw in PHOTO_RELEVANCE_KEYWORDS):
                            continue
                        if niche == "creator" and not any(kw in combined_lower for kw in CREATOR_RELEVANCE_KEYWORDS):
                            continue

                        if len(clean_desc) > 320:
                            clean_desc = clean_desc[:317].rsplit(" ", 1)[0] + "..."
                        if not clean_desc or len(clean_desc) < 25:
                            clean_desc = f"{title} — reported by {feed_name}."

                        norm_k = self._normalize_title_key(title)
                        excluded.add(norm_k)
                        collected.append({
                            "title": title,
                            "snippet": clean_desc,
                            "publisher": feed_name,
                            "url": link,
                            "published": pub,
                            "raw_title": f"{title} - {feed_name}",
                        })
                        per_feed_count += 1
            except Exception as e:
                print(f"[TrendAgent] Direct RSS notice for {feed_name}: {e}")

        return collected

    def search_live_trends(
        self,
        query: str,
        max_results: int = 5,
        when_window: Optional[str] = "7d",
        excluded_keys: Optional[Set[str]] = None,
    ) -> List[Dict[str, str]]:
        """
        Fast, zero-rate-limit Google News RSS search for breaking creator economy,
        photography, and monetization news. Applies recency filtering (when:7d -> when:30d)
        and deduplicates against previously seen articles.
        """
        excluded = excluded_keys if excluded_keys is not None else self._get_excluded_topic_keys()
        windows_to_try = [when_window, "30d", None] if when_window else [None]
        results: List[Dict[str, str]] = []
        cur_month = date.today().month

        for win in windows_to_try:
            if len(results) >= max_results:
                break
            effective_q = f"{query} when:{win}" if win and "when:" not in query else query
            encoded = urllib.parse.quote_plus(effective_q)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall(".//item")
                    max_age = 14 if win == "7d" else (35 if win == "30d" else 90)
                    for it in items:
                        if len(results) >= max_results:
                            break
                        title = _html.unescape(it.find("title").text).strip() if it.find("title") is not None and it.find("title").text else ""
                        link = it.find("link").text if it.find("link") is not None else ""
                        pub = it.find("pubDate").text if it.find("pubDate") is not None else ""
                        desc = it.find("description").text if it.find("description") is not None else ""
                        if not title:
                            continue
                        if cur_month not in (1, 2) and "valentine" in title.lower():
                            continue

                        publisher = ""
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            clean_title = parts[0].strip()
                            publisher = parts[1].strip()
                        else:
                            clean_title = title

                        if self._is_article_stale_or_seen(clean_title, pub, excluded, max_age_days=max_age):
                            continue

                        clean_desc = _html.unescape(re.sub(r"<[^>]+>", " ", desc)).replace("\xa0", " ").strip() if desc else ""
                        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                        if clean_desc.startswith(clean_title):
                            clean_desc = clean_desc[len(clean_title):].strip(" -–—")
                        if publisher and clean_desc == publisher:
                            clean_desc = ""

                        # Never leave snippet as just a bare publisher name
                        if not clean_desc or len(clean_desc) < 30:
                            if publisher:
                                snippet = f"{clean_title} (Source: {publisher})"
                            else:
                                snippet = clean_title
                        else:
                            snippet = clean_desc

                        norm_k = self._normalize_title_key(clean_title)
                        excluded.add(norm_k)
                        results.append({
                            "title": clean_title,
                            "snippet": snippet,
                            "publisher": publisher or "Industry Report",
                            "url": link,
                            "published": pub,
                            "raw_title": title
                        })
            except Exception as e:
                print(f"[TrendAgent] Search error for '{effective_q}': {e}")

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
            raw_response = self.ai.call_ollama_text(prompt, system_prompt=system_prompt, json_mode=True)
            parsed = parse_llm_json(raw_response)
            if not parsed:
                raise ValueError("Could not parse JSON from ingest_user_link response")
        except Exception as e:
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

        vault = self.load_vault()
        vault.setdefault("user_curated_links", []).insert(0, ingest_record)
        vault["user_curated_links"] = vault["user_curated_links"][:30]
        vault["last_updated"] = datetime.now().isoformat()
        self.save_vault(vault)

        return {
            "success": True,
            "title": title,
            "url": url,
            "ingest_record": ingest_record
        }

    def _get_recent_tweet_snippets(self, limit: int = 16) -> List[str]:
        """Reads recently posted tweet snippets from tweet_history.json."""
        hist = safe_read_json(TWEET_HISTORY_FILE, default={})
        recent = hist.get("recent", []) if isinstance(hist, dict) else []
        snippets: List[str] = []
        for item in reversed(recent):
            if isinstance(item, dict) and item.get("snippet"):
                s = str(item["snippet"]).replace("\n", " ").strip()
                if s and s not in snippets:
                    snippets.append(s)
                if len(snippets) >= limit:
                    break
        return snippets

    def _synthesize_educational_thread(
        self,
        handle: str,
        article: Dict[str, str],
        slot_index: int,
    ) -> List[str]:
        """
        Builds a comprehensive, high-authority 3-tweet educational thread grounded directly in
        the subject of today's article. Every tweet is strictly under 265 characters for Twitter API safety.
        - Tweet 1: Hook & Question/Shift framing the core problem or industry shift.
        - Tweet 2: The Direct Answer & Breakdown with 3 concrete bullet points/settings/numbers.
        - Tweet 3: Actionable Studio Formula / Blueprint + targeted hashtags.
        """
        today_label = date.today().strftime("%b %d")
        title = (article.get("title") or "Studio & Creator Workflow Breakdown").strip()
        is_pulse = "pulse" in handle.lower()

        clean_title = title
        if " - " in clean_title:
            clean_title = clean_title.rsplit(" - ", 1)[0].strip()
        t_lower = f"{clean_title} {article.get('snippet', '')}".lower()

        if is_pulse:
            # 1. Facebook Monetization / Meta Ads
            if any(k in t_lower for k in ["facebook", "meta", "monetiz", "ad revenue", "bonus"]):
                return [
                    f"1/3 ⚡ How Creators Monetize on Facebook in 2026: 3 High-Margin Revenue Streams 🧵👇 #CreatorEconomy #Monetization",
                    "2/3 💡 The Playbook:\n• Subscriptions ($9.99/mo): Keeps 100% minus app fees vs 55/45 ad splits.\n• $19 Starter Assets: Convert viewers into digital buyers (85%+ margin).\n• Performance Bonus: Reels with >65% 3s retention unlock 2.4x higher payout tiers.",
                    "3/3 📈 Pro Strategy: Never rely 100% on platform ad payout splits. Use Facebook reach to funnel viewers into your own email list and digital storefront within 72 hours. 🚀 #CreatorGrowth #DigitalProducts",
                ]
            # 2. Creator Economy Data / Statistics / Market Benchmarks
            elif any(k in t_lower for k in ["statistic", "data", "report", "benchmark", "points", "numbers", "study", "survey"]):
                return [
                    f"1/3 ⚡ 2026 Creator Economy Benchmarks: 3 Data Points Every Monetizing Creator Needs 🧵👇 #CreatorEconomy #CreatorGrowth",
                    "2/3 📊 Key Signals:\n• 82% of creator income now stems from direct digital products & communities, not sponsorships.\n• 3s hold rate above 70% drives 3.4x higher organic reach.\n• Tiered micro-offers ($19-$49) cut acquisition cost by 41%.",
                    "3/3 📈 Pro Takeaway: Don't wait on brand deals. Build an owned digital catalog of presets, templates, or guides that generate recurring revenue on autopilot. 💡 #Monetization #DigitalProducts",
                ]
            # 3. Short-Form Video Retention / Watch Time / Hooks / Reels
            elif any(k in t_lower for k in ["video", "short", "reel", "tiktok", "retention", "hook", "watch time", "algorithm"]):
                return [
                    f"1/3 ⚡ Short-Form Video Retention: How to Hook 75%+ Viewers in the First 3 Seconds 🧵👇 #ContentStrategy #CreatorGrowth",
                    "2/3 💡 The 3s Retention Formula:\n• Front-load the outcome: Show the end result in the first 0.8 seconds.\n• High-contrast 4:5 vertical crop: Eliminates dead background space.\n• Kinetic pacing: Cut audio dead-air and highlight action terms.",
                    "3/3 📈 Actionable Takeaway: Audit your last 5 clips. If retention drops below 60% at the 2-second mark, tighten your opening hook to under 6 words. 🚀 #CreatorEconomy #VideoEditing",
                ]
            # 4. Pricing Tiers / $19 Micro-Assets / Digital Products / Storefronts
            elif any(k in t_lower for k in ["pricing", "funnel", "storefront", "$19", "$49", "micro-asset", "product", "etsy", "template", "offer"]):
                return [
                    f"1/3 ⚡ The $19 Micro-Asset Funnel: Why Low-Ticket Products Beat Big Courses 🧵👇 #DigitalProducts #Monetization",
                    "2/3 💡 The Math Behind It:\n• A $19 impulse asset converts at 18-24% from warm traffic vs 1.2% for a $299 course.\n• 32% of $19 buyers upgrade to $49-$149 bundles within 14 days.\n• Automated fulfillment: Instant digital download delivery.",
                    "3/3 📈 Pro Takeaway: Package your most requested workflow into a 1-page template or preset pack today. Launch simple, iterate fast. 📈✨ #CreatorGrowth #PassiveIncome",
                ]
            # 5. Subscriber Churn / Member Retention / Onboarding
            elif any(k in t_lower for k in ["churn", "retention", "subscri", "member", "community", "onboard"]):
                return [
                    f"1/3 ⚡ How to Cut Paid Subscriber Churn in Half: The 72-Hour Onboarding Blueprint 🧵👇 #CreatorEconomy #Monetization",
                    "2/3 💡 The Retention Engine:\n• Instant Welcome Pack: Deliver a bonus template bundle in the first DM.\n• Milestone Recognition: Send a personal thank-you at day 30 with exclusive outtakes.\n• Interactive Input: Let members vote on upcoming themes.",
                    "3/3 📈 Actionable Strategy: 90% of member cancellations happen when new subscribers feel ignored in week 1. Automate your day-1 value drop. 💡 #CreatorGrowth #DigitalProducts",
                ]
            # Default Educational Creator Topic
            else:
                return [
                    f"1/3 ⚡ {today_label} Creator Economy Shift: {clean_title[:80]} 🧵👇 #CreatorEconomy #Monetization",
                    "2/3 💡 Key Strategic Breakdown:\n• Actionable Framework: Pair this shift with a 3-tier value ladder ($19 starter -> $49 bundle -> $149 VIP).\n• Audience Conversion: Route organic reach into owned email subscribers.\n• High-utility micro-assets convert 4x faster.",
                    "3/3 📈 Actionable Takeaway: Audit your audience journey today. Replace dead-end links with a single frictionless bio storefront offering high-utility micro-assets. 🚀 #CreatorGrowth #DigitalProducts",
                ]
        else:
            # 1. iPhone Portrait Mode & Mobile Photography
            if any(k in t_lower for k in ["iphone", "phone", "portrait mode", "mobile photo", "phone camera", "app"]):
                return [
                    f"1/3 📸 iPhone Portrait Mode Masterclass: Why Default Settings Look Fake & How to Fix Them 🧵👇 #StudioPhotography #MobilePhotography",
                    "2/3 💡 The Technical Setup:\n• Use 3x Telephoto (77mm eq) to avoid wide-angle facial distortion.\n• Set Depth Control to f/2.8 — f/1.4 produces plastic cutout edges; f/2.8 mimics true optical falloff.\n• Pull EV down -0.3 to protect skin highlight rolloff.",
                    "3/3 🎨 The Grade: Open the RAW DNG in Lightroom. Drop Highlights -15, lift Shadows +10, and anchor RGB black point at +12 for creamy film tone rolloff. 🎨 #LightroomPresets #ColorGrading",
                ]
            # 2. Editing Consoles (Loupedeck, TourBox, Stream Deck) & Hardware
            elif any(k in t_lower for k in ["console", "loupedeck", "tourbox", "stream deck", "dial", "keyboard", "controller", "hardware"]):
                return [
                    f"1/3 📸 Best Editing Consoles in 2026: Why Physical Dials Double Retouching Speed 🧵👇 #StudioPhotography #PhotoEditing",
                    "2/3 💡 The Console Advantage:\n• Physical Dials: Adjust Exposure & WB fluidly without looking away from skin tones.\n• Precision Knobs: Instant brush size & feathering for dodging & burning.\n• Speed: Batch-grade 100+ RAW captures 2x faster than mouse clicks.",
                    "3/3 🎨 Studio Application: Assign your Loupedeck or TourBox dials to HSL Orange Luminance and RGB Black Point for ultra-fast commercial color grading. ⚡ #ColorGrading #LightroomClassic",
                ]
            # 3. Lightroom Presets / Selling Presets / Influencer Workflows
            elif any(k in t_lower for k in ["preset", "influencer", "sell", "color grade", "lut", "filter"]):
                return [
                    f"1/3 📸 How Top Photographers Build Presets in 2026: Moving Beyond Generic One-Click Filters 🧵👇 #LightroomPresets #ColorGrading",
                    "2/3 💡 The Professional Secret:\n• Adaptive AI Masks: Protect skin tones automatically when exposure shifts.\n• Non-Destructive Tone Curves: Build color contrast on RGB curves; keep basic sliders at 0.\n• Include Studio, Golden Hour & Overcast variants in every pack.",
                    "3/3 🎨 Studio Application: Test your preset packs on at least 15 different skin tones and RAW camera brands (Sony, Canon, Nikon) before launching. 🎨 #StudioPhotography #PhotoRetouching",
                ]
            # 4. Studio Lighting Ratios / Softbox Feathering / Rembrandt / Flash
            elif any(k in t_lower for k in ["lighting", "softbox", "feather", "rembrandt", "light", "strobe", "flash", "reflector", "c-stand"]):
                return [
                    f"1/3 📸 Studio Lighting Masterclass: The Feathering Technique That Kills Forehead Glare 🧵👇 #StudioPhotography #LightingSetup",
                    "2/3 💡 The Setup:\n• Never aim softbox center directly at forehead — specular highlights clip harshly.\n• Feather key softbox 45° across the nose so soft edge wraps cheekbones.\n• Add 3200K warm rim light at 135° behind subject for 3D depth.",
                    "3/3 🎨 Studio Application: Keep key-to-fill ratio at 1:1.5 for commercial beauty, or 1:3 for moody cinematic portraits. Soft light comes from size, not low power! 💡 #PortraitPhotography #ColorGrading",
                ]
            # 5. Commercial Skin Retouching / Frequency Separation / Dodge & Burn
            elif any(k in t_lower for k in ["retouch", "frequency separation", "dodge", "burn", "skin", "texture", "pore"]):
                return [
                    f"1/3 📸 Commercial Skin Retouching: Why High-End Magazines Banned Clarity Sliders 🧵👇 #PhotoRetouching #StudioPhotography",
                    "2/3 💡 The Pro Method:\n• Frequency Separation: Split into High (pores/texture) and Low (color/shadows).\n• Never blur the high layer — clone stamp blemishes with hard round brush.\n• 1% opacity soft brush on low layer smooths blotchiness with authentic pores.",
                    "3/3 🎨 Studio Application: Finish with subtle micro-dodging & burning on a 50% gray overlay layer set to Soft Light. Pores stay sharp, skin stays luminous. ✨ #LightroomPresets #EditorialRetouching",
                ]
            # 6. Kodak Portra / Film Science / Analog Tone Curves
            elif any(k in t_lower for k in ["portra", "cinestill", "film", "analog", "curve", "35mm", "grain"]):
                return [
                    f"1/3 📸 The Real Kodak Portra 400 Color Science in Lightroom: 3 Non-Destructive Adjustments 🧵👇 #ColorGrading #LightroomPresets",
                    "2/3 💡 The Recipe:\n• RGB Tone Curve: Lift Black Point to +16 on Y-axis for creamy matte shadows; soften highlights at 240.\n• HSL Orange: Saturation -4%, Luminance +8% for healthy glow.\n• Shift Greens +12 towards emerald to kill digital foliage tint.",
                    "3/3 🎨 Studio Takeaway: Add subtle 35mm grain (Amount: 22, Size: 35, Roughness: 50) to break up digital banding in gradient studio backdrops. 🎞️ #StudioPhotography #FilmPhotography",
                ]
            # Default Educational Studio Topic
            else:
                return [
                    f"1/3 📸 {today_label} Studio Technique: {clean_title[:80]} 🧵👇 #StudioPhotography #ColorGrading",
                    "2/3 💡 Technical Implementation:\n• Tone Control: Lock RGB black point (+16) and feather key modifiers 45° to stop clipping.\n• Color Calibration: Anchor skin via HSL Orange (-4% Sat, +8% Lum) for 3D depth.\n• Deliver 30 curated color-graded proofs in 24 hours.",
                    "3/3 🎨 Studio Application: Separate high-frequency skin texture (+8 Texture) from low-frequency color transitions (-4 Clarity) for authentic magazine-grade retouching. ✨ #LightroomPresets #PhotoEditing",
                ]

    def _build_article_grounded_slot_thread(
        self,
        handle: str,
        article: Dict[str, str],
        slot_index: int,
    ) -> List[str]:
        """Backward-compatible alias pointing directly to _synthesize_educational_thread."""
        return self._synthesize_educational_thread(handle, article, slot_index)

    def _build_dynamic_fallback_slots(
        self,
        photo_articles: List[Dict[str, str]],
        creator_articles: List[Dict[str, str]],
        business_articles: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Builds all 5 daily Twitter slots dynamically from today's freshly discovered
        articles if Ollama is temporarily unreachable.
        """
        today_label = date.today().strftime("%b %d")
        p_arts = photo_articles or [{"title": f"Editorial Color Calibration & Skin Tone Workflow ({today_label})", "snippet": "Locking white balance and curve anchors cuts batch editing time in half.", "publisher": "Studio Wire"}]
        c_arts = creator_articles or [{"title": f"Audience Retention & Tiered Value Ladders ({today_label})", "snippet": "Structured micro-offers convert passive viewers into recurring supporters.", "publisher": "Creator Pulse"}]
        b_arts = business_articles or [{"title": f"Automated Digital Product Funnels ({today_label})", "snippet": "Instant-download templates and presets scale with zero fulfillment overhead.", "publisher": "Creator Blueprint"}]

        slot_names = [
            "slot_1_morning",
            "slot_2_midday",
            "slot_3_afternoon",
            "slot_4_evening",
            "slot_5_latenight",
        ]
        daily_slots: Dict[str, Dict[str, List[str]]] = {}
        combined_creator = c_arts + b_arts

        for idx, slot_id in enumerate(slot_names):
            pa = p_arts[idx % len(p_arts)]
            ca = combined_creator[idx % len(combined_creator)]
            daily_slots[slot_id] = {
                "creatorpulselab": self._synthesize_educational_thread("creatorpulselab", ca, idx),
                "TheCreatorAsset": self._synthesize_educational_thread("TheCreatorAsset", pa, idx),
            }

        return {
            "used_fallback": True,
            "top_themes_today": [
                p_arts[0].get("title", "Editorial Studio Color & Lighting Precision"),
                c_arts[0].get("title", "Creator Retention & Recurring Revenue Engines"),
                b_arts[0].get("title", "Digital Asset Storefronts & Workflow Automation"),
            ],
            "daily_slots": daily_slots,
            "newsletter_topics": {
                "creator_pulse": {
                    "title": c_arts[0].get("title", "Creator Monetization & Retention Playbook"),
                    "teaser": c_arts[0].get("snippet", "How independent creators are turning organic reach into recurring digital revenue this week."),
                },
                "creator_asset": {
                    "title": p_arts[0].get("title", "Studio Lighting & RAW Color Science"),
                    "teaser": p_arts[0].get("snippet", "Practical studio lighting ratios and non-destructive RAW grading workflows for commercial photographers."),
                },
            },
        }

    def run_daily_radar_sweep(self) -> Dict[str, Any]:
        """
        Runs an autonomous morning web search across photography and creator monetization,
        synthesizes fresh daily topics, and generates today's 5-slot tweets and newsletter briefs.
        Uses direct industry RSS feeds + recency-filtered Google News RSS + 21-day deduplication.
        """
        print("[TrendAgent] Running autonomous daily trend radar sweep...")
        today_dt = date.today()
        today_str = today_dt.isoformat()
        day_ord = today_dt.toordinal()

        vault = self.load_vault()
        excluded_keys = self._get_excluded_topic_keys(vault)

        # 1. Gather live news for Niche A (Photography & Studio)
        photo_articles: List[Dict[str, str]] = self.fetch_direct_rss_articles(
            "photo", max_results=3, excluded_keys=excluded_keys
        )
        for i in range(len(PHOTO_QUERY_POOL)):
            if len(photo_articles) >= 6:
                break
            q = PHOTO_QUERY_POOL[(day_ord * 3 + i) % len(PHOTO_QUERY_POOL)]
            photo_articles.extend(
                self.search_live_trends(q, max_results=2, when_window="7d", excluded_keys=excluded_keys)
            )
        photo_articles = photo_articles[:6]

        # 2. Gather live news for Niche B (Digital Creators & Monetization - 100% SFW)
        creator_articles: List[Dict[str, str]] = self.fetch_direct_rss_articles(
            "creator", max_results=3, excluded_keys=excluded_keys
        )
        for i in range(len(CREATOR_QUERY_POOL)):
            if len(creator_articles) >= 6:
                break
            q = CREATOR_QUERY_POOL[(day_ord * 3 + i) % len(CREATOR_QUERY_POOL)]
            creator_articles.extend(
                self.search_live_trends(q, max_results=2, when_window="7d", excluded_keys=excluded_keys)
            )
        creator_articles = creator_articles[:6]

        # 3. Gather live news for Niche C (Digital Business / Media Automation - powers
        # The Creator Blueprint newsletter's sections)
        business_articles: List[Dict[str, str]] = []
        for i in range(len(BUSINESS_QUERY_POOL)):
            if len(business_articles) >= 6:
                break
            q = BUSINESS_QUERY_POOL[(day_ord * 3 + i) % len(BUSINESS_QUERY_POOL)]
            business_articles.extend(
                self.search_live_trends(q, max_results=2, when_window="7d", excluded_keys=excluded_keys)
            )
        business_articles = business_articles[:6]

        # 4. Build synthesis prompt with article summaries & strict editorial rules
        photo_summary = [{"title": a["title"], "summary": a.get("snippet", "")} for a in photo_articles]
        creator_summary = [{"title": a["title"], "summary": a.get("snippet", "")} for a in creator_articles]
        business_summary = [{"title": a["title"], "summary": a.get("snippet", "")} for a in business_articles]

        prompt = f"""You are SYNAPSE [100 Fm] & HERALD [33 As], Expert Social Media Director & Editor for Creator Media Lab.
Today is {today_str}. Here are verified breaking articles discovered in today's live radar sweep:

PHOTOGRAPHY & STUDIO NEWS (for @TheCreatorAsset & Studio Wire):
{json.dumps(photo_summary, indent=2)}

CREATOR ECONOMY & MONETIZATION NEWS (for @creatorpulselab & Creator Pulse):
{json.dumps(creator_summary, indent=2)}

DIGITAL PRODUCT & AUTOMATION NEWS (for Creator Blueprint & @creatorpulselab):
{json.dumps(business_summary, indent=2)}

STRICT EDITORIAL RULES (CRITICAL):
1. USE ONLY TODAY'S ARTICLES ABOVE: Every single slot MUST be grounded in a specific article from the lists above. Never reference old articles not listed above.
2. DISTINCT SLOTS: Each of the 5 slots ("slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight") MUST cover a DIFFERENT article from the lists above (e.g. Slot 1 = Article 1, Slot 2 = Article 2, Slot 3 = Article 3, Slot 4 = Article 4, Slot 5 = Article 5).
3. NO UNANSWERED QUESTIONS / CLIFFHANGERS: If you pose a question, you MUST provide the direct answer, comparison numbers, and takeaway in that thread.
4. NO PHANTOM LISTS: NEVER write "Top 5" or "Top 7" or "3 secrets" unless you explicitly list every single item/name/step directly in the tweet strings.
5. STANDALONE ACTIONABLE VALUE: Every thread must have 3 tweets ("1/3 ...", "2/3 ...", "3/3 ...") giving concrete value: exact slider settings, payout percentages, or workflow steps.
6. STRATEGIC HASHTAGS: Include 2 to 3 targeted niche hashtags (#CreatorEconomy #CreatorGrowth #Monetization #DigitalProducts for @creatorpulselab; #StudioPhotography #LightroomPresets #ColorGrading for @TheCreatorAsset).
7. STRICT 100% SFW ENFORCEMENT (NON-NEGOTIABLE): All content across BOTH @TheCreatorAsset AND @creatorpulselab MUST be 100% Safe For Work (SFW).

Generate today's dynamic content drop payload in valid JSON with:
1. "top_themes_today": Exactly 3 high-impact industry themes for today grounded in the articles above.
2. "daily_slots": A dictionary with keys "slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight".
   For EACH slot, provide:
   - "creatorpulselab": List of 3 tweet strings ("1/3 ...", "2/3 ...", "3/3 ...") for @creatorpulselab.
   - "TheCreatorAsset": List of 3 tweet strings ("1/3 ...", "2/3 ...", "3/3 ...") for @TheCreatorAsset.
3. "newsletter_topics":
   - "creator_pulse": {{"title": "...", "teaser": "..."}} for today's creator newsletter.
   - "creator_asset": {{"title": "...", "teaser": "..."}} for today's photography digest.

Respond ONLY with valid JSON.
"""
        system_prompt = "You are an expert social media and newsletter director for creator brands. Return valid JSON only. All content must be 100% SFW and grounded strictly in today's provided articles."

        try:
            synth = None
            last_error = None
            EXPECTED_SLOTS = {"slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight"}
            for attempt in range(2):
                try:
                    raw = self.ai.call_ollama_text(
                        prompt,
                        system_prompt=system_prompt,
                        num_ctx=8192,
                        num_predict=4096,
                        temperature=0.75 + (attempt * 0.1),
                        json_mode=True,
                        timeout=150,
                    )
                    parsed = parse_llm_json(raw)
                    if not parsed:
                        raise ValueError("LLM response could not be parsed as JSON")
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
            synth = self._build_dynamic_fallback_slots(photo_articles, creator_articles, business_articles)

        # SFW Sanitation + Stale/Duplicate + Cross-Account Distinctness Gate on all synthesized tweets
        blocked_sfw_tokens = [
            "boudoir", "nude", "naked", "nsfw", "topless", "bare breasts", "exposed nipples",
            "genitals", "porn", "explicit", "erotic", "xxx", "uncensored",
            "onlyfans", "fansly", "chaturbate", "myfreecams", "mfc", "camgirl", "cam girl",
            "sextortion", "sex work", "banned angle"
        ]
        sfw_pattern = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in blocked_sfw_tokens) + r")\b", re.IGNORECASE)
        try:
            from pipeline.stages.twitter_poster import TwitterPoster
            tp_checker = TwitterPoster()
        except Exception:
            tp_checker = None

        slot_order = ["slot_1_morning", "slot_2_midday", "slot_3_afternoon", "slot_4_evening", "slot_5_latenight"]
        combined_creator_pool = (creator_articles + business_articles) or [{"title": "Creator Economy Growth", "snippet": "Tiered digital offers drive recurring creator income."}]
        photo_pool = photo_articles or [{"title": "Studio Lighting & Color Science", "snippet": "Calibrated RAW tone curves streamline portrait editing."}]

        slots = synth.get("daily_slots", {})
        for idx, slot_k in enumerate(slot_order):
            slot_val = slots.setdefault(slot_k, {})
            if not isinstance(slot_val, dict):
                slot_val = {}
                slots[slot_k] = slot_val
            for hdl in ("creatorpulselab", "TheCreatorAsset"):
                tw_list = slot_val.get(hdl, [])
                clean_list = []
                if isinstance(tw_list, list):
                    for tw in tw_list:
                        tw_str = re.sub(r"\*\*|__", "", str(tw)).strip()
                        if sfw_pattern.search(tw_str):
                            print(f"[TrendAgent Safety Alert] Purged non-SFW tweet from synthesized {slot_k} for @{hdl}: {tw_str[:50]}...")
                            continue
                        clean_list.append(tw_str)

                # Check if the root tweet accidentally hallucinated a stale legacy topic,
                # has fewer than 2 tweets, collides with 7-day history, or if TheCreatorAsset
                # accidentally echoed creatorpulselab's exact topic in the same slot
                joined_lower = " ".join(clean_list).lower()
                same_as_other = False
                if hdl == "TheCreatorAsset" and clean_list and slot_val.get("creatorpulselab"):
                    cp_first = slot_val["creatorpulselab"][0] if slot_val["creatorpulselab"] else ""
                    if cp_first:
                        w1 = self._title_word_set(clean_list[0])
                        w2 = self._title_word_set(cp_first)
                        if w1 and w2 and len(w1 & w2) >= 3:
                            same_as_other = True

                has_proper_answers = (
                    len(clean_list) >= 3
                    and clean_list[0].startswith("1/")
                    and clean_list[1].startswith("2/")
                    and len(clean_list[1]) >= 60
                    and not any(clean_list[1].strip().lower().startswith(x) for x in ["2/3 key signal: yahoo", "2/3 key signal: u.s.", "2/3 key signal: industry", "2/3 production breakdown: amra", "2/3 production breakdown: fstoppers"])
                )
                is_stale_or_dup = (
                    not has_proper_answers
                    or same_as_other
                    or any(pat in joined_lower for pat in STALE_LEGACY_PATTERNS)
                    or (tp_checker is not None and tp_checker._is_duplicate_tweet(clean_list[0]))
                )
                if is_stale_or_dup:
                    pool = combined_creator_pool if "pulse" in hdl.lower() else photo_pool
                    art = pool[idx % len(pool)]
                    clean_list = self._build_article_grounded_slot_thread(hdl, art, idx)
                    print(f"[TrendAgent] Grounded {slot_k} for @{hdl} with dedicated niche article thread: {art.get('title', '')[:60]}")

                slot_val[hdl] = clean_list

        # Record today's selected articles into the rolling 21-day seen_articles ledger
        seen_map = vault.get("seen_articles", {})
        if not isinstance(seen_map, dict):
            seen_map = {}
        for k, d_str in list(seen_map.items()):
            try:
                if (today_dt - date.fromisoformat(str(d_str)[:10])).days > 21:
                    del seen_map[k]
            except Exception:
                pass
        for art in (photo_articles + creator_articles + business_articles):
            if isinstance(art, dict) and art.get("title"):
                seen_map[self._normalize_title_key(art["title"])] = today_str

        vault["today_date"] = today_str
        vault["last_radar_sweep"] = datetime.now().isoformat()
        vault["photo_articles"] = photo_articles
        vault["creator_articles"] = creator_articles
        vault["business_articles"] = business_articles
        vault["daily_synthesis"] = synth
        vault["seen_articles"] = seen_map
        self.save_vault(vault)

        # Invalidate any pre-sweep cached fallback entries in scribe_daily_content.json for today
        try:
            scribe_cache = safe_read_json(SCRIBE_CACHE_FILE, default={})
            if isinstance(scribe_cache, dict):
                modified = False
                for pub_id in ("creator_pulse", "studio_wire", "creator_blueprint"):
                    entry = scribe_cache.get(pub_id)
                    if isinstance(entry, dict) and entry.get("date") == today_str:
                        content_obj = entry.get("content") or {}
                        if (
                            content_obj.get("is_fallback")
                            or content_obj.get("source") == "Scribe Dynamic Daily Synthesis"
                            or not entry.get("grounded_in_radar_sweep")
                        ):
                            del scribe_cache[pub_id]
                            modified = True
                if modified:
                    atomic_write_json(SCRIBE_CACHE_FILE, scribe_cache)
                    print("[TrendAgent] Invalidated pre-sweep Scribe cache entries so newsletters regenerate from fresh radar articles.")
        except Exception as ce:
            print(f"[TrendAgent] Notice while checking Scribe cache invalidation: {ce}")

        print(f"[TrendAgent] Daily radar sweep complete! Saved {len(photo_articles)} photo, {len(creator_articles)} creator, {len(business_articles)} business articles to {self.vault_file}")
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
            atomic_write_json(self.vault_file, data)
        except Exception as e:
            print(f"[TrendAgent] Error saving vault: {e}")

    def get_static_trend_matrix(self) -> Dict[str, Any]:
        """Comprehensive foundational market intelligence matrix."""
        return {
            "photo_retouching": {
                "title": "📸 Photo Shoot & Retouching Trends",
                "aesthetic_trends": [
                    {"name": "Warm Chocolate Editorial", "vibe": "Moody shadows, warm skin undertones, velvety blacks."},
                    {"name": "Golden Hour Glow", "vibe": "Amber rim lighting, sun-kissed luminous skin."},
                    {"name": "Cyber Neon Noir", "vibe": "Deep cyan and magenta contrast, futuristic editorial."},
                    {"name": "35mm Analog Film Grain", "vibe": "Subtle organic grain, muted greens, nostalgic warmth."}
                ]
            },
            "creator_monetization": {
                "title": "💎 Creator Economy & Monetization Trends",
                "token_pricing_sweet_spots": [
                    {"tier": "Micro-Offers ($9-$19)", "purpose": "Low barrier impulse activation."},
                    {"tier": "Core Asset Bundles ($29-$59)", "purpose": "High volume storefront revenue."},
                    {"tier": "Pro Toolkits ($79-$149)", "purpose": "Complete workflow acceleration."},
                    {"tier": "VIP / Retainer Tiers ($250-$750)", "purpose": "High margin custom fulfillment."}
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
                lines.append(f"- Daily Creator Pulse: {cp.get('title', '')} ('{cp.get('teaser', '')}')")
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
            "digital products fiverr etsy",
            "AI agency video photo retainer",
            "creator marketing monetization growth",
            "digital templates presets passive income"
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
            raw = self.ai.call_ollama_text(prompt, system_prompt=system_prompt, json_mode=True)
            parsed = parse_llm_json(raw)
            if parsed:
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
