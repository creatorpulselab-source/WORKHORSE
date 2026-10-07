/* =========================================================================
   Prism — AI Social Media Content Studio — app.js
   ========================================================================= */

const MODES = [
  { id: 'post',       label: 'Social Caption',    desc: 'IG · TikTok · FB · X', icon: '✍️', color: '#4F46E5', rgb: '79,70,229' },
  { id: 'flux_image', label: 'Flux Image Prompt', desc: 'Flux.1 / Flux.2 ComfyUI', icon: '🎨', color: '#7C3AED', rgb: '124,58,237' },
  { id: 'wan_video',  label: 'WAN Video Prompt',  desc: 'WAN2.1 / WAN2.2 clip',  icon: '🎬', color: '#0EA5E9', rgb: '14,165,233' },
  { id: 'pose_series',label: 'Pose Series',       desc: '6 variations for sets', icon: '📸', color: '#F59E0B', rgb: '245,158,11' },  { id: 'thread',     label: 'X Thread',          desc: '5-tweet thread from image', icon: '🧵', color: '#1DA1F2', rgb: '29,161,242' },];
const ALL_MODE = { id: 'all', label: 'Generate All', desc: 'Caption + prompts + poses', icon: '⚡', color: '#4F46E5', rgb: '79,70,229' };

// Fixed display order for the results carousel, independent of which mode's AI call
// finishes first (captions always lead, pose series always trails).
const RESULT_ORDER = ['post', 'flux_image', 'wan_video', 'thread', 'hashtag_set', 'pose_series'];
function _resultOrderIndex(mode) { const i = RESULT_ORDER.indexOf(mode); return i === -1 ? RESULT_ORDER.length : i; }

const MODE_META = {
  post:        { label: 'Social Caption',    icon: '✍️', color: '#4F46E5', rgb: '79,70,229'  },
  flux_image:  { label: 'Flux Image Prompt', icon: '🎨', color: '#7C3AED', rgb: '124,58,237' },
  wan_video:   { label: 'WAN Video Prompt',  icon: '🎬', color: '#0EA5E9', rgb: '14,165,233'  },
  pose_series: { label: 'Pose Series',       icon: '📸', color: '#F59E0B', rgb: '245,158,11' },  thread:      { label: 'X Thread',          icon: '🧵', color: '#1DA1F2', rgb: '29,161,242' },
  hashtag_set: { label: 'Hashtag Set',       icon: '🏷️', color: '#10B981', rgb: '16,185,129' },
};

const CONTENT_TYPE_META = {
  creator: { note: 'Person-focused captions and pose series',           poseLabel: '\uD83D\uDCF8 Pose Series',      poseDesc: '6 pose variations for photo sets' },
  ugc:     { note: 'Person + product \u2014 product maintained in all shots', poseLabel: '\uD83E\uDD1D UGC Angles',       poseDesc: '6 variations keeping product featured' },
  product: { note: 'Product-focused captions and photography angles',   poseLabel: '\uD83D\uDECD\uFE0F Product Angles',   poseDesc: '6 professional product angles' },
  general: { note: 'Works with any image \u2014 food, pets, landscapes, objects', poseLabel: '\uD83D\uDCF8 Scene Variations', poseDesc: '6 composition variations' },
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state = {
  imageB64: null, fileName: '',
  mode: 'all', platform: 'general', hashtags: true,
  loading: false, results: null,
  language: 'en', variants: false, style: '', hashtagSet: false,
  contentType: 'creator',
  searchBrand: false,
  brandUrl: '',
  autoPoseImages: true,
  // video
  isVideo: false, videoFile: null, videoObjectURL: null,
  transcribeAudio: true,
  // Distribution & Tags — hashtags selected from feature-page hubs, appended to the caption
  hubHashtags: [],
  selectedHubs: [],
};

let currentUser = { username: '', is_admin: false, settings: { enabled_modes: ['flux_image', 'wan_video', 'pose_series'], gender: 'neutral' } };

const $ = (id) => document.getElementById(id);
const show = (id) => { const el = $(id); if (el) el.style.display = ''; };
const hide = (id) => { const el = $(id); if (el) el.style.display = 'none'; };

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
  await loadWhoami();
  buildModeGrid();
  setupUpload();
  setupKeyboard();
  loadSettings().then(fillSettingsForm);
  loadUsage();
  registerServiceWorker();
});

async function loadWhoami() {
  try {
    const res = await fetch('/api/whoami');
    if (res.ok) currentUser = await res.json();
  } catch {}
  const gearBtn = document.getElementById('btn-settings');
  if (gearBtn) gearBtn.style.display = currentUser.is_admin ? '' : 'none';
}

// ---------------------------------------------------------------------------
// Dark mode
// ---------------------------------------------------------------------------
const MOON_ICON_PATH = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
const SUN_ICON_PATH = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('que_theme', theme); } catch {}
  const metaTheme = document.getElementById('meta-theme-color');
  if (metaTheme) metaTheme.setAttribute('content', theme === 'dark' ? '#1A1D23' : '#4F46E5');
  const icon = $('dark-mode-icon');
  const btn = $('btn-dark-mode');
  if (icon) icon.innerHTML = theme === 'dark' ? SUN_ICON_PATH : MOON_ICON_PATH;
  if (btn) btn.title = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
}

function toggleDarkMode() {
  const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// ---------------------------------------------------------------------------
// Mode grid
// ---------------------------------------------------------------------------
function buildModeGrid() {
  const grid = $('mode-grid');
  grid.innerHTML = '';
  const enabled = currentUser.settings?.enabled_modes || ['flux_image', 'wan_video', 'pose_series'];

  // In video mode filter to caption/flux/wan only — poses and threads don't apply
  const VIDEO_MODES = new Set(['post', 'flux_image', 'wan_video']);

  MODES.forEach((m) => {
    if (m.id !== 'post' && !enabled.includes(m.id)) return;
    if (state.isVideo && !VIDEO_MODES.has(m.id)) return;
    // Dynamically update pose_series label/desc based on content type
    let displayM = m;
    if (m.id === 'pose_series') {
      const ctMeta = CONTENT_TYPE_META[state.contentType] || CONTENT_TYPE_META.creator;
      displayM = { ...m, label: ctMeta.poseLabel.replace(/^[^\s]+\s/, '').trim(), desc: ctMeta.poseDesc, icon: ctMeta.poseLabel.split(' ')[0] };
    }
    const btn = document.createElement('button');
    btn.className = 'mode-btn' + (state.mode === m.id ? ' active' : '');
    btn.dataset.mode = m.id;
    btn.style.setProperty('--mode-color', displayM.color);
    btn.style.setProperty('--mode-color-rgb', displayM.rgb);
    btn.innerHTML = `<span class="mode-btn-icon">${displayM.icon}</span><span class="mode-btn-label">${displayM.label}</span><span class="mode-btn-desc">${displayM.desc}</span>`;
    btn.onclick = () => setMode(m.id);
    grid.appendChild(btn);
  });

  const activeCount = MODES.filter(m => m.id === 'post' || enabled.includes(m.id)).length;
  if (activeCount > 1) {
    const allBtn = document.createElement('button');
    allBtn.className = 'mode-btn mode-btn-all' + (state.mode === 'all' ? ' active' : '');
    allBtn.dataset.mode = 'all';
    allBtn.style.setProperty('--mode-color', ALL_MODE.color);
    allBtn.style.setProperty('--mode-color-rgb', ALL_MODE.rgb);
    allBtn.innerHTML = `<span class="mode-btn-icon">${ALL_MODE.icon}</span><div class="mode-btn-texts"><span class="mode-btn-label">${ALL_MODE.label}</span><span class="mode-btn-desc">${ALL_MODE.desc}</span></div>`;
    allBtn.onclick = () => setMode('all');
    grid.appendChild(allBtn);
  }
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
}

// ---------------------------------------------------------------------------
// Platform
// ---------------------------------------------------------------------------
function setPlatform(platform, btn) {
  state.platform = platform;
  document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function setContentType(type, btn) {
  state.contentType = type;
  document.querySelectorAll('.ct-card').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const meta = CONTENT_TYPE_META[type] || CONTENT_TYPE_META.creator;
  const note = document.getElementById('content-type-note');
  if (note) note.textContent = meta.note;
  // Change accent + background gradient to reflect content type
  const ctColors   = { creator: '#4F46E5', ugc: '#059669', product: '#D97706', general: '#0284C7' };
  const ctRGB      = { creator: '79,70,229', ugc: '5,150,105', product: '217,119,6', general: '2,132,199' };
  const bgGradients = {
    creator: 'radial-gradient(ellipse at 30% 0%, rgba(79,70,229,0.08) 0%, var(--bg) 60%)',
    ugc:     'radial-gradient(ellipse at 30% 0%, rgba(5,150,105,0.08) 0%, var(--bg) 60%)',
    product: 'radial-gradient(ellipse at 30% 0%, rgba(217,119,6,0.08) 0%, var(--bg) 60%)',
    general: 'radial-gradient(ellipse at 30% 0%, rgba(2,132,199,0.08) 0%, var(--bg) 60%)',
  };
  const color = ctColors[type] || '#4F46E5';
  document.documentElement.style.setProperty('--ct-accent', color);
  document.documentElement.style.setProperty('--ct-accent-rgb', ctRGB[type] || '79,70,229');
  document.documentElement.style.setProperty('--ct-bg-gradient', bgGradients[type] || 'var(--bg)');
  if (note) note.style.color = color;
  // Show brand search toggle only for product/ugc
  const brandRow = $('brand-search-row');
  const urlRow = $('brand-url-row');
  if (brandRow) {
    const isProductUGC = type === 'product' || type === 'ugc';
    brandRow.style.display = isProductUGC ? '' : 'none';
    if (urlRow) urlRow.style.display = isProductUGC ? '' : 'none';
    state.searchBrand = isProductUGC;
    if (!isProductUGC) { state.brandUrl = ''; const ui = $('brand-url-input'); if (ui) ui.value = ''; }
    const tog = $('brand-search-toggle');
    if (tog) tog.checked = state.searchBrand;
  }
  buildModeGrid();
}

function setStyle(style, btn) {
  state.style = style;
  document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------
function setupUpload() {
  const zone = $('upload-zone');
  const input = $('file-input');
  zone.addEventListener('click', (e) => { if (e.target.tagName !== 'BUTTON') input.click(); });
  input.addEventListener('change', () => {
    const f = input.files[0];
    if (f) { if (f.type.startsWith('video/')) handleVideoFile(f); else handleFile(f); }
    input.value = '';
  });
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (!f) return;
    if (f.type.startsWith('video/')) handleVideoFile(f);
    else if (f.type.startsWith('image/')) handleFile(f);
    else toast('Please drop an image or video file', 'error');
  });
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (!f || state.loading) return;
    if (f.type.startsWith('video/')) handleVideoFile(f);
    else if (f.type.startsWith('image/') && !state.loading) handleFile(f);
  });
}

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    state.imageB64 = e.target.result;
    state.isVideo = false;
    state.videoFile = null;
    state.poseImagePrefetch = {};
    state._cachedPoseSeriesText = null;
    state._cachedPoseSeriesContentType = null;
    if (state.videoObjectURL) { URL.revokeObjectURL(state.videoObjectURL); state.videoObjectURL = null; }
    state.fileName = file.name;
    $('preview-img').src = state.imageB64;
    $('preview-img').style.display = '';
    $('preview-video').style.display = 'none';
    $('preview-name').textContent = file.name;
    buildModeGrid();
    const ts = $('video-audio-section'); if (ts) ts.style.display = 'none';
    hide('upload-zone');
    $('workspace').style.display = 'flex';
    hide('results');
    state.results = null;
    wizToStep(1);
    // Pre-warm description cache while user picks settings
    prefetchDescription(state.imageB64);
  };
  reader.readAsDataURL(file);
}

function handleVideoFile(file) {
  state.videoFile = file;
  state.imageB64 = null;
  state.isVideo = true;
  state.fileName = file.name;
  if (state.videoObjectURL) URL.revokeObjectURL(state.videoObjectURL);
  state.videoObjectURL = URL.createObjectURL(file);
  $('preview-video').src = state.videoObjectURL;
  $('preview-video').style.display = '';
  $('preview-img').style.display = 'none';
  $('preview-img').src = '';
  $('preview-name').textContent = file.name;
  // Auto-select 'post' if current mode isn't valid for video
  const videoModes = new Set(['post', 'flux_image', 'wan_video', 'all']);
  if (!videoModes.has(state.mode)) setMode('post');
  buildModeGrid();
  const ts = $('video-audio-section'); if (ts) ts.style.display = '';
  hide('upload-zone');
  $('workspace').style.display = 'flex';
  hide('results');
  state.results = null;
  wizToStep(1);
  toast('Video loaded — select a mode and Generate', 'success');
}

function clearImage() {
  if (state.videoObjectURL) { URL.revokeObjectURL(state.videoObjectURL); state.videoObjectURL = null; }
  state.imageB64 = null; state.fileName = ''; state.results = null;
  state.videoFile = null; state.isVideo = false;
  show('upload-zone'); hide('workspace');
  $('workspace').style.display = 'none';
  $('preview-img').src = ''; $('preview-img').style.display = '';
  $('preview-video').src = ''; $('preview-video').style.display = 'none';
  const ts = $('video-audio-section'); if (ts) ts.style.display = 'none';
  $('results-carousel').innerHTML = '';
  _wizStep = 1;
}

// ---------------------------------------------------------------------------
// Wizard navigation
// ---------------------------------------------------------------------------
let _wizStep = 1;
let _wizDirection = 1; // 1 = forward, -1 = back

