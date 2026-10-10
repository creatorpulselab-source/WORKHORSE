"""Unit tests for Herald's Twitter/Pinterest dispatch self-healing fix (2026-10-09
audit): dispatch_slot() and dispatch_pinterest_daily() previously marked a slot/pin
"done for the day" even when the actual post failed, with zero incident logging or
Commander alert - the same silent-failure bug class fixed for newsletters on
2026-10-07, applied here. These tests verify:
  1. A failed post keeps the slot/pin retryable (not marked done).
  2. A successful post DOES mark it done.
  3. The watchdog retries up to MAX_DISPATCH_RETRIES, then logs an incident and
     alerts the Commander exactly once (not every tick after exhausting retries).
  4. Pinterest's watchdog is a true no-op when disabled/unconfigured (not a failure).

Uses a throwaway state file (monkeypatched STATE_FILE) so these tests never touch
the real production daily_schedule_state.json that the live dashboard server uses.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.stages.herald_scheduler import HeraldScheduler, MAX_DISPATCH_RETRIES, DAILY_SLOTS


@pytest.fixture
def scheduler(tmp_path, monkeypatch):
    state_file = tmp_path / "daily_schedule_state.json"
    monkeypatch.setattr("pipeline.stages.herald_scheduler.STATE_FILE", state_file)

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "marketing_channels": {
            "main_brand": {
                "pinterest": {"enabled": True, "default_board_id": "board123", "daily_slot_time": "00:00"}
            }
        }
    }))

    sched = HeraldScheduler(config_path=str(config_file))
    # Avoid real brand-visual lookups (ComfyUI/filesystem) in these dispatch-logic tests
    monkeypatch.setattr(sched, "_get_brand_visual_for_post", lambda handle: None)
    return sched


def _first_slot_id():
    return DAILY_SLOTS[0]["slot_id"]


# --- dispatch_slot() only marks "done" on real success ---

def test_dispatch_slot_marks_executed_when_all_accounts_succeed(scheduler):
    slot_id = _first_slot_id()
    with patch.object(scheduler.twitter, "post_thread", return_value={"success": True}):
        res = scheduler.dispatch_slot(slot_id)
    assert res["fully_succeeded"] is True
    assert slot_id in scheduler.state["executed_slots"]


def test_dispatch_slot_does_not_mark_executed_when_a_post_fails(scheduler):
    slot_id = _first_slot_id()
    with patch.object(scheduler.twitter, "post_thread", return_value={"success": False, "error": "401 Unauthorized - token expired"}):
        res = scheduler.dispatch_slot(slot_id)
    assert res["fully_succeeded"] is False
    assert slot_id not in scheduler.state["executed_slots"]


def test_dispatch_slot_does_not_mark_executed_on_exception(scheduler):
    slot_id = _first_slot_id()
    with patch.object(scheduler.twitter, "post_thread", side_effect=RuntimeError("network error")):
        res = scheduler.dispatch_slot(slot_id)
    assert res["fully_succeeded"] is False
    assert slot_id not in scheduler.state["executed_slots"]


# --- Twitter watchdog: retry then alert exactly once ---

def test_twitter_watchdog_retries_up_to_max_then_alerts_once(scheduler, monkeypatch):
    """Freezes the clock to just after slot_1's target time (and before slot_2's) so
    exactly one slot is due, regardless of what time of day this test actually runs -
    without this, every slot whose target_time has already passed "today" (which, late
    in the day, can be all 5 of them) would independently retry/alert, making the
    "alerted exactly once" assertion below flaky depending on wall-clock time."""
    slot_id = _first_slot_id()
    scheduler.state["last_date"] = __import__("datetime").date.today().isoformat()  # skip rollover reset mid-test

    fixed_now = __import__("datetime").datetime.combine(__import__("datetime").date.today(), __import__("datetime").time(9, 30))

    class _FrozenDateTime(__import__("datetime").datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr("pipeline.stages.herald_scheduler.datetime", _FrozenDateTime)

    with patch.object(scheduler.twitter, "post_thread", return_value={"success": False, "error": "boom"}), \
         patch("pipeline.stages.ai_operator.ai_operator.log_incident") as mock_log, \
         patch("pipeline.stages.ai_operator.ai_operator.notify_commander") as mock_notify:

        for _ in range(MAX_DISPATCH_RETRIES + 2):  # run well past the retry cap
            scheduler._monitor_and_remediate_twitter_slots()

        assert mock_log.call_count == 1  # alerted exactly once, not every tick after exhausting retries
        assert mock_notify.call_count == 1
    assert scheduler.state[f"{slot_id}_attempts"] == MAX_DISPATCH_RETRIES
    assert scheduler.state[f"{slot_id}_alerted_today"] is True
    assert slot_id not in scheduler.state["executed_slots"]


def test_twitter_watchdog_stops_retrying_once_slot_succeeds(scheduler):
    slot_id = _first_slot_id()
    with patch.object(scheduler.twitter, "post_thread", return_value={"success": True}):
        scheduler._monitor_and_remediate_twitter_slots()
    assert slot_id in scheduler.state["executed_slots"]

    # A second pass must NOT attempt to dispatch again (it's already done for today)
    with patch.object(scheduler.twitter, "post_thread") as mock_post:
        scheduler._monitor_and_remediate_twitter_slots()
        mock_post.assert_not_called()


# --- dispatch_pinterest_daily() only marks "done" on real success ---

def test_dispatch_pinterest_daily_marks_posted_on_success(scheduler, monkeypatch):
    monkeypatch.setattr(scheduler, "_get_brand_visual_for_post", lambda handle: "F:/fake/visual.jpg")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    with patch.object(scheduler.pinterest, "create_pin", return_value={"success": True, "pin_url": "https://pinterest.com/pin/123"}):
        res = scheduler.dispatch_pinterest_daily()
    assert res["status"] == "ok"
    assert scheduler.state["pinterest_posted_today"] is True


def test_dispatch_pinterest_daily_does_not_mark_posted_on_failure(scheduler, monkeypatch):
    monkeypatch.setattr(scheduler, "_get_brand_visual_for_post", lambda handle: "F:/fake/visual.jpg")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    with patch.object(scheduler.pinterest, "create_pin", return_value={"success": False, "error": "401 Unauthorized"}):
        res = scheduler.dispatch_pinterest_daily()
    assert res["status"] == "error"
    assert scheduler.state.get("pinterest_posted_today") is not True


# --- Pinterest watchdog: skip when disabled, retry+alert otherwise ---

def test_pinterest_watchdog_is_noop_when_disabled(scheduler):
    disabled_config = Path(scheduler.config_path)
    disabled_config.write_text(json.dumps({
        "marketing_channels": {"main_brand": {"pinterest": {"enabled": False}}}
    }))
    with patch.object(scheduler, "dispatch_pinterest_daily") as mock_dispatch:
        scheduler._monitor_and_remediate_pinterest()
        mock_dispatch.assert_not_called()
    assert scheduler.state.get("pinterest_alerted_today") is not True


def test_pinterest_watchdog_retries_up_to_max_then_alerts_once(scheduler, monkeypatch):
    monkeypatch.setattr(scheduler, "_get_brand_visual_for_post", lambda handle: "F:/fake/visual.jpg")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

    with patch.object(scheduler.pinterest, "create_pin", return_value={"success": False, "error": "boom"}), \
         patch("pipeline.stages.ai_operator.ai_operator.log_incident") as mock_log, \
         patch("pipeline.stages.ai_operator.ai_operator.notify_commander") as mock_notify:

        for _ in range(MAX_DISPATCH_RETRIES + 2):
            scheduler._monitor_and_remediate_pinterest()

        assert mock_log.call_count == 1
        assert mock_notify.call_count == 1
    assert scheduler.state["pinterest_attempts"] == MAX_DISPATCH_RETRIES
    assert scheduler.state["pinterest_alerted_today"] is True
