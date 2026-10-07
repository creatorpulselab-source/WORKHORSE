import os
import time
import uuid
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from pipeline.stages.scene_extractor import get_video_info, extract_6_poses, cut_preview_video, generate_social_crops
from pipeline.stages.audio_agent import AudioAgent
from pipeline.stages.vision_agent import VisionAgent
from pipeline.stages.copy_synthesizer import CopySynthesizer
from pipeline.stages.package_exporter import PackageExporter

class PipelineJob:
    def __init__(self, job_id: str, video_path: Path, preset: str = "Adult Creator Shoot"):
        self.job_id = job_id
        self.video_path = video_path
        self.preset = preset
        self.status = "queued"
        self.progress = 0
        self.current_stage = 0
        self.total_stages = 7
        self.active_agent = "vanguard"
        self.agent_message = "Vanguard: Job initialized and standing by in queue."
        self.logs: List[str] = []
        self.results: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None

    def add_log(self, text: str):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {text}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "filename": self.video_path.name,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "total_stages": self.total_stages,
            "active_agent": self.active_agent,
            "agent_message": self.agent_message,
            "logs": self.logs[-50:],
            "results": self.results,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_sec": round(self.finished_at - self.started_at, 1) if (self.started_at and self.finished_at) else None
        }

class WorkhorseOrchestrator:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.config_path = Path(config_path)
        self.jobs: Dict[str, PipelineJob] = {}
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self.lock = threading.Lock()

        self.audio_agent = AudioAgent()
        self.vision_agent = VisionAgent(str(config_path))
        self.copy_agent = CopySynthesizer(str(config_path))
        self.exporter = PackageExporter()

    def load_latest_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def notify_event(self, job: PipelineJob):
        data = job.to_dict()
        for cb in list(self.subscribers):
            try:
                cb(data)
            except Exception:
                pass

    def create_job(self, video_path: Path, preset: str = "Adult Creator Shoot") -> PipelineJob:
        job_id = f"wh_{uuid.uuid4().hex[:8]}"
        job = PipelineJob(job_id, video_path, preset)
        with self.lock:
            self.jobs[job_id] = job
        self.notify_event(job)
        return job

    def run_job_async(self, job_id: str):
        t = threading.Thread(target=self._execute_pipeline, args=(job_id,), daemon=True)
        t.start()

    def _execute_pipeline(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        cfg = self.load_latest_config()
        agents_cfg = cfg.get("agents", {})

        vanguard_cfg = agents_cfg.get("vanguard", {})
        iris_cfg = agents_cfg.get("iris", {})
        echo_cfg = agents_cfg.get("echo", {})
        aura_cfg = agents_cfg.get("aura", {})
        forge_cfg = agents_cfg.get("forge", {})

        job.status = "running"
        job.started_at = time.time()
        job.add_log(f"Starting WORKHORSE pipeline on: {job.video_path.name}")
        job.add_log(f"100% Local GPU Execution Mode (Air-Gapped Private)")
        self.notify_event(job)

        work_dir = Path("F:/WORKHORSE/workspace/temp") / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # STAGE 1: VANGUARD
            job.current_stage = 1
            job.active_agent = "vanguard"
            job.agent_message = "Vanguard: Inspecting stream specs and configuring Dual RTX 3060 allocation..."
            job.add_log("Stage 1/7: Vanguard verifying stream integrity...")
            self.notify_event(job)

            v_info = get_video_info(job.video_path)
            job.results["video_info"] = v_info
            job.progress = 12
            job.add_log(f"Video verified: {v_info.get('duration', 0)}s, {v_info.get('width', 0)}x{v_info.get('height', 0)} @ {v_info.get('fps', 0)}fps")
            self.notify_event(job)

            # STAGE 2: IRIS (Pose Extraction)
            job.current_stage = 2
            job.active_agent = "iris"
            pose_target = int(iris_cfg.get("pose_count", 6))
            job.agent_message = f"Iris: Extracting {pose_target} high-res pose screenshots..."
            job.add_log(f"Stage 2/7: Iris sampling {pose_target} frames...")
            self.notify_event(job)

            poses = extract_6_poses(
                job.video_path,
                work_dir / "poses",
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 12, 28, pct)
            )
            job.results["pose_count"] = len(poses)
            job.progress = 28
            job.add_log(f"Captured {len(poses)} high-res pose screenshots.")
            self.notify_event(job)

            # STAGE 3: FORGE (Teaser & Crops)
            job.current_stage = 3
            job.active_agent = "forge"
            teaser_duration = int(forge_cfg.get("preview_duration_sec", 60))
            job.agent_message = f"Forge: Cutting {teaser_duration}s teaser trailer & rendering social crops..."
            job.add_log(f"Stage 3/7: Forge encoding {teaser_duration}s teaser with NVENC...")
            self.notify_event(job)

            preview_cut = cut_preview_video(
                job.video_path,
                work_dir / "previews",
                target_duration=teaser_duration,
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 28, 42, pct)
            )
            social_crops = {}
            if preview_cut:
                social_crops = generate_social_crops(
                    preview_cut,
                    work_dir / "previews",
                    progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 42, 50, pct)
                )

            job.progress = 50
            job.add_log("Teaser preview and social crops generated.")
            self.notify_event(job)

            # STAGE 4: ECHO (Whisper Audio)
            job.current_stage = 4
            job.active_agent = "echo"
            whisper_model = echo_cfg.get("whisper_model", "base")
            job.agent_message = f"Echo: Extracting audio and running Faster-Whisper ({whisper_model})..."
            job.add_log("Stage 4/7: Echo isolating vocal audio and detecting hooks...")
            self.notify_event(job)

            audio_data = self.audio_agent.transcribe(
                job.video_path,
                work_dir / "audio",
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 50, 65, pct)
            )
            job.results["audio"] = audio_data
            job.progress = 65
            job.add_log(f"Audio processed: {len(audio_data.get('segments', []))} speech segments, {len(audio_data.get('hooks', []))} spoken hooks.")
            self.notify_event(job)

            # STAGE 5: IRIS (Aesthetic Analysis)
            job.current_stage = 5
            job.active_agent = "iris"
            vision_model = iris_cfg.get("vision_model", "huihui_ai/qwen3-vl-abliterated:8b-instruct")
            job.agent_message = f"Iris: Analyzing poses locally with {vision_model.split(':')[0]}..."
            job.add_log("Stage 5/7: Iris inspecting lighting, setting, and wardrobe aesthetics...")
            self.notify_event(job)

            vision_data = self.vision_agent.analyze_poses(
                poses,
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 65, 78, pct)
            )
            job.results["vision"] = vision_data
            job.progress = 78
            job.add_log("Vision analysis complete.")
            self.notify_event(job)

            # STAGE 6: AURA (Copy Synthesizer)
            job.current_stage = 6
            job.active_agent = "aura"
            text_model = aura_cfg.get("text_model", "huihui_ai/qwen3-abliterated:14b")
            tone = aura_cfg.get("tone_preset", "seductive_teasing")
            job.agent_message = f"Aura: Generating release kit with {text_model.split(':')[0]} (Tone: {tone})..."
            job.add_log("Stage 6/7: Aura crafting OnlyFans, Fansly, IG, Twitter, and TikTok copy...")
            self.notify_event(job)

            copy_kit = self.copy_agent.generate_release_kit(
                video_name=job.video_path.name,
                visual_analysis=vision_data.get("visual_summary", ""),
                transcript_text=audio_data.get("full_text", ""),
                spoken_hooks=audio_data.get("hooks", []),
                preset=job.preset,
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 78, 90, pct)
            )
            job.results["copy_kit"] = copy_kit
            job.progress = 90
            job.add_log("Social media release kit synthesized.")
            self.notify_event(job)

            # STAGE 7: FORGE (Package Export)
            job.current_stage = 7
            job.active_agent = "forge"
            job.agent_message = "Forge: Bundling all deliverables and building final ZIP package..."
            job.add_log("Stage 7/7: Forge saving deliverables to output directory...")
            self.notify_event(job)

            bundle_res = self.exporter.export_bundle(
                video_name=job.video_path.name,
                pose_files=poses,
                preview_video=preview_cut,
                social_crops=social_crops,
                audio_data=audio_data,
                vision_data=vision_data,
                copy_kit=copy_kit,
                progress_cb=lambda msg, pct: self._update_subprogress(job, msg, 90, 100, pct)
            )
            job.results["bundle"] = bundle_res
            job.progress = 100
            job.status = "completed"
            job.active_agent = "vanguard"
            job.agent_message = f"Vanguard: Mission accomplished! Complete package ready at {bundle_res.get('package_dir')}."
            job.finished_at = time.time()
            job.add_log(f"SUCCESS: Package saved to: {bundle_res.get('package_dir')}")
            self.notify_event(job)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.active_agent = "vanguard"
            job.agent_message = f"Vanguard: Alert! Error encountered during pipeline execution: {e}"
            job.finished_at = time.time()
            job.add_log(f"FATAL ERROR: {e}")
            self.notify_event(job)

    def _update_subprogress(self, job: PipelineJob, message: str, stage_start: int, stage_end: int, sub_pct: int):
        range_span = stage_end - stage_start
        overall_pct = int(stage_start + (sub_pct / 100.0) * range_span)
        job.progress = min(99, max(job.progress, overall_pct))
        job.agent_message = message
        job.add_log(message)
        self.notify_event(job)

if __name__ == "__main__":
    orchestrator = WorkhorseOrchestrator()
    print("Orchestrator ready with dynamic agent tuning.")
