// ============================================================================
// WORKHORSE — WORK BAYS CONTROLLER
// 1. Bay Navigation Switcher
// 2. Photo Shoot & Glamour Retouching Bay
// 3. Shoot Ideas & Style Reverse-Engineering Lab
// 4. Live Cam & Creator Store (Dedicated Tip Menu Maker + Full Bio Kits)
// ============================================================================

class WorkBaysManager {
  constructor() {
    const initHash = window.location.hash.replace('#', '');
this.currentBay = initHash || 'command-center';
    this.stagedPhotos = [];
    this.retouchedPhotos = [];
    this.viewMode = 'master'; // 'master' or 'teaser'

    // Tip Menu Maker State
    this.camSubMode = 'tip-menu'; // 'tip-menu' or 'full-bio'
    this.tipViewTab = 'preview'; // 'preview', 'code', 'bot'
    this.tipItems = [];
    this.currentTipResult = null;
    this.currentBioResult = null;

    this.initNavigation();
    this.switchBay(this.currentBay);
    this.initCommandIslands();
    this.initPhotoBay();
    this.initInspirationLab();
    this.initTipMenuMaker();
    this.initFiverrBot();
    this.initOrderRadar();
    this.initMarketingHub();
    this.initNewsletterHub();
  }

  // --------------------------------------------------------------------------
  // 0. MASTER COMMAND ISLANDS
  // --------------------------------------------------------------------------
  initCommandIslands() {
    const islands = document.querySelectorAll('.cyber-island, .cyber-circle-orb, .chemical-atom-node');
    islands.forEach(island => {
      island.addEventListener('click', (e) => {
        const targetBay = island.getAttribute('data-target-bay');
        if (targetBay) {
          this.playChimeSound();
          this.switchBay(targetBay);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
    });

    const brandLogo = document.getElementById('brand-logo-home');
    if (brandLogo) {
      brandLogo.addEventListener('click', () => {
        this.switchBay('command-center');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  // --------------------------------------------------------------------------
  // 1. BAY NAVIGATION SWITCHER
  // --------------------------------------------------------------------------
  initNavigation() {
    const hash = window.location.hash.replace('#', '');
    if (hash) {
      setTimeout(() => this.switchBay(hash), 100);
    }
    const tabs = document.querySelectorAll('.bay-tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const bay = tab.getAttribute('data-bay');
        this.switchBay(bay);
      });
    });
  }

  switchBay(bayId) {
    this.currentBay = bayId;
    document.querySelectorAll('.bay-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-bay') === bayId);
    });

    document.querySelectorAll('.bay-view-panel').forEach(panel => {
      panel.classList.remove('active');
    });

    const targetPanel = document.getElementById(`view-${bayId}`);
    if (targetPanel) {
      targetPanel.classList.add('active');
    }

    if (bayId === 'photo-bay') {
      this.refreshInputPhotos();
    } else if (bayId === 'inspiration-lab') {
      this.refreshInspirationVault();
    } else if (bayId === 'etsy-empire') {
      if (!document.getElementById('etsy-metadata-pre')?.innerText.includes('LISTING TITLE')) {
        this.bundleEtsy('all');
      }
    } else if (bayId === 'fiverr-bot') {
      if (!this.fiverrGigs) {
        this.initFiverrBot();
    }
    } else if (bayId === 'cam-templates') {
      if (!this.currentTipResult) {
        this.loadTipPreset('lovense');
      }
    } else if (bayId === 'marketing-hub') {
      this.initMarketingHub();
    } else if (bayId === 'newsletter-hub') {
      this.initNewsletterHub();
    } else if (bayId === 'completed-work') {
      this.refreshCompletedWork();
    }
  }

  // --------------------------------------------------------------------------
  // 2. PHOTO SHOOT & RETOUCHING BAY
  // --------------------------------------------------------------------------
  initPhotoBay() {
    const dropZone = document.getElementById('photo-drop-zone');
    const fileInput = document.getElementById('photo-file-input');
    const slider = document.getElementById('photo-smooth-slider');
    const sliderVal = document.getElementById('photo-smooth-val');
    const btnRetouch = document.getElementById('btn-start-retouch');
    const btnOpenFolder = document.getElementById('btn-open-photos-folder');
    const toggleMaster = document.getElementById('toggle-view-master');
    const toggleTeaser = document.getElementById('toggle-view-teaser');

    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());
      dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
      dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.uploadPhotos(e.dataTransfer.files);
        }
      });
      fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
          this.uploadPhotos(fileInput.files);
        }
      });
    }

    if (slider && sliderVal) {
      slider.addEventListener('input', () => {
        sliderVal.innerText = slider.value;
      });
    }

    if (btnRetouch) {
      btnRetouch.addEventListener('click', () => this.runPhotoRetouch());
    }

    if (btnOpenFolder) {
      btnOpenFolder.addEventListener('click', () => {
        fetch('/api/open-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: 'F:/WORKHORSE/workspace/photos_output' })
        });
      });
    }

    if (toggleMaster && toggleTeaser) {
      toggleMaster.addEventListener('click', () => {
        this.viewMode = 'master';
        toggleMaster.classList.add('active');
        toggleTeaser.classList.remove('active');
        this.renderPhotoGallery();
      });
      toggleTeaser.addEventListener('click', () => {
        this.viewMode = 'teaser';
        toggleTeaser.classList.add('active');
        toggleMaster.classList.remove('active');
        this.renderPhotoGallery();
      });
    }
  }

  async uploadPhotos(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    const statusText = document.getElementById('photo-upload-status');
    if (statusText) statusText.innerText = `Uploading ${files.length} photos to local GPU vault...`;

    try {
      const res = await fetch('/api/photos/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (statusText) {
        statusText.innerText = `✓ Staged ${data.count} photos ready for retouching.`;
      }
      this.refreshInputPhotos();
    } catch (err) {
      if (statusText) statusText.innerText = `Upload failed: ${err.message}`;
    }
  }

  async refreshInputPhotos() {
    try {
      const res = await fetch('/api/photos/list-input');
      const data = await res.json();
      const countBadge = document.getElementById('photo-staged-count');
      if (countBadge) {
        countBadge.innerText = `${data.count} photos staged`;
      }
    } catch (e) {}
  }

  async runPhotoRetouch() {
    const shootName = document.getElementById('photo-shoot-name')?.value.trim() || 'glamour_shoot';
    const preset = document.getElementById('photo-preset-select')?.value || 'moody_boudoir';
    const smoothStrength = document.getElementById('photo-smooth-slider')?.value || '0.5';
    const watermark = document.getElementById('photo-watermark-text')?.value.trim() || '@ExclusiveDrop';
    const btnRetouch = document.getElementById('btn-start-retouch');
    const statusText = document.getElementById('photo-retouch-status');

    if (btnRetouch) btnRetouch.disabled = true;
    if (statusText) statusText.innerText = '⚡ Processing batch on Dual RTX 3060 (Skin softening + color grading + crops)...';

    try {
      const res = await fetch('/api/photos/retouch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shoot_name: shootName,
          preset: preset,
          smooth_strength: smoothStrength,
          watermark_text: watermark
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Retouching failed');
      }

      const data = await res.json();
      this.retouchedPhotos = data.photos || [];
      if (statusText) statusText.innerText = `✓ Finished ${data.total_processed} photos. ZIP package ready (${data.zip_size_mb} MB).`;

      const zipBtn = document.getElementById('btn-download-photos-zip');
      if (zipBtn) {
        zipBtn.style.display = 'inline-flex';
        zipBtn.onclick = () => {
          window.location.href = `/api/download/photos-zip/${shootName}`;
        };
      }

      this.renderPhotoGallery();
    } catch (err) {
      if (statusText) statusText.innerText = `Error: ${err.message}`;
    } finally {
      if (btnRetouch) btnRetouch.disabled = false;
    }
  }

  renderPhotoGallery() {
    const grid = document.getElementById('photo-gallery-grid');
    if (!grid) return;

    if (!this.retouchedPhotos.length) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 40px;">No retouched photos generated yet. Drop photos above and click Launch Retouching.</div>';
      return;
    }

    grid.innerHTML = this.retouchedPhotos.map((p) => {
      const imgSrc = this.viewMode === 'master' ? `/api/media/${p.master}` : `/api/media/${p.teaser}`;
      const badge = this.viewMode === 'master' ? 'MASTER 4K' : 'WATERMARKED TEASER (4:5)';
      const badgeColor = this.viewMode === 'master' ? 'var(--cyan-glow)' : 'var(--amber-warm)';

      return `
        <div class="photo-card">
          <div class="photo-thumb-wrap">
            <img src="${imgSrc}" alt="${p.original}" loading="lazy" />
          </div>
          <div class="photo-card-info">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 700; color: #fff; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 110px;">${p.original}</span>
              <span style="font-size: 9px; font-family: var(--font-mono); color: ${badgeColor}; border: 1px solid ${badgeColor}; padding: 1px 4px; border-radius: 3px;">${badge}</span>
            </div>
            <div style="display: flex; gap: 6px; margin-top: 6px;">
              <a href="/api/media/${p.master}" target="_blank" class="btn-cyber" style="padding: 2px 6px; font-size: 10px; flex: 1; justify-content: center; text-decoration: none;">Fullres</a>
              <a href="/api/media/${p.crop_9x16}" target="_blank" class="btn-cyber" style="padding: 2px 6px; font-size: 10px; flex: 1; justify-content: center; text-decoration: none;">9:16 Story</a>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // --------------------------------------------------------------------------
  // 3. SHOOT IDEAS & INSPIRATION LAB
  // --------------------------------------------------------------------------
  initInspirationLab() {
    this.selectedInspImage = null;
    this.latestComfyData = null;
    this.inspActiveTab = 'comfyui';

    const dropZone = document.getElementById('insp-drop-zone');
    const fileInput = document.getElementById('insp-file-input');
    const btnScanComfy = document.getElementById('btn-scan-comfyui');
    const btnScanBlueprint = document.getElementById('btn-scan-inspiration');
    const btnOpenFolder = document.getElementById('btn-open-insp-folder');
    const btnClearSelect = document.getElementById('btn-clear-insp-select');

    // Tab buttons
    const tabComfy = document.getElementById('tab-view-comfyui');
    const tabBlueprint = document.getElementById('tab-view-blueprint');
    const containerComfy = document.getElementById('comfyui-prompts-container');
    const containerBlueprint = document.getElementById('blueprint-container');

    // Quick copy buttons in top bar
    const btnCopyImg = document.getElementById('btn-copy-comfyui-image');
    const btnCopyVid = document.getElementById('btn-copy-comfyui-video');
    const btnCopyBlueprint = document.getElementById('btn-copy-blueprint');

    if (tabComfy && tabBlueprint) {
      tabComfy.addEventListener('click', () => {
        this.inspActiveTab = 'comfyui';
        tabComfy.classList.add('active');
        tabBlueprint.classList.remove('active');
        if (containerComfy) containerComfy.style.display = 'flex';
        if (containerBlueprint) containerBlueprint.style.display = 'none';
        if (btnCopyImg) btnCopyImg.style.display = 'inline-flex';
        if (btnCopyVid) btnCopyVid.style.display = 'inline-flex';
        if (btnCopyBlueprint) btnCopyBlueprint.style.display = 'none';
      });

      tabBlueprint.addEventListener('click', () => {
        this.inspActiveTab = 'blueprint';
        tabBlueprint.classList.add('active');
        tabComfy.classList.remove('active');
        if (containerComfy) containerComfy.style.display = 'none';
        if (containerBlueprint) containerBlueprint.style.display = 'flex';
        if (btnCopyImg) btnCopyImg.style.display = 'none';
        if (btnCopyVid) btnCopyVid.style.display = 'none';
        if (btnCopyBlueprint) btnCopyBlueprint.style.display = 'inline-flex';
      });
    }

    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());
      dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
      dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.uploadInspiration(e.dataTransfer.files);
        }
      });
      fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
          this.uploadInspiration(fileInput.files);
        }
      });
    }

    if (btnScanComfy) {
      btnScanComfy.addEventListener('click', () => this.generateComfyUIPrompts());
    }

    if (btnScanBlueprint) {
      btnScanBlueprint.addEventListener('click', () => this.analyzeInspirationVault());
    }

    if (btnClearSelect) {
      btnClearSelect.addEventListener('click', () => this.clearSelectedInspImage());
    }

    if (btnOpenFolder) {
      btnOpenFolder.addEventListener('click', () => {
        fetch('/api/open-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: 'F:/WORKHORSE/workspace/inspiration' })
        });
      });
    }

    if (btnCopyImg) {
      btnCopyImg.addEventListener('click', () => {
        const text = this.latestComfyData?.image_prompt || '';
        if (!text) return;
        navigator.clipboard.writeText(text);
        btnCopyImg.innerText = '✓ Copied Image Prompt!';
        setTimeout(() => btnCopyImg.innerText = '📋 Copy Image Prompt', 2000);
      });
    }

    if (btnCopyVid) {
      btnCopyVid.addEventListener('click', () => {
        const text = this.latestComfyData?.video_prompt || '';
        if (!text) return;
        navigator.clipboard.writeText(text);
        btnCopyVid.innerText = '✓ Copied Video Prompt!';
        setTimeout(() => btnCopyVid.innerText = '🎬 Copy Video Prompt', 2000);
      });
    }

    const btnDispatchRender = document.getElementById('btn-dispatch-comfyui-render');
    if (btnDispatchRender) {
      btnDispatchRender.addEventListener('click', async () => {
        const prompt = this.latestComfyData?.image_prompt || '';
        if (!prompt) {
          alert("Please generate or select a ComfyUI prompt first by clicking 'Write ComfyUI Image & Video Prompts'.");
          return;
        }

        const origText = btnDispatchRender.innerHTML;
        btnDispatchRender.innerHTML = '⚡ Dispatching to 5070 Ti...';
        btnDispatchRender.disabled = true;

        try {
          const res = await fetch('/api/comfy/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              prompt: prompt,
              negative_prompt: this.latestComfyData?.negative_prompt || '',
              auto_qc: true
            })
          });
          const data = await res.json();
          if (data.success) {
            const audit = data.qc_audit || {};
            alert(`🎨 Render Complete on RTX 5070 Ti!\n\n✓ Iris Vision QC Status: ${audit.passed ? 'APPROVED' : 'WARNING'}\n✓ Aesthetic Score: ${audit.aesthetic_score || 'N/A'}/10\n✓ Extra Limbs: ${audit.extra_limbs_detected ? 'DETECTED' : 'None'}\n✓ Saved to: ${data.filename}`);
            if (window.workhorseBays && typeof window.workhorseBays.switchBay === 'function') {
              window.workhorseBays.switchBay('ai-operator');
            }
          } else {
            alert(`⚠ ComfyUI Error: ${data.error || 'Failed to generate'}\n\n${data.details?.hint || ''}`);
          }
        } catch (err) {
          alert(`⚠ Connection Error: ${err.message}`);
        } finally {
          btnDispatchRender.innerHTML = origText;
          btnDispatchRender.disabled = false;
        }
      });
    }

    if (btnCopyBlueprint) {
      btnCopyBlueprint.addEventListener('click', () => {
        const text = document.getElementById('blueprint-content')?.innerText || '';
        navigator.clipboard.writeText(text);
        btnCopyBlueprint.innerText = '✓ Copied Blueprint!';
        setTimeout(() => btnCopyBlueprint.innerText = '📋 Copy Shoot Blueprint', 2000);
      });
    }
  }

  selectInspImage(filename) {
    if (this.selectedInspImage === filename) {
      this.clearSelectedInspImage();
      return;
    }
    this.selectedInspImage = filename;

    // Highlight thumbnail
    document.querySelectorAll('.insp-thumb').forEach(el => {
      if (el.getAttribute('data-filename') === filename) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });

    // Update banner
    const banner = document.getElementById('insp-selected-banner');
    const nameLabel = document.getElementById('insp-selected-filename');
    if (banner && nameLabel) {
      nameLabel.innerText = filename;
      banner.style.display = 'flex';
    }

    // Update button text
    const btnComfy = document.getElementById('btn-scan-comfyui');
    if (btnComfy) {
      btnComfy.innerText = `🎨 Write ComfyUI Prompts for "${filename}"`;
    }
    const btnBlueprint = document.getElementById('btn-scan-inspiration');
    if (btnBlueprint) {
      btnBlueprint.innerText = `🔍 Generate Blueprint for "${filename}"`;
    }
  }

  clearSelectedInspImage() {
    this.selectedInspImage = null;
    document.querySelectorAll('.insp-thumb').forEach(el => el.classList.remove('selected'));
    const banner = document.getElementById('insp-selected-banner');
    if (banner) banner.style.display = 'none';

    const btnComfy = document.getElementById('btn-scan-comfyui');
    if (btnComfy) {
      btnComfy.innerText = '🎨 Write ComfyUI Image & Video Prompts';
    }
    const btnBlueprint = document.getElementById('btn-scan-inspiration');
    if (btnBlueprint) {
      btnBlueprint.innerText = '🔍 Generate Director Shoot Blueprint';
    }
  }

  async uploadInspiration(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    const status = document.getElementById('insp-status');
    if (status) status.innerText = `Adding ${files.length} reference photos to vault...`;

    try {
      await fetch('/api/inspiration/upload', {
        method: 'POST',
        body: formData
      });
      if (status) status.innerText = `✓ Added to vault. Ready to reverse-engineer.`;
      this.refreshInspirationVault();
    } catch (err) {
      if (status) status.innerText = `Upload failed: ${err.message}`;
    }
  }

  async refreshInspirationVault() {
    try {
      const res = await fetch('/api/inspiration/files');
      const data = await res.json();
      const grid = document.getElementById('insp-vault-grid');
      const countLabel = document.getElementById('insp-count-label');
      if (countLabel) countLabel.innerText = `${data.count} photos in vault`;

      if (grid) {
        if (!data.files.length) {
          grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 30px; font-size: 11px;">Inspiration vault is empty. Drop competitor or moodboard photos here.</div>';
          return;
        }
        grid.innerHTML = data.files.map(f => `
          <div style="position: relative; overflow: hidden; border-radius: 6px;" title="Click to target ${f} for ComfyUI Prompt Generation">
            <img src="/api/media/${f}" 
                 class="insp-thumb ${this.selectedInspImage === f ? 'selected' : ''}" 
                 data-filename="${f}" 
                 alt="${f}" 
                 onclick="window.workBaysManager.selectInspImage('${f}')" />
          </div>
        `).join('');
      }
    } catch (e) {}
  }

  // --------------------------------------------------------------------------
  // COMPLETED WORK GALLERY — unified, authenticated view of everything any bot
  // has generated (/api/outputs/gallery), fully separated into the Commander's 4
  // real business lines (Fiverr / Etsy / Social Media / Synapse) as distinct top-
  // level tabs - never mixed into one pile. Client-specific categories within the
  // Synapse tab keep a red border accent and a '🎭'/'📦' tag so they can never be
  // visually mistaken for postable marketing content.
  // --------------------------------------------------------------------------
  async initCompletedWorkCategoryRegistry() {
    if (this._completedWorkCategoryRegistry) return this._completedWorkCategoryRegistry;
    try {
      const res = await fetch('/api/outputs/categories');
      const data = await res.json();
      this._completedWorkCategoryRegistry = data.categories || [];
    } catch (e) {
      this._completedWorkCategoryRegistry = [];
    }
    return this._completedWorkCategoryRegistry;
  }

  async switchCompletedWorkGroup(group) {
    this.completedWorkGroup = group;
    this.completedWorkCategory = '';
    document.querySelectorAll('.completed-work-group-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-group') === group);
    });
    await this.renderCompletedWorkCategoryFilters();
    this.refreshCompletedWork();
  }

  async renderCompletedWorkCategoryFilters() {
    const bar = document.getElementById('completed-work-filters');
    if (!bar) return;
    const registry = await this.initCompletedWorkCategoryRegistry();
    const group = this.completedWorkGroup || 'fiverr';
    const groupCategories = registry.filter(c => c.group === group);

    const isClientCat = (cat) => cat.startsWith('client_');
    let html = `<button type="button" class="btn-cyber completed-work-filter-btn active" data-category="" onclick="window.workBaysManager.filterCompletedWork('')" style="font-size: 11px; padding: 5px 12px;">All</button>`;
    html += groupCategories.map(c => `
      <button type="button" class="btn-cyber completed-work-filter-btn" data-category="${c.category}" onclick="window.workBaysManager.filterCompletedWork('${c.category}')" style="font-size: 11px; padding: 5px 12px;${isClientCat(c.category) ? ' border-color: rgba(255,100,100,0.4);' : ''}">${c.label}</button>
    `).join('');
    bar.innerHTML = html;
  }

  async refreshCompletedWork(category) {
    const grid = document.getElementById('completed-work-grid');
    const totalPill = document.getElementById('completed-work-total-pill');
    const navPill = document.getElementById('completed-work-count-pill');
    if (!grid) return;
    this.completedWorkGroup = this.completedWorkGroup || 'fiverr';
    this.completedWorkCategory = category !== undefined ? category : (this.completedWorkCategory || '');

    // First load of this bay - make sure the group's category sub-filters exist.
    if (!document.querySelector('#completed-work-filters .completed-work-filter-btn')) {
      await this.renderCompletedWorkCategoryFilters();
    }

    try {
      const params = new URLSearchParams();
      if (this.completedWorkCategory) {
        params.set('category', this.completedWorkCategory);
      } else {
        params.set('group', this.completedWorkGroup);
      }
      const res = await fetch(`/api/outputs/gallery?${params.toString()}`);
      if (!res.ok) throw new Error(`Gallery request failed (${res.status})`);
      const data = await res.json();
      const items = data.items || [];

      if (totalPill) totalPill.innerText = `${items.length} item${items.length === 1 ? '' : 's'}`;
      if (navPill) navPill.innerText = `${data.total_found || items.length} TOTAL`;

      if (!items.length) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 30px; font-size: 11px;">Nothing finished yet here. Ask Synapse to generate something, or let the automation run!</div>';
        return;
      }

      grid.innerHTML = items.map(item => this.renderCompletedWorkCard(item)).join('');
    } catch (e) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #ff6b6b; padding: 30px; font-size: 11px;">Failed to load completed work: ${e.message}</div>`;
    }
  }

  filterCompletedWork(category) {
    document.querySelectorAll('.completed-work-filter-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-category') === category);
    });
    this.refreshCompletedWork(category);
  }

  renderCompletedWorkCard(item) {
    const viewer = window.outputViewer;
    const media = viewer.normalize(item);
    const esc = value => viewer.escape(value);
    const isClient = item.category.startsWith('client_');
    const sizeLabel = item.size_kb >= 1024 ? `${(item.size_kb / 1024).toFixed(1)} MB` : `${item.size_kb} KB`;
    let preview = `<span class="act-icon" style="font-size: 32px;">${item.media_type === 'archive' ? '📦' : '🧊'}</span>`;
    if (item.media_type === 'image') {
      preview = `<img src="${esc(media.preview_url)}" alt="${esc(item.filename)}" loading="lazy">`;
    } else if (item.media_type === 'video') {
      preview = `<video src="${esc(media.preview_url)}" preload="metadata" muted playsinline></video>`;
    }
    return `
      <div class="completed-work-card ${isClient ? 'client-tagged' : ''}" title="${esc(item.filename)}">
        <button type="button" class="completed-work-preview" data-workhorse-view="${esc(JSON.stringify(media))}" aria-label="View ${esc(item.filename)}">${preview}</button>
        <div class="completed-work-info">
          <span class="completed-work-label">${esc(item.label)}</span>
          <span class="completed-work-filename">${esc(item.filename)}</span>
          <span class="completed-work-meta">${sizeLabel} &middot; ${new Date(item.created * 1000).toLocaleString()}</span>
        </div>
        ${viewer.actions(item)}
      </div>
    `;
  }

  async generateComfyUIPrompts() {
    const btnScan = document.getElementById('btn-scan-comfyui');
    const status = document.getElementById('insp-status');
    const content = document.getElementById('comfyui-content');

    // Switch to ComfyUI tab view automatically
    const tabComfy = document.getElementById('tab-view-comfyui');
    if (tabComfy) tabComfy.click();

    if (btnScan) btnScan.disabled = true;
    const targetMsg = this.selectedInspImage ? `image "${this.selectedInspImage}"` : 'inspiration vault';
    if (status) status.innerText = `🎨 Cipher AI crafting ComfyUI Image & Video Prompts for ${targetMsg} on RTX 3060...`;

    try {
      const url = `/api/inspiration/comfyui-prompts${this.selectedInspImage ? '?image=' + encodeURIComponent(this.selectedInspImage) : ''}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.status === 'empty') {
        if (content) content.innerHTML = `<div style="color: var(--amber-warm);">${data.message}</div>`;
        if (status) status.innerText = 'Vault is empty.';
        return;
      }

      this.latestComfyData = data;

      if (content) {
        content.innerHTML = `
          <!-- CARD 1: POSITIVE IMAGE PROMPT -->
          <div class="comfy-card">
            <div class="comfy-card-header">
              <span class="comfy-card-title cyan">
                <span>🖼️</span> ComfyUI Positive Image Prompt (FLUX.1 / SDXL)
              </span>
              <button class="btn-cyber" data-copy-type="image" style="padding: 4px 10px; font-size: 10px; border-color: #00f2fe; color: #00f2fe;">
                📋 Copy
              </button>
            </div>
            <pre class="comfy-prompt-code" id="box-comfy-pos">${this.escapeHtml(data.image_prompt)}</pre>
          </div>

          <!-- CARD 2: NEGATIVE PROMPT -->
          <div class="comfy-card">
            <div class="comfy-card-header">
              <span class="comfy-card-title amber">
                <span>🛡️</span> ComfyUI Negative Prompt (Anti-Artifacts)
              </span>
              <button class="btn-cyber" data-copy-type="negative" style="padding: 4px 10px; font-size: 10px; border-color: var(--amber-warm); color: var(--amber-warm);">
                📋 Copy
              </button>
            </div>
            <pre class="comfy-prompt-code" style="color: #cbd5e1; font-size: 11px;">${this.escapeHtml(data.negative_prompt)}</pre>
          </div>

          <!-- CARD 3: VIDEO MOTION PROMPT -->
          <div class="comfy-card video">
            <div class="comfy-card-header">
              <span class="comfy-card-title rose">
                <span>🎬</span> ComfyUI Video Motion Prompt (Wan2.1 / CogVideoX / AnimateDiff / SVD)
              </span>
              <button class="btn-cyber" data-copy-type="video" style="padding: 4px 10px; font-size: 10px; border-color: #f72585; color: #f72585;">
                📋 Copy
              </button>
            </div>
            <pre class="comfy-prompt-code" style="color: #fce7f3; border-color: rgba(247,37,133,0.2);">${this.escapeHtml(data.video_prompt)}</pre>
          </div>

          <!-- CARD 4: FULL BREAKDOWN & RECOMMENDED SETTINGS -->
          <div class="comfy-card settings">
            <div class="comfy-card-header">
              <span class="comfy-card-title amber">
                <span>⚙️</span> Recommended ComfyUI Parameters & Director Breakdown
              </span>
              <button class="btn-cyber" data-copy-type="full" style="padding: 4px 10px; font-size: 10px; border-color: var(--amber-warm); color: var(--amber-warm);">
                📋 Copy Full Notes
              </button>
            </div>
            <div id="box-comfy-full" style="font-size: 12px; line-height: 1.6; color: var(--text-main);">
              ${this.renderMarkdown(data.full_markdown)}
            </div>
          </div>
        `;

        // Wire up copy buttons safely
        content.querySelector('button[data-copy-type="image"]')?.addEventListener('click', (e) => {
          navigator.clipboard.writeText(data.image_prompt);
          e.target.innerText = '✓ Copied!';
          setTimeout(() => e.target.innerText = '📋 Copy', 1500);
        });
        content.querySelector('button[data-copy-type="negative"]')?.addEventListener('click', (e) => {
          navigator.clipboard.writeText(data.negative_prompt);
          e.target.innerText = '✓ Copied!';
          setTimeout(() => e.target.innerText = '📋 Copy', 1500);
        });
        content.querySelector('button[data-copy-type="video"]')?.addEventListener('click', (e) => {
          navigator.clipboard.writeText(data.video_prompt);
          e.target.innerText = '✓ Copied!';
          setTimeout(() => e.target.innerText = '📋 Copy', 1500);
        });
        content.querySelector('button[data-copy-type="full"]')?.addEventListener('click', (e) => {
          navigator.clipboard.writeText(data.full_markdown);
          e.target.innerText = '✓ Copied Full!';
          setTimeout(() => e.target.innerText = '📋 Copy Full Notes', 1500);
        });
      }

      if (status) status.innerText = `✓ ComfyUI prompts ready from ${data.images_scanned.join(', ')}!`;
    } catch (err) {
      if (status) status.innerText = `Prompt generation failed: ${err.message}`;
    } finally {
      if (btnScan) btnScan.disabled = false;
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async analyzeInspirationVault() {
    const btnScan = document.getElementById('btn-scan-inspiration');
    const status = document.getElementById('insp-status');
    const content = document.getElementById('blueprint-content');

    // Switch to blueprint tab view automatically
    const tabBlueprint = document.getElementById('tab-view-blueprint');
    if (tabBlueprint) tabBlueprint.click();

    if (btnScan) btnScan.disabled = true;
    const targetMsg = this.selectedInspImage ? `image "${this.selectedInspImage}"` : 'inspiration vault';
    if (status) status.innerText = `🔍 Local Qwen-VL inspecting lighting, posing, and aesthetics for ${targetMsg} on RTX 3060...`;

    try {
      const url = `/api/inspiration/analyze${this.selectedInspImage ? '?image=' + encodeURIComponent(this.selectedInspImage) : ''}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.status === 'empty') {
        if (content) content.innerHTML = `<div style="color: var(--amber-warm);">${data.message}</div>`;
        if (status) status.innerText = 'Vault is empty.';
        return;
      }

      if (content) {
        content.innerHTML = this.renderMarkdown(data.blueprint_markdown);
      }
      if (status) status.innerText = `✓ Shoot Blueprint generated from ${data.images_scanned.length} reference photos.`;
    } catch (err) {
      if (status) status.innerText = `Analysis failed: ${err.message}`;
    } finally {
      if (btnScan) btnScan.disabled = false;
    }
  }

  // --------------------------------------------------------------------------
  // 4. TIP MENU MAKER & CREATOR STORE SUITE
  // --------------------------------------------------------------------------
  initTipMenuMaker() {
    const btnBuild = document.getElementById('btn-build-tip-menu');
    const btnAddTier = document.getElementById('btn-add-menu-tier');
    const btnCopyCode = document.getElementById('btn-copy-active-tip-code');
    const btnDownloadZip = document.getElementById('btn-download-tip-pack');
    const btnCopyBot = document.getElementById('btn-copy-chatbot-text');
    const themeSelect = document.getElementById('tip-menu-theme');
    const layoutSelect = document.getElementById('tip-menu-layout');

    // Bio Mode Buttons
    const btnGenBio = document.getElementById('btn-generate-full-bio');
    const btnBioZip = document.getElementById('btn-download-bio-bundle-zip');
    const btnBioCopy = document.getElementById('btn-copy-full-bio-code');

    if (btnBuild) btnBuild.addEventListener('click', () => this.buildTipMenu());
    if (btnAddTier) btnAddTier.addEventListener('click', () => this.addTipRow('150 tks', 'New sensual tease tier'));
    if (themeSelect) themeSelect.addEventListener('change', () => this.buildTipMenu());
    if (layoutSelect) layoutSelect.addEventListener('change', () => this.buildTipMenu());

    // Personalization Dynamic Listeners
    ['tip-menu-avatar', 'tip-menu-banner', 'tip-menu-top-tipper', 'tip-menu-schedule'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () => this.buildTipMenu());
    });

    if (btnCopyCode) {
      btnCopyCode.addEventListener('click', () => {
        let textToCopy = '';
        if (this.tipViewTab === 'code') {
          textToCopy = document.getElementById('tipmenu-code-pre')?.innerText || '';
        } else if (this.tipViewTab === 'bot') {
          textToCopy = document.getElementById('tipmenu-bot-pre')?.innerText || '';
        } else {
          // If in preview mode, copy the HTML
          textToCopy = this.currentTipResult?.rendered_html || '';
        }
        navigator.clipboard.writeText(textToCopy);
        btnCopyCode.innerText = '✓ Copied!';
        setTimeout(() => btnCopyCode.innerText = '📋 Copy', 2000);
      });
    }

    if (btnCopyBot) {
      btnCopyBot.addEventListener('click', () => {
        const text = this.currentTipResult?.chatbot_text || '';
        navigator.clipboard.writeText(text);
        btnCopyBot.innerText = '✓ Copied Bot Text!';
        setTimeout(() => btnCopyBot.innerText = '🤖 Copy Chatbot Text', 2000);
      });
    }

    if (btnDownloadZip) {
      btnDownloadZip.addEventListener('click', () => {
        if (this.currentTipResult?.bundle?.bundle_name) {
          window.location.href = `/api/download/cam-template/${this.currentTipResult.bundle.bundle_name}`;
        }
      });
    }

    // Full Bio Handlers
    if (btnGenBio) btnGenBio.addEventListener('click', () => this.generateFullBio());
    if (btnBioZip) {
      btnBioZip.addEventListener('click', () => {
        if (this.currentBioResult?.bundle_name) {
          window.location.href = `/api/download/cam-template/${this.currentBioResult.bundle_name}`;
        }
      });
    }
    if (btnBioCopy) {
      btnBioCopy.addEventListener('click', () => {
        const html = this.currentBioResult?.chaturbate_html || '';
        navigator.clipboard.writeText(html);
        btnBioCopy.innerText = '✓ Copied Bio!';
        setTimeout(() => btnBioCopy.innerText = '📋 Copy Bio Code', 2000);
      });
    }
  }

  switchCamSubMode(mode) {
    this.camSubMode = mode;
    document.getElementById('subtab-tip-menu')?.classList.toggle('active', mode === 'tip-menu');
    document.getElementById('subtab-full-bio')?.classList.toggle('active', mode === 'full-bio');

    const modeTip = document.getElementById('cam-mode-tip-menu');
    const modeBio = document.getElementById('cam-mode-full-bio');
    if (modeTip) modeTip.style.display = mode === 'tip-menu' ? 'grid' : 'none';
    if (modeBio) modeBio.style.display = mode === 'full-bio' ? 'grid' : 'none';

    if (mode === 'full-bio' && !this.currentBioResult) {
      this.generateFullBio();
    }
  }

  switchTipViewTab(tab) {
    this.tipViewTab = tab;
    document.getElementById('tab-tipmenu-preview')?.classList.toggle('active', tab === 'preview');
    document.getElementById('tab-tipmenu-code')?.classList.toggle('active', tab === 'code');
    document.getElementById('tab-tipmenu-bot')?.classList.toggle('active', tab === 'bot');

    const prevWrap = document.getElementById('tipmenu-preview-wrapper');
    const codeWrap = document.getElementById('tipmenu-code-wrapper');
    const botWrap = document.getElementById('tipmenu-bot-wrapper');

    if (prevWrap) prevWrap.style.display = tab === 'preview' ? 'block' : 'none';
    if (codeWrap) codeWrap.style.display = tab === 'code' ? 'block' : 'none';
    if (botWrap) botWrap.style.display = tab === 'bot' ? 'block' : 'none';
  }

  loadTipPreset(presetKey) {
    const presets = {
      lovense: {
        title: "⚡ Interactive Lovense Toy Menu ⚡",
        subtitle: "✨ Lush 3 & Domi Synced · High Vibration Pulse · Sound On ✨",
        goal: "Tonight's Goal: 2000 / 4000 Tokens — 10 Min Max Orgasm Challenge",
        items: [
          { tokens: "25 tks", action: "Low Vibration Buzz (1 min)" },
          { tokens: "75 tks", action: "Medium Pulse Waves (2 mins)" },
          { tokens: "150 tks", action: "Earthquake Max Vibration (3 mins)" },
          { tokens: "300 tks", action: "Edge Me / Stop & Go Tease" },
          { tokens: "600 tks", action: "5-Minute Continuous Orgasm Challenge" },
          { tokens: "1000 tks", action: "Toy Overdrive Max / 10 Min VIP Control" }
        ]
      },
      sensual: {
        title: "💋 Goddess Aura's Sensual Strip Menu 💋",
        subtitle: "🔥 Tip to unlock the next level of tease 🔥",
        goal: "Tonight's Goal: 1500 / 3000 Tokens — Full Lingerie Strip & Oil Show",
        items: [
          { tokens: "25 tks", action: "Flash & Smile / Flirty Wink" },
          { tokens: "50 tks", action: "Blow Kisses & Flirty Shiver" },
          { tokens: "100 tks", action: "Sensual Body Oil on Décolletage" },
          { tokens: "250 tks", action: "Topless Tease / Slow Dance Routine" },
          { tokens: "500 tks", action: "Lingerie Strip & Ass Tease" },
          { tokens: "1000 tks", action: "Private Snapchat & VIP Room Access" }
        ]
      },
      kink: {
        title: "👠 Mistress Dominant & Kink Menu 👠",
        subtitle: "⛓️ Obey your Goddess · Pay for your insolence ⛓️",
        goal: "Tonight's Goal: 2500 / 5000 Tokens — Leather & Latex Domination Show",
        items: [
          { tokens: "35 tks", action: "Cold Stare Down & Smirk" },
          { tokens: "75 tks", action: "Leather Glove Tease" },
          { tokens: "150 tks", action: "High-Heel Shoe Praise" },
          { tokens: "250 tks", action: "Spank Myself in Leather Skirt" },
          { tokens: "500 tks", action: "Humiliation Task / Voice Command" },
          { tokens: "1000 tks", action: "Slave Contract / 10 Min Domination" }
        ]
      },
      dares: {
        title: "🥂 Party Dares, Drinks & Fun Menu 🥂",
        subtitle: "🎉 Let's get wild tonight · Tip to dare me 🎉",
        goal: "Tonight's Goal: 1000 / 2000 Tokens — Ice Cube Body Melt",
        items: [
          { tokens: "15 tks", action: "Drink a Big Shot of Water" },
          { tokens: "35 tks", action: "High-Pitch Cute Giggle" },
          { tokens: "100 tks", action: "Write Your Name on My Chest in Lipstick" },
          { tokens: "200 tks", action: "30-Second High-Energy Twerk" },
          { tokens: "350 tks", action: "Ice Cube Slide Down My Stomach" },
          { tokens: "500 tks", action: "10 Pushups in 6-Inch Heels" }
        ]
      }
    };

    const p = presets[presetKey] || presets.lovense;
    const titleInput = document.getElementById('tip-menu-title');
    const subInput = document.getElementById('tip-menu-subtitle');
    const goalInput = document.getElementById('tip-menu-goal');

    if (titleInput) titleInput.value = p.title;
    if (subInput) subInput.value = p.subtitle;
    if (goalInput) goalInput.value = p.goal;

    this.tipItems = JSON.parse(JSON.stringify(p.items));
    this.renderTipRows();
    this.buildTipMenu();
  }

  renderTipRows() {
    const container = document.getElementById('tip-menu-rows-container');
    if (!container) return;
    container.innerHTML = '';

    this.tipItems.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = 'tip-menu-builder-row';
      row.innerHTML = `
        <input type="text" class="tip-token-input" value="${item.tokens}" placeholder="50 tks" />
        <input type="text" class="tip-desc-input" value="${item.action}" placeholder="Action description" />
        <button class="btn-cyber" style="padding: 4px 8px; color: var(--pink-hot); border-color: rgba(247,37,133,0.3);" title="Remove tier">✕</button>
      `;

      const tInput = row.querySelector('.tip-token-input');
      const dInput = row.querySelector('.tip-desc-input');
      const delBtn = row.querySelector('button');

      tInput.addEventListener('input', (e) => {
        this.tipItems[idx].tokens = e.target.value;
      });
      dInput.addEventListener('input', (e) => {
        this.tipItems[idx].action = e.target.value;
      });
      delBtn.addEventListener('click', () => {
        this.tipItems.splice(idx, 1);
        this.renderTipRows();
        this.buildTipMenu();
      });

      container.appendChild(row);
    });
  }

  addTipRow(tokens = '150 tks', action = 'Custom Sensual Tease Action') {
    this.tipItems.push({ tokens, action });
    this.renderTipRows();
    this.buildTipMenu();
  }

  async buildTipMenu() {
    const title = document.getElementById('tip-menu-title')?.value.trim() || 'Interactive Tip Menu';
    const subtitle = document.getElementById('tip-menu-subtitle')?.value.trim() || 'Lovense Lush Active';
    const theme = document.getElementById('tip-menu-theme')?.value || 'neon_cyber';
    const layout = document.getElementById('tip-menu-layout')?.value || 'vip_showcase';
    const goal = document.getElementById('tip-menu-goal')?.value.trim() || '';
    const avatar = document.getElementById('tip-menu-avatar')?.value.trim() || '';
    const banner = document.getElementById('tip-menu-banner')?.value.trim() || '';
    const topTipper = document.getElementById('tip-menu-top-tipper')?.value.trim() || '';
    const schedule = document.getElementById('tip-menu-schedule')?.value.trim() || '';
    const status = document.getElementById('tip-menu-build-status');

    if (status) status.innerText = '⚡ Building high-level VIP creator showcase & tip menu...';

    try {
      const res = await fetch('/api/templates/tip-menu/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          subtitle: subtitle,
          theme: theme,
          layout_style: layout,
          items: this.tipItems,
          goal_text: goal,
          avatar_url: avatar,
          banner_url: banner,
          top_tipper: topTipper,
          schedule: schedule
        })
      });

      const data = await res.json();
      this.currentTipResult = data;

      if (status) status.innerText = `✓ Tip menu ready! Bundled into ${data.bundle.zip_name} (${data.bundle.zip_size_kb} KB).`;

      // Flag any fields still on stock/demo placeholder data before this ships to a real client
      const warnBox = document.getElementById('tip-menu-build-warnings');
      if (warnBox) {
        if (data.warnings && data.warnings.length > 0) {
          warnBox.style.display = 'block';
          warnBox.innerHTML = `⚠ Still using demo placeholder data for:<br>` + data.warnings.map(w => `• ${w}`).join('<br>');
        } else {
          warnBox.style.display = 'none';
          warnBox.innerHTML = '';
        }
      }
      // 1. Update Preview Sandbox Frame
      const frame = document.getElementById('tipmenu-preview-frame');
      if (frame) {
        frame.srcdoc = data.rendered_html;
      }

      // 2. Update Code display
      const codePre = document.getElementById('tipmenu-code-pre');
      if (codePre) {
        codePre.innerText = data.rendered_html;
      }

      // 3. Update Chatbot text display
      const botPre = document.getElementById('tipmenu-bot-pre');
      if (botPre) {
        botPre.innerText = data.chatbot_text;
      }

      // 4. Update Download Button
      const zipBtn = document.getElementById('btn-download-tip-pack');
      if (zipBtn && data.bundle) {
        zipBtn.innerText = `📦 Download Tip Pack ZIP (${data.bundle.zip_name})`;
      }

    } catch (err) {
      if (status) status.innerText = `Build error: ${err.message}`;
    }
  }

  async generateFullBio() {
    const modelName = document.getElementById('cam-model-name')?.value.trim() || 'GoddessAura';
    const theme = document.getElementById('cam-bio-theme-select')?.value || 'neon_cyber';
    const platform = document.getElementById('cam-bio-platform-select')?.value || 'chaturbate';

    try {
      const res = await fetch('/api/templates/generate-cam', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_name: modelName,
          theme: theme,
          tip_menu: this.tipItems
        })
      });

      const data = await res.json();
      this.currentBioResult = data;

      const html = platform === 'mfc' ? data.mfc_html : data.chaturbate_html;
      const frame = document.getElementById('bio-preview-frame');
      if (frame) frame.srcdoc = html;

      const zipBtn = document.getElementById('btn-download-bio-bundle-zip');
      if (zipBtn) {
        zipBtn.innerText = `📦 Download Complete Bio Digital Pack (${data.zip_name})`;
      }
    } catch (e) {}
  }


  // --------------------------------------------------------------------------
  // 5. ETSY DIGITAL STORE (THE MULTI-THOUSAND DOLLAR WORKAROUND)
  // --------------------------------------------------------------------------
  async bundleEtsy(productType = 'all') {
    const status = document.getElementById('etsy-bundle-status');
    const metaPre = document.getElementById('etsy-metadata-pre');

    if (status) status.innerText = `⚡ Generating ${productType.toUpperCase()} package & Adobe presets on GPU...`;

    try {
      const res = await fetch('/api/etsy/bundle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_type: productType })
      });

      const data = await res.json();
      if (status) {
        status.innerHTML = `✓ Packaged ${data.total_files} files into <strong style="color:#fff;">${data.zip_name}</strong> (${data.zip_size_kb} KB)! <a href="/api/download/etsy/${data.bundle_name}" class="btn-cyber" style="padding:2px 8px; font-size:10px; margin-left:8px; text-decoration:none; color:var(--amber-warm);">Download ZIP</a>`;
      }

      if (metaPre) {
        metaPre.innerText = data.listing_guide;
      }
    } catch (err) {
      if (status) status.innerText = `Bundle error: ${err.message}`;
    }
  }

  openEtsyFolder() {
    fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: 'F:/WORKHORSE/workspace/etsy_bundles' })
    });
  }

  copyEtsyMetadata() {
    const text = document.getElementById('etsy-metadata-pre')?.innerText || '';
    navigator.clipboard.writeText(text);
    const btn = document.getElementById('btn-copy-etsy-meta');
    if (btn) {
      btn.innerText = '✓ Copied!';
      setTimeout(() => btn.innerText = '📋 Copy Listing Kit', 2000);
    }
  }

  // --------------------------------------------------------------------------
  // 6. FIVERR SERVICE BOT (HIGH-DEMAND GIG AUTOMATION)
  // --------------------------------------------------------------------------
  async initFiverrBot() {
    try {
      const res = await fetch('/api/fiverr/gigs');
      const data = await res.json();
      this.fiverrGigs = data.gigs || [];
      if (this.fiverrGigs.length) {
        this.selectFiverrGig(this.fiverrGigs[0].id);
      }
    } catch (e) {}
  }

  selectFiverrGig(gigId) {
    this.activeFiverrGigId = gigId;

    document.querySelectorAll('.fiverr-gig-card').forEach(card => {
      card.classList.toggle('active', card.id === `fiverr-card-${gigId}`);
    });

    const gig = this.fiverrGigs?.find(g => g.id === gigId);
    if (!gig) return;

    // 1. Update Title & Category
    const titleEl = document.getElementById('fiverr-active-gig-title');
    const catEl = document.getElementById('fiverr-active-gig-category');
    if (titleEl) titleEl.innerText = `"${gig.title}"`;
    if (catEl) catEl.innerText = gig.category;

    // 2. Update Pricing Table
    const tbody = document.getElementById('fiverr-pricing-tbody');
    if (tbody && gig.pricing) {
      tbody.innerHTML = `
        <tr>
          <td><strong style="color:var(--green-neon);">Basic</strong><br><span style="font-size:10px; color:var(--text-muted);">${gig.pricing.basic.name}</span></td>
          <td style="font-weight:bold; color:#fff;">${gig.pricing.basic.price}</td>
          <td>${gig.pricing.basic.desc}</td>
          <td style="font-family:monospace; color:var(--cyan-glow);">${gig.pricing.basic.delivery}</td>
        </tr>
        <tr>
          <td><strong style="color:var(--green-neon);">Standard</strong><br><span style="font-size:10px; color:var(--text-muted);">${gig.pricing.standard.name}</span></td>
          <td style="font-weight:bold; color:#fff;">${gig.pricing.standard.price}</td>
          <td>${gig.pricing.standard.desc}</td>
          <td style="font-family:monospace; color:var(--cyan-glow);">${gig.pricing.standard.delivery}</td>
        </tr>
        <tr>
          <td><strong style="color:var(--green-neon);">Premium</strong><br><span style="font-size:10px; color:var(--text-muted);">${gig.pricing.premium.name}</span></td>
          <td style="font-weight:bold; color:#fff;">${gig.pricing.premium.price}</td>
          <td>${gig.pricing.premium.desc}</td>
          <td style="font-family:monospace; color:var(--cyan-glow);">${gig.pricing.premium.delivery}</td>
        </tr>
      `;
    }

    // 3. Update Search Tags
    const tagsRow = document.getElementById('fiverr-active-tags-row');
    if (tagsRow && gig.search_tags) {
      tagsRow.innerHTML = gig.search_tags.map(t => `
        <span class="bay-pill" style="color:var(--green-neon); border:1px solid rgba(6,214,160,0.4);">${t}</span>
      `).join('');
    }

    // 4. Update Description
    const descPre = document.getElementById('fiverr-active-desc-pre');
    if (descPre) {
      descPre.innerText = gig.description;
    }
  }

  async fulfillFiverrOrder() {
    const gigId = this.activeFiverrGigId || 'gig_retouch';
    const clientName = document.getElementById('fiverr-client-name')?.value.trim() || 'Valued Buyer';
    const orderNum = document.getElementById('fiverr-order-number')?.value.trim() || 'FO_1001';
    const status = document.getElementById('fiverr-fulfill-status');

    if (status) status.innerText = `⚡ Bundling finished assets for ${clientName} (${orderNum})...`;

    try {
      const res = await fetch('/api/fiverr/fulfill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gig_id: gigId,
          client_name: clientName,
          order_number: orderNum
        })
      });

      const data = await res.json();
      if (status) status.innerText = `✓ Order ${orderNum} fulfilled! ${data.delivery_zip_name} (${data.delivery_zip_size_kb} KB)`;

      const outBox = document.getElementById('fiverr-delivery-output');
      if (outBox) outBox.style.display = 'block';

      const notePre = document.getElementById('fiverr-delivery-note-pre');
      if (notePre) notePre.innerText = data.delivery_note;

      const downBtn = document.getElementById('btn-download-fiverr-zip');
      if (downBtn) {
        downBtn.onclick = () => {
          window.location.href = `/api/download/fiverr/${orderNum}`;
        };
      }
    } catch (err) {
      if (status) status.innerText = `Fulfillment error: ${err.message}`;
    }
  }

  copyFiverrDeliveryNote() {
    const text = document.getElementById('fiverr-delivery-note-pre')?.innerText || '';
    navigator.clipboard.writeText(text);
  }

  copyFiverrGigBlueprint() {
    const gig = this.fiverrGigs?.find(g => g.id === this.activeFiverrGigId);
    if (!gig) return;

    const blueprint = `TITLE: ${gig.title}\n\nCATEGORY: ${gig.category}\n\nTAGS: ${gig.search_tags.join(', ')}\n\nDESCRIPTION:\n${gig.description}\n\nPRICING:\nBasic: ${gig.pricing.basic.price} - ${gig.pricing.basic.desc}\nStandard: ${gig.pricing.standard.price} - ${gig.pricing.standard.desc}\nPremium: ${gig.pricing.premium.price} - ${gig.pricing.premium.desc}`;
    navigator.clipboard.writeText(blueprint);
  }

  openFiverrFolder() {
    fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: 'F:/WORKHORSE/workspace/fiverr_deliveries' })
    });
  }


  // --------------------------------------------------------------------------
  // 7. CIPHER MARKET INTELLIGENCE & TREND MATRIX
  // --------------------------------------------------------------------------
  switchInspSubTab(tab) {
    document.getElementById('subtab-insp-scanner')?.classList.toggle('active', tab === 'scanner');
    document.getElementById('subtab-insp-matrix')?.classList.toggle('active', tab === 'matrix');

    const modeScanner = document.getElementById('insp-mode-scanner');
    const modeMatrix = document.getElementById('insp-mode-matrix');

    if (modeScanner) modeScanner.style.display = tab === 'scanner' ? 'grid' : 'none';
    if (modeMatrix) modeMatrix.style.display = tab === 'matrix' ? 'block' : 'none';
  }

  async generateCipherBriefing() {
    const box = document.getElementById('cipher-briefing-box');
    const textEl = document.getElementById('cipher-briefing-text');

    if (box) box.style.display = 'block';
    if (textEl) textEl.innerText = '⚡ Cipher analyzing cross-bay intelligence across Dual RTX 3060 GPUs (Photo Retouching, Lighting/Posing, Cam Menus, Etsy & Fiverr)...';

    try {
      const res = await fetch('/api/research/briefing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focus_area: 'all' })
      });

      const data = await res.json();
      if (textEl) {
        textEl.innerText = data.briefing;
      }
    } catch (err) {
      if (textEl) textEl.innerText = `Cipher briefing error: ${err.message}`;
    }
  }

  copyCipherBriefing() {
    const text = document.getElementById('cipher-briefing-text')?.innerText || '';
    navigator.clipboard.writeText(text);
  }

  renderMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/\n/gim, '<br>');
    return html;
  }

  // --------------------------------------------------------------------------
  // ORDER RADAR (Live Gmail & Platform Orders)
  // --------------------------------------------------------------------------
  initOrderRadar() {
    const btnOpen = document.getElementById('btn-open-radar');
    const modal = document.getElementById('radar-modal');
    const btnClose = document.getElementById('btn-close-radar');
    const btnSavePw = document.getElementById('btn-radar-save-pw');
    const btnCheckNow = document.getElementById('btn-radar-check-now');
    const btnSimFiverr = document.getElementById('btn-sim-fiverr');
    const btnSimEtsy = document.getElementById('btn-sim-etsy');

    if (btnOpen && modal) {
      btnOpen.addEventListener('click', () => {
        modal.classList.add('open');
        this.fetchRadarStatus();
      });
    }

    if (btnClose && modal) {
      btnClose.addEventListener('click', () => {
        modal.classList.remove('open');
      });
    }

    if (btnSavePw) {
      btnSavePw.addEventListener('click', async () => {
        const pw = document.getElementById('radar-app-password').value;
        const msg = document.getElementById('radar-status-msg');
        msg.innerText = 'Saving password...';
        try {
          const res = await fetch('/api/radar/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app_password: pw, auto_check: true })
          });
          const data = await res.json();
          msg.innerText = '✅ App Password saved securely!';
          this.fetchRadarStatus();
        } catch (e) {
          msg.innerText = `Error: ${e.message}`;
        }
      });
    }

    if (btnCheckNow) {
      btnCheckNow.addEventListener('click', async () => {
        const msg = document.getElementById('radar-status-msg');
        msg.innerText = 'Connecting to Gmail IMAP...';
        try {
          const res = await fetch('/api/radar/check', { method: 'POST' });
          const data = await res.json();
          if (data.status === 'awaiting_app_password') {
            msg.innerText = '⚠️ Enter Google App Password first.';
          } else if (data.status === 'connected') {
            msg.innerText = `✅ Connected. ${data.new_orders} new orders detected!`;
            if (data.new_orders > 0) this.playChimeSound();
          } else if (data.status === 'auth_error') {
            msg.innerText = `❌ ${data.error}`;
          } else {
            msg.innerText = data.message || 'Checked.';
          }
          this.fetchRadarStatus();
        } catch (e) {
          msg.innerText = `Error: ${e.message}`;
        }
      });
    }

    if (btnSimFiverr) {
      btnSimFiverr.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/radar/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: 'fiverr' })
          });
          const data = await res.json();
          this.playChimeSound();
          this.fetchRadarStatus();
        } catch (e) {
          alert('Error simulating order: ' + e.message);
        }
      });
    }

    if (btnSimEtsy) {
      btnSimEtsy.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/radar/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: 'etsy' })
          });
          const data = await res.json();
          this.playChimeSound();
          this.fetchRadarStatus();
        } catch (e) {
          alert('Error simulating order: ' + e.message);
        }
      });
    }

    // Initial check
    this.fetchRadarStatus();
    // Poll every 30 seconds
    setInterval(() => this.fetchRadarStatus(), 30000);
  }

  playChimeSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const playTone = (freq, time, dur) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, time);
        gain.gain.setValueAtTime(0.15, time);
        gain.gain.exponentialRampToValueAtTime(0.001, time + dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(time);
        osc.stop(time + dur);
      };
      const now = ctx.currentTime;
      playTone(523.25, now, 0.25); // C5
      playTone(659.25, now + 0.12, 0.25); // E5
      playTone(783.99, now + 0.24, 0.4); // G5
    } catch (e) {
      console.log('Audio chime not permitted without user gesture');
    }
  }

  async fetchRadarStatus() {
    try {
      const res = await fetch('/api/radar/status');
      const data = await res.json();
      
      const badge = document.getElementById('radar-badge-count');
      const ordersCount = document.getElementById('radar-orders-count');
      const listEl = document.getElementById('radar-orders-list');
      
      const orders = data.active_orders || [];
      const pendingOrders = orders.filter(o => o.status === 'pending');

      if (badge) badge.innerText = pendingOrders.length;
      if (ordersCount) ordersCount.innerText = orders.length;

      if (!listEl) return;

      if (orders.length === 0) {
        listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">No orders in queue. Click Simulate above or connect Gmail inbox.</div>';
        return;
      }

      listEl.innerHTML = orders.map(o => {
        const isFiverr = o.platform === 'fiverr';
        const tagClass = isFiverr ? 'platform-fiverr' : 'platform-etsy';
        const isPending = o.status === 'pending';

        return `
          <div class="radar-order-item">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="radar-order-platform-tag ${tagClass}">${o.platform}</span>
              <div>
                <div style="font-size: 12px; font-weight: bold; color: #fff;">${o.id} &bull; ${o.buyer}</div>
                <div style="font-size: 11px; color: #94a3b8;">${o.title || o.package}</div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="text-align: right;">
                <div style="font-size: 13px; font-weight: bold; color: #06d6a0;">${o.amount}</div>
                <div style="font-size: 10px; color: ${isPending ? '#ffd166' : '#06d6a0'}; font-family: monospace;">
                  ${isPending ? 'PENDING ACTION' : 'FULFILLED'}
                </div>
              </div>
              ${isFiverr && isPending ? `
                <button class="btn-cyber cyan-btn" style="font-size: 10px; padding: 4px 8px;" onclick="window.workBaysManager.loadOrderIntoFulfill('${o.id}', '${o.buyer}', '${o.gig_id || 'gig_retouch'}')">
                  ⚡ Fulfill
                </button>
              ` : ''}
            </div>
          </div>
        `;
      }).join('');

    } catch (e) {
      console.error('Error fetching radar status:', e);
    }
  }

  loadOrderIntoFulfill(orderId, buyer, gigId) {
    // Close radar modal
    const modal = document.getElementById('radar-modal');
    if (modal) modal.classList.remove('open');

    // Switch to fiverr bot bay
    this.switchBay('fiverr-bot');

    // Pre-fill inputs
    const orderInput = document.getElementById('fiverr-fulfill-order');
    const clientInput = document.getElementById('fiverr-fulfill-client');
    const gigSelect = document.getElementById('fiverr-fulfill-gig');

    if (orderInput) orderInput.value = orderId;
    if (clientInput) clientInput.value = buyer;
    if (gigSelect && gigId) gigSelect.value = gigId;

    // Scroll to fulfillment box
    const fulfillBox = document.getElementById('fiverr-fulfill-order');
    if (fulfillBox) fulfillBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }


