# WORKHORSE — Complete System Capabilities Catalog
**Autonomous Media Production, Diffusion Studio & Creator Monetization Archipelago**
*System Architecture: Dual NVIDIA GeForce RTX 3060 (24GB VRAM) Local Node + NVIDIA GeForce RTX 5070 Ti (16GB VRAM) Main PC Diffusion Server*

---

## 1. System Overview & Hardware Architecture

WORKHORSE is a fully autonomous, local-first media production and creator monetization command center. It operates 24/7 without external cloud dependencies, enforcing strict air-gapped data privacy for commercial and adult creator assets.

```
                    ┌────────────────────────────────────────────────────────┐
                    │               WORKHORSE COMMAND CENTER                 │
                    │               Web Dashboard (Port 8800)                │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
  ┌──────────────────────────────┐                              ┌──────────────────────────────┐
  │   LOCAL RIG: DUAL RTX 3060   │                              │   MAIN PC: RTX 5070 Ti 16GB  │
  │     (24GB Total VRAM)        │                              │     (LAN: 192.168.1.74:8188) │
  ├──────────────────────────────┤                              ├──────────────────────────────┤
  │ GPU 0 (12GB VRAM - sm_86):   │                              │ Dedicated Heavy Diffusion:   │
  │ • Ollama LLM (Qwen3-14B)     │                              │ • FLUX.1 [dev] & [schnell]   │
  │ • Qwen-VL Vision (8B-VL)     │                              │ • MiniMax H3 V2V & FastH3    │
  │ • Dynamic Block Swapping     │                              │ • LTX-Video 2.3 (22B)        │
  ├──────────────────────────────┤                              │ • Trellis 2 & Pixal3D (PBR)  │
  │ GPU 1 (12GB VRAM - sm_86):   │                              │ • 67 Headless API Templates  │
  │ • Faster-Whisper (cuda:1)    │                              │ • 23 Curriculum Modules      │
  │ • Dual NVENC 60fps Encoder   │                              │ • SageAttention sm_89 CUDA   │
  │ • GPU 1 Process Arbiter      │                              └──────────────────────────────┘
  └──────────────────────────────┘
```

### Core Hardware & Privacy Guarantees
- **Strict Local & Air-Gapped Operation:** All model weights, customer photos, and commercial videos are processed 100% locally on dedicated hardware. Zero private media or prompt data is ever transmitted to commercial third-party cloud APIs.
- **Hardware Isolation (GPU 1 Arbiter):** NVENC video encoding and Faster-Whisper audio extraction run on dedicated GPU 1 under an atomic OS file lock and threading mutex, guaranteeing zero Out-Of-Memory (OOM) collisions with GPU 0 LLM reasoning.
- **VRAM Circuit Breaker:** Continuous background monitoring protects GPU 0. If VRAM reaches $\ge 80\%$ for $>45$s while idle, memory is flushed; active orchestrator render jobs are safely detected and preserved.
- **Storage Protection:** Automated background pruning scrubs temporary rendering buffers older than 48 hours on Drive F:, preventing disk exhaustion.

---

## 2. Periodic Table of Agents (14 Autonomous Specialists)

The WORKHORSE archipelago is powered by 11 core autonomous agents and 3 auxiliary specialists, each with certified domain responsibilities:

