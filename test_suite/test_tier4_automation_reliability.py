"""
Unit & Regression Tests for TIER 4: Automation Reliability (Herald, Twitter, Pinterest, Newsletter).
Verifies:
  1. Herald Social Media Strategy & Exposure Optimizer (hashtag insertion, 280-char enforcement, brand routing).
  2. Answer-backed copy (elimination of cliffhangers and unanswered questions).
  3. Full-day catch-up dispatch across all daily slots in dispatch_today_all_now().
  4. TwitterPoster 7-day SHA-256 duplicate prevention gate and test isolation.
  5. TwitterPoster case-insensitive handle matching and success-only hash recording.
  6. PinterestPoster mandatory TOS safety gate (hard-blocks adult terms/paths, allows general).
  7. PinterestPoster 7-day duplicate prevention.
  8. NewsletterManager independent issue counters and unsubscribe lifecycle.
"""
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pipeline.stages.herald_scheduler import HeraldScheduler, DAILY_SLOTS, BRAND_HASHTAGS
from pipeline.stages.twitter_poster import TwitterPoster
from pipeline.stages.pinterest_poster import PinterestPoster
from pipeline.stages.newsletter_manager import NewsletterManager


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def tmp_env(tmp_path):
    """Provides isolated paths for config, secrets, and history files."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "marketing_channels": {
            "main_brand": {
                "pinterest": {
                    "enabled": True,
                    "default_board_id": "board_123",
                    "daily_slot_time": "12:00"
                }
            }
        }
    }), encoding="utf-8")

    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({
        "twitter_credentials": {
            "thecreatorasset": {
                "api_key": "k1", "api_secret": "s1",
                "access_token": "t1", "access_token_secret": "ts1"
            },
            "creatorpulselab": {
                "api_key": "k2", "api_secret": "s2",
                "access_token": "t2", "access_token_secret": "ts2"
            }
        },
        "pinterest_credentials": {
            "app_id": "app_id_123",
            "app_secret": "app_sec_123",
            "access_token": "pin_token_123",
            "token_expires_at": time.time() + 3600
        }
    }), encoding="utf-8")

    state_file = tmp_path / "daily_schedule_state.json"
    tweet_history_file = tmp_path / "tweet_history.json"
    pin_history_file = tmp_path / "pinterest_pin_history.json"

    return {
        "config": str(config_file),
        "secrets": str(secrets_file),
        "state_file": state_file,
        "tweet_history": str(tweet_history_file),
        "pin_history": str(pin_history_file)
    }


# ==============================================================================
# 1. HERALD HASHTAG & SOCIAL STRATEGY TESTS
# ==============================================================================

def test_herald_optimizes_thread_with_hashtags(tmp_env):
    sched = HeraldScheduler(config_path=tmp_env["config"], state_file=tmp_env["state_file"])

    # Tweet with no hashtags
    raw_tweets = [
        "1/2 Stop using generic studio lighting.",
        "2/2 Use a 45-degree feathered key light for soft shadows."
    ]

    optimized = sched._optimize_thread_for_exposure("TheCreatorAsset", raw_tweets)
    closing = optimized[-1]

    assert "#" in closing
    assert any(tag in closing for tag in BRAND_HASHTAGS["TheCreatorAsset"])
    assert len(closing) <= 280


def test_herald_does_not_double_add_existing_hashtags(tmp_env):
    sched = HeraldScheduler(config_path=tmp_env["config"], state_file=tmp_env["state_file"])

    raw_tweets = [
        "1/1 Master Portra 400 color science in Lightroom. #StudioPhotography #Portra400"
    ]

    optimized = sched._optimize_thread_for_exposure("TheCreatorAsset", raw_tweets)
    assert optimized[0] == raw_tweets[0]


def test_herald_routes_hashtags_by_brand(tmp_env):
    sched = HeraldScheduler(config_path=tmp_env["config"], state_file=tmp_env["state_file"])

    pulse_tweets = ["Tip menus with fewer than 8 items convert 32% faster."]
    opt_pulse = sched._optimize_thread_for_exposure("creatorpulselab", pulse_tweets)
    assert any(tag in opt_pulse[0] for tag in ["#CreatorEconomy", "#OnlyFansTips", "#PPVStrategy", "#CamModelTips"])

    asset_tweets = ["Soft light is created by apparent light size, not wattage."]
    opt_asset = sched._optimize_thread_for_exposure("TheCreatorAsset", asset_tweets)
    assert any(tag in opt_asset[0] for tag in ["#StudioPhotography", "#LightroomPresets", "#ColorGrading"])


def test_herald_enforces_280_character_limit_when_adding_hashtags(tmp_env):
    sched = HeraldScheduler(config_path=tmp_env["config"], state_file=tmp_env["state_file"])

    # Very long tweet close to 275 chars
    long_tweet = "A" * 270
    optimized = sched._optimize_thread_for_exposure("TheCreatorAsset", [long_tweet])
    assert len(optimized[0]) <= 280


# ==============================================================================
# 2. NO UNANSWERED QUESTIONS / COMPLETE VALUE COPY TESTS
# ==============================================================================

def test_daily_slots_contain_no_unanswered_cliffhanger_questions(tmp_env):
    """Verifies that none of Herald's fallback daily slots end with open-ended cliffhanger questions."""
    for slot in DAILY_SLOTS:
        for account, tweets in slot.get("tweets", {}).items():
            for t in tweets:
                assert "Drop your thoughts below 👇💋 @creatorpulselab" not in t, (
                    f"Slot '{slot['slot_id']}' still contains an unanswered cliffhanger question"
                )

    # Verify slot_5 specifically gives the data-backed answer
    slot5 = next(s for s in DAILY_SLOTS if s["slot_id"] == "slot_5_latenight")
    pulse_slot5 = slot5["tweets"]["creatorpulselab"][0]
    assert "converts at 24.3%" in pulse_slot5
    assert "$18–$22" in pulse_slot5 or "$18-$22" in pulse_slot5


