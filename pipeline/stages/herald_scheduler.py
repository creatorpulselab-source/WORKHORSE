from shared.atomic_writer import atomic_write_json, safe_read_json
"""
WORKHORSE AUTONOMOUS DAILY SCHEDULER & DISPATCHER (AGENT: HERALD [33 As])
Manages automated daily multi-publication newsletters and 3-5 daily tweets/threads
per account for both:
  - @TheCreatorAsset (Studio Photography, Color Grading, Presets)
  - @creatorpulselab (Adult Creators, PPV Strategies, Cam Tip Menus)
"""

import os
import sys
import json
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union

sys.path.insert(0, "F:/WORKHORSE")
from pipeline.stages.twitter_poster import TwitterPoster
from pipeline.stages.newsletter_manager import NewsletterManager
from pipeline.stages.pinterest_poster import PinterestPoster

logger = logging.getLogger("workhorse.herald_scheduler")

# Each brand has its own distinct visual "vibe" since @creatorpulselab and @TheCreatorAsset
# serve different audiences - Herald generates a FRESH on-brand image per post rather than
# reusing a leftover/test render, and every render still passes through the Iris QC gate.
BRAND_VIBES = {
    "creator_pulse_lab": {
        "brand_target": "creator_pulse_lab",
        "prompts": [
            # 1. Sexy & Alluring
            "Sunlit luxury resort infinity pool, gorgeous creator wearing a chic metallic gold string bikini relaxing on a teak sunlounger with an iPad displaying daily Stripe sales analytics, sparkling turquoise water, palm shadows, commercial 85mm portrait, 8k resolution, raw photo quality",
            "Alluring evening creator portrait, stunning model wearing an elegant emerald satin cowl-neck slip dress with delicate gold jewelry, warm ambient candlelight, soft rim lighting, confident inviting gaze, 85mm f/1.4 prime lens",
            "Luxury penthouse balcony at sunset, attractive creator in a sculpted black sweetheart strapless mini dress leaning gracefully against glass railing, golden hour city skyline bokeh, alluring confident posture, 50mm lens",
            "Private resort cabana, sun-kissed creator in a stylish bronze cutout one-piece swimsuit smiling playfully while checking her smartphone, vibrant tropical poolside atmosphere, commercial editorial 85mm",
            "High-fashion creator studio, confident woman wearing an alluring low-cut silk wrap top with subtle tasteful cleavage, soft beauty dish lighting, clean direct sightline with zero occlusions, 85mm lens",
            "Sunlit Mediterranean beach club, attractive creator wearing a white bikini with gold rings with a breezy open silk kimono, radiant golden tan, ocean breeze in hair, 85mm portrait",
            # 2. Playful & Cute
            "Playful rooftop lifestyle shoot, cute creator in a white cotton crop tank top and high-waisted denim cutoffs laughing in golden sunlight, wind moving hair naturally, holding a mini vlog mic, 50mm prime",
            "Vibrant summer beach boardwalk, playful creator in a bright floral bikini and breezy linen cover-up spinning with a wide joyful smile, sunbeams catching ocean mist, cinematic lifestyle 35mm",
            "Sunny creative agency terrace, radiant creator wearing a cute pastel tie-front top and pleated tennis skirt enjoying an iced latte, laughing candidly, warm morning sunlight, 50mm f/1.8",
            "Playful creator in a yellow summer sundress dancing on an outdoor urban terrace at golden hour, fabric swaying naturally, joyful radiant expression, cinematic 50mm lens",
            "Cute aesthetic studio portrait, attractive creator in a smocked off-shoulder peasant blouse and delicate gold earrings, warm honey catchlights in eyes, relaxed inviting expression, 85mm lens",
            # 3. Cozy & Inviting
            "Cozy sunlit loft morning, creator wearing an oversized chunky oat cable-knit off-shoulder sweater holding a steaming ceramic coffee mug, curled up in a bay window, serene warm smile, 35mm lens",
            "Warm evening creator lounge, attractive woman in a cozy brushed mohair crewneck sweater sitting cross-legged on a plush velvet couch with a MacBook reviewing creator revenue, 50mm f/1.4",
            "Relaxed aesthetic home studio, creator in a cozy fuzzy cream sweater dress relaxing with studio headphones around neck, soft warm fairy lights, steaming tea mug, 50mm prime",
            "Fireside creator retreat, attractive creator in an alpaca knit sweater sketching digital product blueprints in a leather journal, warm crackling fireplace glow, 35mm film aesthetic",
            # 4. Active Creator & Workflow
            "Creator actively filming a vertical video reel with a mirrorless camera on a handheld gimbal in a bright modern studio, wearing a stylish fitted tank top, confident energetic expression, 35mm lens",
            "Independent creator at modern wooden desk holding up digital product template download cards, smiling proudly at camera, dual 4K editing monitors glowing behind her, 50mm prime",
            "Over-the-shoulder creator workflow, hands on a custom mechanical keyboard and DaVinci color grading console, glowing dual ultrawide monitors displaying monetization analytics, 35mm lens",
            "Aesthetic creator podcast lounge, attractive creator in an open linen shirt leaning toward a desktop microphone, warm amber lamp glow, engaging conversational expression, 50mm lens",
            "Modern flat-lay of creator monetization gear: iPad Pro displaying digital product pricing tiers ($19, $49, $149), Sony camera with G-Master lens, AirPods Max, and leather notebook, 50mm macro",
            "Late-night creator video editing suite, dark mode timeline glowing with vibrant purple and cyan accents, Sony headphones on stand, steaming coffee mug, sleek creative atmosphere, 35mm lens"
        ],
        "negative_prompt": "nude, nudity, naked, topless, bare breasts, exposed nipples, exposed genitals, lingerie, underwear, bra, panties, sheer transparent clothing exposing nipples, erotic, explicit adult content, porn, NSFW, objects in front of face, microphone blocking face, tripod obscuring subject, camera cutting off head, poles in front of body, clutter obscuring person, foreground obstruction, equipment blocking face, boom mic in frame, extra limbs, deformed hands, mutated fingers, fused digits, bad anatomy, blurry, low quality, watermark, text, cartoon, illustration",
        "video_motion_prompts": [
            "subtle natural head turn toward camera, warm natural smile with confident expression, soft studio light drift, cinematic 24fps, high production value, photorealistic",
            "slow cinematic push-in on modern creator workstation, gentle LED light pulse, professional creative atmosphere, cinematic motion, photorealistic",
            "creator adjusting camera lens on desk, natural micro-movements, warm practical rim light flicker, cinematic 24fps, photorealistic",
            "subtle confident nod with a creative director smile, stylish studio lighting shift, cinematic motion, photorealistic",
            "slow cinematic camera glide over modern editing desk and audio gear, clean architectural lines, photorealistic, high production value",
            "creator looking up from tablet with engaging confident expression, soft ambient light shift, cinematic 24fps, photorealistic",
            "gentle ocean breeze moving hair, golden sunlight rippling on pool water, relaxing happy smile toward camera, cinematic slow motion",
            "slow playful spin in sunlight, fabric swaying naturally, radiant confident expression, cinematic 24fps"
        ]
    },
    "creator_media_lab": {
        "brand_target": "creator_media_lab",
        "prompts": [
            # 1. Studio Lighting & Science
            "Editorial studio photography session, photographer in a chic fitted black tank top actively positioning a 48-inch parabolic softbox on a heavy-duty C-stand, crisp 5600K key light, 35mm lens",
            "Alluring studio portrait, stunning model in an elegant sculpted strapless black sweetheart dress, dramatic 45-degree feathered key lighting casting soft dimensional shadows across shoulder, 85mm lens",
            "Professional beauty dish lighting test, model in a stylish low-cut satin camisole, large circular catchlights in eyes, authentic textured skin with natural pores, soft highlight rolloff, 105mm macro",
            "Classic Rembrandt studio portrait, attractive subject in an alluring open-back velvet evening dress, single key light with silver reflector fill creating iconic triangle highlight on cheek, 85mm prime",
            "Studio photographer in a cute linen crop top holding a handheld light meter near model's face, checking key-to-fill lighting ratios, professional studio background, 50mm lens",
            "Behind-the-scenes studio lighting masterclass setup, large Profoto beauty dish on boom arm with honeycomb grid, silver reflector clamshell, seamless grey studio backdrop, soft atmospheric haze, 35mm lens",
            # 2. Color Grading & Film Science
            "Colorist actively grading an editorial portrait at a dual Apple Studio Display workstation, hands adjusting DaVinci Resolve color wheels, warm studio ambient glow, 35mm lens",
            "Photographer in a stylish silk wrap blouse examining 35mm Kodak Portra 400 film negative strips on an illuminated light table with a handheld loupe, natural daylight, 50mm macro",
            "High-fashion editorial portrait showcasing authentic Kodak Portra 400 color science, model in an alluring emerald cowl-neck slip dress, luminous golden skin tones, velvety matte shadows, 85mm lens",
            "Cinematic Cinestill 800T color-graded portrait, attractive creator in a sleek black leather jacket on a rain-slicked city sidewalk under neon signs, rich red halation and teal shadows, 50mm f/1.4",
            "Macro flat-lay of vintage film photography tools: Kodak Portra 400 and Cinestill 800T film canisters, Loupedeck editing console, Pantone color chips, and Leica M camera on dark walnut desk, 50mm macro",
            # 3. Retouching & Beauty
            "High-fashion beauty retouching close-up, radiant female model with natural skin texture, visible pores, and glowing skin roll-off, wearing delicate gold jewelry, clean studio background, 105mm macro",
            "Editorial retoucher's hands using a Wacom digital stylus on a high-res Cintiq tablet, frequency separation layer split visible on screen, warm ambient desk lamp, 50mm prime",
            "Stunning model in a cute tie-front satin top looking into a vanity ring light, radiant smiling expression, flawless natural makeup, crisp catchlights, 85mm portrait",
            # 4. Playful & Alluring Outdoor / Beach
            "Golden hour beach portrait, gorgeous subject in a white string bikini with gold accents smiling toward camera, low-angle warm sunlight creating radiant rim glow, ocean waves softly blurred, 85mm f/1.4",
            "Sunlit Mediterranean villa terrace, attractive creator in an ivory linen backless sundress walking toward the camera, warm golden sunlight streaming through olive branches, 50mm prime",
            "Playful urban rooftop portrait, model in a cute cropped baby tee and vintage cutoffs laughing naturally, golden hour skyline bokeh, crisp rim light, 50mm f/1.8",
            # 5. Cozy & Creative Lifestyle
            "Cozy autumn studio shoot, attractive photographer in an oversized chunky cable-knit cream sweater holding a vintage SLR camera, warm amber window light, steam from coffee mug, 50mm lens",
            "Late-night monitor calibration session, creator in a soft comfortable camisole and draped cardigan holding a Spyder calibrator to display screen, dim ambient studio mood, 35mm lens",
            "Behind-the-scenes creator workshop, studio owner in a chic dark sleeveless top reviewing photo contact sheets on a tablet, C-stands and softboxes softly blurred in background, 50mm lens"
        ],
        "negative_prompt": "nude, nudity, naked, topless, bare breasts, exposed nipples, exposed genitals, lingerie, underwear, bra, panties, sheer transparent clothing exposing nipples, erotic, explicit adult content, porn, NSFW, objects in front of face, microphone blocking face, tripod obscuring subject, camera cutting off head, poles in front of body, clutter obscuring person, foreground obstruction, equipment blocking face, boom mic in frame, extra limbs, deformed hands, mutated fingers, fused digits, bad anatomy, blurry, low quality, watermark, text, cartoon, illustration",
        "video_motion_prompts": [
            "subtle natural head turn toward camera, gentle breathing motion, soft ambient light drift, cinematic 24fps, high production value, photorealistic",
            "slow cinematic push-in, gentle hair movement in a light breeze, natural blinking and micro-expressions, photorealistic, cinematic motion",
            "gentle walk-and-turn toward camera, fabric and hair moving naturally, soft rim light shift, cinematic 24fps, photorealistic",
            "subtle confident nod with a slow smile forming, soft practical light flicker in background, cinematic motion, photorealistic",
            "gentle hand adjusting camera/gear with natural micro-movements, soft studio light drift, documentary-style cinematic motion, photorealistic",
            "slow environmental pan feel with subject's gaze following camera, natural outdoor breeze movement, cinematic 24fps, photorealistic",
            "creator gently adjusting dials on color console, screen light reflecting softly, natural breathing, cinematic 24fps",
            "photographer raising camera to eye level, adjusting focus ring, warm key light shifting smoothly, cinematic 24fps"
        ]
    }
}

