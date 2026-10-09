"""
WORKHORSE DaVinci Resolve Bridge
Professional color grading for both stills and video, driven through Resolve's
official scripting API (Blackmagic Design's public, documented DaVinciResolveScript
module) - never GUI automation, and never the cracked Retouch4me binaries that were
removed from this project. Resolve applies real ASC-CDL (Color Decision List) grades
- the same primary-color-correction math colorists use - via TimelineItem.SetCDL(),
which is a first-class, documented scripting call.

One-time manual setup required (can't be done headlessly - it's a GUI preference):
  1. Open DaVinci Resolve.
  2. Preferences > System > General > "External scripting using:" -> set to "Local".
  3. Restart Resolve.
Resolve must also be running (with a project open or not - we create/open our own
working project) whenever this bridge is used.
"""
import os
import sys
import time
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

RESOLVE_INSTALL_DIR = Path("C:/Program Files/Blackmagic Design/DaVinci Resolve")
RESOLVE_SCRIPT_MODULES_DIR = Path(
    "C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules"
)
RESOLVE_SCRIPT_LIB = RESOLVE_INSTALL_DIR / "fusionscript.dll"
WORKHORSE_GRADE_PROJECT = "WORKHORSE_AutoGrade"
RENDER_STAGING_DIR = Path("F:/WORKHORSE/workspace/davinci_renders")
RENDER_STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ASC-CDL (slope/offset/power/saturation) grades matching WORKHORSE's named edit
# styles - the same professional color-correction primitives a real colorist uses,
# applied programmatically instead of by hand. Shared by both the native OpenCV engine
# (photo_retoucher.py) and this Resolve path so style NAMES mean the same creative
# intent everywhere in the pipeline, whichever engine actually renders them.
STYLE_CDL_GRADES: Dict[str, Dict[str, Any]] = {
    "natural": {
        "Slope": "1.01 1.0 0.99", "Offset": "0.004 0.0 0.0",
        "Power": "1.0 1.0 1.0", "Saturation": "1.0"
    },
    "glamour": {
        "Slope": "1.08 1.0 0.92", "Offset": "0.02 0.0 -0.02",
        "Power": "1.12 1.1 1.12", "Saturation": "1.08"
    },
    "concert_stage": {
        "Slope": "1.05 1.0 1.05", "Offset": "0.03 0.025 0.03",
        "Power": "1.1 1.1 1.1", "Saturation": "1.12"
    },
    "family_event": {
        "Slope": "1.05 1.02 0.97", "Offset": "0.015 0.01 0.0",
        "Power": "1.03 1.03 1.03", "Saturation": "1.05"
    },
    "golden_hour": {
        "Slope": "1.15 1.05 0.85", "Offset": "0.0 0.0 0.0",
        "Power": "1.0 1.0 1.0", "Saturation": "1.05"
    },
    "cyber_neon": {
        "Slope": "1.12 0.9 1.25", "Offset": "0.0 0.0 0.0",
        "Power": "1.0 1.0 1.0", "Saturation": "1.15"
    },
    "monochrome_noir": {
        "Slope": "1.0 1.0 1.0", "Offset": "0.0 0.0 0.0",
        "Power": "1.3 1.3 1.3", "Saturation": "0.0"
    },
    "vintage_35mm": {
        "Slope": "1.05 1.02 0.95", "Offset": "0.04 0.02 0.04",
        "Power": "1.0 1.0 1.0", "Saturation": "0.95"
    },
    "clean_editorial": {
        "Slope": "1.03 1.0 1.0", "Offset": "0.015 0.0 0.0",
        "Power": "1.05 1.05 1.05", "Saturation": "1.0"
    }
}


class DaVinciBridgeUnavailable(Exception):
    """Raised when Resolve isn't running or its scripting API can't be reached -
    always a clear, actionable message, never a raw import traceback."""
    pass