| Element | Agent Name | Title | Primary Role & Core Capabilities |
| :---: | :--- | :--- | :--- |
| **`[100 Fm]`** | **Synapse** | Master AI Operator & Studio Overwatch | Central studio concierge, multi-agent orchestrator, automated self-healing remediation loop, VRAM block swapping, system diagnostics. |
| **`[74 W]`** | **Vanguard** | Video Intake Sentinel & Dispatcher | File integrity validator, corrupt packet quarantiner, 8-stage video pipeline orchestrator, client upload isolation. |
| **`[77 Ir]`** | **Iris** | Computer Vision Quality Control Gate | Forensic visual auditor using Qwen-VL (8B-VL) on GPU 0; audits every image/video for anatomy defects, extra limbs, fused digits, facial symmetry, and strict SFW/nudity compliance. |
| **`[28 Ni]`** | **Forge** | Media Packager & NVENC Video Cutter | Dual RTX 3060 NVENC 60fps video cutter; automated 9:16 vertical smart crops, 60s teaser trailers, pose sheet extraction, and slideshow compilation. |
| **`[26 Fe]`** | **Echo** | Audio Intelligence & Transcription | Faster-Whisper speech-to-text on GPU 1; word-level timestamps, multi-speaker diarization, hook extraction, and subtitle generation. |
| **`[79 Au]`** | **Aura** | Editorial Retouching & Color Grading | Frequency separation skin smoothing, non-destructive dodge & burn, 3D LUT color grading, Portra/Cinestill film emulation, and multi-layer compositing. |
| **`[34 Se]`** | **Muse** | Prompt Engineer & Aesthetic Director | Crafts high-converting prompt matrices for FLUX.1, SDXL, LTX-Video, and MiniMax H3 across 5 commercial moods (*Sexy/Alluring, Playful, Cute, Cozy, High-Fashion Action*). |
| **`[6 C]`** | **Scribe** | High-Converting Editorial Engine | Dynamic date-seeded copywriter; produces non-repeating daily newsletters, social media copy kits (Twitter, Instagram, Reddit, Threads, Pinterest), and PPV scripts. |
| **`[80 Hg]`** | **Mercury** | Omni-Channel Marketing Maestro | Funnel mechanics, multi-channel distribution strategy, conversion math, Etsy/Fiverr SEO, Linktree routing, and promotional campaign scheduling. |
| **`[33 As]`** | **Herald** | Autonomous Newsletter & Social Dispatcher | Autonomous scheduler; dispatches 4 daily email newsletters, manages 5 daily Twitter slots across `@TheCreatorAsset` & `@creatorpulselab`, and verifies recipient delivery with 3x retry healing. |
| **`[36 Cp]`** | **Cipher** | Real-Time Trend & Market Scout | Daily trend sweeper (RSS/web intelligence), creator monetization analytics, OnlyFans/Fansly tip menu intelligence, and Etsy/Fiverr keyword scout. |
| **`[78 Pt]`** | **Apex** | Master Packaging Specialist | Bundles completed client deliverables into organized ZIP archives with licensing agreements and manifests. |
| **`[47 Ag]`** | **Radar** | Order Intake Sentinel | 24/7 background scanner monitoring `digitalcreatorassets@gmail.com` for inbound Etsy, Fiverr, Stripe, and Gumroad orders with 14-day token generation. |
| **`[82 Pb]`** | **Scrubber** | Privacy & Metadata Sanitizer | Air-gapped EXIF/IPTC scrubber; strips GPS coordinates, camera serial numbers, and embedded workflow JSON to guarantee complete client anonymity. |

---

## 3. ComfyUI Generative & Diffusion Suite

Connected via high-speed LAN to the primary diffusion workstation (`192.168.1.74:8188`), WORKHORSE controls **67 production workflow templates** backed by a **23-module deep curriculum**:

### A. Video-to-Video (V2V) Transformation Engine (MiniMax H3)
Treats video footage as a unified 3D spatiotemporal volume via `MiniMaxH3ReferenceToVideo`, binding source motion with reference images:
1. **Clothing & Wardrobe Replacement (Video VTON):** Replaces shirts, dresses, hoodies, or swimwear on moving talent while locking body kinetics, lighting, and camera motion 100%.
2. **Shoe, Footwear, Tattoo & Accessory Swapping:** Replaces sneakers, jewelry, watches, or applies/erases tattoos across 100+ moving video frames without temporal jitter or detachment.
3. **Background & Environment Replacement (Scene Relocation):** Transplants moving performers from plain studio rooms into luxury outdoor sets, cafes, or villas while preserving shadows, perspective, and natural subject motion.
4. **Character Replacement & Motion Choreography Transfer:** Erases original performers (dancers, athletes, actors) and maps a new character's likeness onto the identical choreography and camera path.
5. **3-Part Semantic Prompt Engineering Contract:** Enforces strict role definitions (`Video 1` = motion; `Picture 1` = target attribute), explicit replacement directives, and mandatory preservation invariants.

### B. Accelerated Temporal Video Synthesis (MiniMax FastH3 & LTX-Video)
1. **MiniMax FastH3 8-Step Sampler:** High-speed video generation utilizing Kitchen Attention & Sparse Attention to eliminate VRAM thrashing.
   - Text-to-Video (T2V)
   - FirstFrame-to-Video (I2V still animation)
   - First-and-Last-Frame Interpolation (smooth scene transitions between two boundary images)
   - Dual Latent Decoding: Video frames via `minimax_h3_video_vae_fp16` + synchronized audio soundscapes via `minimax_h3_audio_vae_fp32`.
2. **LTX-Video 2.3 (22B):** Cinematic 30fps video generation (720x1280 9:16 vertical and 1280x720 16:9 widescreen, 300 frames, ~10s duration).

