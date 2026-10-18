"""
Integration Test Suite for Cricut SVG Clean-Cut, Bambu Studio 3MF Mockups, and PPV 2257 Vault
==============================================================================================
Validates:
1. `CricutSVGOptimizer`: Micro-path / confetti pruning, node simplification, Cricut XML grouping.
2. `BambuMockupEngine`: Bambu Studio / OrcaSlicer `.3mf` container, lifestyle mockups (t-shirt, mug, bed).
3. `PPVTeaserEngine`: Dynamic censorship, vertical 9:16 micro-loop reel, 18 USC 2257 compliance vault.
4. `EtsyDigitalStore`: End-to-end integration with Cricut optimizer and Bambu 3MF mockups.
5. `AIOperatorEngine`: Internal tool routing and aliases for `cricut_optimize_svg`, `bambu_export_3mf`, and `generate_ppv_teaser`.
"""

from pathlib import Path
import zipfile
import numpy as np
from PIL import Image
import pytest

from pipeline.stages.svg_cricut_optimizer import cricut_svg_optimizer, CricutSVGOptimizer
from pipeline.stages.bambu_3mf_mockup_engine import bambu_mockup_engine, BambuMockupEngine
from pipeline.stages.ppv_teaser_engine import ppv_teaser_engine, PPVTeaserEngine
from pipeline.stages.etsy_digital_store import EtsyDigitalStore
from pipeline.stages.ai_operator import AIOperatorEngine


def test_cricut_svg_optimizer_cleans_confetti_and_simplifies_nodes(tmp_path):
    # Create an SVG with 1 large star/polygon and 3 tiny confetti specks
    raw_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">
  <g id="Layer_01_RED" fill="#FF0000">
    <!-- Large cutting shape -->
    <path d="M 100,100 L 400,100 L 400,400 L 100,400 Z"/>
    <!-- Micro confetti speck 1 (area = 4) -->
    <path d="M 500,500 L 502,500 L 502,502 L 500,502 Z"/>
    <!-- Micro confetti speck 2 (area = 9) -->
    <path d="M 600,600 L 603,600 L 603,603 L 600,603 Z"/>
  </g>
  <g id="Layer_02_BLUE" fill="#0000FF">
    <!-- Medium circle-like polygon -->
    <path d="M 500,100 L 700,100 L 700,300 L 500,300 Z"/>
    <!-- Micro confetti speck 3 -->
    <path d="M 800,800 L 802,800 L 802,802 Z"/>
  </g>
</svg>"""
    in_svg = tmp_path / "dirty_test.svg"
    in_svg.write_text(raw_svg, encoding="utf-8")
    out_svg = tmp_path / "clean_test_cricut.svg"

    res = cricut_svg_optimizer.optimize_svg_file(in_svg, output_svg_path=out_svg, min_cut_area_px=50.0)
    assert res["success"] is True
    assert res["confetti_paths_removed"] >= 2
    assert res["cricut_compatibility_score"] == 100
    assert out_svg.exists()

    clean_content = out_svg.read_text(encoding="utf-8")
    assert "cricut:layer-name" in clean_content
    assert 'fill-rule="evenodd"' in clean_content


def test_bambu_3mf_project_builder_creates_valid_container(tmp_path):
    # Create a simple binary STL box
    stl_path = tmp_path / "cube_test.stl"
    # Write sample ASCII STL
    ascii_stl = """solid cube
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 10.0
      vertex 10.0 0.0 10.0
      vertex 10.0 10.0 10.0
    endloop
  endfacet
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 10.0
      vertex 10.0 10.0 10.0
      vertex 0.0 10.0 10.0
    endloop
  endfacet
