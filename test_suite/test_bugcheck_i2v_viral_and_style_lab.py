"""
Regression tests for the 2026-10-18 bug check:

  * Synapse image-to-video produced a "similar but different" video (last night) and a totally
    different video (this morning) - prompt invented without seeing the photo, wrong tool for the
    viral-mode wording, 4:5 photo forced into 9:16, prompt silently truncated by Ollama.
  * Iris "Style & Pose Lab" wrote no prompts from images - every call hit an HTTP 400 context
    overflow, then a canned prompt was cached and displayed as if it came from the photo.

All external services (Ollama, ComfyUI, web search) are mocked.
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from pipeline.stages import synapse_media_router as smr
from pipeline.stages import inspiration_scanner as scanner_module


# ------------------------------------------------------------------------------------------------
# synapse_media_router: viral mode routing
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("message,expected", [
    ("Use the micro cinema image to video workflow on this image", "micro_cinema"),
    ("run the Micro-Cinema viral moment on this", "micro_cinema"),
    ("use the handheld camera workflow on this image", "handheld_camera"),
    ("apply the handheld viral workflow", "handheld_camera"),
    ("make a fast cut reel from this photo", "fast_cut"),
    ("do the one take shot viral moment", "one_take_shot"),
    ("make a time lapse video of this", "time_lapse"),
    ("use time_lapse mode", "time_lapse"),
])
def test_detect_viral_mode_recognises_natural_wording(message, expected):
    assert smr.detect_viral_mode(message) == expected


@pytest.mark.parametrize("message", [
    "remove the background from this photo",
    "make a video where she holds a handheld mirror",   # bare 'handheld' is content, not the mode
    "make this image into a video and have her lick the controller",
    "",
])
def test_detect_viral_mode_ignores_unrelated_text(message):
    assert smr.detect_viral_mode(message) is None


def test_generic_viral_wording_is_detected_but_does_not_pick_a_mode():
    msg = "use one of the new viral moments on this image"
    assert smr.detect_viral_mode(msg) is None
    assert smr.mentions_generic_viral(msg) is True
    assert smr.mentions_generic_viral("viral") is False


@pytest.mark.parametrize("message,expected", [("upscale it 4x please", 4), ("2x super scale", 2), ("no scale given", 3)])
def test_parse_super_scale(message, expected):
    assert smr.parse_super_scale(message) == expected


# ------------------------------------------------------------------------------------------------
# synapse_media_router: motion keyword detection (word boundaries)
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("message", [
    "remove the background from this photo",     # old check: 'move' in 'remove'
    "click the link and send it",                # old check: 'lick' in 'click'
    "removed the logo",
])
def test_message_requests_motion_no_longer_matches_substrings(message):
    assert smr.message_requests_motion(message) is False


@pytest.mark.parametrize("message", [
    "Make this image into a video and have her lick the game controller",
    "animate this photo",
    "make it move",
    "image to video please",
    "have her lick the controller",
])
def test_message_requests_motion_still_matches_real_requests(message):
    assert smr.message_requests_motion(message) is True


# ------------------------------------------------------------------------------------------------
# synapse_media_router: aspect-correct resolution
# ------------------------------------------------------------------------------------------------
def test_pick_i2v_resolution_keeps_the_portrait_4x5_aspect():
    # The Commander's actual photo: 3648x4560 (0.8). It used to be forced to 704x1280 (0.55).
    w, h = smr.pick_i2v_resolution(3648, 4560)
    assert (w, h) == (768, 960)
    assert w % 64 == 0 and h % 64 == 0
    assert abs((w / h) - 0.8) < 0.02


@pytest.mark.parametrize("src", [(1080, 1920), (1920, 1080), (1000, 1000), (4000, 3000)])
def test_pick_i2v_resolution_valid_for_any_source(src):
    w, h = smr.pick_i2v_resolution(*src)
    assert w % 64 == 0 and h % 64 == 0
    assert 0.7 * smr.I2V_PIXEL_BUDGET <= w * h <= 1.25 * smr.I2V_PIXEL_BUDGET
    assert abs(((w / h) / (src[0] / src[1])) - 1) < 0.1


def test_pick_i2v_resolution_bad_input_falls_back():
    assert smr.pick_i2v_resolution(0, 0) == (704, 1280)


# ------------------------------------------------------------------------------------------------
# synapse_media_router: grounded motion prompts
# ------------------------------------------------------------------------------------------------
HALLUCINATED = (
    "A slow, graceful camera dolly forward as the subject walks confidently down a rain-slicked city street at night, "
    "neon signs reflecting on wet pavement. The camera follows slightly behind, maintaining focus on the subject's silhouette. "
    "Ambient city sounds fade into a smooth, cinematic jazz track with subtle synth pads and muted percussion."
)
BARN_CAPTION = "A woman in a cowboy hat and snakeskin boots leans against wooden barn slats in warm backlighting."


def test_scene_drift_detects_the_actual_hallucination_from_this_morning():
    hits = smr.find_scene_drift(HALLUCINATED, "Use the micro cinema image to video workflow on this image " + BARN_CAPTION)
    assert {"street", "city", "night", "neon", "rain"} <= set(hits)


def test_scene_drift_allows_words_the_photo_or_commander_actually_use():
    assert smr.find_scene_drift("she walks along the beach at night", "make her walk on the beach at night") == []
    assert smr.find_scene_drift("the camera pushes in on the street", "a woman standing in a street") == []


def test_grounded_prompt_discards_hallucinated_scene_and_keeps_continuity():
    prompt, notes = smr.build_grounded_i2v_prompt(
        "Use the micro cinema image to video workflow on this image", HALLUCINATED, BARN_CAPTION
    )
    low = prompt.lower()
    for bad in ("street", "neon", "rain", "city", "pavement"):
        assert bad not in low
    assert "no scene change" in low and "same subject" in low
    assert any("Discarded" in n for n in notes)


def test_grounded_prompt_keeps_a_faithful_prompt_but_fixes_the_close_up_opener():
    user = ("Make this image into a video and have her lick the game controller that her tongue is on "
            "and have the camera slowly zoom towards her mouth.")
    llm = ("A close-up shot of a woman with her tongue extended, licking a game controller. The camera slowly zooms "
           "toward her mouth, capturing the motion of her tongue across the controller's surface.")
    prompt, notes = smr.build_grounded_i2v_prompt(user, llm, "A woman with glasses on a couch holding a game controller.")
    assert prompt.startswith("Starting from the photo's framing, a woman")   # no longer tells the model to START tight
    assert "licking a game controller" in prompt
    assert "no scene change" in prompt.lower()
    assert not any("Discarded" in n for n in notes)


def test_composed_prompt_uses_the_commanders_own_words():
    user = ("Make this image into a video and have her lick the game controller that her tongue is on "
            "and have the camera slowly zoom towards her mouth.")
    prompt = smr.compose_motion_prompt(user)
    assert "slowly zooms toward her mouth" in prompt
    assert "She licks the game controller that her tongue is on" in prompt
    assert "street" not in prompt.lower()


def test_short_or_empty_model_prompt_is_rebuilt_not_trusted():
    prompt, notes = smr.build_grounded_i2v_prompt("animate this photo", "Slow pan", "")
    assert "no scene change" in prompt.lower()
    assert notes


# ------------------------------------------------------------------------------------------------
# synapse_media_router: prompt budget
# ------------------------------------------------------------------------------------------------
def test_knowledge_budget_shrinks_with_the_rest_of_the_prompt_and_can_hit_zero():
    assert smr.knowledge_char_budget(16384, 30_000) == 16000          # plenty of room: capped at guide max
    mid = smr.knowledge_char_budget(16384, 40_000)
    assert 2500 <= mid < 16000
    assert smr.knowledge_char_budget(16384, 47_500) == 0              # not even the minimum slice fits
    assert smr.estimate_tokens("x" * 3500) == 1000


# ------------------------------------------------------------------------------------------------
# Inspiration scanner (Iris Style & Pose Lab)
# ------------------------------------------------------------------------------------------------
GOOD_ANALYSIS = (
    "### SECTION 0: WHAT YOU SEE\nA woman in a cowboy hat leans on a barn door in strong backlight.\n\n"
    "### SECTION 1: COMFYUI POSITIVE IMAGE PROMPT (FLUX.1 / SDXL)\nA woman in a cowboy hat and snakeskin boots leaning on weathered barn slats, backlit.\n---\n\n"
    "### SECTION 2: COMFYUI VIDEO MOTION PROMPT (LTX 2.3 / MiniMax FastH3 image-to-video)\n"
    "The camera slowly pushes in while her hair sways gently and she shifts her weight, no scene change.\n---\n\n"
    "### SECTION 3: COMFYUI NEGATIVE IMAGE PROMPT\nblurry, bad hands, extra fingers, watermark\n\n"
    "### SECTION 4: RECOMMENDED COMFYUI NODE PARAMETERS\nUse 28 steps.\n"
)


@pytest.fixture
def scanner(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    sc = scanner_module.InspirationScanner(str(vault), str(tmp_path / "config.json"))
    monkeypatch.setattr(scanner_module, "VAULT_CACHE_FILE", tmp_path / "cache.json")
    Image.new("RGB", (64, 64), (120, 90, 60)).save(vault / "ref.jpg")
    return sc


def test_lab_vision_failure_is_reported_not_cached_and_never_replaced_by_a_canned_prompt(scanner, tmp_path):
    err = 'Error from Local Ollama Vision: HTTP 400 - {"error":"request (5896 tokens) exceeds the available context size (4096 tokens)"}'
    scanner.ai.call_ollama_vision = Mock(return_value=err)
    res = scanner.generate_comfyui_prompts()
    assert res["status"] == "error"
    assert res["image_prompt"] == "" and res["video_prompt"] == ""
    assert "captivating glamour model" not in json.dumps(res)          # the old canned fallback
    assert not (tmp_path / "cache.json").exists()                       # nothing poisoned
    assert scanner.generate_comfyui_prompts()["status"] == "error"      # next click retries, not a stale cache hit
    assert scanner.ai.call_ollama_vision.call_count == 2


def test_lab_blueprint_failure_is_reported_not_cached(scanner, tmp_path):
    scanner.ai.call_ollama_vision = Mock(return_value="Ollama Vision error: connection refused")
    res = scanner.scan_and_analyze()
    assert res["status"] == "error"
    assert not (tmp_path / "cache.json").exists()


def test_lab_success_uses_a_window_and_output_budget_that_actually_fit(scanner):
    scanner.ai.call_ollama_vision = Mock(return_value=GOOD_ANALYSIS)
    res = scanner.generate_comfyui_prompts("ref.jpg")
    assert res["status"] == "ok"
    kwargs = scanner.ai.call_ollama_vision.call_args.kwargs
    assert kwargs["num_predict"] >= 1200                  # was the 350-token default
    assert kwargs["num_ctx"] >= 8192                      # was 4096 -> HTTP 400 on every call
    assert kwargs["repeat_penalty"] and kwargs["repeat_penalty"] > 1.0
    assert len(kwargs["system_prompt"]) <= 7600           # knowledge slice trimmed to fit the vision window
    assert "## Module 6:" in kwargs["system_prompt"]      # ...without losing the prompt-writing guidance
    assert res["image_description"].startswith("A woman in a cowboy hat")
    assert res["video_prompt"].startswith("The camera slowly pushes in")
    assert res["negative_prompt"] == "blurry, bad hands, extra fingers, watermark"
    assert "---" not in res["image_prompt"] and "---" not in res["video_prompt"]


def test_lab_result_is_cached_only_when_complete(scanner):
    scanner.ai.call_ollama_vision = Mock(return_value=GOOD_ANALYSIS)
    first = scanner.generate_comfyui_prompts("ref.jpg")
    second = scanner.generate_comfyui_prompts("ref.jpg")
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert scanner.ai.call_ollama_vision.call_count == 1


def test_lab_missing_video_prompt_triggers_one_focused_retry(scanner):
    no_video = (
        "### SECTION 0: WHAT YOU SEE\nA woman on a couch.\n"
        "### SECTION 1: COMFYUI POSITIVE IMAGE PROMPT\nA woman on a leather couch holding a game controller, soft window light.\n"
        "### SECTION 3: COMFYUI NEGATIVE IMAGE PROMPT\nblurry, watermark\n"
    )
    retry = ("The camera drifts slowly closer while she breathes naturally, blinks softly and shifts the controller "
             "a little, keeping the same couch and lighting with no cut or scene change.")
    scanner.ai.call_ollama_vision = Mock(side_effect=[no_video, retry])
    res = scanner.generate_comfyui_prompts("ref.jpg")
    assert res["status"] == "ok"
    assert res["video_prompt"].startswith("The camera drifts slowly closer")
    assert any("second focused pass" in w for w in res["warnings"])
    assert scanner.ai.call_ollama_vision.call_count == 2


def test_lab_partial_result_is_labelled_partial_and_not_cached(scanner, tmp_path):
    only_image = "### SECTION 1: COMFYUI POSITIVE IMAGE PROMPT\nA woman on a leather couch holding a game controller, soft window light.\n"
    scanner.ai.call_ollama_vision = Mock(side_effect=[only_image, "too short"])
    res = scanner.generate_comfyui_prompts("ref.jpg")
    assert res["status"] == "partial"
    assert res["image_prompt"].startswith("A woman on a leather couch")
    assert res["video_prompt"] == ""
    assert any("missing" in w for w in res["warnings"])
    assert not (tmp_path / "cache.json").exists()


def test_lab_runaway_repetition_cannot_starve_the_result(scanner):
    looped = GOOD_ANALYSIS.replace("blurry, bad hands, extra fingers, watermark",
                                   "ugly, " + ", ".join(["oversaturated, oversharpened, oversmoothed"] * 200))
    scanner.ai.call_ollama_vision = Mock(return_value=looped)
    res = scanner.generate_comfyui_prompts("ref.jpg")
    assert res["status"] == "ok"
    assert res["negative_prompt"].count("oversaturated") == 1
    assert len(res["negative_prompt"]) < 200


def test_lab_poisoned_cache_entries_from_the_old_bug_are_purged_on_load(scanner, tmp_path):
    poisoned = {
        "comfyui:aaa": {"images_scanned": ["x.jpg"], "image_prompt": "Cinematic 85mm portrait of a captivating glamour model, ...",
                         "full_markdown": "Error from Local Ollama Vision: HTTP 400 - exceeds the available context size", "cached_at": 1},
        "blueprint:bbb": {"images_scanned": ["x.jpg"], "blueprint_markdown": "Ollama Vision error: WORKHORSE test suite: blocked a real network connection", "cached_at": 2},
        "blueprint:good": {"images_scanned": ["y.jpg"], "blueprint_markdown": "**SHOOT BLUEPRINT** real content that is long enough", "cached_at": 3},
    }
    (tmp_path / "cache.json").write_text(json.dumps(poisoned), encoding="utf-8")
    loaded = scanner._load_vault_cache()
    assert list(loaded) == ["blueprint:good"]
    assert list(json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))) == ["blueprint:good"]


@pytest.mark.parametrize("text,key,expected_start", [
    ("### SECTION 2: COMFYUI VIDEO MOTION PROMPT\nslow push\n", "video", "slow push"),
    ("**Section 1 - Positive Image Prompt**\nA cowboy hat\n", "image", "A cowboy hat"),
    ("## SECTION 3: NEGATIVE\nblurry\n", "negative", "blurry"),
])
def test_section_parser_classifies_by_heading_name_not_just_number(text, key, expected_start):
    assert scanner_module._split_sections(text)[key].startswith(expected_start)


def test_collapse_repetition_leaves_clean_text_alone():
    clean = "A woman in a hat. She leans on a door. Warm backlight."
    assert scanner_module._collapse_repetition(clean) == clean


# ------------------------------------------------------------------------------------------------
# ai_providers / knowledge plumbing
# ------------------------------------------------------------------------------------------------
def test_vision_call_sends_the_requested_window_image_cap_and_sampling(tmp_path, monkeypatch):
    from shared import ai_providers
    svc = ai_providers.AIProviderService(str(tmp_path / "config.json"))
    img = tmp_path / "a.jpg"
    Image.new("RGB", (2000, 3000), (10, 20, 30)).save(img)
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen["payload"] = json
        return Mock(status_code=200, json=lambda: {"response": "ok"})

    monkeypatch.setattr(ai_providers.requests, "post", fake_post)
    monkeypatch.setattr(ai_providers.vram_manager, "prepare_for_model", lambda m, **kw: seen.setdefault("warm", kw))
    out = svc.call_ollama_vision("describe", [img], num_predict=900, num_ctx=12288, image_max_dim=512, temperature=0.4, repeat_penalty=1.2)
    assert out == "ok"
    opts = seen["payload"]["options"]
    assert opts == {"temperature": 0.4, "num_predict": 900, "num_ctx": 12288, "repeat_penalty": 1.2}
    assert seen["warm"] == {"num_ctx": 12288}              # warm-up and request use the same window
    # image really was downscaled to the requested cap (JPEG base64 of a <=512px image is small)
    import base64, io
    decoded = Image.open(io.BytesIO(base64.b64decode(seen["payload"]["images"][0])))
    assert max(decoded.size) <= 512


def test_vision_call_default_keeps_qc_behaviour_but_with_a_usable_window(tmp_path, monkeypatch):
    from shared import ai_providers
    svc = ai_providers.AIProviderService(str(tmp_path / "config.json"))
    img = tmp_path / "a.jpg"
    Image.new("RGB", (100, 100)).save(img)
    seen = {}
    monkeypatch.setattr(ai_providers.requests, "post",
                        lambda url, json=None, timeout=None: seen.update(payload=json) or Mock(status_code=200, json=lambda: {"response": "x"}))
    monkeypatch.setattr(ai_providers.vram_manager, "prepare_for_model", lambda m, **kw: None)
    svc.call_ollama_vision("qc", [img])
    opts = seen["payload"]["options"]
    assert opts["temperature"] == 0.1 and opts["num_predict"] == 350      # QC behaviour unchanged
    assert opts["num_ctx"] == ai_providers.VISION_NUM_CTX and "repeat_penalty" not in opts


def test_context_windows_are_big_enough_and_warmups_match(monkeypatch):
    from shared import ai_providers
    from shared.vram_manager import VramManager
    assert ai_providers.TEXT_NUM_CTX >= 16384 and ai_providers.VISION_NUM_CTX >= 12288
    posted = []
    vm = VramManager(idle_timeout_seconds=300)
    monkeypatch.setattr("shared.vram_manager.requests.post",
                        lambda url, json=None, timeout=None: posted.append(json) or Mock(status_code=200))
    vm._warm_up_model("huihui_ai/qwen3-abliterated:14b", "5m")
    vm._warm_up_model("huihui_ai/qwen3-vl-abliterated:8b-instruct", "5m")
    assert posted[0]["options"]["num_ctx"] == ai_providers.TEXT_NUM_CTX
    assert posted[1]["options"]["num_ctx"] == ai_providers.VISION_NUM_CTX


def test_get_comfyui_context_honours_a_smaller_budget_without_cutting_excerpts():
    from shared.comfyui_knowledge import get_comfyui_context, MAX_CONTEXT_CHARS
    small = get_comfyui_context("inspiration", max_chars=6500)
    full = get_comfyui_context("inspiration")
    assert len(small) <= 6500 < len(full) <= MAX_CONTEXT_CHARS
    assert "## Module 6:" in small
    assert get_comfyui_context("inspiration", max_chars=10 ** 9) == full     # can only shrink, never exceed the cap


# ------------------------------------------------------------------------------------------------
# Synapse engine: end-to-end behaviour with mocked services
# ------------------------------------------------------------------------------------------------
@pytest.fixture
def engine(tmp_path, monkeypatch):
    from pipeline.stages import ai_operator as op
    from pipeline.stages.comfyui_bridge import comfy_bridge
    from pipeline.stages.trend_researcher import trend_researcher

    monkeypatch.setattr(op, "OPERATOR_CHAT_SESSIONS_DIR", tmp_path / "sessions")
    (tmp_path / "sessions").mkdir()
    monkeypatch.setattr(op, "get_latest_client_batch_dir", lambda session: None)
    monkeypatch.setattr(op.vram_manager, "prepare_for_model", lambda model, **kw: None)
    monkeypatch.setattr(comfy_bridge, "get_prompt_context_summary", lambda: "LIVE COMFY INVENTORY")
    monkeypatch.setattr(trend_researcher, "get_daily_summary_prompt_context", lambda: "")
    eng = op.AIOperatorEngine()
    monkeypatch.setattr(eng, "get_live_task_status_context", lambda: "LIVE AGENT STATUS")
    monkeypatch.setattr(eng, "get_recent_incidents", lambda **kwargs: [])
    return eng


@pytest.fixture
def photo(tmp_path):
    batch = tmp_path / "client_inbox" / "batch_20261018_063441_abc123"
    batch.mkdir(parents=True)
    img = batch / "JT2A6087_teaser_preview.jpg"
    Image.new("RGB", (800, 1000), (90, 60, 40)).save(img)      # 4:5 portrait like the real photo
    return img


def _ollama_reply(text="Done, Commander."):
    resp = Mock(status_code=200)
    resp.json.return_value = {"message": {"content": text}}
    return Mock(return_value=resp)


def test_micro_cinema_wording_runs_the_viral_director_not_generic_image_to_video(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    post = _ollama_reply()
    monkeypatch.setattr(op.requests, "post", post)
    calls = []
    monkeypatch.setattr(engine, "run_tool_and_log",
                        lambda tool_call, **kw: calls.append(tool_call) or {"status": "ok", "tool": tool_call["tool"],
                                                                           "media": [{"type": "video", "filename": "reel.mp4"}]})
    res = engine.chat("Use the micro cinema image to video workflow on this image",
                      model="huihui_ai/qwen3-vl-abliterated:8b-instruct", web_search=True,
                      attached_files=[str(photo)], session_id="viral-test")
    assert calls == [{"tool": "comfy_viral_video_director", "image": photo.name, "mode": "micro_cinema", "super_scale": 3}]
    post.assert_not_called()                                   # no LLM guesswork at all
    assert res["status"] == "ok" and "Micro Cinema" in res["reply"]
    assert res["executed_actions"][0]["tool"] == "comfy_viral_video_director"


def test_named_super_scale_is_passed_to_the_viral_director(engine, photo, monkeypatch):
    calls = []
    monkeypatch.setattr(engine, "run_tool_and_log", lambda t, **kw: calls.append(t) or {"status": "ok", "tool": t["tool"]})
    engine.chat("run the time lapse viral workflow with 4x upscale", attached_files=[str(photo)], session_id="s4")
    assert calls[0]["mode"] == "time_lapse" and calls[0]["super_scale"] == 4


def test_generic_viral_request_asks_which_mode_instead_of_guessing(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    post = _ollama_reply()
    monkeypatch.setattr(op.requests, "post", post)
    ran = []
    monkeypatch.setattr(engine, "run_tool_and_log", lambda *a, **k: ran.append(a) or {})
    res = engine.chat("use one of the new viral moments on this image", attached_files=[str(photo)], session_id="generic")
    assert ran == [] and post.call_count == 0
    assert len(res["quick_options"]) == 5
    assert all("viral workflow" in o for o in res["quick_options"])
    assert "Micro Cinema" in res["reply"] and "Time-Lapse" in res["reply"]


def test_viral_wording_without_any_photo_falls_through_to_the_normal_path(engine, monkeypatch):
    from pipeline.stages import ai_operator as op
    post = _ollama_reply("Please attach a photo, Commander.")
    monkeypatch.setattr(op.requests, "post", post)
    monkeypatch.setattr(engine, "detect_vision_requirement", lambda **kw: (False, "", [], None))
    res = engine.chat("use the micro cinema workflow", session_id="nophoto")
    assert post.called and res["reply"].startswith("Please attach a photo")


def test_media_command_uses_the_14b_operator_even_if_the_ui_sent_the_vision_model(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    post = _ollama_reply("Sure.")
    monkeypatch.setattr(op.requests, "post", post)
    # The motion fallback queues an image-to-video call after the chat turn; keep it away from the real handler.
    monkeypatch.setattr(engine, "run_tool_and_log", lambda t, **kw: {"status": "ok", "tool": t["tool"]})
    engine.chat("Make this image into a video and slowly zoom toward her mouth",
                model="huihui_ai/qwen3-vl-abliterated:8b-instruct", attached_files=[str(photo)], session_id="m14")
    first_chat_payload = post.call_args_list[0].kwargs["json"]
    assert first_chat_payload["model"] == op.DEFAULT_TEXT_MODEL
    assert "images" not in first_chat_payload["messages"][-1]                  # no image was sent to the LLM


def test_media_command_skips_web_search_even_if_the_toggle_is_on(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    monkeypatch.setattr(op.requests, "post", _ollama_reply("Sure."))
    monkeypatch.setattr(engine, "run_tool_and_log", lambda t, **kw: {"status": "ok", "tool": t["tool"]})
    search = Mock(return_value=[{"title": "best cinema cameras", "url": "http://x", "snippet": "s"}])
    monkeypatch.setattr(engine, "search_web", search)
    res = engine.chat("Make this image into a video", web_search=True, attached_files=[str(photo)], session_id="nosearch")
    search.assert_not_called()
    assert res["web_sources"] == [] and "Skipped web search" in res["web_search_skipped_reason"]


def test_normal_questions_still_honour_the_web_search_toggle(engine, monkeypatch):
    from pipeline.stages import ai_operator as op
    monkeypatch.setattr(op.requests, "post", _ollama_reply("Here you go."))
    monkeypatch.setattr(engine, "detect_vision_requirement", lambda **kw: (False, "", [], None))
    search = Mock(return_value=[{"title": "T", "url": "http://x", "snippet": "s"}])
    monkeypatch.setattr(engine, "search_web", search)
    engine.chat("what is the best lens for boudoir portraits", web_search=True, session_id="search-ok")
    search.assert_called_once()


def test_remove_background_no_longer_queues_a_video_render(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    monkeypatch.setattr(op.requests, "post", _ollama_reply("I can do that, Commander."))
    run = Mock(return_value={"status": "ok"})
    monkeypatch.setattr(engine, "run_tool_and_log", run)
    res = engine.chat("remove the background from this photo", attached_files=[str(photo)], session_id="rm-bg")
    run.assert_not_called()
    assert res["executed_actions"] == []


def test_synapse_prompt_fits_the_window_and_keeps_the_tool_documentation(engine, monkeypatch):
    from pipeline.stages import ai_operator as op
    from shared.ai_providers import TEXT_NUM_CTX
    post = _ollama_reply("OK")
    monkeypatch.setattr(op.requests, "post", post)
    monkeypatch.setattr(engine, "detect_vision_requirement", lambda **kw: (False, "", [], None))
    # a long, realistic history + a web result stress the budget
    hist = engine.get_history("budget")
    for i in range(6):
        hist.append({"role": "user" if i % 2 == 0 else "assistant", "content": "lorem ipsum dolor sit amet " * 120})
    res = engine.chat("Explain a Trellis PBR workflow", session_id="budget")
    payload = post.call_args.kwargs["json"]
    assert payload["options"]["num_ctx"] == TEXT_NUM_CTX == 16384            # was 8192 (and effectively 4098)
    system = payload["messages"][0]["content"]
    assert "comfy_viral_video_director" in system and "comfy_image_to_video" in system   # tool docs intact
    total_tokens = smr.estimate_tokens("".join(str(m["content"]) for m in payload["messages"]))
    assert total_tokens <= TEXT_NUM_CTX - smr.OUTPUT_RESERVE_TOKENS          # fits => Ollama never truncates it
    assert res["prompt_budget"]["prompt_tokens_estimate"] <= TEXT_NUM_CTX - smr.OUTPUT_RESERVE_TOKENS


def test_second_pass_summary_uses_a_compact_prompt_and_the_real_window(engine, photo, monkeypatch):
    from pipeline.stages import ai_operator as op
    first = Mock(status_code=200)
    first.json.return_value = {"message": {"content": '```json\n{"tool": "system_diagnostics"}\n```'}}
    second = Mock(status_code=200)
    second.json.return_value = {"message": {"content": "All systems nominal, Commander."}}
    post = Mock(side_effect=[first, second])
    monkeypatch.setattr(op.requests, "post", post)
    monkeypatch.setattr(engine, "detect_vision_requirement", lambda **kw: (False, "", [], None))
    monkeypatch.setattr(engine, "run_tool_and_log", lambda t, **kw: {"status": "ok", "tool": "system_diagnostics", "message": "fine"})
    res = engine.chat("check system health", session_id="second-pass")
    payload2 = post.call_args_list[1].kwargs["json"]
    assert payload2["options"]["num_ctx"] == 16384
    assert len(payload2["messages"][0]["content"]) < 600                       # not the 26K-char system prompt
    assert res["reply"] == "All systems nominal, Commander."


# --- image-to-video handler -------------------------------------------------------------------
def _run_i2v(engine, photo, monkeypatch, tool_extra=None, caption=BARN_CAPTION, prompt=HALLUCINATED, user_msg="Use the micro cinema image to video workflow on this image"):
    from pipeline.stages.comfyui_bridge import comfy_bridge
    captured = {}

    def fake_i2v(**kwargs):
        captured.update(kwargs)
        return {"success": True, "file_path": str(photo.parent / "out.mp4"), "filename": "out.mp4"}

    monkeypatch.setattr(comfy_bridge, "generate_image_to_video", fake_i2v)
    monkeypatch.setattr(engine, "describe_image_for_video", lambda p: caption)
    call = {"tool": "comfy_image_to_video", "image": photo.name, "prompt": prompt, "_user_message": user_msg}
    call.update(tool_extra or {})
    result = engine.execute_internal_tool(call, attached_files=[str(photo)], batch_dir=photo.parent)
    return result, captured


def test_i2v_handler_discards_the_hallucinated_scene_and_fits_the_photo_aspect(engine, photo, monkeypatch):
    result, sent = _run_i2v(engine, photo, monkeypatch)
    assert result["status"] == "ok"
    low = sent["prompt"].lower()
    assert all(w not in low for w in ("street", "neon", "rain", "pavement"))
    assert "no scene change" in low
    assert sent["width"] % 64 == 0 and sent["height"] % 64 == 0
    assert abs(sent["width"] / sent["height"] - 0.8) < 0.03                       # 4:5 photo stays 4:5
    assert result["grounding"]["image_caption"] == BARN_CAPTION
    assert any("Discarded" in n for n in result["grounding"]["notes"])
    assert result["expanded_prompt"] == sent["prompt"]


def test_i2v_handler_respects_an_explicit_resolution(engine, photo, monkeypatch):
    _, sent = _run_i2v(engine, photo, monkeypatch, tool_extra={"width": 704, "height": 1280})
    assert (sent["width"], sent["height"]) == (704, 1280)


def test_i2v_handler_keeps_a_faithful_prompt(engine, photo, monkeypatch):
    good = ("The camera slowly pushes in toward her face while her hair sways gently and she shifts her weight, "
            "breathing naturally with soft blinks.")
    result, sent = _run_i2v(engine, photo, monkeypatch, prompt=good, user_msg="make it move with a slow push in", caption="")
    assert sent["prompt"].startswith("The camera slowly pushes in toward her face")
    assert not any("Discarded" in n for n in result["grounding"]["notes"])


def test_video_workflow_default_soundtrack_is_no_longer_forced_sensual():
    from pipeline.stages.comfyui_bridge import ComfyUIBridge
    wf = ComfyUIBridge.build_image_to_video_workflow(
        Mock(), source_image_name="a.jpg", prompt="The camera pushes in on the product on a white table.", seed=1)
    text = wf["267:266"]["inputs"]["value"]
    assert "sensual" not in text.lower()
    assert "smooth ambient background music" in text


def test_caption_helper_returns_empty_when_vision_errors_and_caches_success(engine, photo, monkeypatch):
    from shared import ai_providers
    engine._caption_cache.clear()
    monkeypatch.setattr(ai_providers.AIProviderService, "call_ollama_vision",
                        lambda self, *a, **k: "Ollama Vision error: down")
    assert engine.describe_image_for_video(photo) == ""
    calls = []
    monkeypatch.setattr(ai_providers.AIProviderService, "call_ollama_vision",
                        lambda self, *a, **k: calls.append(1) or "A woman in a hat.")
    assert engine.describe_image_for_video(photo) == "A woman in a hat."
    assert engine.describe_image_for_video(photo) == "A woman in a hat."
    assert len(calls) == 1                                                        # second call served from cache
