// Universal Folder Opener for PC (Windows Explorer) & Mobile (In-Browser Files Modal)
window.openWorkspaceFolder = async function(folderPath, folderLabel = "Workspace Folder") {
  try {
    const res = await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folderPath })
    });
    const data = await res.json();
    if (res.ok) {
      if (window.appController && window.appController.showFolderBrowserModal) {
        window.appController.showFolderBrowserModal(data, folderLabel);
      }
      if (window.pipelineController && data.opened) {
        window.pipelineController.addLogLine(`📂 Folder: ${folderLabel} (${data.total_files || 0} items)`, "success");
      }
    }
  } catch (e) {
    console.error("Failed to open folder", e);
  }
};

// ==========================================================================
// WORKHORSE AI COMMAND CENTER — APP MANAGER & SYSTEM TELEMETRY
// ==========================================================================

class AppController {
  constructor() {
    this.pollTelemetry();
    this.initRealtimeAgentMonitor();
    this.initSettingsModal();
    this.initBrandModal();
    this.initVramManager();
    this.initPrismLauncher();
    this.initFolderBrowser();
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
      openFolderBtn.addEventListener("click", () => window.openWorkspaceFolder("F:/WORKHORSE/workspace/brand_assets", "Brand Assets & Banners"));
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

  initRealtimeAgentMonitor() {
    this.pollAgentMonitor();
    
    // Toggle expand roster grid
    const toggleBtn = document.getElementById("btn-toggle-monitor-expand");
    const rosterGrid = document.getElementById("monitor-expand-roster");
    if (toggleBtn && rosterGrid) {
      toggleBtn.addEventListener("click", () => {
        rosterGrid.classList.toggle("open");
        const isOpen = rosterGrid.classList.contains("open");
        toggleBtn.textContent = isOpen ? "👥 Collapse Roster" : `👥 Roster (${this.lastActiveCount || 0}/14 Active)`;
      });
    }

    // Stop stuck/active job button
    const stopBtn = document.getElementById("btn-monitor-stop-job");
    if (stopBtn) {
      stopBtn.addEventListener("click", async () => {
        const jobId = stopBtn.dataset.jobId;
        if (!jobId) return;
        if (!confirm(`Are you sure you want to halt job ${jobId}? This will stop processing immediately.`)) return;
        stopBtn.disabled = true;
        stopBtn.textContent = "🛑 Halting...";
        try {
          const res = await fetch(`/api/pipeline/jobs/${jobId}/cancel`, { method: "POST" });
          const data = await res.json();
          if (res.ok) {
            alert(`Job ${jobId} cancellation initiated.`);
          } else {
            alert(`Could not cancel job: ${data.detail || data.message}`);
          }
        } catch (e) {
          alert(`Failed to cancel job: ${e.message}`);
        } finally {
          setTimeout(() => this.pollAgentMonitor(), 1000);
        }
      });
    }

    // Emergency abort all button
    const abortBtn = document.getElementById("btn-monitor-emergency-abort");
    if (abortBtn) {
      abortBtn.addEventListener("click", async () => {
        if (!confirm("EMERGENCY ABORT: Are you sure you want to stop all active pipeline jobs, ComfyUI renders, and purge local GPU VRAM?")) return;
        abortBtn.disabled = true;
        abortBtn.textContent = "🛑 Stopping All...";
        try {
          const res = await fetch("/api/monitor/stop-process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target: "emergency_stop" })
          });
          const data = await res.json();
          alert(`Emergency Abort executed:\n${data.message}`);
        } catch (e) {
          alert(`Emergency abort error: ${e.message}`);
        } finally {
          abortBtn.disabled = false;
          abortBtn.textContent = "🛑 Emergency Abort";
          setTimeout(() => this.pollAgentMonitor(), 1200);
        }
      });
    }
  }

  async pollAgentMonitor() {
    try {
      const res = await fetch("/api/monitor/agents-active");
      if (res.ok) {
        const data = await res.json();
        this.updateAgentMonitorUI(data);
      }
    } catch (e) {
      console.warn("Agent monitor poll error", e);
    }
    setTimeout(() => this.pollAgentMonitor(), 3000);
  }