def _ensure_scripting_module_importable() -> None:
    """Makes the official DaVinciResolveScript module importable without requiring the
    Commander to have set any environment variables globally - WORKHORSE configures its
    own process environment at call time instead."""
    os.environ.setdefault("RESOLVE_SCRIPT_API", str(RESOLVE_SCRIPT_MODULES_DIR.parent))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", str(RESOLVE_SCRIPT_LIB))
    if str(RESOLVE_SCRIPT_MODULES_DIR) not in sys.path:
        sys.path.append(str(RESOLVE_SCRIPT_MODULES_DIR))


def _is_resolve_process_running() -> bool:
    """Checks whether the DaVinci Resolve process is actually alive BEFORE ever loading
    fusionscript.dll or calling into it. This matters because calling the scripting API
    while Resolve isn't running doesn't fail gracefully with a Python exception - it can
    hard-crash the whole process (an access violation in the native DLL) - so we must
    never attempt the connection at all unless the app is confirmed running."""
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        return "Resolve.exe" in out.stdout
    except Exception:
        return False


def get_resolve():
    """Connects to a running DaVinci Resolve instance. Raises DaVinciBridgeUnavailable
    with a clear, actionable message (never a raw traceback) if Resolve isn't running,
    the scripting module can't be found, or "External scripting using" hasn't been
    enabled in Resolve's preferences yet (a one-time manual GUI step - see module
    docstring)."""
    if not RESOLVE_SCRIPT_LIB.exists():
        raise DaVinciBridgeUnavailable(
            f"DaVinci Resolve scripting library not found at {RESOLVE_SCRIPT_LIB} - "
            "is DaVinci Resolve installed?"
        )
    if not _is_resolve_process_running():
        raise DaVinciBridgeUnavailable(
            "DaVinci Resolve is not currently running. Please open DaVinci Resolve "
            "first (and make sure Preferences > System > General > 'External "
            "scripting using' is set to 'Local', then restart Resolve once after "
            "changing that setting)."
        )
    _ensure_scripting_module_importable()
    try:
        import DaVinciResolveScript as dvr_script
    except Exception as e:
        raise DaVinciBridgeUnavailable(f"Could not import DaVinciResolveScript module: {e}")

    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        raise DaVinciBridgeUnavailable(
            "Could not connect to DaVinci Resolve. Make sure: (1) DaVinci Resolve is "
            "running, and (2) Preferences > System > General > 'External scripting "
            "using' is set to 'Local' (then restart Resolve once after changing it)."
        )
    return resolve


def check_connection() -> Dict[str, Any]:
    """Lightweight connectivity/status check for the dashboard - never raises."""
    try:
        resolve = get_resolve()
        version = resolve.GetVersionString()
        return {"connected": True, "version": version}
    except DaVinciBridgeUnavailable as e:
        return {"connected": False, "error": str(e)}
    except Exception as e:
        return {"connected": False, "error": f"Unexpected error: {e}"}


def _get_or_create_grade_project(resolve):
    pm = resolve.GetProjectManager()
    project = pm.LoadProject(WORKHORSE_GRADE_PROJECT)
    if not project:
        project = pm.CreateProject(WORKHORSE_GRADE_PROJECT)
    return project


def _apply_cdl_to_timeline_item(timeline_item, style: str) -> bool:
    cdl = STYLE_CDL_GRADES.get(style, STYLE_CDL_GRADES["natural"])
    cdl_map = {"NodeIndex": "1", **cdl}
    return bool(timeline_item.SetCDL(cdl_map))


