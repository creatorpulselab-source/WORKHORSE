"""
Regression tests for the Single-Image Viral Video Director bugs found in the 2026-10-18 bug check:

  * Klein plates were cached by file name inside a per-MODE folder, so running a mode on a SECOND photo
    silently re-used the FIRST photo's plates (a video of the previous subject).
  * The director reported success=True even when DaVinci Resolve wasn't running and no video existed.
  * With Resolve closed there was no way to get a deliverable at all - now an ffmpeg fallback masters it.
"""
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from pipeline.stages import single_image_viral_director as svd
from pipeline.stages.single_image_viral_director import SingleImageViralDirector


@pytest.fixture
def director(monkeypatch):
    d = SingleImageViralDirector.__new__(SingleImageViralDirector)     # skip __init__ (touches global bridge/Resolve)
    d.comfy = Mock()
    d.resolve = Mock()
    d.template_klein = Path("unused.json")
    monkeypatch.setattr(svd.time, "sleep", lambda s: None)
    return d


def _photo(tmp_path, name, color):
    p = tmp_path / name
    Image.new("RGB", (320, 400), color).save(p)
    return p


def test_work_folder_is_unique_per_photo_so_plates_cannot_leak_between_subjects(director, tmp_path, monkeypatch):
    monkeypatch.setattr(svd, "SHORTS_OUT_ROOT", tmp_path / "shorts_out")
    a = _photo(tmp_path, "a.jpg", (200, 10, 10))
    b = _photo(tmp_path, "b.jpg", (10, 10, 200))
    a_copy = tmp_path / "batch_2" / "a.jpg"        # the same photo re-uploaded later in a new batch folder
    a_copy.parent.mkdir()
    a_copy.write_bytes(a.read_bytes())
    plate_dirs = []

    def fake_klein(source_image_path, edit_prompts, output_dir, seed_base=9001):
        plate_dirs.append(output_dir)
        return []

    director.generate_klein_multi_angle_edits = fake_klein
    director.comfy.generate_video_fasth3 = Mock(return_value={"success": False})
    results = [director.render_viral_mode_video(p, mode="micro_cinema") for p in (a, b, a_copy)]

    assert plate_dirs[0] != plate_dirs[1]          # different photos never share a plates folder
    assert plate_dirs[0] == plate_dirs[2]          # identical bytes may legitimately reuse their own plates
    assert "mode_micro_cinema" in str(plate_dirs[0]) and str(plate_dirs[0]).startswith(str(tmp_path / "shorts_out"))
    assert all(r["success"] is False and "No animated clips" in r["error"] for r in results)   # empty run is not "success"


def test_unique_output_name_per_run_never_reuses_a_stale_reel(director, tmp_path):
    photo = _photo(tmp_path, "p.jpg", (50, 50, 50))
    director.generate_klein_multi_angle_edits = Mock(return_value=[])
    director.comfy.generate_video_fasth3 = Mock(return_value={"success": False})
    res = director.render_viral_mode_video(photo, mode="fast_cut", work_dir=tmp_path / "w")
    assert Path(res["output_mp4"]).parent == tmp_path / "w"
    assert Path(res["output_mp4"]).name.startswith("fast_cut_master_reel_")


def _clips_ok(director, tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"c" * 70_000)
    director.generate_klein_multi_angle_edits = Mock(return_value=[])
    director.comfy.generate_video_fasth3 = Mock(return_value={"success": True, "file_path": str(clip)})
    director.resolve.generate_cinematic_cube_lut = Mock(return_value=None)
    return clip


def test_success_is_not_claimed_when_resolve_is_closed_and_nothing_was_rendered(director, tmp_path):
    photo = _photo(tmp_path, "p.jpg", (50, 50, 50))
    _clips_ok(director, tmp_path)
    director.resolve.assemble_and_grade_timeline_in_resolve = Mock(return_value={"used_resolve": False, "reason": "Resolve not active"})
    director._ffmpeg_master = Mock(return_value={"success": False, "reason": "ffmpeg missing"})
    res = director.render_viral_mode_video(photo, mode="handheld_camera", work_dir=tmp_path / "w")
    assert res["success"] is False                       # used to be a hard-coded True
    assert "Mastering failed" in res["error"]
    assert res["mastering"] == "ffmpeg_fallback"


def test_resolve_closed_falls_back_to_ffmpeg_and_says_so(director, tmp_path):
    photo = _photo(tmp_path, "p.jpg", (50, 50, 50))
    _clips_ok(director, tmp_path)
    director.resolve.assemble_and_grade_timeline_in_resolve = Mock(return_value={"used_resolve": False, "reason": "Resolve not active"})

    def fake_master(clips, out, w, h, fps, lut):
        Path(out).write_bytes(b"v" * 80_000)
        return {"success": True, "encoder": "h264_nvenc"}

    director._ffmpeg_master = fake_master
    res = director.render_viral_mode_video(photo, mode="micro_cinema", work_dir=tmp_path / "w")
    assert res["success"] is True and res["mastering"] == "ffmpeg_fallback"
    assert any("Resolve wasn't available" in w for w in res["warnings"])
    assert Path(res["output_mp4"]).exists()


