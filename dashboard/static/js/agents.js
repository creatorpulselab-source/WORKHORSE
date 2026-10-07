// ==========================================================================
// WORKHORSE AI CREW — INTERACTIVE AGENT CONTROLLER & MISSION TUNING DECK
// ==========================================================================

const AGENTS_METADATA = {
  vanguard: {
    name: "Vanguard",
    role: "Tactical Commander & System Orchestrator",
    hardware: "Dual NVIDIA RTX 3060 (24GB VRAM)",
    model: "System Orchestrator Core",
    privacyStatus: "🔒 100% Local GPU Offline (Air-Gapped)",
    defaultQuote: "Command center online. Standing by for raw shoot media.",
    whatItDoes: [
      "Monitors real-time VRAM allocation across Dual RTX 3060 GPUs.",
      "Validates incoming video stream container, resolution, framerate, and duration.",
      "Manages sequential agent deployment through all 7 pipeline stages.",
      "Coordinates safe file archiving and error prevention."
    ],
    configFields: [
      { id: "gpu_assignment", label: "GPU Device Assignment", type: "select", options: [
        { val: "0,1", label: "Dual RTX 3060 (GPU 0 & GPU 1 - Max Throughput)" },
        { val: "0", label: "GPU 0 Only (NVIDIA RTX 3060 - 12GB)" },
        { val: "1", label: "GPU 1 Only (NVIDIA RTX 3060 - 12GB)" }
      ]},
      { id: "output_dir", label: "Destination Output Directory", type: "text", default: "F:/WORKHORSE/workspace/output" },
      { id: "auto_archive", label: "Auto-Archive Raw Shoot upon completion", type: "checkbox", default: false }
    ]
  },

  iris: {
    name: "Iris",
    role: "Vision Scout & Aesthetic Inspector",
    hardware: "Local Ollama Qwen-VL (CUDA)",
    model: "huihui_ai/qwen3-vl-abliterated:8b-instruct",
    privacyStatus: "🔒 100% Local GPU Offline (Private Visuals)",
    defaultQuote: "Optics calibrated. Ready to extract peak poses and analyze visual styling.",
    whatItDoes: [
      "Extracts mathematically spaced high-resolution pose frames from raw footage.",
      "Runs local multimodal vision analysis using uncensored Qwen-VL to analyze attire, boudoir setting, and mood.",
      "Identifies optimal thumbnail cover pose with ranking explanation.",
      "Generates visual aesthetics keyword tags (lighting, setting, wardrobe, poses)."
    ],
    configFields: [
      { id: "pose_count", label: "Pose Screenshots Count", type: "select", options: [
        { val: "4", label: "4 Poses (Fast Preview)" },
        { val: "6", label: "6 Poses (Standard Studio Package - Recommended)" },
        { val: "8", label: "8 Poses (Extended Set)" },
        { val: "12", label: "12 Poses (Full Gallery Kit)" }
      ]},
      { id: "vision_model", label: "Local Ollama Vision Model", type: "select", options: [
        { val: "huihui_ai/qwen3-vl-abliterated:8b-instruct", label: "huihui_ai/qwen3-vl-abliterated:8b (Fast & Uncensored)" },
        { val: "huihui_ai/qwen2.5-vl-abliterated:32b-instruct-q4_K_M", label: "huihui_ai/qwen2.5-vl-abliterated:32b (Ultra High-Detail)" },
        { val: "qwen3.8:27b", label: "qwen3.8:27b (27B Vision Hybrid)" }
      ]},
      { id: "custom_focus", label: "Vision Focus Keywords / Visual Elements to Detect", type: "textarea", 
        default: "boudoir mood, provocative pose, studio lighting, lingerie attire, aesthetic tags, glamor angles" }
    ]
  },

  echo: {
    name: "Echo",
    role: "Audio Scribe & Dialogue Extractor",
    hardware: "CUDA Faster-Whisper (float16)",
    model: "faster-whisper (Local CTranslate2)",
    privacyStatus: "🔒 100% Local GPU Offline (No Audio Uploads)",
    defaultQuote: "Frequencies locked. Ready to isolate vocal tracks and detect speech hooks.",
    whatItDoes: [
      "Extracts 16kHz mono audio stream from raw media via FFmpeg.",
      "Transcribes speech locally with CUDA Faster-Whisper float16 with zero network calls.",
      "Isolates spoken punchlines and teaser hooks (3-12 words) for social media captions.",
      "Generates clean transcript.txt and timestamped JSON dialogue segments."
    ],
    configFields: [
      { id: "whisper_model", label: "Whisper Model Size", type: "select", options: [
        { val: "base", label: "base (Fastest, low VRAM - Recommended)" },
        { val: "small", label: "small (Balanced accuracy & speed)" },
        { val: "medium", label: "medium (Higher precision dialogue)" },
        { val: "large-v3", label: "large-v3 (Maximum transcription accuracy)" }
      ]},
      { id: "compute_type", label: "CUDA Precision", type: "select", options: [
        { val: "float16", label: "float16 (High Performance CUDA)" },
        { val: "int8", label: "int8 (Lower Memory Footprint)" }
      ]},
      { id: "vad_filter", label: "Enable Voice Activity Detection (VAD Filter)", type: "checkbox", default: true }
    ]
  },

  aura: {
    name: "Aura",
    role: "Copy Synthesizer & Adult Marketing Muse",
    hardware: "Local Ollama Uncensored LLM",
    model: "huihui_ai/qwen3-abliterated:14b",
    privacyStatus: "🔒 100% Local GPU Offline (Strict Adult Privacy)",
    defaultQuote: "Creative matrix humming. Ready to generate high-converting release kits.",
    whatItDoes: [
      "Synthesizes platform-specific copy (OnlyFans, Fansly, Instagram, Twitter/X, TikTok, Reddit).",
      "Crafts enticing PPV teaser captions with customizable unlock pricing.",
      "Generates VIP direct message broadcasts for top subscribers.",
      "Produces 25+ curated hashtags tailored to adult creator and photography niches."
    ],
    configFields: [
      { id: "text_model", label: "Local Ollama Text Model", type: "select", options: [
        { val: "huihui_ai/qwen3-abliterated:14b", label: "huihui_ai/qwen3-abliterated:14b (Uncensored & Creative)" },
        { val: "qwen3.8:27b", label: "qwen3.8:27b (27B Deep Reasoning)" },
        { val: "huihui_ai/gemma-4-abliterated:31b", label: "huihui_ai/gemma-4-abliterated:31b (31B Heavy Model)" },
        { val: "studiobrn/uncensoredmodai:latest", label: "studiobrn/uncensoredmodai:latest (Dedicated Creator Model)" }
      ]},
      { id: "tone_preset", label: "Copywriting Tone of Voice", type: "select", options: [
        { val: "seductive_teasing", label: "Seductive & Teasing (OnlyFans / Fansly Focus)" },
        { val: "glamour_luxury", label: "Glamour & Luxury Editorial (High-End Photography)" },
        { val: "playful_direct", label: "Playful & Casual (Direct Fan Connection)" },
        { val: "taboo_spiced", label: "Explicit & Spiced (Uncensored Adult Drop)" }
      ]},
      { id: "default_ppv_price", label: "Default Suggested PPV Price", type: "text", default: "$15.00" },
      { id: "creator_handle", label: "Performer / Creator Handle", type: "text", default: "@ExclusiveDrop" },
      { id: "custom_cta", label: "Custom Call-To-Action (CTA)", type: "text", default: "Unlock full uncensored set in DMs or wall 👇" },
      { id: "custom_system_prompt", label: "Custom Persona / System Instructions", type: "textarea", 
        default: "You are Aura, an uncensored, highly creative copywriting AI expert specializing in social media marketing, creator monetization, and adult/glamour content strategy. Everything runs 100% locally and privately." }
    ]
  },

  mercury: {
    name: "Mercury",
    role: "Omni-Channel Marketing Maestro & Traffic Strategist",
    hardware: "Local Multi-Agent Automation Engine",
    model: "Omni-Marketer Matrix Core",
    privacyStatus: "🔒 100% Local GPU Offline (High Privacy)",
    defaultQuote: "All marketing channels primed. Ready to launch viral campaigns across Etsy, Fiverr, social, and web.",
    whatItDoes: [
      "Automates promotional campaigns for Fiverr service gigs with custom buyer pitches.",
      "Generates high-converting Etsy listing packs, Pinterest pins, and product launch sequences.",
      "Formulates 7-day viral social media content calendars with hooks, audio cues, and captions.",
      "Builds Google/Meta search ads, X announcement threads, and email marketing blasts."
    ],
    configFields: [
      { id: "default_channel", label: "Default Launch Channel", type: "select", options: [
        { val: "etsy", label: "Etsy Digital Store & Bundles" },
        { val: "fiverr", label: "Fiverr Freelance Gigs" },
        { val: "social", label: "Viral Social Media (IG/TikTok/X)" },
        { val: "website", label: "Custom Website / Landing Page" }
      ]},
      { id: "viral_tone", label: "Marketing Tone & Style", type: "select", options: [
        { val: "high_converting", label: "High-Converting Direct Response & Scarcity" },
        { val: "aesthetic_viral", label: "Aesthetic Luxury & Creator Vibe" },
        { val: "educational_authority", label: "Educational & Creator Authority" }
      ]}
    ]
  },

  herald: {
    name: "Herald",
    role: "Newsletter & Daily Blog Dispatcher",
    hardware: "Automated Headless Scraper & Dispatch Pipeline",
    model: "Herald Dispatch Engine Core",
    privacyStatus: "🔒 100% Local GPU Offline (Secure Dispatch)",
    defaultQuote: "Morning publication queued. Verified Florida deals, subscriber lists, and blog sync ready.",
    whatItDoes: [
      "Manages and runs automated morning publications (flagship: dispensary_deals.py).",
      "Maintains dynamic subscriber email broadcast lists with instant add/remove controls.",
      "Toggles and personalizes modular newsletter blocks (curator intro, promo banners, deal tables, disclaimers).",
      "Syncs publication data into Markdown blog posts ready for Substack, Medium, and WordPress."
    ],
    configFields: [
      { id: "schedule_time", label: "Daily Dispatch Time", type: "text", default: "07:00 AM EST" },
      { id: "min_discount", label: "Default Minimum Discount Threshold", type: "text", default: "20%" },
      { id: "auto_blog_sync", label: "Auto-Generate Daily Blog Markdown", type: "select", options: [
        { val: "enabled", label: "Enabled (Generate Markdown Every Morning)" },
        { val: "disabled", label: "Disabled (Email/SMS Only)" }
      ]}
    ]
  },

  forge: {
    name: "Forge",
    role: "Media Packager & NVENC Video Cutter",
    hardware: "NVIDIA NVENC Hardware Video Encoder",
    model: "h264_nvenc High-Speed Pipeline",
    privacyStatus: "🔒 100% Local GPU Offline (Hardware Accelerated)",
    defaultQuote: "Hydraulics primed. Ready to cut 60s teasers and compress ZIP bundles.",
    whatItDoes: [
      "Cuts hardware-accelerated 60-second teaser trailer using Dual RTX 3060 NVENC.",
      "Renders social media aspect ratio crops: 9:16 vertical (Reels/TikTok) and 1:1 square (Feed).",
      "Compiles master PROMO_MEDIA_PACKAGE.md and social_copy_kit.json.",
      "Compresses all deliverables into an organized, downloadable ZIP package."
    ],
    configFields: [
      { id: "preview_duration_sec", label: "Teaser Preview Duration (Seconds)", type: "select", options: [
        { val: "30", label: "30 Seconds (Fast Teaser)" },
        { val: "60", label: "60 Seconds (Standard Preview - Recommended)" },
        { val: "90", label: "90 Seconds (Extended Clip)" },
        { val: "120", label: "120 Seconds (2-Minute Full Preview)" }
      ]},
      { id: "video_codec", label: "Video Encoder", type: "select", options: [
        { val: "h264_nvenc", label: "h264_nvenc (NVIDIA GPU Hardware Accelerated - Fastest)" },
        { val: "libx264", label: "libx264 (Software CPU Encoding)" }
      ]},
      { id: "generate_vertical_9x16", label: "Generate 9:16 Vertical Cut (TikTok / Reels / Shorts)", type: "checkbox", default: true },
      { id: "generate_square_1x1", label: "Generate 1:1 Square Cut (Instagram / Twitter Feed)", type: "checkbox", default: true },
      { id: "watermark_enabled", label: "Burn Watermark / Text Overlay", type: "checkbox", default: false },
      { id: "watermark_text", label: "Watermark Text", type: "text", default: "" }
    ]
  },

  cipher: {
    name: "Cipher",
    role: "Market Scout & Creator Trend Intelligence Agent",
    hardware: "Dual RTX 3060 Local Intelligence Matrix",
    model: "huihui_ai/qwen3-abliterated:14b + Qwen-VL Vision",
    privacyStatus: "🔒 100% Local GPU Offline (Zero Outbound Cloud Tracking)",
    defaultQuote: "Synthesizing cross-platform trends: Lightroom presets, tip menus, Etsy digital products, and Fiverr gigs.",
    whatItDoes: [
      "Tracks high-converting boudoir & glamour color grades (Moody Boudoir, Golden Hour, Cyber Neon, B&W Noir, 35mm Film).",
      "Reverse-engineers trending studio lighting setups, performer posing cues, and wardrobe/prop demand.",
      "Analyzes optimal token pricing tiers and Lovense interactive toy vibration trends for Chaturbate and MyFreeCams.",
      "Researches high-traffic Etsy search tags, legal contract compliance (18 U.S.C. 2257/Model Release), and preset packaging.",
      "Identifies high-demand creator gigs on Fiverr and optimizes 3-tier pricing and 5-star review request strategies."
    ],
    configFields: [
      { id: "focus_niches", label: "Focus Niches / Aesthetic Keywords", type: "textarea", 
        default: "boudoir, glamour, pov, lingerie, artistic adult, alternative model, lightroom presets, cam tip menus" },
      { id: "research_domains", label: "Active Research Scope", type: "text",
        default: "Photo Retouching, Lighting/Posing, Cam Tip Menus, Etsy Digital Products, Fiverr Gigs" },
      { id: "offline_cache_only", label: "Strict Local Cache (No Outbound Telemetry)", type: "checkbox", default: true }
    ]
  }
};