endsolid cube"""
    stl_path.write_text(ascii_stl, encoding="utf-8")
    out_3mf = tmp_path / "cube_project.3mf"

    res = bambu_mockup_engine.export_bambu_3mf_project(
        stl_or_glb_path=stl_path,
        output_3mf_path=out_3mf,
        model_name="TestSculpt",
        layer_height_mm=0.16,
        infill_pct=15,
    )
    assert res["success"] is True
    assert out_3mf.exists()

    # Verify 3MF is a valid ZIP package containing required OPC files
    with zipfile.ZipFile(out_3mf, "r") as z:
        names = z.namelist()
        assert "[Content_Types].xml" in names
        assert "_rels/.rels" in names
        assert "3D/3dmodel.model" in names
        assert "Metadata/model_settings.config" in names

        config_data = z.read("Metadata/model_settings.config").decode("utf-8")
        assert "gyroid" in config_data
        assert "tree(auto)" in config_data


def test_bambu_mockup_engine_generates_all_lifestyle_mockups(tmp_path):
    # Create sample graphic PNG and sample clay render
    graphic_png = tmp_path / "sample_graphic.png"
    Image.new("RGBA", (500, 500), (220, 40, 40, 255)).save(graphic_png)

    clay_png = tmp_path / "sample_clay.png"
    Image.new("RGBA", (500, 500), (140, 150, 160, 255)).save(clay_png)

    engine = BambuMockupEngine(output_dir=tmp_path)
    mockups = engine.generate_all_mockups(
        svg_preview_png_path=graphic_png,
        stl_clay_render_path=clay_png,
        output_prefix="unit_test",
    )

    assert "tshirt_mockup" in mockups and Path(mockups["tshirt_mockup"]).exists()
    assert "mug_mockup" in mockups and Path(mockups["mug_mockup"]).exists()
    assert "wood_mockup" in mockups and Path(mockups["wood_mockup"]).exists()
    assert "printer_bed_mockup" in mockups and Path(mockups["printer_bed_mockup"]).exists()


def test_ppv_teaser_engine_censorship_and_micro_loop(tmp_path):
    # Create sample portrait image (800x1200) with skin tones
    test_img = tmp_path / "performer_test.jpg"
    img_arr = np.full((1200, 800, 3), (170, 195, 235), dtype=np.uint8)  # BGR skin tone approx
    Image.fromarray(img_arr).save(test_img)

    engine = PPVTeaserEngine(output_dir=tmp_path)

    # 1. Test dynamic frosted glass censorship
    c_res = engine.apply_dynamic_censorship(test_img, mode="frosted_glass", badge_text="[ VIP EXCLUSIVE ]")
    assert c_res["success"] is True
    assert Path(c_res["censored_promo_image"]).exists()

    # 2. Test micro-loop video generation (1.0 sec for fast test)
    v_res = engine.create_micro_teaser_loop(test_img, duration_sec=1.0, cta_text="UNLOCK IN DM")
    assert v_res["success"] is True
    assert Path(v_res["teaser_video_path"]).exists()

    # 3. Test 18 USC 2257 compliance release generation
    vault_res = engine.generate_2257_compliance_package(model_stage_name="Scarlet_01", output_dir=tmp_path)
    assert vault_res["success"] is True
    assert Path(vault_res["compliance_doc_path"]).exists()
    assert len(vault_res["verification_hash"]) >= 16


def test_etsy_digital_store_cricut_and_bambu_integration(tmp_path, monkeypatch):
    store = EtsyDigitalStore(output_base=str(tmp_path))

    # Mock comfy_bridge.generate_etsy_svg_from_idea_or_image
    dummy_svg = tmp_path / "mock.svg"
    dummy_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M 10 10 L 90 10 L 90 90 Z"/></svg>', encoding="utf-8")
    dummy_png = tmp_path / "mock.png"
    Image.new("RGB", (100, 100), (50, 50, 50)).save(dummy_png)

    def mock_gen_svg(*args, **kwargs):
        return {
            "success": True,
            "svg_path": str(dummy_svg),
            "vector_preview_png": str(dummy_png),
            "master_png": str(dummy_png),
        }

    monkeypatch.setattr("pipeline.stages.comfyui_bridge.comfy_bridge.generate_etsy_svg_from_idea_or_image", mock_gen_svg)

    svg_asset = store.create_svg_stencil_asset(idea_prompt="celtic wolf medallion", output_name="celtic_wolf")
    assert svg_asset["success"] is True
    assert "cricut_optimization" in svg_asset
    assert "commercial_mockups" in svg_asset


def test_synapse_internal_tool_dispatch_for_cricut_bambu_and_ppv(tmp_path):
    engine = AIOperatorEngine()
    assert "cricut_optimize_svg" in engine.TOOL_AGENT_MAP
    assert "bambu_export_3mf" in engine.TOOL_AGENT_MAP
    assert "generate_ppv_teaser" in engine.TOOL_AGENT_MAP

    # Test cricut tool alias execution
    test_svg = tmp_path / "tool_dispatch.svg"
    test_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M 0 0 L 50 0 L 50 50 Z"/></svg>', encoding="utf-8")

    res_cricut = engine.execute_internal_tool({
        "tool": "clean_svg",
        "svg_path": str(test_svg),
    })
    assert res_cricut["status"] == "ok"
