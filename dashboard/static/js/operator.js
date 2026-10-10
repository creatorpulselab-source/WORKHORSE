/**
 * WORKHORSE Master AI Operator Interface [operator.js]
 * SYNAPSE [100 Fm] - Autonomous Studio Concierge, Self-Healing System & Health Telemetry
 */

class AIOperatorUI {
  constructor() {
    this.attachedFiles = [];
    this.isGenerating = false;
    this.init();
  }

  async init() {
    this.cacheElements();
    this.bindEvents();
    this.initMobileNavigation();
    this.initSynapse3DMotion();
    this.initHeraldDailyDrop();
    await this.loadModels();
    await this.loadChatHistory();
    this.pollHealthStatus();
    setInterval(() => this.pollHealthStatus(), 20000); // Poll health every 20s
  }

  // Restores prior SYNAPSE conversation turns from the server-persisted history so the
  // Commander's chat survives page reloads, tab switches, or a dropped connection.
  async loadChatHistory() {
    try {
      const res = await fetch('/api/operator/history');
      const data = await res.json();
      const history = data.history || [];
      if (history.length === 0 || !this.chatContainer) return;

      this.chatContainer.innerHTML = '';
      history.forEach(entry => {
        this.appendMessage({
          role: entry.role,
          content: entry.content
        });
      });
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    } catch (err) {
      console.error('Failed to load SYNAPSE chat history:', err);
    }
  }

  cacheElements() {
    this.chatContainer = document.getElementById('operator-messages');
    this.chatInput = document.getElementById('operator-input');
    this.visionAutoPill = document.getElementById('vision-auto-pill');
    this.linkAutoPill = document.getElementById('link-auto-pill');
    this.sendBtn = document.getElementById('operator-send-btn');
    this.modelSelect = document.getElementById('operator-model-select');
    this.webSearchToggle = document.getElementById('operator-web-search');
    this.adultModeToggle = document.getElementById('operator-adult-mode');
    this.fileInput = document.getElementById('operator-file-input');
    this.attachBtn = document.getElementById('operator-attach-btn');
    this.filesPreview = document.getElementById('operator-files-preview');
    this.clearBtn = document.getElementById('operator-clear-btn');
    this.chips = document.querySelectorAll('.operator-prompt-chip');

    // Sidebar quick chat
    this.quickInput = document.getElementById('sidebar-quick-input');
    this.quickSendBtn = document.getElementById('sidebar-quick-send-btn');
    this.quickFeedback = document.getElementById('sidebar-quick-feedback');

    // Health telemetry & self-healing
    this.healthPill = document.getElementById('hud-system-health');
    this.healthStatusText = document.getElementById('health-status-text');
    this.healthModal = document.getElementById('modal-health-diagnostics');
    this.closeHealthModalBtn = document.getElementById('btn-close-health-modal');
    this.btnSelfHealAll = document.getElementById('btn-self-heal-all');
    this.btnPurgeVram = document.getElementById('btn-self-heal-vram');
    this.btnRepairDb = document.getElementById('btn-self-heal-db');

    // Saved conversation log viewer
    this.historyBtn = document.getElementById('operator-history-btn');
    this.historyModal = document.getElementById('modal-operator-history');
    this.closeHistoryModalBtn = document.getElementById('btn-close-history-modal');

    // Generic long-form content pop-out (shoot blueprints, etc.)
    this.contentViewerModal = document.getElementById('modal-content-viewer');
    this.contentViewerTitle = document.getElementById('content-viewer-title');
    this.contentViewerBody = document.getElementById('content-viewer-body');
    this.closeContentViewerBtn = document.getElementById('btn-close-content-viewer-modal');
  }