function wizToStep(n) {
  // Step 4 ("Review") is a pop-out modal now, not a wizard page — open it as an
  // overlay instead of navigating (there is no content behind #wiz-page-4 anymore).
  if (n === 4) { openReviewModal(); return; }
  // Jumping to any real step (e.g. via an "Edit →" row inside the review modal)
  // should dismiss the review overlay so it doesn't linger on top of the page.
  hide('review-modal');

  const prev = _wizStep;
  _wizDirection = n >= prev ? 1 : -1;
  _wizStep = n;

  // Slide transition — show target, hide others
  for (let i = 1; i <= 5; i++) {
    const pg = $('wiz-page-' + i);
    if (!pg) continue;
    pg.classList.remove('slide-in-right', 'slide-in-left');
    if (i === n) {
      pg.style.display = 'flex';
      if (prev !== n) pg.classList.add(_wizDirection > 0 ? 'slide-in-right' : 'slide-in-left');
    } else {
      pg.style.display = 'none';
    }
  }

  // Update progress bar
  const progWidths = { 1: '25%', 2: '50%', 3: '75%', 4: '100%', 5: '100%' };
  const progEl = $('wiz-progress');
  if (progEl) progEl.style.width = progWidths[n] || '25%';

  // Update step dots
  const dots = document.querySelectorAll('.wiz-step-dot');
  dots.forEach((dot, i) => {
    dot.classList.remove('active', 'done');
    if (i + 1 === n && n <= 4) dot.classList.add('active');
    else if (i + 1 < n) dot.classList.add('done');
  });
  // Hide dots on step 5 (results)
  const dotsRow = $('wiz-step-dots');
  if (dotsRow) dotsRow.style.display = n >= 5 ? 'none' : '';

  // Hide the source-image preview on the results step — it otherwise stays
  // pinned at ~25vh/250px and starves the results carousel of vertical space,
  // making multi-mode results (and multi-pose series) look cut off after one item.
  const progBar = $('wiz-progress')?.parentElement;
  const previewCard = $('wiz-preview-card');
  if (previewCard) {
    previewCard.style.display = n >= 5 ? 'none' : '';
    // Steps 2-3: shrink the full preview down to a small thumbnail bar so the
    // step's own controls (platform buttons, toggles, textarea) aren't pushed
    // below the fold on phones. Step 1 keeps the full preview to confirm the
    // upload; the review screen (step 4) is a separate modal with its own thumb.
    previewCard.classList.toggle('compact', n === 2 || n === 3);
  }
  if (progBar) progBar.style.display = n >= 5 ? 'none' : '';

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function wizNext() {
  // Leaving step 1: content type is now finalized, so this is the earliest safe point
  // to start the pose series (text depends on content type, chosen right here).
  if (_wizStep === 1) prefetchPoseSeriesText();
  if (_wizStep < 4) wizToStep(_wizStep + 1);
}
function wizBack() { if (_wizStep > 1) wizToStep(_wizStep - 1); }

// Kicks off the pose_series text generation as soon as the user confirms content type on
// step 1 (before platform/style/etc are even chosen), so it's likely already done by the
// time they reach Generate. Gated by the auto-pose toggle since it always costs an AI call.
function prefetchPoseSeriesText() {
  if (!state.autoPoseImages || !state.imageB64 || state.isVideo) return;
  if (state._cachedPoseSeriesText && state._cachedPoseSeriesContentType === state.contentType) return; // already have it for this content type
  if (state._poseTextPrefetchInFlight) return;
  state._poseTextPrefetchInFlight = true;
  const contentTypeAtRequest = state.contentType;
  fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_b64: state.imageB64, mode: 'pose_series', content_type: contentTypeAtRequest }),
  }).then(async (res) => {
    if (!res.ok) return;
    const data = await res.json();
    const text = data.results?.pose_series;
    if (!text) return;
    state._cachedPoseSeriesText = text;
    state._cachedPoseSeriesContentType = contentTypeAtRequest;
    prefetchPoseSeriesImages(text);
  }).catch(() => {}).finally(() => { state._poseTextPrefetchInFlight = false; });
}

function openReviewModal() {
  buildReviewGrid();
  show('review-modal');
}

function closeReviewModal() {
  hide('review-modal');
}

function buildReviewGrid() {
  const list = $('review-modal-body'); if (!list) return;
  const CT = { creator:'👤 Creator', ugc:'🤝 UGC', product:'🛍️ Product', general:'📸 General' };
  const STYLE = { '':'✨ Auto', hook:'🎣 Hook', story:'📖 Story', question:'❓ Question', hot_take:'🔥 Hot Take', tips:'💡 Tips', bts:'🎬 BTS', soft_sell:'🛍️ Soft Sell', relatable:'🫂 Relatable' };
  const PLAT = { general:'🌐 General', instagram:'📷 Instagram', tiktok:'🎵 TikTok', facebook:'👥 Facebook', twitter:'𝕏 Twitter' };
  const modeLabel = state.mode === 'all' ? '⚡ Generate All' : (MODE_META[state.mode]?.label || state.mode);
  const opts = [state.hashtags ? '📌 Hashtags' : null, state.hashtagSet ? '🏷️ 30-tag set' : null, state.variants ? '✨ 3 variants' : null, state.searchBrand ? '🔍 Brand search' : null].filter(Boolean);
  const ctx = ($('caption-context')?.value || '').trim();

  // Build media preview
  let mediaHtml = '';
  if (state.isVideo && state.videoObjectURL) {
    mediaHtml = `<div class="review-media-preview"><video src="${state.videoObjectURL}" muted playsinline style="pointer-events:none"></video><div class="review-media-overlay"><span class="review-media-name">${escHtml(state.fileName)}</span><span class="review-media-badge">🎬 Video</span></div></div>`;
  } else if (state.imageB64) {
    mediaHtml = `<div class="review-media-preview"><img src="${state.imageB64}" alt="Preview"><div class="review-media-overlay"><span class="review-media-name">${escHtml(state.fileName)}</span><span class="review-media-badge">${CT[state.contentType] || '📸'}</span></div></div>`;
  }

  list.innerHTML = `
    ${mediaHtml}
    <div class="review-category" onclick="wizToStep(1)">
      <div class="review-category-hdr">🎨 Content Setup <span style="margin-left:auto;color:var(--ct-accent,var(--accent));text-transform:none;font-size:0.78rem">Edit →</span></div>
      <div class="review-item"><span class="review-item-label">Content Type</span><span class="review-item-value">${CT[state.contentType] || state.contentType}</span></div>
    </div>
    
    <div class="review-category" onclick="wizToStep(2)">
      <div class="review-category-hdr">⚡ Generation Mode <span style="margin-left:auto;color:var(--ct-accent,var(--accent));text-transform:none;font-size:0.78rem">Edit →</span></div>
      <div class="review-item"><span class="review-item-label">Mode</span><span class="review-item-value">${modeLabel}</span></div>
      <div class="review-item"><span class="review-item-label">Platform</span><span class="review-item-value">${PLAT[state.platform] || state.platform}</span></div>
    </div>
    
    <div class="review-category" onclick="wizToStep(3)">
      <div class="review-category-hdr">💨 Refinements <span style="margin-left:auto;color:var(--ct-accent,var(--accent));text-transform:none;font-size:0.78rem">Edit →</span></div>
      <div class="review-item"><span class="review-item-label">Style</span><span class="review-item-value">${STYLE[state.style] || '✨ Auto'}</span></div>
      <div class="review-item"><span class="review-item-label">Language</span><span class="review-item-value">${$('lang-select')?.options[$('lang-select')?.selectedIndex]?.text || 'English'}</span></div>
      ${opts.length ? `<div class="review-item"><span class="review-item-label">Options</span><span class="review-item-value">${opts.join(' · ')}</span></div>` : ''}
      ${ctx ? `<div class="review-item"><span class="review-item-label">Context</span><span class="review-item-value">${escHtml(ctx)}</span></div>` : ''}
    </div>
  `;
}

// Fire-and-forget: pre-warms description cache so Generate All is instant
function prefetchDescription(imageB64) {
  fetch('/api/prefetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_b64: imageB64 }),
  }).catch(() => {}); // silent fail — this is just a warm-up
}

