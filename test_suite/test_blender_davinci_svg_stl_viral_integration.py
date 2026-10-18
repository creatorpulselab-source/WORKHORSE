"""Integration & regression test suite for WORKHORSE's Blender 5.2 MCP/CLI bridge,
DaVinci Resolve Studio 21.1+ Neural Engine Super Scale bridge, 5-Mode Single-Image
Viral Video Director, Full-Color 6-Layer / B&W Vinyl Cut .SVG generator, and
Watertight .STL + .GLB ("From Idea" or "From Image") pipelines."""

import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

from shared import comfyui_knowledge as knowledge
from shared.output_categories import OUTPUT_CATEGORIES, build_media_entry, categorize_path
from shared.output_preview import preview_format
from pipeline.stages.ai_operator import AIOperatorEngine, SYSTEM_PROMPT
from pipeline.stages.blender_bridge import BlenderBridge
from pipeline.stages.comfyui_bridge import ComfyUIBridge
from pipeline.stages.davinci_resolve_bridge import DaVinciResolveBridge
from pipeline.stages.etsy_digital_store import EtsyDigitalStore
from pipeline.stages.single_image_viral_director import SingleImageViralDirector, VIRAL_MODES


# ---------------------------------------------------------------------------
# 1. ComfyUI LLM Curriculum & Runtime Knowledge Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("query", "expected_section"), [
    ("Create a Cricut full-color stencil SVG cut file", "### 19.4"),
    ("Export a watertight manifold STL in Blender with voxel remesh", "### 20.4"),
    ("Run the 5-mode viral video director handheld_camera and one_take_shot", "### 21.4"),
    ("Upscale video in DaVinci Resolve Studio with Super Scale and Optical Flow", "### 21.5"),
])
def test_knowledge_retrieves_new_svg_blender_viral_and_davinci_sections(query, expected_section):
    context = knowledge.get_comfyui_context("operator", query)
    assert expected_section in context
    assert len(context) <= knowledge.MAX_CONTEXT_CHARS


# ---------------------------------------------------------------------------
# 2. Output Preview & Gallery Categories (.svg, .stl, .glb, viral .mp4)
# ---------------------------------------------------------------------------

def test_preview_format_supports_svg_and_stl():
    assert preview_format("emblem.svg") == ("image", "image/svg+xml")
    assert preview_format("sculpture.stl") == ("model_3d", "model/stl")
    assert preview_format("model.glb") == ("model_3d", "model/gltf-binary")


def test_new_output_categories_resolve_and_attach_media(tmp_path, monkeypatch):
    svg_dir = tmp_path / "06_SVG_TShirt_Vinyl_Cut_Files"
    stl_dir = tmp_path / "03_3D_Maker_PBR_Prop_Design"
    viral_dir = tmp_path / "shorts_out" / "mode_handheld_camera"
    pbr_dir = tmp_path / "comfy_3d_pbr_renders"
    for d in (svg_dir, stl_dir, viral_dir, pbr_dir):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setitem(OUTPUT_CATEGORIES, "etsy_svg_cut_files", {**OUTPUT_CATEGORIES["etsy_svg_cut_files"], "dir": svg_dir})
    monkeypatch.setitem(OUTPUT_CATEGORIES, "etsy_3d_stl_glb_assets", {**OUTPUT_CATEGORIES["etsy_3d_stl_glb_assets"], "dir": stl_dir})
    monkeypatch.setitem(OUTPUT_CATEGORIES, "viral_video_director", {**OUTPUT_CATEGORIES["viral_video_director"], "dir": tmp_path / "shorts_out"})
    monkeypatch.setitem(OUTPUT_CATEGORIES, "marketing_3d_models", {**OUTPUT_CATEGORIES["marketing_3d_models"], "dir": pbr_dir})

    svg_file = svg_dir / "custom_stencil.svg"
    svg_file.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    stl_file = pbr_dir / "dragon_bust.stl"
    stl_file.write_bytes(b"solid test")
    viral_mp4 = viral_dir / "handheld_camera_master_reel.mp4"
    viral_mp4.write_bytes(b"fake-mp4")

    assert categorize_path(svg_file) == "etsy_svg_cut_files"
    assert categorize_path(stl_file) == "marketing_3d_models"
    assert categorize_path(viral_mp4) == "viral_video_director"

    svg_entry = build_media_entry(svg_file, title="Custom Stencil SVG")
    assert svg_entry["preview_type"] == "image"
    assert svg_entry["group"] == "etsy"

    stl_entry = build_media_entry(stl_file, title="Watertight STL")
    assert stl_entry["preview_type"] == "model_3d"
    assert stl_entry["group"] == "synapse"

    viral_entry = build_media_entry(viral_mp4, title="Viral Reel")
    assert viral_entry["preview_type"] == "video"
    assert viral_entry["group"] == "synapse"


