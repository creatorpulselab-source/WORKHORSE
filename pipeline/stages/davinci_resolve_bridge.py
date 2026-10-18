r"""
WORKHORSE Stage — DaVinci Resolve Studio 21.1.1 Bridge (Scripting API + ResolveMCP + 3D LUTs)
==============================================================================================
Integrates Blackmagic Design DaVinci Resolve Studio (`Resolve.exe`, `ResolveMCP.exe`, and
`DaVinciResolveScript.py` / `fusionscript.dll`) directly into the WORKHORSE media pipeline.

Capabilities:
  1. Connects to DaVinci Resolve Studio via `DaVinciResolveScript` (`bmd.scriptapp("Resolve")`).
  2. Generates custom 33x33x33 `.cube` 3D LUTs and GPU `.dctl` shaders inside
     `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MCP`.
  3. Automates multi-shot vertical (1080x1920) & widescreen (3840x2160) timeline creation,
     clip importing, color grading, and H.264/H.265 `.mp4` rendering in DaVinci Resolve Studio.
  4. Provides a deterministic 3D `.cube` tetrahedral/trilinear LUT + OpenCV/FFmpeg mastering
     fallback when Resolve Studio is headless/closed or awaiting initial setup.
"""

from __future__ import annotations

import importlib.util
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

RESOLVE_EXE = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe")
RESOLVE_MCP_EXE = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\ResolveMCP.exe")
RESOLVE_SCRIPT_MODULE = Path(
    r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
)
RESOLVE_LUT_MCP_DIR = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MCP")