// ---------------------------------------------------------------------------
// Generate (streaming)
// ---------------------------------------------------------------------------
async function generate() {
  if (!state.imageB64 && !state.videoFile) { toast('Upload an image or video first', 'error'); return; }
  if (state.loading) return;
  if (state.isVideo) { await generateVideo(); return; }
  setLoading(true);
  const poseTextReady = state._cachedPoseSeriesText && state._cachedPoseSeriesContentType === state.contentType;
  const payload = {
    image_b64: state.imageB64, mode: state.mode, platform: state.platform,
    hashtags: state.hashtags, guidance: ($('caption-context')?.value || '').trim(),
    language: state.language, variants: state.variants, style: state.style,
    hashtag_set: state.hashtagSet, content_type: state.contentType,
    search_brand: state.searchBrand,
    brand_url: state.brandUrl,
    hub_hashtags: state.hubHashtags,
    cached_pose_series: poseTextReady ? state._cachedPoseSeriesText : '',
  };
  // Stream results — text appears token-by-token so users don't stare at a blank spinner
  const streamingCards = {};  // mode → DOM card
  const streamingTexts = {};  // mode → accumulated text
  state.results = {};
  try {
    const res = await fetch('/api/generate-stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    $('results-carousel').innerHTML = '';
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let ev; try { ev = JSON.parse(line.slice(6)); } catch { continue; }
        if (ev.type === 'mode_start') {
          streamingTexts[ev.mode] = '';
          streamingCards[ev.mode] = _createStreamCard(ev.mode);
          _insertResultSlide($('results-carousel'), streamingCards[ev.mode], ev.mode);
        } else if (ev.type === 'token') {
          streamingTexts[ev.mode] = (streamingTexts[ev.mode] || '') + ev.text;
          _updateStreamCard(streamingCards[ev.mode], streamingTexts[ev.mode]);
        } else if (ev.type === 'mode_done') {
          _finalizeStreamCard(streamingCards[ev.mode], ev.mode, streamingTexts[ev.mode]);
          state.results[ev.mode] = streamingTexts[ev.mode];
          // Pose Series / UGC Angles / etc: start rendering all 6 pose images now, in the
          // background, so they're likely already done by the time the user taps "Image".
          if (ev.mode === 'pose_series') prefetchPoseSeriesImages(streamingTexts[ev.mode]);
        } else if (ev.type === 'mode_error') {
          _failStreamCard(streamingCards[ev.mode], ev.mode, ev.message);
        } else if (ev.type === 'done') {
          wizToStep(5);
          setTimeout(activateCarousel, 50); // slight delay so DOM is ready
          toast('Generated!', 'success');
          loadUsage();
        } else if (ev.type === 'error') {
          toast(`Error: ${ev.message}`, 'error');
        }
      }
    }
  } catch (err) {
    toast(`Error: ${err.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

function _createStreamCard(mode) {
  const meta = MODE_META[mode] || { label: mode.replace(/_/g,' '), icon: '⚡', color: '#4F46E5', rgb: '79,70,229' };
  
  const slide = document.createElement('div');
  slide.className = 'carousel-slide';
  slide.dataset.mode = mode;
  
  const card = document.createElement('div');
  card.className = 'result-card';
  card.style.setProperty('--result-accent', meta.color);
  card.innerHTML = `
    <div class="result-card-hdr">
      <span class="result-badge" style="--badge-color:${meta.color};--badge-rgb:${meta.rgb}">${meta.icon} ${meta.label}</span>
      <div class="result-card-actions"><span style="font-size:0.72rem;color:var(--accent);animation:_pulse 1s ease-in-out infinite">Generating…</span></div>
    </div>
    <div class="result-body"><div class="result-text _stream-text" style="white-space:pre-wrap;min-height:2em"></div></div>`;
    
  slide.appendChild(card);
  return slide;
}

// Keeps the carousel in RESULT_ORDER regardless of which mode's SSE events arrive first.
function _insertResultSlide(container, slide, mode) {
  if (!container) return;
  const idx = _resultOrderIndex(mode);
  const next = Array.from(container.children).find(el => _resultOrderIndex(el.dataset.mode) > idx);
  if (next) container.insertBefore(slide, next);
  else container.appendChild(slide);
}

function _updateStreamCard(card, text) {
  if (!card) return;
  const el = card.querySelector('._stream-text');
  if (el) {
    el.textContent = text;
    el.classList.add('_stream-cursor');
  }
}

function _finalizeStreamCard(slide, mode, text) {
  if (!slide) return;
  const card = slide.querySelector('.result-card') || slide;
  const meta = MODE_META[mode] || { label: mode.replace(/_/g,' '), icon: '⚡', color: '#4F46E5', rgb: '79,70,229' };
  let displayIcon = meta.icon, displayLabel = meta.label;
  if (mode === 'pose_series') {
    const ctMeta = CONTENT_TYPE_META[state.contentType] || CONTENT_TYPE_META.creator;
    const parts = ctMeta.poseLabel.split(' ');
    displayIcon = parts[0]; displayLabel = parts.slice(1).join(' ');
  }
  let bodyHtml;
  if (mode === 'pose_series') bodyHtml = renderPoseSeriesBody(text, meta.color);
  else if (mode === 'thread') bodyHtml = renderThreadBody(text);
  else if (mode === 'hashtag_set') bodyHtml = renderHashtagSetBody(text);
  else if (mode === 'post' && /\n---\n/.test(text)) bodyHtml = renderVariantsBody(text, meta.color);
  else {
    const isP = mode === 'flux_image' || mode === 'wan_video';
    const n = text.length;
    const cc = mode === 'post' ? `<div class="char-counter ${n>280?'over':n>240?'warn':''}">${n} characters</div>` : '';
    // Tap/click the text to pop it out in a full-size modal (also scrolls internally if long)
    bodyHtml = `<div class="result-body"><div class="result-text${isP?' prompt-style':''}" data-mode="${mode}" onclick="expandResultText(this, '${displayLabel}')">${escHtml(text)}</div>${cc}</div>`;
  }
  card.innerHTML = `<div class="result-card-hdr">
    <span class="result-badge" style="--badge-color:${meta.color};--badge-rgb:${meta.rgb}">${displayIcon} ${displayLabel}</span>
    <div class="result-card-actions">
      <button class="btn-regen-result" onclick="regenModeQUE('${mode}',this.closest('.result-card'))">&#8635;</button>
      <button class="btn-edit-result" onclick="toggleEdit(this,this.closest('.result-card'))">&#9998; Edit</button>
      ${mode === 'post' ? `<button class="btn-checklist-result" title="Pre-Publish Checklist" onclick="openChecklist()">\u{1F4CB}</button>` : ''}
      ${mode === 'post' ? `<button class="btn-checklist-result" title="Score Hook" onclick="scoreHook('${mode}', this)">\u{1FA9D}</button>` : ''}
      ${mode === 'post' ? `<button class="btn-checklist-result" title="Generate Alt Text" onclick="generateAltText(this)">\u{1F5BC}\uFE0F</button>` : ''}
      ${mode === 'post' ? `<button class="btn-checklist-result" title="Schedule This Post" onclick="openScheduleForResult('${mode}')">\u{1F4C5}</button>` : ''}
      <button class="btn-copy-result" onclick="copyResult(this,'${mode}')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button>
    </div>
  </div>${bodyHtml}`;
}

// A generation failure (provider error/timeout/quota) must never look like real
// content: no copy/edit/schedule actions, no char count \u2014 just the reason + retry.
function _failStreamCard(slide, mode, message) {
  if (!slide) return;
  const card = slide.querySelector('.result-card') || slide;
  const meta = MODE_META[mode] || { label: mode.replace(/_/g,' '), icon: '⚡', color: '#4F46E5', rgb: '79,70,229' };
  card.innerHTML = `<div class="result-card-hdr">
    <span class="result-badge" style="--badge-color:#EF4444;--badge-rgb:239,68,68">⚠️ ${meta.label} failed</span>
  </div>
  <div class="result-body">
    <div class="result-error-text">${escHtml(message)}</div>
    <button class="btn-retry-result" onclick="regenModeQUE('${mode}', this.closest('.result-card'))">&#8635; Retry</button>
  </div>`;
}

async function generateVideo() {
  setLoading(true, 'Analyzing video…');
  try {
    const fd = new FormData();
    fd.append('file', state.videoFile);
    // pose_series/thread not valid for video — fall back to post
    const vMode = (state.mode === 'pose_series' || state.mode === 'thread') ? 'post' : state.mode;
    fd.append('mode', vMode);
    fd.append('platform', state.platform);
    fd.append('hashtags', state.hashtags ? 'true' : 'false');
    fd.append('style', state.style || '');
    fd.append('content_type', state.contentType);
    fd.append('guidance', ($('caption-context')?.value || '').trim());
    fd.append('language', state.language);
    fd.append('transcribe_audio', state.transcribeAudio ? 'true' : 'false');
    fd.append('variants', state.variants ? 'true' : 'false');
    const res = await fetch('/api/video', { method: 'POST', body: fd });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    state.results = data.results;
    renderResults(data.results);
    wizToStep(5);
    setTimeout(activateCarousel, 50);
    const transcriptNote = data.transcript_available ? ' + audio transcript' : '';
    toast(`Video analyzed — ${data.frame_count} frames${transcriptNote}`, 'success');
    loadUsage();
  } catch (err) {
    toast(`Error: ${err.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

function setLoading(on, label = '') {
  state.loading = on;
  const btn = $('btn-generate'), txt = $('btn-txt'), spin = $('btn-spin'), bar = $('loading-bar');
  btn.disabled = on;
  btn.classList.toggle('loading', on);
  if (on && label) { txt.textContent = label; txt.style.display = ''; spin.style.display = 'none'; }
  else { txt.textContent = '\u26A1 Generate Magic'; txt.style.display = on ? 'none' : ''; spin.style.display = on ? 'block' : 'none'; }
  bar.style.width = on ? '70%' : '0';
  if (!on) { bar.style.width = '100%'; setTimeout(() => { bar.style.width = '0'; }, 400); }
}

// ---------------------------------------------------------------------------
// Render results
// ---------------------------------------------------------------------------
function renderResults(results) {
  const grid = $('results-carousel'); if (grid) grid.innerHTML = '';
  const modes = Object.keys(results).sort((a, b) => _resultOrderIndex(a) - _resultOrderIndex(b));
  modes.forEach((mode) => {
    const text = results[mode];
    const slide = document.createElement('div'); slide.className = 'carousel-slide'; slide.dataset.mode = mode;
    const card = document.createElement('div'); card.className = 'result-card';
    slide.appendChild(card);

    if (mode === 'hashtag_set') {
      card.style.setProperty('--result-accent', '#10B981');
      card.innerHTML = `<div class="result-card-hdr"><span class="result-badge" style="--badge-color:#10B981;--badge-rgb:16,185,129">🏷️ Hashtag Set</span><div class="result-card-actions"><button class="btn-copy-result" onclick="copyResult(this,'hashtag_set')"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy All</button></div></div>${renderHashtagSetBody(text)}`;
      grid.appendChild(slide);
      return;
    }

    const meta = MODE_META[mode] || { label: mode, icon: '⚡', color: '#4F46E5', rgb: '79,70,229' };
    card.style.setProperty('--result-accent', meta.color);
    let displayIcon = meta.icon, displayLabel = meta.label;
    if (mode === 'pose_series') {
      const ctMeta = CONTENT_TYPE_META[state.contentType] || CONTENT_TYPE_META.creator;
      const parts = ctMeta.poseLabel.split(' ');
      displayIcon = parts[0];
      displayLabel = parts.slice(1).join(' ');
    }
    let bodyHtml;
    if (mode === 'pose_series') bodyHtml = renderPoseSeriesBody(text, meta.color);
    else if (mode === 'post' && /\n---\n/.test(text)) bodyHtml = renderVariantsBody(text, meta.color);
    else {
      const isPrompt = mode === 'flux_image' || mode === 'wan_video';
      bodyHtml = `<div class="result-body"><div class="result-text ${isPrompt ? 'prompt-style' : ''}" onclick="expandResultText(this, '${displayLabel}')">${escHtml(text)}</div></div>`;
    }
    card.innerHTML = `<div class="result-card-hdr"><span class="result-badge" style="--badge-color:${meta.color};--badge-rgb:${meta.rgb}">${displayIcon} ${displayLabel}</span><div class="result-card-actions">${mode === 'post' ? `<button class="btn-checklist-result" title="Pre-Publish Checklist" onclick="openChecklist()">\u{1F4CB}</button>` : ''}${mode === 'post' ? `<button class="btn-checklist-result" title="Score Hook" onclick="scoreHook('${mode}', this)">\u{1FA9D}</button>` : ''}<button class="btn-copy-result" onclick="copyResult(this,'${mode}')"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div></div>${bodyHtml}`;
    grid.appendChild(slide);
  });
  activateCarousel();
}

function renderHashtagSetBody(text) {
  const tierColors = { 'HIGH REACH': '#4F46E5', 'ENGAGEMENT': '#F59E0B', 'NICHE': '#10B981' };
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const tiers = [];
  lines.forEach(line => {
    const match = line.match(/^([A-Z ]+):\s*(.+)$/);
    if (match) tiers.push({ label: match[1].trim(), tags: match[2].trim(), color: tierColors[match[1].trim()] || '#6B7280' });
  });
  if (!tiers.length) return `<div class="result-body"><div class="result-text">${escHtml(text)}</div></div>`;
  const html = tiers.map(t => `
    <div class="hashtag-tier">
      <div class="hashtag-tier-hdr">
        <span class="hashtag-tier-label" style="color:${t.color}">${escHtml(t.label)}</span>
        <button class="btn-copy-result" style="font-size:0.7rem;padding:3px 8px" onclick="copyText(this,'${escAttr(t.tags)}')">Copy</button>
      </div>
      <div class="hashtag-tier-tags">${escHtml(t.tags)}</div>
    </div>`).join('');
  return `<div class="result-body">${html}</div>`;
}

function renderPoseSeriesBody(text, accentColor) {
  const poses = parsePoseSeries(text);
  if (!poses.length) return `<div class="result-body"><div class="result-text prompt-style">${escHtml(text)}</div></div>`;
  const items = poses.map(p => `
    <div class="pose-item">
      <div class="pose-item-hdr">
        <span class="pose-num" style="color:${accentColor}">Pose ${p.num}</span>
        <div style="display:flex;gap:5px;align-items:center">
          <button class="btn-gen-img" onclick="genPoseImage(this,'${escAttr(p.text)}')">&#127912; Image</button>
          <button class="btn-copy-result" onclick="copyText(this.dataset.text)" data-text="${escAttr(p.text)}" style="padding:4px 8px;font-size:0.75rem">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:2px"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Copy
          </button>
        </div>
      </div>
      <div class="pose-text prompt-style" style="cursor:pointer;" onclick="showTextModal(this.dataset.text, 'Pose ${p.num}')" data-text="${escAttr(p.text)}">${escHtml(p.text)}</div>
      <div class="pose-img-preview" style="display:none"></div>
    </div>`).join('');
  return `<div class="result-body"><div class="poses-list">${items}</div></div>`;
}

async function genPoseImage(btn, prompt) {
  let card, preview, origHtml;
  try {
    card = btn.closest('.pose-item');
    preview = card.querySelector('.pose-img-preview');
    origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:13px;height:13px;border-width:2px;border-color:rgba(79,70,229,0.3);border-top-color:var(--accent)"></div>';
    let data = await _awaitPrefetchedPoseImage(prompt);
    if (!data) {
      const res = await fetch('/api/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, reference_b64: state.imageB64, mode: 'pose_series', content_type: state.contentType }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }
      data = await res.json();
    }
    renderPoseImage(preview, data.image_b64);
    toast('Image generated!', 'success');
    if (data.restore_job_id) pollRestoreJob(preview, data.restore_job_id);
  } catch (err) {
    console.error('[Prism] genPoseImage failed:', err);
    toast(`Image gen: ${err.message || err}`, 'error');
  } finally {
    btn.disabled = false;
    if (origHtml !== undefined) btn.innerHTML = origHtml;
  }
}

// Kick off pass-1 generation for every pose as soon as the pose series text is available,
// so results are ready (or nearly ready) by the time the user taps a pose's "Image" button.
// Gated by the step-1 auto-pose toggle since it always costs an AI image gen call per pose.
function prefetchPoseSeriesImages(text) {
  if (!state.imageB64 || !state.autoPoseImages) return;
  state.poseImagePrefetch = state.poseImagePrefetch || {};
  parsePoseSeries(text).forEach(p => {
    if (state.poseImagePrefetch[p.text]) return; // already prefetching or cached
    state.poseImagePrefetch[p.text] = { status: 'pending' };
    fetch('/api/generate-image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: p.text, reference_b64: state.imageB64, mode: 'pose_series', content_type: state.contentType }),
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        console.error('[Prism] pose image prefetch failed:', err.detail || res.statusText);
        state.poseImagePrefetch[p.text] = { status: 'error' };
        return;
      }
      const data = await res.json();
      state.poseImagePrefetch[p.text] = { status: 'ready', image_b64: data.image_b64, restore_job_id: data.restore_job_id };
    }).catch((e) => { console.error('[Prism] pose image prefetch error:', e); state.poseImagePrefetch[p.text] = { status: 'error' }; });
  });
}

// Waits for a prefetch already in flight for this exact pose prompt rather than firing a
// redundant second /api/generate-image call. Returns null (meaning "do a normal live fetch")
// if there's no prefetch, it errored, or it's taking unexpectedly long.
async function _awaitPrefetchedPoseImage(prompt) {
  const entry = state.poseImagePrefetch?.[prompt];
  if (!entry) return null;
  for (let i = 0; i < 300; i++) { // ~300 * 300ms = ~90s ceiling for pass-1 to land
    const cur = state.poseImagePrefetch[prompt];
    if (cur.status === 'ready') return { image_b64: cur.image_b64, restore_job_id: cur.restore_job_id };
    if (cur.status === 'error') return null;
    await new Promise((r) => setTimeout(r, 300));
  }
  return null;
}

function renderPoseImage(preview, imageB64) {
  const ts = Date.now();
  preview.innerHTML = `
    <img src="${imageB64}" alt="Generated pose" loading="lazy"
         style="cursor:zoom-in;width:100%;border-radius:10px;display:block"
         onclick="openImageLightbox(this.src)">
    <div style="display:flex;gap:8px;margin-top:8px;align-items:center">
      <span class="pose-restore-status" style="font-size:0.72rem;color:var(--text-muted)">Tap image to preview full size</span>
      <a href="${imageB64}" download="pose-${ts}.png" class="btn-download-img" style="margin-left:auto">\u2193 Download</a>
    </div>`;
  preview.style.display = '';
}

// Face/tattoo/logo/text/product touch-up runs in the background (can take up to ~2 min) —
// poll for it here so the pass-1 image doesn't have to wait on it, and swap it in once ready.
async function pollRestoreJob(preview, jobId, attempt = 0) {
  const statusEl = preview.querySelector('.pose-restore-status');
  const maxAttempts = 40; // ~40 * 4s = ~2.5 min ceiling, matches backend's worst-case restore time
  if (statusEl && attempt === 0) statusEl.textContent = '\u2728 Restoring face/tattoo/logo details in background\u2026';
  if (attempt >= maxAttempts) {
    if (statusEl) statusEl.textContent = 'Tap image to preview full size';
    return;
  }
  try {
    const res = await fetch(`/api/generate-image/status/${jobId}`);
    if (res.ok) {
      const job = await res.json();
      if (job.status === 'done') {
        renderPoseImage(preview, job.image_b64);
        toast('Details restored!', 'success');
        return;
      }
      if (job.status === 'error') {
        if (statusEl) statusEl.textContent = 'Tap image to preview full size';
        return;
      }
    }
  } catch { /* network hiccup — just retry */ }
  setTimeout(() => pollRestoreJob(preview, jobId, attempt + 1), 4000);
}

function parsePoseSeries(text) {
  const poses = [], regex = /\[(\d+)\]\s*([\s\S]*?)(?=\[\d+\]|$)/g; let m;
  while ((m = regex.exec(text)) !== null) { const b = m[2].trim(); if (b) poses.push({ num: m[1], text: b }); }
  return poses;
}

// ---------------------------------------------------------------------------
// Copy
// ---------------------------------------------------------------------------
async function copyResult(btn, mode) { if (state.results?.[mode]) await copyText(btn, state.results[mode]); }

async function copyText(btnOrNull, text) {
  try {
    await navigator.clipboard.writeText(text);
    toast('Copied!', 'success');
    if (btnOrNull?.classList) { const o = btnOrNull.innerHTML; btnOrNull.classList.add('copied'); btnOrNull.innerHTML = '✓ Copied'; setTimeout(() => { btnOrNull.classList.remove('copied'); btnOrNull.innerHTML = o; }, 1800); }
  } catch { toast('Copy failed', 'error'); }
}

async function copyAll() {
  if (!state.results) return;
  const lines = Object.entries(state.results).map(([m, t]) => `=== ${(MODE_META[m]?.label || m).toUpperCase()} ===\n${t}`);
  try { await navigator.clipboard.writeText(lines.join('\n\n')); toast('All copied!', 'success'); }
  catch { toast('Copy failed', 'error'); }
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------
async function openHistory() {
  show('history-modal');
  const list = $('history-list'); list.innerHTML = '<p class="history-empty">Loading…</p>';
  loadStreak();
  try {
    const res = await fetch('/api/history'); const items = await res.json();
    if (!items.length) { list.innerHTML = '<p class="history-empty">No history yet.</p>'; return; }
    list.innerHTML = ''; items.forEach(item => list.appendChild(buildHistoryItem(item)));
  } catch { list.innerHTML = '<p class="history-empty" style="color:var(--error)">Failed to load</p>'; }
}

async function loadStreak() {
  const badge = $('streak-badge');
  if (!badge) return;
  try {
    const res = await fetch('/api/streak');
    if (!res.ok) return;
    const d = await res.json();
    if (d.current_streak > 0) {
      badge.style.display = '';
      badge.textContent = `\ud83d\udd25 ${d.current_streak} day${d.current_streak === 1 ? '' : 's'}`;
      badge.title = `Longest streak: ${d.longest_streak} day${d.longest_streak === 1 ? '' : 's'}`;
    } else {
      badge.style.display = 'none';
    }
  } catch { badge.style.display = 'none'; }
}

function buildHistoryItem(item) {
  const div = document.createElement('div'); div.className = 'history-item';
  const date = new Date(item.created_at + 'Z').toLocaleString();
  const modeLabel = MODE_META[item.mode]?.label || item.mode;
  const preview = (Object.values(item.results)[0] || '').slice(0, 80);
  const thumbHtml = item.thumb ? `<img class="history-thumb" src="${item.thumb}" alt="">` : `<div class="history-thumb-placeholder">🖼</div>`;
  const feedbackHtml = item.results && item.results.post ? `
    <div class="history-feedback" onclick="event.stopPropagation()">
      <label class="history-posted-toggle">
        <input type="checkbox" ${item.posted ? 'checked' : ''} onchange="toggleHistoryPosted('${item.id}', this.checked)"> Posted
      </label>
      <span class="history-stars" data-id="${item.id}">
        ${[1, 2, 3, 4, 5].map(n => `<span class="history-star ${n <= (item.rating || 0) ? 'filled' : ''}" onclick="rateHistory('${item.id}', ${n})">\u2605</span>`).join('')}
      </span>
    </div>` : '';
  const metricsHtml = item.results && item.results.post ? `
    <div class="history-feedback" onclick="event.stopPropagation()">
      <button class="btn-wiz-secondary" style="padding:3px 8px;font-size:0.72rem" onclick="toggleMetricsForm('${item.id}')">\ud83d\udcca Log Stats</button>
    </div>
    <div id="metrics-form-${item.id}" style="display:none;margin-top:6px" onclick="event.stopPropagation()">
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
        <input type="number" min="0" class="field-input" id="metrics-likes-${item.id}" placeholder="Likes" style="width:70px;padding:6px 8px;font-size:0.75rem">
        <input type="number" min="0" class="field-input" id="metrics-views-${item.id}" placeholder="Views" style="width:70px;padding:6px 8px;font-size:0.75rem">
        <input type="number" min="0" class="field-input" id="metrics-comments-${item.id}" placeholder="Comments" style="width:80px;padding:6px 8px;font-size:0.75rem">
        <input type="number" min="0" class="field-input" id="metrics-shares-${item.id}" placeholder="Shares" style="width:70px;padding:6px 8px;font-size:0.75rem">
      </div>
      <button class="btn-wiz-primary" style="padding:4px 10px;font-size:0.75rem" onclick="saveMetrics('${item.id}')">Save Stats</button>
    </div>` : '';
  div.innerHTML = `${thumbHtml}
    <div class="history-meta" onclick="loadHistoryItem(${JSON.stringify(item).replace(/"/g, '&quot;')})">
      <div class="history-mode">${modeLabel} · ${item.platform || 'general'}</div>
      <div class="history-date">${date}</div>
      <div class="history-preview">${escHtml(preview)}${preview.length >= 80 ? '…' : ''}</div>
      ${feedbackHtml}
      ${metricsHtml}
    </div>
    <button class="history-item-del" onclick="deleteHistory('${item.id}',this.closest('.history-item'))" title="Delete">✕</button>`;
  return div;
}

function toggleMetricsForm(id) {
  const form = $(`metrics-form-${id}`);
  if (!form) return;
  form.style.display = form.style.display === 'none' ? '' : 'none';
}

async function saveMetrics(id) {
  const num = (elId) => Math.max(0, parseInt($(elId)?.value, 10) || 0);
  try {
    const res = await fetch(`/api/history/${id}/metrics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        likes: num(`metrics-likes-${id}`),
        views: num(`metrics-views-${id}`),
        comments: num(`metrics-comments-${id}`),
        shares: num(`metrics-shares-${id}`),
      }),
    });
    if (!res.ok) throw new Error('Failed to save stats');
    toast('Stats saved', 'success');
    toggleMetricsForm(id);
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function rateHistory(id, rating) {
  try {
    const res = await fetch(`/api/history/${id}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ posted: true, rating }),
    });
    if (!res.ok) throw new Error('Failed to save rating');
    const stars = document.querySelector(`.history-stars[data-id="${id}"]`);
    if (stars) {
      stars.querySelectorAll('.history-star').forEach((s, i) => s.classList.toggle('filled', i < rating));
      const cb = stars.closest('.history-feedback')?.querySelector('.history-posted-toggle input');
      if (cb) cb.checked = true;
    }
    toast('Thanks \u2014 this helps improve future captions', 'success');
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function toggleHistoryPosted(id, checked) {
  const stars = document.querySelector(`.history-stars[data-id="${id}"]`);
  const rating = stars ? stars.querySelectorAll('.history-star.filled').length : 0;
  try {
    const res = await fetch(`/api/history/${id}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ posted: checked, rating }),
    });
    if (!res.ok) throw new Error('Failed to save');
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

function loadHistoryItem(item) { state.results = item.results; renderResults(item.results); $('workspace').style.display = 'flex'; wizToStep(5); closeHistory(); }
async function deleteHistory(id, el) { try { await fetch(`/api/history/${id}`, { method: 'DELETE' }); el.remove(); toast('Deleted', 'success'); } catch { toast('Delete failed', 'error'); } }
function closeHistory() { hide('history-modal'); }

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
let cachedSettings = {};
async function loadSettings() { try { const r = await fetch('/api/settings'); cachedSettings = await r.json(); return cachedSettings; } catch { return {}; } }
function fillSettingsForm(cfg) {
  const pEl = document.getElementById('s-provider');
  if (pEl) { pEl.value = cfg.provider || 'ollama'; onProviderChange(cfg.provider || 'ollama', cfg); }
  if ($('s-host')) $('s-host').value = cfg.ollama_host || '';
  if ($('s-model')) $('s-model').value = cfg.vision_model || '';
  if ($('s-apikey')) $('s-apikey').value = '';
  if ($('s-cloud-model')) $('s-cloud-model').value = cfg.cloud_model || '';
}
async function openSettings() { fillSettingsForm(await loadSettings()); hide('model-list'); show('settings-modal'); }
function closeSettings() { hide('settings-modal'); }

function openDeleteAccount() {
  const pw = $('delete-account-password'), err = $('delete-account-error');
  if (pw) pw.value = '';
  if (err) err.style.display = 'none';
  show('delete-account-modal');
}
function closeDeleteAccount() { hide('delete-account-modal'); }

async function confirmDeleteAccount() {
  const pw = $('delete-account-password'), err = $('delete-account-error'), btn = $('delete-account-btn');
  const password = pw ? pw.value : '';
  if (!password) { err.textContent = 'Enter your password to confirm.'; err.style.display = 'block'; return; }
  btn.disabled = true;
  try {
    const res = await fetch('/api/delete-account', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
    if (res.ok) {
      window.location.href = '/login';
      return;
    }
    const d = await res.json().catch(() => ({}));
    err.textContent = d.detail || 'Could not delete account.';
    err.style.display = 'block';
  } catch {
    err.textContent = 'Connection error — try again.';
    err.style.display = 'block';
  } finally {
    btn.disabled = false;
  }
}

function toggleHeaderMore() {
  const menu = $('header-more-menu');
  const btn = $('btn-header-more');
  if (!menu) return;
  const opening = !menu.classList.contains('open');
  if (opening && btn) {
    const r = btn.getBoundingClientRect();
    menu.style.top = Math.round(r.bottom + 8) + 'px';
    menu.style.right = Math.round(window.innerWidth - r.right) + 'px';
  }
  menu.classList.toggle('open');
}
function closeHeaderMore() {
  const menu = $('header-more-menu');
  if (menu) menu.classList.remove('open');
}
document.addEventListener('click', (e) => {
  const menu = $('header-more-menu');
  if (menu && menu.classList.contains('open') && !e.target.closest('.header-more-wrap')) {
    menu.classList.remove('open');
  }
});

function onProviderChange(provider) {
  const isCloud = provider !== 'ollama';
  const os = document.getElementById('s-ollama-section');
  const cs = document.getElementById('s-cloud-section');
  if (os) os.style.display = isCloud ? 'none' : '';
  if (cs) cs.style.display = isCloud ? '' : 'none';
  const hints = { gemini: 'Default: gemini-2.0-flash · Also: gemini-1.5-flash', grok: 'Default: grok-2-vision-1212', openai: 'Default: gpt-4o' };
  const h = document.getElementById('s-cloud-hint'); if (h) h.textContent = hints[provider] || '';
}

async function saveSettings() {
  const pEl = document.getElementById('s-provider');
  const provider = pEl?.value || 'ollama';
  const payload = { provider };
  if (provider === 'ollama') {
    payload.ollama_host = ($('s-host')?.value || '').trim();
    payload.vision_model = ($('s-model')?.value || '').trim();
  } else {
    const key = ($('s-apikey')?.value || '').trim();
    if (key) payload.api_key = key; else payload.api_key = '';
    payload.cloud_model = ($('s-cloud-model')?.value || '').trim();
  }
  try {
    await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    toast('Settings saved', 'success'); closeSettings();
  } catch { toast('Save failed', 'error'); }
}

async function loadModels() {
  const list = $('model-list'); list.innerHTML = '<div class="model-list-item" style="color:var(--text-muted)">Loading…</div>'; show('model-list');
  try {
    const data = await (await fetch('/api/models')).json();
    if (!data.models?.length) { list.innerHTML = '<div class="model-list-item">No models found</div>'; return; }
    list.innerHTML = ''; let lastV = null;
    data.models.forEach(m => {
      if (lastV === null || lastV !== m.has_vision) {
        const h = document.createElement('div'); h.style.cssText = 'padding:5px 12px 3px;font-size:0.67rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--text-muted);border-bottom:1px solid var(--border)';
        h.textContent = m.has_vision ? '👁 Vision Models' : '💬 Text Only'; list.appendChild(h); lastV = m.has_vision;
      }
      const item = document.createElement('div'); item.className = 'model-list-item'; item.style.cssText = m.has_vision ? '' : 'opacity:0.5';
      item.innerHTML = `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(m.name)}</span><span style="font-size:0.67rem;font-weight:700;margin-left:6px;color:${m.has_vision ? 'var(--success)' : 'var(--error)'}">${m.has_vision ? '✓' : '✗'}</span>`;
      item.style.display = 'flex'; item.style.alignItems = 'center';
      item.onclick = () => { $('s-model').value = m.name; hide('model-list'); if (!m.has_vision) toast('⚠ Text-only model — cannot analyze images', 'error'); };
      list.appendChild(item);
    });
  } catch (e) { list.innerHTML = `<div class="model-list-item" style="color:var(--error)">Ollama unreachable: ${e.message}</div>`; }
}

// ---------------------------------------------------------------------------
// Preferences
// ---------------------------------------------------------------------------
function openPrefs() {
  const modal = document.getElementById('prefs-modal'); if (!modal) return;
  modal.style.cssText = 'display:flex';
  try {
    const s = currentUser?.settings || { enabled_modes: ['flux_image', 'wan_video', 'pose_series'], gender: 'neutral' };
    const gender = s.gender || 'neutral'; const modes = s.enabled_modes || [];
    ['neutral','female','male'].forEach(g => { const el = document.getElementById(`pref-${g}`); if (el) el.classList.toggle('active', gender === g); });
    const fl = $('pref-flux'); const wn = $('pref-wan'); const po = $('pref-poses');
    if (fl) fl.checked = modes.includes('flux_image');
    if (wn) wn.checked = modes.includes('wan_video');
    if (po) po.checked = modes.includes('pose_series');
    const bv = $('pref-brand-voice');
    if (bv) bv.value = s.brand_voice || '';
    const niche = $('pref-niche');
    if (niche) niche.value = s.niche || '';
    const sig = $('pref-signature');
    if (sig) { sig.value = s.signature || ''; const sc = $('sig-char-count'); if (sc) sc.textContent = sig.value.length; sig.oninput = () => { const c = $('sig-char-count'); if (c) c.textContent = sig.value.length; }; }
    initNotificationToggle();
  } catch (_) {}
}

function closePrefs() { const m = document.getElementById('prefs-modal'); if (m) m.style.cssText = 'display:none'; }

async function setPrefGender(gender) {
  currentUser.settings.gender = gender;
  ['neutral','female','male'].forEach(g => { const el = document.getElementById(`pref-${g}`); if (el) el.classList.toggle('active', g === gender); });
  await _savePrefs();
}

async function savePrefModes() {
  const modes = [];
  if ($('pref-flux')?.checked)  modes.push('flux_image');
  if ($('pref-wan')?.checked)   modes.push('wan_video');
  if ($('pref-poses')?.checked) modes.push('pose_series');
  currentUser.settings.enabled_modes = modes;
  if (state.mode !== 'all' && state.mode !== 'post' && !modes.includes(state.mode)) setMode('all');
  buildModeGrid();
  await _savePrefs();
}

async function _savePrefs() {
  try {
    const bv = $('pref-brand-voice');
    const sg = $('pref-signature');
    const res = await fetch('/api/user-settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled_modes: currentUser.settings.enabled_modes, gender: currentUser.settings.gender, brand_voice: bv ? bv.value : '', signature: sg ? sg.value : '' }) });
    if (res.ok) { currentUser.settings = await res.json(); toast('Saved', 'success'); }
  } catch { toast('Save failed', 'error'); }
}

async function savePrefNiche() {
  try {
    const niche = $('pref-niche');
    const res = await fetch('/api/user-settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ niche: niche ? niche.value : '' }) });
    if (res.ok) { currentUser.settings = await res.json(); toast('Saved', 'success'); }
  } catch { toast('Save failed', 'error'); }
}

// ---------------------------------------------------------------------------
// Push Notifications — reminders for posting consistency
// ---------------------------------------------------------------------------
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}

async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return null;
  try { return await navigator.serviceWorker.register('/sw.js'); } catch (e) { console.warn('SW registration failed', e); return null; }
}

async function getPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  try {
    const reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  } catch { return null; }
}

function initNotificationToggle() {
  const toggle = $('pref-notifications-enabled');
  if (!toggle) return;
  const subToggles = $('notif-sub-toggles');
  const supported = 'serviceWorker' in navigator && 'PushManager' in window;
  if (!supported) {
    toggle.disabled = true;
    const note = $('notif-unsupported-note'); if (note) note.style.display = '';
    return;
  }
  const s = currentUser?.settings || {};
  toggle.checked = !!s.notifications_enabled;
  if (subToggles) subToggles.style.display = toggle.checked ? '' : 'none';
  const streakEl = $('pref-notify-streak'); if (streakEl) streakEl.checked = s.notify_streak_risk !== false;
  const schedEl = $('pref-notify-sched'); if (schedEl) schedEl.checked = s.notify_scheduled_due !== false;
  const limitEl = $('pref-notify-limit'); if (limitEl) limitEl.checked = s.notify_limit_reset !== false;
  const inactEl = $('pref-notify-inactivity'); if (inactEl) inactEl.checked = s.notify_inactivity !== false;
  const milestoneEl = $('pref-notify-streak-milestone'); if (milestoneEl) milestoneEl.checked = s.notify_streak_milestone !== false;
  const recapEl = $('pref-notify-weekly-recap'); if (recapEl) recapEl.checked = s.notify_weekly_recap !== false;
  const bestEl = $('pref-notify-personal-best'); if (bestEl) bestEl.checked = s.notify_personal_best !== false;
  const holidayEl = $('pref-notify-holiday'); if (holidayEl) holidayEl.checked = s.notify_holiday_idea !== false;
  const trendEl = $('pref-notify-trend'); if (trendEl) trendEl.checked = s.notify_trend_alert !== false;
}

async function toggleNotifications(checkbox) {
  const subToggles = $('notif-sub-toggles');
  if (checkbox.checked) {
    try {
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') { checkbox.checked = false; toast('Notification permission denied', 'error'); return; }
      const reg = await registerServiceWorker();
      if (!reg) throw new Error('Service worker unavailable');
      const keyRes = await fetch('/api/push/public-key');
      if (!keyRes.ok) throw new Error('Could not get push key');
      const { public_key } = await keyRes.json();
      let sub = await reg.pushManager.getSubscription();
      if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(public_key) });
      await fetch('/api/push/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sub.toJSON()) });
      if (subToggles) subToggles.style.display = '';
      await _saveNotifPrefs({ notifications_enabled: true });
      toast('Notifications enabled', 'success');
    } catch (e) {
      checkbox.checked = false;
      toast('Could not enable notifications: ' + e.message, 'error');
    }
  } else {
    try {
      const sub = await getPushSubscription();
      if (sub) {
        await fetch('/api/push/unsubscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ endpoint: sub.endpoint }) });
        await sub.unsubscribe();
      }
    } catch (_) {}
    if (subToggles) subToggles.style.display = 'none';
    await _saveNotifPrefs({ notifications_enabled: false });
    toast('Notifications turned off', 'success');
  }
}

async function saveNotifSubToggles() {
  await _saveNotifPrefs({
    notify_streak_risk: $('pref-notify-streak')?.checked ?? true,
    notify_scheduled_due: $('pref-notify-sched')?.checked ?? true,
    notify_limit_reset: $('pref-notify-limit')?.checked ?? true,
    notify_inactivity: $('pref-notify-inactivity')?.checked ?? true,
    notify_streak_milestone: $('pref-notify-streak-milestone')?.checked ?? true,
    notify_weekly_recap: $('pref-notify-weekly-recap')?.checked ?? true,
    notify_personal_best: $('pref-notify-personal-best')?.checked ?? true,
    notify_holiday_idea: $('pref-notify-holiday')?.checked ?? true,
    notify_trend_alert: $('pref-notify-trend')?.checked ?? true,
  });
}

async function _saveNotifPrefs(fields) {
  try {
    const res = await fetch('/api/user-settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields) });
    if (res.ok) currentUser.settings = await res.json();
  } catch { toast('Save failed', 'error'); }
}

async function sendTestNotification() {
  try {
    const res = await fetch('/api/push/test', { method: 'POST' });
    if (res.ok) toast('Test notification sent', 'success'); else toast('Failed to send test notification', 'error');
  } catch { toast('Failed to send test notification', 'error'); }
}

// ---------------------------------------------------------------------------
// Ideas
// ---------------------------------------------------------------------------
const ideaState = { type: 'post', expanding: false };
let suggestionIdeas = [], lastExpandedResult = '', onThisDayPick = null;

function openIdeas() { const m = document.getElementById('ideas-modal'); if (m) { m.style.cssText = 'display:flex'; } hide('expanded-result'); $('idea-input').value = ''; loadSuggestions(); }
function closeIdeas() { const m = document.getElementById('ideas-modal'); if (m) m.style.cssText = 'display:none'; }
function setIdeaType(type, btn) { ideaState.type = type; document.querySelectorAll('.ideas-type-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); }

async function expandIdea() {
  const keywords = $('idea-input').value.trim(); if (!keywords) { toast('Type some keywords first', 'error'); return; }
  if (ideaState.expanding) return;
  ideaState.expanding = true;
  const btn = $('btn-expand'), txt = $('expand-txt'), spin = $('expand-spin');
  btn.disabled = true; txt.style.display = 'none'; spin.style.display = 'block'; hide('expanded-result');
  try {
    const res = await fetch('/api/expand-idea', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keywords, prompt_type: ideaState.type, platform: state.platform, hashtags: state.hashtags }) });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    const data = await res.json(); lastExpandedResult = data.result;
    const labels = { post: '✍️ Social Caption', flux_image: '🎨 Flux Image Prompt', wan_video: '🎬 WAN Video Prompt' };
    const resultEl = $('expanded-result');
    resultEl.innerHTML = `<div class="expanded-result-hdr"><span class="expanded-result-label">${labels[ideaState.type] || ideaState.type}</span><button class="btn-copy-result" onclick="copyExpandedResult(this)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div><div class="expanded-result-text">${escHtml(data.result)}</div>`;
    show('expanded-result'); toast('Expanded!', 'success');
  } catch (err) { toast(`Error: ${err.message}`, 'error'); }
  finally { ideaState.expanding = false; btn.disabled = false; txt.style.display = ''; spin.style.display = 'none'; }
}

function copyExpandedResult(btn) { copyText(btn, lastExpandedResult); }

async function loadSuggestions() {
  const area = $('suggestions-area'); area.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading…</p>';
  try { const data = await (await fetch('/api/suggestions')).json(); renderSuggestions(data); }
  catch { area.innerHTML = '<p class="ideas-hint" style="color:var(--error);text-align:center">Could not load suggestions</p>'; }
}

function renderSuggestions(data) {
  suggestionIdeas = []; onThisDayPick = data.on_this_day || null; const area = $('suggestions-area'); let html = '';
  if (onThisDayPick) {
    const otd = onThisDayPick;
    const preview = (Object.values(otd.results || {})[0] || '').toString().slice(0, 100);
    const label = otd.is_anniversary ? '📅 On This Day' : '⭐ From Your Best Posts';
    html += `<div class="sugg-section"><div class="sugg-section-title">${label}</div>
      <div class="hub-card" style="cursor:pointer" onclick="viewOnThisDay()">
        <p class="hub-bio"><strong>${MODE_META[otd.mode]?.label || otd.mode} · ${escHtml(otd.platform || 'general')}</strong> — ${'★'.repeat(otd.rating)} · ${new Date(otd.created_at + 'Z').toLocaleDateString()}</p>
        <p class="hub-bio">${escHtml(preview)}${preview.length >= 100 ? '…' : ''}</p>
      </div>
    </div>`;
  }
  if (data.upcoming?.length) {
    html += `<div class="sugg-section"><div class="sugg-section-title">🗓 Upcoming</div><div class="sugg-grid">`;
    data.upcoming.forEach(h => { html += buildSuggCard(h.name, h.icon, h.ideas, h.days_until === 0 ? 'Today!' : `in ${h.days_until}d`, false); });
    html += `</div></div>`;
  }
  if (data.season) { const s = data.season; html += `<div class="sugg-section"><div class="sugg-section-title">${s.icon} ${s.name} Vibes</div><div class="sugg-grid">${buildSuggCard(s.name+' Season',s.icon,s.ideas,'Now',true)}</div></div>`; }
  if (data.evergreen?.length) {
    html += `<div class="sugg-section"><div class="sugg-section-title">✨ Always Fresh</div><div class="sugg-grid">`;
    for (let i = 0; i < data.evergreen.length; i += 3) { const c = data.evergreen.slice(i,i+3); html += buildSuggCard(c.map(e=>e.theme).join(' · '), c[0].icon, c.map(e=>e.idea), null, false); }
    html += `</div></div>`;
  }
  area.innerHTML = html || '<p class="ideas-hint" style="text-align:center">No suggestions available</p>';
}

function buildSuggCard(name, icon, ideas, badge, isSeason) {
  const badgeHtml = badge ? `<span class="sugg-badge${isSeason ? ' season' : ''}">${badge}</span>` : '';
  const ideasHtml = ideas.map(idea => { const idx = suggestionIdeas.length; suggestionIdeas.push(idea); return `<div class="sugg-idea-item" onclick="useIdea(${idx})"><span class="sugg-idea-text">${escHtml(idea)}</span><button class="btn-use" onclick="event.stopPropagation();useIdea(${idx})">Use</button></div>`; }).join('');
  return `<div class="sugg-card"><div class="sugg-card-hdr"><span class="sugg-name"><span>${icon}</span>${escHtml(name)}</span>${badgeHtml}</div><div class="sugg-ideas">${ideasHtml}</div></div>`;
}

function useIdea(idx) { const idea = suggestionIdeas[idx]; if (!idea) return; $('idea-input').value = idea; $('idea-input').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); $('idea-input').focus(); toast('Idea loaded — click Expand!', 'success'); }

function viewOnThisDay() {
  if (!onThisDayPick) return;
  closeIdeas();
  loadHistoryItem(onThisDayPick);
}

// ---------------------------------------------------------------------------
// Overlay / keyboard
// ---------------------------------------------------------------------------
function overlayClose(e, id) { if (e.target.id === id) hide(id); }

// ---------------------------------------------------------------------------
// Text Modal
// ---------------------------------------------------------------------------
function expandResultText(el, title) {
  if (!el || el.isContentEditable) return;
  showTextModal(el.textContent, title || 'Full Text');
}

let textModalItems = [];
let textModalIndex = 0;

// Single-text popup — wraps showTextModalMulti with a 1-item list (carousel nav auto-hides).
function showTextModal(text, title) {
  showTextModalMulti([text], 0, title);
}

function showTextModalMulti(items, startIndex, title) {
  textModalItems = items || [];
  textModalIndex = Math.max(0, Math.min(textModalItems.length - 1, startIndex || 0));
  const carousel = $('text-modal-carousel');
  if (carousel) {
    carousel.innerHTML = textModalItems.map(t => `<div style="flex:0 0 100%;width:100%;min-width:0;scroll-snap-align:start;padding:16px;overflow-y:auto;white-space:pre-wrap;line-height:1.5;font-size:0.92rem;">${escHtml(t)}</div>`).join('');
  }
  const titleEl = $('text-modal-title'); if (titleEl) titleEl.textContent = title || 'Prompt Details';
  _updateTextModalNav();
  show('text-modal');
  if (carousel) carousel.scrollLeft = textModalIndex * carousel.clientWidth;
}

function _updateTextModalNav() {
  const multi = textModalItems.length > 1;
  const dots = $('text-modal-dots');
  if (dots) dots.innerHTML = multi ? textModalItems.map((_, i) => `<span style="width:6px;height:6px;border-radius:50%;background:${i===textModalIndex?'var(--accent)':'var(--border)'}"></span>`).join('') : '';
  const counter = $('text-modal-counter'); if (counter) counter.textContent = multi ? `${textModalIndex+1}/${textModalItems.length}` : '';
  const prevBtn = $('tm-prev'), nextBtn = $('tm-next');
  if (prevBtn) prevBtn.style.display = multi ? '' : 'none';
  if (nextBtn) nextBtn.style.display = multi ? '' : 'none';
  const copyBtn = $('btn-copy-modal'); if (copyBtn) copyBtn.onclick = () => copyText(copyBtn, textModalItems[textModalIndex] || '');
}

function textModalGo(dir) {
  if (textModalItems.length < 2) return;
  textModalIndex = Math.max(0, Math.min(textModalItems.length - 1, textModalIndex + dir));
  const carousel = $('text-modal-carousel');
  if (carousel) carousel.scrollTo({ left: textModalIndex * carousel.clientWidth, behavior: 'smooth' });
  _updateTextModalNav();
}

function closeTextModal() { hide('text-modal'); }

// Full-size image preview overlay — created/destroyed on demand since it only ever
// shows one image at a time (unlike the text modal's persistent carousel markup).
function openImageLightbox(src) {
  closeImageLightbox();
  const overlay = document.createElement('div');
  overlay.className = 'img-lightbox';
  overlay.id = 'img-lightbox';
  overlay.onclick = closeImageLightbox;
  overlay.innerHTML = `<button class="img-lightbox-close" onclick="closeImageLightbox()">&times;</button><img src="${escAttr(src)}" alt="Full size preview">`;
  document.body.appendChild(overlay);
  document.addEventListener('keydown', _lightboxEscHandler);
}

function closeImageLightbox() {
  const el = document.getElementById('img-lightbox');
  if (el) el.remove();
  document.removeEventListener('keydown', _lightboxEscHandler);
}

function _lightboxEscHandler(e) { if (e.key === 'Escape') closeImageLightbox(); }

function setupKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { ['history-modal','settings-modal','ideas-modal','prefs-modal','text-modal','schedule-modal','analytics-modal'].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; }); hide('model-list'); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && (state.imageB64 || state.videoFile) && !state.loading) generate();
  });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
