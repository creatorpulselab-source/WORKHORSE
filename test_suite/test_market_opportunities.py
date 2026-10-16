import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from dashboard.server import app
from pipeline.stages.trend_researcher import TrendResearchAgent, OPPORTUNITIES_VAULT
from pipeline.stages.omni_marketer import OmniMarketer

from shared.auth import make_session_token
from dashboard.server import app, SESSION_COOKIE, _get_session_secret

client = TestClient(app)

@pytest.fixture(autouse=True)
def auth_client():
    token = make_session_token(_get_session_secret(), max_age_seconds=3600)
    client.cookies.set(SESSION_COOKIE, token)

def test_market_opportunities_endpoint():
    res = client.get("/api/market/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "vault" in data
    assert "opportunities" in data["vault"]
    assert len(data["vault"]["opportunities"]) >= 4
    
    # Check structure of the first opportunity
    opp = data["vault"]["opportunities"][0]
    assert "id" in opp
    assert "title" in opp
    assert "platform" in opp
    assert "potential_revenue" in opp
    assert "market_trend" in opp
    assert "workhorse_automation" in opp
    assert "action_steps" in opp

def test_deploy_market_opportunity():
    opp_payload = {
        "opportunity_id": "fiverr_dynamic_video_motion",
        "opportunity": {
            "id": "fiverr_dynamic_video_motion",
            "title": "4K 60fps AI Photo-to-Video & Dynamic Motion Teasers",
            "platform": "Fiverr",
            "potential_revenue": "$45 - $120 per client delivery",
            "market_trend": "High demand for vertical video",
            "workhorse_automation": "Synapse + Forge NVENC",
            "marketing_hook": "Transform flat photos into moving video reels in 24 hours.",
            "action_steps": ["Step 1", "Step 2", "Step 3"]
        }
    }
    res = client.post("/api/market/deploy-opportunity", json=opp_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "campaign" in data
    assert "content" in data["campaign"]
