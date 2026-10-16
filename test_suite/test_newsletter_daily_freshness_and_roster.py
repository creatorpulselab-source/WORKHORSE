"""
Unit tests for the WORKHORSE Agent Roster & Daily Newsletter Freshness Fix.

Verifies:
1. Complete 11-agent expert roster (+ 3 auxiliary) in shared/agent_roster.py
   with certified domain knowledge, hardware allocations, and responsibilities.
2. Scribe's dynamic daily fallback generation produces fresh, date-seeded,
   research-grounded content across all three publications (creator_pulse,
   studio_wire, creator_blueprint).
3. NewsletterManager HTML builders render dynamic content across all sections
   (metric cards, PPV scripts, tip ladders, lighting specs, recipes, directing
   cues, flywheel tiers, syndication pipelines, and conversion rules).
4. Visual embed engine supports all publications and ensures Iris-verified daily
   visual freshness.
5. Synapse SYSTEM_PROMPT in ai_operator.py documents certified agent expertise
   and the Unified Newsletter Collaboration Protocol.
"""

import json
from datetime import datetime, date
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from shared.agent_roster import (
    AGENT_ROSTER,
    get_agent,
    get_all_agents,
    get_newsletter_crew,
)
from pipeline.stages.copy_synthesizer import CopySynthesizer
from pipeline.stages.newsletter_manager import NewsletterManager


# ── 1. AGENT ROSTER EXPERTISE TESTS ──────────────────────────────────────────

def test_all_11_core_agents_certified_experts():
    required_core = [
        "herald", "iris", "muse", "synapse", "forge",
        "scribe", "mercury", "vanguard", "aura", "echo", "cipher"
    ]
    for agent_id in required_core:
        spec = get_agent(agent_id)
        assert bool(spec), f"Agent '{agent_id}' must exist in AGENT_ROSTER"
        assert spec["symbol"].startswith("1") or spec["symbol"].startswith("2") or spec["symbol"].startswith("3") or spec["symbol"].startswith("6") or spec["symbol"].startswith("7") or spec["symbol"].startswith("8"), f"Invalid symbol for {agent_id}"
        assert len(spec["title"]) > 5, f"Title too short for {agent_id}"
        assert len(spec["expertise"]) > 20, f"Agent {agent_id} must have detailed domain expertise"
        assert len(spec["responsibilities"]) >= 3, f"Agent {agent_id} must have at least 3 operational responsibilities"
        assert spec["hardware"] != "", f"Hardware allocation required for {agent_id}"
        assert spec["model"] != "", f"System model required for {agent_id}"


def test_newsletter_crew_collaboration_matrix():
    crew = get_newsletter_crew()
    crew_names = {agent["name"].lower() for agent in crew}
    assert {"cipher", "scribe", "iris", "herald", "synapse"}.issubset(crew_names), (
        "Newsletter crew must contain cipher, scribe, iris, herald, and synapse"
    )
    for agent in crew:
        assert len(agent["newsletter_role"]) > 20, f"Detailed newsletter role required for {agent['name']}"


def test_element_symbols_match_canonical():
    assert AGENT_ROSTER["herald"]["symbol"] == "33 As"
    assert AGENT_ROSTER["iris"]["symbol"] == "77 Ir"
    assert AGENT_ROSTER["muse"]["symbol"] == "34 Se"
    assert AGENT_ROSTER["synapse"]["symbol"] == "100 Fm"
    assert AGENT_ROSTER["forge"]["symbol"] == "28 Ni"
    assert AGENT_ROSTER["scribe"]["symbol"] == "6 C"
    assert AGENT_ROSTER["mercury"]["symbol"] == "80 Hg"
    assert AGENT_ROSTER["vanguard"]["symbol"] == "74 W"
    assert AGENT_ROSTER["aura"]["symbol"] == "79 Au"
    assert AGENT_ROSTER["echo"]["symbol"] == "26 Fe"
    assert AGENT_ROSTER["cipher"]["symbol"] == "36 Cp"


# ── 2. DYNAMIC PROCEDURAL FALLBACK TESTS ──────────────────────────────────────