# Comprehensive 100% SFW safety blocklist - enforced across ALL external channels (Twitter, Pinterest)
SFW_BLOCKED_KEYWORDS = [
    "boudoir", "nude", "naked", "nsfw", "topless", "bare breasts", "exposed nipples",
    "genitals", "porn", "explicit", "erotic", "xxx", "uncensored",
    "onlyfans", "fansly", "chaturbate", "myfreecams", "mfc", "camgirl", "cam girl",
    "webcam", "sextortion", "sex work", "banned angle"
]

# Curated strategic hashtag taxonomy per brand for maximum algorithmic reach on X/Twitter.
BRAND_HASHTAGS = {
    "creatorpulselab": ["#CreatorEconomy", "#CreatorGrowth", "#Monetization", "#ContentStrategy", "#DigitalProducts"],
    "TheCreatorAsset": ["#StudioPhotography", "#LightroomPresets", "#ColorGrading", "#EditorialPhotography", "#PhotoRetouching"],
}

STATE_FILE = Path("F:/WORKHORSE/workspace/daily_schedule_state.json")
LOGS_DIR = Path("F:/WORKHORSE/workspace/newsletter_logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Public newsletters that previously had NO automated send path at all - only
# dispensary_deals (private) was ever actually dispatched by trigger_dispatch().
PUBLICATION_SCHEDULE = {
    "studio_wire": "08:30",
    "creator_pulse": "09:00",
    "creator_blueprint": "10:00",
}

# dispensary_deals is dispatched via its own legacy flag name (newsletters_sent_today)
# for backward compat with the dashboard, but is monitored the same way as the rest.
ALL_MONITORED_PUBLICATIONS = {"dispensary_deals": "09:00", **PUBLICATION_SCHEDULE}

# A dispatch isn't marked "done" until real delivery is verified. Failed dispatches are
# auto-retried up to this many times before Synapse gives up and alerts the Commander.
MAX_DISPATCH_RETRIES = 3

# Pipe 3 - Autonomous AI Model Content Engine (Cipher -> RTX 5070 Ti -> Forge -> Scribe).
# One hands-off content drop per day; output is staged for manual review, never auto-posted.
CONTENT_ENGINE_SCHEDULE_TIME = "11:30"

# How long Herald keeps retrying the morning radar sweep (every ~60s) when it comes back
# degraded/fallback before giving up and accepting whatever content it has for the day.
RADAR_SWEEP_RETRY_CUTOFF = "10:30"

DAILY_SLOTS = [
    {
        "slot_id": "slot_1_morning",
        "name": "Morning Masterclass & Newsletter Drop",
        "target_time": "09:00",
        "description": "Daily 4-tweet deep-dive educational thread & morning newsletter release",
        "tweets": {
            "creatorpulselab": [
                "1/4 ⚡ 3 digital product offer structures that converted 20%+ higher this week for independent creators 🧵👇 @creatorpulselab #CreatorEconomy #Monetization",
                "2/4 Structure 1: The 'Micro-Asset' Entry Point.\n\nDon't launch a $300 course first. Launch a $19 actionable template or preset bundle that solves one painful bottleneck in under 10 minutes.",
                "3/4 Structure 2: The 3-Tier Value Ladder.\n\nTier 1 ($19): Core template.\nTier 2 ($49): Template + video walkthrough + raw asset project files.\nTier 3 ($149): All templates + 1-on-1 async review.",
                "4/4 Structure 3: The Educational Email Engine.\n\nDeliver free tactical value 5 days a week, with a frictionless checkout link at the bottom. Explore our daily creator monetization blueprints & newsletter 👇\nhttps://digitalcreatorassets-source.github.io/creatormedialab/?pub=creator_pulse #CreatorGrowth #DigitalProducts"
            ],
            "TheCreatorAsset": [
                "1/4 📸 Stop using cheap Instagram filters on paid client photo shoots.\n\nHere is the exact color science behind the Kodak Portra 400 film aesthetic in Lightroom 🧵👇 @TheCreatorAsset #StudioPhotography #Portra400",
                "2/4 Portra 400 Tone Curve Breakdown:\n\n1. Lift the black point on the RGB curve by +8 to +12 for that matte film floor.\n2. Drop shadows slightly (-5) to preserve dynamic contrast.\n3. Keep midtone skin values linear to avoid harsh digital clipping.",
                "3/4 HSL Color Calibration:\n\n- Orange Hue: +2 to +4 (warms natural skin tones without looking artificial)\n- Red Luminance: +6 (creates that healthy, glowing studio look)\n- Green Saturation: -18 (eliminates harsh digital foliage tint)",
                "4/4 ✨ Download our master studio preset pack (.XMP) and explore the full editorial retouching suite:\nhttps://www.etsy.com/shop/CreatorMediaLab\nhttps://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire #LightroomPresets #ColorGrading"
            ]
        }
    },
    {
        "slot_id": "slot_2_midday",
        "name": "Mid-Day Creator Tip & Lightroom Science",
        "target_time": "13:00",
        "description": "High-converting quick tip and before-and-after breakdown",
        "tweets": {
            "creatorpulselab": [
                "⚡ Quick Monetization Tip: Digital product checkout pages with fewer than 3 pricing options convert 34% higher than cluttered catalogs.\n\nDecision fatigue kills sales. Tier your offerings: Starter Kit ($17), Pro Asset Bundle ($47), and VIP All-Access ($147).\n\nKeep it punchy, Commander. 👑 @creatorpulselab #CreatorEconomy #Monetization"
            ],
            "TheCreatorAsset": [
                "📸 Studio Lighting Rule of Thumb: If your key light is less than 3 feet from your subject, feather it 45 degrees across their shoulder rather than pointing directly at their face.\n\nSoft light is created by apparent light size, not lower wattage. #StudioPhotography #CreatorMediaLab"
            ]
        }
    },
    {
        "slot_id": "slot_3_afternoon",
        "name": "Afternoon Monetization & Service Spotlight",
        "target_time": "17:00",
        "description": "Spotlight on live Fiverr gigs and high-earning digital products",
        "tweets": {
            "creatorpulselab": [
                "✨ Upgrading your digital creator storefront or video editing workflow? Clean visual branding pays for itself in client retention.\n\nExplore our custom creator media kits, video editing templates, and asset flywheels:\nhttps://digitalcreatorassets-source.github.io/creatormedialab/ ⚡ @creatorpulselab #CreatorEconomy #DigitalCreator"
            ],
            "TheCreatorAsset": [
                "🎨 Editorial Photo Retouching & Film Color Grading for creators and photographers.\n\nFrequency separation, non-destructive dodge & burn, and Portra/Cinestill film emulation starting at $20:\nhttps://www.fiverr.com/s/GPz71VL 📸 @TheCreatorAsset #PhotoRetouching #LightroomPresets"
            ]
        }
    },
    {
        "slot_id": "slot_4_evening",
        "name": "Prime Evening Video Cuts & Asset Flywheel",
        "target_time": "20:30",
        "description": "Video trailer teasers, 9:16 vertical cuts & multi-channel promo",
        "tweets": {
            "creatorpulselab": [
                "🎬 Turn your long-form shoots into 60s viral teasers, 9:16 TikTok crops, and high-retention video assets.\n\nAll media processed 100% locally with NVENC 60fps hardware encoding:\nhttp://www.fiverr.com/s/emmRYZm ⚡ @creatorpulselab #CreatorEconomy #VideoEditing"
            ],
            "TheCreatorAsset": [
                "⚡ The Creator Media Asset Flywheel: Shoot once. Cut 60s trailers. Extract 6 high-res poses. Synthesize platform copy. Distribute across 5 channels.\n\nRead our full media automation guide:\nhttps://digitalcreatorassets-source.github.io/creatormedialab/ 📸 @TheCreatorAsset #ContentCreation #CreatorMediaLab"
            ]
        }
    },
    {
        "slot_id": "slot_5_latenight",
        "name": "Late Night Community Engagement",
        "target_time": "23:00",
        "description": "Late-night data-backed monetization breakdown & studio color tips",
        "tweets": {
            "creatorpulselab": [
                "🌙 Digital Offer Pricing Breakdown: Across 1,400+ creator campaigns, the $18–$22 bracket converts at 24.3% with the highest revenue per recipient. $12 gets volume but leaves money on the table; $28 drops conversion to 8.1%. Sweet spot: A $19 micro-asset bundle with a 15s tutorial clip. 📈 @creatorpulselab #CreatorEconomy #ContentStrategy"
            ],
            "TheCreatorAsset": [
                "🌙 Night studio tip: Always calibrate your monitor to 120 cd/m² when editing in dim lighting. Over-bright screens lead to dark, muddy exports on client phones. Goodnight creators. ✨ @TheCreatorAsset #StudioPhotography #EditingTips"
            ]
        }
    }
]

# Pinterest content pool - CreatorMediaLab / @TheCreatorAsset (mainstream brand) ONLY.
# There is deliberately no equivalent list for the adult_creator_brand ("creatorpulselab") -
# Pinterest's Community Guidelines prohibit sexual content, nudity, and promotion of cam/
# webcam services, so that brand must never have a Pinterest content source at all. Every
# entry here still passes through PinterestPoster.is_pinterest_safe() before publishing as
# defense-in-depth, with content_type hardcoded to "general".
PINTEREST_DAILY_CONTENT = [
    {
        "title": "Kodak Portra 400 Film Color Grade Tutorial",
        "description": "Studio photography color science: how to recreate the Kodak Portra 400 film look in Lightroom with tone curve and HSL adjustments. Free masterclass from CreatorMediaLab.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire"
    },
    {
        "title": "Cinematic 3D LUT Pack for Premiere Pro & DaVinci Resolve",
        "description": "7 Signature film color grading 3D LUTs (.CUBE) for filmmakers and videographers. Kodak Portra 400, Cinestill 800T, Teal & Orange, and Fuji Provia. Instant digital download.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "150+ FLUX.1 & Midjourney v6 AI Prompt Bible",
        "description": "Master prompt engineering swipe file and interactive lookbook for photorealistic studio portraits, commercial product photography, and architectural lighting.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Convert 2D Photo into 3D PBR Model (.GLB/.OBJ)",
        "description": "Neural photogrammetry pipeline: turn single product shots or photos into production-ready 3D models with 4K PBR textures for Unreal Engine, Unity, and Shopify AR.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "Animate Still Photos into 4K 60fps Cinematic Video Loops",
        "description": "Seamless video loop synthesis: bring your still portrait or product photography to life with natural micro-motion and dynamic camera moves. Perfect for Spotify Canvas and video reels.",
        "link": "http://www.fiverr.com/s/emmRYZm"
    },
    {
        "title": "Studio Portrait Relighting & Luxury Backdrop Transformation",
        "description": "Physically accurate AI portrait relighting and environment transformation. Upgrade headshots with Rembrandt studio key lighting and high-rise penthouse office backdrops.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "45-Degree Studio Lighting Setup Guide",
        "description": "A simple studio lighting rule of thumb for soft, flattering portrait light using key light feathering and apparent light size. #StudioPhotography",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Editorial Photo Retouching & Film Emulation Presets",
        "description": "Frequency separation, non-destructive dodge & burn, and Portra/Cinestill film color grading presets for photographers and creators.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "The Creator Media Asset Flywheel",
        "description": "Shoot once, cut trailers, extract poses, synthesize platform copy, and distribute across channels. A full media automation guide for creators.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/"
    },
    {
        "title": "Lightroom Preset Pack for Studio Portraits",
        "description": "Master studio preset pack (.XMP) for editorial-quality portrait photography and color grading.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Rembrandt Lighting for Portrait Photographers",
        "description": "How to set up classic Rembrandt lighting with a single key light and reflector fill for moody, dimensional portraits. #PortraitLighting",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire"
    },
    {
        "title": "Frequency Separation Retouching Walkthrough",
        "description": "Non-destructive skin retouching with frequency separation - smooth texture without losing detail. Step-by-step guide for editorial photographers.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "Cinestill 800T Color Grade Recipe",
        "description": "Recreate the Cinestill 800T halation and tungsten-balanced look digitally with tone curve and split-toning adjustments.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire"
    },
    {
        "title": "Golden Hour Outdoor Portrait Checklist",
        "description": "Camera settings, positioning, and reflector tips for warm, flattering golden-hour environmental portraits.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Editorial Headshot Posing Guide",
        "description": "Confident, natural posing cues for studio headshots and editorial portrait sessions - angles, hands, and expression direction.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/"
    },
    {
        "title": "Beauty Dish vs Softbox: Which Modifier to Use",
        "description": "A practical comparison of beauty dish and softbox light quality for portrait and editorial photography.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "Kodak Gold 200 Film Emulation Preset",
        "description": "Warm, nostalgic Kodak Gold 200 color grading preset pack for Lightroom - great for outdoor and lifestyle shoots.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Dodge & Burn for Dimensional Portrait Retouching",
        "description": "Add depth and sculpt light on skin with non-destructive dodge and burn layers - a core editorial retouching technique.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "Building a Repeatable Creator Content Workflow",
        "description": "From shoot planning to multi-platform distribution: a repeatable system for consistent, high-quality creator content output.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/"
    }
]

class HeraldScheduler:
    DAILY_SLOTS = DAILY_SLOTS

    def __init__(self, config_path: str = "F:/WORKHORSE/config.json",
                 newsletter_workspace_base: Optional[str] = None,
                 state_file: Optional[str] = None):
        self.config_path = config_path
        self.twitter = TwitterPoster(config_path)
        self.pinterest = PinterestPoster(config_path)
        # Optional override so a test (or any future caller) can fully isolate this
        # scheduler's newsletter sub-dispatcher from the real F:/WORKHORSE/workspace -
        # without this, constructing a HeraldScheduler always touched the real
        # newsletter_logs dir and subscribers file regardless of config_path.
        self.newsletter = (
            NewsletterManager(workspace_base=newsletter_workspace_base)
            if newsletter_workspace_base else NewsletterManager()
        )
        # Same isolation need for the daily-schedule-state file, which previously was
        # only ever the hardcoded module-level STATE_FILE constant with no per-instance
        # override at all.
        self.state_file = Path(state_file) if state_file else STATE_FILE
        self.is_running = False
        self._load_state()

    def _pick_from_pool(self, brand_key: str, pool: list, state_key: str) -> str:
        """Selects an entry from the given prompt pool for this brand while avoiding
        recent repeats - the same entry won't be reused until every other variant in
        the pool has had a turn, so a week of daily posts doesn't end up visually or
        texturally samey even though each individual generation is already a fresh
        render with its own random seed. Shared helper for both image prompts and
        video motion prompts."""
        recent_map = self.state.setdefault(state_key, {})
        recent = recent_map.setdefault(brand_key, [])

        lookback = max(0, len(pool) - 1)
        recently_used = set(recent[-lookback:]) if lookback else set()
        available = [i for i in range(len(pool)) if i not in recently_used]
        if not available:
            available = list(range(len(pool)))

        chosen_idx = random.choice(available)
        recent.append(chosen_idx)
        recent_map[brand_key] = recent[-20:]
        self._save_state()
        return pool[chosen_idx]

    def _craft_topic_visual_prompt(self, brand_key: str, topic_text: Optional[str] = None, variant_seed: int = 0) -> str:
        """
        Dynamically crafts an on-brand, high-fidelity visual prompt that DIRECTLY MATCHES
        the subject matter and action of today's post or newsletter, rather than rolling a generic prompt.
        Incorporates dynamic creator actions (grading, adjusting lights, reviewing sales, shooting on location),
        non-human scenes (macro flat-lays, camera rigs, editing suites), and diverse flattering wardrobes
        across the 5 approved commercial moods (Sexy/Alluring, Playful, Cute, Cozy, High-Fashion).
        variant_seed allows generating multiple distinct creative interpretations of the same topic.
        """
        if not topic_text or len(topic_text.strip()) < 8:
            return self._pick_image_prompt(brand_key)

        txt_lower = topic_text.lower()

        # 1. Monitor Calibration / Display Screen Tuning / 120 cd/m² / Dim Lighting
        # (Placed BEFORE generic lighting so 'editing in dim lighting' never misfires as flash equipment!)
        if any(k in txt_lower for k in ["calibrat", "monitor", "120 cd", "display", "screen", "spyder", "colorchecker", "gamma"]):
            variants = [
                "Atmospheric night studio session, creator in a comfortable soft camisole and draped knit cardigan holding a monitor calibrator against an Apple Studio Display, dim ambient warm desk lamp, 120 cd/m² calibration, 35mm lens, photorealistic commercial aesthetic",
                "Professional creative director in an alluring silk wrap blouse refining display color calibration and gamma curves at an ultrawide monitor in a moody night editing suite, warm amber lamp, city skyline lights outside, 50mm f/1.4",
                "Aesthetic midnight editing workstation setup, ultrawide display showing monitor calibration color patches and waveforms, studio headphones on stand, steaming ceramic mug, subtle violet neon edge lighting, 35mm lens",
                "Creator sitting at high-end color-calibrated dual editing screens with a monitor hood in dim ambient studio lighting, reviewing accurate skin tones, focused confident expression, 50mm prime"
            ]
            return variants[variant_seed % len(variants)]

        # 2. Color Science / Portra / Cinestill / Lightroom / Tone Curve / HSL / Presets / LUTs
        elif any(k in txt_lower for k in ["portra", "cinestill", "tone curve", "hsl", "lightroom", "color grade", "preset", "color science", "palette", "lut", "saturation"]):
            variants = [
                "Attractive photographer wearing a chic emerald satin cowl-neck slip dress actively adjusting DaVinci color wheels and tone curves at an Apple Studio Display editing station, warm studio glow, vivid film tones on screen, professional 85mm portrait, 8k resolution",
                "Creator in a cute white ribbed crop tank top holding vintage 35mm Kodak Portra film negative strips up to an illuminated desktop light box with a loupe, warm natural daylight, smiling focused expression, 50mm f/1.8 lens",
                "High-fashion beauty photograph showcasing authentic Kodak Portra 400 color science, model in an alluring low-cut silk wrap top with delicate gold necklace, luminous warm skin tones, velvety matte shadows, 85mm f/1.4 prime",
                "Macro commercial flat-lay of vintage Kodak Portra 400 and Cinestill 800T film canisters, Loupedeck color grading console, Pantone color chips, and Leica camera on dark oak desk, soft 5600K studio light, 50mm macro"
            ]
            return variants[variant_seed % len(variants)]

        # 3. Retouching / Frequency Separation / Dodge & Burn / Skin Pores
        elif any(k in txt_lower for k in ["retouch", "frequency separation", "dodge", "burn", "skin pore", "skin texture", "pore", "texture", "blemish"]):
            variants = [
                "High-fashion beauty close-up, gorgeous model in an attractive low-cut satin camisole, authentic natural skin texture with visible pores, radiant eye catchlights, soft beauty dish lighting, clean direct sightline, 105mm macro",
                "Digital retoucher's hands using a Wacom stylus pen sculpting light and shadow on a high-res beauty portrait on a Cintiq display, split frequency separation visible on screen, warm desk lamp, 50mm prime",
                "Radiant creator in a cute ribbed tank top smiling into a vanity mirror ring light, glowing authentic skin highlight roll-off, delicate gold chain, clean modern dressing room backdrop, 85mm lens"
            ]
            return variants[variant_seed % len(variants)]

        # 4. Digital Product Monetization / Pricing Tiers ($19, $49, $149) / Value Ladders / Micro-Assets / Checkout Pages / Revenue
        elif any(k in txt_lower for k in ["monetiz", "pricing", "$19", "$49", "$149", "ladder", "micro-asset", "checkout", "revenue", "tier", "storefront", "sales", "passive income", "funnel", "offer", "etsy"]):
            variants = [
                "Sun-drenched luxury creator lifestyle, attractive creator wearing a chic metallic gold string bikini lounging on a teak sunlounger beside an infinity pool, smiling while reviewing daily Stripe sales analytics on an iPad, sparkling turquoise water backdrop, 85mm commercial lens",
                "Radiant creator in a cute white ribbed tank top and denim shorts holding up sleek digital template download cards at a modern sunlit agency desk, smiling proudly, dual editing screens showing revenue growth, 50mm prime",
                "Cozy creator in an oversized chunky oat cable-knit off-shoulder sweater curled up on a sunlit window seat with a warm ceramic coffee mug, laughing while reviewing creator revenue dashboard on a MacBook, 35mm film aesthetic",
                "Modern creative flat-lay: iPad Pro displaying digital asset value ladder pricing tiers ($19, $49, $149), Sony mirrorless camera, revenue blueprint notebook, and cold brew coffee on white marble desk, 50mm macro"
            ]
            return variants[variant_seed % len(variants)]

        # 5. Video Editing / Loops / 4K 60fps / Motion Teasers / Vertical Cuts / TikTok & Reels / Hardware Encoding
        elif any(k in txt_lower for k in ["video", "loop", "60fps", "teaser", "9:16", "reel", "tiktok", "cut", "encode", "nvenc", "trailer", "motion", "clip"]):
            variants = [
                "Dynamic cinematic motion shot, alluring creator wearing a sculpted open-back halter dress walking fluidly along an oceanfront boardwalk during golden hour, cinematic breeze moving hair, camera tracking smoothly, 50mm prime",
                "Playful creator in a cute cropped baby tee and vintage cutoffs smiling and filming dynamic vertical video reels with a smartphone gimbal on a sunlit city rooftop terrace, 35mm lens",
                "Late-night video editing bay, creative editor at an ultrawide curved monitor editing a fast-paced 60fps dynamic timeline with purple and cyan ambient rim glow, hands on jog-wheel controller, 50mm lens",
                "Close-up of professional cinema camera rig with follow-focus on an electronic gimbal catching golden lens flares at sunset, high production value commercial shot, 85mm f/1.4"
            ]
            return variants[variant_seed % len(variants)]

        # 6. Studio Lighting Modifiers & Flash Gear (Softbox / Beauty Dish / Rembrandt / Feathering)
        # Note: 'lighting' is guarded by specific modifiers so ambient phrases like 'dim lighting' don't misfire
        elif any(k in txt_lower for k in ["feather", "45", "softbox", "beauty dish", "rembrandt", "key light", "modifier", "studio lighting", "clamshell", "reflector fill", "c-stand"]):
            variants = [
                "Alluring creator in a sculpted black strapless sweetheart mini dress posing in a photo studio, dramatic 45-degree feathered key light from a large parabolic softbox casting soft dimensional shadows across her shoulder, 85mm f/1.4 lens",
                "Photographer in a cute tie-front linen crop top actively positioning a 48-inch softbox on a C-stand in a professional studio, clear line of sight, warm backlight glow, candid working-artist energy, 50mm prime",
                "High-fashion commercial studio portrait, model in an alluring backless slip dress illuminated by Rembrandt triangle lighting and silver reflector fill, luminous skin, magazine editorial aesthetic, 85mm lens",
                "Behind-the-scenes studio lighting masterclass setup, large Profoto beauty dish on boom arm with honeycomb grid, silver reflector clamshell, seamless grey studio backdrop, soft atmospheric haze, 35mm lens"
            ]
            return variants[variant_seed % len(variants)]

        # 7. 3D Photogrammetry / Neural Mesh / PBR / AR
        elif any(k in txt_lower for k in ["3d", "pbr", "mesh", "photogrammetry", "neural", "turntable", "glb", "obj"]):
            variants = [
                "Creator in a cute fitted athletic tank top holding a mirrorless camera scanning a physical product on an automated rotating turntable, ultrawide studio display showing real-time 3D PBR wireframe, 35mm lens",
                "Sleek high-tech studio visual: 3D textured asset turntable rotating on an aesthetic pedestal with studio rim lighting, holographic material maps visible, modern creative lab aesthetic, 50mm lens"
            ]
            return variants[variant_seed % len(variants)]

        # 8. Flywheel / Repurposing / Shoot Once
        elif any(k in txt_lower for k in ["flywheel", "repurpos", "shoot once", "distribute", "workflow", "system"]):
            variants = [
                "Creative agency founder in an attractive low-cut linen wrap top organizing multi-channel storyboards and video clips on a whiteboard and iPad in a modern sunny loft atelier, 50mm prime",
                "Behind-the-scenes multi-camera production setup around an alluring model in a chic yellow sundress, showing the multi-format content asset flywheel in action, 35mm lens"
            ]
            return variants[variant_seed % len(variants)]

        # Fallback to rich mood-curated prompt pool
        return self._pick_image_prompt(brand_key)

    def _pick_image_prompt(self, brand_key: str) -> str:
        """Selects an image prompt for this brand, avoiding recent repeats."""
        return self._pick_from_pool(brand_key, BRAND_VIBES[brand_key]["prompts"], "recent_image_prompts")

    def _pick_motion_prompt(self, brand_key: str, topic_text: Optional[str] = None) -> str:
        """Selects a video motion/camera-movement prompt that matches the topic and action."""
        if topic_text:
            txt_lower = topic_text.lower()
            if any(k in txt_lower for k in ["monitor", "calibrat", "screen", "display", "gamma"]):
                return "gentle cinematic slow push-in toward creator focused on calibrating monitor screen, ambient warm desk glow, 24fps"
            elif any(k in txt_lower for k in ["video", "loop", "motion", "reel", "60fps", "teaser", "clip"]):
                return "smooth cinematic gimbal tracking move, subject gracefully moving with natural breeze in hair, radiant confident expression, 24fps"
            elif any(k in txt_lower for k in ["feather", "softbox", "beauty dish", "rembrandt", "key light", "studio lighting"]):
                return "slow cinematic push-in on subject framed by softbox key light, subtle confident eye contact, warm rim light shift, 24fps"
            elif any(k in txt_lower for k in ["color", "grade", "portra", "film", "hsl", "curve", "edit"]):
                return "creator gently adjusting dials on color console, screen light reflecting softly, natural breathing, cinematic 24fps"
            elif any(k in txt_lower for k in ["monetiz", "pricing", "revenue", "pool", "resort"]):
                return "gentle breeze moving hair, golden sunlight rippling on pool water, relaxing happy smile toward camera, cinematic slow motion"
            elif any(k in txt_lower for k in ["cozy", "sweater", "coffee", "morning"]):
                return "taking a sip from ceramic mug, relaxing back with warm natural smile, soft morning light drift, cinematic motion"

        pool = BRAND_VIBES[brand_key].get("video_motion_prompts") or [
            "subtle natural motion, gentle cinematic movement, high production value, photorealistic"
        ]
        return self._pick_from_pool(brand_key, pool, "recent_motion_prompts")

    def _get_brand_visual_for_post(self, handle: str, topic_text: Optional[str] = None) -> Optional[str]:
        """
        Generates a FRESH, on-brand image that MATCHES the specific post topic (each account
        has its own distinct vibe/audience) rather than reusing a leftover render. The render
        goes through the standard Iris QC gate; only a passed image is ever returned.
        Falls back to the latest already-verified render for this brand if ComfyUI is
        offline or the fresh generation fails/fails QC - never returns an unverified file.
        Passes multiple alternative topic variants so if attempt 1 fails Iris QC, it restarts
        with a fresh prompt instead of repeating the failed prompt.
        """
        is_pulse = "pulse" in handle.lower()
        brand_key = "creator_pulse_lab" if is_pulse else "creator_media_lab"
        pub_key = "creator_pulse" if is_pulse else "studio_wire"
        vibe = BRAND_VIBES[brand_key]

        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            prompt = self._craft_topic_visual_prompt(brand_key, topic_text, variant_seed=0)
            alt_prompts = [
                self._craft_topic_visual_prompt(brand_key, topic_text, variant_seed=i)
                for i in range(1, 4)
            ]
            gen_res = comfy_bridge.generate_and_audit(
                positive_prompt=prompt,
                negative_prompt=vibe["negative_prompt"],
                checkpoint="epicrealismXL_vxviiCrystalclear.safetensors",
                brand_target=vibe["brand_target"],
                auto_qc=True,
                prompt_alternatives=alt_prompts
            )
            if gen_res.get("success") and gen_res.get("qc_audit", {}).get("passed") and gen_res.get("qc_audit", {}).get("is_sfw", False):
                print(f"[Herald Scheduler] Fresh on-brand visual generated for @{handle}: {gen_res.get('filename')}")
                return gen_res.get("file_path")
            print(f"[Herald Scheduler] Fresh visual for @{handle} did not pass Iris QC / SFW gate, falling back to last verified render.")
        except Exception as e:
            print(f"[Herald Scheduler] Fresh visual generation unavailable for @{handle} ({e}), falling back to last verified render.")

        # Safety net: last known IRIS-verified render for this brand (never an unaudited file)
        vis_path = self.newsletter.get_latest_comfy_visual(pub_key)
        return str(vis_path) if vis_path else None

    def _verify_media_is_strictly_sfw(self, file_path: Union[str, Path]) -> bool:
        """
        FAIL-CLOSED SFW MEDIA GATE:
        Verifies that any image or video destined for public posting (Twitter, Pinterest, newsletters):
        1. Does not contain any adult/boudoir keywords in its filename.
        2. Does not reside in an adult/quarantine path.
        3. If present in comfy_qc_audit.json:
           - must have passed=True
           - must have is_sfw=True (or not False)
           - must not have nudity_or_nsfw=True
           - must not have recommendation='REJECT_NSFW_CONTENT'
           - prompt must not contain any adult/boudoir tokens.
        """
        p = Path(file_path)
        name_lower = p.name.lower()
        if any(k in name_lower for k in SFW_BLOCKED_KEYWORDS):
            return False

        path_lower = str(p).lower()
        blocked_path_markers = [
            "qc_rejected", "client_character_renders", "boudoir", "onlyfans", "fansly"
        ]
        if any(m in path_lower for m in blocked_path_markers):
            return False

        # 1. DETERMINISTIC PIXEL-LEVEL NSFW & SKIN-DENSITY FIREWALL (Zero-tolerance mathematical gate)
        try:
            from pipeline.stages.nsfw_firewall import evaluate_image_sfw, evaluate_video_sfw
            suffix = p.suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".webp"):
                is_safe, reason, metrics = evaluate_image_sfw(p)
                if not is_safe:
                    print(f"[Herald Safety Alert] REJECTED non-SFW image by pixel firewall: {p.name} ({reason})")
                    return False
            elif suffix in (".mp4", ".mov", ".webm", ".m4v"):
                is_safe, reason, metrics = evaluate_video_sfw(p)
                if not is_safe:
                    print(f"[Herald Safety Alert] REJECTED non-SFW video by pixel firewall: {p.name} ({reason})")
                    return False
        except Exception as fe:
            print(f"[Herald Safety Alert] Pixel firewall execution error ({fe}). Failing closed for safety.")
            return False

        # 2. Inspect audit history
        audit_log = Path("F:/WORKHORSE/workspace/comfy_qc_audit.json")
        if audit_log.exists():
            try:
                records = safe_read_json(audit_log, default=[])
                for r in records:
                    if r.get("filename") == p.name:
                        if not r.get("passed") or r.get("is_sfw") is False or r.get("nudity_or_nsfw"):
                            return False
                        if r.get("recommendation") == "REJECT_NSFW_CONTENT":
                            return False
                        prompt_str = (r.get("prompt") or "").lower()
                        if any(k in prompt_str for k in SFW_BLOCKED_KEYWORDS):
                            return False
                        break
            except Exception:
                pass

        return True

    def _maybe_upgrade_to_video(self, handle: str, slot_id: str, still_image_path: str, topic_text: Optional[str] = None) -> Optional[str]:
        """
        For the one designated daily "video slot" (per-brand config), converts the
        freshly-generated still image into a short video instead of posting a static
        image. Disabled by default; returns None (keep the still) if video_posting is
        disabled, misconfigured, this isn't the configured slot, or generation fails/
        times out - Herald never blocks or fails a scheduled post over this.

        BRAND SAFETY: the MiniMax H3 engine's adult/boudoir-tuned LoRAs are only ever
        reachable for the adult_creator_brand ("creatorpulselab"), and only when that
        brand's own config explicitly sets engine="minimax_h3" - creator_media_lab
        (mainstream/@TheCreatorAsset) can NEVER reach the adult-tuned path, regardless
        of what any config value says, full stop.
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            return None

        is_pulse = "pulse" in handle.lower()
        brand_key = "creator_pulse_lab" if is_pulse else "creator_media_lab"
        brand_cfg_key = "adult_creator_brand" if is_pulse else "main_brand"
        video_cfg = cfg.get("marketing_channels", {}).get(brand_cfg_key, {}).get("video_posting", {})

        if not video_cfg.get("enabled"):
            return None
        if video_cfg.get("slot_id") != slot_id:
            return None

        engine = (video_cfg.get("engine") or "ltx2.3").strip().lower()
        duration_seconds = video_cfg.get("duration_seconds", 8)
        motion_prompt = self._pick_motion_prompt(brand_key, topic_text=topic_text)

        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            # STRICT NSFW GUARDRAIL: Herald is an automated publisher posting to public
            # social channels and newsletters. Under the Commander's strict directive,
            # Herald CANNOT produce or post nude images or video. Adult-tuned LoRAs are
            # strictly disabled in automated social dispatches (lora_config=[]).
            anti_nude_neg = "nude, nudity, naked, topless, bare breasts, exposed nipples, genitals, explicit, nsfw, porn, sexual, uncensored, erotica, extra limbs, bad anatomy, blurry"
            if engine in ("minimax_h3", "minimax") and brand_key == "creator_pulse_lab":
                vid_res = comfy_bridge.generate_image_to_video_minimax(
                    source_image_path=still_image_path,
                    prompt=motion_prompt,
                    duration_seconds=duration_seconds,
                    lora_config=[],  # Strictly zeroed out: NO adult/boudoir LoRAs for autonomous social posts
                    dest_subdir=brand_key
                )
            else:
                vid_res = comfy_bridge.generate_image_to_video(
                    source_image_path=still_image_path,
                    prompt=motion_prompt,
                    negative_prompt=anti_nude_neg,
                    num_frames=int(duration_seconds * 24),
                    fps=24,
                    dest_subdir=brand_key
                )
            if vid_res.get("success"):
                print(f"[Herald Scheduler] Upgraded @{handle} {slot_id} post to video: {vid_res.get('filename')}")
                return vid_res.get("file_path")
            print(f"[Herald Scheduler] Video generation failed for @{handle}, keeping static image: {vid_res.get('error')}")
        except Exception as e:
            print(f"[Herald Scheduler] Video generation error for @{handle}, keeping static image: {e}")
        return None

    def _load_state(self) -> Dict[str, Any]:
        loaded = safe_read_json(self.state_file, default=None)
        if isinstance(loaded, dict) and loaded:
            self.state = loaded
            for pub_id in ALL_MONITORED_PUBLICATIONS:
                self.state.setdefault(f"{pub_id}_attempts", 0)
                self.state.setdefault(f"{pub_id}_alerted_today", False)
            self.state.setdefault("content_engine_sent_today", False)
            self.state.setdefault("content_engine_attempts", 0)
            self.state.setdefault("content_engine_alerted_today", False)
            return self.state

        self.state = {
            "last_date": str(date.today()),
            "executed_slots": [],
            "newsletters_sent_today": False,
            "studio_wire_sent_today": False,
            "creator_pulse_sent_today": False,
            "creator_blueprint_sent_today": False,
            "content_engine_sent_today": False,
            "content_engine_attempts": 0,
            "content_engine_alerted_today": False,
            "history": []
        }
        for pub_id in ALL_MONITORED_PUBLICATIONS:
            self.state.setdefault(f"{pub_id}_attempts", 0)
            self.state.setdefault(f"{pub_id}_alerted_today", False)
        self._save_state()
        return self.state

    def _save_state(self):
        try:
            atomic_write_json(self.state_file, self.state)
        except Exception as e:
            logger.error(f"Failed to save schedule state: {e}")

    def _check_day_rollover(self):
        today_str = str(date.today())
        if self.state.get("last_date") != today_str:
            self.state["last_date"] = today_str
            self.state["executed_slots"] = []
            self.state["slot_accounts_succeeded_today"] = {}
            self.state["newsletters_sent_today"] = False
            self.state["radar_sweep_done_today"] = False
            self.state["studio_wire_sent_today"] = False
            self.state["creator_pulse_sent_today"] = False
            self.state["creator_blueprint_sent_today"] = False
            self.state["content_engine_sent_today"] = False
            self.state["content_engine_attempts"] = 0
            self.state["content_engine_alerted_today"] = False
            self.state["pinterest_posted_today"] = False
            self.state["pinterest_attempts"] = 0
            self.state["pinterest_alerted_today"] = False
            for pub_id in ALL_MONITORED_PUBLICATIONS:
                self.state[f"{pub_id}_attempts"] = 0
                self.state[f"{pub_id}_alerted_today"] = False
            for s in DAILY_SLOTS:
                self.state[f"{s['slot_id']}_attempts"] = 0
                self.state[f"{s['slot_id']}_alerted_today"] = False
            self._save_state()
            print(f"[Herald Scheduler] Day rollover to {today_str}. Schedule reset for 5 new slots.")

    def get_status(self) -> Dict[str, Any]:
        self._check_day_rollover()
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        slots_status = []
        for s in DAILY_SLOTS:
            is_done = s["slot_id"] in self.state.get("executed_slots", [])
            slots_status.append({
                "slot_id": s["slot_id"],
                "name": s["name"],
                "target_time": s["target_time"],
                "executed": is_done,
                "due": not is_done and current_time_str >= s["target_time"]
            })

        return {
            "status": "active" if self.is_running else "standby",
            "date": str(date.today()),
            "current_time": current_time_str,
            "newsletters_sent_today": self.state.get("newsletters_sent_today", False),
            "publications_sent_today": {
                pub_id: self.state.get(f"{pub_id}_sent_today", False)
                for pub_id in PUBLICATION_SCHEDULE
            },
            "content_engine_sent_today": self.state.get("content_engine_sent_today", False),
            "content_engine_attempts": self.state.get("content_engine_attempts", 0),
            "executed_slots_count": len(self.state.get("executed_slots", [])),
            "total_slots": len(DAILY_SLOTS),
            "slots": slots_status,
            "recent_history": self.state.get("history", [])[-10:]
        }

    get_daily_schedule_state = get_status

    def _optimize_thread_for_exposure(self, handle: str, tweets: List[str]) -> List[str]:
        """
        Social Media Strategy & Exposure Optimizer (Herald [33 As]):
        Ensures outbound tweets/threads are optimized for maximal X/Twitter discoverability
        by appending 2-3 curated, niche-relevant hashtags to standalone tweets and to the
        closing tweet of a thread, strictly enforcing Twitter's 280-character limit.
        """
        if not tweets:
            return tweets

        clean_handle = handle.lstrip("@").strip()
        tags_pool = BRAND_HASHTAGS.get(clean_handle, BRAND_HASHTAGS["TheCreatorAsset"])

        optimized = list(tweets)
        target_idx = -1  # Closing tweet is the primary anchor for hashtags & calls to action

        closing_tweet = optimized[target_idx]
        if "#" not in closing_tweet:
            available_space = 280 - len(closing_tweet) - 2
            chosen_tags = []
            for tag in tags_pool:
                if len(" ".join(chosen_tags + [tag])) <= available_space:
                    chosen_tags.append(tag)
                if len(chosen_tags) >= 2:
                    break

            if chosen_tags:
                tag_str = " ".join(chosen_tags)
                separator = "\n\n" if "\n" in closing_tweet else " "
                if len(closing_tweet) + len(separator) + len(tag_str) <= 280:
                    optimized[target_idx] = f"{closing_tweet}{separator}{tag_str}"

        return optimized

    def _generate_non_duplicate_thread(self, handle: str, slot_id: str) -> Optional[List[str]]:
        """Synthesizes a fresh, non-duplicate thread on demand when a slot's candidate thread
        collides with recent 7-day tweet history."""
        try:
            from pipeline.stages.trend_researcher import trend_researcher
            from shared.ai_providers import AIProviderService, parse_llm_json
            is_pulse = "pulse" in handle.lower()
            pub_id = "creator_pulse" if is_pulse else "studio_wire"
            if slot_id == "slot_1_morning":
                refreshed = self.newsletter._get_daily_scribe_content(pub_id, auto_generate=True, force_refresh=True)
                cand = (refreshed or {}).get("tweet_thread")
                if cand and isinstance(cand, list) and not self.twitter._is_duplicate_tweet(cand[0]):
                    return cand

            articles = trend_researcher.get_research_articles_for_pub(pub_id)
            if not articles:
                vault = trend_researcher.run_daily_radar_sweep()
                articles = trend_researcher.get_research_articles_for_pub(pub_id)
            recent_snips = trend_researcher._get_recent_tweet_snippets(limit=15)
            ai = AIProviderService(str(self.config_path))
            niche_desc = (
                "creator economy monetization, audience retention, and digital product funnels (#CreatorEconomy #Monetization)"
                if is_pulse
                else "commercial studio photography, RAW color grading, and lighting setups (#StudioPhotography #ColorGrading)"
            )
            prompt = f"""Write a brand-new, high-authority 3-tweet educational thread for @{handle} ({niche_desc}) for slot {slot_id} on {date.today().isoformat()}.