  updateAgentMonitorUI(data) {
    if (!data) return;
    if (data.version && window.__WORKHORSE_VERSION__ && data.version !== window.__WORKHORSE_VERSION__) {
      window.location.reload(true);
      return;
    }
    this.lastActiveCount = data.active_count || 0;

    const countBadge = document.getElementById("monitor-active-count-badge");
    if (countBadge) countBadge.textContent = data.active_count || 0;

    const statusBadge = document.getElementById("monitor-status-badge");
    const pulseDot = document.getElementById("monitor-pulse-dot");
    const taskText = document.getElementById("monitor-task-text");
    const stopBtn = document.getElementById("btn-monitor-stop-job");
    const progressRow = document.getElementById("monitor-progress-container");
    const progressFill = document.getElementById("monitor-progress-fill");
    const progressLabel = document.getElementById("monitor-progress-label");
    const elapsedLabel = document.getElementById("monitor-elapsed-label");
    const stalledWarning = document.getElementById("monitor-stalled-warning");

    const hasActive = Boolean(data.has_active);
    const hasStalled = Boolean(data.stalled_count > 0);
    const primaryJob = (data.active_jobs && data.active_jobs.length > 0) ? data.active_jobs[0] : null;

    if (hasStalled) {
      if (statusBadge) {
        statusBadge.className = "monitor-status-pill stalled";
        statusBadge.innerHTML = `<span class="pulse-dot" style="background:#ef4444;"></span> ⚠️ STALLED (${data.stalled_count})`;
      }
      if (pulseDot) pulseDot.style.background = "#ef4444";
      if (stalledWarning) {
        stalledWarning.style.display = "block";
        stalledWarning.textContent = `⚠️ STALLED: ${data.stalled_alerts[0]?.message || 'Process taking longer than expected'}`;
      }
    } else if (hasActive) {
      if (statusBadge) {
        statusBadge.className = "monitor-status-pill active";
        statusBadge.innerHTML = `<span class="pulse-dot" style="background:#00f2fe;"></span> PROCESSING (${data.active_count} AGENTS)`;
      }
      if (pulseDot) pulseDot.style.background = "#00f2fe";
      if (stalledWarning) stalledWarning.style.display = "none";
    } else {
      if (statusBadge) {
        statusBadge.className = "monitor-status-pill";
        statusBadge.innerHTML = `<span class="pulse-dot" style="background:#06d6a0;"></span> IDLE`;
      }
      if (pulseDot) pulseDot.style.background = "#06d6a0";
      if (stalledWarning) stalledWarning.style.display = "none";
    }

    if (primaryJob) {
      if (taskText) taskText.textContent = `${primaryJob.active_agent?.toUpperCase()}: ${primaryJob.agent_message || 'Processing stage...'}`;
      if (stopBtn) {
        stopBtn.style.display = "inline-flex";
        stopBtn.disabled = false;
        stopBtn.dataset.jobId = primaryJob.job_id;
        stopBtn.textContent = `🛑 Stop Job (${primaryJob.active_agent?.toUpperCase()})`;
      }
      if (progressRow) progressRow.style.display = "flex";
      if (progressFill) {
        const pct = primaryJob.progress || 0;
        progressFill.style.width = `${pct}%`;
        progressFill.className = primaryJob.is_stalled ? "monitor-progress-fill stalled" : "monitor-progress-fill";
      }
      if (progressLabel) progressLabel.textContent = `Stage ${primaryJob.current_stage || 1}/8 · ${primaryJob.progress || 0}%`;
      if (elapsedLabel) {
        const sec = primaryJob.stage_elapsed_sec || 0;
        const mins = Math.floor(sec / 60);
        const remSecs = Math.floor(sec % 60);
        elapsedLabel.textContent = `Stage Runtime: ${String(mins).padStart(2, '0')}:${String(remSecs).padStart(2, '0')}`;
      }
    } else if (hasActive) {
      const activeAgent = data.agents?.find(a => a.state === 'active');
      if (taskText) taskText.textContent = activeAgent ? `${activeAgent.name}: ${activeAgent.current_task}` : 'Active tasks running in studio...';
      if (stopBtn) stopBtn.style.display = "none";
      if (progressRow) progressRow.style.display = "none";
    } else {
      if (taskText) taskText.textContent = "All 14 Agents Standing By · Systems Idle";
      if (stopBtn) stopBtn.style.display = "none";
      if (progressRow) progressRow.style.display = "none";
    }

    // Active Agent Chips Strip
    const chipsStrip = document.getElementById("monitor-agent-chips");
    if (chipsStrip && data.agents) {
      chipsStrip.innerHTML = data.agents.map(a => {
        let cls = "agent-chip";
        let dot = "⚪";
        if (a.state === "stalled") {
          cls += " stalled";
          dot = "🔴";
        } else if (a.state === "active") {
          cls += " active";
          dot = "🔵";
        }
        return `<span class="${cls}" title="${a.name} [${a.symbol}] — ${a.title}\nHardware: ${a.hardware}\nStatus: ${a.state.toUpperCase()}\nTask: ${a.current_task}">${dot} ${a.symbol} ${a.name}</span>`;
      }).join("");
    }

    // Sync 3D character cards & chamber states with live backend telemetry
    if (window.character3dEngine && data.agents) {
      data.agents.forEach(a => {
        const isWorking = (a.state === "active" || a.state === "stalled");
        window.character3dEngine.setAgentState(a.id, isWorking ? "working" : "idle");
      });
    }

    // Expandable Roster Grid
    const rosterGrid = document.getElementById("monitor-expand-roster");
    if (rosterGrid && data.agents && rosterGrid.classList.contains("open")) {
      rosterGrid.innerHTML = data.agents.map(a => `
        <div class="agent-status-tile ${a.state}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; font-weight:800; color:#fff;">${a.symbol} ${a.name}</span>
            <span style="font-size:9.5px; font-weight:700; padding:2px 6px; border-radius:4px; ${a.state === 'stalled' ? 'background:#ef4444; color:#fff;' : (a.state === 'active' ? 'background:#00f2fe; color:#000;' : 'background:rgba(255,255,255,0.08); color:#94a3b8;')}">${a.state.toUpperCase()}</span>
          </div>
          <div style="font-size:10px; color:#00f2fe; font-family:var(--font-mono);">${a.title}</div>
          <div style="font-size:10px; color:#94a3b8; line-height:1.3; margin-top:2px;">${a.current_task}</div>
          <div style="font-size:9px; color:#64748b; font-family:var(--font-mono); margin-top:3px;">⚡ ${a.hardware}</div>
        </div>
      `).join("");
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.appController = new AppController();
});