def test_resolve_path_is_used_and_labelled_when_resolve_renders(director, tmp_path):
    photo = _photo(tmp_path, "p.jpg", (50, 50, 50))
    _clips_ok(director, tmp_path)

    def fake_resolve(project_name, clip_paths, output_mp4_path, **kw):
        Path(output_mp4_path).write_bytes(b"r" * 90_000)
        return {"used_resolve": True, "super_scale": f"{kw['super_scale']}x"}

    director.resolve.assemble_and_grade_timeline_in_resolve = fake_resolve
    director._ffmpeg_master = Mock()
    res = director.render_viral_mode_video(photo, mode="time_lapse", work_dir=tmp_path / "w", super_scale=4)
    assert res["success"] is True and res["mastering"] == "davinci_resolve_super_scale" and res["warnings"] == []
    director._ffmpeg_master.assert_not_called()


def test_a_rejected_klein_queue_is_skipped_instead_of_waiting_on_none(tmp_path):
    d = SingleImageViralDirector.__new__(SingleImageViralDirector)
    d.comfy = Mock()
    d.resolve = Mock()
    template = tmp_path / "t.json"
    template.write_text('{"1":{"inputs":{}},"2":{"inputs":{}},"3":{"inputs":{}},"4":{"inputs":{"LoadImageMiniState":"{}"}},'
                        '"5":{"inputs":{}},"7":{"inputs":{}},"8":{"inputs":{}},"16":{"inputs":{}}}', encoding="utf-8")
    d.template_klein = template
    d.comfy.upload_image_to_comfy.return_value = "up.jpg"
    d.comfy.queue_prompt.return_value = {"node_errors": {"x": "bad"}}          # no prompt_id
    photo = _photo(tmp_path, "p.jpg", (1, 2, 3))
    plates = d.generate_klein_multi_angle_edits(photo, ["one", "two"], tmp_path / "out")
    assert plates == []
    d.comfy.wait_for_execution.assert_not_called()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_ffmpeg_master_really_builds_a_graded_vertical_reel(tmp_path):
    """Runs real ffmpeg: two differently sized clips -> 1080x1920 reel with the LUT applied."""
    d = SingleImageViralDirector.__new__(SingleImageViralDirector)
    clips = []
    for i, size in enumerate(("640x480", "480x848")):
        c = tmp_path / f"c{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=24:duration=2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(c)], check=True, timeout=60)
        clips.append(c)
    lut = tmp_path / "id.cube"
    lines = ["TITLE \"identity\"", "LUT_3D_SIZE 2"]
    for b in (0, 1):
        for g in (0, 1):
            for r in (0, 1):
                lines.append(f"{r}.0 {g}.0 {b}.0")
    lut.write_text("\n".join(lines), encoding="utf-8")
    out = tmp_path / "reel.mp4"
    res = d._ffmpeg_master(clips, out, 1080, 1920, 24, lut)
    assert res["success"] is True, res
    assert out.exists() and out.stat().st_size > 50_000
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True, timeout=30).stdout.strip()
    w, h, dur = probe.split(",")
    assert (int(w), int(h)) == (1080, 1920)
    assert 3.5 < float(dur) < 4.6                                   # both 2s clips concatenated


# ---- chat tool result reflects the director's real outcome ---------------------------------------
@pytest.fixture
def engine(tmp_path, monkeypatch):
    from pipeline.stages import ai_operator as op
    monkeypatch.setattr(op, "OPERATOR_CHAT_SESSIONS_DIR", tmp_path / "s")
    (tmp_path / "s").mkdir()
    return op.AIOperatorEngine()


def _run_tool(engine, tmp_path, monkeypatch, director_result):
    batch = tmp_path / "batch_1"
    batch.mkdir()
    img = batch / "x.jpg"
    Image.new("RGB", (64, 64)).save(img)
    monkeypatch.setattr(SingleImageViralDirector, "__init__", lambda self, *a, **k: None)
    monkeypatch.setattr(SingleImageViralDirector, "render_viral_mode_video", lambda self, **kw: director_result)
    return engine.execute_internal_tool({"tool": "comfy_viral_video_director", "image": "x.jpg", "mode": "micro_cinema", "super_scale": 3},
                                        attached_files=[str(img)], batch_dir=batch)


def test_tool_reports_error_when_director_fails(engine, tmp_path, monkeypatch):
    res = _run_tool(engine, tmp_path, monkeypatch, {"success": False, "mode_name": "Micro Cinema", "error": "No animated clips were produced"})
    assert res["status"] == "error" and "No animated clips" in res["error"]
    assert "message" not in res or "mastered" not in res.get("message", "")


