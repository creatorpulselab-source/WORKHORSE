// ==========================================================================
// WORKHORSE AI PIPELINE — WEBSOCKET, JOBS, DELIVERABLES & FOLDER EXPLORER
// ==========================================================================

class PipelineController {
  constructor() {
    this.ws = null;
    this.currentJobId = null;
    this.uploadedFile = null;
    this.activeCopyKit = null;
    this.activeCopyTab = "instagram";
    this.currentPackageDir = "F:/WORKHORSE/workspace/output";

    this.initWebSocket();
    this.initUploadEvents();
    this.initCopyTabs();
    this.initFolderButtons();
  }

  initWebSocket() {
    const loc = window.location;
    const protocol = loc.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${loc.host}/ws/telemetry`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.addLogLine("System connected to live telemetry stream.", "success");
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleEvent(data);
        } catch (e) {
          console.error("WS Parse Error", e);
        }
      };

      this.ws.onclose = () => {
        setTimeout(() => this.initWebSocket(), 3000);
      };
    } catch (e) {
      console.error("WebSocket failed", e);
    }
  }

  handleEvent(data) {
    if (data.type === "telemetry") {
      if (window.appController) {
        window.appController.updateHudStats(data.stats);
      }
    } else if (data.type === "job_update") {
      const job = data.job;
      if (!job) return;

      this.currentJobId = job.job_id;
      this.updateProgress(job.progress);
      this.updateStageStep(job.current_stage);
      if (window.factoryController) {
        window.factoryController.setPipelineStage(job.current_stage, job.active_agent, job.agent_message);
      }

      if (window.crewManager && job.active_agent) {
        window.crewManager.setActiveAgent(job.active_agent, job.agent_message);
      }

      if (job.logs && job.logs.length > 0) {
        const lastLog = job.logs[job.logs.length - 1];
        this.addLogLine(lastLog);
      }

      if (job.status === "completed") {
        this.addLogLine("🎉 Pipeline completed! All assets saved locally.", "success");
        this.renderResults(job);
        const runBtn = document.getElementById("btn-run-pipeline");
        runBtn.disabled = false;
        runBtn.innerHTML = `<i class="icon">🚀</i> Launch Pipeline Run`;
      } else if (job.status === "failed") {
        this.addLogLine(`❌ Pipeline failed: ${job.error}`, "error");
        const runBtn = document.getElementById("btn-run-pipeline");
        runBtn.disabled = false;
        runBtn.innerHTML = `<i class="icon">🚀</i> Launch Pipeline Run`;
      }
    }
  }

  updateProgress(pct) {
    const bar = document.getElementById("master-progress-fill");
    const label = document.getElementById("progress-percent-label");
    if (bar) bar.style.width = `${pct}%`;
    if (label) label.textContent = `${pct}%`;
  }

  updateStageStep(currentStage) {
    for (let i = 1; i <= 7; i++) {
      const el = document.getElementById(`stage-step-${i}`);
      if (!el) continue;

      el.classList.remove("active", "completed");
      if (i < currentStage) {
        el.classList.add("completed");
      } else if (i === currentStage) {
        el.classList.add("active");
      }
    }
  }

  addLogLine(text, cssClass = "") {
    const stream = document.getElementById("log-stream");
    if (!stream) return;

    const div = document.createElement("div");
    div.className = `log-entry ${cssClass}`;
    div.textContent = text;
    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
  }

  initUploadEvents() {
    const dropArea = document.getElementById("drop-area");
    const fileInput = document.getElementById("file-input");

    if (!dropArea || !fileInput) return;

    ["dragenter", "dragover"].forEach(evt => {
      dropArea.addEventListener(evt, (e) => {
        e.preventDefault();
        dropArea.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(evt => {
      dropArea.addEventListener(evt, (e) => {
        e.preventDefault();
        dropArea.classList.remove("dragover");
      });
    });

    dropArea.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) this.handleSelectedFile(files[0]);
    });

    dropArea.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) this.handleSelectedFile(e.target.files[0]);
    });

    const runBtn = document.getElementById("btn-run-pipeline");
    if (runBtn) {
      runBtn.addEventListener("click", () => this.startPipeline());
    }
  }

  handleSelectedFile(file) {
    this.uploadedFile = file;
    document.getElementById("selected-filename").textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
    document.getElementById("upload-placeholder").style.display = "none";
    document.getElementById("upload-preview-info").style.display = "flex";
    this.addLogLine(`Selected file: ${file.name}`, "highlight");
  }

  async startPipeline() {
    if (!this.uploadedFile) {
      alert("Please select or drop a video file first!");
      return;
    }

    const runBtn = document.getElementById("btn-run-pipeline");
    runBtn.disabled = true;
    runBtn.innerHTML = `<i class="icon">⏳</i> Vanguard Initializing...`;

    this.addLogLine("Uploading media to local WORKHORSE workspace...", "highlight");
    const formData = new FormData();
    formData.append("file", this.uploadedFile);

    try {
      const uploadRes = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const uploadData = await uploadRes.json();
      if (!uploadRes.ok) throw new Error(uploadData.detail || "Upload failed");

      const filePath = uploadData.saved_path;
      const preset = document.getElementById("pipeline-preset-select").value;

      this.addLogLine(`File saved locally: ${filePath}. Deploying agents...`, "success");

      const startRes = await fetch("/api/pipeline/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: filePath,
          preset: preset
        })
      });
      const startData = await startRes.json();
      if (!startRes.ok) throw new Error(startData.detail || "Failed to start job");

      this.currentJobId = startData.job_id;
      this.addLogLine(`Job [${startData.job_id}] running 100% locally on Dual RTX 3060.`, "success");

    } catch (e) {
      this.addLogLine(`Error: ${e.message}`, "error");
      runBtn.disabled = false;
      runBtn.innerHTML = `<i class="icon">🚀</i> Launch Pipeline Run`;
    }
  }

  renderResults(job) {
    const resultsContainer = document.getElementById("results-section");
    if (!resultsContainer) return;
    resultsContainer.style.display = "block";
    resultsContainer.scrollIntoView({ behavior: "smooth" });

    const bundle = job.results?.bundle || {};
    const copyKit = job.results?.copy_kit || {};
    this.activeCopyKit = copyKit;
    this.currentPackageDir = bundle.package_dir || "F:/WORKHORSE/workspace/output";

    // Update Output Location Text
    const locEl = document.getElementById("output-location-path");
    if (locEl) {
      locEl.textContent = this.currentPackageDir;
    }

    // Render Preview Video Player
    const player = document.getElementById("preview-video-player");
    if (bundle.previews?.preview_60s) {
      player.src = `/api/media/${encodeURIComponent(bundle.previews.preview_60s)}`;
      player.load();
    }

    // Render 6 Pose Screenshots
    const posesStrip = document.getElementById("poses-strip");
    if (posesStrip && bundle.poses) {
      posesStrip.innerHTML = bundle.poses.map((p, idx) => `
        <div class="pose-thumb" onclick="window.open('/api/media/${encodeURIComponent(p)}', '_blank')">
          <img src="/api/media/${encodeURIComponent(p)}" alt="Pose ${idx+1}" title="Pose ${idx+1} (Click to open full res)" />
        </div>
      `).join("");
    }

    // Render Copywriting
    this.renderCopyTabContent();

    // Download ZIP button
    const zipBtn = document.getElementById("btn-download-zip");
    if (zipBtn && bundle.zip_name) {
      zipBtn.onclick = () => {
        window.location.href = `/api/download/zip/${job.job_id}`;
      };
      document.getElementById("zip-size-badge").textContent = `${bundle.zip_size_mb || 0} MB`;
    }
  }

  initFolderButtons() {
    const openFolderBtn = document.getElementById("btn-open-output-folder");
    if (openFolderBtn) {
      openFolderBtn.addEventListener("click", () => this.openFolderInExplorer(this.currentPackageDir));
    }

    const openHeaderBtn = document.getElementById("btn-header-open-folder");
    if (openHeaderBtn) {
      openHeaderBtn.addEventListener("click", () => this.openFolderInExplorer("F:/WORKHORSE/workspace/output"));
    }
  }

  async openFolderInExplorer(folderPath) {
    try {
      const res = await fetch("/api/open-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: folderPath })
      });
      const data = await res.json();
      if (res.ok) {
        this.addLogLine(`Opened Windows File Explorer at: ${data.opened}`, "success");
      }
    } catch (e) {
      console.warn("Could not open folder in Explorer", e);
    }
  }

  initCopyTabs() {
    const tabs = document.querySelectorAll(".copy-tab");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        this.activeCopyTab = tab.dataset.platform;
        this.renderCopyTabContent();
      });
    });

    const copyBtn = document.getElementById("btn-copy-clipboard");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        const text = document.getElementById("copy-content-box").textContent;
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = "✅ Copied to Clipboard!";
          setTimeout(() => { copyBtn.textContent = "📋 Copy Caption"; }, 2000);
        });
      });
    }
  }

  renderCopyTabContent() {
    const box = document.getElementById("copy-content-box");
    if (!box || !this.activeCopyKit) return;

    let content = "";
    const kit = this.activeCopyKit;

    switch (this.activeCopyTab) {
      case "instagram":
        content = `${kit.instagram?.caption || ""}\n\n${(kit.instagram?.hashtags || []).join(" ")}`;
        break;
      case "twitter_x":
        content = `${kit.twitter_x?.tweet || ""}\n\n${kit.twitter_x?.reply_cta || ""}`;
        break;
      case "onlyfans":
        content = `[TEASER POST]:\n${kit.onlyfans_fansly?.teaser_post || ""}\n\nSuggested PPV Price: ${kit.onlyfans_fansly?.suggested_ppv_price || "$15.00"}\n\n[VIP DM BROADCAST]:\n${kit.onlyfans_fansly?.vip_dm_broadcast || ""}`;
        break;
      case "tiktok":
        content = `${kit.tiktok_reels?.caption || ""}\n\nAudio recommendation: ${kit.tiktok_reels?.trending_sound_suggestion || ""}\n\n${(kit.tiktok_reels?.hashtags || []).join(" ")}`;
        break;
      case "reddit":
        content = `TITLE: ${kit.reddit?.post_title || ""}\n\nFIRST COMMENT:\n${kit.reddit?.first_comment || ""}`;
        break;
      case "fiverr":
        content = kit.fiverr_delivery_note || "Delivery note placeholder.";
        break;
    }

    box.textContent = content.trim();
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.pipelineController = new PipelineController();
});