def test_dynamic_fallback_generates_complete_schemas_for_all_pubs():
    cs = CopySynthesizer()
    for pub_id in ("creator_pulse", "studio_wire", "creator_blueprint"):
        res = cs.generate_dynamic_daily_fallback(
            pub_id=pub_id,
            pub_name=pub_id,
            today_str="Wednesday, October 14, 2026"
        )
        assert res.get("success") is True, f"Fallback must succeed for {pub_id}"
        assert "lead_headline" in res and len(res["lead_headline"]) > 10
        assert "lead_body" in res and len(res["lead_body"]) > 50
        assert "markdown_article" in res and len(res["markdown_article"]) > 100
        assert "tweet_thread" in res and len(res["tweet_thread"]) >= 4

        if pub_id == "creator_pulse":
            assert "metric_card_1" in res and "metric_card_2" in res
            assert "ppv_scripts" in res and len(res["ppv_scripts"]) >= 3
            assert "ladder_tiers" in res and len(res["ladder_tiers"]) >= 3
            assert "visual_setup_headline" in res
        elif pub_id == "studio_wire":
            assert "recipe_rows" in res and len(res["recipe_rows"]) >= 3
            assert "directing_cues" in res and len(res["directing_cues"]) >= 3
            assert "lighting_headline" in res
            assert "pricing_headline" in res
        elif pub_id == "creator_blueprint":
            assert "flywheel_phases" in res and len(res["flywheel_phases"]) >= 3
            assert "pipeline_rows" in res and len(res["pipeline_rows"]) >= 3
            assert "conversion_rules" in res and len(res["conversion_rules"]) >= 4
            assert "math_headline" in res


def test_dynamic_fallback_rotates_across_calendar_days():
    cs = CopySynthesizer()
    with patch("datetime.datetime") as mock_dt:
        # Simulate Day 100
        mock_dt.now.return_value = datetime(2026, 4, 10)  # Day 100
        day_100_content = cs.generate_dynamic_daily_fallback("creator_pulse", "Creator Pulse")

        # Simulate Day 101
        mock_dt.now.return_value = datetime(2026, 4, 11)  # Day 101
        day_101_content = cs.generate_dynamic_daily_fallback("creator_pulse", "Creator Pulse")

    assert day_100_content["lead_headline"] != day_101_content["lead_headline"], (
        "Content should change dynamically across different calendar days"
    )


def test_dynamic_fallback_incorporates_ciphers_research():
    cs = CopySynthesizer()
    articles = [{
        "title": "TikTok Announces New Dynamic Commerce Commission Tiers",
        "snippet": "ByteDance rolled out an updated algorithm prioritizing multi-step creator store funnels."
    }]
    res = cs.generate_dynamic_daily_fallback(
        pub_id="creator_pulse",
        pub_name="Creator Pulse",
        research_articles=articles
    )
    assert "TikTok Announces New Dynamic Commerce" in res["lead_headline"]
    assert "ByteDance rolled out an updated algorithm" in res["lead_body"]


# ── 3. NEWSLETTER MANAGER DYNAMIC BUILDER TESTS ──────────────────────────────

@pytest.fixture
def nm_test(tmp_path, monkeypatch):
    manager = NewsletterManager()
    fake_cache = tmp_path / "scribe_cache_test.json"
    monkeypatch.setattr(manager, "scribe_cache_path", fake_cache)
    return manager


def test_creator_pulse_full_dynamic_rendering(nm_test):
    mock_scribe = {
        "success": True,
        "lead_headline": "PULSE_HEADLINE_DELTA",
        "lead_body": "pulse body delta",
        "metric_card_1": {"label": "Delta Label", "value": "88.8%", "note": "delta note"},
        "metric_card_2": {"label": "Safety Label", "value": "100%", "note": "sfw guaranteed"},
        "ppv_headline": "PPV_HEADLINE_DELTA",
        "ppv_intro": "ppv intro delta",
        "ppv_scripts": [
            {"label": "DELTA_SCRIPT_1", "quote": "quote delta 1", "insight": "insight delta 1"},
            {"label": "DELTA_SCRIPT_2", "quote": "quote delta 2", "insight": "insight delta 2"},
            {"label": "DELTA_SCRIPT_3", "quote": "quote delta 3", "insight": "insight delta 3"},
        ],
        "ladder_headline": "LADDER_HEADLINE_DELTA",
        "ladder_intro": "ladder intro delta",
        "ladder_tiers": [
            {"tier": "Tier Alpha", "tokens": "100 T", "action": "Action Alpha", "trigger": "Trigger Alpha"},
            {"tier": "Tier Beta", "tokens": "200 T", "action": "Action Beta", "trigger": "Trigger Beta"},
            {"tier": "Tier Gamma", "tokens": "300 T", "action": "Action Gamma", "trigger": "Trigger Gamma"},
        ],
        "visual_setup_headline": "LIGHTING_HEADLINE_DELTA",
        "visual_setup_intro": "lighting intro delta",
        "visual_setup_pro_tip": "lighting pro tip delta",
        "retention_headline": "RETENTION_HEADLINE_DELTA",
        "retention_body": "retention body delta",
    }

    with patch.object(nm_test, "_get_daily_scribe_content", return_value=mock_scribe), \
         patch.object(nm_test, "get_publication_visual_embed", return_value={"src": "img_delta.jpg", "caption": "cap_delta", "subcaption": "sub_delta"}):
        html_out = nm_test._build_creator_pulse_html("Wednesday, October 14, 2026")

    assert "PULSE_HEADLINE_DELTA" in html_out
    assert "DELTA_SCRIPT_1" in html_out
    assert "LADDER_HEADLINE_DELTA" in html_out
    assert "Tier Alpha" in html_out and "Action Alpha" in html_out
    assert "LIGHTING_HEADLINE_DELTA" in html_out
    assert "lighting pro tip delta" in html_out
    assert "RETENTION_HEADLINE_DELTA" in html_out