def grade_still_image(image_path: Path, style: str = "natural", dpi: int = 300) -> Dict[str, Any]:
    """Grades a single still photo through Resolve's real color engine using an
    ASC-CDL primary grade matching the requested style, then renders it back out as a
    TIFF - a legitimate, professional color-managed alternative/companion to the native
    OpenCV grading in photo_retoucher.py for Commanders who want Resolve's specific
    color science on a given shot."""
    image_path = Path(image_path)
    if not image_path.exists():
        return {"success": False, "error": f"Source image not found: {image_path}"}

    try:
        resolve = get_resolve()
        project = _get_or_create_grade_project(resolve)
        media_pool = project.GetMediaPool()
        media_storage = resolve.GetMediaStorage()

        clips = media_storage.AddItemListToMediaPool([str(image_path)])
        if not clips:
            return {"success": False, "error": "Resolve could not import the source image into its Media Pool."}

        timeline = media_pool.CreateTimelineFromClips(f"grade_{int(time.time())}", clips)
        if not timeline:
            return {"success": False, "error": "Resolve could not create a working timeline for the still."}

        project.SetCurrentTimeline(timeline)
        timeline_item = timeline.GetItemListInTrack("video", 1)[0]
        if not _apply_cdl_to_timeline_item(timeline_item, style):
            return {"success": False, "error": "Resolve rejected the CDL grade for this clip."}

        out_name = f"{image_path.stem}_{style}_davinci_graded"
        project.SetRenderSettings({
            "SelectAllFrames": True,
            "TargetDir": str(RENDER_STAGING_DIR),
            "CustomName": out_name,
            "ExportVideo": True,
            "ExportAudio": False,
            "Format": "tif",
            "FrameRate": project.GetSetting("timelineFrameRate") or "24"
        })
        job_id = project.AddRenderJob()
        project.StartRendering(job_id)
        timeout_s, waited = 120, 0
        while project.IsRenderingInProgress() and waited < timeout_s:
            time.sleep(1)
            waited += 1

        rendered = sorted(RENDER_STAGING_DIR.glob(f"{out_name}*"))
        if not rendered:
            return {"success": False, "error": "Render finished but no output file was found."}
        return {"success": True, "file_path": str(rendered[0]), "style": style, "engine": "davinci_resolve"}
    except DaVinciBridgeUnavailable as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"DaVinci grading failed: {e}"}


def grade_video_clip(video_path: Path, style: str = "natural") -> Dict[str, Any]:
    """Grades a video clip through Resolve's real color engine using an ASC-CDL
    primary grade matching the requested style, rendering a graded MP4/H.264 copy -
    for professional color work on concert/stage, event, or marketing footage before
    it goes out to a platform."""
    video_path = Path(video_path)
    if not video_path.exists():
        return {"success": False, "error": f"Source video not found: {video_path}"}

    try:
        resolve = get_resolve()
        project = _get_or_create_grade_project(resolve)
        media_pool = project.GetMediaPool()
        media_storage = resolve.GetMediaStorage()

        clips = media_storage.AddItemListToMediaPool([str(video_path)])
        if not clips:
            return {"success": False, "error": "Resolve could not import the source video into its Media Pool."}

        timeline = media_pool.CreateTimelineFromClips(f"grade_{int(time.time())}", clips)
        if not timeline:
            return {"success": False, "error": "Resolve could not create a working timeline for the clip."}

        project.SetCurrentTimeline(timeline)
        timeline_item = timeline.GetItemListInTrack("video", 1)[0]
        if not _apply_cdl_to_timeline_item(timeline_item, style):
            return {"success": False, "error": "Resolve rejected the CDL grade for this clip."}

        out_name = f"{video_path.stem}_{style}_davinci_graded"
        project.SetRenderSettings({
            "SelectAllFrames": True,
            "TargetDir": str(RENDER_STAGING_DIR),
            "CustomName": out_name,
            "ExportVideo": True,
            "ExportAudio": True,
            "Format": "mp4",
            "VideoCodec": "H.264"
        })
        job_id = project.AddRenderJob()
        project.StartRendering(job_id)
        timeout_s, waited = 600, 0
        while project.IsRenderingInProgress() and waited < timeout_s:
            time.sleep(2)
            waited += 2

        rendered = sorted(RENDER_STAGING_DIR.glob(f"{out_name}*"))
        if not rendered:
            return {"success": False, "error": "Render finished but no output file was found."}
        return {"success": True, "file_path": str(rendered[0]), "style": style, "engine": "davinci_resolve"}
    except DaVinciBridgeUnavailable as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"DaVinci grading failed: {e}"}


if __name__ == "__main__":
    print(json.dumps(check_connection(), indent=2))
