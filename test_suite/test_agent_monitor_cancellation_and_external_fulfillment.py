"""
Unit tests for the Real-time Agent & Process Monitor, Stuck Process Cancellation,
Content Deletion with Path Traversal Protection, and External Fulfillment (Etsy & Fiverr).
"""
import time
import shutil
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from dashboard.server import app, orchestrator, order_radar, BASE_DIR, _get_session_secret, SESSION_COOKIE
from pipeline.orchestrator import PipelineJob
from shared.agent_roster import AGENT_ROSTER
from shared.auth import make_session_token

client = TestClient(app)
client.cookies.set(SESSION_COOKIE, make_session_token(_get_session_secret()))


# -----------------------------------------------------------------------------
# 1. Real-time Agent & Process Monitor Tests
# -----------------------------------------------------------------------------

def test_active_agents_monitor_structure():
    """Verify GET /api/monitor/agents-active returns all 14 agents and valid telemetry."""
    response = client.get("/api/monitor/agents-active")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "has_active" in data
    assert "active_jobs" in data
    assert "agents" in data
    assert "active_count" in data
    assert "stalled_count" in data
    assert "stalled_alerts" in data
    
    # Verify all 14 agents from AGENT_ROSTER are present
    agent_ids = {a["id"] for a in data["agents"]}
    for expected_id in AGENT_ROSTER.keys():
        assert expected_id in agent_ids, f"Agent {expected_id} missing from monitor response"
        
    for agent in data["agents"]:
        assert agent["state"] in ("idle", "active", "stalled")
        assert "name" in agent
        assert "symbol" in agent
        assert "current_task" in agent
        assert "hardware" in agent


def test_pipeline_job_cancellation_and_abort():
    """Verify job cancellation sets cancel_requested and halts gracefully."""
    dummy_video = BASE_DIR / "workspace" / "temp" / "test_cancel_sample.mp4"
    dummy_video.parent.mkdir(parents=True, exist_ok=True)
    dummy_video.write_bytes(b"dummy_mp4_bytes")
    
    job = orchestrator.create_job(dummy_video, preset="Test Preset")
    job.status = "running"
    job.started_at = time.time()
    job.stage_started_at = time.time()
    job.current_stage = 2
    job.active_agent = "iris"
    
    # Test cancel endpoint
    res = client.post(f"/api/pipeline/jobs/{job.job_id}/cancel")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "ok"
    assert job.cancel_requested is True
    assert job.status == "cancelling"


def test_stalled_process_detection_in_monitor():
    """Verify that jobs exceeding 180s on a stage are flagged as stalled in the monitor."""
    dummy_video = BASE_DIR / "workspace" / "temp" / "test_stalled_sample.mp4"
    dummy_video.parent.mkdir(parents=True, exist_ok=True)
    dummy_video.write_bytes(b"dummy_mp4_bytes")
    
    job = orchestrator.create_job(dummy_video, preset="Test Preset")
    job.status = "running"
    job.started_at = time.time() - 300
    job.stage_started_at = time.time() - 250  # Over 180s threshold
    job.current_stage = 3
    job.active_agent = "forge"
    job.agent_message = "Forge: Cutting 60s teaser trailer..."
    
    assert job.is_stalled is True
    assert job.stage_elapsed_sec >= 240
    
    # Query monitor API
    res = client.get("/api/monitor/agents-active")
    assert res.status_code == 200
    data = res.json()
    assert data["stalled_count"] >= 1
    stalled_job_ids = [s["job_id"] for s in data["stalled_alerts"]]
    assert job.job_id in stalled_job_ids
    
    # Clean up job
    job.status = "cancelled"