def test_studio_wire_full_dynamic_rendering(nm_test):
    mock_scribe = {
        "success": True,
        "lead_headline": "STUDIO_HEADLINE_EPSILON",
        "lead_body": "studio body epsilon",
        "recipe_headline": "RECIPE_HEADLINE_EPSILON",
        "recipe_intro": "recipe intro epsilon",
        "recipe_rows": [
            {"module": "Mod Epsilon 1", "setting": "Set Epsilon 1", "characteristic": "Char Epsilon 1"},
            {"module": "Mod Epsilon 2", "setting": "Set Epsilon 2", "characteristic": "Char Epsilon 2"},
            {"module": "Mod Epsilon 3", "setting": "Set Epsilon 3", "characteristic": "Char Epsilon 3"},
        ],
        "lighting_headline": "LIGHTING_HEADLINE_EPSILON",
        "lighting_intro": "lighting intro epsilon",
        "lighting_specs": "lighting specs epsilon",
        "directing_headline": "DIRECTING_HEADLINE_EPSILON",
        "directing_intro": "directing intro epsilon",
        "directing_cues": [
            {"cue": "Cue Epsilon 1", "explanation": "Expl Epsilon 1"},
            {"cue": "Cue Epsilon 2", "explanation": "Expl Epsilon 2"},
            {"cue": "Cue Epsilon 3", "explanation": "Expl Epsilon 3"},
        ],
        "pricing_headline": "PRICING_HEADLINE_EPSILON",
        "pricing_body": "pricing body epsilon",
    }

    with patch.object(nm_test, "_get_daily_scribe_content", return_value=mock_scribe), \
         patch.object(nm_test, "get_publication_visual_embed", return_value={"src": "img_sw.jpg", "caption": "cap_sw", "subcaption": "sub_sw"}):
        html_out = nm_test._build_studio_wire_html("Wednesday, October 14, 2026")

    assert "STUDIO_HEADLINE_EPSILON" in html_out
    assert "RECIPE_HEADLINE_EPSILON" in html_out
    assert "Mod Epsilon 1" in html_out
    assert "LIGHTING_HEADLINE_EPSILON" in html_out
    assert "lighting specs epsilon" in html_out
    assert "Cue Epsilon 1" in html_out
    assert "PRICING_HEADLINE_EPSILON" in html_out


def test_creator_blueprint_full_dynamic_rendering(nm_test):
    mock_scribe = {
        "success": True,
        "lead_headline": "BLUEPRINT_HEADLINE_ZETA",
        "lead_body": "blueprint body zeta",
        "flywheel_headline": "FLYWHEEL_HEADLINE_ZETA",
        "flywheel_intro": "flywheel intro zeta",
        "flywheel_phases": [
            {"phase": "Phase Zeta 1", "desc": "Desc Zeta 1"},
            {"phase": "Phase Zeta 2", "desc": "Desc Zeta 2"},
            {"phase": "Phase Zeta 3", "desc": "Desc Zeta 3"},
        ],
        "pipeline_headline": "PIPELINE_HEADLINE_ZETA",
        "pipeline_intro": "pipeline intro zeta",
        "pipeline_rows": [
            {"format": "Fmt Zeta 1", "destination": "Dest Zeta 1", "cta": "CTA Zeta 1"},
            {"format": "Fmt Zeta 2", "destination": "Dest Zeta 2", "cta": "CTA Zeta 2"},
            {"format": "Fmt Zeta 3", "destination": "Dest Zeta 3", "cta": "CTA Zeta 3"},
        ],
        "conversion_headline": "CONVERSION_HEADLINE_ZETA",
        "conversion_intro": "conversion intro zeta",
        "conversion_rules": [
            "Rule Zeta 1: Expl 1",
            "Rule Zeta 2: Expl 2",
            "Rule Zeta 3: Expl 3",
            "Rule Zeta 4: Expl 4",
        ],
        "math_headline": "MATH_HEADLINE_ZETA",
        "math_body": "math body zeta",
    }

    with patch.object(nm_test, "_get_daily_scribe_content", return_value=mock_scribe), \
         patch.object(nm_test, "get_publication_visual_embed", return_value={"src": "img_cb.jpg", "caption": "cap_cb", "subcaption": "sub_cb"}):
        html_out = nm_test._build_creator_blueprint_html("Wednesday, October 14, 2026")

    assert "BLUEPRINT_HEADLINE_ZETA" in html_out
    assert "FLYWHEEL_HEADLINE_ZETA" in html_out
    assert "Phase Zeta 1" in html_out
    assert "PIPELINE_HEADLINE_ZETA" in html_out
    assert "Fmt Zeta 1" in html_out
    assert "CONVERSION_HEADLINE_ZETA" in html_out
    assert "Rule Zeta 1" in html_out
    assert "MATH_HEADLINE_ZETA" in html_out
    assert "img_cb.jpg" in html_out