Ground it in one of these current industry articles:
{json.dumps(articles[:4], indent=2)}

DO NOT repeat or resemble any of these recently posted hooks:
{json.dumps(recent_snips[:12], indent=2)}

Rules:
- 100% Safe For Work (SFW), plain text only (no ** markdown), under 250 characters per tweet.
- Tweet 1 starts with "1/3 ", Tweet 2 starts with "2/3 ", Tweet 3 starts with "3/3 ".
- Return valid JSON: {{"tweets": ["1/3 ...", "2/3 ...", "3/3 ..."]}}
"""
            raw = ai.call_ollama_text(prompt, system_prompt="Return valid JSON only.", json_mode=True, num_predict=1024)
            parsed = parse_llm_json(raw)
            if parsed and isinstance(parsed.get("tweets"), list) and len(parsed["tweets"]) >= 2:
                return [str(t).strip() for t in parsed["tweets"] if str(t).strip()]
        except Exception as e:
            print(f"[Herald Scheduler] On-demand non-duplicate synthesis notice for @{handle}: {e}")
        return None

    def dispatch_slot(self, slot_id: str) -> Dict[str, Any]:
        """Execute a specific tweet slot across both Twitter accounts."""
        self._check_day_rollover()
        slot = next((s for s in DAILY_SLOTS if s["slot_id"] == slot_id), None)
        if not slot:
            return {"status": "error", "message": f"Slot {slot_id} not found"}

        results = {"slot_id": slot_id, "timestamp": datetime.now().isoformat(), "accounts": {}}
        tweets_dict = dict(slot.get("tweets", {}))

        # 1. For slot_1_morning, cross-pollinate directly with today's morning newsletter lead story
        # so the daily newsletter drop and Twitter drop look unified and come from the exact same source
        if slot_id == "slot_1_morning":
            try:
                pulse_content = self.newsletter._get_daily_scribe_content("creator_pulse", auto_generate=True)
                if pulse_content and pulse_content.get("tweet_thread"):
                    tweets_dict["creatorpulselab"] = pulse_content["tweet_thread"]
                    print(f"[Herald Scheduler] Synchronized slot_1 for @creatorpulselab with Creator Pulse newsletter thread.")

                wire_content = self.newsletter._get_daily_scribe_content("studio_wire", auto_generate=True)
                if wire_content and wire_content.get("tweet_thread"):
                    tweets_dict["TheCreatorAsset"] = wire_content["tweet_thread"]
                    print(f"[Herald Scheduler] Synchronized slot_1 for @TheCreatorAsset with Studio Wire newsletter thread.")
            except Exception as e:
                print(f"[Herald Scheduler] Notice: could not bind slot_1 to newsletter thread: {e}")

        # 2. For other slots (midday, afternoon, evening, latenight), inject today's synthesized trend tweets
        else:
            try:
                from pipeline.stages.trend_researcher import trend_researcher
                vault = trend_researcher.load_vault()
                if vault.get("today_date") != str(date.today()):
                    print(f"[Herald Scheduler] Trend vault is stale (today_date={vault.get('today_date')!r}, expected {date.today()}) - triggering live radar sweep now for {slot_id}...")
                    vault = trend_researcher.run_daily_radar_sweep()
                daily_synth = vault.get("daily_synthesis", {})
                dynamic_slots = daily_synth.get("daily_slots", {})
                if slot_id in dynamic_slots:
                    dyn = dynamic_slots[slot_id]
                    for handle, dyn_tweets in dyn.items():
                        if dyn_tweets and len(dyn_tweets) > 0:
                            tweets_dict[handle] = dyn_tweets
                            print(f"[Herald Scheduler] Using dynamic trending tweets for @{handle} in {slot_id}")
            except Exception as e:
                print(f"[Herald Scheduler] Error reading dynamic tweets from vault: {e}")

        slot_done_map = self.state.setdefault("slot_accounts_succeeded_today", {})
        already_done_handles = set(slot_done_map.get(slot_id, []) or [])

        all_succeeded = True
        for handle, tweets in tweets_dict.items():
            if handle in already_done_handles:
                results["accounts"][handle] = {"success": True, "already_posted_today": True, "handle": handle}
                print(f"[Herald Scheduler] Skipping @{handle} for {slot_id} (already succeeded earlier today).")
                continue
            if tweets:
                if self.twitter._is_duplicate_tweet(tweets[0]):
                    print(f"[Herald Scheduler] Candidate root tweet for @{handle} in {slot_id} matched recent 7-day history — generating fresh replacement thread...")
                    fresh_tweets = self._generate_non_duplicate_thread(handle, slot_id)
                    if fresh_tweets:
                        tweets = fresh_tweets
                # STRICT 100% SFW TEXT FIREWALL: All external social posts must be SFW on all platforms
                sanitized_tweets = []
                for t in tweets:
                    t_clean = t.replace("**", "").replace("__", "").strip()
                    t_lower = t_clean.lower()
                    if any(k in t_lower for k in SFW_BLOCKED_KEYWORDS):
                        print(f"[Herald Safety Alert] Suppressed non-SFW tweet text from public post for @{handle}: {t_clean[:60]}...")
                    else:
                        sanitized_tweets.append(t_clean)
                if not sanitized_tweets:
                    print(f"[Herald Safety Alert] All tweets for @{handle} in {slot_id} were non-SFW. Suppressing post.")
                    results["accounts"][handle] = {"success": False, "error": "Suppressed non-SFW tweet content"}
                    all_succeeded = False
                    continue
                tweets = sanitized_tweets

                tweets = self._optimize_thread_for_exposure(handle, tweets)
                try:
                    media_paths = None
                    try:
                        post_topic = tweets[0] if (tweets and len(tweets) > 0) else None
                        try:
                            vis_path = self._get_brand_visual_for_post(handle, topic_text=post_topic)
                        except TypeError:
                            vis_path = self._get_brand_visual_for_post(handle)
                        if vis_path and Path(vis_path).exists():
                            media_paths = [str(vis_path)]
                            print(f"[Herald Scheduler] Topic-matched visual attached for @{handle} -> {Path(vis_path).name}")

                            video_path = self._maybe_upgrade_to_video(handle, slot_id, vis_path, topic_text=post_topic)
                            if video_path:
                                media_paths = [video_path]
                    except Exception as ve:
                        print(f"[Herald Scheduler] Visual lookup notice: {ve}")

                    # STRICT SFW MEDIA GATE: Only allow media verified as strictly SFW
                    if media_paths:
                        safe_media = [mp for mp in media_paths if self._verify_media_is_strictly_sfw(mp)]
                        if len(safe_media) < len(media_paths):
                            print(f"[Herald Safety Alert] Suppressed non-SFW or unverified media from @{handle}")
                        media_paths = safe_media if safe_media else None

                    post_res = self.twitter.post_thread(handle, tweets, media_paths=media_paths)
                    results["accounts"][handle] = post_res
                    if post_res.get("success"):
                        already_done_handles.add(handle)
                        slot_done_map[slot_id] = sorted(already_done_handles)
                    else:
                        all_succeeded = False
                    print(f"[Herald Scheduler] Posted {slot_id} to @{handle} (media={bool(media_paths)}): {post_res.get('success')}")
                except Exception as e:
                    results["accounts"][handle] = {"success": False, "error": str(e)}
                    all_succeeded = False

        # Only mark this slot "done" for the day if every account that had content to
        # post actually succeeded - a partial or total post failure (expired token,
        # API error, rate limit) must stay retryable instead of being silently
        # accepted as complete. This mirrors the newsletter dispatch-gap bug fixed
        # 2026-10-07 (verify real delivery, don't trust a one-shot attempt), which had
        # never been applied to Twitter dispatch until this 2026-10-09 self-healing audit.
        results["fully_succeeded"] = all_succeeded
        if all_succeeded and slot_id not in self.state["executed_slots"]:
            self.state["executed_slots"].append(slot_id)

        self.state["history"].append({
            "type": "twitter_slot",
            "slot_id": slot_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        })
        self._save_state()
        return results

    def dispatch_pinterest_daily(self) -> Dict[str, Any]:
        """
        Publishes one pin per day to the mainstream CreatorMediaLab/@TheCreatorAsset
        Pinterest board, sourced exclusively from PINTEREST_DAILY_CONTENT (general-brand
        content only). content_type is hardcoded to "general" here and re-verified inside
        PinterestPoster.create_pin()'s TOS safety gate - there is no path for
        adult_creator_brand content to reach this method.
        """
        self._check_day_rollover()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"Failed to read config.json: {e}"}

        pin_cfg = cfg.get("marketing_channels", {}).get("main_brand", {}).get("pinterest", {})
        if not pin_cfg.get("enabled"):
            return {"status": "skipped", "reason": "pinterest_disabled", "message": "Pinterest publishing is disabled in config.json (marketing_channels.main_brand.pinterest.enabled)."}

        board_id = pin_cfg.get("default_board_id", "").strip()
        if not board_id:
            return {"status": "skipped", "reason": "no_board_id", "message": "No default_board_id configured under marketing_channels.main_brand.pinterest."}

        day_index = date.today().toordinal() % len(PINTEREST_DAILY_CONTENT)
        content = PINTEREST_DAILY_CONTENT[day_index]

        vis_path = None
        try:
            vis_path = self._get_brand_visual_for_post("TheCreatorAsset")
        except Exception as e:
            print(f"[Herald Scheduler] Pinterest visual lookup notice: {e}")

        if not vis_path or not Path(vis_path).exists():
            result = {"status": "error", "message": "No verified brand visual available for Pinterest pin (ComfyUI unavailable and no fallback render found)."}
        else:
            # STRICT SFW FILTER: Pinterest cannot receive non-SFW media
            if not self._verify_media_is_strictly_sfw(vis_path):
                print(f"[Herald Safety Alert] Suppressed non-compliant visual from Pinterest pin: {vis_path}")
                vis_path = None

            if not vis_path:
                result = {"status": "error", "message": "Filtered non-compliant visual from Pinterest pin."}
                return result

            post_res = self.pinterest.create_pin(
                board_id=board_id,
                title=content["title"],
                description=content["description"],
                link=content.get("link", ""),
                image_path=vis_path,
                content_type="general"
            )
            result = {"status": "ok" if post_res.get("success") else "error", "content": content, "result": post_res}
            print(f"[Herald Scheduler] Pinterest daily pin dispatched: {post_res.get('success')} ({post_res.get('status', post_res.get('pin_url'))})")

        # Only mark today's pin as done if it actually posted - an error (ComfyUI
        # unavailable, expired token, Pinterest API error) must stay retryable instead
        # of being silently accepted as complete for the day. Same dispatch-gap bug
        # class fixed for newsletters 2026-10-07; applied here 2026-10-09.
        if result.get("status") == "ok":
            self.state["pinterest_posted_today"] = True
        self.state["history"].append({
            "type": "pinterest_pin",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": result
        })
        self._save_state()
        return result

    def _verify_dispensary_dispatch(self, timeout_s: int = 180) -> Dict[str, Any]:
        """Blocks until the dispensary_deals.py subprocess finishes, then inspects its
        captured log output for a real '[Email] Sent to' line. A clean exit code alone
        does NOT prove the email was actually sent - a 2026-10-07 bug had the script
        exit 0 while silently skipping send_email() entirely, with SMS masking it."""
        waited = 0
        while self.newsletter.run_status == "running" and waited < timeout_s:
            time.sleep(2)
            waited += 2
        status = self.newsletter.get_run_status()
        logs = status.get("recent_logs", "")
        email_confirmed = "[Email] Sent to" in logs
        email_disabled = "[Email] No recipients configured" in logs
        return {
            "success": status.get("status") == "completed" and (email_confirmed or email_disabled),
            "email_confirmed": email_confirmed,
            "process_status": status.get("status"),
            "logs_tail": logs[-800:]
        }

    def dispatch_newsletters_all(self) -> Dict[str, Any]:
        """Trigger the private Dispensary Deals dispatch (dispensary_deals.py subprocess),
        then BLOCK until it finishes and verify real email delivery before marking today's
        dispatch successful - a launched-OK subprocess is not proof the email went out."""
        self._check_day_rollover()
        launch_res = self.newsletter.trigger_dispatch()
        verify_res = self._verify_dispensary_dispatch()
        res = {**launch_res, **verify_res}
        if verify_res["success"]:
            self.state["newsletters_sent_today"] = True
        self.state["history"].append({
            "type": "newsletter_dispatch",
            "pub_id": "dispensary_deals",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": res
        })
        self._save_state()
        return res

    def dispatch_publication(self, pub_id: str) -> Dict[str, Any]:
        """Sends a public newsletter (studio_wire / creator_pulse / creator_blueprint) to its
        real subscriber list. Only marks today's send as successful if send_publication_now()
        confirms recipients were actually emailed - success=False or sent=0 must NOT be
        silently treated as 'done for today' (see 2026-10-07 dispatch-gap incident)."""
        self._check_day_rollover()
        res = self.newsletter.send_publication_now(pub_id)
        if bool(res.get("success")) and res.get("sent", 0) > 0:
            self.state[f"{pub_id}_sent_today"] = True
        self.state["history"].append({
            "type": "newsletter_dispatch",
            "pub_id": pub_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": res
        })
        self._save_state()
        return res

    def _monitor_and_remediate_publications(self):
        """Autonomous watchdog - called every 60s from run_loop(). For any publication
        whose target time has passed and hasn't been VERIFIED sent today, retries the
        dispatch (up to MAX_DISPATCH_RETRIES). Once retries are exhausted, logs a
        'needs_attention' incident and texts the Commander directly via Synapse's
        notify_commander - added 2026-10-07 so a dispatch failure can never again go
        unnoticed just because nothing checked back on it."""
        current_time = datetime.now().strftime("%H:%M")
        for pub_id, target in ALL_MONITORED_PUBLICATIONS.items():
            if current_time < target:
                continue

            sent_key = "newsletters_sent_today" if pub_id == "dispensary_deals" else f"{pub_id}_sent_today"
            if self.state.get(sent_key):
                continue

            attempts_key = f"{pub_id}_attempts"
            alerted_key = f"{pub_id}_alerted_today"
            attempts = self.state.get(attempts_key, 0)

            if attempts >= MAX_DISPATCH_RETRIES:
                if not self.state.get(alerted_key):
                    msg = (f"WORKHORSE ALERT: '{pub_id}' newsletter failed to send after "
                           f"{MAX_DISPATCH_RETRIES} automatic retries today. Manual check needed.")
                    print(f"[Herald Scheduler] {msg}")
                    try:
                        from pipeline.stages.ai_operator import ai_operator
                        ai_operator.log_incident(
                            f"newsletter_{pub_id}",
                            f"Failed to dispatch after {MAX_DISPATCH_RETRIES} attempts",
                            "Auto-retry exhausted - Commander notified via SMS.",
                            status="needs_attention"
                        )
                        ai_operator.notify_commander(msg)
                    except Exception as e:
                        print(f"[Herald Scheduler] Failed to notify commander: {e}")
                    self.state[alerted_key] = True
                    self._save_state()
                continue

            print(f"[Herald Scheduler] '{pub_id}' not yet confirmed sent today "
                  f"(attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Dispatching...")
            self.state[attempts_key] = attempts + 1
            self._save_state()
            if pub_id == "dispensary_deals":
                self.dispatch_newsletters_all()
            else:
                self.dispatch_publication(pub_id)

    def _monitor_and_remediate_twitter_slots(self):
        """Autonomous watchdog for daily Twitter slot dispatch, mirroring
        _monitor_and_remediate_publications - added after a 2026-10-09 self-healing
        audit found dispatch_slot() previously marked a slot 'done' for the day even
        when post_thread() failed for every account (expired token, API error, rate
        limit), with zero incident logging or Commander alert. Retries a not-yet-
        fully-successful slot up to MAX_DISPATCH_RETRIES, then alerts."""
        # Circuit Breaker: Master toggle for autonomous social dispatch
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            main_mktg = cfg.get("marketing_channels", {}).get("main_brand", {})
            if main_mktg.get("auto_post_enabled") is False or cfg.get("system", {}).get("twitter_auto_post_enabled") is False:
                return
        except Exception:
            pass

        current_time = datetime.now().strftime("%H:%M")
        for s in DAILY_SLOTS:
            slot_id = s["slot_id"]
            target = s["target_time"]
            if current_time < target:
                continue
            if slot_id in self.state.get("executed_slots", []):
                continue

            attempts_key = f"{slot_id}_attempts"
            alerted_key = f"{slot_id}_alerted_today"
            attempts = self.state.get(attempts_key, 0)

            if attempts >= MAX_DISPATCH_RETRIES:
                if not self.state.get(alerted_key):
                    msg = (f"WORKHORSE ALERT: Twitter slot '{slot_id}' failed to post to one "
                           f"or more accounts after {MAX_DISPATCH_RETRIES} automatic retries "
                           f"today. Manual check needed.")
                    print(f"[Herald Scheduler] {msg}")
                    try:
                        from pipeline.stages.ai_operator import ai_operator
                        ai_operator.log_incident(
                            f"twitter_{slot_id}",
                            f"Failed to post after {MAX_DISPATCH_RETRIES} attempts",
                            "Auto-retry exhausted - Commander notified via SMS.",
                            status="needs_attention"
                        )
                        ai_operator.notify_commander(msg)
                    except Exception as e:
                        print(f"[Herald Scheduler] Failed to notify commander: {e}")
                    self.state[alerted_key] = True
                    self._save_state()
                continue

            print(f"[Herald Scheduler] Twitter slot '{slot_id}' not yet confirmed fully "
                  f"posted today (attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Dispatching...")
            self.state[attempts_key] = attempts + 1
            self._save_state()
            self.dispatch_slot(slot_id)
            break  # Stagger dispatches: handle at most 1 slot per 60s watchdog pass to prevent burst spamming

    def _monitor_and_remediate_pinterest(self):
        """Autonomous watchdog for the daily Pinterest pin, mirroring
        _monitor_and_remediate_publications - added after the same 2026-10-09 audit
        found dispatch_pinterest_daily() marked 'pinterest_posted_today' True even on
        failure. Skips entirely (no retry/alert) if Pinterest is simply disabled or
        unconfigured in config.json - that's an intentional state, not a failure."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                pin_cfg = json.load(f).get("marketing_channels", {}).get("main_brand", {}).get("pinterest", {})
        except Exception:
            pin_cfg = {}

        if not pin_cfg.get("enabled") or not pin_cfg.get("default_board_id", "").strip():
            return

        current_time = datetime.now().strftime("%H:%M")
        pin_target = pin_cfg.get("daily_slot_time", "12:00")
        if current_time < pin_target:
            return
        if self.state.get("pinterest_posted_today"):
            return

        attempts = self.state.get("pinterest_attempts", 0)
        if attempts >= MAX_DISPATCH_RETRIES:
            if not self.state.get("pinterest_alerted_today"):
                msg = (f"WORKHORSE ALERT: Daily Pinterest pin failed to post after "
                       f"{MAX_DISPATCH_RETRIES} automatic retries today. Manual check needed.")
                print(f"[Herald Scheduler] {msg}")
                try:
                    from pipeline.stages.ai_operator import ai_operator
                    ai_operator.log_incident(
                        "pinterest_daily",
                        f"Failed to post after {MAX_DISPATCH_RETRIES} attempts",
                        "Auto-retry exhausted - Commander notified via SMS.",
                        status="needs_attention"
                    )
                    ai_operator.notify_commander(msg)
                except Exception as e:
                    print(f"[Herald Scheduler] Failed to notify commander: {e}")
                self.state["pinterest_alerted_today"] = True
                self._save_state()
            return

        print(f"[Herald Scheduler] Pinterest daily pin not yet confirmed posted today "
              f"(attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Dispatching...")
        self.state["pinterest_attempts"] = attempts + 1
        self._save_state()
        self.dispatch_pinterest_daily()

    def dispatch_content_engine(self) -> Dict[str, Any]:
        """Runs one Pipe 3 autonomous content drop (Cipher -> RTX 5070 Ti -> Forge -> Scribe).
        Only marks today's run successful if the full chain actually produced a manifest -
        a render that fails partway (e.g. ComfyUI offline) must NOT be silently treated as done."""
        self._check_day_rollover()
        from pipeline.stages.content_engine import content_engine
        res = content_engine.run_autonomous_cycle()
        if res.get("success"):
            self.state["content_engine_sent_today"] = True
        self.state["history"].append({
            "type": "content_engine_cycle",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": {k: v for k, v in res.items() if k != "copy_kit"}  # copy kit is large, keep history compact
        })
        self._save_state()
        return res

    def _monitor_and_remediate_content_engine(self):
        """Autonomous watchdog for Pipe 3, mirroring _monitor_and_remediate_publications:
        retries a failed/missed daily content drop up to MAX_DISPATCH_RETRIES, then alerts
        the Commander via Synapse's notify_commander once retries are exhausted."""
        current_time = datetime.now().strftime("%H:%M")
        if current_time < CONTENT_ENGINE_SCHEDULE_TIME:
            return
        if self.state.get("content_engine_sent_today"):
            return

        attempts = self.state.get("content_engine_attempts", 0)
        if attempts >= MAX_DISPATCH_RETRIES:
            if not self.state.get("content_engine_alerted_today"):
                msg = (f"WORKHORSE ALERT: Autonomous content engine (Pipe 3) failed to produce "
                       f"today's drop after {MAX_DISPATCH_RETRIES} automatic retries. Manual check needed.")
                print(f"[Herald Scheduler] {msg}")
                try:
                    from pipeline.stages.ai_operator import ai_operator
                    ai_operator.log_incident(
                        "content_engine",
                        f"Failed to complete autonomous content cycle after {MAX_DISPATCH_RETRIES} attempts",
                        "Auto-retry exhausted - Commander notified via SMS.",
                        status="needs_attention"
                    )
                    ai_operator.notify_commander(msg)
                except Exception as e:
                    print(f"[Herald Scheduler] Failed to notify commander: {e}")
                self.state["content_engine_alerted_today"] = True
                self._save_state()
            return

        print(f"[Herald Scheduler] Content engine not yet confirmed done today "
              f"(attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Running cycle...")
        self.state["content_engine_attempts"] = attempts + 1
        self._save_state()
        self.dispatch_content_engine()

    def dispatch_today_all_now(self) -> Dict[str, Any]:
        """
        Instant catch-up: Dispatches today's newsletters AND posts the current/pending
        tweets across both accounts immediately for all scheduled daily slots.
        """
        self._check_day_rollover()
        results = {
            "timestamp": datetime.now().isoformat(),
            "newsletters": self.dispatch_newsletters_all(),
            "twitter_slots_dispatched": []
        }

        # Dispatch all daily slots that haven't fully succeeded yet today
        for slot in DAILY_SLOTS:
            slot_id = slot["slot_id"]
            if slot_id not in self.state.get("executed_slots", []):
                slot_res = self.dispatch_slot(slot_id)
                results["twitter_slots_dispatched"].append(slot_res)

        return results

    async def run_loop(self):
        """Continuous background loop running inside FastAPI."""
        self.is_running = True
        print("[Herald Scheduler] Background Autonomous Daily Dispatcher online. Checking slots every 60s...")
        while True:
            try:
                await asyncio.sleep(60)
                self._check_day_rollover()
                now = datetime.now()
                current_time = now.strftime("%H:%M")

                # Autonomous Morning Trend Radar Sweep (08:00 AM). If the sweep comes back
                # degraded/fallback content (LLM hiccup, incomplete JSON, etc.) it is NOT
                # marked done - Herald keeps retrying every ~60s until RADAR_SWEEP_RETRY_CUTOFF,
                # so a single transient failure doesn't silently stick Herald with repeated
                # static content for the whole day.
                if current_time >= "08:00" and not self.state.get("radar_sweep_done_today"):
                    print("[Herald Scheduler] 08:00 AM window reached: Triggering autonomous morning trend radar sweep...")
                    try:
                        from pipeline.stages.trend_researcher import trend_researcher
                        loop = asyncio.get_event_loop()
                        vault_result = await loop.run_in_executor(None, trend_researcher.run_daily_radar_sweep)
                        used_fallback = vault_result.get("daily_synthesis", {}).get("used_fallback", False)
                        if used_fallback and current_time < RADAR_SWEEP_RETRY_CUTOFF:
                            print(f"[Herald Scheduler] Radar sweep returned degraded/fallback content - will retry next cycle (before {RADAR_SWEEP_RETRY_CUTOFF} cutoff).")
                        else:
                            if used_fallback:
                                print(f"[Herald Scheduler] Radar sweep still degraded past {RADAR_SWEEP_RETRY_CUTOFF} cutoff - accepting fallback content for today.")
                                try:
                                    from pipeline.stages.ai_operator import ai_operator
                                    ai_operator.log_incident(
                                        "trend_researcher",
                                        "Daily radar sweep used degraded/fallback content after repeated retries (LLM synthesis failed or returned incomplete slots)",
                                        f"Accepted fallback content past the {RADAR_SWEEP_RETRY_CUTOFF} retry cutoff - some tweet slots today may repeat prior static copy.",
                                        status="needs_attention"
                                    )
                                except Exception:
                                    pass
                            self.state["radar_sweep_done_today"] = True
                            self._save_state()
                    except Exception as e:
                        print(f"[Herald Scheduler] Radar sweep error: {e}")

                # Autonomous Twitter slot dispatch, retry, and Commander alerting - mirrors
                # the newsletter watchdog pattern (verify every account actually posted,
                # retry up to MAX_DISPATCH_RETRIES, then alert) instead of the old one-shot
                # fire-and-forget trigger that silently accepted partial/total failures as
                # "done for the day".
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._monitor_and_remediate_twitter_slots)

                # Daily Pinterest pin - same retry/alert watchdog pattern (no-op if
                # disabled/unconfigured).
                await loop.run_in_executor(None, self._monitor_and_remediate_pinterest)

                # Autonomous newsletter dispatch, retry, and Commander alerting (Dispensary
                # Deals, Studio Wire, Creator Pulse, Creator Blueprint) - verifies ACTUAL
                # delivery every pass instead of trusting a one-shot "launched" flag.
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._monitor_and_remediate_publications)

                # Pipe 3 - Autonomous AI Model Content Engine: same verify/retry/alert
                # pattern, once per day at CONTENT_ENGINE_SCHEDULE_TIME.
                await loop.run_in_executor(None, self._monitor_and_remediate_content_engine)

            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"[Herald Scheduler] Error in loop: {e}")

# Global singleton
herald_scheduler = HeraldScheduler()