# ---------------------------------------------------------------------------
# 3. Full-Color 6-Layer Stencil & B&W Cut .SVG Generation (Idea or Image)
# ---------------------------------------------------------------------------

def _create_synthetic_stencil_image(path: Path):
    img = Image.new("RGB", (256, 256), (245, 240, 230))
    draw = ImageDraw.Draw(img)
    draw.ellipse([28, 28, 228, 228], fill=(20, 35, 65))
    draw.polygon([(128, 48), (195, 190), (60, 190)], fill=(220, 85, 35))
    draw.ellipse([96, 96, 160, 160], fill=(40, 180, 170))
    img.save(path)


def test_generate_etsy_svg_from_image_full_color_and_bw_with_xml_escaping(tmp_path):
    src_img = tmp_path / "source_art.png"
    _create_synthetic_stencil_image(src_img)

    bridge = ComfyUIBridge()

    # 1. Full-Color 6-layer stencil with '&' in title/text to verify XML escaping
    fc_res = bridge.generate_etsy_svg_from_idea_or_image(
        source_image_path=src_img,
        output_name="rock_and_roll_badge",
        stencil_mode="full_color",
        num_layers=4,
        top_text="ROCK & ROLL",
        bottom_text="CUSTOM GARAGE",
        output_dir=tmp_path,
    )
    assert fc_res["success"] is True
    assert fc_res["creation_mode"] == "from_image"
    fc_svg = Path(fc_res["svg_path"])
    assert fc_svg.exists()
    assert Path(fc_res["layers_strip_png"]).exists()

    # Parse XML to verify valid SVG & escaped '&amp;' + layered <g> groups
    root = ET.parse(fc_svg).getroot()
    groups = [el.attrib.get("id", "") for el in root.iter() if el.tag.endswith("g")]
    assert any(g.startswith("Layer_01_") for g in groups)

    # 2. B&W Vinyl Cut mode
    bw_res = bridge.generate_etsy_svg_from_idea_or_image(
        source_image_path=src_img,
        output_name="skull_and_roses_bw",
        stencil_mode="bw_cut",
        top_text="LIVE FREE",
        output_dir=tmp_path,
    )
    assert bw_res["success"] is True
    bw_svg = Path(bw_res["svg_path"])
    assert bw_svg.exists()
    ET.parse(bw_svg)  # Must parse with 0 XML errors


def test_shipped_media_kit_svgs_and_stls_pass_strict_integrity():
    svg_kit_dir = Path(r"F:\WORKHORSE\workspace\media_kits\06_SVG_TShirt_Vinyl_Cut_Files")
    if svg_kit_dir.exists():
        svg_files = list(svg_kit_dir.glob("*.svg"))
        assert len(svg_files) >= 10
        for sf in svg_files:
            ET.parse(sf)  # 0 XML syntax errors across all shipped SVGs

    stl_kit_dir = Path(r"F:\WORKHORSE\workspace\media_kits\03_3D_Maker_PBR_Prop_Design")
    if stl_kit_dir.exists():
        for stl_name in ("dragon_guardian_bust.stl", "celestial_arcane_chalice.stl", "cyber_wolf_helmet.stl", "svg_3d_relief_medallion.stl"):
            sp = stl_kit_dir / stl_name
            assert sp.exists(), f"Missing {stl_name}"
            data = sp.read_bytes()
            tri_count = struct.unpack("<I", data[80:84])[0]
            assert tri_count > 1000
            assert len(data) == 84 + tri_count * 50


# ---------------------------------------------------------------------------
# 4. DaVinci Resolve Studio 21.1+ Super Scale & 5-Mode Viral Video Director
# ---------------------------------------------------------------------------

def test_davinci_resolve_bridge_generates_valid_33x33x33_cube_lut(tmp_path):
    resolve = DaVinciResolveBridge(lut_dir=tmp_path)
    lut_path = resolve.generate_cinematic_cube_lut("Test_Grade.cube")
    assert lut_path.exists()
    lines = [
        ln.strip() for ln in lut_path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith(("#", "TITLE", "LUT_3D_SIZE", "DOMAIN_"))
    ]
    assert len(lines) == 33 * 33 * 33


