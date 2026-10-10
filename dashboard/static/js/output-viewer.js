/**
 * One preview/download contract for Completed Work and Synapse chat.
 * Opening a preview never clicks a download link or navigates away.
 */
class WorkhorseOutputViewer {
  constructor() {
    this.dialog = document.createElement('dialog');
    this.dialog.className = 'output-viewer';
    this.dialog.innerHTML = `
      <header class="output-viewer-header">
        <h3 id="output-viewer-title">Created work</h3>
        <button type="button" class="btn-cyber" data-close-preview aria-label="Close preview">Close</button>
      </header>
      <p class="output-viewer-note">View here first. Download only if you want to keep a copy.</p>
      <div class="output-viewer-body"></div>
      <footer><a class="btn-cyber" data-preview-download download>Download original</a></footer>`;
    this.dialog.setAttribute('aria-labelledby', 'output-viewer-title');
    document.body.appendChild(this.dialog);
    this.body = this.dialog.querySelector('.output-viewer-body');
    this.dialog.querySelector('[data-close-preview]').addEventListener('click', () => this.dialog.close());
    this.dialog.addEventListener('click', event => {
      if (event.target === this.dialog) {
        const rect = this.dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right ||
            event.clientY < rect.top || event.clientY > rect.bottom) this.dialog.close();
      }
    });
    this.dialog.addEventListener('close', () => {
      this.controller?.abort();
      this.body.replaceChildren();
    });
    document.addEventListener('click', event => {
      const button = event.target.closest('[data-workhorse-view]');
      if (!button) return;
      event.preventDefault();
      this.open(JSON.parse(button.dataset.workhorseView));
    });
  }

  escape(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
  }

  normalize(item) {
    const download = item.download_url || item.url;
    const url = new URL(download, location.origin);
    if (url.origin !== location.origin || url.pathname !== '/api/outputs/file') {
      throw new Error('This output does not have a WORKHORSE file link.');
    }
    const filename = item.filename || item.title || '';
    const ext = filename.split('.').pop().toLowerCase();
    const types = {
      png: 'image', jpg: 'image', jpeg: 'image', webp: 'image', gif: 'image',
      mp4: 'video', mov: 'video', webm: 'video', mp3: 'audio', wav: 'audio', ogg: 'audio',
      glb: 'model_3d', pdf: 'document', html: 'document', htm: 'document',
      txt: 'text', md: 'text', csv: 'text', json: 'text', zip: 'archive'
    };
    return {
      filename, title: item.title || filename,
      preview_type: item.preview_type === undefined ? (types[ext] || null) : item.preview_type,
      download_url: url.pathname + url.search,
      preview_url: '/api/outputs/preview' + url.search
    };
  }

  actions(item) {
    const media = this.normalize(item);
    return `<div class="output-card-actions">
      <button type="button" class="btn-cyber" data-workhorse-view="${this.escape(JSON.stringify(media))}">View</button>
      <a class="btn-cyber" href="${this.escape(media.download_url)}" download>Download</a>
    </div>`;
  }

  async request(url, signal) {
    const response = await fetch(url, { signal });
    if (response.redirected) throw new Error('Please sign in to WORKHORSE again to view this file.');
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || `Preview failed (${response.status})`);
    }
    return response;
  }

  async open(item) {
    this.controller?.abort();
    this.controller = new AbortController();
    const signal = this.controller.signal;
    this.body.textContent = 'Loading preview...';
    this.dialog.querySelector('h3').textContent = item.title || item.filename;
    const download = this.dialog.querySelector('[data-preview-download]');
    download.href = item.download_url;
    if (!this.dialog.open) this.dialog.showModal();
    try {
      if (item.preview_type === 'archive') {
        const url = new URL(item.preview_url, location.origin);
        url.pathname = '/api/outputs/archive';
        const response = await this.request(url, signal);
        const data = await response.json();
        if (signal.aborted) return;
        this.renderArchive(data.items, signal);
      } else {
        await this.renderPreview(item, this.body, signal);
      }
    } catch (error) {
      if (signal.aborted) return;
      this.body.textContent = error.message;
      this.body.setAttribute('role', 'alert');
    }
  }

  renderArchive(items, signal) {
    this.body.replaceChildren();
    const note = document.createElement('p');
    note.textContent = 'Choose a file to view inside this package. Unsupported formats require the original ZIP. HTML previews are static; scripts and external assets are disabled.';
    const list = document.createElement('div');
    list.className = 'output-archive-list';
    const pane = document.createElement('div');
    pane.className = 'output-archive-preview';
    pane.textContent = items.length ? 'Select a file above to preview it.' : 'This package has no readable files.';
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'output-archive-row';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn-cyber';
      button.textContent = item.filename;
      button.disabled = !item.preview_type;
      button.title = item.preview_type ? 'View file' : 'Preview unavailable for this format or size';
      button.addEventListener('click', async () => {
        this.memberController?.abort();
        this.memberController = new AbortController();
        const memberSignal = this.memberController.signal;
        const cancel = () => this.memberController?.abort();
        signal.addEventListener('abort', cancel, { once: true });
        try {
          await this.renderPreview(item, pane, memberSignal);
        } catch (error) {
          if (!memberSignal.aborted) pane.textContent = error.message;
        } finally {
          signal.removeEventListener('abort', cancel);
        }
      });
      row.appendChild(button);
      if (item.download_url) {
        const link = document.createElement('a');
        link.className = 'btn-cyber';
        link.textContent = 'Download file';
        link.href = item.download_url;
        link.setAttribute('download', '');
        row.appendChild(link);
      }
      list.appendChild(row);
    }
    this.body.append(note, list, pane);
    signal.addEventListener('abort', () => this.memberController?.abort(), { once: true });
  }

  async renderPreview(item, pane, signal) {
    pane.replaceChildren();
    pane.removeAttribute('role');
    if (!item.preview_type) {
      pane.textContent = 'This format cannot be viewed in WORKHORSE. Use Download only if you want a copy. For 3D previews, generate a self-contained GLB file.';
      return;
    }
    if (item.preview_type === 'text') {
      const response = await this.request(item.preview_url, signal);
      if (Number(response.headers.get('content-length')) > 2 * 1024 * 1024) {
        throw new Error('Text file is too large for the viewer (2 MiB limit).');
      }
      const text = await response.text();
      if (signal.aborted) return;
      const pre = document.createElement('pre');
      pre.textContent = text;
      pane.appendChild(pre);
      return;
    }
    const tags = { image: 'img', video: 'video', audio: 'audio', model_3d: 'model-viewer', document: 'iframe' };
    const element = document.createElement(tags[item.preview_type]);
    element.className = 'output-preview-media';
    if (item.preview_type === 'image') element.alt = item.filename;
    if (['video', 'audio'].includes(item.preview_type)) {
      element.controls = true;
      element.preload = 'metadata';
      element.setAttribute('playsinline', '');
    }
    if (item.preview_type === 'model_3d') {
      element.setAttribute('camera-controls', '');
      element.setAttribute('touch-action', 'pan-y');
      element.setAttribute('alt', item.filename);
    }
    if (item.preview_type === 'document') {
      element.title = item.filename;
      element.setAttribute('sandbox', '');
    }
    element.addEventListener('error', () => {
      if (signal.aborted) return;
      const error = document.createElement('p');
      error.setAttribute('role', 'alert');
      error.textContent = 'Unable to display this file. It may be missing, damaged, or use a format/codec your browser cannot play. Download remains optional.';
      pane.appendChild(error);
    }, { once: true });
    element.src = item.preview_url;
    pane.appendChild(element);
  }
}

window.outputViewer = new WorkhorseOutputViewer();