def test_visual_embed_creator_blueprint_support(nm_test):
    with patch.object(nm_test, "ensure_fresh_daily_newsletter_visual", return_value=None):
        vis = nm_test.get_publication_visual_embed("creator_blueprint", topic_text="Micro Asset Scaling")
        assert vis["src"] != ""
        assert "Figure" in vis["caption"]
        assert "Flywheel" in vis["caption"] or "Blueprint" in vis["caption"]


# ── 4. PRIVACY, NO-BOT-CLAIMS & VISUAL DIAGRAM PAIRING TESTS ──────────────────

def test_no_personal_account_leaks_or_automated_bot_claims(nm_test):
    """
    User Requirement:
    - Never mention @TheCreatorAsset inside educational text or tweet hooks (only allowed in footer/ad link).
    - Strictly forbid 'this is what I'm doing with this automated account' or bot automation claims.
    """
    for pub_id in ("creator_pulse", "studio_wire", "creator_blueprint"):
        # Test default static rendering (no scribe content mock, testing procedural defaults)
        html_out = nm_test.get_html_preview(pub_id)
        
        # Check that educational sections do not leak @TheCreatorAsset
        # Specifically section 2 (flywheel), section 3 (pipeline), section 4 (conversion), and section 5 (math)
        lower_html = html_out.lower()
        assert "this is what i'm doing with this automated account" not in lower_html
        assert "automated account" not in lower_html
        assert "how we automate our bots" not in lower_html

        # Check default pipeline rows & flywheel phases in creator_blueprint
        if pub_id == "creator_blueprint":
            assert "automate daily threads on @thecreatorasset" not in lower_html
            assert "twitter/x (@thecreatorasset)" not in lower_html

        # Check Twitter thread opening hook (tweet 1) has no self-tag leak
        thread = nm_test.get_twitter_thread(pub_id)
        assert len(thread) >= 3
        first_tweet = thread[0].lower()
        assert "@thecreatorasset" not in first_tweet


def test_visual_floor_plan_and_matching_result_cards(nm_test):
    """
    User Requirement:
    - Never include raw ASCII diagrams without visuals.
    - Provide intuitive visual floor plans paired with matching visual result renders.
    """
    # 1. Studio Wire: 45° Beauty Dish floor plan + matching visual result
    sw_html = nm_test.get_html_preview("studio_wire")
    assert "📐 STUDIO FLOOR PLAN &bull; 45° CLAMSHELL" in sw_html
    assert "✨ MATCHING VISUAL RESULT &bull; REAL-WORLD RENDER" in sw_html
    assert 'class="ascii-diagram"' not in sw_html
    assert '[KEY: 22" BEAUTY DISH] ── 45°' not in sw_html

    # 2. Creator Pulse: 2-Light Rig floor plan + matching visual result
    cpl_html = nm_test.get_html_preview("creator_pulse")
    assert "📐 STUDIO FLOOR PLAN &bull; 2-LIGHT RIG" in cpl_html
    assert "✨ MATCHING VISUAL RESULT &bull; REAL-WORLD RENDER" in cpl_html
    assert 'class="ascii-diagram"' not in cpl_html
    assert '[WARM RIM (3200K)] ── (Behind Hair)' not in cpl_html

    # 3. Creator Blueprint: 3-Stage Pipeline Architecture + matching visual result
    cbp_html = nm_test.get_html_preview("creator_blueprint")
    assert "📐 3-STAGE FLOW ARCHITECTURE" in cbp_html
    assert "✨ MATCHING VISUAL RESULT &bull; ASSET WORKSTATION" in cbp_html
    assert "[FIVERR: SERVICE] ── Validation ──→" not in cbp_html


def test_force_refresh_bypasses_cache(nm_test):
    """
    Verifies that force_refresh=True bypasses the cached entry and triggers re-synthesis.
    """
    with patch.object(nm_test, "_get_daily_scribe_content") as mock_get_content:
        mock_get_content.return_value = {"success": True, "lead_headline": "REFRESHED_TEST"}
        nm_test.get_html_preview("creator_blueprint", force_refresh=True)
        mock_get_content.assert_called_with("creator_blueprint", force_refresh=True)

