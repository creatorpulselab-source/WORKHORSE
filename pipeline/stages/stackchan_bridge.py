"""
WORKHORSE M5Stack-chan AI Hardware Bridge
Connects physical M5Stack-chan desktop robot companions to WORKHORSE and ComfyUI.

Robot 1: Synapse (WORKHORSE AI PC) - Master Orchestrator, Operations & Financial Director
Robot 2: Muse    (ComfyUI PC)     - Creative Visionary, Diffusion Artist & GPU Telemetry Watchdog
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stackchan_bridge")


class StackChanRobot:
    """
    Base hardware interface for an M5Stack-chan desktop AI companion robot.
    Supports USB Serial (COM port) and Wi-Fi WebSocket/HTTP communication.
    """
    def __init__(self, name: str = "Synapse", role: str = "orchestrator", port: Optional[str] = None):
        self.name = name
        self.role = role
        self.port = port
        self.serial_conn = None
        self._init_connection()

    def _init_connection(self):
        if not serial:
            logger.warning("pyserial not installed. Serial communication disabled.")
            return

        if not self.port:
            # Auto-detect M5Stack (typically Silicon Labs CP210x, CH340, or ESP32 USB)
            ports = serial.tools.list_ports.comports()
            for p in ports:
                desc = p.description.lower()
                if any(k in desc for k in ["cp210", "ch340", "ch910", "usb-serial", "m5stack", "esp32"]):
                    self.port = p.device
                    break

        if self.port:
            try:
                self.serial_conn = serial.Serial(self.port, baudrate=115200, timeout=1)
                logger.info(f"✅ Connected to {self.name} on {self.port}!")
            except Exception as e:
                logger.warning(f"Could not open serial on {self.port}: {e}")

    def send_packet(self, data: Dict[str, Any]):
        """Sends JSON command packet to M5Stack-chan firmware."""
        packet = json.dumps(data) + "\n"
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(packet.encode("utf-8"))
            except Exception as e:
                logger.error(f"Serial write error: {e}")
        else:
            logger.info(f"[{self.name} Telemetry] -> {data}")

    def set_expression(self, expression: str):
        """Available expressions: 'happy', 'blink', 'thinking', 'excited', 'sleepy', 'dizzy', 'sad'"""
        self.send_packet({"type": "expression", "val": expression})

    def speak(self, text: str, expression: str = "happy"):
        """Triggers speech synthesis and animated mouth movement."""
        self.send_packet({"type": "speak", "text": text, "expression": expression})

    def move_head(self, pan: int = 0, tilt: int = 0):
        """Pans (-45 to 45 deg) and tilts (-20 to 20 deg)."""
        self.send_packet({"type": "motion", "pan": pan, "tilt": tilt})


class SynapseRobot(StackChanRobot):
    """
    Robot 1: Synapse (Docked on WORKHORSE AI PC)
    The Master Orchestrator, Executive Brain, CashApp Radar & Community Concierge.
    Theme: Cyan / Electric Blue.
    """
    def __init__(self, port: Optional[str] = None):
        super().__init__(name="Synapse", role="orchestrator", port=port)

    def on_whale_sale(self, buyer: str, amount: float):
        """High-roller or $350 Mega-Vault purchase."""
        self.send_packet({
            "type": "event",
            "name": "whale_sale",
            "expression": "excited",
            "pan": 20,
            "sound": "cash_register",
            "theme_color": "#00f2fe",
            "text": f"Whale alert! {buyer} unlocked the {int(amount)} dollar vault!"
        })

    def on_cashapp_verified(self, buyer: str, amount: float, manager_cut: float):
        """Verified CashApp receipt scanned and delivered."""
        self.send_packet({
            "type": "event",
            "name": "cashapp_verified",
            "expression": "happy",
            "sound": "ding",
            "theme_color": "#00f2fe",
            "text": f"Payment verified for {buyer}. {int(amount)} dollars in. Your cut is {int(manager_cut)} dollars."
        })

    def on_cam_show_detected(self, filename: str):
        """Raw recording dropped into inbox."""
        self.send_packet({
            "type": "event",
            "name": "cam_show",
            "expression": "thinking",
            "pan": -15,
            "theme_color": "#00f2fe",
            "text": "New cam stream detected in dropzone. Firing multi-cam cutter."
        })

    def on_vault_milestone(self, count: int, total: int):
        """ManyVids vault sync milestone."""
        self.send_packet({
            "type": "event",
            "name": "vault_milestone",
            "expression": "happy",
            "theme_color": "#00f2fe",
            "text": f"Vault ingestion at {count} of {total} videos secured on CDN."
        })


class MuseRobot(StackChanRobot):
    """
    Robot 2: Muse (Docked on ComfyUI PC - 192.168.1.74)
    The Creative Visionary, Diffusion Artist, Prompt Dreamer & GPU Watchdog.
    Theme: Magenta / Electric Purple.
    """
    def __init__(self, port: Optional[str] = None):
        super().__init__(name="Muse", role="artist", port=port)

    def on_render_start(self, prompt_summary: str, model_type: str = "FLUX"):
        """Triggered when KSampler job begins on RTX 5070 Ti."""
        self.send_packet({
            "type": "event",
            "name": "render_start",
            "expression": "thinking",
            "motion": "swirl",
            "theme_color": "#ff007f",
            "text": f"Dreaming with {model_type}: {prompt_summary[:40]}..."
        })

    def on_render_complete(self, count: int, seconds: float):
        """Triggered when diffusion batch finishes."""
        self.send_packet({
            "type": "event",
            "name": "render_complete",
            "expression": "happy",
            "sound": "chime",
            "theme_color": "#ff007f",
            "text": f"Canvas ready! {count} renders rendered in {int(seconds)} seconds."
        })

    def on_qc_passed(self, score: float):
        """Iris Vision QC gate passed."""
        self.send_packet({
            "type": "event",
            "name": "qc_passed",
            "expression": "excited",
            "theme_color": "#ff007f",
            "text": f"Quality audit passed with score {score:.1f}. Flawless anatomy."
        })

    def on_video_progress(self, model: str, frame: int, total_frames: int):
        """Minimax FastH3 or LTX Video 2.3 rendering step."""
        self.send_packet({
            "type": "event",
            "name": "video_progress",
            "expression": "thinking",
            "theme_color": "#ff007f",
            "text": f"Synthesizing {model}: frame {frame} of {total_frames}."
        })

    def on_gpu_warning(self, vram_used_gb: float, temp_c: float):
        """VRAM saturation or thermal alert on the 5070 Ti."""
        self.send_packet({
            "type": "event",
            "name": "gpu_warning",
            "expression": "dizzy",
            "sound": "alert",
            "theme_color": "#ff007f",
            "text": f"GPU alert: VRAM at {vram_used_gb:.1f} GB, temperature {int(temp_c)} degrees."
        })


if __name__ == "__main__":
    synapse = SynapseRobot()
    muse = MuseRobot()
    print("Testing M5Stack-chan Robot Personas (Synapse & Muse)...")
    synapse.on_whale_sale(buyer="Carey", amount=350.0)
    synapse.on_cashapp_verified(buyer="Vance", amount=100.0, manager_cut=20.0)
    muse.on_render_start("Glamour shoot 85mm portrait", model_type="CyberRealistic Flux")
    muse.on_render_complete(count=4, seconds=18.2)

