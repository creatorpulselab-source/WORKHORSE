"""
WORKHORSE M5Stack-chan AI Hardware Bridge
Connects physical M5Stack-chan desktop robot companions to WORKHORSE and ComfyUI.
Author: Antigravity / WORKHORSE Pipeline
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
    Interface for an M5Stack-chan desktop AI companion robot.
    Supports USB Serial (COM port) and Wi-Fi WebSocket/HTTP communication.
    """
    def __init__(self, name: str = "WorkhorseChan", role: str = "orchestrator", port: Optional[str] = None):
        self.name = name
        self.role = role  # "orchestrator" (WORKHORSE PC) or "artist" (ComfyUI PC)
        self.port = port
        self.serial_conn = None
        self._init_connection()

    def _init_connection(self):
        if not serial:
            logger.warning("pyserial not installed. Serial communication disabled.")
            return

        if not self.port:
            # Auto-detect M5Stack (typically Silicon Labs CP210x or CH340 or ESP USB)
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
            logger.info(f"[{self.name} Simulation] -> {data}")

    def set_expression(self, expression: str):
        """Available expressions: 'happy', 'blink', 'thinking', 'excited', 'sleepy', 'dizzy', 'sad'"""
        self.send_packet({"type": "expression", "val": expression})

    def speak(self, text: str, expression: str = "happy"):
        """Triggers speech synthesis and animated mouth movement."""
        self.send_packet({"type": "speak", "text": text, "expression": expression})

    def move_head(self, pan: int = 0, tilt: int = 0):
        """Pans (-45 to 45 deg) and tilts (-20 to 20 deg)."""
        self.send_packet({"type": "motion", "pan": pan, "tilt": tilt})

    # --- Pre-Configured WORKHORSE Agent Events ---

    def on_whale_sale(self, buyer: str, amount: float):
        """Triggered on $350 Mega-Vault or high-roller sale."""
        self.send_packet({
            "type": "event",
            "name": "whale_sale",
            "expression": "excited",
            "pan": 15,
            "sound": "cash_register",
            "text": f"Whale Alert! {buyer} unlocked the {int(amount)} dollar vault!"
        })

    def on_cam_show_detected(self, filename: str):
        """Triggered when raw cam show drops into inbox."""
        self.send_packet({
            "type": "event",
            "name": "cam_show",
            "expression": "thinking",
            "pan": -10,
            "text": "New cam show detected in inbox! Cutting active scenes now."
        })

    def on_render_start(self, prompt_summary: str):
        """Triggered on ComfyUI PC when sampling begins."""
        self.send_packet({
            "type": "event",
            "name": "render_start",
            "expression": "thinking",
            "motion": "swirl",
            "text": "Sampling prompt in ComfyUI."
        })

    def on_render_complete(self, count: int, seconds: float):
        """Triggered when FLUX / SDXL batch completes."""
        self.send_packet({
            "type": "event",
            "name": "render_complete",
            "expression": "happy",
            "sound": "chime",
            "text": f"Batch of {count} renders finished in {int(seconds)} seconds!"
        })

    def on_error(self, message: str):
        """Triggered on VRAM OOM or pipeline error."""
        self.send_packet({
            "type": "event",
            "name": "error",
            "expression": "dizzy",
            "sound": "alert",
            "text": f"Warning: {message}"
        })


if __name__ == "__main__":
    robot1 = StackChanRobot(name="Aura (WORKHORSE)", role="orchestrator")
    robot2 = StackChanRobot(name="Iris (ComfyUI)", role="artist")
    print("Testing M5Stack-chan Robot Simulation...")
    robot1.on_whale_sale(buyer="Carey", amount=350.0)
    robot2.on_render_complete(count=8, seconds=24.5)
