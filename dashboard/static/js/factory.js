// ==========================================================================
// WORKHORSE RPG FACTORY CONTROLLER — CHAMBER ANIMATIONS & PIPE FLOW
// ==========================================================================

class FactoryFloorController {
  constructor() {
    this.currentStage = 0;
    this.initPipes();
  }

  initPipes() {
    // Reference SVG pipe elements
    this.pipes = {
      p1: document.getElementById("pipe-energy-1"),
      p2: document.getElementById("pipe-energy-2"),
      p3: document.getElementById("pipe-energy-3"),
      p4: document.getElementById("pipe-energy-4"),
      p5: document.getElementById("pipe-energy-5")
    };
  }

  setPipelineStage(stageNum, activeAgent = "vanguard", thoughtText = "") {
    this.currentStage = stageNum;

    // Reset all chambers
    const chambers = document.querySelectorAll(".factory-chamber");
    chambers.forEach(c => {
      c.classList.remove("active-chamber");
      const meter = c.querySelector(".chamber-activity-meter");
      if (meter) meter.textContent = "STANDBY";
    });

    // Reset all pipe pulses
    Object.values(this.pipes).forEach(p => {
      if (p) p.classList.remove("flowing");
    });

    // Mark previous chambers completed
    if (stageNum >= 1) this._markCompleted("chamber-vanguard");
    if (stageNum >= 2) this._markCompleted("chamber-iris");
    if (stageNum >= 3) this._markCompleted("chamber-forge");
    if (stageNum >= 4) this._markCompleted("chamber-echo");
    if (stageNum >= 5) this._markCompleted("chamber-iris");
    if (stageNum >= 6) this._markCompleted("chamber-aura");
    if (stageNum >= 7) this._markCompleted("chamber-vault");

    // Activate the appropriate chamber based on current stage
    let activeChamberId = null;
    let activePipe = null;

    switch (stageNum) {
      case 1:
        activeChamberId = "chamber-vanguard";
        break;
      case 2:
        activeChamberId = "chamber-iris";
        activePipe = this.pipes.p1;
        break;
      case 3:
        activeChamberId = "chamber-forge";
        activePipe = this.pipes.p2;
        break;
      case 4:
        activeChamberId = "chamber-echo";
        activePipe = this.pipes.p3;
        break;
      case 5:
        activeChamberId = "chamber-iris";
        activePipe = this.pipes.p1;
        break;
      case 6:
        activeChamberId = "chamber-aura";
        activePipe = this.pipes.p4;
        break;
      case 7:
        activeChamberId = "chamber-vault";
        activePipe = this.pipes.p5;
        break;
    }

    if (window.character3dEngine) {
      Object.keys(window.character3dEngine.instances || {}).forEach(k => {
        window.character3dEngine.setAgentState(k, 'idle');
      });
      if (activeAgent) {
        window.character3dEngine.setAgentState(activeAgent.toLowerCase(), 'working');
      }
    }

    if (activeChamberId) {
      const chamberEl = document.getElementById(activeChamberId);
      if (chamberEl) {
        chamberEl.classList.remove("completed");
        chamberEl.classList.add("active-chamber");
        const meter = chamberEl.querySelector(".chamber-activity-meter");
        if (meter) meter.textContent = "ONLINE · ACTIVE";

        const speech = chamberEl.querySelector(".chamber-speech");
        if (speech && thoughtText) {
          speech.textContent = thoughtText;
        }
      }
    }

    if (activePipe) {
      activePipe.classList.add("flowing");
    }
  }

  _markCompleted(chamberId) {
    const el = document.getElementById(chamberId);
    if (el) {
      el.classList.add("completed");
      const meter = el.querySelector(".chamber-activity-meter");
      if (meter) meter.textContent = "COMPLETED";
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.factoryController = new FactoryFloorController();
});