// --------------------------------------------------------------------------
  // 7. OMNI-CHANNEL MARKETING HUB (MERCURY [80 Hg])
  // --------------------------------------------------------------------------
  initMarketingHub() {
    this.currentMarketingTab = 'social';
    if (!this.marketingInitialized) {
      this.marketingInitialized = true;
      const channelSelect = document.getElementById('mkt-channel-select');
      if (channelSelect) {
        channelSelect.addEventListener('change', (e) => {
          this.setMarketingChannel(e.target.value);
        });
      }
    }
  }

  setMarketingChannel(channel) {
    const channelSelect = document.getElementById('mkt-channel-select');
    if (channelSelect) channelSelect.value = channel;

    const nameInput = document.getElementById('mkt-target-name');
    const urlInput = document.getElementById('mkt-target-url');

    if (channel === 'etsy') {
      if (nameInput) nameInput.value = 'Boudoir & Glamour Lightroom Presets (.XMP)';
      if (urlInput) urlInput.value = 'https://www.etsy.com/shop/CreatorMediaLab';
    } else if (channel === 'fiverr') {
      if (nameInput) nameInput.value = 'High-End Studio Photo Retouching & Color Grading';
      if (urlInput) urlInput.value = 'https://www.fiverr.com/s/X00R79G';
    } else if (channel === 'social') {
      if (nameInput) nameInput.value = 'Digital Creator Assets & Media Lab';
      if (urlInput) urlInput.value = '@TheCreatorAsset';
    } else if (channel === 'website') {
      if (nameInput) nameInput.value = 'WORKHORSE Studio & Digital Goods Store';
      if (urlInput) urlInput.value = 'https://careypmedia.com';
    }
  }

  async generateMarketingCampaign() {
    const btn = document.getElementById('btn-generate-campaign');
    const pane = document.getElementById('mkt-output-pane');
    if (btn) btn.innerText = '⚡ Synthesizing Campaign...';

    const payload = {
      channel: document.getElementById('mkt-channel-select')?.value || 'etsy',
      target_name: document.getElementById('mkt-target-name')?.value || 'Digital Product Bundle',
      target_url: document.getElementById('mkt-target-url')?.value || '',
      goal: document.getElementById('mkt-goal-select')?.value || 'conversions',
      custom_notes: document.getElementById('mkt-custom-notes')?.value || ''
    };

    try {
      const res = await fetch('/api/marketing/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'ok') {
        this.currentCampaign = data.campaign;
        this.renderMarketingOutput();
      } else {
        if (pane) pane.innerHTML = `<span style="color:#f87171;">Error: ${data.detail || 'Failed to generate campaign'}</span>`;
      }
    } catch (err) {
      if (pane) pane.innerHTML = `<span style="color:#f87171;">Network Error: ${err.message}</span>`;
    } finally {
      if (btn) btn.innerText = '⚡ Generate Omni-Campaign Kit →';
    }
  }

  setMarketingTab(tab) {
    this.currentMarketingTab = tab;
    ['social', 'ads', 'seo', 'ai', 'history'].forEach(t => {
      const el = document.getElementById(`tab-mkt-${t}`);
      if (el) el.classList.toggle('active', t === tab);
    });
    this.renderMarketingOutput();
  }

  renderMarketingOutput() {
    const pane = document.getElementById('mkt-output-pane');
    if (!pane) return;
    if (!this.currentCampaign) {
      pane.innerHTML = '<div style="text-align:center;color:var(--text-dim);padding:40px 0;">No active campaign yet. Click Generate to build one.</div>';
      return;
    }

    const c = this.currentCampaign.content || {};
    const tab = this.currentMarketingTab;

    if (tab === 'social') {
      let html = `<h4 style="color:#a855f7;margin-bottom:8px;">📱 Viral Social Scripts & Roadmap</h4>`;
      if (c.tiktok_reels_script) {
        html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
          <strong>🎬 TikTok & Reels Script (9:16)</strong><br>
          <span style="color:#a855f7;">Visual Hook:</span> ${c.tiktok_reels_script.hook_visual}<br>
          <span style="color:#00f2fe;">Voiceover:</span> "${c.tiktok_reels_script.voiceover}"<br>
          <span style="color:#10b981;">Caption:</span> ${c.tiktok_reels_script.caption}
        </div>`;
      }
      if (c.weekly_content_calendar) {
        html += `<strong>📅 7-Day Content Roadmap:</strong><br><br>`;
        c.weekly_content_calendar.forEach(d => {
          html += `<div style="margin-bottom:8px;"><strong>${d.day} (${d.theme}):</strong> [${d.format}] "${d.hook}" &rarr; <em>${d.call_to_action}</em></div>`;
        });
      }
      if (c.viral_hook_vault) {
        html += `<br><strong>🔥 Viral Hooks Vault:</strong><br>`;
        c.viral_hook_vault.forEach(h => html += `&bull; "${h}"<br>`);
      }
      pane.innerHTML = html;
    } else if (tab === 'ads') {
      let html = `<h4 style="color:#a855f7;margin-bottom:8px;">📢 High-Converting Ad Copy & Outreach</h4>`;
      if (c.buyer_pitch) {
        html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
          <strong>💼 Fiverr Pitch / Buyer Response:</strong><br>${c.buyer_pitch}
        </div>`;
      }
      if (c.meta_facebook_ads) {
        c.meta_facebook_ads.forEach((ad, i) => {
          html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
            <strong>Meta Ad Variation ${i+1}:</strong><br>
            <span style="color:#00f2fe;">Primary Text:</span> ${ad.primary_text}<br>
            <span style="color:#10b981;">Headline:</span> ${ad.headline}<br>
            <span style="color:#ffd166;">CTA:</span> ${ad.call_to_action}
          </div>`;
        });
      }
      if (c.launch_email_copy) {
        html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
          <strong>📧 Launch Announcement Email:</strong><br><pre style="white-space:pre-wrap;font-family:inherit;">${c.launch_email_copy}</pre>
        </div>`;
      }
      pane.innerHTML = html;
    } else if (tab === 'seo') {
      let html = `<h4 style="color:#a855f7;margin-bottom:8px;">🔍 SEO Tags & Pinterest Pins</h4>`;
      if (c.pinterest_pins) {
        c.pinterest_pins.forEach((pin, i) => {
          html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
            <strong>📌 Pinterest Pin #${i+1}:</strong> ${pin.title}<br>
            <span style="color:#94a3b8;">Description:</span> ${pin.description}<br>
            <span style="color:#a855f7;">Keywords:</span> ${pin.keywords?.join(', ')}
          </div>`;
        });
      }
      if (c.etsy_seo_listing_pack) {
        html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:12px;">
          <strong>🛍️ Optimized Etsy Title:</strong><br>${c.etsy_seo_listing_pack.optimized_title}<br><br>
          <strong>🏷️ 13 High-Rank Tags:</strong><br>${c.etsy_seo_listing_pack.tags?.join(', ')}<br><br>
          <strong>🏷️ Price Suggestion:</strong> ${c.etsy_seo_listing_pack.price_recommendation}
        </div>`;
      }
      if (c.high_growth_hashtags) {
        html += `<strong>#️⃣ High-Reach Hashtags:</strong><br>${c.high_growth_hashtags.join(' ')}`;
      }
      pane.innerHTML = html;
    } else if (tab === 'ai') {
      let html = `<h4 style="color:#a855f7;margin-bottom:8px;">🎨 Ready-to-Generate Prompts for Forge & Iris</h4>`;
      if (c.ai_creative_prompt) {
        html += `<div style="background:rgba(255,255,255,0.04);padding:14px;border-radius:6px;margin-bottom:12px;">
          <strong>Visual Generation Prompt:</strong><br><br>
          <div style="color:#10b981;padding:10px;background:rgba(0,0,0,0.3);border-radius:4px;">${c.ai_creative_prompt}</div><br>
          <button class="btn-cyber" onclick="navigator.clipboard.writeText('${c.ai_creative_prompt.replace(/'/g, "\\'")}')" style="font-size:11px;padding:4px 10px;">
            📋 Copy Prompt
          </button>
        </div>`;
      }
      pane.innerHTML = html;
    }
  }

  async loadMarketingHistory() {
    this.currentMarketingTab = 'history';
    ['social', 'ads', 'seo', 'ai'].forEach(t => document.getElementById(`tab-mkt-${t}`)?.classList.remove('active'));
    document.getElementById('tab-mkt-history')?.classList.add('active');

    const pane = document.getElementById('mkt-output-pane');
    if (!pane) return;
    pane.innerHTML = '<div>Loading past campaigns...</div>';

    try {
      const res = await fetch('/api/marketing/history');
      const data = await res.json();
      if (data.status === 'ok' && data.campaigns?.length) {
        let html = `<h4 style="color:#a855f7;margin-bottom:10px;">📜 Saved Marketing Campaigns (${data.campaigns.length})</h4>`;
        data.campaigns.forEach(cmp => {
          html += `<div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:6px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">
            <div>
              <strong>${cmp.target_name}</strong> [${cmp.channel.toUpperCase()}]<br>
              <small style="color:var(--text-dim);">${cmp.created_at} &bull; Goal: ${cmp.goal}</small>
            </div>
            <button class="btn-cyber" onclick="window.workBaysManager.reloadCampaign('${cmp.id}')" style="font-size:11px;padding:4px 10px;">
              Load Kit
            </button>
          </div>`;
        });
        pane.innerHTML = html;
        this.campaignVault = data.campaigns;
      } else {
        pane.innerHTML = '<div>No saved campaigns found.</div>';
      }
    } catch (e) {
      pane.innerHTML = `<div>Error loading history: ${e.message}</div>`;
    }
  }

  reloadCampaign(cmpId) {
    if (!this.campaignVault) return;
    const found = this.campaignVault.find(c => c.id === cmpId);
    if (found) {
      this.currentCampaign = found;
      this.setMarketingTab('social');
    }
  }

  copyMarketingOutput() {
    const pane = document.getElementById('mkt-output-pane');
    if (pane) {
      navigator.clipboard.writeText(pane.innerText);
      alert('Marketing output copied to clipboard!');
    }
  }

  // --------------------------------------------------------------------------
  // 8. NEWSLETTER & BLOG DISPATCHER (HERALD [33 As])
  // --------------------------------------------------------------------------
  initNewsletterHub() {
    const urlParams = new URLSearchParams(window.location.search);
    const pubParam = urlParams.get('pub') || 'creator_pulse';
    const tabParam = urlParams.get('tab') || 'preview';
    this.currentNewsletterTab = tabParam;
    this.selectedPublication = pubParam;
    this.refreshNewsletterConfig();
    this.selectPublication(pubParam);
    if (tabParam !== 'preview') {
      this.setNewsletterTab(tabParam);
    }
  }

  selectPublication(pubId) {
    this.selectedPublication = pubId;

    // Update active button state across ALL instances of the publication selector bar
    // (it's duplicated in both the Marketing bay and the Newsletter bay), not just the
    // first one found - using getElementById here used to only ever update whichever
    // bay's bar happened to come first in the DOM, leaving the other bay's buttons stuck.
    ['creator_pulse', 'studio_wire', 'creator_blueprint', 'dispensary_deals'].forEach(id => {
      const btns = document.querySelectorAll(`[data-pub-id="${id}"]`);
      btns.forEach(btn => {
        if (id === pubId) {
          const color = id === 'creator_pulse' ? '#f72585' :
                        id === 'studio_wire' ? '#3b82f6' :
                        id === 'creator_blueprint' ? '#eab308' :
                        '#10b981';
          btn.style.background = id === 'creator_pulse' ? 'rgba(247,37,133,0.3)' :
                                 id === 'studio_wire' ? 'rgba(59,130,246,0.3)' :
                                 id === 'creator_blueprint' ? 'rgba(234,179,8,0.3)' :
                                 'rgba(16,185,129,0.3)';
          btn.style.borderColor = color;
          btn.style.color = '#fff';
          btn.style.boxShadow = `0 0 12px ${color}`;
        } else {
          btn.style.background = 'rgba(255,255,255,0.04)';
          btn.style.borderColor = 'rgba(255,255,255,0.12)';
          btn.style.color = '#94a3b8';
          btn.style.boxShadow = 'none';
        }
      });
    });

    // Update header subtitle
    const subHeader = document.getElementById('nl-sub-header');
    if (subHeader) {
      if (pubId === 'creator_pulse') {
        subHeader.innerHTML = '💋 <strong>The Daily Creator Pulse</strong> &bull; Handle: <a href="https://twitter.com/creatorpulselab" target="_blank" style="color:#f72585;font-weight:bold;">@creatorpulselab</a> &bull; Audience: Adult Creators &bull; <a href="https://digitalcreatorassets-source.github.io/creatormedialab/?pub=creator_pulse" target="_blank" style="color:#f72585;">Web Portal</a> &bull; Funnel: <a href="https://linktr.ee/CreatorMediaLab" target="_blank" style="color:#10b981;font-weight:bold;">Linktree</a>';
      } else if (pubId === 'studio_wire') {
        subHeader.innerHTML = '📸 <strong>The Shutter & Studio Wire</strong> &bull; Handle: <a href="https://twitter.com/TheCreatorAsset" target="_blank" style="color:#3b82f6;font-weight:bold;">@TheCreatorAsset</a> &bull; Audience: Photographers &bull; <a href="https://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire" target="_blank" style="color:#3b82f6;">Portal</a> &bull; Funnel: <a href="https://linktr.ee/CreatorMediaLab" target="_blank" style="color:#10b981;font-weight:bold;">Linktree</a>';
      } else if (pubId === 'creator_blueprint') {
        subHeader.innerHTML = '⚡ <strong>The Creator Blueprint</strong> &bull; Handle: <a href="https://twitter.com/TheCreatorAsset" target="_blank" style="color:#eab308;font-weight:bold;">@TheCreatorAsset</a> &bull; Audience: Digital Creators &bull; <a href="https://digitalcreatorassets-source.github.io/creatormedialab/?pub=creator_blueprint" target="_blank" style="color:#eab308;">Portal</a> &bull; Funnel: <a href="https://linktr.ee/CreatorMediaLab" target="_blank" style="color:#10b981;font-weight:bold;">Linktree</a>';
      } else {
        subHeader.innerHTML = '🌿 <strong>Florida Dispensary Deals</strong> &bull; Status: <span style="color:#10b981;font-weight:bold;">Private &bull; Invite-Only</span> &bull; Audience: Florida Patients &bull; <a href="https://digitalcreatorassets-source.github.io/creatormedialab/?pub=dispensary_deals" target="_blank" style="color:#10b981;font-weight:bold;">Portal</a>';
      }
      
      const tabThreadBtn = document.getElementById('tab-nl-thread');
      if (tabThreadBtn) {
        tabThreadBtn.innerText = (pubId === 'creator_pulse') ? '🐦 Twitter/X Viral Thread (@creatorpulselab)' : '🐦 Twitter/X Viral Thread (@TheCreatorAsset)';
      }
      const threadHeader = document.getElementById('nl-thread-channel-name');
      if (threadHeader) {
        threadHeader.innerHTML = (pubId === 'creator_pulse') ? '🐦 Twitter/X Viral Thread &bull; Channel: @creatorpulselab' : '🐦 Twitter/X Viral Thread &bull; Channel: @TheCreatorAsset';
      }
    }

    // Refresh whichever tab is active
    if (this.currentNewsletterTab === 'preview') {
      this.refreshNewsletterPreview();
    } else if (this.currentNewsletterTab === 'thread') {
      this.fetchTwitterThread();
    } else if (this.currentNewsletterTab === 'blog') {
      this.fetchNewsletterBlogMarkdown();
    }
  }

  async refreshNewsletterConfig() {
    try {
      const res = await fetch('/api/newsletter/config');
      const data = await res.json();
      if (data.status === 'ok') {
        this.renderSubscribers(data.config?.recipients_list || []);
        this.populateNewsletterElements(data.config?.elements || {});
        if (data.execution) {
          this.renderNewsletterStatus(data.execution);
        }
      }
    } catch (err) {
      console.error('Failed to load newsletter config:', err);
    }
  }

  renderSubscribers(recipients) {
    const badge = document.getElementById('subscriber-count-badge');
    if (badge) badge.innerText = `${recipients.length} Active`;

    const list = document.getElementById('subscribers-pill-list');
    if (!list) return;

    if (!recipients.length) {
      list.innerHTML = '<div style="font-size:11px;color:var(--text-dim);text-align:center;padding:8px;">No subscribers yet. Add an email above.</div>';
      return;
    }

    list.innerHTML = recipients.map(email => `
      <div class="sub-pill-item">
        <span>✉️ ${email}</span>
        <button class="sub-pill-remove" onclick="window.workBaysManager.removeSubscriber('${email}')" title="Remove subscriber">&times;</button>
      </div>
    `).join('');
  }

  populateNewsletterElements(elem) {
    if (elem.header_title) {
      const chk = document.getElementById('elem-header-enabled');
      const txt = document.getElementById('elem-header-title');
      if (chk) chk.checked = elem.header_title.enabled !== false;
      if (txt && elem.header_title.title) txt.value = elem.header_title.title;
    }
    if (elem.intro_note) {
      const chk = document.getElementById('elem-intro-enabled');
      const txt = document.getElementById('elem-intro-text');
      if (chk) chk.checked = elem.intro_note.enabled !== false;
      if (txt && elem.intro_note.text) txt.value = elem.intro_note.text;
    }
    if (elem.promo_banner) {
      const chk = document.getElementById('elem-promo-enabled');
      const head = document.getElementById('elem-promo-headline');
      const url = document.getElementById('elem-promo-url');
      if (chk) chk.checked = elem.promo_banner.enabled !== false;
      if (head && elem.promo_banner.headline) head.value = elem.promo_banner.headline;
      if (url && elem.promo_banner.button_url) url.value = elem.promo_banner.button_url;
    }
    if (elem.curator_tip) {
      const chk = document.getElementById('elem-tip-enabled');
      const title = document.getElementById('elem-tip-title');
      const text = document.getElementById('elem-tip-text');
      if (chk) chk.checked = elem.curator_tip.enabled !== false;
      if (title && elem.curator_tip.title) title.value = elem.curator_tip.title;
      if (text && elem.curator_tip.text) text.value = elem.curator_tip.text;
    }
  }

  async addSubscriber() {
    const input = document.getElementById('new-subscriber-email');
    if (!input || !input.value.trim()) return;
    const email = input.value.trim();

    try {
      const res = await fetch('/api/newsletter/subscribers/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (data.success) {
        input.value = '';
        this.renderSubscribers(data.recipients);
      } else {
        alert(data.error || 'Failed to add subscriber');
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    }
  }

  async removeSubscriber(email) {
    if (!confirm(`Remove ${email} from daily morning dispatch?`)) return;

    try {
      const res = await fetch('/api/newsletter/subscribers/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (data.success) {
        this.renderSubscribers(data.recipients);
      } else {
        alert(data.error || 'Failed to remove subscriber');
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    }
  }

  async saveNewsletterElements() {
    const payload = {
      elements: {
        header_title: {
          enabled: document.getElementById('elem-header-enabled')?.checked,
          title: document.getElementById('elem-header-title')?.value
        },
        intro_note: {
          enabled: document.getElementById('elem-intro-enabled')?.checked,
          text: document.getElementById('elem-intro-text')?.value
        },
        promo_banner: {
          enabled: document.getElementById('elem-promo-enabled')?.checked,
          headline: document.getElementById('elem-promo-headline')?.value,
          button_url: document.getElementById('elem-promo-url')?.value
        },
        curator_tip: {
          enabled: document.getElementById('elem-tip-enabled')?.checked,
          title: document.getElementById('elem-tip-title')?.value,
          text: document.getElementById('elem-tip-text')?.value
        }
      },
      categories: ['flower', 'vape', 'edible', 'concentrate', 'pre-roll'].filter(c => {
        const el = document.getElementById(`cat-${c}`);
        return el ? el.checked : true;
      }),
      min_discount_pct: parseInt(document.getElementById('slider-min-discount')?.value || '20', 10)
    };

    try {
      const res = await fetch('/api/newsletter/elements/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'ok') {
        this.refreshNewsletterPreview();
        alert('Newsletter modular layout saved successfully!');
      }
    } catch (e) {
      alert(`Error saving layout: ${e.message}`);
    }
  }

  async sendTestEmail() {
    const pub = this.selectedPublication || 'creator_pulse';
    const recipient = 'careypmediagroup@gmail.com';
    const btn = event?.currentTarget;
    if (btn) btn.innerText = '⏳ Sending Test...';

    try {
      const res = await fetch('/api/newsletter/send-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pub, recipient })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Test email for '${pub}' delivered to ${recipient}! Check your inbox.`);
      } else {
        alert(`Failed to send test email: ${data.error || 'Unknown error'}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      if (btn) btn.innerText = '✉️ Send Test to Inbox';
    }
  }

  async triggerNewsletterDispatch() {
    try {
      const res = await fetch('/api/newsletter/run', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        this.setNewsletterTab('logs');
        this.pollNewsletterLogs();
      }
    } catch (e) {
      alert(`Error starting dispatch: ${e.message}`);
    }
  }

  setNewsletterTab(tab) {
    this.currentNewsletterTab = tab;
    ['preview', 'thread', 'blog', 'logs'].forEach(t => {
      const btn = document.getElementById(`tab-nl-${t}`);
      const pane = document.getElementById(`nl-pane-${t}`);
      if (btn) btn.classList.toggle('active', t === tab);
      if (pane) pane.style.display = (t === tab) ? 'block' : 'none';
    });

    const copyBlogBtn = document.getElementById('btn-copy-nl-blog');
    const copyThreadBtn = document.getElementById('btn-copy-nl-thread');
    if (copyBlogBtn) copyBlogBtn.style.display = (tab === 'blog') ? 'block' : 'none';
    if (copyThreadBtn) copyThreadBtn.style.display = (tab === 'thread') ? 'block' : 'none';

    if (tab === 'preview') {
      this.refreshNewsletterPreview();
    } else if (tab === 'thread') {
      this.fetchTwitterThread();
    } else if (tab === 'blog') {
      this.fetchNewsletterBlogMarkdown();
    } else if (tab === 'logs') {
      this.pollNewsletterLogs();
    }
  }

  refreshNewsletterPreview() {
    const frame = document.getElementById('newsletter-preview-frame');
    if (frame) {
      const pub = this.selectedPublication || 'creator_pulse';
      frame.src = `/api/newsletter/preview?pub=${pub}&t=${Date.now()}`;
    }
  }

  async fetchTwitterThread() {
    const container = document.getElementById('nl-thread-cards-container');
    if (!container) return;
    const pub = this.selectedPublication || 'creator_pulse';
    container.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:12px;">Loading thread for @TheCreatorAsset...</div>';

    try {
      const res = await fetch(`/api/newsletter/thread?pub=${pub}`);
      const data = await res.json();
      if (data.status === 'ok' && data.thread) {
        this.currentTwitterThreadList = data.thread;
        this.renderTwitterCards(data.thread);
      }
    } catch (e) {
      container.innerHTML = `<div style="color:#ef4444;font-size:12px;">Error loading thread: ${e.message}</div>`;
    }
  }

  renderTwitterCards(tweets) {
    const container = document.getElementById('nl-thread-cards-container');
    if (!container) return;

    container.innerHTML = tweets.map((tweet, idx) => {
      const charCount = tweet.length;
      const countColor = charCount > 280 ? '#ef4444' : '#10b981';
      return `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(29,161,242,0.25); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 11px; font-weight: 800; color: #1da1f2; font-family: var(--font-mono);">TWEET ${idx + 1} OF ${tweets.length}</span>
            <div style="display: flex; gap: 10px; align-items: center;">
              <span style="font-size: 10.5px; color: ${countColor}; font-family: var(--font-mono);">${charCount}/280 chars</span>
              <button class="btn-cyber" onclick="window.workBaysManager.copySingleTweet(${idx})" style="font-size: 10px; padding: 3px 8px; border-color: rgba(29,161,242,0.4); color: #1da1f2;">
                📋 Copy
              </button>
              <a href="https://twitter.com/intent/tweet?text=${encodeURIComponent(tweet)}" target="_blank" class="btn-cyber" style="font-size: 10px; padding: 3px 8px; border-color: #1da1f2; color: #fff; background: rgba(29,161,242,0.25); text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                𝕏 Post
              </a>
            </div>
          </div>
          <div style="font-size: 12.5px; line-height: 1.5; color: #e2e8f0; white-space: pre-wrap; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">${tweet.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
        </div>
      `;
    }).join('');
  }

  copySingleTweet(index) {
    if (this.currentTwitterThreadList && this.currentTwitterThreadList[index]) {
      navigator.clipboard.writeText(this.currentTwitterThreadList[index]);
      alert(`Tweet ${index + 1} copied to clipboard! Ready to paste into Twitter/X.`);
    }
  }

  copyTwitterThread() {
    if (this.currentTwitterThreadList && this.currentTwitterThreadList.length) {
      const formatted = this.currentTwitterThreadList.join('\n\n---\n\n');
      navigator.clipboard.writeText(formatted);
      const handle = (this.selectedPublication === 'creator_pulse') ? '@creatorpulselab' : '@TheCreatorAsset';
      alert(`Entire viral thread copied to clipboard! Ready to post sequentially to ${handle}.`);
    }
  }

  async publishTwitterThread() {
    if (!this.currentTwitterThreadList || !this.currentTwitterThreadList.length) {
      alert('No thread content available to publish.');
      return;
    }
    const handle = (this.selectedPublication === 'creator_pulse') ? '@creatorpulselab' : '@TheCreatorAsset';
    const btn = document.getElementById('btn-auto-publish-thread');
    if (btn) btn.innerText = '⏳ Publishing to X...';

    try {
      const res = await fetch('/api/twitter/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          handle: handle,
          thread: this.currentTwitterThreadList
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`🎉 Success! Thread with ${data.tweet_count} tweets published to ${handle}!\n\nView live thread: ${data.thread_url}`);
        window.open(data.thread_url, '_blank');
      } else {
        alert(`Notice for ${handle}:\n${data.error}\n\n💡 Tip: You can also use the '𝕏 Post' button on each tweet card or copy the thread while setting up API keys.`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      if (btn) btn.innerText = '⚡ Auto-Publish Thread';
    }
  }

  async pollNewsletterLogs() {
    const pane = document.getElementById('nl-pane-logs');
    if (!pane) return;

    try {
      const res = await fetch('/api/newsletter/logs');
      const data = await res.json();
      if (data.recent_logs) {
        pane.innerText = data.recent_logs;
        pane.scrollTop = pane.scrollHeight;
      }
      this.renderNewsletterStatus(data);
    } catch (e) {
      console.error(e);
    }
  }

  renderNewsletterStatus(exec) {
    const pill = document.getElementById('newsletter-status-pill');
    if (!pill) return;
    if (exec.status === 'running') {
      pill.innerHTML = '<span class="pulse-dot" style="background:#f59e0b;"></span> DISPATCHING LIVE...';
      pill.style.color = '#f59e0b';
      pill.style.borderColor = '#f59e0b';
    } else if (exec.status === 'completed') {
      pill.innerHTML = '<span class="pulse-dot" style="background:#10b981;"></span> LAST RUN SUCCESSFUL';
      pill.style.color = '#10b981';
      pill.style.borderColor = '#10b981';
    } else if (exec.status === 'error') {
      pill.innerHTML = '<span class="pulse-dot" style="background:#ef4444;"></span> DISPATCH ENCOUNTERED ERROR';
      pill.style.color = '#ef4444';
      pill.style.borderColor = '#ef4444';
    } else {
      pill.innerHTML = '<span class="pulse-dot" style="background:#10b981;"></span> Dispatch Radar Live';
      pill.style.color = '#10b981';
      pill.style.borderColor = '#10b981';
    }
  }

  async fetchNewsletterBlogMarkdown() {
    const pane = document.getElementById('nl-pane-blog');
    if (!pane) return;
    const pub = this.selectedPublication || 'creator_pulse';
    try {
      const res = await fetch(`/api/newsletter/blog-post?pub=${pub}`);
      const data = await res.json();
      if (data.status === 'ok') {
        pane.innerText = data.markdown;
        this.currentBlogMarkdown = data.markdown;
      }
    } catch (e) {
      pane.innerText = `Error loading blog post: ${e.message}`;
    }
  }

  copyNewsletterBlogMarkdown() {
    if (this.currentBlogMarkdown) {
      navigator.clipboard.writeText(this.currentBlogMarkdown);
      alert('Morning blog post Markdown copied to clipboard!');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.workBaysManager = new WorkBaysManager();
});
