"""Unit tests for the 2026-10-09 newsletter content-freshness fix.

Root cause found: across all 4 daily newsletters, only the top lead headline/body
was ever dynamic - every other section (3-5 per publication, with specific PPV
scripts, data tables, tip lists, etc.) was 100% hardcoded boilerplate that repeated
verbatim every single day forever, and the "ISSUE #NNN" badge never incremented.
These tests verify:
  1. Issue numbers are real, persistent, and increment once per calendar day.
  2. Each rewritten builder (creator_pulse, studio_wire, creator_blueprint) renders
     DIFFERENT content when given different mock Scribe section content - proving
     the dynamism actually flows through to the HTML, not just accepted silently.
  3. Each builder still works and falls back gracefully to the original static
     copy when Scribe content is empty/missing fields (never crashes).
  4. trend_researcher's new per-publication research mapping and date-staleness
     guard.
  5. copy_synthesizer's per-publication section schema is present and well-formed.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.stages.newsletter_manager import NewsletterManager
from pipeline.stages.copy_synthesizer import CopySynthesizer


@pytest.fixture
def nm(tmp_path, monkeypatch):
    manager = NewsletterManager()
    # Isolate the Scribe cache (issue counters + daily content cache) to a
    # throwaway file so these tests never touch the real production cache the
    # live dashboard server uses.
    fake_cache = tmp_path / "scribe_daily_content.json"
    monkeypatch.setattr(manager, "scribe_cache_path", fake_cache)
    return manager


# --- Issue number counter ---

def test_issue_number_starts_at_configured_value(nm):
    assert nm._get_daily_issue_number("creator_pulse", start_at=42) == 42


def test_issue_number_stable_within_same_day(nm):
    first = nm._get_daily_issue_number("studio_wire", start_at=88)
    second = nm._get_daily_issue_number("studio_wire", start_at=88)
    assert first == second == 88


def test_issue_number_increments_on_new_day(nm):
    nm._get_daily_issue_number("creator_blueprint", start_at=19)
    cache = json.loads(nm.scribe_cache_path.read_text(encoding="utf-8"))
    # Simulate yesterday's entry
    cache["issue_counters"]["creator_blueprint"]["date"] = "2000-01-01"
    nm.scribe_cache_path.write_text(json.dumps(cache), encoding="utf-8")

    new_number = nm._get_daily_issue_number("creator_blueprint", start_at=19)
    assert new_number == 20


def test_issue_numbers_are_independent_per_publication(nm):
    assert nm._get_daily_issue_number("creator_pulse", start_at=42) == 42
    assert nm._get_daily_issue_number("studio_wire", start_at=88) == 88
    assert nm._get_daily_issue_number("creator_blueprint", start_at=19) == 19


# --- Builders render actually-different content, not just accept it silently ---

def test_creator_pulse_renders_dynamic_ppv_scripts(nm):
    mock_content = {
        "success": True,
        "lead_headline": "UNIQUE_TEST_HEADLINE_12345",
        "lead_body": "unique test body",
        "metric_card_1": {"label": "Test Metric One", "value": "99.9%", "note": "test note one"},
        "metric_card_2": {"label": "Test Metric Two", "value": "1.2%", "note": "test note two"},
        "ppv_headline": "UNIQUE_PPV_HEADLINE",
        "ppv_intro": "unique ppv intro",
        "ppv_scripts": [
            {"label": "UNIQUE_SCRIPT_ONE", "quote": "unique quote one", "insight": "unique insight one"},
            {"label": "UNIQUE_SCRIPT_TWO", "quote": "unique quote two", "insight": "unique insight two"},
            {"label": "UNIQUE_SCRIPT_THREE", "quote": "unique quote three", "insight": "unique insight three"},
        ],
        "ladder_headline": "UNIQUE_LADDER_HEADLINE",
        "ladder_intro": "unique ladder intro",
        "retention_headline": "UNIQUE_RETENTION_HEADLINE",
        "retention_body": "unique retention body",
    }
    with patch.object(nm, "_get_daily_scribe_content", return_value=mock_content), \
         patch.object(nm, "get_publication_visual_embed", return_value={"src": "x", "caption": "c", "subcaption": "s"}):
        out = nm._build_creator_pulse_html("Thursday, October 9, 2026")

    assert "UNIQUE_TEST_HEADLINE_12345" in out
    assert "UNIQUE_SCRIPT_ONE" in out and "UNIQUE_SCRIPT_TWO" in out and "UNIQUE_SCRIPT_THREE" in out
    assert "UNIQUE_LADDER_HEADLINE" in out
    assert "UNIQUE_RETENTION_HEADLINE" in out
    assert "Test Metric One" in out and "99.9%" in out
    # The old hardcoded placeholder text must be GONE, not just supplemented
    assert "Midnight Audio" not in out
    assert "Why Tight Face-Framing Crops" not in out


def test_creator_pulse_falls_back_gracefully_when_scribe_unavailable(nm):
    with patch.object(nm, "_get_daily_scribe_content", return_value=None), \
         patch.object(nm, "get_publication_visual_embed", return_value={"src": "x", "caption": "c", "subcaption": "s"}):
        out = nm._build_creator_pulse_html("Thursday, October 9, 2026")
    # Original static fallback copy still present - never crashes, never blank
    assert "Why Tight Face-Framing Crops" in out
    assert "Midnight Audio" in out


def test_studio_wire_renders_dynamic_recipe_rows(nm):
    mock_content = {
        "success": True,
        "lead_headline": "UNIQUE_SW_HEADLINE",
        "lead_body": "unique sw body",
        "recipe_headline": "UNIQUE_RECIPE_HEADLINE",
        "recipe_intro": "unique recipe intro",
        "recipe_rows": [
            {"module": "UNIQUE_MODULE_ONE", "setting": "UNIQUE_SETTING_ONE", "characteristic": "UNIQUE_CHAR_ONE"},
            {"module": "UNIQUE_MODULE_TWO", "setting": "UNIQUE_SETTING_TWO", "characteristic": "UNIQUE_CHAR_TWO"},
            {"module": "UNIQUE_MODULE_THREE", "setting": "UNIQUE_SETTING_THREE", "characteristic": "UNIQUE_CHAR_THREE"},
        ],
        "directing_headline": "UNIQUE_DIRECTING_HEADLINE",
        "directing_intro": "unique directing intro",
        "directing_cues": [
            {"cue": "UNIQUE_CUE_ONE", "explanation": "unique explanation one"},
            {"cue": "UNIQUE_CUE_TWO", "explanation": "unique explanation two"},
            {"cue": "UNIQUE_CUE_THREE", "explanation": "unique explanation three"},
        ],
        "pricing_headline": "UNIQUE_PRICING_HEADLINE",
        "pricing_body": "unique pricing body",
    }
    with patch.object(nm, "_get_daily_scribe_content", return_value=mock_content), \
         patch.object(nm, "get_publication_visual_embed", return_value={"src": "x", "caption": "c", "subcaption": "s"}):
        out = nm._build_studio_wire_html("Thursday, October 9, 2026")

    assert "UNIQUE_MODULE_ONE" in out and "UNIQUE_MODULE_TWO" in out and "UNIQUE_MODULE_THREE" in out
    assert "UNIQUE_CUE_ONE" in out
    assert "UNIQUE_PRICING_HEADLINE" in out
    assert "RGB Tone Curve" not in out  # old hardcoded recipe row gone


def test_studio_wire_falls_back_gracefully(nm):
    with patch.object(nm, "_get_daily_scribe_content", return_value=None), \
         patch.object(nm, "get_publication_visual_embed", return_value={"src": "x", "caption": "c", "subcaption": "s"}):
        out = nm._build_studio_wire_html("Thursday, October 9, 2026")
    assert "RGB Tone Curve" in out


def test_creator_blueprint_renders_dynamic_sections(nm):
    mock_content = {
        "success": True,
        "lead_headline": "UNIQUE_CB_HEADLINE",
        "lead_body": "unique cb body",
        "pipeline_headline": "UNIQUE_PIPELINE_HEADLINE",
        "pipeline_intro": "unique pipeline intro",
        "math_headline": "UNIQUE_MATH_HEADLINE",
        "math_body": "unique math body",
    }
    with patch.object(nm, "_get_daily_scribe_content", return_value=mock_content):
        out = nm._build_creator_blueprint_html("Thursday, October 9, 2026")

    assert "UNIQUE_PIPELINE_HEADLINE" in out
    assert "UNIQUE_MATH_HEADLINE" in out
    assert "UNIQUE_MATH_HEADLINE" in out
    assert "You Only Need 200 Targeted Clicks" not in out


def test_creator_blueprint_falls_back_gracefully(nm):
    with patch.object(nm, "_get_daily_scribe_content", return_value=None):
        out = nm._build_creator_blueprint_html("Thursday, October 9, 2026")
    assert "You Only Need 200 Targeted Clicks" in out


# --- trend_researcher research grounding ---

def test_get_research_articles_for_pub_maps_correctly(tmp_path, monkeypatch):
    from pipeline.stages import trend_researcher as tr_module
    fake_vault = tmp_path / "vault.json"
    monkeypatch.setattr(tr_module, "VAULT_FILE", fake_vault)
    agent = tr_module.TrendResearchAgent()
    monkeypatch.setattr(agent, "vault_file", fake_vault)

    from datetime import date
    agent.save_vault({
        "today_date": date.today().isoformat(),
        "photo_articles": [{"title": "photo news"}],
        "creator_articles": [{"title": "creator news"}],
        "business_articles": [{"title": "business news"}]
    })

    assert agent.get_research_articles_for_pub("studio_wire") == [{"title": "photo news"}]
    assert agent.get_research_articles_for_pub("creator_pulse") == [{"title": "creator news"}]
    assert agent.get_research_articles_for_pub("creator_blueprint") == [{"title": "business news"}]
    assert agent.get_research_articles_for_pub("dispensary_deals") == []


def test_get_research_articles_for_pub_empty_when_vault_stale(tmp_path, monkeypatch):
    from pipeline.stages import trend_researcher as tr_module
    fake_vault = tmp_path / "vault.json"
    monkeypatch.setattr(tr_module, "VAULT_FILE", fake_vault)
    agent = tr_module.TrendResearchAgent()
    monkeypatch.setattr(agent, "vault_file", fake_vault)

    agent.save_vault({"today_date": "2000-01-01", "photo_articles": [{"title": "stale"}]})
    assert agent.get_research_articles_for_pub("studio_wire") == []


# --- copy_synthesizer schema shape ---

def test_section_schemas_cover_all_three_grounded_publications():
    cs = CopySynthesizer()
    assert set(cs.SECTION_SCHEMAS.keys()) == {"creator_pulse", "studio_wire", "creator_blueprint"}
    for pub_id, schema in cs.SECTION_SCHEMAS.items():
        # Each schema block is valid-ish JSON fragment material: balanced braces/brackets
        assert schema.count("{") == schema.count("}"), pub_id
        assert schema.count("[") == schema.count("]"), pub_id
        assert schema.rstrip().endswith(","), f"{pub_id} schema must end with a trailing comma"