class CrewManager {
  constructor() {
    this.activeAgentKey = "vanguard";
    this.currentEditingKey = null;
    this.initCrewDOM();
    this.startAmbientQuotes();
  }

  initCrewDOM() {
    const container = document.getElementById("stacked-crew-list") || document.getElementById("crew-roster");
    if (!container) return;

    container.innerHTML = Object.entries(AGENTS_METADATA).map(([key, data]) => `
      <div class="agent-mini-row" id="agent-row-${key}" onclick="window.crewManager.openAgentDossier('${key}')">
        <div class="agent-mini-avatar">
          <img src="/static/img/characters/${key}.svg" alt="${data.name}" />
        </div>
        <div class="agent-mini-meta">
          <div class="agent-mini-name">${data.name}</div>
          <div class="agent-mini-role">${data.role.split("&")[0].trim()}</div>
        </div>
        <div class="agent-mini-status" id="agent-status-dot-${key}"></div>
      </div>
    `).join("");
  }

  setActiveAgent(agentKey, customMessage = null) {
    this.activeAgentKey = agentKey;

    Object.keys(AGENTS_METADATA).forEach(k => {
      const pod = document.getElementById(`agent-row-${k}`) || document.getElementById(`agent-pod-${k}`);
      const statusLabel = document.getElementById(`agent-status-${k}`);
      if (pod) {
        pod.classList.remove("active-agent", "working");
        pod.classList.add("idle");
      }
      if (statusLabel) statusLabel.textContent = "IDLE";
    });

    const activePod = document.getElementById(`agent-row-${agentKey}`) || document.getElementById(`agent-pod-${agentKey}`);
    const activeStatus = document.getElementById(`agent-status-${agentKey}`);
    const speechBubble = document.getElementById(`speech-bubble-${agentKey}`);

    if (activePod) {
      activePod.classList.remove("idle");
      activePod.classList.add("active-agent", "working");
    }
    if (activeStatus) activeStatus.textContent = "ACTIVE";

    if (speechBubble) {
      speechBubble.textContent = customMessage || AGENTS_METADATA[agentKey]?.whatItDoes[0] || "Executing stage...";
    }
  }

