"""
WORKHORSE AGENT ROSTER & EXPERT KNOWLEDGE BASE
Authoritative Periodic Table of Agents for the WORKHORSE Studio Archipelago.

Defines the exact elemental identity, hardware binding, domain expertise,
operational responsibilities, and collaborative touchpoints for all 11 core
agents and 3 auxiliary support agents.
"""

from typing import Dict, Any, List

WORKHORSE_ROSTER: Dict[str, Dict[str, Any]] = {
    "synapse": {
        "name": "Synapse",
        "symbol": "100 Fm",
        "element": "Fermium",
        "title": "Master AI Operator & Chief Cybernetic Architect",
        "hardware": "Dual NVIDIA RTX 3060 (24GB VRAM) - GPU 0 Dedicated",
        "model": "Local Ollama huihui_ai/qwen3-abliterated:14b",
        "expertise": (
            "Executive pipeline orchestration, dynamic VRAM resource management, dual-GPU "
            "guardrails, self-healing automated remediation, system diagnostics, and studio command concierge."
        ),
        "responsibilities": [
            "Coordinates all 14 agents across the 8-stage video pipeline and autonomous publishing cycles.",
            "Enforces GPU 0 dynamic block swapping: automatically purges text model before loading Qwen-VL vision weights.",
            "Executes 10-minute background self-healing auto-remediation loop (disk space, subscriber DB repairs, incident logging).",
            "Monitors VRAM circuit breaker (protects against runaway leaks while respecting active render jobs).",
            "Serves as the interactive studio concierge with 40+ registered tools for system control and diagnostics."
        ],
        "newsletter_role": "Central overwatch sentinel: verifies daily schedule execution, monitors dispatch health, and logs delivery incidents."
    },

    "herald": {
        "name": "Herald",
        "symbol": "33 As",
        "element": "Arsenic",
        "title": "Autonomous Newsletter & Social Media Dispatcher",
        "hardware": "Dedicated Asynchronous Dispatch Engine (CPU / Network)",
        "model": "Herald Autonomous Dispatcher Core",
        "expertise": (
            "Daily newsletter multi-publication dispatch, automated 5-slot Twitter/X scheduling, "
            "cross-pollination between newsletter and social feeds, real delivery verification, and fail-closed SFW enforcement."
        ),
        "responsibilities": [
            "Dispatches 4 daily publications: Studio Wire (08:30), Creator Pulse (09:00), Creator Blueprint (10:00), and Dispensary Deals (09:00).",
            "Schedules and dispatches 5 daily Twitter slots (09:00, 13:00, 17:00, 20:30, 23:00) across @TheCreatorAsset and @creatorpulselab.",
            "Synchronizes slot 1 morning tweets directly with today's fresh newsletter lead story and threads.",
            "Pairs every social and newsletter drop with topic-matched, Iris-verified SFW visual assets (and video upgrades on designated slots).",
            "Enforces delivery verification: retries failed sends up to 3 times before logging incidents and notifying the Commander."
        ],
        "newsletter_role": "Publication distribution manager: compiles the final responsive HTML issues, embeds Iris-verified visuals, and executes verified SMTP sends."
    },

    "iris": {
        "name": "Iris",
        "symbol": "77 Ir",
        "element": "Iridium",
        "title": "Computer Vision Quality Control Gate & Forensic Visual Auditor",
        "hardware": "Local Ollama Qwen-VL (CUDA on GPU 0)",
        "model": "huihui_ai/qwen3-vl-abliterated:8b-instruct",
        "expertise": (
            "Forensic anatomy auditing, aesthetic lighting and composition evaluation, "
            "pixel-level skin-density firewalling, foreground occlusion detection, and strict SFW certification."
        ),
        "responsibilities": [
            "Extracts mathematically spaced high-resolution pose frames from raw video footage (Stage 2 & Stage 5).",
            "Audits every ComfyUI render: verifies anatomical correctness (hands, fingers, limb counts, facial symmetry).",
            "Enforces zero-tolerance SFW gate: blocks real nudity, sheer exposure, or adult content from reaching public feeds.",
            "Detects foreground clutter, microphones, tripods, or equipment blocking the subject's face/body.",
            "Quarantine and retry: immediately moves rejected assets to qc_rejected/ and triggers a fresh prompt variant generation."
        ],
        "newsletter_role": "Visual compliance gatekeeper: audits and certifies every newsletter image render as 100% SFW, properly framed, and high-fidelity."
    },

    "muse": {
        "name": "Muse",
        "symbol": "34 Se",
        "element": "Selenium",
        "title": "AI Image & Video Prompt Engineer",
        "hardware": "Local Ollama LLM Prompt Synthesizer (GPU 0)",
        "model": "Prompt Synthesizer Core",
        "expertise": (
            "FLUX.1 [dev/schnell] diffusion prompt engineering, cinematic LTX-Video / MiniMax motion directing, "
            "multi-mood wardrobe styling, and topic-matched visual concept design."
        ),
        "responsibilities": [
            "Converts Iris scene descriptions and post topics into photorealistic FLUX.1 generation prompts.",
            "Engineers diverse wardrobe and aesthetic vibes (Sexy/Alluring, Playful, Cute, Cozy, Active) without real nudity.",
            "Crafts topic-matched visual scenes: studio feathering lighting, color grading consoles, flat-lays, and creator workstations.",
            "Generates cinematic video motion prompts under 90 words for LTX-Video 2.3 and MiniMax H3.",
            "Produces 6-variation pose series prompt sets tailored to specific commercial or editorial concepts."
        ],
        "newsletter_role": "Prompt architect: designs the topic-aligned positive and negative prompts used to generate fresh daily newsletter visual embeds."
    },

    "forge": {
        "name": "Forge",
        "symbol": "28 Ni",
        "element": "Nickel",
        "title": "Media Packager & NVENC Hardware Video Specialist",
        "hardware": "Dual RTX 3060 NVENC Hardware Video Encoder (GPU 1)",
        "model": "h264_nvenc High-Speed Pipeline",
        "expertise": (
            "Hardware-accelerated 60fps video encoding, scene extraction, 9:16 vertical smart-crops, "
            "1:1 square crops, teaser cuts, and promotional video loop generation."
        ),
        "responsibilities": [
            "Cuts hardware-accelerated 60-second teaser trailers using Dual RTX 3060 NVENC (Stage 3).",
            "Renders multi-aspect ratio social crops: 9:16 vertical (Reels/TikTok/Shorts) and 1:1 square (Feed).",
            "Executes video upgrades for Herald's evening social posts and video showcase previews.",
            "Operates under gpu1_arbiter to ensure zero VRAM collision with GPU 0 LLM tasks.",
            "Compiles master PROMO_MEDIA_PACKAGE.md and structured deliverable archives."
        ],
        "newsletter_role": "Media asset processor: encodes high-efficiency video previews, teaser clips, and promotional assets linked within newsletter issues."
    },

    "scribe": {
        "name": "Scribe",
        "symbol": "6 C",
        "element": "Carbon",
        "title": "High-Converting Master Copywriter & Daily Editorial Engine",
        "hardware": "Local Ollama Uncensored LLM (GPU 0)",
        "model": "huihui_ai/qwen3-abliterated:14b",
        "expertise": (
            "Publication journalism, direct-response copywriting, creator monetization psychology, "
            "multi-platform social copy kits, and date-seeded dynamic editorial generation."
        ),
        "responsibilities": [
            "Writes genuinely fresh daily editorial content for Creator Pulse, Studio Wire, and Creator Blueprint.",
            "Guarantees complete enumeration: every numbered framework, slider recipe, script quote, and math breakdown is fully articulated.",
            "Eliminates static repetition: incorporates Cipher's daily research and date-seeded procedural generation so no section repeats.",
            "Generates multi-platform social release kits (Instagram caption style pills, Twitter threads, TikTok hooks, Reddit posts).",
            "Provides robust dynamic fallback generation so publications change daily even if external LLM services are temporarily offline."
        ],
        "newsletter_role": "Chief editorial writer: synthesizes daily lead stories, metric cards, PPV swipe files, Lightroom recipes, directing playbooks, and monetization math."
    },

    "mercury": {
        "name": "Mercury",
        "symbol": "80 Hg",
        "element": "Hydrargyrum",
        "title": "Omni-Channel Marketing Maestro & Service Strategist",
        "hardware": "Local Multi-Agent Automation Engine (GPU 0 / CPU)",
        "model": "Omni-Marketer Matrix Core",
        "expertise": (
            "Freelance gig monetization (Fiverr), digital product storefronts (Etsy), "
            "Linktree conversion architecture, 3-tier value ladders, and multi-channel campaign strategy."
        ),
        "responsibilities": [
            "Architects high-converting Fiverr gig listings, intake questionnaires, and custom buyer pitches.",
            "Designs Etsy digital product bundles (.XMP preset packs, stream bio kits, prompt cheat sheets).",
            "Structures 3-tier creator value ladders ($19 micro-asset, $49 bundle with walkthrough, $149 VIP access).",
            "Develops 7-day multi-channel launch funnels integrating email, social media, and digital storefronts.",
            "Optimizes Linktree hub conversion flows adhering to the strict Rule of 4."
        ],
        "newsletter_role": "Commercial funnel architect: designs the promotional cards, calls-to-action, and product offerings embedded at the base of every newsletter issue."
    },

    "vanguard": {
        "name": "Vanguard",
        "symbol": "74 W",
        "element": "Tungsten",
        "title": "Video Intake Sentinel & Pipeline Dispatcher",
        "hardware": "Dual RTX 3060 Stream Ingestion Engine (GPU 0 & GPU 1)",
        "model": "Master Video Pipeline Orchestrator",
        "expertise": (
            "Stream container validation, video metadata extraction, framerate/resolution verification, "
            "sequential pipeline stage dispatching, and execution isolation locks."
        ),
        "responsibilities": [
            "Ingests incoming client shoot media and validates stream containers (MP4, MOV, MKV, AVI).",
            "Verifies video resolution, framerate (24fps/30fps/60fps), audio track presence, and color space.",
            "Orchestrates sequential execution across Stages 1–8 on Dual RTX 3060 hardware.",
            "Acquires execution locks and manages isolated client upload batches in workspace/client_inbox.",
            "Guarantees post-stage asset verification and prevents concurrent pipeline job collisions."
        ],
        "newsletter_role": "Intake integrity guardian: validates all incoming video and media assets before they enter the processing pipeline."
    },

    "aura": {
        "name": "Aura",
        "symbol": "79 Au",
        "element": "Gold",
        "title": "Editorial Retouching & Film Color Science Specialist",
        "hardware": "CPU / OpenCV Image Processing Pipeline + DaVinci Color Engine",
        "model": "OpenCV Frequency-Separation Retouch & Color-Grade Engine",
        "expertise": (
            "True frequency-separation skin retouching, authentic skin pore preservation, "
            "analog film tone curve replication (Kodak Portra 400, Cinestill 800T), and 16-bit TIFF / .XMP export."
        ),
        "responsibilities": [
            "Performs true frequency separation: splits texture/pore high frequencies from tone/color low frequencies to eliminate waxy blur.",
            "Applies 6 signature color grades: Moody Boudoir, Golden Hour, Cyber Neon, Monochrome Noir, Vintage 35mm, Clean Editorial.",
            "Calibrates exact Lightroom slider recipes: RGB black point lifts, HSL orange saturation/luminance, and color wheel split toning.",
            "Executes batch photo retouching for client fulfillment with watermark and aspect ratio formatting.",
            "Packages Lightroom .XMP presets and commercial photo deliverables for Etsy storefronts."
        ],
        "newsletter_role": "Color & aesthetic master: provides the verified Lightroom develop recipes, slider parameters, and lighting tone curves featured in Studio Wire."
    },

    "echo": {
        "name": "Echo",
        "symbol": "26 Fe",
        "element": "Iron",
        "title": "Audio Intelligence & Dialogue Extraction Specialist",
        "hardware": "CUDA Faster-Whisper float16 (GPU 1 Dedicated)",
        "model": "faster-whisper (Local CTranslate2)",
        "expertise": (
            "High-speed vocal isolation, speech-to-text transcription, spoken punchline detection, "
            "teaser hook isolation, and audio normalization."
        ),
        "responsibilities": [
            "Extracts 16kHz mono audio streams from raw video files via FFmpeg.",
            "Transcribes dialogue locally on GPU 1 with CUDA Faster-Whisper float16 with zero network latency.",
            "Isolates spoken punchlines and teaser hooks (3-12 words) optimized for social video captions.",
            "Generates clean transcript.txt and timestamped JSON dialogue segments.",
            "Operates under gpu1_arbiter to guarantee zero memory interference with GPU 0."
        ],
        "newsletter_role": "Audio intelligence provider: extracts spoken soundbites and quote transcriptions for creator spotlight sections."
    },

    "cipher": {
        "name": "Cipher",
        "symbol": "36 Cp",
        "element": "Copernicium",
        "title": "Market Scout & Trend Intelligence Agent",
        "hardware": "Dual RTX 3060 Local Intelligence Matrix (CPU / Network / GPU 0)",
        "model": "huihui_ai/qwen3-abliterated:14b + Google News RSS Engine",
        "expertise": (
            "Autonomous morning radar sweeps, breaking creator economy news discovery, "
            "photography lighting/color trends, digital business automation research, and dropped link synthesis."
        ),
        "responsibilities": [
            "Runs autonomous morning web radar sweeps at 08:00 across photography, creator monetization, and business automation.",
            "Ingests dropped URLs from the Commander, extracting core takeaways, tweet threads, and newsletter feature blurbs.",
            "Maintains the daily trend vault (workspace/daily_trends_vault.json) with verified breaking industry news.",
            "Feeds live research articles directly into Scribe's morning newsletter generation.",
            "Synthesizes 5-slot dynamic tweet themes across @TheCreatorAsset and @creatorpulselab."
        ],
        "newsletter_role": "Intelligence ground truth: discovers and verifies the real-world news, algorithm changes, and market trends that seed today's newsletter content."
    },

    # Auxiliary support agents
    "apex": {
        "name": "Apex",
        "symbol": "78 Pt",
        "element": "Platinum",
        "title": "Master Packaging & Fulfillment Exporter",
        "hardware": "High-Speed Storage Exporter (CPU / IO)",
        "model": "Package Exporter Engine Core",
        "expertise": "Client archive compilation, commercial licensing agreements, 2257 compliance release documentation, and 1-click delivery bundles.",
        "responsibilities": [
            "Packages finished deliverables into organized client-ready ZIP archives.",
            "Compiles master PROMO_MEDIA_PACKAGE.md and social copy kits.",
            "Embeds licensing agreements and compliance paperwork."
        ],
        "newsletter_role": "Archive manager for subscriber lead magnets and digital asset downloads."
    },

    "radar": {
        "name": "Radar",
        "symbol": "47 Ag",
        "element": "Silver",
        "title": "Order Radar & Client Intake Sentinel",
        "hardware": "Automated SSL IMAP & Webhook Receiver (CPU / Network)",
        "model": "Multi-Platform Order Scanner",
        "expertise": "E-commerce order intake, Stripe/Gumroad webhook parsing, IMAP inbox monitoring, and secure 14-day token generation.",
        "responsibilities": [
            "Monitors incoming orders from Fiverr, Etsy, Stripe, and Gumroad.",
            "Mints single-use secure download tokens with 14-day expiry.",
            "Stages incoming orders for automated fulfillment."
        ],
        "newsletter_role": "Tracks new subscriber sign-ups and purchase attribution from newsletter promo links."
    },

    "scrubber": {
        "name": "Scrubber",
        "symbol": "82 Pb",
        "element": "Lead",
        "title": "Privacy & Air-Gapped Metadata Sanitizer",
        "hardware": "PIL / ExifTool Media Sanitizer (CPU)",
        "model": "Zero-Trace Privacy Engine",
        "expertise": "Zero-trace EXIF metadata stripping, GPS sanitization, camera serial scrubbing, and generation prompt sanitization.",
        "responsibilities": [
            "Strips all EXIF metadata, GPS coordinates, and camera serials from media files.",
            "Scrubs embedded ComfyUI generation workflow JSON and prompt texts from images.",
            "Guarantees privacy for creators and clients before public publishing."
        ],
        "newsletter_role": "Sanitizes all embedded newsletter imagery to ensure zero metadata leakage."
    }
}


def get_agent(agent_key: str) -> Dict[str, Any]:
    """Retrieve the authoritative expert dossier for an agent."""
    key = agent_key.lower().strip()
    return WORKHORSE_ROSTER.get(key, {})


def get_newsletter_crew() -> List[Dict[str, Any]]:
    """Returns the dedicated 5-agent crew responsible for the daily newsletter lifecycle."""
    crew_keys = ["cipher", "scribe", "iris", "herald", "synapse"]
    return [WORKHORSE_ROSTER[k] for k in crew_keys]


def get_all_agents() -> Dict[str, Dict[str, Any]]:
    """Returns the full 14-agent roster."""
    return WORKHORSE_ROSTER


AGENT_ROSTER = WORKHORSE_ROSTER