# ==============================================================================
# 3. FULL-DAY CATCH-UP DISPATCH TESTS
# ==============================================================================

def test_dispatch_today_all_now_dispatches_all_daily_slots(tmp_env, monkeypatch):
    sched = HeraldScheduler(config_path=tmp_env["config"], state_file=tmp_env["state_file"])
    monkeypatch.setattr(sched, "_get_brand_visual_for_post", lambda handle, topic_text=None: None)

    dispatched_slots = []

    def mock_dispatch_slot(slot_id):
        dispatched_slots.append(slot_id)
        return {"slot_id": slot_id, "fully_succeeded": True}

    monkeypatch.setattr(sched, "dispatch_slot", mock_dispatch_slot)
    monkeypatch.setattr(sched, "dispatch_newsletters_all", lambda: {"success": True})

    res = sched.dispatch_today_all_now()

    # All 5 daily slots must be dispatched
    expected_slots = [s["slot_id"] for s in DAILY_SLOTS]
    assert dispatched_slots == expected_slots
    assert len(res["twitter_slots_dispatched"]) == 5


# ==============================================================================
# 4. TWITTER POSTER DUPLICATE PREVENTION & CREDENTIALS
# ==============================================================================

def test_twitter_poster_blocks_duplicate_tweets(tmp_env):
    poster = TwitterPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["tweet_history"]
    )

    # Mock tweepy client
    mock_client = MagicMock()
    mock_client.create_tweet.return_value = MagicMock(data={"id": "123456789"})

    with patch.object(poster, "get_client", return_value=mock_client):
        # First post succeeds
        res1 = poster.post_thread("TheCreatorAsset", ["Unique tweet 1 for today #test"])
        assert res1["success"] is True

        # Second identical post is blocked as duplicate
        res2 = poster.post_thread("TheCreatorAsset", ["Unique tweet 1 for today #test"])
        assert res2["success"] is False
        assert res2.get("is_duplicate") is True
        assert "Duplicate tweet detected" in res2.get("error", "")


def test_twitter_poster_does_not_record_hash_on_failure(tmp_env):
    poster = TwitterPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["tweet_history"]
    )

    mock_client = MagicMock()
    mock_client.create_tweet.side_effect = RuntimeError("API 500 error")

    with patch.object(poster, "get_client", return_value=mock_client):
        res1 = poster.post_thread("TheCreatorAsset", ["Failing tweet to test retryability"])
        assert res1["success"] is False

    # Should NOT be marked duplicate on retry
    assert not poster._is_duplicate_tweet("Failing tweet to test retryability")