async function logout() { await fetch('/api/logout', { method: 'POST' }).catch(() => {}); window.location.href = '/login'; }

function setLanguage(lang) { state.language = lang; }

async function loadUsage() {
  try {
    const res = await fetch('/api/usage'); if (!res.ok) return;
    const d = await res.json();
    const badge = document.getElementById('usage-badge'); if (!badge) return;
    badge.style.display = '';
    badge.textContent = d.limit > 0 ? `${d.count}/${d.limit}` : `${d.count} today`;
    badge.className = 'usage-badge';
    if (d.limit > 0) { if (d.count >= d.limit) badge.classList.add('at-limit'); else if (d.count >= d.limit * 0.8) badge.classList.add('near-limit'); }
  } catch {}
}

async function exportHistory() {
  try {
    const a = document.createElement('a'); a.href = '/api/history/export'; a.download = 'que_history.txt';
    document.body.appendChild(a); a.click(); document.body.removeChild(a); toast('Downloading...', 'success');
  } catch { toast('Export failed', 'error'); }
}

function renderVariantsBody(text, accentColor) {
  const variants = text.split(/\n?\s*---\s*\n?/).map(p => p.trim()).filter(p => p.length > 0).slice(0, 3);
  if (variants.length < 2) return `<div class="result-body"><div class="result-text">${escHtml(text)}</div></div>`;
  const items = variants.map((v, i) => `<div class="variant-item"><div class="variant-item-hdr"><span class="variant-num" style="color:${accentColor}">Take ${i+1}</span><div style="display:flex;gap:5px;align-items:center"><span class="char-counter ${v.length > 280 ? 'over' : v.length > 240 ? 'warn' : ''}">${v.length} chars</span><button class="btn-copy-result" onclick="copyVariant(this)" data-text="${escAttr(v)}"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div></div><div class="variant-text" onclick="expandResultText(this, 'Take ${i+1}')">${escHtml(v)}</div></div>`).join('');
  return `<div class="result-body"><div class="variants-list">${items}</div></div>`;
}

