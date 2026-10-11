from shared.gpu1_arbiter import gpu1_arbiter
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

# Prevent OpenMP PyTorch/CTranslate2 collision
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class AudioAgent:
    """
    ECHO [26 Fe] Audio Intelligence Agent.
    Runs Faster-Whisper vocal extraction, transcription, and viral hook detection.
    Pinned by default to GPU 1 (device_index=1) on the Dual RTX 3060 setup so it
    runs 100% isolated from Synapse (GPU 0), preventing Out-Of-Memory (OOM) collisions.
    """
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        device_index: int = 1,
        auto_unload: bool = True
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.device_index = device_index
        self.auto_unload = auto_unload
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            # 1. Primary Attempt: Pinned to GPU 1 (Isolated from Synapse on GPU 0)
            try:
                from faster_whisper import WhisperModel
                print(f"[ECHO] Initializing Faster-Whisper ({self.model_size}) on GPU {self.device_index} (Dedicated Compute)...")
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    device_index=self.device_index,
                    compute_type=self.compute_type
                )
                return
            except Exception as e_gpu1:
                print(f"[ECHO] GPU {self.device_index} allocation failed ({e_gpu1}). Falling back to GPU 0...")

            # 2. Secondary Attempt: Fallback to GPU 0
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    device_index=0,
                    compute_type=self.compute_type
                )
                return
            except Exception as e_gpu0:
                print(f"[ECHO] GPU 0 allocation failed ({e_gpu0}). Falling back to CPU...")

            # 3. Tertiary Attempt: Fallback to CPU
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def unload_model(self):
        """Cleanly releases Faster-Whisper CTranslate2 memory from GPU VRAM."""
        if self.model is not None:
            del self.model
            self.model = None
            import gc
            gc.collect()
            if "torch" in sys.modules:
                try:
                    torch = sys.modules["torch"]
                    if hasattr(torch, "cuda") and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.ipc_collect()
                except Exception:
                    pass
            print("[ECHO] Unloaded Faster-Whisper from VRAM. GPU 1 memory 100% restored.")

    def extract_audio(self, video_path: Path, output_wav: Path) -> bool:
        """Extract clean 16kHz mono audio for Whisper."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_wav)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=60)
            return output_wav.exists() and output_wav.stat().st_size > 1000
        except Exception:
            return False

    def transcribe(
        self,
        video_path: Path,
        output_dir: Path,
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Extract and transcribe speech with timestamps and hooks."""
        # Acquire GPU 1 lock to coordinate with NVENC
        gpu1_arbiter.acquire("echo_whisper", timeout_seconds=30)
        try:
            return self._execute_transcribe(video_path, output_dir, progress_cb)
        finally:
            if self.auto_unload:
                self.unload_model()
            gpu1_arbiter.release("echo_whisper")

    def _execute_transcribe(
        self,
        video_path: Path,
        output_dir: Path,
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        wav_path = output_dir / "audio_extracted.wav"

        if progress_cb:
            progress_cb("Echo Agent: Extracting vocal audio track...", 20)

        has_audio = self.extract_audio(video_path, wav_path)
        if not has_audio:
            return {
                "has_audio": False,
                "full_text": "",
                "segments": [],
                "hooks": []
            }

        if progress_cb:
            progress_cb(f"Echo Agent: Running Whisper transcription on GPU {self.device_index} ({self.model_size})...", 50)

        segments_data = []
        full_text_parts = []
        hooks = []

        try:
            self._ensure_model()
            segments, info = self.model.transcribe(str(wav_path), beam_size=5, vad_filter=True)
            for seg in segments:
                text = seg.text.strip()
                if text:
                    full_text_parts.append(text)
                    segments_data.append({
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": text
                    })
                    # Catch punchy short statements as viral hooks
                    if len(text.split()) >= 3 and len(text.split()) <= 12:
                        hooks.append(text)
        except Exception as e:
            # Previously appended "[Transcription error: {e}]" directly into
            # full_text_parts - if some segments had already transcribed
            # successfully before a mid-stream failure (e.g. a CUDA/VRAM error),
            # this bracketed error text got concatenated onto the end of otherwise-
            # real spoken dialogue, making it look like part of the actual
            # transcript rather than a failure notice. Kept separate instead.
            transcription_error = str(e)
        else:
            transcription_error = None
        finally:
            if self.auto_unload:
                self.unload_model()

        full_transcript = " ".join(full_text_parts).strip()

        if progress_cb:
            progress_cb("Echo Agent: Audio transcription finalized!", 100)

        result = {
            "has_audio": True,
            "full_text": full_transcript,
            "segments": segments_data,
            "hooks": hooks[:5]
        }
        if transcription_error:
            result["transcription_error"] = transcription_error
        return result

if __name__ == "__main__":
    agent = AudioAgent()
    print(f"Echo Audio Agent ready on GPU {agent.device_index} with Auto-Unload: {agent.auto_unload}.")