def test_tool_labels_ffmpeg_mastering_as_a_warning_not_resolve_super_scale(engine, tmp_path, monkeypatch):
    res = _run_tool(engine, tmp_path, monkeypatch, {"success": True, "mode_name": "Micro Cinema", "mastering": "ffmpeg_fallback",
                                                    "warnings": ["Resolve wasn't available"], "output_mp4": str(tmp_path / "r.mp4")})
    assert res["status"] == "warning"
    assert "ffmpeg" in res["message"] and "no Neural Engine Super Scale" in res["message"]
    assert "Neural Engine Super Scale 3x mastered" not in res["message"]


def test_tool_reports_resolve_super_scale_when_resolve_did_the_work(engine, tmp_path, monkeypatch):
    res = _run_tool(engine, tmp_path, monkeypatch, {"success": True, "mode_name": "Micro Cinema", "mastering": "davinci_resolve_super_scale",
                                                    "warnings": [], "output_mp4": str(tmp_path / "r.mp4")})
    assert res["status"] == "ok" and "Neural Engine Super Scale 3x mastered" in res["message"]


# ---- invented-object / black-bar fixes found in the live Micro Cinema test ------------------------
def test_no_mode_prompt_names_objects_a_photo_may_not_contain():
    """The old Micro Cinema prompt said 'jewelry or sunlit glass/prop' -> Klein invented gold rings and glassware."""
    banned = ("sunlit glass", "jewelry or", "earring or accessory", "necklace, collar", "flowers/environment", "neon city")
    for mode, spec in svd.VIRAL_MODES.items():
        for prompt in spec["klein_angle_prompts"]:
            assert not any(b in prompt.lower() for b in banned), (mode, prompt)


def test_every_klein_prompt_gets_the_reality_guard_and_plates_are_keyed_to_the_prompt(tmp_path):
    d = SingleImageViralDirector.__new__(SingleImageViralDirector)
    d.comfy = Mock()
    template = tmp_path / "t.json"
    template.write_text('{"1":{"inputs":{}},"2":{"inputs":{}},"3":{"inputs":{}},"4":{"inputs":{"LoadImageMiniState":"{}"}},'
                        '"5":{"inputs":{}},"7":{"inputs":{}},"8":{"inputs":{}},"16":{"inputs":{}}}', encoding="utf-8")
    d.template_klein = template
    d.comfy.upload_image_to_comfy.return_value = "up.jpg"
    sent = []
    d.comfy.queue_prompt.side_effect = lambda wf: sent.append(wf["8"]["inputs"]["text"]) or {}     # rejected -> skipped
    photo = _photo(tmp_path, "p.jpg", (9, 9, 9))
    d.generate_klein_multi_angle_edits(photo, ["Dreamy close-up of a real detail."], tmp_path / "plates")
    assert svd.KLEIN_REALITY_GUARD in sent[0] and "do not add any new object" in sent[0]

    # Same index, different prompt text => different cache file, so an edited prompt can never reuse an old plate.
    def plate_name(prompt):
        import hashlib
        return hashlib.sha1(f"{prompt} {svd.KLEIN_REALITY_GUARD}".encode()).hexdigest()[:8]
    assert plate_name("a") != plate_name("b")
    stale = tmp_path / "plates" / "klein_angle_01.png"                       # the old index-only name
    stale.write_bytes(b"x" * 200_000)
    d.comfy.queue_prompt.reset_mock()
    d.comfy.queue_prompt.side_effect = lambda wf: {}
    d.generate_klein_multi_angle_edits(photo, ["Dreamy close-up of a real detail."], tmp_path / "plates")
    assert d.comfy.queue_prompt.called                                       # stale plate was NOT served from cache


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_clips_are_center_cropped_to_the_reel_aspect_without_scaling(tmp_path):
    src = tmp_path / "portrait_4x5.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=768x960:rate=24:duration=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)], check=True, timeout=60)
    out = SingleImageViralDirector._conform_clips_to_aspect([src], 1080, 1920, tmp_path / "conformed")[0]
    assert out != src and out.exists()
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True, timeout=30).stdout.strip()
    w, h = (int(x) for x in probe.split(","))
    assert h == 960                                   # native height kept: no pre-scaling, Super Scale gets real pixels
    assert w == 540 and abs(w / h - 1080 / 1920) < 0.01   # cropped (not letterboxed) to 9:16


def test_matching_or_unreadable_clips_pass_through_untouched(tmp_path):
    garbage = tmp_path / "garbage.mp4"
    garbage.write_bytes(b"not a video")
    assert SingleImageViralDirector._conform_clips_to_aspect([garbage], 1080, 1920, tmp_path / "c") == [garbage]