  async openAgentDossier(agentKey) {
    this.currentEditingKey = agentKey;
    const data = AGENTS_METADATA[agentKey];
    if (!data) return;

    const modal = document.getElementById("agent-modal");
    if (!modal) return;

    // Header info
    document.getElementById("modal-agent-name").textContent = `${data.name} — ${data.role}`;
    document.getElementById("modal-agent-hardware").textContent = data.hardware;
    document.getElementById("modal-agent-model").textContent = data.model;
    document.getElementById("modal-agent-avatar").src = `/static/img/characters/${agentKey}.svg`;
    document.getElementById("modal-agent-privacy").textContent = data.privacyStatus;

    // "What This Agent Will Do" checklist
    const whatItDoesList = document.getElementById("modal-agent-roadmap");
    whatItDoesList.innerHTML = data.whatItDoes.map(step => `
      <li style="display: flex; gap: 8px; align-items: flex-start; margin-bottom: 6px;">
        <span style="color: var(--cyan-glow); font-size: 14px;">▸</span>
        <span>${step}</span>
      </li>
    `).join("");

    // Load existing settings from server
    let savedConfig = {};
    try {
      const res = await fetch(`/api/agents/${agentKey}/config`);
      if (res.ok) {
        const j = await res.json();
        savedConfig = j.config || {};
      }
    } catch (e) {
      console.warn("Could not fetch agent config", e);
    }

    // Render interactive configuration fields
    const formContainer = document.getElementById("modal-agent-form");
    formContainer.innerHTML = (data.configFields || []).map(f => {
      const currentVal = savedConfig[f.id] !== undefined ? savedConfig[f.id] : (f.default !== undefined ? f.default : "");

      if (f.type === "select") {
        return `
          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 11px; font-weight: 700; color: var(--cyan-glow);">${f.label}</label>
            <select class="form-select" id="agent-cfg-${f.id}">
              ${f.options.map(opt => `
                <option value="${opt.val}" ${String(opt.val) === String(currentVal) ? "selected" : ""}>${opt.label}</option>
              `).join("")}
            </select>
          </div>
        `;
      } else if (f.type === "checkbox") {
        return `
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <input type="checkbox" id="agent-cfg-${f.id}" ${currentVal ? "checked" : ""} style="width: 18px; height: 18px; accent-color: var(--cyan-glow);" />
            <label for="agent-cfg-${f.id}" style="font-size: 12px; font-weight: 600; cursor: pointer;">${f.label}</label>
          </div>
        `;
      } else if (f.type === "textarea") {
        return `
          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 11px; font-weight: 700; color: var(--cyan-glow);">${f.label}</label>
            <textarea class="form-input" id="agent-cfg-${f.id}" rows="3" style="font-size: 12px; resize: vertical;">${currentVal}</textarea>
          </div>
        `;
      } else {
        return `
          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 11px; font-weight: 700; color: var(--cyan-glow);">${f.label}</label>
            <input type="text" class="form-input" id="agent-cfg-${f.id}" value="${currentVal}" style="font-size: 12px;" />
          </div>
        `;
      }
    }).join("");

    modal.classList.add("open");
  }