function renderThreadBody(text) {
  const tweets = parsePoseSeries(text);
  if (!tweets.length) return `<div class="result-body"><div class="result-text prompt-style">${escHtml(text)}</div></div>`;
  const items = tweets.map(t => `<div class="thread-tweet"><div class="thread-tweet-hdr"><span class="thread-tweet-num">Tweet ${t.num}</span><button class="btn-copy-result" onclick="copyText(this,'${escAttr(t.text)}')"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div><div class="thread-tweet-text" onclick="expandResultText(this, 'Tweet ${t.num}')">${escHtml(t.text)}</div><div class="thread-tweet-chars" style="color:${t.text.length > 240 ? 'var(--error)' : 'var(--text-muted)'}">${t.text.length}/240</div></div>`).join('');
  return `<div class="result-body"><div class="thread-list">${items}</div></div>`;
}

async function copyVariant(btn) { if (btn.dataset.text) await copyText(btn, btn.dataset.text); }

function toggleEdit(btn, card) {
  const el = card.querySelector('.result-text, .variant-text'); if (!el) return;
  const editing = el.contentEditable === 'true'; el.contentEditable = editing ? 'false' : 'true';
  btn.innerHTML = editing ? '&#9998; Edit' : '&#10003; Done'; btn.classList.toggle('editing', !editing);
  if (!editing) el.focus();
}

