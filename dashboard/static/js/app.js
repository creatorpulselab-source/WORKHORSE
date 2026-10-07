// ==========================================================================
// WORKHORSE AI COMMAND CENTER — APP MANAGER & SYSTEM TELEMETRY
// ==========================================================================

class AppController {
  constructor() {
    this.pollTelemetry();
    this.initSettingsModal();
    this.initBrandModal();
    this.initVramManager();
    this.initPrismLauncher();
    this.loadSystemModels();
  }

  async pollTelemetry() {
    try {
      const res = await fetch("/api/system/stats");
      if (res.ok) {
        const data = await res.json();
        this.updateHudStats(data);
      }
    } catch (e) {
      console.warn("Telemetry fetch error", e);
    }
    setTimeout(() => this.pollTelemetry(), 4000);
  }

  updateHudStats(data) {
    if (!data) return;

    // GPU 0
    const gpu0 = data.gpus?.[0];
    const gpu0El = document.getElementById("hud-gpu0-val");
    if (gpu0El && gpu0) {
      gpu0El.textContent = `GPU 0 [Synapse/Iris]: ${(gpu0.memory_used_mb / 1024).toFixed(1)} / ${(gpu0.memory_total_mb / 1024).toFixed(0)} GB (${gpu0.utilization_gpu_percent}% · ${gpu0.temperature_c}°C)`;
    }

    // GPU 1
    const gpu1 = data.gpus?.[1];
    const gpu1El = document.getElementById("hud-gpu1-val");
    if (gpu1El && gpu1) {
      gpu1El.textContent = `GPU 1 [Echo/Forge]: ${(gpu1.memory_used_mb / 1024).toFixed(1)} / ${(gpu1.memory_total_mb / 1024).toFixed(0)} GB (${gpu1.utilization_gpu_percent}% · ${gpu1.temperature_c}°C)`;
    }

    // Disk
    const disk = data.disk;
    const diskEl = document.getElementById("hud-disk-val");
    if (diskEl && disk) {
      diskEl.textContent = `F: Drive: ${disk.free_gb} GB Free (${disk.percent_used}% Used)`;
    }

    // Ollama
    const ollama = data.ollama;
    
    // VRAM Watchdog
    const vram = data.vram_watchdog;
    const vramEl = document.getElementById("hud-vram-val");
    const vramDot = document.getElementById("hud-vram-dot");
    if (vramEl && vram) {
      if (vram.is_busy) {
        vramEl.textContent = "VRAM: Job Active ⚡";
        if (vramDot) vramDot.style.background = "#ff007f";
      } else if (vram.loaded_models_count > 0) {
        vramEl.textContent = `VRAM: ${vram.total_vram_used_mb}MB · Idle ${vram.idle_formatted}`;
        if (vramDot) vramDot.style.background = "#ffd166";
      } else {
        vramEl.textContent = `VRAM: Clean · Idle ${vram.idle_formatted}`;
        if (vramDot) vramDot.style.background = "#06d6a0";
      }
    }

    const ollamaEl = document.getElementById("hud-ollama-val");
    if (ollamaEl && ollama) {
      ollamaEl.textContent = ollama.online ? `Ollama: Online (${ollama.models?.length || 0} models)` : "Ollama: Offline";
    }

    // ComfyUI (RTX 5070 Ti Main PC) health - alert banner if it goes offline.
    // Backed by a 45s-interval background monitor on the server; see
    // comfy_health_monitor_loop() in dashboard/server.py.
    this.updateComfyHealthBanner(data.comfy_health);
  }

