"""
WORKHORSE DaVinci Resolve Post-Processing Pipeline for MiniMax H3 Videos
Upscales raw 768p ComfyUI generations to 4K UHD (2160x3840) with 3x Neural SuperScale
and applies the Clean Commercial Beauty Color Grade Preset.
"""

import sys
import os
import time

def process_h3_video_in_davinci(
    input_video_path,
    output_dir=r"F:\WORKHORSE\workspace\scratch",
    output_name=None,
    preset="clean_beauty", # "clean_beauty" or "natural"
    width=2160,
    height=3840,
    fps=24.0
):
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Input video not found: {input_video_path}")
        
    os.makedirs(output_dir, exist_ok=True)
    if not output_name:
        base = os.path.splitext(os.path.basename(input_video_path))[0]
        output_name = f"{base}_davinci_4k"

    # Initialize DaVinci Resolve Scripting API
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
    except ImportError:
        # Fallback to standard environment lookup
        ext_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules"
        sys.path.append(ext_path)
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")

    if not resolve:
        raise RuntimeError("Could not connect to DaVinci Resolve. Please ensure DaVinci Resolve Studio is running.")

    pm = resolve.GetProjectManager()
    proj_name = f"H3_PostProcess_{int(time.time())}"
    proj = pm.CreateProject(proj_name)
    if not proj:
        proj = pm.GetCurrentProject()

    # 1. Configure Timeline Settings
    proj.SetSetting("timelineResolutionWidth", str(width))
    proj.SetSetting("timelineResolutionHeight", str(height))
    proj.SetSetting("timelineFrameRate", str(fps))
    proj.SetSetting("superScale", 3) # 3x Neural SuperScale
    proj.SetSetting("superScaleSharpness", "1")
    proj.SetSetting("superScaleNoiseReduction", "0")
    proj.SetSetting("imageResizeMode", "sharper")

    # 2. Import Media
    mp = proj.GetMediaPool()
    items = mp.ImportMedia([input_video_path])
    if not items:
        raise RuntimeError(f"Failed to import media: {input_video_path}")

    # 3. Create Timeline
    tl = mp.CreateTimelineFromClips("H3_SuperScale_Master", items)
    v_items = tl.GetItemListInTrack("video", 1)
    if not v_items:
        raise RuntimeError("No items found on video track 1")
    clip = v_items[0]

    # 4. Color Grading
    graph = clip.GetNodeGraph()
    if preset == "clean_beauty":
        # Apply Clean Studio Beauty 3D LUT
        lut_path = "MCP/Workhorse_Clean_Studio_Beauty.cube"
        graph.SetLUT(1, lut_path)
        clip.SetCDL({
            "NodeIndex": 1,
            "Slope": "1.00 1.00 1.00",
            "Offset": "0.00 0.00 0.00",
            "Power": "1.00 1.00 1.00",
            "Saturation": "1.00"
        })
    else: # pure natural
        graph.ResetAllGrades()
        clip.SetCDL({
            "NodeIndex": 1,
            "Slope": "1.00 1.00 1.00",
            "Offset": "0.01 0.01 0.01", # open shadow details
            "Power": "0.99 0.99 0.99",
            "Saturation": "1.00"
        })

    # 5. Render Settings
    proj.DeleteAllRenderJobs()
    proj.SetCurrentRenderFormatAndCodec("mp4", "H264_NVIDIA")
    proj.SetRenderSettings({
        "SelectAllFrames": True,
        "TargetDir": output_dir,
        "CustomName": output_name,
        "ExportVideo": True,
        "ExportAudio": True,
        "FormatWidth": width,
        "FormatHeight": height,
        "FrameRate": fps,
        "VideoQuality": "Best"
    })

    # 6. Queue and Render
    job_id = proj.AddRenderJob()
    proj.StartRendering([job_id])
    print(f"Rendering {output_name} in DaVinci Resolve Studio...")

    while proj.IsRenderingInProgress():
        time.sleep(1)

    status = proj.GetRenderJobStatus(job_id)
    out_file = os.path.join(output_dir, f"{output_name}.mp4")
    print(f"Render complete! Status: {status.get('JobStatus')}")
    print(f"Deliverable saved to: {out_file}")
    return out_file

if __name__ == "__main__":
    test_in = sys.argv[1] if len(sys.argv) > 1 else r"F:\WORKHORSE\workspace\scratch\melissa_h3_test_03_12502268.mp4"
    process_h3_video_in_davinci(test_in)