def test_single_image_viral_director_has_all_5_modes_and_orchestrates_super_scale(tmp_path):
    assert set(VIRAL_MODES.keys()) == {
        "handheld_camera", "micro_cinema", "fast_cut", "one_take_shot", "time_lapse"
    }
    src_img = tmp_path / "portrait.png"
    _create_synthetic_stencil_image(src_img)

    director = SingleImageViralDirector()
    fake_plate = tmp_path / "plate_01.png"
    _create_synthetic_stencil_image(fake_plate)
    fake_clip = tmp_path / "clip_01.mp4"
    fake_clip.write_bytes(b"fake-mp4")

    with patch.object(director, "generate_klein_multi_angle_edits", return_value=[fake_plate]), \
         patch.object(director.comfy, "remote_purge_vram", return_value={"success": True}), \
         patch.object(director.comfy, "generate_video_fasth3", return_value={"success": True, "file_path": str(fake_clip)}), \
         patch.object(director.resolve, "assemble_and_grade_timeline_in_resolve", return_value={"status": "COMPLETED", "super_scale": "3x", "codec": "H264_NVIDIA"}) as mock_resolve:
        res = director.render_viral_mode_video(
            source_image_path=src_img,
            mode="one_take_shot",
            work_dir=tmp_path / "work",
            super_scale=3,
        )
        assert res["success"] is True
        assert res["mode"] == "one_take_shot"
        assert mock_resolve.call_args.kwargs["super_scale"] == 3


# ---------------------------------------------------------------------------
# 5. SYNAPSE AI Operator Tool Dispatch & System Diagnostics
# ---------------------------------------------------------------------------

def test_synapse_system_prompt_and_tool_dispatch_for_svg_stl_and_viral_director(tmp_path):
    assert "comfy_generate_svg" in SYSTEM_PROMPT
    assert "comfy_viral_video_director" in SYSTEM_PROMPT
    assert "Super Scale" in SYSTEM_PROMPT
    assert "comfy_generate_svg" in AIOperatorEngine.TOOL_AGENT_MAP
    assert "comfy_viral_video_director" in AIOperatorEngine.TOOL_AGENT_MAP
    assert "comfy_generate_3d_pbr" in AIOperatorEngine.TOOL_AGENT_MAP

    engine = AIOperatorEngine()

    # 1. comfy_generate_3d_pbr from idea (also testing 'make_stl' alias)
    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_3d_glb_stl_from_idea_or_image") as mock_3d:
        mock_3d.return_value = {
            "success": True,
            "creation_mode": "from_idea",
            "glb_path": str(tmp_path / "model.glb"),
            "stl_path": str(tmp_path / "model.stl"),
        }
        r3d = engine.execute_internal_tool({
            "tool": "make_stl",
            "prompt": "ornate cyberpunk dragon bust",
            "output_name": "dragon_bust",
        })
        assert r3d["status"] == "ok"
        assert mock_3d.call_args.kwargs["idea_prompt"] == "ornate cyberpunk dragon bust"

    # 2. comfy_generate_svg from idea (also testing 'generate_svg' alias)
    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_etsy_svg_from_idea_or_image") as mock_svg:
        mock_svg.return_value = {
            "success": True,
            "creation_mode": "from_idea",
            "svg_path": str(tmp_path / "badge.svg"),
            "vector_preview_png": str(tmp_path / "badge_preview.png"),
            "layers_strip_png": str(tmp_path / "badge_strip.png"),
        }
        rsvg = engine.execute_internal_tool({
            "tool": "generate_svg",
            "prompt": "retro synthwave sunset palm badge",
            "stencil_mode": "full_color",
            "top_text": "RETRO VIBES",
        })
        assert rsvg["status"] == "ok"
        assert mock_svg.call_args.kwargs["idea_prompt"] == "retro synthwave sunset palm badge"

    # 3. EtsyDigitalStore helper methods delegate cleanly
    store = EtsyDigitalStore(output_base=str(tmp_path))
    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_etsy_svg_from_idea_or_image", return_value={"success": True}) as m_store_svg, \
         patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_3d_glb_stl_from_idea_or_image", return_value={"success": True}) as m_store_3d:
        assert store.create_svg_stencil_asset(idea_prompt="vintage biker eagle")["success"] is True
        assert store.create_3d_glb_stl_asset(idea_prompt="arcane crystal goblet")["success"] is True
        assert m_store_svg.called and m_store_3d.called
