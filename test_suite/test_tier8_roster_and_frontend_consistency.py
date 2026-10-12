"""
Test Tier 8 — Agent Roster, Character Badges, Decision #6, and Frontend Consistency
Verifies:
1. Complete 14-agent roster defined in dashboard/static/js/agents.js
2. Standalone app separation (Prism is NOT an agent, verified absent from AGENTS_METADATA and characters dir)
3. 100% SVG avatar coverage in dashboard/static/img/characters/ for all 14 agents
4. Pipeline stage agents in pipeline/orchestrator.py are fully registered in AGENTS_METADATA
5. Synapse SYSTEM_PROMPT in pipeline/stages/ai_operator.py consistency
6. Decision #6 alignment: Vanguard (Video Intake Sentinel & Dispatcher) vs Mercury (Marketing Maestro) vs Radar (Order Intake)
7. Frontend timer and resilience contracts (app.js 4000ms stats polling, pipeline.js 3000ms WS reconnect)
"""

import json
import re
from pathlib import Path
import pytest

BASE_DIR = Path(r"F:\WORKHORSE")
EXPECTED_14_AGENTS = {
    "synapse",
    "vanguard",
    "iris",
    "echo",
    "aura",
    "mercury",
    "herald",
    "forge",
    "cipher",
    "scribe",
    "muse",
    "apex",
    "radar",
    "scrubber"
}

def parse_agents_metadata():
    """Extract and parse AGENTS_METADATA dictionary keys and structure from agents.js."""
    agents_js = (BASE_DIR / "dashboard" / "static" / "js" / "agents.js").read_text(encoding="utf-8")
    # Extract keys using regex pattern matching agent definition blocks: '<agentKey>: {'
    match = re.search(r"const AGENTS_METADATA\s*=\s*\{([\s\S]*?)\n\};", agents_js)
    assert match, "Could not find AGENTS_METADATA in agents.js"
    block = match.group(1)
    
    agent_keys = re.findall(r"^\s*([a-z_]+)\s*:\s*\{", block, re.MULTILINE)
    return set(agent_keys), block, agents_js


def test_agents_metadata_exact_roster():
    agent_keys, _, _ = parse_agents_metadata()
    assert agent_keys == EXPECTED_14_AGENTS, (
        f"Mismatch in AGENTS_METADATA. Expected {EXPECTED_14_AGENTS}, got {agent_keys}"
    )
    # Explicitly ensure Prism is not treated as an agent
    assert "prism" not in agent_keys, "Prism must NOT be in AGENTS_METADATA (it is a standalone app, not an agent)"


def test_all_14_agents_have_svg_avatars():
    characters_dir = BASE_DIR / "dashboard" / "static" / "img" / "characters"
    assert characters_dir.exists(), "Characters directory missing"
    
    for agent in EXPECTED_14_AGENTS:
        svg_file = characters_dir / f"{agent}.svg"
        assert svg_file.exists(), f"Missing character avatar SVG for agent '{agent}': {svg_file}"
        assert svg_file.stat().st_size > 50, f"Character avatar SVG for agent '{agent}' is suspiciously empty"
    
    # Verify prism.svg is not in characters directory
    prism_svg = characters_dir / "prism.svg"
    assert not prism_svg.exists(), "prism.svg should not exist in characters directory because Prism is a standalone app"


def test_pipeline_orchestrator_stage_agents_supported_in_ui():
    orchestrator_py = (BASE_DIR / "pipeline" / "orchestrator.py").read_text(encoding="utf-8")
    active_agent_refs = set(re.findall(r'job\.active_agent\s*=\s*["\']([a-zA-Z0-9_]+)["\']', orchestrator_py))
    
    assert len(active_agent_refs) >= 6, f"Expected multiple active agents in orchestrator, found {active_agent_refs}"
    agent_keys, _, _ = parse_agents_metadata()
    
    for agent in active_agent_refs:
        assert agent in agent_keys, (
            f"Orchestrator uses stage agent '{agent}', but '{agent}' is not registered in AGENTS_METADATA in agents.js"
        )


def test_synapse_system_prompt_roster_consistency():
    ai_op_py = (BASE_DIR / "pipeline" / "stages" / "ai_operator.py").read_text(encoding="utf-8")
    
    # Check that each expected agent appears in ai_operator.py SYSTEM_PROMPT
    for agent in EXPECTED_14_AGENTS:
        # Match case-insensitively agent name in prompt
        assert re.search(rf"\b{agent}\b", ai_op_py, re.IGNORECASE), f"Agent '{agent}' missing in ai_operator.py SYSTEM_PROMPT"
        
    # Check note that Prism is a standalone app
    assert "Prism is a standalone" in ai_op_py or "Prism is a standalone viewer app" in ai_op_py, (
        "ai_operator.py SYSTEM_PROMPT must clarify that Prism is a standalone app, not a WORKHORSE agent"
    )


def test_decision_6_role_specializations():
    _, block, _ = parse_agents_metadata()
    
    # 1. Vanguard should be video intake / pipeline dispatcher
    vanguard_match = re.search(r"vanguard:\s*\{([\s\S]*?)\},", block)
    assert vanguard_match, "vanguard block not found in agents.js"
    vanguard_text = vanguard_match.group(1)
    assert "Intake" in vanguard_text or "Pipeline Dispatcher" in vanguard_text, "Vanguard must reflect Video Intake / Dispatcher role"
    
    # 2. Mercury should be marketing / social broadcaster
    mercury_match = re.search(r"mercury:\s*\{([\s\S]*?)\},", block)
    assert mercury_match, "mercury block not found in agents.js"
    mercury_text = mercury_match.group(1)
    assert "Marketing" in mercury_text or "Traffic" in mercury_text, "Mercury must reflect Marketing / Traffic Strategist role"
    
    # 3. Radar should be order intake
    radar_match = re.search(r"radar:\s*\{([\s\S]*?)\},", block)
    assert radar_match, "radar block not found in agents.js"
    radar_text = radar_match.group(1)
    assert "Order Radar" in radar_text, "Radar must reflect Order Radar & Client Intake role"