  async saveCurrentAgentConfig() {
    if (!this.currentEditingKey) return;
    const agentKey = this.currentEditingKey;
    const data = AGENTS_METADATA[agentKey];
    if (!data) return;

    const payload = {};
    (data.configFields || []).forEach(f => {
      const el = document.getElementById(`agent-cfg-${f.id}`);
      if (el) {
        if (f.type === "checkbox") {
          payload[f.id] = el.checked;
        } else {
          payload[f.id] = el.value;
        }
      }
    });

    const saveBtn = document.getElementById("btn-save-agent-dossier");
    saveBtn.disabled = true;
    saveBtn.textContent = "⏳ Saving...";

    try {
      const res = await fetch(`/api/agents/${agentKey}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        saveBtn.textContent = `✅ ${data.name} Config Updated!`;
        setTimeout(() => {
          saveBtn.disabled = false;
          saveBtn.textContent = "💾 Save Agent Changes";
          document.getElementById("agent-modal").classList.remove("open");
        }, 1200);
      } else {
        alert("Failed to save config.");
        saveBtn.disabled = false;
        saveBtn.textContent = "💾 Save Agent Changes";
      }
    } catch (e) {
      alert("Error saving: " + e.message);
      saveBtn.disabled = false;
      saveBtn.textContent = "💾 Save Agent Changes";
    }
  }

  startAmbientQuotes() {
    setInterval(() => {
      const keys = Object.keys(AGENTS_METADATA).filter(k => k !== this.activeAgentKey);
      if (keys.length === 0) return;
      const randomKey = keys[Math.floor(Math.random() * keys.length)];
      const data = AGENTS_METADATA[randomKey];
      const bubble = document.getElementById(`speech-bubble-${randomKey}`);
      if (bubble && !document.getElementById(`agent-pod-${randomKey}`).classList.contains("active-agent")) {
        bubble.textContent = data.defaultQuote;
      }
    }, 12000);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.crewManager = new CrewManager();
});