async function regenModeQUE(mode, card) {
  if (state.isVideo || !state.imageB64 || state.loading) return;
  const rb = card.querySelector('.btn-regen-result'); if (rb) { rb.disabled = true; rb.textContent = '\u231b'; }
  try {
    const res = await fetch('/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64: state.imageB64, mode, platform: state.platform, hashtags: state.hashtags, guidance: ($('caption-context')?.value || '').trim(), language: state.language, variants: state.variants, hub_hashtags: state.hubHashtags }) });
    if (!res.ok) { toast('Regen failed', 'error'); return; }
    const data = await res.json();
    if (data.results[mode] !== undefined) {
      if (!state.results) state.results = {}; state.results[mode] = data.results[mode];
      if (mode === 'pose_series') prefetchPoseSeriesImages(data.results[mode]);
      renderResults(state.results); loadUsage(); toast('Regenerated!', 'success');
    }
  } catch (e) { toast(`Error: ${e.message}`, 'error'); }
  finally { if (rb && rb.isConnected) { rb.disabled = false; rb.textContent = '\u8635'; } }
}

const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const res = await _origFetch(...args);
  if (res.status === 401) window.location.href = '/login';
  return res;
};

// ---------------------------------------------------------------------------
// Distribution & Tags \u2014 Feature Page Discovery & Targeting Engine (Instagram
// hubs + Reddit research panel). Hub data is entirely user-submitted after the
// user finds accounts themselves via search \u2014 nothing here scrapes Instagram
// or TikTok directly, so it stays ToS-compliant.
// ---------------------------------------------------------------------------
let distTier = '';
let distPlatform = 'instagram';
let _distNicheTimer = null;

function _guessNiche() {
  const ctx = ($('caption-context')?.value || '').trim();
  if (!ctx) return '';
  return ctx.split(/\s+/).slice(0, 4).join(' ').toLowerCase();
}

function openDistribution() {
  const m = $('distribution-modal');
  if (!m) return;
  m.style.cssText = 'display:flex';
  const input = $('dist-niche-input');
  if (input && !input.value) input.value = _guessNiche();
  hide('add-hub-form');
  loadDistData();
}

function closeDistribution() { hide('distribution-modal'); }

function setDistTab(tab, btn) {
  document.querySelectorAll('#dist-tabs .ideas-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  $('dist-instagram-panel').style.display = tab === 'instagram' ? '' : 'none';
  $('dist-reddit-panel').style.display = tab === 'reddit' ? '' : 'none';
  $('dist-vault-panel').style.display = tab === 'vault' ? '' : 'none';
  $('dist-peer-panel').style.display = tab === 'peers' ? '' : 'none';
  $('dist-trends-panel').style.display = tab === 'trends' ? '' : 'none';
  if (tab === 'vault') loadVaults();
  if (tab === 'peers') { loadMyCreatorProfile(); loadPeerList(); }
}

function setDistTier(tier, btn) {
  distTier = tier;
  document.querySelectorAll('#dist-tier-row .ideas-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadHubs();
}

function setDistPlatform(platform, btn) {
  distPlatform = platform;
  document.querySelectorAll('#dist-platform-row .ideas-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadHubs();
}

function onDistNicheInput() {
  clearTimeout(_distNicheTimer);
  _distNicheTimer = setTimeout(loadDistData, 400);
}

function loadDistData() { loadHubs(); loadRedditPanel(); loadPeerList(); }

async function loadHubs() {
  const niche = ($('dist-niche-input')?.value || '').trim();
  const list = $('dist-hub-list');
  if (!list) return;
  list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading\u2026</p>';
  try {
    const params = new URLSearchParams({ niche, tier: distTier, platform: distPlatform });
    const res = await fetch(`/api/hubs?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load hubs');
    const data = await res.json();
    renderHubList(data.hubs || []);
  } catch (e) {
    list.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(e.message)}</p>`;
  }
}

function renderHubList(hubs) {
  const list = $('dist-hub-list');
  if (!list) return;
  if (!hubs.length) {
    list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">No hubs saved for this niche yet \u2014 search for one below and add it.</p>';
    return;
  }
  const tierLabel = { micro: 'Micro', mid: 'Mid-Tier', mega: 'Mega' };
  list.innerHTML = hubs.map(h => {
    const tags = (h.hashtags || []);
    const checked = tags.length && tags.every(t => state.hubHashtags.includes(t)) ? 'checked' : '';
    const delBtn = currentUser.is_admin
      ? `<button class="history-item-del" title="Delete hub" onclick="deleteHubQUE('${h.id}')">\u2715</button>`
      : '';
    const flagBadge = h.status === 'flagged'
      ? `<span class="hub-flag-badge" title="Community-flagged as possibly inactive">\u26a0\ufe0f Flagged (${h.flag_count})</span>`
      : (h.flag_count > 0 ? `<span class="hub-flag-badge hub-flag-mild" title="Some users reported this hub">\u26a0\ufe0f ${h.flag_count} report${h.flag_count === 1 ? '' : 's'}</span>` : '');
    const reportBtn = h.reported_by_me
      ? `<span class="hub-report-done">Reported \u2713</span>`
      : `<button class="hub-report-btn" type="button" onclick="openReportModal('${h.id}','${escAttr(h.handle)}')">\ud83d\udea9 Report</button>`;
    const profileUrl = h.platform === 'tiktok'
      ? `https://www.tiktok.com/@${escAttr(h.handle)}`
      : `https://www.instagram.com/${escAttr(h.handle)}/`;
    return `
      <div class="hub-card" data-id="${escAttr(h.id)}">
        <div class="hub-card-hdr">
          <a href="${profileUrl}" target="_blank" rel="noopener" class="hub-handle">${h.platform === 'tiktok' ? '\ud83c\udfb5' : '\ud83d\udcf8'} @${escHtml(h.handle)}</a>
          <span class="hub-tier-badge hub-tier-${escAttr(h.tier)}">${tierLabel[h.tier] || h.tier}</span>
          ${delBtn}
        </div>
        ${flagBadge}
        ${h.bio_snippet ? `<p class="hub-bio">${escHtml(h.bio_snippet)}</p>` : ''}
        ${h.submission_rule ? `<p class="hub-rule"><strong>Submission:</strong> ${escHtml(h.submission_rule)}</p>` : ''}
        ${tags.length ? `
          <label class="hub-hashtag-row">
            <input type="checkbox" ${checked} onchange="toggleHub(${JSON.stringify(h).replace(/"/g, '&quot;')}, this)">
            <span>Use tags: ${tags.map(t => `#${escHtml(t)}`).join(' ')}</span>
          </label>` : ''}
        <div class="hub-card-footer">${reportBtn}</div>
      </div>`;
  }).join('');
}

let _reportHubId = null;

function openReportModal(hubId, handle) {
  _reportHubId = hubId;
  const label = $('report-hub-label');
  if (label) label.textContent = `@${handle}`;
  const modal = $('report-hub-modal');
  if (modal) modal.style.cssText = 'display:flex';
}

function closeReportModal() { hide('report-hub-modal'); _reportHubId = null; }

async function submitHubReport() {
  if (!_reportHubId) return;
  const reason = $('report-hub-reason')?.value || 'inactive';
  const note = ($('report-hub-note')?.value || '').trim();
  try {
    const res = await fetch(`/api/hubs/${_reportHubId}/report`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, note }) });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    toast('Thanks \u2014 report submitted', 'success');
    closeReportModal();
    const noteEl = $('report-hub-note'); if (noteEl) noteEl.value = '';
    loadHubs();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

function toggleHub(hub, checkboxEl) {
  const tags = hub.hashtags || [];
  if (checkboxEl.checked) {
    tags.forEach(t => { if (!state.hubHashtags.includes(t)) state.hubHashtags.push(t); });
    if (!state.selectedHubs.some(h => h.id === hub.id)) state.selectedHubs.push(hub);
  } else {
    state.hubHashtags = state.hubHashtags.filter(t => !tags.includes(t));
    state.selectedHubs = state.selectedHubs.filter(h => h.id !== hub.id);
  }
  renderSelectedHashtags();
}

function clearHubHashtags() {
  state.hubHashtags = [];
  state.selectedHubs = [];
  document.querySelectorAll('#dist-hub-list input[type=checkbox]').forEach(cb => cb.checked = false);
  renderSelectedHashtags();
}

// ---------------------------------------------------------------------------
// Pre-Publish Checklist — lightweight reminder helper, purely client-side
// (no backend state; checkboxes reset each time it's opened).
// ---------------------------------------------------------------------------
function openChecklist() {
  const modal = $('checklist-modal');
  if (!modal) return;
  modal.style.cssText = 'display:flex';
  renderChecklist();
}

function closeChecklist() { hide('checklist-modal'); }

function renderChecklist() {
  const body = $('checklist-content');
  if (!body) return;
  const hubs = state.selectedHubs || [];
  const tags = state.hubHashtags || [];
  const tierLabel = { micro: 'Micro', mid: 'Mid-Tier', mega: 'Mega' };
  let html = `<label class="checklist-item"><input type="checkbox"><span>Caption copied and ready to paste</span></label>`;

  if (tags.length) {
    html += `<label class="checklist-item"><input type="checkbox"><span>Required hashtags included: ${tags.map(t => `#${escHtml(t)}`).join(' ')}</span></label>`;
  }

  if (hubs.length) {
    html += `<div class="section-label" style="margin-top:12px">Feature Hub Submission Steps</div>`;
    html += hubs.map(h => `
      <label class="checklist-item">
        <input type="checkbox">
        <span><strong>@${escHtml(h.handle)}</strong> (${tierLabel[h.tier] || h.tier}) — ${escHtml(h.submission_rule || "Follow their bio for submission instructions")}</span>
      </label>`).join('');
    html += `<label class="checklist-item"><input type="checkbox"><span>Reviewed each hub's posting norms before submitting</span></label>`;
  } else {
    html += `<p class="ideas-hint" style="margin-top:10px">Select hubs in the Distribution &amp; Tags panel to get per-hub submission reminders here.</p>`;
  }

  body.innerHTML = html;
}

