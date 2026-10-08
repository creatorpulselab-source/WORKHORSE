/**
 * WORKHORSE AI COMMAND CENTER • NEXT-GEN 3D REALISTIC CHARACTER ENGINE
 * 
 * Performance & Stability Architecture:
 *  - 100% Instant Zero-Delay WebGL Canvas Render on Page Load (0ms blocking)
 *  - Dual Kinetic States for every agent:
 *      * IDLE: Living ambient motion tailored to the character's persona
 *      * WORKING: High-energy operational overdrive motion
 *  - Interactive 360° Mouse & Touch Gaze Tracking (studio spotlight & specular sheen)
 *  - Interactive State Switcher ("⚡ TEST ACTIVE / 💤 IDLE")
 *  - Lazy On-Demand 3D GLB Viewport (mounts <model-viewer> only when user clicks 3D button)
 */

(function () {
  'use strict';

  const CHARACTERS = {
    synapse: {
      id: 'synapse',
      name: 'Synapse',
      element: '[100 Fm]',
      color: [0.0, 0.95, 1.0],      // #00f2fe electric cyan
      glowHex: '#00f2fe',
      profile: 'neural',
      idle: { speed: 0.85, pitchAmp: 0.10, yawAmp: 0.08, bobAmp: 8.0, depthAmp: 0.065, glowPulse: 1.2 },
      working: { speed: 2.8, pitchAmp: 0.18, yawAmp: 0.22, bobAmp: 14.0, depthAmp: 0.095, glowPulse: 3.0 }
    },
    iris: {
      id: 'iris',
      name: 'Iris',
      element: '[77 Ir]',
      color: [0.97, 0.15, 0.52],    // #f72585 optical laser rose
      glowHex: '#f72585',
      profile: 'scanner',
      idle: { speed: 0.90, pitchAmp: 0.09, yawAmp: 0.18, bobAmp: 6.0, depthAmp: 0.060, glowPulse: 1.2 },
      working: { speed: 3.2, pitchAmp: 0.20, yawAmp: 0.35, bobAmp: 12.0, depthAmp: 0.090, glowPulse: 3.5 }
    },
    aura: {
      id: 'aura',
      name: 'Aura',
      element: '[79 Au]',
      color: [1.0, 0.82, 0.40],     // #ffd166 24K liquid gold
      glowHex: '#ffd166',
      profile: 'precession',
      idle: { speed: 0.70, pitchAmp: 0.11, yawAmp: 0.12, bobAmp: 7.0, depthAmp: 0.040, glowPulse: 1.1 },
      working: { speed: 2.2, pitchAmp: 0.22, yawAmp: 0.26, bobAmp: 14.0, depthAmp: 0.080, glowPulse: 3.2 }
    },
    echo: {
      id: 'echo',
      name: 'Echo',
      element: '[26 Fe]',
      color: [0.30, 0.79, 0.94],    // #4cc9f0 acoustic cyan
      glowHex: '#4cc9f0',
      profile: 'rhythm',
      idle: { speed: 1.30, pitchAmp: 0.10, yawAmp: 0.12, bobAmp: 9.0, depthAmp: 0.055, glowPulse: 1.4 },
      working: { speed: 3.8, pitchAmp: 0.28, yawAmp: 0.24, bobAmp: 18.0, depthAmp: 0.090, glowPulse: 3.8 }
    },
    forge: {
      id: 'forge',
      name: 'Forge',
      element: '[74 W]',
      color: [1.0, 0.42, 0.21],     // #ff6b35 molten tungsten orange
      glowHex: '#ff6b35',
      profile: 'hydraulic',
      idle: { speed: 1.0, pitchAmp: 0.12, yawAmp: 0.08, bobAmp: 8.0, depthAmp: 0.065, glowPulse: 1.3 },
      working: { speed: 3.0, pitchAmp: 0.30, yawAmp: 0.20, bobAmp: 16.0, depthAmp: 0.100, glowPulse: 3.6 }
    },
    cipher: {
      id: 'cipher',
      name: 'Cipher',
      element: '[82 Pb]',
      color: [0.65, 0.72, 0.82],    // #94a3b8 stealth titanium
      glowHex: '#94a3b8',
      profile: 'levitate',
      idle: { speed: 0.80, pitchAmp: 0.14, yawAmp: 0.12, bobAmp: 11.0, depthAmp: 0.070, glowPulse: 1.5 },
      working: { speed: 3.0, pitchAmp: 0.28, yawAmp: 0.26, bobAmp: 16.0, depthAmp: 0.095, glowPulse: 3.4 }
    },
    herald: {
      id: 'herald',
      name: 'Herald',
      element: '[33 As]',
      color: [0.06, 0.73, 0.51],    // #10b981 emerald green
      glowHex: '#10b981',
      profile: 'dispatch',
      idle: { speed: 0.90, pitchAmp: 0.10, yawAmp: 0.12, bobAmp: 7.0, depthAmp: 0.060, glowPulse: 1.3 },
      working: { speed: 3.4, pitchAmp: 0.22, yawAmp: 0.30, bobAmp: 15.0, depthAmp: 0.090, glowPulse: 3.5 }
    },
    mercury: {
      id: 'mercury',
      name: 'Mercury',
      element: '[80 Hg]',
      color: [0.66, 0.33, 0.97],    // #a855f7 electric violet
      glowHex: '#a855f7',
      profile: 'omni',
      idle: { speed: 1.10, pitchAmp: 0.12, yawAmp: 0.15, bobAmp: 9.0, depthAmp: 0.065, glowPulse: 1.4 },
      working: { speed: 3.2, pitchAmp: 0.24, yawAmp: 0.28, bobAmp: 16.0, depthAmp: 0.095, glowPulse: 3.6 }
    },
    scribe: {
      id: 'scribe',
      name: 'Scribe',
      element: '[6 C]',
      color: [0.94, 0.27, 0.27],    // #ef4444 ink-red
      glowHex: '#ef4444',
      profile: 'quill',
      idle: { speed: 1.00, pitchAmp: 0.10, yawAmp: 0.14, bobAmp: 7.5, depthAmp: 0.055, glowPulse: 1.3 },
      working: { speed: 3.4, pitchAmp: 0.20, yawAmp: 0.32, bobAmp: 15.0, depthAmp: 0.090, glowPulse: 3.5 }
    }
  };

  const VS_SOURCE = `
    attribute vec2 a_position;
    attribute vec2 a_texCoord;
    varying vec2 v_texCoord;
    void main() {
      gl_Position = vec4(a_position, 0.0, 1.0);
      v_texCoord = a_texCoord;
    }
  `;

  const FS_SOURCE = `
    precision mediump float;
    uniform sampler2D u_image;
    uniform sampler2D u_depth;
    uniform vec2 u_offset;      // mouse / touch tilt
    uniform vec2 u_idleOffset;  // kinetic 3D motion drift
    uniform vec3 u_glowColor;   // character aura
    uniform float u_energy;     // energy state (1.0 = idle, 2.6 = working)
    uniform float u_time;
    varying vec2 v_texCoord;

    void main() {
      float d = texture2D(u_depth, v_texCoord).r;

      // Volumetric Parallax displacement
      vec2 totalOffset = (u_offset + u_idleOffset) * (d - 0.45);
      vec2 displacedUV = v_texCoord - totalOffset;

      if (displacedUV.x < 0.0 || displacedUV.x > 1.0 || displacedUV.y < 0.0 || displacedUV.y > 1.0) {
        discard;
      }

      vec4 col = texture2D(u_image, displacedUV);
      if (col.a < 0.02) {
        discard;
      }

      // Dynamic normal calculation for PBR specular & metallic shine
      float stepX = 0.0035;
      float stepY = 0.0035;
      float dR = texture2D(u_depth, displacedUV + vec2(stepX, 0.0)).r;
      float dL = texture2D(u_depth, displacedUV - vec2(stepX, 0.0)).r;
      float dU = texture2D(u_depth, displacedUV + vec2(0.0, stepY)).r;
      float dD = texture2D(u_depth, displacedUV - vec2(0.0, stepY)).r;

      vec3 normal = normalize(vec3((dL - dR) * 3.8, (dD - dU) * 3.8, 1.0));
      vec2 lightCenter = vec2(0.5, 0.35) - u_offset * 1.6;
      vec3 lightDir = normalize(vec3(lightCenter - displacedUV, 0.50));

      // Specular highlight on metallic armor & glass visor
      float spec = pow(max(dot(normal, lightDir), 0.0), 16.0) * (0.45 * u_energy);
      
      // Dynamic metallic rim lighting
      float rim = pow(1.0 - max(normal.z, 0.0), 2.2) * (0.40 * u_energy);

      // Working state pulse burst
      float pulseWave = sin(u_time * 6.0) * 0.5 + 0.5;
      float workBoost = (u_energy > 1.5) ? (pulseWave * 0.25) : 0.0;

      // Combine PBR studio lighting
      col.rgb += u_glowColor * (spec + rim * 0.45 + workBoost);

      gl_FragColor = col;
    }
  `;

  class CharacterCard3D {
    constructor(containerEl, charKey) {
      this.container = containerEl;
      this.key = charKey;
      this.config = CHARACTERS[charKey] || CHARACTERS.synapse;
      this.state = 'idle';
      
      this.targetOffset = { x: 0, y: 0 };
      this.currentOffset = { x: 0, y: 0 };
      this.idleOffset = { x: 0, y: 0 };
      
      this.canvas = containerEl.querySelector('canvas');
      this.modelViewer = null;
      this.isGlbActive = false;

      this.initWebGL();
      this.bindMouseEvents();
      this.updateCardUI();
    }

    initWebGL() {
      if (!this.canvas) return;
      const gl = this.canvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: false });
      if (!gl) {
        return;
      }
      this.gl = gl;

      const vs = this.compileShader(gl.VERTEX_SHADER, VS_SOURCE);
      const fs = this.compileShader(gl.FRAGMENT_SHADER, FS_SOURCE);
      if (!vs || !fs) return;

      this.program = gl.createProgram();
      gl.attachShader(this.program, vs);
      gl.attachShader(this.program, fs);
      gl.linkProgram(this.program);
      gl.useProgram(this.program);

      const positions = new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]);
      const texCoords = new Float32Array([0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0]);

      this.posBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuf);
      gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

      this.texBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.texBuf);
      gl.bufferData(gl.ARRAY_BUFFER, texCoords, gl.STATIC_DRAW);

      this.uOffset = gl.getUniformLocation(this.program, 'u_offset');
      this.uIdleOffset = gl.getUniformLocation(this.program, 'u_idleOffset');
      this.uGlowColor = gl.getUniformLocation(this.program, 'u_glowColor');
      this.uEnergy = gl.getUniformLocation(this.program, 'u_energy');
      this.uTime = gl.getUniformLocation(this.program, 'u_time');
      this.uImage = gl.getUniformLocation(this.program, 'u_image');
      this.uDepth = gl.getUniformLocation(this.program, 'u_depth');

      this.loadTextures();
    }

    compileShader(type, src) {
      const s = this.gl.createShader(type);
      this.gl.shaderSource(s, src);
      this.gl.compileShader(s);
      return s;
    }

    loadTextures() {
      const gl = this.gl;
      const charImg = new Image();
      const depthImg = new Image();

      let charSrc = `/static/img/characters_3d/${this.key}_rig_char.png?v=20261006_v2`;
      let depthSrc = `/static/img/characters_3d/${this.key}_rig_depth.png?v=20261006_v2`;

      if (this.key === 'synapse') {
        charSrc = `/static/img/characters_3d/synapse_card_2x.png?v=20261006_v2`;
        depthSrc = `/static/img/characters_3d/cipher_rig_depth.png?v=20261006_v2`;
      }

      let loaded = 0;
      const checkDone = () => {
        loaded++;
        if (loaded === 2) {
          this.texChar = this.createTexture(charImg, 0);
          this.texDepth = this.createTexture(depthImg, 1);
          this.ready = true;
        }
      };

      charImg.crossOrigin = 'anonymous';
      depthImg.crossOrigin = 'anonymous';
      charImg.onload = checkDone;
      depthImg.onload = checkDone;
      charImg.src = charSrc;
      depthImg.src = depthSrc;
    }

    createTexture(img, unit) {
      const gl = this.gl;
      const tex = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      return tex;
    }

    bindMouseEvents() {
      const card = this.container.closest('.factory-chamber') || this.container;

      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
        this.targetOffset.x = nx * 0.035;
        this.targetOffset.y = -ny * 0.035;
      });

      card.addEventListener('mouseleave', () => {
        this.targetOffset.x = 0;
        this.targetOffset.y = 0;
      });
    }

    setState(newState) {
      this.state = newState === 'working' ? 'working' : 'idle';
      this.updateCardUI();
    }

    toggleState() {
      this.setState(this.state === 'idle' ? 'working' : 'idle');
    }

    updateCardUI() {
      const card = this.container.closest('.factory-chamber, .chemical-atom-node');
      if (!card) return;

      const meter = card.querySelector('.chamber-activity-meter');
      const light = card.querySelector('.chamber-status-light');
      const toggleBtn = card.querySelector('.btn-card-toggle-state, .btn-card-direct-state');

      if (this.state === 'working') {
        card.classList.add('working-chamber'); card.classList.add('working');
        if (meter) {
          meter.textContent = '⚡ ACTIVE · OVERDRIVE';
          meter.style.color = this.config.glowHex;
        }
        if (light) {
          light.style.background = this.config.glowHex;
          light.style.boxShadow = `0 0 12px ${this.config.glowHex}`;
        }
        if (toggleBtn) {
          toggleBtn.innerHTML = '⚡ ACTIVE';
          toggleBtn.classList.add('active');
        }
      } else {
        card.classList.remove('working-chamber'); card.classList.remove('working');
        if (meter) {
          meter.textContent = 'STANDBY · READY';
          meter.style.color = 'rgba(255, 255, 255, 0.7)';
        }
        if (light) {
          light.style.background = '#10b981';
          light.style.boxShadow = '0 0 8px #10b981';
        }
        if (toggleBtn) {
          toggleBtn.innerHTML = '💤 IDLE';
          toggleBtn.classList.remove('active');
        }
      }
    }

    updateKinematics(time) {
      const p = this.config[this.state] || this.config.idle;
      const speed = p.speed;
      const t = time * speed;

      switch (this.config.profile) {
        case 'neural':
          this.idleOffset.x = Math.sin(t * 0.9) * p.yawAmp + Math.cos(t * 1.8) * 0.02;
          this.idleOffset.y = Math.cos(t * 1.1) * p.pitchAmp + Math.sin(t * 2.2) * 0.015;
          break;
        case 'scanner':
          this.idleOffset.x = Math.sin(t * 1.2) * p.yawAmp;
          this.idleOffset.y = Math.cos(t * 0.7) * p.pitchAmp * 0.6;
          break;
        case 'precession':
          this.idleOffset.x = Math.sin(t * 0.8) * p.yawAmp;
          this.idleOffset.y = Math.cos(t * 0.8) * p.pitchAmp;
          break;
        case 'rhythm':
          this.idleOffset.x = Math.sin(t * 0.7) * (p.yawAmp * 0.5);
          this.idleOffset.y = Math.abs(Math.sin(t * 1.5)) * -p.pitchAmp;
          break;
        case 'hydraulic':
          this.idleOffset.x = Math.sin(t * 0.6) * (p.yawAmp * 0.4);
          this.idleOffset.y = (Math.sin(t * 1.2) > 0 ? 1 : -0.3) * p.pitchAmp * 0.7;
          break;
        case 'levitate':
          this.idleOffset.x = Math.sin(t * 0.5) * p.yawAmp;
          this.idleOffset.y = Math.sin(t * 1.0) * p.pitchAmp;
          break;
        case 'dispatch':
          this.idleOffset.x = Math.sin(t * 1.1) * p.yawAmp;
          this.idleOffset.y = Math.cos(t * 1.1) * (p.pitchAmp * 0.7);
          break;
        case 'quill':
          this.idleOffset.x = Math.sin(t * 1.4) * p.yawAmp * 0.8;
          this.idleOffset.y = Math.sin(t * 0.9) * p.pitchAmp + Math.cos(t * 2.6) * 0.01;
          break;
        case 'omni':
        default:
          this.idleOffset.x = Math.cos(t * 0.9) * p.yawAmp;
          this.idleOffset.y = Math.sin(t * 1.2) * p.pitchAmp;
          break;
      }
    }

    render(time) {
      if (!this.ready || !this.gl) return;

      const gl = this.gl;
      gl.useProgram(this.program);

      this.currentOffset.x += (this.targetOffset.x - this.currentOffset.x) * 0.12;
      this.currentOffset.y += (this.targetOffset.y - this.currentOffset.y) * 0.12;

      this.updateKinematics(time);

      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      const aPos = gl.getAttribLocation(this.program, 'a_position');
      gl.enableVertexAttribArray(aPos);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuf);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

      const aTex = gl.getAttribLocation(this.program, 'a_texCoord');
      gl.enableVertexAttribArray(aTex);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.texBuf);
      gl.vertexAttribPointer(aTex, 2, gl.FLOAT, false, 0, 0);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.texChar);
      gl.uniform1i(this.uImage, 0);

      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, this.texDepth);
      gl.uniform1i(this.uDepth, 1);

      gl.uniform2f(this.uOffset, this.currentOffset.x, this.currentOffset.y);
      gl.uniform2f(this.uIdleOffset, this.idleOffset.x, this.idleOffset.y);
      gl.uniform3fv(this.uGlowColor, this.config.color);
      gl.uniform1f(this.uEnergy, this.state === 'working' ? 2.6 : 1.0);
      gl.uniform1f(this.uTime, time);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }
  }

  class Character3DEngine {
    constructor() {
      this.instances = {};
      this.startTime = performance.now();
      this.init();
    }

    init() {
      document.addEventListener('DOMContentLoaded', () => this.boot());
      if (document.readyState === 'complete' || document.readyState === 'interactive') {
        this.boot();
      }
    }

    boot() {
      const cards = document.querySelectorAll('.factory-avatar-3d-box, .atom-3d-card-viewport');
      cards.forEach((el) => {
        const charKey = el.dataset.character || el.closest('[data-character]')?.dataset.character;
        const canvas = el.querySelector('canvas');
        if (charKey && CHARACTERS[charKey] && canvas && !this.instances[charKey]) {
          this.instances[charKey] = new CharacterCard3D(el, charKey);
        }
      });

      this.loop = this.loop.bind(this);
      requestAnimationFrame(this.loop);
      console.log('[CHARACTER 3D] Instant WebGL Engine online with', Object.keys(this.instances).length, 'agents.');
    }

    setAgentState(charKey, state) {
      const isWorking = state === 'working';
      const cfg = CHARACTERS[charKey] || CHARACTERS.synapse;
      const nodes = document.querySelectorAll(`[data-character="${charKey}"]`);

      nodes.forEach((card) => {
        if (isWorking) {
          card.classList.add('working', 'working-chamber');
        } else {
          card.classList.remove('working', 'working-chamber');
        }

        const btns = card.querySelectorAll('.btn-card-direct-state, .btn-card-toggle-state');
        btns.forEach((btn) => {
          if (isWorking) {
            btn.innerHTML = '⚡ ACTIVE';
            btn.classList.add('active');
            btn.style.borderColor = cfg.glowHex || '#ff6b35';
            btn.style.color = '#fff';
            btn.style.boxShadow = `0 0 14px ${cfg.glowHex || '#ff6b35'}`;
          } else {
            btn.innerHTML = '💤 IDLE';
            btn.classList.remove('active');
            btn.style.borderColor = '';
            btn.style.color = '';
            btn.style.boxShadow = '';
          }
        });

        const meter = card.querySelector('.chamber-activity-meter');
        if (meter) {
          meter.textContent = isWorking ? '⚡ ACTIVE · OVERDRIVE' : 'STANDBY · READY';
          meter.style.color = isWorking ? (cfg.glowHex || '#ff6b35') : 'rgba(255, 255, 255, 0.7)';
        }

        const light = card.querySelector('.chamber-status-light');
        if (light) {
          light.style.background = isWorking ? (cfg.glowHex || '#ff6b35') : '#10b981';
          light.style.boxShadow = isWorking ? `0 0 12px ${cfg.glowHex || '#ff6b35'}` : '0 0 8px #10b981';
        }

        // Swap the GLB animation clip (Idle <-> Working) on any mounted model-viewer
        const modelViewer = card.querySelector(`model-viewer[data-character="${charKey}"]`);
        if (modelViewer) {
          const clip = isWorking ? 'Working' : 'Idle';
          modelViewer.setAttribute('animation-name', clip);
          if (modelViewer.availableAnimations && modelViewer.availableAnimations.includes(clip)) {
            modelViewer.play({ repetitions: Infinity });
          }
        }
      });

      if (this.instances[charKey]) {
        this.instances[charKey].setState(state);
      }
    }

    // Lazily mounts the real .glb for a character (src is only set on first click
    // to avoid loading every model on page load) and toggles between the flat
    // sprite and the 3D <model-viewer>. Requires a rigged/animated .glb dropped
    // into dashboard/static/models/<agent>.glb with "Idle"/"Working" clips -
    // otherwise the model will display as a static mesh with no animation.
    toggleGlbViewer(charKey) {
      const cards = document.querySelectorAll(`[data-character="${charKey}"]`);
      cards.forEach((card) => {
        const modelViewer = card.querySelector(`model-viewer[data-character="${charKey}"]`);
        const sprite = card.querySelector('.atom-character-live');
        if (!modelViewer) return;

        if (!modelViewer.dataset.srcLoaded) {
          modelViewer.setAttribute('src', `/static/models/${charKey}.glb`);
          modelViewer.dataset.srcLoaded = 'true';
        }

        const nowShowing3d = modelViewer.style.display !== 'none';
        modelViewer.style.display = nowShowing3d ? 'none' : 'block';
        if (sprite) sprite.style.display = nowShowing3d ? '' : 'none';

        const btn = card.querySelector('.btn-card-3d-toggle');
        if (btn) {
          btn.classList.toggle('active', !nowShowing3d);
          btn.innerHTML = nowShowing3d ? '🧊 3D' : '🖼️ 2D';
        }
      });
    }

    toggleAgentState(charKey) {
      const nodes = document.querySelectorAll(`[data-character="${charKey}"]`);
      let isWorking = false;
      nodes.forEach((el) => {
        if (el.classList.contains('working') || el.classList.contains('working-chamber')) {
          isWorking = true;
        }
      });
      const nextState = isWorking ? 'idle' : 'working';
      this.setAgentState(charKey, nextState);
    }

    loop() {
      const time = (performance.now() - this.startTime) * 0.001;
      for (const k in this.instances) {
        this.instances[k].render(time);
      }
      requestAnimationFrame(this.loop);
    }
  }

  window.character3dEngine = new Character3DEngine();
})();