def test_agent_dossier_contract_completeness():
    _, block, _ = parse_agents_metadata()
    for agent in EXPECTED_14_AGENTS:
        pattern = rf"{agent}:\s*\{{([\s\S]*?)\n\s*\}}(?:,|$)"
        match = re.search(pattern, block)
        assert match, f"Could not isolate config block for agent '{agent}'"
        agent_block = match.group(1)
        
        assert 'name:' in agent_block, f"Agent '{agent}' missing 'name'"
        assert 'role:' in agent_block, f"Agent '{agent}' missing 'role'"
        assert 'hardware:' in agent_block, f"Agent '{agent}' missing 'hardware'"
        assert 'model:' in agent_block, f"Agent '{agent}' missing 'model'"
        assert 'privacyStatus:' in agent_block, f"Agent '{agent}' missing 'privacyStatus'"
        assert 'defaultQuote:' in agent_block, f"Agent '{agent}' missing 'defaultQuote'"
        assert 'whatItDoes:' in agent_block, f"Agent '{agent}' missing 'whatItDoes'"
        assert 'configFields:' in agent_block, f"Agent '{agent}' missing 'configFields'"


def test_frontend_timer_resilience_contracts():
    app_js = (BASE_DIR / "dashboard" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    pipeline_js = (BASE_DIR / "dashboard" / "static" / "js" / "pipeline.js").read_text(encoding="utf-8")
    
    # 1. Telemetry polling in app.js should be ~4000ms with try/catch
    assert "pollTelemetry" in app_js
    assert "4000" in app_js, "app.js should poll telemetry every 4000ms"
    assert "try {" in app_js and "catch" in app_js
    
    # 2. WebSocket auto-reconnect in pipeline.js should be ~3000ms
    assert "initWebSocket" in pipeline_js
    assert "3000" in pipeline_js, "pipeline.js should reconnect WebSocket after 3000ms"
    assert "onclose" in pipeline_js


def test_open_folder_api_creates_and_scans():
    from fastapi.testclient import TestClient
    from dashboard.server import app, _get_session_secret, SESSION_COOKIE
    from shared.auth import make_session_token

    client = TestClient(app)
    token = make_session_token(_get_session_secret())
    client.cookies.set(SESSION_COOKIE, token)

    target_path = BASE_DIR / "workspace" / "photos_output"
    res = client.post("/api/open-folder", json={"path": str(target_path)})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"
    assert data["folder_name"] == "photos_output"
    assert "photos_output" in data["opened"]
    assert "files" in data
    assert isinstance(data["files"], list)
    assert "total_files" in data
    assert "total_size_mb" in data
    assert "opened_in_os" in data
    assert target_path.exists()


def test_open_brand_folder_api():
    from fastapi.testclient import TestClient
    from dashboard.server import app, _get_session_secret, SESSION_COOKIE
    from shared.auth import make_session_token

    client = TestClient(app)
    token = make_session_token(_get_session_secret())
    client.cookies.set(SESSION_COOKIE, token)

    res = client.post("/api/open-brand-folder")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"
    assert "brand_assets" in data["opened"]
    assert data["folder_name"] == "brand_assets"


def test_folder_browser_modal_in_index_html():
    html = (BASE_DIR / "dashboard" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="modal-folder-browser"' in html
    assert 'id="folder-browser-title"' in html
    assert 'id="folder-browser-path"' in html
    assert 'id="folder-browser-files-list"' in html
    assert 'id="btn-copy-folder-path"' in html
    assert 'id="btn-close-folder-browser"' in html


def test_all_folder_buttons_wired_to_universal_opener():
    app_js = (BASE_DIR / "dashboard" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    pipe_js = (BASE_DIR / "dashboard" / "static" / "js" / "pipeline.js").read_text(encoding="utf-8")
    bays_js = (BASE_DIR / "dashboard" / "static" / "js" / "bays.js").read_text(encoding="utf-8")

    assert "window.openWorkspaceFolder =" in app_js
    assert "window.openWorkspaceFolder" in pipe_js
    assert "window.openWorkspaceFolder" in bays_js
    
    # Check specific folder buttons wire to window.openWorkspaceFolder
    assert "photos_output" in bays_js
    assert "inspiration" in bays_js
    assert "etsy_bundles" in bays_js
    assert "fiverr_deliveries" in bays_js
    assert "brand_assets" in app_js


def test_responsive_meta_and_css_media_queries():
    html = (BASE_DIR / "dashboard" / "static" / "index.html").read_text(encoding="utf-8")
    assert '<meta name="viewport"' in html
    assert 'viewport-fit=cover' in html
    assert 'mobile-pane-switcher' in html

    layout_css = (BASE_DIR / "dashboard" / "static" / "css" / "operator_layout.css").read_text(encoding="utf-8")
    assert "@media (max-width: 1024px)" in layout_css
    assert "@media (max-width: 768px)" in layout_css
    assert "@media (max-width: 420px)" in layout_css