def test_twitter_poster_case_insensitive_handle(tmp_env):
    poster = TwitterPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["tweet_history"]
    )

    client1 = poster.get_client("@TheCreatorAsset")
    client2 = poster.get_client("thecreatorasset")
    client3 = poster.get_client("@CREATORPULSELAB")

    assert client1 is not None
    assert client2 is not None
    assert client3 is not None


# ==============================================================================
# 5. PINTEREST POSTER TOS SAFETY GATE & DUPLICATION
# ==============================================================================

def test_pinterest_poster_hard_blocks_adult_content(tmp_env):
    poster = PinterestPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["pin_history"]
    )

    # Blocked by content_type
    safe, reason = poster.is_pinterest_safe(content_type="adult")
    assert not safe
    assert "content_type is 'adult'" in reason

    # Blocked by keyword
    safe, reason = poster.is_pinterest_safe(
        content_type="general",
        text_blobs=["New cam tip menu with Lovense integration"]
    )
    assert not safe
    assert "disallowed term" in reason

    # Blocked by source path marker
    safe, reason = poster.is_pinterest_safe(
        content_type="general",
        text_blobs=["Portra color grading guide"],
        source_path="F:/WORKHORSE/workspace/client_character_renders/boudoir_shoot.png"
    )
    assert not safe
    assert "associated with the adult content brand" in reason


def test_pinterest_poster_allows_general_photography(tmp_env):
    poster = PinterestPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["pin_history"]
    )

    safe, reason = poster.is_pinterest_safe(
        content_type="general",
        text_blobs=["Kodak Portra 400 Lightroom Color Science", "How to set up studio lighting"],
        source_path="F:/WORKHORSE/workspace/brand_assets/studio_headshot.jpg"
    )
    assert safe
    assert reason == ""


def test_pinterest_poster_blocks_duplicate_pins(tmp_env):
    poster = PinterestPoster(
        config_path=tmp_env["config"],
        secrets_path=tmp_env["secrets"],
        history_path=tmp_env["pin_history"]
    )

    # First pin record
    poster._record_pin("Portra 400 Recipe|Lightroom settings")
    assert poster._is_duplicate_pin("Portra 400 Recipe|Lightroom settings")

    # In create_pin, duplicate pin is rejected before network
    res = poster.create_pin(
        board_id="b123",
        title="Portra 400 Recipe",
        description="Lightroom settings",
        image_url="https://example.com/img.jpg"
    )
    assert res["success"] is False
    assert res.get("status") == "duplicate"


# ==============================================================================
# 6. NEWSLETTER MANAGER INDEPENDENT COUNTERS & LIFECYCLE
# ==============================================================================

def test_newsletter_manager_independent_issue_numbers(tmp_path):
    mgr = NewsletterManager(workspace_base=str(tmp_path))

    n1 = mgr._get_daily_issue_number("creator_pulse", start_at=10)
    n2 = mgr._get_daily_issue_number("studio_wire", start_at=20)
    n3 = mgr._get_daily_issue_number("creator_blueprint", start_at=30)

    assert n1 == 10
    assert n2 == 20
    assert n3 == 30

    # Stable within the same day
    assert mgr._get_daily_issue_number("creator_pulse", start_at=10) == 10
    assert mgr._get_daily_issue_number("studio_wire", start_at=20) == 20


def test_newsletter_manager_unsubscribe_all(tmp_path):
    mgr = NewsletterManager(workspace_base=str(tmp_path))

    mgr.subscribe_multi("test@example.com", ["creator_pulse", "studio_wire"], send_welcome=False)

    unsub_res = mgr.unsubscribe("test@example.com", publication="all")
    assert unsub_res["success"] is True

    summary = mgr.get_subscribers_summary()
    target = next((s for s in summary["subscribers"] if s["email"] == "test@example.com"), None)
    assert target is not None
    assert target["status"] == "unsubscribed"
    assert target["publications"] == []