def test_stop_process_emergency_abort():
    """Verify POST /api/monitor/stop-process aborts active jobs and purges VRAM."""
    res = client.post("/api/monitor/stop-process", json={"target": "emergency_stop"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "actions" in data


# -----------------------------------------------------------------------------
# 2. Content Deletion & Path Traversal Protection Tests
# -----------------------------------------------------------------------------

def test_output_file_deletion_and_security(tmp_path):
    """Verify safe output file deletion and strict rejection of path traversal."""
    # Create test deliverable inside fiverr_deliveries
    fiverr_dir = BASE_DIR / "workspace" / "fiverr_deliveries"
    fiverr_dir.mkdir(parents=True, exist_ok=True)
    test_file = fiverr_dir / "test_delete_artifact.zip"
    test_file.write_bytes(b"fake_zip_bytes")
    
    # 1. Path traversal attack test: try deleting outside category directory
    traversal_res = client.post("/api/outputs/delete", json={
        "category": "fiverr_deliveries",
        "path": "../../config.json"
    })
    assert traversal_res.status_code in (403, 404)
    # Ensure config.json was NOT deleted
    assert (BASE_DIR / "config.json").exists()
    
    # 2. Valid deletion
    del_res = client.post("/api/outputs/delete", json={
        "category": "fiverr_deliveries",
        "path": "test_delete_artifact.zip"
    })
    assert del_res.status_code == 200
    assert not test_file.exists()
    
    # 3. Repeat deletion on already deleted file should return 404
    missing_res = client.post("/api/outputs/delete", json={
        "category": "fiverr_deliveries",
        "path": "test_delete_artifact.zip"
    })
    assert missing_res.status_code == 404


def test_photo_package_deletion():
    """Verify DELETE /api/photos/packages/{package_name} safely removes package directory and zip."""
    photos_dir = BASE_DIR / "workspace" / "photos_output"
    photos_dir.mkdir(parents=True, exist_ok=True)
    
    pkg_name = "test_cleanup_session_99"
    pkg_folder = photos_dir / pkg_name
    pkg_folder.mkdir(parents=True, exist_ok=True)
    (pkg_folder / "master.jpg").write_bytes(b"jpg_bytes")
    
    pkg_zip = photos_dir / f"{pkg_name}_PHOTO_PACKAGE.zip"
    pkg_zip.write_bytes(b"zip_bytes")
    
    # Traversal test
    traversal_res = client.delete("/api/photos/packages/..invalid_package")
    assert traversal_res.status_code == 400

    
    # Valid package deletion
    del_res = client.delete(f"/api/photos/packages/{pkg_name}")
    assert del_res.status_code == 200
    assert not pkg_folder.exists()
    assert not pkg_zip.exists()


# -----------------------------------------------------------------------------
# 3. External Fulfillment (Etsy & Fiverr) Tests
# -----------------------------------------------------------------------------

def test_etsy_orders_listing_and_quick_fulfill():
    """Verify Etsy orders are listed and can be 1-click fulfilled."""
    # Simulate an incoming Etsy order
    sim_res = order_radar.simulate_order(platform="etsy")
    order = sim_res["order"]
    order_id = order["id"]
    assert order["platform"] == "etsy"
    assert order["status"] == "pending"
    
    # Fetch Etsy orders list
    res = client.get("/api/etsy/orders")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert any(o["id"] == order_id for o in data["orders"])
    
    # 1-Click fulfill Etsy order
    fulfill_res = client.post(f"/api/etsy/fulfill-order/{order_id}")
    assert fulfill_res.status_code == 200
    fulfill_data = fulfill_res.json()
    assert fulfill_data["status"] == "ok"
    assert "bundle" in fulfill_data
    
    # Verify order status updated to fulfilled in radar
    updated_order = next(o for o in order_radar.orders if o["id"] == order_id)
    assert updated_order["status"] == "fulfilled"


def test_fiverr_orders_listing_and_quick_fulfill():
    """Verify Fiverr orders are listed and can be 1-click fulfilled."""
    # Simulate an incoming Fiverr order
    sim_res = order_radar.simulate_order(platform="fiverr")
    order = sim_res["order"]
    order_id = order["id"]
    assert order["platform"] == "fiverr"
    assert order["status"] == "pending"
    
    # Fetch Fiverr orders list
    res = client.get("/api/fiverr/orders")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert any(o["id"] == order_id for o in data["orders"])
    
    # 1-Click fulfill Fiverr order
    fulfill_res = client.post(f"/api/fiverr/fulfill-order/{order_id}")
    assert fulfill_res.status_code == 200
    fulfill_data = fulfill_res.json()
    assert fulfill_data["status"] == "ok"
    assert "delivery" in fulfill_data
    
    # Verify order status updated to fulfilled in radar
    updated_order = next(o for o in order_radar.orders if o["id"] == order_id)
    assert updated_order["status"] == "fulfilled"