### C. Native Image-to-3D & Full-PBR Mesh Generation (Trellis 2 & Pixal3D)
1. **Single-Image to Watertight 3D Mesh:** Converts 2D concept photos into production-ready `.glb` models.
2. **Full PBR Texture Channels:** Bakes real Physically Based Rendering surface maps:
   - **Albedo / Base Color** (up to 4096k resolution)
   - **Normal Map** (surface depth and micro-geometry)
   - **Roughness Map** (specular vs matte balance)
   - **Metallic Map** (dielectric vs conductor reflectance)
3. **Low-VRAM Quantization:** Executes via INT8 ConvRot models (`trellis_2_int8_convrot.safetensors`, `pixal3d_int8_convrot.safetensors`) using under 4.2GB VRAM.
4. **Flux Klein 9B Angle-Locked 3D-to-Image:** Imports 3D viewports and renders photorealistic marketing stills from specified camera yaw/pitch angles while mathematically preserving the 3D perspective.

### D. Industrial Batch Automation (EP38 Engine — 50 Workflows)
1. **Multi-Aspect Ratio Social Cropping:** Ingests an entire directory and outputs 3 cropped formats per image concurrently:
   - Square Feed (`1:1` / 1080x1080)
   - Vertical Story / Reel (`9:16` / 1080x1920)
   - Portrait Post (`4:5` / 1080x1350)
2. **Pixel-Preserving Outpaint Stitching (Flux Klein 9B):** Expands images to 16:9 widescreen or custom dimensions while using `Outpaint Stitch` to keep the original center pixels 100% mathematically un-denoised.
3. **Automated E-Commerce Staging:** Isolates foreground subjects via `BiRefNet`, places them on studio podiums, applies dynamic watermarks via `MathNode` resolution offsets, and compiles indexed contact review sheets.
4. **Batch Photo Restoration & Colorization:** Cleans scratches, removes grain, and colorizes entire vintage photo directories in a single unattended run.
5. **AI Sorting & Filtering:** Evaluates batch outputs with aesthetic and blur metrics, automatically sorting passes and fails into separate review folders.

### E. Inpainting, Subject Swapping & Studio Photography
1. **SAM3 Grounding Background Swap (`comfy_background_change`):** Grounds on text prompts to isolate subjects, invert alpha masks, and inpaint brand-new photoreal studio backdrops.
2. **Skin Tattoo Addition & Removal:** High-precision inpainting that seamlessly removes ink while preserving natural pore texture, or adds intricate custom tattoo art.
3. **PuLID-Flux Subject Swap:** Locks in source pose, wardrobe, and studio lighting while swapping facial identity using a single reference photo.
4. **FLUX.1 [dev] Studio Photorealism:** 2-pass high-resolution generation with guidance embeddings (CFG 3.5) and tiled VAE decoding up to 4K.
5. **Client Character LoRA Ecosystem:** 18+ adult-gated likeness rendering for private licensed talent (Charlette, Margo, Melissa) with isolated output paths.

### F. Pixaroma Node Pack Ergonomics
- **`Load Image (Pixaroma)`:** Exposes source image filenames as string signals (`image_name`) downstream, eliminating blind numbered file collisions.
- **`Image Composer`:** Native in-graph multi-layer compositing with integrated BiRefNet alpha cutouts, affine transforms (translate, scale, rotate), and blend modes.
- **`3D Builder` & `Image Compare`:** In-canvas 3D model orientation and split-slider A/B visual quality verification.

---

## 4. Media Post-Production & Video Pipeline (Stages 1–8)

WORKHORSE runs an automated, multi-stage processing pipeline for client and studio media:

```
[Raw Footage Upload]
        │
        ▼
[Stage 1: Vanguard Intake] ────────► Forensic container validation & packet quarantine
        │
        ▼
[Stage 2: Echo Audio Engine] ─────► Faster-Whisper extraction, timestamps, vocal hooks
        │
        ▼
[Stage 3: Forge Video Engine] ────► NVENC 60fps cutting, 9:16 vertical smart crop
        │
        ▼
[Stage 4: Vision & Iris QC] ──────► 6 key poses extracted, Qwen-VL defect detection
        │
        ▼
[Stage 5: Aura Retouching] ───────► Frequency separation, dodge & burn, 3D LUT grading
        │
        ▼
[Stage 6: Scribe Editorial] ──────► 5-platform social copy kits & newsletter articles
        │
        ▼
[Stage 7: Apex Packaging] ────────► Master ZIP bundle, commercial license, manifest
        │
        ▼
[Stage 8: Dropzone Delivery] ─────► Automated dispatch to client fulfillment bays
```