  bindEvents() {
    // Full view chat
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this.sendMessage());
    }

    if (this.chatInput) {
      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
      this.chatInput.addEventListener('input', () => {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 180) + 'px';
        this.checkAndAutoDetectVision();
        this.checkAndAutoDetectLinks();
      });
    }

    // Global Clipboard Image Paste Handler (Ctrl+V Screenshots / Copied Images)
    document.addEventListener('paste', (e) => {
      const items = (e.clipboardData || window.clipboardData)?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type && items[i].type.startsWith('image/')) {
          const blob = items[i].getAsFile();
          if (blob) {
            const file = new File([blob], `clipboard_image_${Date.now()}.png`, { type: blob.type });
            this.addFiles([file]);
            this.checkAndAutoDetectVision();
            if (this.chatInput) this.chatInput.focus();
            break;
          }
        }
      }
    });

    if (this.attachBtn && this.fileInput) {
      this.attachBtn.addEventListener('click', () => this.fileInput.click());
      this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    if (this.clearBtn) {
      this.clearBtn.addEventListener('click', () => this.clearHistory());
    }

    // Sidebar quick chat
    if (this.quickSendBtn && this.quickInput) {
      this.quickSendBtn.addEventListener('click', () => this.sendQuickMessage());
      this.quickInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.sendQuickMessage();
        }
      });
    }

    // Health modal controls
    if (this.healthPill) {
      this.healthPill.addEventListener('click', () => this.openHealthModal());
    }
    if (this.closeHealthModalBtn && this.healthModal) {
      this.closeHealthModalBtn.addEventListener('click', () => {
        this.healthModal.classList.remove('open');
      });
    }
    if (this.btnSelfHealAll) {
      this.btnSelfHealAll.addEventListener('click', () => this.triggerSelfHeal('all'));
    }
    if (this.btnPurgeVram) {
      this.btnPurgeVram.addEventListener('click', () => this.triggerSelfHeal('vram'));
    }
    if (this.btnRepairDb) {
      this.btnRepairDb.addEventListener('click', () => this.triggerSelfHeal('subscribers'));
    }

    // Saved conversation log modal controls
    if (this.historyBtn) {
      this.historyBtn.addEventListener('click', () => this.openHistoryModal());
    }
    if (this.closeHistoryModalBtn && this.historyModal) {
      this.closeHistoryModalBtn.addEventListener('click', () => {
        this.historyModal.classList.remove('open');
      });
    }
    if (this.closeContentViewerBtn && this.contentViewerModal) {
      this.closeContentViewerBtn.addEventListener('click', () => {
        this.contentViewerModal.classList.remove('open');
      });
    }

    // Dropzone drag/drop
    const dropzone = document.getElementById('operator-dropzone');
    if (dropzone) {
      ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.add('drag-active');
        }, false);
      });
      ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.remove('drag-active');
        }, false);
      });
      dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        this.addFiles(Array.from(files));
      });
    }

    // Chips
    this.chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const prompt = chip.getAttribute('data-prompt');
        if (prompt) {
          this.chatInput.value = prompt;
          this.chatInput.focus();
        }
      });
    });
  }

  async loadModels() {
    try {
      const res = await fetch('/api/operator/models');
      const data = await res.json();
      if (data.status === 'ok' && data.models && data.models.length > 0) {
        if (this.modelSelect) {
          this.modelSelect.innerHTML = '';
          data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.innerText = m;
            if (m.includes('qwen3-abliterated:14b')) {
              opt.selected = true;
            }
            this.modelSelect.appendChild(opt);
          });
        }
      }
    } catch (err) {
      console.warn('[SYNAPSE] Failed to load models:', err);
    }
  }

  handleFileSelect(e) {
    const files = Array.from(e.target.files);
    this.addFiles(files);
    e.target.value = '';
  }

  addFiles(files) {
    files.forEach(f => {
      if (!this.attachedFiles.some(af => af.name === f.name && af.size === f.size)) {
        this.attachedFiles.push(f);
      }
    });
    this.renderFilesPreview();
    this.checkAndAutoDetectVision();
  }

  removeFile(index) {
    this.attachedFiles.splice(index, 1);
    this.renderFilesPreview();
    this.checkAndAutoDetectVision();
  }

  renderFilesPreview() {
    if (!this.filesPreview) return;
    this.filesPreview.innerHTML = '';
    if (this.attachedFiles.length === 0) {
      this.filesPreview.style.display = 'none';
      return;
    }

    this.filesPreview.style.display = 'flex';
    this.attachedFiles.forEach((file, idx) => {
      const chip = document.createElement('div');
      chip.className = 'operator-file-chip';
      const isImg = file.type.startsWith('image/');
      chip.innerHTML = `
        <span class="file-icon">${isImg ? '🖼️' : '📄'}</span>
        <span class="file-name" title="${file.name}">${file.name}</span>
        <span class="file-size">(${Math.round(file.size / 1024)} KB)</span>
        <button type="button" class="file-remove-btn" title="Remove">&times;</button>
      `;

      chip.querySelector('.file-remove-btn').addEventListener('click', () => {
        this.removeFile(idx);
      });

      this.filesPreview.appendChild(chip);
    });
  }

  async sendQuickMessage() {
    const text = this.quickInput.value.trim();
    if (!text || this.isGenerating) return;

    if (this.quickFeedback) {
      this.quickFeedback.innerText = '⚡ SYNAPSE processing command...';
      this.quickFeedback.style.color = '#00f2fe';
    }

    this.quickInput.value = '';

    // Switch to AI Operator full view if desired
    if (window.workhorseBays && typeof window.workhorseBays.switchBay === 'function') {
      window.workhorseBays.switchBay('ai-operator');
    }

    // Route through main chat
    if (this.chatInput) {
      this.chatInput.value = text;
      await this.sendMessage();
      if (this.quickFeedback) {
        this.quickFeedback.innerText = '✓ Command executed.';
        this.quickFeedback.style.color = '#06d6a0';
        setTimeout(() => { this.quickFeedback.innerText = ''; }, 4000);
      }
    }
  }

  sendQuickOption(optionText) {
    if (this.isGenerating) return;
    this.chatInput.value = optionText;
    this.sendMessage();
  }

  async sendMessage() {
    const text = this.chatInput.value.trim();
    if (!text && this.attachedFiles.length === 0) return;
    if (this.isGenerating) return;

    this.isGenerating = true;
    this.sendBtn.disabled = true;

    this.appendMessage({
      role: 'user',
      content: text,
      files: this.attachedFiles.map(f => f.name)
    });

    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';

    const loadingId = this.appendLoadingIndicator();

    const formData = new FormData();
    formData.append('message', text || 'Please inspect attached client files.');
    formData.append('model', this.modelSelect ? this.modelSelect.value : 'huihui_ai/qwen3-abliterated:14b');
    formData.append('web_search', this.webSearchToggle ? this.webSearchToggle.checked : false);
    formData.append('adult_mode', this.adultModeToggle ? this.adultModeToggle.checked : false);

    this.attachedFiles.forEach(file => {
      formData.append('files', file);
    });

    this.attachedFiles = [];
    this.renderFilesPreview();

    if (window.character3dEngine) {
      window.character3dEngine.setAgentState('synapse', 'working');
    }

    try {
      const res = await fetch('/api/operator/chat', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      this.removeLoadingIndicator(loadingId);

      if (data.status === 'ok') {
        this.appendMessage({
          role: 'assistant',
          content: data.reply,
          model: data.model,
          webSources: data.web_sources,
          actions: data.executed_actions,
          quickOptions: data.quick_options,
          visionAutoDetected: data.vision_auto_detected || (data.model && data.model.includes('vl')),
          linkIngested: (data.link_ingestion_results && data.link_ingestion_results.length > 0)
        });
        if (data.web_search_auto_detected && this.webSearchToggle) {
          this.webSearchToggle.checked = true;
        }
        this.checkAndAutoDetectVision();
        this.checkAndAutoDetectLinks();
      } else {
        this.appendMessage({
          role: 'assistant',
          content: `⚠️ **SYNAPSE System Alert**: ${data.reply || 'Could not process request.'}`,
          model: data.model,
          hasError: true
        });
      }
    } catch (err) {
      this.removeLoadingIndicator(loadingId);
      const isFetchFail = err.message && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError'));
      const msg = isFetchFail
        ? `⚠️ **Server Disconnected**: Unable to reach WORKHORSE dashboard server on port 8800 (${err.message}). Please verify the backend server is active.`
        : `⚠️ **Connection Error**: ${err.message}.`;
      this.appendMessage({
        role: 'assistant',
        content: msg,
        hasError: true
      });
    } finally {
      this.isGenerating = false;
      this.sendBtn.disabled = false;
      if (window.character3dEngine) {
        setTimeout(() => {
          window.character3dEngine.setAgentState('synapse', 'idle');
          window.character3dEngine.setAgentState('iris', 'idle');
          window.character3dEngine.setAgentState('cipher', 'idle');
          window.character3dEngine.setAgentState('herald', 'idle');
        }, 1800);
      }
      this.chatInput.focus();
    }
  }

  appendMessage(msg, targetContainer = this.chatContainer) {
    const isUser = msg.role === 'user';
    const msgDiv = document.createElement('div');
    msgDiv.className = `operator-msg-row ${isUser ? 'user-msg' : 'assistant-msg'}`;

    let headerHtml = '';
    if (!isUser) {
      headerHtml = `
        <div class="msg-header">
          <div class="msg-avatar" style="overflow: hidden; padding: 0;">
            <img src="/static/img/characters_3d/synapse_card.png" style="width: 100%; height: 100%; object-fit: cover;">
          </div>
          <span class="msg-author">SYNAPSE [100 Fm]</span>
          <span class="msg-meta-pill">${msg.model || 'Dual RTX 3060'}</span>
          ${msg.visionAutoDetected ? '<span class="msg-vision-tag"><span class="pulse-dot" style="background:#f72585;box-shadow:0 0 6px #f72585;"></span> 👁️ VISION AUTO-ENGAGED</span>' : ''}
          ${msg.linkIngested ? '<span class="msg-vision-tag" style="background:rgba(0,242,254,0.15);border-color:rgba(0,242,254,0.5);color:#00f2fe;"><span class="pulse-dot" style="background:#00f2fe;box-shadow:0 0 6px #00f2fe;"></span> 🔗 LINK INGESTED & VAULT UPDATED</span>' : ''}
        </div>
      `;
    } else {
      headerHtml = `
        <div class="msg-header">
          <span class="msg-author">COMMANDER</span>
          <div class="msg-avatar user-av">👤</div>
        </div>
      `;
    }

    let bodyHtml = `<div class="msg-body">${this.formatMarkdown(msg.content)}</div>`;

    if (msg.files && msg.files.length > 0) {
      bodyHtml += `<div class="msg-attached-list">📎 <strong>Attached:</strong> ${msg.files.join(', ')}</div>`;
    }

    if (msg.webSources && msg.webSources.length > 0) {
      bodyHtml += `
        <div class="msg-web-sources">
          <div class="web-sources-title">🌐 Live Web Sources Cited:</div>
          <div class="web-sources-grid">
            ${msg.webSources.map((s, idx) => `
              <a href="${s.url}" target="_blank" class="web-source-card" title="${s.snippet}">
                <span class="source-num">[${idx + 1}]</span>
                <span class="source-title">${s.title}</span>
              </a>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (msg.actions && msg.actions.length > 0) {
      // Raw tool-call status badges are intentionally not rendered here - the Commander only
      // wants to see SYNAPSE's actual written response. Blueprints and generated images (real
      // content, not tool-execution noise) are still surfaced, with blueprints opening in a
      // full-size pop-out modal instead of a cramped inline <details> dropdown.
      const blueprintActions = msg.actions.filter(act => act.blueprint);
      const imageActions = msg.actions.filter(act => act.images && act.images.length > 0);
      const mediaActions = msg.actions.filter(act => act.media && act.media.length > 0);

      if (blueprintActions.length > 0 || imageActions.length > 0 || mediaActions.length > 0) {
        bodyHtml += `<div class="msg-actions-list">`;

        blueprintActions.forEach(act => {
          const blueprintId = 'bp-' + Date.now() + '-' + Math.floor(Math.random() * 100000);
          this._blueprintStore = this._blueprintStore || {};
          this._blueprintStore[blueprintId] = act.blueprint;
          bodyHtml += `
            <button type="button" class="btn-view-blueprint" data-blueprint-id="${blueprintId}">
              📋 View Full Shoot Blueprint
            </button>
          `;
        });

        imageActions.forEach(act => {
          bodyHtml += `
            <div class="msg-generated-images-grid">
              ${act.images.map(img => img.image_url ? `
                <a href="${img.image_url}" target="_blank" class="msg-generated-image-card" title="${img.title || ''}">
                  <img src="${img.image_url}" alt="${img.title || 'Generated concept'}" loading="lazy">
                  <span class="msg-generated-image-caption">${img.title || ''}</span>
                </a>
              ` : `
                <div class="msg-generated-image-card msg-generated-image-failed" title="${img.error || 'Render failed'}">
                  <span class="act-icon">⚠️</span>
                  <span class="msg-generated-image-caption">${img.title || 'Concept'} failed</span>
                </div>
              `).join('')}
            </div>
          `;
        });

        // Unified rendering for every finished-work item (images, videos, 3D models,
        // zip archives) any tool attached via result['media'] - so anything Synapse is
        // asked to make shows up directly in the chat to view/download, instead of only
        // a text filename the Commander has to go hunting for on disk.
        mediaActions.forEach(act => {
          bodyHtml += `
            <div class="msg-generated-media-grid">
              ${act.media.map(m => this.renderMediaCard(m)).join('')}
            </div>
          `;
        });

        bodyHtml += `</div>`;
      }
    }

    if (msg.quickOptions && msg.quickOptions.length > 0) {
      const msgId = 'qopt-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
      bodyHtml += `
        <div class="operator-chips-bar" id="${msgId}" style="margin-top: 8px;">
          ${msg.quickOptions.map(opt => `<span class="operator-prompt-chip">${opt}</span>`).join('')}
        </div>
      `;
      setTimeout(() => {
        const bar = document.getElementById(msgId);
        if (bar) {
          bar.querySelectorAll('.operator-prompt-chip').forEach(chip => {
            chip.addEventListener('click', () => this.sendQuickOption(chip.innerText));
          });
        }
      }, 0);
    }

    if (msg.hasError) {
      bodyHtml += `
        <div style="margin-top: 10px;">
          <button type="button" class="btn-dock-action" onclick="window.aiOperatorUI.triggerSelfHeal('all')">
            🛠️ Ask SYNAPSE to Auto-Fix & Purge VRAM
          </button>
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="msg-bubble">
        ${headerHtml}
        ${bodyHtml}
      </div>
    `;

    targetContainer.appendChild(msgDiv);
    msgDiv.querySelectorAll('.btn-view-blueprint').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.blueprintId;
        this.openContentViewerModal('📋 Shoot Production Blueprint', this._blueprintStore[id]);
      });
    });
    if (targetContainer === this.chatContainer) {
      this.scrollToBottom();
    }
  }

  // Uses the same View/Download controls as Completed Work, including old history entries.
  renderMediaCard(m) {
    const viewer = window.outputViewer;
    const media = viewer.normalize(m);
    const esc = value => viewer.escape(value);
    const caption = `${m.category_label ? esc(m.category_label) + ' &middot; ' : ''}${esc(m.title || m.filename || '')}`;
    if (m.type === 'image') {
      return `
        <div class="msg-generated-image-card" title="${esc(m.title || '')}">
          <button type="button" class="output-image-button" data-workhorse-view="${esc(JSON.stringify(media))}" aria-label="View ${esc(media.filename)}">
            <img src="${esc(media.preview_url)}" alt="${esc(m.title || 'Generated image')}" loading="lazy">
          </button>
          <span class="msg-generated-image-caption">${caption}</span>
          ${viewer.actions(m)}
        </div>
      `;
    }
    if (m.type === 'video') {
      return `
        <div class="msg-generated-media-card msg-generated-video-card">
          <video src="${esc(media.preview_url)}" controls preload="metadata" playsinline></video>
          <span class="msg-generated-image-caption">${caption}</span>
          ${viewer.actions(m)}
        </div>
      `;
    }
    const icon = m.type === 'model_3d' ? '🧊' : '📦';
    return `
      <div class="msg-generated-media-card msg-generated-download-card" title="${esc(m.title || '')}">
        <span class="act-icon">${icon}</span>
        <span class="msg-generated-image-caption">${caption}</span>
        ${viewer.actions(m)}
      </div>
    `;
  }

  // Generic pop-out for long-form content (currently shoot blueprints) that's too large/
  // unwieldy to read in a small inline chat bubble.
  openContentViewerModal(title, markdownContent) {
    if (!this.contentViewerModal) return;
    if (this.contentViewerTitle) this.contentViewerTitle.innerText = title;
    if (this.contentViewerBody) this.contentViewerBody.innerHTML = this.formatMarkdown(markdownContent || '');
    this.contentViewerModal.classList.add('open');
  }

  appendLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const loadDiv = document.createElement('div');
    loadDiv.id = id;
    loadDiv.className = 'operator-msg-row assistant-msg loading-msg';
    loadDiv.innerHTML = `
      <div class="msg-bubble">
        <div class="msg-header">
          <div class="msg-avatar" style="overflow: hidden; padding: 0;">
            <img src="/static/img/characters_3d/synapse_card.png" style="width: 100%; height: 100%; object-fit: cover;">
          </div>
          <span class="msg-author">SYNAPSE [100 Fm]</span>
          <span class="msg-meta-pill live">Dual RTX 3060 Neural Core Active...</span>
        </div>
        <div class="msg-body">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <span class="thinking-text">SYNAPSE orchestrating tools & analyzing instructions...</span>
        </div>
      </div>
    `;
    this.chatContainer.appendChild(loadDiv);
    this.scrollToBottom();
    return id;
  }

  removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  scrollToBottom() {
    if (this.chatContainer) {
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
  }

  formatMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    html = html.replace(/`([a-zA-Z0-9]*)\r?\n([\s\S]*?)`/g, (match, lang, code) => {

      return `<pre class="code-block"><code class="lang-${lang}">${code.trim()}</code></pre>`;
    });

    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>');
    html = html.replace(/^\- (.*$)/gim, '<li class="md-li">$1</li>');
    html = html.replace(/(<li class="md-li">.*<\/li>)/g, '<ul class="md-ul">$1</ul>');
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="md-link">$1 &rarr;</a>');
    html = html.replace(/\r?\n\r?\n/g, '<br><br>');
    html = html.replace(/\r?\n/g, '<br>');

    return html;
  }

  async clearHistory() {
    if (confirm('Clear current SYNAPSE conversation memory?')) {
      try {
        await fetch('/api/operator/clear', { method: 'POST' });
        this.chatContainer.innerHTML = '';
        this.appendMessage({
          role: 'assistant',
          content: '⚡ **SYNAPSE Online**: Neural memory refreshed. How may I assist with client fulfillment, retouching, or system operations today, Commander?'
        });
      } catch (err) {
        console.error('Failed to clear history:', err);
      }
    }
  }

  // Health Polling & Self-Healing
  async pollHealthStatus() {
    try {
      const res = await fetch('/api/system/health-check');
      const data = await res.json();
      if (this.healthPill && this.healthStatusText) {
        if (data.overall_status === 'healthy') {
          this.healthPill.className = 'hud-health-pill';
          this.healthStatusText.innerText = 'HEALTH: OPTIMAL';
          this.healthPill.querySelector('.hud-dot').style.background = '#06d6a0';
        } else if (data.overall_status === 'warning') {
          this.healthPill.className = 'hud-health-pill warning';
          this.healthStatusText.innerText = `WARNING (${data.issues.length})`;
          this.healthPill.querySelector('.hud-dot').style.background = '#ffd166';
        } else {
          this.healthPill.className = 'hud-health-pill error';
          this.healthStatusText.innerText = `ALERT: ${data.issues[0] || 'SYSTEM ISSUE'}`;
          this.healthPill.querySelector('.hud-dot').style.background = '#ef4444';
        }
      }
    } catch (e) {
      if (this.healthPill && this.healthStatusText) {
        this.healthPill.className = 'hud-health-pill error';
        this.healthStatusText.innerText = 'SERVER OFFLINE';
      }
    }
  }

  // Shows the full persisted conversation for this session in a read-only modal,
  // independent of the live scrollable chat feed above.
  async openHistoryModal() {
    if (!this.historyModal) return;
    this.historyModal.classList.add('open');
    const container = document.getElementById('operator-history-log-container');
    if (!container) return;

    container.innerHTML = '<div style="color:#94a3b8;font-size:12px;">Loading saved conversation...</div>';

    try {
      const res = await fetch('/api/operator/history');
      const data = await res.json();
      const history = data.history || [];

      if (history.length === 0) {
        container.innerHTML = '<div style="color:#94a3b8;font-size:12px;">No saved messages yet for this session.</div>';
        return;
      }

      container.innerHTML = '';
      history.forEach(entry => {
        this.appendMessage({ role: entry.role, content: entry.content }, container);
      });
    } catch (err) {
      container.innerHTML = `<div style="color:#ef4444;font-size:12px;">Failed to load saved conversation: ${err.message}</div>`;
    }
  }

  async openHealthModal() {
    if (!this.healthModal) return;
    this.healthModal.classList.add('open');
    const container = document.getElementById('health-checks-container');
    if (!container) return;

    container.innerHTML = '<div style="color:#94a3b8;font-size:12px;">Running deep diagnostics across Dual RTX 3060, Ollama, and storage...</div>';

    try {
      const res = await fetch('/api/system/health-check');
      const data = await res.json();
      const comp = data.components || {};

      container.innerHTML = `
        <div class="health-check-row">
          <span class="health-row-name">🤖 Local Ollama Server (${comp.ollama?.url || '11434'})</span>
          <span class="health-row-badge" style="background:${comp.ollama?.status === 'online' ? 'rgba(6,214,160,0.2);color:#06d6a0;' : 'rgba(239,68,68,0.2);color:#ef4444;'}">
            ${(comp.ollama?.status || 'UNKNOWN').toUpperCase()} (${comp.ollama?.models_count || 0} Models)
          </span>
        </div>
        <div class="health-check-row">
          <span class="health-row-name">💾 F: Storage Drive Space</span>
          <span class="health-row-badge" style="background:${comp.storage_f?.status === 'ok' ? 'rgba(6,214,160,0.2);color:#06d6a0;' : 'rgba(255,209,102,0.2);color:#ffd166;'}">
            ${comp.storage_f?.free_gb || 0} GB FREE / ${comp.storage_f?.total_gb || 0} GB
          </span>
        </div>
        <div class="health-check-row">
          <span class="health-row-name">🌿 Newsletter Subscriber Database</span>
          <span class="health-row-badge" style="background:${comp.subscribers_db?.status === 'ok' ? 'rgba(6,214,160,0.2);color:#06d6a0;' : 'rgba(239,68,68,0.2);color:#ef4444;'}">
            ${(comp.subscribers_db?.status || 'UNKNOWN').toUpperCase()} (${comp.subscribers_db?.subscribers_count || 0} Active)
          </span>
        </div>
        <div class="health-check-row">
          <span class="health-row-name">⚡ Dual RTX 3060 Sharding (24GB)</span>
          <span class="health-row-badge" style="background:rgba(0,242,254,0.15);color:#00f2fe;">
            GPU 0: SYNAPSE & IRIS | GPU 1: ECHO & FORGE (100% ISOLATED)
          </span>
        </div>
        <div class="health-check-row">
          <span class="health-row-name">🔄 VRAM Dynamic Block Swapper</span>
          <span class="health-row-badge" style="background:rgba(6,214,160,0.2);color:#06d6a0;">
            ACTIVE (Auto-Eviction on GPU 0 • Zero OOM Risk)
          </span>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `<div style="color:#ef4444;font-size:12px;">Diagnostics failed: ${err.message}</div>`;
    }

    await this.loadDailyHealthLog();
    await this.loadErrorLog();
  }

  async loadDailyHealthLog() {
    const container = document.getElementById('daily-health-log-container');
    if (!container) return;
    try {
      const res = await fetch('/api/system/daily-health-log?limit=14');
      const data = await res.json();
      const checks = data.daily_checks || [];
      if (checks.length === 0) {
        container.innerHTML = '<div style="color:#94a3b8;">No daily health snapshots recorded yet.</div>';
        return;
      }
      container.innerHTML = checks.map(c => {
        const badgeColor = c.overall_status === 'healthy' ? 'rgba(6,214,160,0.2);color:#06d6a0;'
          : c.overall_status === 'warning' ? 'rgba(255,209,102,0.2);color:#ffd166;'
          : 'rgba(239,68,68,0.2);color:#ef4444;';
        const issuesText = (c.issues && c.issues.length > 0) ? c.issues.join('; ') : 'No issues detected';
        return `
          <div class="health-check-row">
            <span class="health-row-name">${c.date}</span>
            <span class="health-row-badge" style="background:${badgeColor}" title="${issuesText}">${(c.overall_status || 'unknown').toUpperCase()}</span>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `<div style="color:#ef4444;">Failed to load daily health log: ${err.message}</div>`;
    }
  }

  async loadErrorLog() {
    const container = document.getElementById('error-log-container');
    if (!container) return;
    try {
      const res = await fetch('/api/system/error-log?limit=15');
      const data = await res.json();
      const errors = data.errors || [];
      if (errors.length === 0) {
        container.innerHTML = '<div style="color:#94a3b8;">No errors logged - system has been running clean.</div>';
        return;
      }
      container.innerHTML = errors.map(e => `
        <div class="health-check-row" style="align-items: flex-start;">
          <span class="health-row-name" style="flex: 1;">
            <strong>${e.component}</strong><br>
            <span style="color:#94a3b8; font-weight: 400;">${e.error}</span>
          </span>
          <span class="health-row-badge" style="background:rgba(239,68,68,0.2);color:#ef4444; white-space: nowrap;">${new Date(e.timestamp).toLocaleString()}</span>
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<div style="color:#ef4444;">Failed to load error log: ${err.message}</div>`;
    }
  }

  async triggerSelfHeal(action) {
    const feedbackEl = document.getElementById('self-heal-feedback');
    if (feedbackEl) {
      feedbackEl.innerHTML = '<span style="color:#00f2fe;">⚡ SYNAPSE executing self-healing sequence...</span>';
    }

    try {
      const res = await fetch('/api/system/self-heal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
      });
      const data = await res.json();
      if (feedbackEl) {
        feedbackEl.innerHTML = '<span style="color:#06d6a0;">✓ Self-healing sequence complete. All GPU caches cleared and systems verified.</span>';
      }
      await this.pollHealthStatus();
      setTimeout(() => this.openHealthModal(), 800);
    } catch (err) {
      if (feedbackEl) {
        feedbackEl.innerHTML = `<span style="color:#ef4444;">Self-heal failed: ${err.message}</span>`;
      }
    }
  }

  initMobileNavigation() {
    const switcher = document.getElementById('mobile-pane-switcher');
    const grid = document.querySelector('.studio-main-grid');
    if (!switcher || !grid) return;

    const tabs = switcher.querySelectorAll('.mobile-pane-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const pane = tab.getAttribute('data-pane');
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        grid.classList.remove('mobile-show-sidebar', 'mobile-show-viewport', 'mobile-show-fulfillment');
        if (pane === 'sidebar') {
          grid.classList.add('mobile-show-sidebar');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (pane === 'fulfillment') {
          grid.classList.add('mobile-show-fulfillment');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
          grid.classList.add('mobile-show-viewport');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
    });

    // When clicking any bay navigation button on mobile, auto-switch to active bay viewport
    document.querySelectorAll('.bay-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (window.innerWidth <= 1024) {
          const viewportTab = document.getElementById('mob-tab-viewport');
          if (viewportTab) {
            viewportTab.click();
          }
        }
      });
    });
  }

  initSynapse3DMotion() {
    const stage = document.getElementById('synapse-stage');
    const card = document.getElementById('synapse-card');
    const art = document.getElementById('synapse-art');
    const glare = document.getElementById('synapse-glare');
    if (!stage || !card) return;

    let isHovered = false;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let animId = null;

    const updateTiltFromCoords = (clientX, clientY) => {
      const rect = stage.getBoundingClientRect();
      const x = (clientX - rect.left) / rect.width - 0.5; // -0.5 to 0.5
      const y = (clientY - rect.top) / rect.height - 0.5; // -0.5 to 0.5
      targetX = Math.max(-0.5, Math.min(0.5, x));
      targetY = Math.max(-0.5, Math.min(0.5, y));

      if (glare) {
        const px = Math.round((targetX + 0.5) * 100);
        const py = Math.round((targetY + 0.5) * 100);
        glare.style.background = `radial-gradient(circle at ${px}% ${py}%, rgba(0, 242, 254, 0.95), rgba(168, 85, 247, 0.45) 45%, transparent 75%)`;
      }
    };

    stage.addEventListener('mouseenter', () => {
      isHovered = true;
      card.style.animation = 'none';
      if (glare) glare.style.opacity = '0.45';
      if (!animId) loop();
    });

    stage.addEventListener('mousemove', (e) => {
      updateTiltFromCoords(e.clientX, e.clientY);
    });

    // Mobile touch interaction
    stage.addEventListener('touchmove', (e) => {
      if (e.touches && e.touches.length > 0) {
        isHovered = true;
        card.style.animation = 'none';
        if (glare) glare.style.opacity = '0.45';
        updateTiltFromCoords(e.touches[0].clientX, e.touches[0].clientY);
        if (!animId) loop();
      }
    }, { passive: true });

    stage.addEventListener('mouseleave', () => {
      isHovered = false;
      targetX = 0;
      targetY = 0;
      if (glare) {
        glare.style.opacity = '0.25';
        glare.style.background = 'radial-gradient(circle at 50% 50%, rgba(0, 242, 254, 0.8), rgba(168, 85, 247, 0.3) 40%, transparent 75%)';
      }
    });

    stage.addEventListener('touchend', () => {
      isHovered = false;
      targetX = 0;
      targetY = 0;
    });

    const loop = () => {
      currentX += (targetX - currentX) * 0.15;
      currentY += (targetY - currentY) * 0.15;

      const rotX = (-currentY * 22).toFixed(2);
      const rotY = (currentX * 26).toFixed(2);
      const shiftX = (currentX * 14).toFixed(1);
      const shiftY = (currentY * 12).toFixed(1);

      if (isHovered || Math.abs(currentX) > 0.005 || Math.abs(currentY) > 0.005) {
        card.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale3d(1.025, 1.025, 1.025)`;
        if (art) {
          art.style.transform = `scale(1.06) translate3d(${shiftX}px, ${shiftY}px, 15px)`;
        }
        animId = requestAnimationFrame(loop);
      } else {
        card.style.transform = '';
        if (art) art.style.transform = '';
        card.style.animation = 'synapseFloatKinematics 5.5s ease-in-out infinite alternate';
        animId = null;
      }
    };
  }

  initHeraldDailyDrop() {
    const btn = document.getElementById('btn-dispatch-daily-drop');
    const badge = document.getElementById('herald-daily-count');
    if (!btn) return;

    const checkHerald = async () => {
      try {
        const res = await fetch('/api/herald/schedule-status');
        const data = await res.json();
        if (data.status === 'ok' && badge) {
          const slots = data.schedule.slots || [];
          const executed = slots.filter(s => s.executed).length;
          badge.innerText = `${executed}/${slots.length} Slots`;
        }
      } catch (e) {}
    };

    checkHerald();
    setInterval(checkHerald, 30000);

    btn.addEventListener('click', async () => {
      const origText = btn.innerHTML;
      btn.innerHTML = '⚡ Dispatched! Sending...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/herald/dispatch-daily', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
          btn.innerHTML = '✓ Daily Drop Sent!';
          if (badge) badge.innerText = 'Active Today';
          alert("📰 Herald Daily Drop Triggered!\n\n✓ Today's 4 Newsletters Dispatched\n✓ Scheduled Multi-Tweet Threads Posted to @TheCreatorAsset & @creatorpulselab");
        } else {
          btn.innerHTML = '⚠ Dispatch Failed';
        }
      } catch (err) {
        btn.innerHTML = `⚠ Error: ${err.message}`;
      } finally {
        setTimeout(() => {
          btn.innerHTML = origText;
          btn.disabled = false;
          checkHerald();
        }, 4000);
      }
    });
  }

  checkAndAutoDetectLinks() {
    const text = (this.chatInput ? this.chatInput.value : '');
    const urlRegex = /https?:\/\/[^\s<>"]+/i;
    const match = text.match(urlRegex);
    const isImage = match && /\.(jpe?g|png|webp|bmp|gif)$/i.test(match[0]);
    const isLink = match && !isImage;

    if (this.linkAutoPill) {
      this.linkAutoPill.style.display = isLink ? 'inline-flex' : 'none';
    }
    return isLink;
  }

  checkAndAutoDetectVision() {
    const hasAttachedImage = this.attachedFiles.some(f => 
      (f.type && f.type.startsWith('image/')) || 
      /\.(jpe?g|png|webp|bmp|gif)$/i.test(f.name)
    );

    const text = (this.chatInput ? this.chatInput.value : '').toLowerCase();
    const hasImageMention = /\.(jpe?g|png|webp|bmp|gif)/i.test(text);
    const visionKeywords = [
      'look at this', 'look at the', 'inspect this', 'inspect the',
      'analyze this', 'analyze the photo', 'analyze the image',
      'examine this', 'what is in this', "what's in this", 'what do you see',
      'in this image', 'in this picture', 'in this photo', 'in the screenshot',
      'read the text', 'ocr', 'transcribe image', 'critique this', 'lighting analysis',
      'pose review', 'vision model', 'qwen-vl', 'iris check', 'iris inspect',
      'visual check', 'evaluate photo', 'check this image', 'check this photo',
      'change to vision', 'switch to vision', 'use vision'
    ];
    const hasVisionKeyword = visionKeywords.some(kw => text.includes(kw));

    const isVision = hasAttachedImage || hasImageMention || hasVisionKeyword;

    if (isVision) {
      if (this.visionAutoPill) this.visionAutoPill.style.display = 'inline-flex';
      if (this.modelSelect) {
        const vlOption = Array.from(this.modelSelect.options).find(opt => opt.value.includes('-vl-') || opt.value.includes('vl'));
        if (vlOption && this.modelSelect.value !== vlOption.value) {
          this.modelSelect.value = vlOption.value;
        }
        this.modelSelect.style.borderColor = '#f72585';
        this.modelSelect.style.boxShadow = '0 0 10px rgba(247, 37, 133, 0.4)';
      }
    } else {
      if (this.visionAutoPill) this.visionAutoPill.style.display = 'none';
      if (this.modelSelect) {
        this.modelSelect.style.borderColor = '';
        this.modelSelect.style.boxShadow = '';
      }
    }
    return isVision;
  }

}

window.addEventListener('DOMContentLoaded', () => {
  window.aiOperatorUI = new AIOperatorUI();
});