  updateComfyHealthBanner(comfyHealth) {
    if (!comfyHealth || comfyHealth.online === null || comfyHealth.online === undefined) return;

    let banner = document.getElementById("comfy-offline-banner");
    if (comfyHealth.online === false) {
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "comfy-offline-banner";
        banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;background:#ff2d55;color:#fff;text-align:center;padding:8px 12px;font-family:monospace;font-size:13px;font-weight:bold;letter-spacing:0.5px;box-shadow:0 2px 8px rgba(0,0,0,0.4);";
        document.body.prepend(banner);
      }
      banner.textContent = `⚠ COMFYUI OFFLINE (Main PC ${comfyHealth.host || ""}) - image/video generation unavailable. Last checked ${comfyHealth.last_checked || "unknown"}.`;
    } else if (banner) {
      banner.remove();
    }
  }

  async loadSystemModels() {
    try {
      const res = await fetch("/api/system/models");
      if (res.ok) {
        const data = await res.json();
        const textSelect = document.getElementById("setting-ollama-text");
        const visionSelect = document.getElementById("setting-ollama-vision");

        if (data.models && textSelect && visionSelect) {
          textSelect.innerHTML = data.models.map(m => `
            <option value="${m.name}">${m.name} (${m.size_gb} GB)</option>
          `).join("");

          const visionModels = data.models.filter(m => m.is_vision);
          visionSelect.innerHTML = (visionModels.length > 0 ? visionModels : data.models).map(m => `
            <option value="${m.name}">${m.name} (${m.size_gb} GB)</option>
          `).join("");
        }
      }
    } catch (e) {
      console.warn("Failed to load models list", e);
    }
  }

  
  
  initVramManager() {
    const pill = document.getElementById("hud-vram-pill");
    const btn = document.getElementById("btn-quick-purge-vram");
    
    const purgeHandler = async (e) => {
      e.stopPropagation();
      const valEl = document.getElementById("hud-vram-val");
      const dotEl = document.getElementById("hud-vram-dot");
      if (valEl) valEl.textContent = "VRAM: Purging...";
      if (dotEl) dotEl.style.background = "#00f2fe";
      try {
        const res = await fetch("/api/vram/purge", { method: "POST" });
        if (res.ok) {
          const result = await res.json();
          const unloaded = result.report?.unloaded_models || [];
          if (valEl) {
            valEl.textContent = unloaded.length > 0 
              ? `VRAM: Freed ${unloaded.length} Model${unloaded.length > 1 ? 's' : ''}! 🧹` 
              : "VRAM: Already Clear! ✨";
          }
          if (dotEl) dotEl.style.background = "#06d6a0";
          setTimeout(() => this.pollTelemetry(), 1500);
        }
      } catch (err) {
        console.error("Purge VRAM failed", err);
      }
    };

    if (btn) btn.addEventListener("click", purgeHandler);
    if (pill) pill.addEventListener("click", purgeHandler);
  }

  initBrandModal() {
    const modal = document.getElementById("brand-modal");
    const openBtn = document.getElementById("btn-open-brand");
    const closeBtn = document.getElementById("btn-close-brand");
    const openFolderBtn = document.getElementById("btn-open-brand-folder-disk");

    if (openBtn && modal) {
      openBtn.addEventListener("click", () => modal.classList.add("open"));
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.remove("open"));
    }
    if (openFolderBtn) {
      openFolderBtn.addEventListener("click", async () => {
        try {
          await fetch("/api/open-brand-folder", { method: "POST" });
        } catch (e) {
          console.error("Error opening brand folder", e);
        }
      });
    }
  }

  initSettingsModal() {
    const modal = document.getElementById("settings-modal");
    const openBtn = document.getElementById("btn-open-settings");
    const closeBtn = document.getElementById("btn-close-settings");
    const saveBtn = document.getElementById("btn-save-settings");

    if (openBtn && modal) {
      openBtn.addEventListener("click", () => modal.classList.add("open"));
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.remove("open"));
    }
    if (saveBtn) {
      saveBtn.addEventListener("click", async () => {
        const configPayload = {
          gemini_api_key: document.getElementById("setting-gemini-key")?.value || "",
          openai_api_key: document.getElementById("setting-openai-key")?.value || "",
          ollama_text_model: document.getElementById("setting-ollama-text")?.value,
          ollama_vision_model: document.getElementById("setting-ollama-vision")?.value
        };

        const res = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(configPayload)
        });

        if (res.ok) {
          saveBtn.textContent = "✅ Settings Saved!";
          setTimeout(() => {
            saveBtn.textContent = "💾 Save Settings";
            modal.classList.remove("open");
          }, 1200);
        }
      });
    }
  }

  initPrismLauncher() {
    const launchBtn = document.getElementById("btn-launch-prism");
    if (!launchBtn) return;

    launchBtn.addEventListener("click", async () => {
      launchBtn.disabled = true;
      launchBtn.textContent = "⏳ Starting Local Prism Copy...";

      try {
        const res = await fetch("/api/prism/launch", { method: "POST" });
        const data = await res.json();
        if (res.ok && data.url) {
          launchBtn.textContent = "🚀 Prism Studio Running (Open)";
          window.open(data.url, "_blank");
          setTimeout(() => {
            launchBtn.disabled = false;
            launchBtn.innerHTML = `✨ Launch Local Prism Copy`;
          }, 3000);
        } else {
          alert(`Prism launch note: ${data.message || data.detail}`);
          launchBtn.disabled = false;
          launchBtn.innerHTML = `✨ Launch Local Prism Copy`;
        }
      } catch (e) {
        alert("Failed to trigger local Prism copy: " + e.message);
        launchBtn.disabled = false;
        launchBtn.innerHTML = `✨ Launch Local Prism Copy`;
      }
    });
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.appController = new AppController();
});