---

## 5. Commercial Monetization & Revenue Streams

WORKHORSE operates several integrated revenue generation funnels:

### 1. Etsy Digital Storefront (`CreatorMediaLab`)
- **Lightroom Presets (.XMP / .DNG):** Automated packaging of custom color grading curves (Moody Studio, Vintage Film, Boudoir Golden Hour, Editorial Clean).
- **Digital Asset Bundles:** Pre-rendered video reels, stock background libraries, 3D assets, and creator templates.
- **Automated Listing Sync:** Live monitoring of active shop listings, stock counts, and keyword tags.

### 2. Fiverr High-Demand Creator Gigs
Direct fulfillment workflows configured for:
- **Editorial Photo Retouching & Color Grading:** High-end frequency separation and film emulation.
- **Photo-to-Video Animation:** Converting static portraits into kinetic 30fps cinematic video reels.
- **3D PBR Mesh Generation:** Transforming client photos/products into textured `.glb` models.
- **Seamless Video Loops:** Generating hypnotic ambient looping videos for stream backdrops.
- **Cam & OnlyFans Tip Menus:** Custom branded graphical tip menus and pricing sheets.

### 3. Adult Creator Monetization (The Daily Creator Pulse)
- **PPV Vault Scripts & Teasers:** High-converting pay-per-view sales scripts and countdown sequences.
- **Cam Tip Menus & Posing Cues:** Interactive tip menus with automated pricing ladders.
- **Studio Lighting & Phone Rigs:** Grounded equipment setup recommendations for amateur and pro creators.

---

## 6. Autonomous Editorial & Publishing Engine

### 4 Daily Multi-Platform Publications
1. **The Daily Creator Pulse (09:00):** Adult creator monetization, fan conversion math, cam strategy, and PPV vault optimization.
2. **The Shutter & Studio Wire (08:30):** Professional photography, lighting recipes, Lightroom color science, and camera rig reviews.
3. **The Creator Blueprint (10:00):** AI media business models, automated asset flywheels, and cross-platform growth tactics.
4. **Dispensary Deals (09:00):** Automated consumer retail curation and localized deal roundups.

### Publishing & Distribution Rules
- **Non-Repeating Dynamic Editorial:** Copy is seeded daily by date and grounded in Cipher's morning market research, preventing repetitive content.
- **Iris QC Visual Gate:** All images and diagrams destined for publications are forensically inspected; rejected visuals are rerolled with fresh seeds before send-time.
- **5 Daily Scheduled Twitter Slots:** Automated thread and media dispatching across `@TheCreatorAsset` and `@creatorpulselab`.
- **Delivery Verification:** Herald verifies confirmed subscriber inbox receipt and triggers up to 3 automatic healing retries before alerting the Commander.

---

## 7. Autonomous Self-Healing & Sentinel Overwatch

WORKHORSE runs continuous background health loops to maintain 100% uptime:
- **10-Minute Auto-Remediation Loop:** Inspects database integrity (`newsletter_subscribers.json`), repairs corrupted records, and logs recoveries to `incident_log.json`.
- **Dual-GPU Guardrails:** Dynamic block swapping evicts LLM text weights before loading vision weights on GPU 0, preventing CUDA memory faults.
- **Air-Gapped Adult Mode Firewall:** NSFW generation is strictly blocked from autonomous background engines and general chat. It can only be unlocked upon explicit Commander authorization.
- **TTL Caching & Monitor Efficiency:** Real-time system monitoring uses optimized 3.0-second TTL caching, maintaining overall system CPU utilization at $\sim 15\%$.

---

## 8. Web Command Center & Operator Interface

Accessible locally at **`http://127.0.0.1:8800`**:
- **Interactive AI Operator Bay:** Direct real-time chat with **Synapse [100 Fm]** equipped with 40+ executable tools and media attachments.
- **Real-Time Agent Activity Monitor:** Live heartbeat tracking for all 14 agents with dynamic active/idle status indicators.
- **Interactive 3D Agent Trading Cards:** Three.js / WebGL accelerated cards featuring elemental color palettes and kinetic bob/yaw animations.
- **Pipeline & Fulfillment Bays:** Visual management for video intake, batch queueing, manual QC review, and client release packaging.

---
*Catalog generated and verified on WORKHORSE Studio Architecture • October 2026*