async function scoreHook(mode, btn) {
  const text = state.results?.[mode];
  if (!text) return;
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '\u2026';
  try {
    const res = await fetch('/api/hook-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    openHookScoreModal(data);
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

function openHookScoreModal(data) {
  const modal = $('hook-score-modal');
  const body = $('hook-score-content');
  if (!modal || !body) return;
  if (data.score == null) {
    body.innerHTML = `<p class="ideas-hint">${escHtml(data.feedback || 'Could not score this hook right now.')}</p>`;
  } else {
    const alts = (data.alternatives || []).map(a => `
      <div class="hook-alt" onclick="copyText(this,'${escAttr(a)}')" title="Click to copy">
        <span>${escHtml(a)}</span><span class="hook-alt-copy">Copy</span>
      </div>`).join('');
    body.innerHTML = `
      <div class="hook-score-circle">${data.score}<span>/10</span></div>
      <p class="hook-score-feedback">${escHtml(data.feedback || '')}</p>
      ${alts ? `<div class="section-label" style="margin-top:14px">Stronger Alternatives</div>${alts}` : ''}
    `;
  }
  modal.style.cssText = 'display:flex';
}

function closeHookScore() { hide('hook-score-modal'); }

async function generateAltText(btn) {
  if (!state.imageB64) { toast('No image loaded', 'error'); return; }
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '\u2026';
  try {
    const res = await fetch('/api/alt-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64: state.imageB64 }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    openAltTextModal(data.alt_text || '');
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

function openAltTextModal(altText) {
  const modal = $('hook-score-modal');
  const body = $('hook-score-content');
  if (!modal || !body) return;
  body.innerHTML = `
    <div class="section-label">Alt Text</div>
    <div class="hook-alt" onclick="copyText(this,'${escAttr(altText)}')" title="Click to copy">
      <span>${escHtml(altText)}</span><span class="hook-alt-copy">Copy</span>
    </div>
  `;
  modal.style.cssText = 'display:flex';
}

// ---------------------------------------------------------------------------
// Schedule Queue (internal planning calendar)
// ---------------------------------------------------------------------------

let scheduleTab = 'upcoming';
let scheduleItems = [];
let scheduleView = 'list';
let calendarMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
let selectedCalDay = null;

function openSchedule() {
  show('schedule-modal');
  loadScheduleList();
}
function closeSchedule() { hide('schedule-modal'); }

function toggleAddScheduleForm() {
  const form = $('add-schedule-form');
  if (!form) return;
  form.style.display = form.style.display === 'none' ? '' : 'none';
}

function openScheduleForResult(mode) {
  const text = state.results?.[mode];
  show('schedule-modal');
  loadScheduleList();
  $('add-schedule-form').style.display = '';
  if (text) $('sched-content').value = text;
  if (state.platform) $('sched-platform').value = state.platform;
}

async function submitSchedule() {
  const content = ($('sched-content')?.value || '').trim();
  const dt = $('sched-datetime')?.value || '';
  if (!content) { toast('Enter content to schedule', 'error'); return; }
  if (!dt) { toast('Pick a date and time', 'error'); return; }
  try {
    const res = await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        platform: $('sched-platform')?.value || 'general',
        mode: 'post',
        scheduled_for: dt,
        thumb: state.imageB64 || null,
        notes: ($('sched-notes')?.value || '').trim(),
      }),
    });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    toast('Added to schedule queue', 'success');
    $('sched-content').value = ''; $('sched-datetime').value = ''; $('sched-notes').value = '';
    $('add-schedule-form').style.display = 'none';
    loadScheduleList();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

function setScheduleTab(tab, btn) {
  scheduleTab = tab;
  document.querySelectorAll('#schedule-tabs .ideas-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderScheduleList();
}

async function loadScheduleList() {
  const list = $('schedule-list');
  if (!list) return;
  list.innerHTML = '<p class="history-empty">Loading\u2026</p>';
  try {
    const res = await fetch('/api/schedule');
    if (!res.ok) throw new Error('Failed to load');
    scheduleItems = await res.json();
    renderScheduleList();
    renderScheduleCalendar();
  } catch {
    list.innerHTML = '<p class="history-empty" style="color:var(--error)">Failed to load</p>';
  }
}

function setScheduleView(view, btn) {
  scheduleView = view;
  document.querySelectorAll('#schedule-view-toggle .ideas-type-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  $('schedule-list-view').style.display = view === 'list' ? '' : 'none';
  $('schedule-calendar-view').style.display = view === 'calendar' ? '' : 'none';
  if (view === 'calendar') renderScheduleCalendar();
}

function shiftCalendarMonth(delta) {
  calendarMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + delta, 1);
  selectedCalDay = null;
  renderScheduleCalendar();
}

function renderScheduleCalendar() {
  const grid = $('schedule-calendar-grid');
  const label = $('schedule-cal-label');
  if (!grid || !label) return;
  const year = calendarMonth.getFullYear(), month = calendarMonth.getMonth();
  label.textContent = calendarMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const todayStr = new Date().toDateString();

  const itemsByDay = {};
  scheduleItems.forEach(it => {
    const d = new Date(it.scheduled_for);
    if (d.getFullYear() === year && d.getMonth() === month) {
      const key = d.getDate();
      (itemsByDay[key] = itemsByDay[key] || []).push(it);
    }
  });

  let html = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => `<div class="schedule-cal-dow">${d}</div>`).join('');
  for (let i = 0; i < firstDow; i++) html += `<div class="schedule-cal-day empty"></div>`;
  for (let day = 1; day <= daysInMonth; day++) {
    const dayItems = itemsByDay[day] || [];
    const cellDate = new Date(year, month, day);
    const isToday = cellDate.toDateString() === todayStr;
    const isSelected = selectedCalDay === day;
    const dots = dayItems.slice(0, 4).map(it => {
      const overdue = it.status === 'pending' && new Date(it.scheduled_for) < new Date();
      const cls = overdue ? 'overdue' : (it.status === 'posted' ? 'posted' : (it.status === 'skipped' ? 'skipped' : ''));
      return `<span class="schedule-cal-dot ${cls}"></span>`;
    }).join('');
    const more = dayItems.length > 4 ? `<div class="schedule-cal-more">+${dayItems.length - 4} more</div>` : '';
    html += `<div class="schedule-cal-day${isToday ? ' today' : ''}${isSelected ? ' selected' : ''}" onclick="selectCalendarDay(${day})">
      <div class="schedule-cal-daynum">${day}</div>
      <div class="schedule-cal-dot-row">${dots}</div>
      ${more}
    </div>`;
  }
  grid.innerHTML = html;
  renderDayDetail();
}

function selectCalendarDay(day) {
  selectedCalDay = day;
  renderScheduleCalendar();
}

function renderDayDetail() {
  const detail = $('schedule-day-detail');
  if (!detail) return;
  if (selectedCalDay == null) { detail.innerHTML = ''; return; }
  const year = calendarMonth.getFullYear(), month = calendarMonth.getMonth(), day = selectedCalDay;
  const dayItems = scheduleItems.filter(it => {
    const d = new Date(it.scheduled_for);
    return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
  });
  if (!dayItems.length) { detail.innerHTML = '<p class="ideas-hint">Nothing scheduled this day.</p>'; return; }
  const dateLabel = new Date(year, month, day).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  detail.innerHTML = `<div class="section-label">${dateLabel}</div>`;
  const list = document.createElement('div'); list.className = 'history-list';
  dayItems.forEach(it => list.appendChild(buildScheduleItem(it)));
  detail.appendChild(list);
}

function renderScheduleList() {
  const list = $('schedule-list');
  if (!list) return;
  const now = new Date();
  const filtered = scheduleItems.filter(it => {
    const due = new Date(it.scheduled_for);
    if (scheduleTab === 'upcoming') return it.status === 'pending';
    return it.status !== 'pending' || due < now;
  });
  if (!filtered.length) {
    list.innerHTML = `<p class="history-empty">No ${scheduleTab} scheduled posts.</p>`;
    return;
  }
  list.innerHTML = '';
  filtered.forEach(it => list.appendChild(buildScheduleItem(it)));
}

function buildScheduleItem(item) {
  const div = document.createElement('div'); div.className = 'history-item';
  const due = new Date(item.scheduled_for);
  const overdue = item.status === 'pending' && due < new Date();
  const dateStr = due.toLocaleString();
  const statusLabel = { pending: overdue ? 'Overdue' : 'Pending', posted: 'Posted \u2713', skipped: 'Skipped' }[item.status] || item.status;
  const thumbHtml = item.thumb ? `<img class="history-thumb" src="${item.thumb}" alt="">` : `<div class="history-thumb-placeholder">\ud83d\udcc5</div>`;
  const actionsHtml = item.status === 'pending' ? `
    <div class="history-feedback" onclick="event.stopPropagation()">
      <button class="btn-wiz-secondary" style="padding:4px 10px;font-size:0.75rem" onclick="updateSchedule('${item.id}','posted')">Mark Posted</button>
      <button class="btn-wiz-secondary" style="padding:4px 10px;font-size:0.75rem" onclick="updateSchedule('${item.id}','skipped')">Skip</button>
    </div>` : '';
  div.innerHTML = `${thumbHtml}
    <div class="history-meta">
      <div class="history-mode">${item.platform || 'general'} \u00b7 <span style="color:${overdue ? 'var(--error)' : 'inherit'}">${statusLabel}</span></div>
      <div class="history-date">${dateStr}</div>
      <div class="history-preview">${escHtml((item.content || '').slice(0, 80))}${(item.content || '').length >= 80 ? '\u2026' : ''}</div>
      ${actionsHtml}
    </div>
    <button class="history-item-del" onclick="deleteSchedule('${item.id}',this.closest('.history-item'))" title="Delete">\u2715</button>`;
  return div;
}

async function updateSchedule(id, status) {
  try {
    const res = await fetch(`/api/schedule/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error('Failed to update');
    toast(status === 'posted' ? 'Marked as posted' : 'Skipped', 'success');
    loadScheduleList();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function deleteSchedule(id, el) {
  try {
    await fetch(`/api/schedule/${id}`, { method: 'DELETE' });
    el.remove();
    toast('Removed from queue', 'success');
  } catch {
    toast('Delete failed', 'error');
  }
}

// ---------------------------------------------------------------------------
// Analytics Dashboard
// ---------------------------------------------------------------------------

function openAnalytics() {
  show('analytics-modal');
  loadAnalytics();
}
function closeAnalytics() { hide('analytics-modal'); }

async function loadAnalytics() {
  const content = $('analytics-content');
  if (!content) return;
  content.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading\u2026</p>';
  try {
    const res = await fetch('/api/analytics');
    if (!res.ok) throw new Error('Failed to load analytics');
    const data = await res.json();
    renderAnalytics(data);
  } catch (e) {
    content.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0;color:var(--error)">${escHtml(e.message)}</p>`;
  }
}

function renderAnalytics(data) {
  const content = $('analytics-content');
  if (!content) return;
  const s = data.streak || {};
  const eng = data.engagement_totals || {};
  const platformHtml = (data.by_platform || []).map(p => `
    <div class="hub-card"><p class="hub-bio"><strong>${escHtml(p.platform)}</strong> \u2014 ${p.count} post${p.count === 1 ? '' : 's'}${p.avg_rating != null ? ` \u00b7 avg ${p.avg_rating}\u2605` : ''}</p></div>
  `).join('') || '<p class="ideas-hint">No data yet.</p>';
  const modeHtml = (data.by_mode || []).map(m => `
    <div class="hub-card"><p class="hub-bio"><strong>${MODE_META[m.mode]?.label || m.mode}</strong> \u2014 ${m.count}</p></div>
  `).join('') || '<p class="ideas-hint">No data yet.</p>';
  const styleHtml = (data.by_style || []).map(s => `
    <div class="hub-card"><p class="hub-bio"><strong>${escHtml(s.label)}</strong> \u2014 ${s.count} caption${s.count === 1 ? '' : 's'}${s.avg_rating != null ? ` \u00b7 avg ${s.avg_rating}\u2605` : ''}</p></div>
  `).join('') || '<p class="ideas-hint">Pick a caption style (Hook, Story, Question\u2026) when generating to start tracking which performs best.</p>';
  const bestPost = data.best_post
    ? `<div class="hub-card"><p class="hub-bio">${escHtml(data.best_post.mode)} \u00b7 ${escHtml(data.best_post.platform)} \u2014 ${data.best_post.likes} likes, ${data.best_post.views} views</p></div>`
    : '<p class="ideas-hint">Log stats on a History item to see your best performer here.</p>';
  const bti = data.best_time_insight;
  const bestTimeHtml = bti
    ? `<div class="hub-card"><p class="hub-bio">\ud83d\udcc8 Your posts tend to rate highest on <strong>${escHtml(bti.day)}</strong> during the <strong>${escHtml(bti.time_of_day)}</strong> (avg ${bti.avg_rating}\u2605 across ${bti.sample_size} post${bti.sample_size === 1 ? '' : 's'}).</p></div>`
    : '<p class="ideas-hint">Mark posts as Posted and rate them to unlock a best-time-to-post insight once you have a few data points.</p>';

  content.innerHTML = `
    <div class="analytics-stat-grid">
      <div class="analytics-stat-card"><div class="analytics-stat-num">${data.total_generations}</div><div class="analytics-stat-label">Total Generations</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">${data.total_posted}</div><div class="analytics-stat-label">Marked Posted</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">${data.avg_rating ?? '\u2014'}</div><div class="analytics-stat-label">Avg Rating</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">\ud83d\udd25 ${s.current_streak || 0}</div><div class="analytics-stat-label">Current Streak</div></div>
    </div>

    <div class="section-label" style="margin-top:16px">Last 30 Days</div>
    <canvas id="analytics-chart" width="600" height="120" style="width:100%;height:120px;margin:8px 0 4px"></canvas>

    <div class="section-label" style="margin-top:16px">By Platform</div>
    ${platformHtml}

    <div class="section-label" style="margin-top:16px">By Mode</div>
    ${modeHtml}

    <div class="section-label" style="margin-top:16px">By Caption Style</div>
    ${styleHtml}

    <div class="section-label" style="margin-top:16px">Engagement (manually logged)</div>
    <div class="analytics-stat-grid">
      <div class="analytics-stat-card"><div class="analytics-stat-num">${eng.likes || 0}</div><div class="analytics-stat-label">Likes</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">${eng.views || 0}</div><div class="analytics-stat-label">Views</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">${eng.comments || 0}</div><div class="analytics-stat-label">Comments</div></div>
      <div class="analytics-stat-card"><div class="analytics-stat-num">${eng.shares || 0}</div><div class="analytics-stat-label">Shares</div></div>
    </div>
    <p class="ideas-hint" style="margin-top:8px">No live Instagram/TikTok API connection yet \u2014 log real numbers from your platform's insights on any History item to track them here.</p>
    <div class="section-label" style="margin-top:12px">Best Performer</div>
    ${bestPost}
    <div class="section-label" style="margin-top:12px">Best Time to Post</div>
    ${bestTimeHtml}
  `;
  drawAnalyticsChart(data.daily_activity || []);
}

function drawAnalyticsChart(daily) {
  const canvas = $('analytics-chart');
  if (!canvas || !daily.length) return;
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  const w = canvas.width = rect.width || 600;
  const h = canvas.height = 120;
  ctx.clearRect(0, 0, w, h);
  const max = Math.max(1, ...daily.map(d => d.count));
  const barW = w / daily.length;
  const styles = getComputedStyle(document.documentElement);
  ctx.fillStyle = styles.getPropertyValue('--accent').trim() || '#6366f1';
  daily.forEach((d, i) => {
    const barH = (d.count / max) * (h - 10);
    ctx.fillRect(i * barW + 1, h - barH, Math.max(1, barW - 2), barH);
  });
}

function renderSelectedHashtags() {
  const footer = $('dist-hashtag-footer');
  const row = $('dist-selected-hashtags');
  if (!footer || !row) return;
  if (!state.hubHashtags.length) { footer.style.display = 'none'; row.innerHTML = ''; return; }
  footer.style.display = '';
  row.innerHTML = state.hubHashtags.map(t => `<span class="dist-chip">#${escHtml(t)}</span>`).join('');
}

async function loadRedditPanel() {
  const niche = ($('dist-niche-input')?.value || '').trim();
  const list = $('dist-reddit-list');
  if (!list) return;
  list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading\u2026</p>';
  try {
    const res = await fetch(`/api/reddit-panel?niche=${encodeURIComponent(niche)}`);
    if (!res.ok) throw new Error('Failed to load subreddits');
    const data = await res.json();
    renderRedditList(data.subreddits || []);
  } catch (e) {
    list.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(e.message)}</p>`;
  }
}

function renderRedditList(subs) {
  const list = $('dist-reddit-list');
  if (!list) return;
  if (!subs.length) { list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">No matches \u2014 try a broader niche keyword.</p>'; return; }
  list.innerHTML = subs.map(s => `
    <div class="hub-card">
      <div class="hub-card-hdr">
        <a href="https://www.reddit.com/r/${escAttr(s.subreddit)}/" target="_blank" rel="noopener" class="hub-handle">r/${escHtml(s.subreddit)}</a>
      </div>
      <p class="hub-bio">${escHtml(s.desc)}</p>
      <p class="hub-rule"><strong>Posting norms:</strong> ${escHtml(s.norms)}</p>
    </div>`).join('');
}

// ---------------------------------------------------------------------------
// Targeting Vault \u2014 named, reusable snapshots of a hub + hashtag selection.
// ---------------------------------------------------------------------------
async function loadVaults() {
  const list = $('dist-vault-list');
  if (!list) return;
  list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading\u2026</p>';
  try {
    const res = await fetch('/api/vaults');
    if (!res.ok) throw new Error('Failed to load vaults');
    const data = await res.json();
    renderVaultList(data.vaults || []);
  } catch (e) {
    list.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(e.message)}</p>`;
  }
}

function renderVaultList(vaults) {
  const list = $('dist-vault-list');
  if (!list) return;
  if (!vaults.length) {
    list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">No vaults saved yet \u2014 pick some hubs/hashtags, then use \u201cSave Current\u201d above.</p>';
    return;
  }
  list.innerHTML = vaults.map(v => `
    <div class="hub-card" data-id="${escAttr(v.id)}">
      <div class="hub-card-hdr">
        <span class="hub-handle">\ud83d\udcbe ${escHtml(v.name)}</span>
        <button class="history-item-del" title="Delete vault" onclick="deleteVaultQUE('${v.id}')">\u2715</button>
      </div>
      ${v.niche ? `<p class="hub-bio"><strong>Niche:</strong> ${escHtml(v.niche)}</p>` : ''}
      <p class="hub-rule">${v.hubs.length} hub${v.hubs.length === 1 ? '' : 's'}${v.hashtags.length ? `, tags: ${v.hashtags.map(t => `#${escHtml(t)}`).join(' ')}` : ''}</p>
      <button class="btn-wiz-secondary" type="button" style="margin-top:4px" onclick="applyVault('${v.id}')">Load This Vault</button>
    </div>`).join('');
  window._distVaults = vaults;
}

async function saveVault() {
  const nameInput = $('vault-name-input');
  const name = (nameInput?.value || '').trim();
  if (!name) { toast('Enter a vault name first', 'error'); return; }
  if (!state.selectedHubs.length && !state.hubHashtags.length) { toast('Select at least one hub or hashtag first', 'error'); return; }
  try {
    const res = await fetch('/api/vaults', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, niche: ($('dist-niche-input')?.value || '').trim(), hubs: state.selectedHubs, hashtags: state.hubHashtags }) });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    toast('Vault saved!', 'success');
    if (nameInput) nameInput.value = '';
    loadVaults();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

function applyVault(id) {
  const vault = (window._distVaults || []).find(v => v.id === id);
  if (!vault) return;
  state.selectedHubs = vault.hubs.slice();
  state.hubHashtags = vault.hashtags.slice();
  renderSelectedHashtags();
  toast(`Loaded "${vault.name}"`, 'success');
  document.querySelectorAll('#dist-tabs .ideas-type-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('#dist-tabs [data-tab="instagram"]')?.classList.add('active');
  $('dist-instagram-panel').style.display = '';
  $('dist-reddit-panel').style.display = 'none';
  $('dist-vault-panel').style.display = 'none';
  if (vault.niche && $('dist-niche-input')) $('dist-niche-input').value = vault.niche;
  loadHubs();
}

async function deleteVaultQUE(id) {
  try {
    const res = await fetch(`/api/vaults/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    loadVaults();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function loadMyCreatorProfile() {
  try {
    const res = await fetch('/api/creators/me');
    if (!res.ok) return;
    const data = await res.json();
    const p = data.profile;
    if (!p) return;
    if ($('peer-my-platform')) $('peer-my-platform').value = p.platform || 'instagram';
    if ($('peer-my-handle')) $('peer-my-handle').value = p.handle || '';
    if ($('peer-my-niche')) $('peer-my-niche').value = p.niche || '';
    if ($('peer-my-tier')) $('peer-my-tier').value = p.tier || 'micro';
    if ($('peer-my-pitch')) $('peer-my-pitch').value = p.pitch || '';
  } catch (e) { /* ignore */ }
}

async function saveCreatorProfile() {
  const handle = ($('peer-my-handle')?.value || '').trim();
  const niche = ($('peer-my-niche')?.value || '').trim();
  if (!handle || !niche) {
    toast('Handle and niche are required', 'error');
    return;
  }
  const body = {
    platform: $('peer-my-platform')?.value || 'instagram',
    handle,
    niche,
    tier: $('peer-my-tier')?.value || 'micro',
    pitch: ($('peer-my-pitch')?.value || '').trim(),
  };
  try {
    const res = await fetch('/api/creators', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Save failed');
    toast('Listing saved \u2014 other creators can now find you', 'success');
    loadPeerList();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function removeCreatorProfile() {
  try {
    const res = await fetch('/api/creators/me', { method: 'DELETE' });
    if (!res.ok) throw new Error('Remove failed');
    ['peer-my-handle', 'peer-my-niche', 'peer-my-pitch'].forEach(id => { if ($(id)) $(id).value = ''; });
    toast('Listing removed', 'success');
    loadPeerList();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function loadPeerList() {
  const list = $('dist-peer-list');
  if (!list) return;
  const niche = ($('dist-niche-input')?.value || '').trim();
  list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Loading\u2026</p>';
  try {
    const params = new URLSearchParams({ niche });
    const res = await fetch(`/api/creators?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load creators');
    const data = await res.json();
    renderPeerList(data.creators || []);
  } catch (e) {
    list.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(e.message)}</p>`;
  }
}

function renderPeerList(creators) {
  const list = $('dist-peer-list');
  if (!list) return;
  if (!creators.length) {
    list.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">No creators listed for this niche yet.</p>';
    return;
  }
  const tierLabel = { micro: 'Micro', mid: 'Mid-Tier', mega: 'Mega' };
  list.innerHTML = creators.map(c => {
    const profileUrl = c.platform === 'tiktok'
      ? `https://www.tiktok.com/@${escAttr(c.handle)}`
      : `https://www.instagram.com/${escAttr(c.handle)}/`;
    return `<div class="hub-card">
      <div class="hub-card-hdr">
        <a class="hub-handle" href="${profileUrl}" target="_blank" rel="noopener">@${escHtml(c.handle)}</a>
        <span class="hub-tier-badge hub-tier-${c.tier}">${tierLabel[c.tier] || c.tier}</span>
      </div>
      <p class="hub-bio">${escHtml(c.niche)}</p>
      ${c.pitch ? `<p class="hub-rule">${escHtml(c.pitch)}</p>` : ''}
    </div>`;
  }).join('');
}

async function checkTrends() {
  const niche = ($('dist-niche-input')?.value || '').trim();
  const content = $('dist-trends-content');
  if (!content) return;
  if (!niche) { toast('Enter a niche above first', 'error'); return; }
  const btn = $('btn-check-trends');
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Checking\u2026';
  content.innerHTML = '<p class="ideas-hint" style="text-align:center;padding:16px 0">Searching for current trends\u2026</p>';
  try {
    const res = await fetch('/api/trends', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ niche, platform: distPlatform || 'general' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    renderTrends(data);
  } catch (e) {
    content.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(e.message)}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

function renderTrends(data) {
  const content = $('dist-trends-content');
  if (!content) return;
  const trends = data.trends || [];
  const angles = data.angles || [];
  if (!trends.length && !angles.length) {
    content.innerHTML = `<p class="ideas-hint" style="text-align:center;padding:16px 0">${escHtml(data.raw ? 'Could not parse trend results \u2014 try again.' : 'No trends found for this niche right now.')}</p>`;
    return;
  }
  let html = '';
  if (trends.length) {
    html += `<div class="section-label">Trending This Week</div>` +
      trends.map(t => `<div class="hub-card"><p class="hub-bio">${escHtml(t)}</p></div>`).join('');
  }
  if (angles.length) {
    html += `<div class="section-label" style="margin-top:14px">Suggested Caption Angles</div>` +
      angles.map(a => `<div class="hub-card"><p class="hub-bio">${escHtml(a)}</p></div>`).join('');
  }
  content.innerHTML = html;
}

function openHubSearch(engine) {
  const niche = ($('dist-niche-input')?.value || '').trim() || 'feature page';
  const site = distPlatform === 'tiktok' ? 'tiktok.com' : 'instagram.com';
  let url;
  if (engine === 'google') {
    url = `https://www.google.com/search?q=${encodeURIComponent(`site:${site} "feature" "${niche}" "DM to feature"`)}`;
  } else if (distPlatform === 'tiktok') {
    url = `https://www.tiktok.com/search?q=${encodeURIComponent(niche + ' feature page')}`;
  } else {
    url = `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(niche + ' feature page')}`;
  }
  window.open(url, '_blank', 'noopener');
}

function toggleAddHubForm() {
  const f = $('add-hub-form');
  if (!f) return;
  const willShow = f.style.display === 'none';
  f.style.display = willShow ? '' : 'none';
  if (willShow) {
    const nicheInput = $('add-hub-niche');
    if (nicheInput && !nicheInput.value) nicheInput.value = ($('dist-niche-input')?.value || '').trim();
    const platformInput = $('add-hub-platform');
    if (platformInput) platformInput.value = distPlatform;
  }
}

async function submitAddHub() {
  const platform = $('add-hub-platform')?.value || 'instagram';
  const handle = ($('add-hub-handle')?.value || '').trim();
  const niche = ($('add-hub-niche')?.value || '').trim();
  const tier = $('add-hub-tier')?.value || 'micro';
  const bio = ($('add-hub-bio')?.value || '').trim();
  const rule = ($('add-hub-rule')?.value || '').trim();
  const hashtags = ($('add-hub-hashtags')?.value || '').split(',').map(t => t.trim().replace(/^#/, '')).filter(Boolean);
  if (!handle) { toast('Handle required', 'error'); return; }
  if (!niche) { toast('Niche required', 'error'); return; }
  try {
    const res = await fetch('/api/hubs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ handle, niche, tier, platform, bio_snippet: bio, submission_rule: rule, hashtags }) });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || res.statusText); }
    toast('Hub added!', 'success');
    ['add-hub-handle', 'add-hub-bio', 'add-hub-rule', 'add-hub-hashtags'].forEach(id => { const el = $(id); if (el) el.value = ''; });
    hide('add-hub-form');
    loadHubs();
  } catch (e) {
    toast(`Error: ${e.message}`, 'error');
  }
}

async function deleteHubQUE(id) {
  try {
    await fetch(`/api/hubs/${id}`, { method: 'DELETE' });
    toast('Hub removed', 'success');
    loadHubs();
  } catch { toast('Delete failed', 'error'); }
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
let _toastTimer;
function toast(msg, type = '') { const el = $('toast'); el.textContent = msg; el.className = `toast show ${type}`; clearTimeout(_toastTimer); _toastTimer = setTimeout(() => { el.className = 'toast'; }, 2400); }

// Surface otherwise-silent JS errors (e.g. a broken inline onclick handler) as a visible
// toast instead of a tap that appears to do nothing with no on-screen sign of failure.
window.addEventListener('error', (e) => { console.error('[Prism] uncaught error:', e.error || e.message); toast(`Error: ${e.message}`, 'error'); });
window.addEventListener('unhandledrejection', (e) => { console.error('[Prism] unhandled rejection:', e.reason); toast(`Error: ${e.reason?.message || e.reason}`, 'error'); });

// ---------------------------------------------------------------------------
// Escape helpers
// ---------------------------------------------------------------------------
function escHtml(str) { return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(str) { return String(str).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

// ---------------------------------------------------------------------------
// Carousel Logic
// ---------------------------------------------------------------------------
let currentSlide = 0;
function activateCarousel() {
  const container = $('results-carousel');
  if (!container) return;
  const slides = container.querySelectorAll('.carousel-slide');
  if (!slides.length) return;
  
  currentSlide = 0;
  container.scrollTo({ left: 0, behavior: 'instant' });

  // Remove streaming cursors from all finalized cards
  container.querySelectorAll('._stream-cursor').forEach(el => el.classList.remove('_stream-cursor'));
  
  const dotsContainer = $('carousel-dots');
  if (dotsContainer) {
    dotsContainer.innerHTML = '';
    slides.forEach((_, i) => {
      const d = document.createElement('div');
      d.className = 'carousel-dot' + (i === 0 ? ' active' : '');
      d.onclick = () => { currentSlide = i; updateCarousel(); };
      dotsContainer.appendChild(d);
    });
  }

  // Add result count badges
  slides.forEach((slide, i) => {
    const existing = slide.querySelector('.result-count-badge');
    if (existing) existing.remove();
    if (slides.length > 1) {
      const badge = document.createElement('div');
      badge.className = 'result-count-badge';
      badge.textContent = `${i + 1} of ${slides.length}`;
      slide.style.position = 'relative';
      slide.appendChild(badge);
    }
  });

  // Swipe hint on first result
  if (slides.length > 1) {
    const existingHint = container.parentElement.querySelector('.swipe-hint');
    if (!existingHint) {
      const hint = document.createElement('div');
      hint.className = 'swipe-hint';
      hint.textContent = '← Swipe for more results →';
      container.parentElement.style.position = 'relative';
      container.parentElement.appendChild(hint);
      setTimeout(() => { if (hint.parentElement) hint.remove(); }, 3500);
    }
  }
  
  // Listen for scroll snap to update dots
  container.addEventListener('scroll', () => {
    const w = container.clientWidth;
    const newSlide = Math.round(container.scrollLeft / w);
    if (newSlide !== currentSlide && newSlide >= 0 && newSlide < slides.length) {
      currentSlide = newSlide;
      updateCarouselUI(slides.length);
    }
  }, { passive: true });
  
  updateCarouselUI(slides.length);
}

function updateCarouselUI(total) {
  const dots = document.querySelectorAll('.carousel-dot');
  dots.forEach((d, i) => d.classList.toggle('active', i === currentSlide));
  
  const prevBtn = $('carousel-prev');
  const nextBtn = $('carousel-next');
  if (prevBtn) prevBtn.style.visibility = currentSlide > 0 ? 'visible' : 'hidden';
  if (nextBtn) nextBtn.style.visibility = currentSlide < total - 1 ? 'visible' : 'hidden';
}

function updateCarousel() {
  const container = $('results-carousel');
  if (!container) return;
  const slides = container.querySelectorAll('.carousel-slide');
  if (slides.length) {
    container.scrollTo({ left: currentSlide * container.clientWidth, behavior: 'smooth' });
    updateCarouselUI(slides.length);
  }
}

function carouselGo(dir) {
  const container = $('results-carousel');
  if (!container) return;
  const total = container.querySelectorAll('.carousel-slide').length;
  currentSlide += dir;
  if (currentSlide < 0) currentSlide = 0;
  if (currentSlide >= total) currentSlide = total - 1;
  updateCarousel();
}