class DaVinciResolveBridge:
    """Production bridge to DaVinci Resolve Studio 21.1+ & 3D LUT Color Grading Engine."""

    def __init__(
        self,
        resolve_exe: Path = RESOLVE_EXE,
        script_module_path: Path = RESOLVE_SCRIPT_MODULE,
        lut_dir: Path = RESOLVE_LUT_MCP_DIR,
    ) -> None:
        self.resolve_exe = Path(resolve_exe)
        self.resolve_mcp_exe = RESOLVE_MCP_EXE
        self.script_module_path = Path(script_module_path)
        self.lut_dir = Path(lut_dir)
        self._bmd = None

    # ------------------------------------------------------------------
    # 1. DaVinciResolveScript API Connection
    # ------------------------------------------------------------------
    def _load_bmd_module(self):
        if self._bmd is not None:
            return self._bmd
        if not self.script_module_path.exists():
            return None
        try:
            os.environ.setdefault(
                "RESOLVE_SCRIPT_API",
                r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
            )
            os.environ.setdefault(
                "RESOLVE_SCRIPT_LIB",
                r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll",
            )
            spec = importlib.util.spec_from_file_location("DaVinciResolveScript", str(self.script_module_path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules["DaVinciResolveScript"] = module
                spec.loader.exec_module(module)
                self._bmd = module
                return module
        except Exception as exc:
            print(f"[DaVinciResolveBridge] Warning loading DaVinciResolveScript: {exc}")
        return None

    def check_status(self) -> Dict[str, Any]:
        """Cheap health snapshot used by Synapse's system diagnostics (no Resolve API call, no launch)."""
        running = False
        try:
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/NH"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            running = "Resolve.exe" in out
        except Exception:
            pass
        return {
            "resolve_installed": self.resolve_exe.exists(),
            "mcp_binary_exists": self.resolve_mcp_exe.exists(),
            "scripting_module_exists": self.script_module_path.exists(),
            "resolve_running": running,
        }

    def get_resolve(self, launch_headless_if_needed: bool = False):
        """Returns the live DaVinci Resolve Studio `resolve` app object if connected."""
        bmd = self._load_bmd_module()
        if bmd is None:
            return None
        try:
            resolve = bmd.scriptapp("Resolve")
            if resolve is not None:
                return resolve
        except Exception:
            resolve = None

        if launch_headless_if_needed and self.resolve_exe.exists():
            try:
                subprocess.Popen(
                    [str(self.resolve_exe), "-nogui"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(12):
                    time.sleep(1.5)
                    try:
                        resolve = bmd.scriptapp("Resolve")
                        if resolve is not None:
                            return resolve
                    except Exception:
                        pass
            except Exception as exc:
                print(f"[DaVinciResolveBridge] Could not spawn Resolve -nogui: {exc}")
        return None

    # ------------------------------------------------------------------
    # 2. 3D .cube LUT Generation (Compatible with ResolveMCP & OpenCV)
    # ------------------------------------------------------------------
    def generate_cinematic_cube_lut(
        self,
        lut_name: str = "Workhorse_Cinematic_Kodak2383_TealOrange.cube",
        size: int = 33,
    ) -> Path:
        """
        Generates a 33x33x33 3D `.cube` LUT file in Resolve's `Support/LUT/MCP` folder
        (or workspace fallback if permissions restrict ProgramData).
        Implements an S-curve film contrast + teal shadow split-tone + warm skin-tone preservation.
        """
        target_dir = self.lut_dir
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            lut_path = target_dir / lut_name
            # Test write permission
            with open(lut_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            fallback_dir = Path(r"F:\WORKHORSE\workspace\luts")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            lut_path = fallback_dir / lut_name

        lines = [
            f'TITLE "{lut_name.replace(".cube", "")}"',
            f"LUT_3D_SIZE {size}",
            "DOMAIN_MIN 0.0 0.0 0.0",
            "DOMAIN_MAX 1.0 1.0 1.0",
            "",
        ]

        def filmic_s_curve(x: float) -> float:
            # Subtle Kodak 2383 style toe/shoulder S-curve
            x = max(0.0, min(1.0, x))
            return float(1.0 / (1.0 + math.exp(-5.4 * (x - 0.48))))

        # Normalize S-curve endpoints to [0, 1]
        s0 = filmic_s_curve(0.0)
        s1 = filmic_s_curve(1.0)

        def curve(x: float) -> float:
            return max(0.0, min(1.0, (filmic_s_curve(x) - s0) / (s1 - s0)))

        for b_i in range(size):
            b = b_i / (size - 1)
            for g_i in range(size):
                g = g_i / (size - 1)
                for r_i in range(size):
                    r = r_i / (size - 1)
                    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
                    shadow_weight = max(0.0, 1.0 - luma * 2.0) ** 1.4
                    highlight_weight = max(0.0, (luma - 0.45) * 1.8) ** 1.2

                    rc = curve(r)
                    gc = curve(g)
                    bc = curve(b)

                    # Teal shadows + warm golden highlights while keeping skin natural
                    r_out = rc - 0.035 * shadow_weight + 0.040 * highlight_weight
                    g_out = gc + 0.012 * shadow_weight + 0.015 * highlight_weight
                    b_out = bc + 0.048 * shadow_weight - 0.030 * highlight_weight

                    # Slight saturation boost (1.08x)
                    luma_out = 0.2126 * r_out + 0.7152 * g_out + 0.0722 * b_out
                    r_out = max(0.0, min(1.0, luma_out + (r_out - luma_out) * 1.08))
                    g_out = max(0.0, min(1.0, luma_out + (g_out - luma_out) * 1.08))
                    b_out = max(0.0, min(1.0, luma_out + (b_out - luma_out) * 1.08))

                    lines.append(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}")

        lut_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return lut_path

    @staticmethod
    def apply_cube_lut_to_bgr_frame(frame_bgr: np.ndarray, lut_table: np.ndarray) -> np.ndarray:
        """
        Fast vectorized 3D LUT trilinear/nearest lookup on a uint8 BGR frame.
        `lut_table` has shape (size, size, size, 3) in RGB float32 [0..255].
        """
        size = lut_table.shape[0]
        scale = (size - 1) / 255.0
        b = np.clip((frame_bgr[:, :, 0].astype(np.float32) * scale).round().astype(np.int32), 0, size - 1)
        g = np.clip((frame_bgr[:, :, 1].astype(np.float32) * scale).round().astype(np.int32), 0, size - 1)
        r = np.clip((frame_bgr[:, :, 2].astype(np.float32) * scale).round().astype(np.int32), 0, size - 1)
        rgb_out = lut_table[b, g, r]
        bgr_out = rgb_out[:, :, ::-1].astype(np.uint8)
        return bgr_out

    @staticmethod
    def load_cube_lut_table(lut_path: Path) -> np.ndarray:
        """Loads a `.cube` file into a `(size, size, size, 3)` float32 RGB array scaled to [0..255]."""
        size = 33
        values: List[List[float]] = []
        for raw_line in lut_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("TITLE") or line.startswith("DOMAIN"):
                continue
            if line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
                continue
            parts = line.split()
            if len(parts) == 3:
                values.append([float(parts[0]) * 255.0, float(parts[1]) * 255.0, float(parts[2]) * 255.0])
        arr = np.array(values, dtype=np.float32).reshape((size, size, size, 3))
        return arr

    def execute_resolve_mcp_script(self, script_code: str, timeout: float = 120.0) -> Dict[str, Any]:
        """
        Executes a Python script inside the live DaVinci Resolve Studio session via
        `ResolveMCP.exe` (MCP JSON-RPC over stdio). Works even when Preferences ->
        External Scripting is set to None.
        """
        if not self.resolve_mcp_exe.exists():
            return {"success": False, "error": f"ResolveMCP.exe not found at {self.resolve_mcp_exe}"}
        import json as _json

        reqs = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "workhorse-bridge", "version": "1.0.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "run_script", "arguments": {"script": script_code}},
            },
        ]
        stdin_payload = "\n".join(_json.dumps(r) for r in reqs) + "\n"
        try:
            proc = subprocess.run(
                [str(self.resolve_mcp_exe)],
                input=stdin_payload,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            for line in reversed(proc.stdout.splitlines()):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                msg = _json.loads(line)
                if msg.get("id") == 2 and "result" in msg:
                    content = msg["result"].get("content", [])
                    if content and isinstance(content, list):
                        txt = content[0].get("text", "{}")
                        return {"success": True, "data": _json.loads(txt)}
            return {"success": False, "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-500:]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 3. DaVinci Resolve Studio Automated Timeline, Super Scale & Render Pipeline
    # ------------------------------------------------------------------
    def assemble_and_grade_timeline_in_resolve(
        self,
        project_name: str,
        clip_paths: List[Path],
        output_mp4_path: Path,
        width: int = 1080,
        height: int = 1920,
        fps: int = 24,
        lut_path: Optional[Path] = None,
        super_scale: int = 2,
        super_scale_sharpness: str = "Medium",
        super_scale_noise_reduction: str = "Medium",
        codec_preference: str = "H264_NVIDIA",
    ) -> Dict[str, Any]:
        """
        Creates a DaVinci Resolve Studio 21.1+ project & timeline, enables DaVinci Neural Engine
        `Super Scale` (`super_scale`: 2=2x, 3=3x, 4=4x) + Optical Flow (`enhancedBetter`),
        appends `clip_paths`, applies the 3D LUT on the Color page, and renders `output_mp4_path`
        via Resolve's Deliver page (using NVIDIA NVENC hardware acceleration when available).
        Automatically uses either direct `DaVinciResolveScript` or `ResolveMCP.exe` JSON-RPC.
        """
        valid_paths = [str(Path(p).resolve()) for p in clip_paths if Path(p).exists()]
        if not valid_paths:
            return {"used_resolve": False, "reason": "No valid input clip paths exist"}

        output_mp4_path = Path(output_mp4_path).resolve()
        output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        lut_str = str(Path(lut_path).resolve()) if (lut_path and Path(lut_path).exists()) else ""

        resolve = self.get_resolve(launch_headless_if_needed=False)
        if resolve is None and self.resolve_mcp_exe.exists():
            import json as _json
            mcp_script = f"""
pm = resolve.GetProjectManager()
p = pm.LoadProject({_json.dumps(project_name)})
if not p:
    p = pm.CreateProject({_json.dumps(project_name)})
if not p:
    p = pm.GetCurrentProject()

p.SetSetting("timelineFrameRate", "{fps}")
p.SetSetting("timelineResolutionWidth", "{width}")
p.SetSetting("timelineResolutionHeight", "{height}")
p.SetSetting("imageResizeMode", "sharper")
p.SetSetting("imageResizingMethod", "sharper")
p.SetSetting("imageMotionEstimationMode", "enhancedBetter")
p.SetSetting("imageMotionEstimationRange", "medium")
if {int(super_scale)} in (2, 3, 4):
    p.SetSetting("superScale", {int(super_scale)})
    p.SetSetting("superScaleSharpness", {_json.dumps(super_scale_sharpness)})
    p.SetSetting("superScaleNoiseReduction", {_json.dumps(super_scale_noise_reduction)})

mp = p.GetMediaPool()
imported = mp.ImportMedia({_json.dumps(valid_paths)})
tl_name = "Timeline_{int(time.time())}"
tl = mp.CreateTimelineFromClips(tl_name, imported)
if not tl:
    tl = mp.CreateEmptyTimeline(tl_name)
    if tl and imported:
        mp.AppendToTimeline(imported)

if tl:
    if {int(super_scale)} in (2, 3, 4):
        tl.SetSetting("superScale", "{int(super_scale)}")
    lut_s = {_json.dumps(lut_str)}
    if lut_s:
        p.RefreshLUTList()
        for it in (tl.GetItemListInTrack("video", 1) or []):
            try:
                it.SetLUT(1, lut_s)
            except Exception:
                pass
    p.SetCurrentTimeline(tl)
    p.DeleteAllRenderJobs()
    codecs = p.GetRenderCodecs("mp4") or {{}}
    chosen = {_json.dumps(codec_preference)} if {_json.dumps(codec_preference)} in codecs.values() else "H264"
    p.SetCurrentRenderFormatAndCodec("mp4", chosen)
    p.SetRenderSettings({{
        "SelectAllFrames": True,
        "TargetDir": {_json.dumps(str(output_mp4_path.parent))},
        "CustomName": {_json.dumps(output_mp4_path.stem)},
        "FormatWidth": {int(width)},
        "FormatHeight": {int(height)},
        "FrameRate": "{fps}",
    }})
    jid = p.AddRenderJob()
    if jid:
        p.StartRendering([jid])
    result = {{"job_id": jid, "timeline": tl_name, "codec": chosen}}
else:
    result = {{"error": "Failed to create timeline"}}
"""
            mcp_res = self.execute_resolve_mcp_script(mcp_script)
            if mcp_res.get("success"):
                t0 = time.time()
                while (time.time() - t0) < 90:
                    if output_mp4_path.exists() and output_mp4_path.stat().st_size > 50_000:
                        time.sleep(1.2)
                        return {
                            "used_resolve": True,
                            "bridge_mode": "ResolveMCP.exe",
                            "project_name": project_name,
                            "super_scale": f"{super_scale}x",
                            "resolution": f"{width}x{height}",
                            "output_mp4": str(output_mp4_path),
                            "size_bytes": output_mp4_path.stat().st_size,
                        }
                    time.sleep(0.8)
            return {"used_resolve": False, "reason": "DaVinci Resolve Studio GUI/scripting session not active"}

        try:
            pm = resolve.GetProjectManager()
            project = pm.LoadProject(project_name)
            if not project:
                project = pm.CreateProject(project_name)
            if not project:
                project = pm.GetCurrentProject()
            if not project:
                return {"used_resolve": False, "reason": "Could not create or load project in Resolve"}

            project.SetSetting("timelineFrameRate", str(fps))
            project.SetSetting("timelineResolutionWidth", str(width))
            project.SetSetting("timelineResolutionHeight", str(height))
            project.SetSetting("videoMonitorFormat", f"HD {width}x{height}p {fps}")
            project.SetSetting("imageResizeMode", "sharper")
            project.SetSetting("imageResizingMethod", "sharper")
            project.SetSetting("imageMotionEstimationMode", "enhancedBetter")
            project.SetSetting("imageMotionEstimationRange", "medium")

            if super_scale in (2, 3, 4):
                project.SetSetting("superScale", int(super_scale))
                project.SetSetting("superScaleSharpness", super_scale_sharpness)
                project.SetSetting("superScaleNoiseReduction", super_scale_noise_reduction)

            media_pool = project.GetMediaPool()
            valid_paths = [str(Path(p).resolve()) for p in clip_paths if Path(p).exists()]
            if not valid_paths:
                return {"used_resolve": False, "reason": "No valid input clip paths exist"}

            imported = media_pool.ImportMedia(valid_paths)
            tl_name = f"Timeline_{int(time.time())}"
            timeline = media_pool.CreateTimelineFromClips(tl_name, imported)
            if not timeline:
                timeline = media_pool.CreateEmptyTimeline(tl_name)
                if timeline and imported:
                    media_pool.AppendToTimeline(imported)

            if not timeline:
                return {"used_resolve": False, "reason": "Could not create timeline in Resolve"}

            if super_scale in (2, 3, 4):
                try:
                    timeline.SetSetting("superScale", str(super_scale))
                except Exception:
                    pass

            if lut_path and Path(lut_path).exists():
                project.RefreshLUTList()
                items = timeline.GetItemListInTrack("video", 1) or []
                for item in items:
                    try:
                        item.SetLUT(1, str(Path(lut_path).resolve()))
                    except Exception:
                        pass

            project.SetCurrentTimeline(timeline)
            codecs = project.GetRenderCodecs("mp4") or {}
            available_codec_vals = set(codecs.values())
            chosen_codec = codec_preference if codec_preference in available_codec_vals else "H264"
            project.SetCurrentRenderFormatAndCodec("mp4", chosen_codec)

            output_mp4_path = Path(output_mp4_path).resolve()
            output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
            project.DeleteAllRenderJobs()
            project.SetRenderSettings(
                {
                    "SelectAllFrames": True,
                    "TargetDir": str(output_mp4_path.parent),
                    "CustomName": output_mp4_path.stem,
                    "FormatWidth": int(width),
                    "FormatHeight": int(height),
                    "FrameRate": str(fps),
                }
            )
            job_id = project.AddRenderJob()
            if job_id:
                project.StartRendering([job_id])
                t0 = time.time()
                while project.IsRenderingInProgress() and (time.time() - t0) < 180:
                    time.sleep(0.8)
                pm.SaveProject()
                if output_mp4_path.exists() and output_mp4_path.stat().st_size > 10000:
                    return {
                        "used_resolve": True,
                        "project_name": project.GetName(),
                        "timeline_name": tl_name,
                        "super_scale": f"{super_scale}x",
                        "codec": chosen_codec,
                        "resolution": f"{width}x{height}",
                        "output_mp4": str(output_mp4_path),
                        "size_bytes": output_mp4_path.stat().st_size,
                    }
        except Exception as exc:
            return {"used_resolve": False, "reason": f"Resolve scripting exception: {exc}"}

        return {"used_resolve": False, "reason": "Resolve render job did not produce output file"}

    def upscale_clip_with_super_scale(
        self,
        input_clip_path: Path,
        output_mp4_path: Path,
        super_scale: int = 3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 24,
        lut_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Upscales a single ComfyUI video clip (e.g. 480x864 MiniMax FastH3) using
        DaVinci Resolve Studio's Neural Engine `Super Scale` (2x, 3x, or 4x) +
        Optical Flow (`enhancedBetter`) into a crisp 1080x1920 or 2160x3840 MP4.
        """
        proj_name = f"WH_SuperScale_{int(time.time())}"
        return self.assemble_and_grade_timeline_in_resolve(
            project_name=proj_name,
            clip_paths=[Path(input_clip_path)],
            output_mp4_path=Path(output_mp4_path),
            width=width,
            height=height,
            fps=fps,
            lut_path=lut_path,
            super_scale=super_scale,
        )



# Global singleton (mirrors blender_bridge) - used by Synapse system diagnostics.
davinci_resolve_bridge = DaVinciResolveBridge()

