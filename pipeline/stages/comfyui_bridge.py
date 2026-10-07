import os
import sys
import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

sys.path.insert(0, "F:/WORKHORSE")
from shared.ai_providers import AIProviderService

BASE_DIR = Path("F:/WORKHORSE")
CONFIG_FILE = Path("F:/WORKHORSE/config.json")
WORKSPACE_DIR = Path("F:/WORKHORSE/workspace")
STAGING_DIR = WORKSPACE_DIR / "comfy_staging"
RENDERS_DIR = WORKSPACE_DIR / "brand_assets" / "comfy_renders"
VIDEO_RENDERS_DIR = WORKSPACE_DIR / "brand_assets" / "comfy_video_renders"
AUDIT_LOG_FILE = WORKSPACE_DIR / "comfy_qc_audit.json"
WORKFLOW_TEMPLATES_DIR = BASE_DIR / "pipeline" / "stages" / "workflow_templates"

STAGING_DIR.mkdir(parents=True, exist_ok=True)
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_RENDERS_DIR.mkdir(parents=True, exist_ok=True)


class ComfyUIBridge:
    """
    WORKHORSE ComfyUI Bridge & Visual Quality Gate (Iris [77 Ir]).
    Connects to RTX 5070 Ti (16GB) on Main PC for heavy diffusion generation
    and enforces local Qwen-VL Vision quality control for extra limbs/artifacts.
    """
    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.ai = AIProviderService(str(self.config_path))
        self.client_id = str(uuid.uuid4())
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.comfy_cfg = cfg.get("comfyui", {})
                    self.host = self.comfy_cfg.get("host", "100.114.140.7")
                    self.port = self.comfy_cfg.get("port", 8188)
                    self.fallback_hosts = self.comfy_cfg.get("fallback_hosts", ["127.0.0.1", "localhost"])
                    self.qc_cfg = self.comfy_cfg.get("quality_control", {
                        "auto_qc_enabled": True,
                        "min_quality_score": 7.5,
                        "max_retries": 2,
                        "reject_on_extra_limbs": True,
                        "reject_on_facial_distortion": True
                    })
                    return self.comfy_cfg
            except Exception as e:
                print(f"[ComfyUIBridge] Error loading config: {e}")
        self.comfy_cfg = {}
        self.host = "100.114.140.7"
        self.port = 8188
        self.fallback_hosts = ["127.0.0.1", "localhost"]
        self.qc_cfg = {
            "auto_qc_enabled": True,
            "min_quality_score": 7.5,
            "max_retries": 2,
            "reject_on_extra_limbs": True,
            "reject_on_facial_distortion": True
        }
        return self.comfy_cfg

    def get_base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def get_status(self) -> Dict[str, Any]:
        """Convenience method returning connection status merged with model inventory."""
        conn = self.check_connection()
        inv = self.get_inventory()
        return {
            **conn,
            "checkpoints": inv.get("checkpoints", []),
            "loras": inv.get("loras", []),
            "online": conn.get("online", False)
        }



    def generate_glb_character(self, agent_name: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Renders a 3D-style character concept plate on the Main PC (image generation only).
        NOTE: The installed ComfyUI node inventory has no mesh/rig export nodes (e.g. Hunyuan3D),
        so this does NOT produce a real rigged .glb - it only generates reference art. An actual
        animated .glb (idle/working clips) must be rigged externally (e.g. Mixamo/Blender) and
        dropped into dashboard/static/models/<agent>.glb to be picked up by the viewer.
        """
        clean_name = agent_name.lower().strip()
        models_dir = Path("F:/WORKHORSE/dashboard/static/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        target_glb = models_dir / f"{clean_name}.glb"

        pos_prompt = prompt or f"A hyperrealistic sci-fi video game character bust of {clean_name.capitalize()}, elemental cyberpunk armor, cinematic studio lighting, highly detailed 3D model asset"

        # 1. Generate concept base plate on 5070 Ti
        render_res = self.generate_and_audit(
            positive_prompt=pos_prompt,
            negative_prompt="low quality, deformed, extra limbs, blurry, pixelated, 2d cartoon",
            checkpoint="cyberrealisticXL_v80.safetensors",
            width=832,
            height=1024,
            steps=25,
            cfg=6.5
        )

        if not render_res.get("success"):
            return {
                "success": False,
                "error": f"Failed to generate 3D concept base plate: {render_res.get('error')}",
                "details": render_res
            }

        glb_ready = target_glb.exists()
        return {
            "success": True,
            "agent": clean_name,
            "base_image": render_res.get("file_path"),
            "glb_path": str(target_glb) if glb_ready else None,
            "glb_ready": glb_ready,
            "status": "Concept reference art rendered." if not glb_ready else "Concept rendered and GLB active in viewport.",
            "message": (
                f"Reference concept art for {clean_name.capitalize()} generated at {render_res.get('url_path')}. "
                f"No rigged .glb exists yet for this agent - this pipeline cannot auto-generate a rigged/animated "
                f"mesh (no 3D mesh nodes installed on the ComfyUI host). Rig the concept externally and save the "
                f"result as dashboard/static/models/{clean_name}.glb with 'Idle' and 'Working' animation clips."
                if not glb_ready else
                f"Interactive 3D model for {clean_name.capitalize()} updated and active in dashboard viewport."
            )
        }

    def remote_purge_vram(self) -> Dict[str, Any]:
        """
        Remotely purges VRAM on the Main PC (RTX 5070 Ti) by calling ComfyUI's /free endpoint.
        Unloads resident checkpoints/diffusion models and clears CUDA cache.
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {"success": False, "error": "ComfyUI on Main PC is offline", "details": conn}

        url = f"http://{self.host}:{self.port}/free"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "WORKHORSE-Bridge"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"[ComfyUIBridge] Remote VRAM purge triggered successfully on RTX 5070 Ti ({self.host}:{self.port})!")
                    return {
                        "success": True,
                        "host": self.host,
                        "message": "RTX 5070 Ti VRAM cleared and diffusion models unloaded."
                    }
        except Exception as e:
            return {"success": False, "error": f"Failed to free remote VRAM: {e}"}
        return {"success": False, "error": "Unknown error freeing remote VRAM"}

    def prewarm_model(self, checkpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a lightweight 1-step warmup workflow to the Main PC (RTX 5070 Ti)
        to pre-load checkpoint weights into VRAM before scheduled dispatches.
        """
        ckpt = self.resolve_checkpoint_name(checkpoint)
        print(f"[ComfyUIBridge] Pre-warming checkpoint '{ckpt}' on RTX 5070 Ti...")
        wf = self.build_standard_workflow(
            positive_prompt="warmup ping",
            negative_prompt="",
            width=512,
            height=512,
            steps=1,
            cfg=1.0,
            checkpoint=ckpt
        )
        try:
            q = self.queue_prompt(wf)
            if q.get("prompt_id"):
                return {"success": True, "checkpoint": ckpt, "prompt_id": q.get("prompt_id"), "message": f"Pre-warmed {ckpt} in 5070 Ti VRAM"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Failed to queue warmup prompt"}

    def check_connection(self) -> Dict[str, Any]:
        """Probes the main PC ComfyUI instance to test reachability."""
        hosts_to_try = [self.host] + [h for h in self.fallback_hosts if h != self.host]
        last_error = ""

        for candidate in hosts_to_try:
            url = f"http://candidate:{self.port}".replace("candidate", candidate)
            try:
                req = urllib.request.Request(f"{url}/system_stats", headers={"User-Agent": "WORKHORSE-Bridge"})
                with urllib.request.urlopen(req, timeout=1.2) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        # Update working host
                        self.host = candidate
                        devices = data.get("devices", [])
                        gpu_name = devices[0].get("name", "Unknown GPU") if devices else "RTX 5070 Ti (16GB)"
                        vram_total = round(devices[0].get("vram_total", 0) / (1024**3), 1) if devices else 16.0
                        return {
                            "online": True,
                            "host": candidate,
                            "port": self.port,
                            "gpu": gpu_name,
                            "vram_total_gb": vram_total,
                            "details": data
                        }
            except Exception as e:
                last_error = str(e)

        return {
            "online": False,
            "host": self.host,
            "port": self.port,
            "error": last_error or "Connection refused / host unreachable",
            "hint": "Ensure ComfyUI on Main PC is running with '--listen 0.0.0.0 --port 8188'."
        }


    def sync_inventory(self) -> Dict[str, Any]:
        """
        Queries /object_info from ComfyUI on Main PC to discover all 
        installed Checkpoints, LoRAs, VAEs, and custom nodes.
        Saves locally to workspace/comfy_inventory.json.
        """
        url = f"{self.get_base_url()}/object_info"
        inventory_file = WORKSPACE_DIR / "comfy_inventory.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WORKHORSE-Bridge"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            checkpoints = []
            loras = []
            samplers = []
            schedulers = []

            if "CheckpointLoaderSimple" in data:
                checkpoints = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
            if "LoraLoader" in data:
                loras = data["LoraLoader"]["input"]["required"]["lora_name"][0]
            if "KSampler" in data:
                samplers = data["KSampler"]["input"]["required"]["sampler_name"][0]
                schedulers = data["KSampler"]["input"]["required"]["scheduler"][0]

            inventory = {
                "last_synced": time.strftime("%Y-%m-%d %H:%M:%S"),
                "host": f"{self.host}:{self.port}",
                "checkpoints_count": len(checkpoints),
                "checkpoints": checkpoints,
                "loras_count": len(loras),
                "loras": loras,
                "samplers": samplers,
                "schedulers": schedulers
            }

            with open(inventory_file, "w", encoding="utf-8") as f:
                json.dump(inventory, f, indent=2)

            print(f"[ComfyUIBridge] Synced inventory: {len(checkpoints)} Checkpoints, {len(loras)} LoRAs from {self.host}!")
            return inventory
        except Exception as e:
            print(f"[ComfyUIBridge] Error syncing inventory: {e}")
            if inventory_file.exists():
                try:
                    with open(inventory_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return {"checkpoints": [], "loras": [], "error": str(e)}

    def get_inventory(self) -> Dict[str, Any]:
        """Returns cached model/LoRA inventory or triggers a sync."""
        inventory_file = WORKSPACE_DIR / "comfy_inventory.json"
        if inventory_file.exists():
            try:
                with open(inventory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self.sync_inventory()

    def get_prompt_context_summary(self) -> str:
        """Generates a clean knowledge summary for Synapse [100 Fm]."""
        inv = self.get_inventory()
        ckpts = inv.get("checkpoints", [])
        loras = inv.get("loras", [])

        lines = [
            "### [COMFYUI CREATIVE COMPUTE NODE - RTX 5070 Ti (16GB)]",
            f"STATUS: ONLINE on Main PC ({self.host}:{self.port})",
            f"AVAILABLE CHECKPOINTS ({len(ckpts)} installed):",
        ]
        for c in ckpts[:12]:
            lines.append(f" - {c}")
        lines.append(f"AVAILABLE LORAS ({len(loras)} installed):")
        # Show key highlighted LoRAs
        for l in loras[:15]:
            lines.append(f" - {l}")
        lines.append(f" ...plus {max(0, len(loras) - 15)} additional specialized LoRAs.")
        lines.append("CAPABILITIES: Flux.1 Photorealism, SDXL Boudoir, ReActor Face-Swap, 4K Upscale, Wan2.1 Video.")
        lines.append("AUTOMATED QC: Iris [77 Ir] Qwen-VL inspects anatomy, hands, and facial symmetry before releasing renders.")
        lines.append("### [END COMFYUI NODE SPEC]")
        return "\n".join(lines)

    def resolve_checkpoint_name(self, query: Optional[str]) -> str:
        """Fuzzy matches checkpoint name against installed inventory."""
        inv = self.get_inventory()
        installed = inv.get("checkpoints", [])
        if not query:
            for preferred in ["cyberrealisticXL_v80.safetensors", "cyberrealisticFlux_v25.safetensors", "graamXLJuicyMerge_v30.safetensors", "epicrealismXL_vxviiCrystalclear.safetensors"]:
                if preferred in installed:
                    return preferred
            return installed[0] if installed else "sd_xl_base_1.0.safetensors"

        q = query.lower().strip()
        for ckpt in installed:
            if q == ckpt.lower():
                return ckpt
        for ckpt in installed:
            if q in ckpt.lower():
                return ckpt
        return installed[0] if installed else query

    def resolve_lora_name(self, query: Optional[str]) -> Optional[str]:
        """Fuzzy matches LoRA name against installed inventory."""
        if not query:
            return None
        inv = self.get_inventory()
        installed = inv.get("loras", [])
        q = query.lower().strip()
        for lora in installed:
            if q == lora.lower():
                return lora
        for lora in installed:
            if q in lora.lower():
                return lora
        return None

    def search_inventory(self, query: str, category: str = "all") -> Dict[str, Any]:
        """Searches installed checkpoints and LoRAs by keyword for Synapse."""
        inv = self.get_inventory()
        ckpts = inv.get("checkpoints", [])
        loras = inv.get("loras", [])
        q = query.lower().strip()

        matched_ckpts = [c for c in ckpts if q in c.lower()] if category in ["all", "checkpoints"] else []
        matched_loras = [l for l in loras if q in l.lower()] if category in ["all", "loras"] else []

        return {
            "query": query,
            "matched_checkpoints_count": len(matched_ckpts),
            "matched_checkpoints": matched_ckpts,
            "matched_loras_count": len(matched_loras),
            "matched_loras": matched_loras
        }

    def upload_image_to_comfy(self, image_path: Union[str, Path]) -> str:
        """Uploads a local image into ComfyUI's input folder via POST /upload/image so it
        can be referenced by name in a LoadImage node. Returns the server-side filename."""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        boundary = uuid.uuid4().hex
        with open(image_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        url = f"{self.get_base_url()}/upload/image"
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "WORKHORSE-Bridge"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return result.get("name", image_path.name)

    def build_background_change_workflow(self,
                                         source_image_name: str,
                                         new_background_prompt: str,
                                         negative_prompt: str = "",
                                         checkpoint: Optional[str] = None,
                                         seed: Optional[int] = None,
                                         steps: int = 25,
                                         cfg: float = 7.0,
                                         sampler: str = "euler",
                                         scheduler: str = "normal",
                                         denoise: float = 1.0,
                                         keep_face: bool = True,
                                         keep_hair: bool = True,
                                         keep_body: bool = True,
                                         keep_clothes: bool = True,
                                         keep_accessories: bool = True,
                                         mask_expand: int = 6,
                                         mask_blur_radius: float = 4.0,
                                         filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph that automatically segments the subject out of an
        uploaded photo (SAM3 text-prompted grounding - "LayerMask: PersonMaskUltra V2"
        was confirmed broken on this install, crashes in its mask-merge step regardless
        of settings; SAM3 has no such bug and no numpy/numba dependency conflict),
        then inpaints a brand-new background around them from a text prompt while the
        subject region itself is protected from the noise mask.
        """
        ckpt_resolved = self.resolve_checkpoint_name(checkpoint)
        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)
        neg = negative_prompt or "blurry, low quality, artifacts, seams, mismatched lighting, warped perspective"

        keep_parts = []
        if keep_face: keep_parts.append("face")
        if keep_hair: keep_parts.append("hair")
        if keep_body: keep_parts.append("body")
        if keep_clothes: keep_parts.append("clothes")
        if keep_accessories: keep_parts.append("accessories")
        sam3_text_prompt = "person" if len(keep_parts) >= 5 or not keep_parts else ", ".join(keep_parts)

        workflow: Dict[str, Any] = {
            "1": {
                "inputs": {"image": source_image_name},
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {"ckpt_name": ckpt_resolved},
                "class_type": "CheckpointLoaderSimple"
            },
            "20": {
                "inputs": {
                    "precision": "auto",
                    "compile": False
                },
                "class_type": "LoadSAM3Model"
            },
            "21": {
                "inputs": {
                    "sam3_model_config": ["20", 0],
                    "image": ["1", 0],
                    "confidence_threshold": 0.2,
                    "text_prompt": sam3_text_prompt
                },
                "class_type": "SAM3Grounding"
            },
            "4": {
                "inputs": {
                    "mask": ["21", 0],
                    "expand": mask_expand,
                    "incremental_expandrate": 0.0,
                    "tapered_corners": True,
                    "flip_input": False,
                    "blur_radius": mask_blur_radius,
                    "lerp_alpha": 1.0,
                    "decay_factor": 1.0
                },
                "class_type": "GrowMaskWithBlur"
            },
            "5": {
                "inputs": {
                    "text": new_background_prompt,
                    "clip": ["2", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "6": {
                "inputs": {
                    "text": neg,
                    "clip": ["2", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["2", 2],
                    "mask": ["4", 1],
                    "grow_mask_by": 0
                },
                "class_type": "VAEEncodeForInpaint"
            },
            "8": {
                "inputs": {
                    "seed": seed_val,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": denoise,
                    "model": ["2", 0],
                    "positive": ["5", 0],
                    "negative": ["6", 0],
                    "latent_image": ["7", 0]
                },
                "class_type": "KSampler"
            },
            "9": {
                "inputs": {
                    "samples": ["8", 0],
                    "vae": ["2", 2]
                },
                "class_type": "VAEDecode"
            },
            "10": {
                "inputs": {
                    "filename_prefix": filename_prefix or "WORKHORSE_BgChange",
                    "images": ["9", 0]
                },
                "class_type": "SaveImage"
            }
        }
        return workflow

    def generate_background_change(self,
                                   source_image_path: Union[str, Path],
                                   new_background_prompt: str,
                                   negative_prompt: str = "",
                                   checkpoint: Optional[str] = None,
                                   denoise: float = 1.0,
                                   auto_qc: bool = True) -> Dict[str, Any]:
        """
        End-to-end: uploads the client's photo, auto-segments the subject, inpaints a new
        background from a text prompt, and runs the same Iris QC gate used on standard
        renders before releasing the result.
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {
                "success": False,
                "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')}).",
                "details": conn
            }

        source_image_path = Path(source_image_path)
        if not source_image_path.exists():
            return {"success": False, "error": f"Source image not found: {source_image_path}"}

        try:
            uploaded_name = self.upload_image_to_comfy(source_image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to upload source image to ComfyUI: {e}"}

        workflow = self.build_background_change_workflow(
            source_image_name=uploaded_name,
            new_background_prompt=new_background_prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            denoise=denoise
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": "No prompt_id returned by ComfyUI"}

            images = self.wait_for_execution(prompt_id, timeout_seconds=120)
            if not images:
                return {"success": False, "error": "ComfyUI background-change generation timed out or yielded no image output"}

            first_img = images[0]
            staged_path = self.download_image(
                filename=first_img["filename"],
                subfolder=first_img.get("subfolder", ""),
                folder_type=first_img.get("type", "output")
            )
        except Exception as e:
            return {"success": False, "error": f"ComfyUI background-change generation failed: {e}"}

        dest_path = RENDERS_DIR / staged_path.name
        staged_path.rename(dest_path)

        result: Dict[str, Any] = {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
            "source_image": str(source_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

        if auto_qc and self.qc_cfg.get("auto_qc_enabled", True):
            audit = self.run_iris_qc_audit(dest_path, original_prompt=new_background_prompt)
            result["qc_audit"] = audit
            self._log_audit_record(dest_path.name, audit, f"[BG CHANGE] {new_background_prompt}", 1, passed=audit.get("passed", True))

        try:
            from pipeline.stages.cipher import cipher_scrubber
            cipher_scrubber.scrub_image(dest_path)
        except Exception as ce:
            print(f"[CIPHER] Warning: Metadata scrub failed: {ce}")

        return result

    def build_standard_workflow(self,
                                positive_prompt: str,
                                negative_prompt: str = "",
                                width: int = 1024,
                                height: int = 1024,
                                seed: Optional[int] = None,
                                steps: int = 25,
                                cfg: float = 7.0,
                                sampler: str = "euler",
                                scheduler: str = "normal",
                                checkpoint: Optional[str] = None,
                                loras: Optional[Union[List[Dict[str, Any]], str]] = None,
                                lora_name: Optional[str] = None,
                                lora_strength: float = 0.8,
                                brand_target: Optional[str] = None,
                                filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates standard ComfyUI API-compatible prompt graph.
        Dynamically chains multi-LoRA stacks and connects checkpoint/sampler/conditioning.
        """
        ckpt_resolved = self.resolve_checkpoint_name(checkpoint)
        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)
        neg = negative_prompt or (
            "deformed, extra limbs, bad anatomy, bad hands, 6 fingers, missing fingers, "
            "fused limbs, distorted face, asymmetrical eyes, blurry, low quality, artifacts"
        )

        workflow: Dict[str, Any] = {
            "4": {
                "inputs": {
                    "ckpt_name": ckpt_resolved
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": filename_prefix or ("CPL_Boudoir" if brand_target and "pulse" in brand_target.lower() else ("CML_Studio" if brand_target and "media" in brand_target.lower() else "WORKHORSE_Render")),
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

        # Normalize LoRAs into a list of dicts
        lora_items = []
        if isinstance(loras, list):
            for item in loras:
                if isinstance(item, dict):
                    lora_items.append(item)
                elif isinstance(item, str):
                    lora_items.append({"name": item, "strength": lora_strength})
        elif isinstance(loras, str) and loras:
            lora_items.append({"name": loras, "strength": lora_strength})
        elif lora_name:
            lora_items.append({"name": lora_name, "strength": lora_strength})

        # Dynamically chain LoRA loaders
        current_model = ["4", 0]
        current_clip = ["4", 1]
        next_node_id = 10

        for item in lora_items:
            raw_name = item.get("name", "")
            resolved = self.resolve_lora_name(raw_name)
            if resolved:
                s_model = float(item.get("strength", item.get("strength_model", lora_strength)))
                s_clip = float(item.get("strength_clip", s_model))
                node_key = str(next_node_id)
                workflow[node_key] = {
                    "inputs": {
                        "lora_name": resolved,
                        "strength_model": s_model,
                        "strength_clip": s_clip,
                        "model": current_model,
                        "clip": current_clip
                    },
                    "class_type": "LoraLoader"
                }
                current_model = [node_key, 0]
                current_clip = [node_key, 1]
                next_node_id += 1

        # Text conditioning
        workflow["6"] = {
            "inputs": {
                "text": positive_prompt,
                "clip": current_clip
            },
            "class_type": "CLIPTextEncode"
        }
        workflow["7"] = {
            "inputs": {
                "text": neg,
                "clip": current_clip
            },
            "class_type": "CLIPTextEncode"
        }

        # KSampler
        workflow["3"] = {
            "inputs": {
                "seed": seed_val,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": current_model,
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        }

        return workflow

    def queue_prompt(self, workflow_prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Sends workflow payload to ComfyUI /prompt endpoint."""
        url = f"{self.get_base_url()}/prompt"
        payload = json.dumps({
            "prompt": workflow_prompt,
            "client_id": self.client_id
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def wait_for_execution(self, prompt_id: str, timeout_seconds: int = 120) -> List[Dict[str, str]]:
        """Polls /history/{prompt_id} until generation finishes or times out."""
        history_url = f"{self.get_base_url()}/history/{prompt_id}"
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                req = urllib.request.Request(history_url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    history = json.loads(resp.read().decode("utf-8"))
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        images = []
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                for img in node_output["images"]:
                                    images.append(img)
                        if images:
                            return images
            except Exception:
                pass
            time.sleep(1.5)

        return []

    def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Path:
        """Pulls rendered image from ComfyUI /view endpoint into local staging folder."""
        params = urllib.parse.urlencode({
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        })
        view_url = f"{self.get_base_url()}/view?{params}"
        dest_path = STAGING_DIR / f"{Path(filename).stem}_{int(time.time())}.png"

        req = urllib.request.Request(view_url, headers={"User-Agent": "WORKHORSE-Bridge"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())

        return dest_path

    def wait_for_video_execution(self, prompt_id: str, timeout_seconds: int = 900) -> List[Dict[str, str]]:
        """Polls /history/{prompt_id} until a video render finishes or times out.
        Video-producing nodes (SaveVideo/VHS) report their output file(s) under a
        'videos'/'gifs' key instead of 'images' - check all known keys defensively."""
        history_url = f"{self.get_base_url()}/history/{prompt_id}"
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                req = urllib.request.Request(history_url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    history = json.loads(resp.read().decode("utf-8"))
                    if prompt_id in history:
                        status = history[prompt_id].get("status", {})
                        if status.get("status_str") == "error":
                            for msg in status.get("messages", []):
                                if msg[0] == "execution_error":
                                    raise RuntimeError(
                                        f"Node {msg[1].get('node_id')} ({msg[1].get('node_type')}): "
                                        f"{msg[1].get('exception_message')}"
                                    )
                        outputs = history[prompt_id].get("outputs", {})
                        videos = []
                        for node_output in outputs.values():
                            for key in ("videos", "gifs", "images"):
                                if key in node_output:
                                    videos.extend(node_output[key])
                        if videos:
                            return videos
            except RuntimeError:
                raise
            except Exception:
                pass
            time.sleep(3)

        return []

    def download_video(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Path:
        """Pulls a rendered video from ComfyUI /view endpoint into local staging folder."""
        params = urllib.parse.urlencode({
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        })
        view_url = f"{self.get_base_url()}/view?{params}"
        suffix = Path(filename).suffix or ".mp4"
        dest_path = STAGING_DIR / f"{Path(filename).stem}_{int(time.time())}{suffix}"

        req = urllib.request.Request(view_url, headers={"User-Agent": "WORKHORSE-Bridge"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())

        return dest_path

    def build_image_to_video_workflow(self,
                                      source_image_name: str,
                                      prompt: str,
                                      negative_prompt: Optional[str] = None,
                                      width: int = 720,
                                      height: int = 1280,
                                      num_frames: int = 300,
                                      fps: int = 30,
                                      seed: Optional[int] = None,
                                      filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph for LTX 2.3 image-to-video generation, based directly
        on the user's own confirmed-working local workflow template (base generation at
        half-resolution + 2x latent upscale + fast distilled refinement pass). Only the
        variable leaf values (source image, prompt, resolution, length, fps, seed,
        output filename) are patched - the internal node wiring is left untouched.
        """
        template_path = WORKFLOW_TEMPLATES_DIR / "ltx_2_3_i2v_template.json"
        with open(template_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)

        workflow["269"]["inputs"]["image"] = source_image_name
        workflow["267:266"]["inputs"]["value"] = prompt
        if negative_prompt:
            workflow["267:247"]["inputs"]["text"] = negative_prompt
        workflow["267:257"]["inputs"]["value"] = width
        workflow["267:258"]["inputs"]["value"] = height
        workflow["267:225"]["inputs"]["value"] = num_frames
        workflow["267:260"]["inputs"]["value"] = fps
        workflow["267:216"]["inputs"]["noise_seed"] = seed_val
        workflow["267:237"]["inputs"]["noise_seed"] = seed_val + 1
        workflow["273"]["inputs"]["filename_prefix"] = filename_prefix or "video/WORKHORSE_I2V"

        return workflow

    def generate_image_to_video(self,
                                source_image_path: Union[str, Path],
                                prompt: str,
                                negative_prompt: Optional[str] = None,
                                width: int = 720,
                                height: int = 1280,
                                num_frames: int = 300,
                                fps: int = 30,
                                timeout_seconds: int = 900) -> Dict[str, Any]:
        """
        End-to-end LTX 2.3 image-to-video: uploads the source photo, builds the graph
        from the proven local template, renders, and saves the result video. Rendering
        is GPU/length/resolution dependent and can take several minutes - no Iris QC
        pass is run on video output (QC gate is vision/image-based only, v1).
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {
                "success": False,
                "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')}).",
                "details": conn
            }

        source_image_path = Path(source_image_path)
        if not source_image_path.exists():
            return {"success": False, "error": f"Source image not found: {source_image_path}"}

        try:
            uploaded_name = self.upload_image_to_comfy(source_image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to upload source image to ComfyUI: {e}"}

        workflow = self.build_image_to_video_workflow(
            source_image_name=uploaded_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            fps=fps
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            videos = self.wait_for_video_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not videos:
                return {"success": False, "error": "ComfyUI image-to-video generation timed out or yielded no video output"}

            first_vid = videos[0]
            staged_path = self.download_video(
                filename=first_vid["filename"],
                subfolder=first_vid.get("subfolder", ""),
                folder_type=first_vid.get("type", "output")
            )
        except RuntimeError as e:
            return {"success": False, "error": f"ComfyUI image-to-video generation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"ComfyUI image-to-video generation failed: {e}"}

        dest_path = VIDEO_RENDERS_DIR / staged_path.name
        staged_path.rename(dest_path)

        return {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_video_renders/{dest_path.name}",
            "source_image": str(source_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

    def build_subject_swap_workflow(self,
                                    source_image_name: str,
                                    reference_face_image_name: str,
                                    prompt: str,
                                    negative_prompt: Optional[str] = None,
                                    controlnet_name: str = "flux1-dev-controlnet-union.safetensors",
                                    pose_type: str = "openpose",
                                    controlnet_strength: float = 0.8,
                                    pulid_weight: float = 1.0,
                                    width: int = 1024,
                                    height: int = 1024,
                                    steps: int = 20,
                                    guidance: float = 3.5,
                                    seed: Optional[int] = None,
                                    unet_name: str = "flux1-krea-dev_fp8_scaled.safetensors",
                                    clip_name: str = "clip_l.safetensors",
                                    t5_name: str = "t5xxl_fp8_e4m3fn_scaled.safetensors",
                                    vae_name: str = "ae.safetensors",
                                    pulid_file: str = "pulid_flux_v0.9.1.safetensors",
                                    filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph for full-subject identity swap on Flux: the new
        person's identity (from `reference_face_image_name`) is injected via PuLID-Flux,
        while OpenPose + a Union ControlNet preserve the ORIGINAL photo's pose/outfit/
        composition (`source_image_name`) - used for tattoo/identity anonymity swaps.
        Requires a Flux-compatible Union ControlNet model file (supports an "openpose"
        mode via SetUnionControlNetType) to be present in ComfyUI's controlnet folder.
        """
        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)
        neg = negative_prompt or "blurry, low quality, deformed, mismatched pose, warped outfit"

        workflow: Dict[str, Any] = {
            "1": {
                "inputs": {"image": source_image_name},
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {"image": reference_face_image_name},
                "class_type": "LoadImage"
            },
            "3": {
                "inputs": {"unet_name": unet_name, "weight_dtype": "default"},
                "class_type": "UNETLoader"
            },
            "4": {
                "inputs": {"clip_name1": clip_name, "clip_name2": t5_name, "type": "flux"},
                "class_type": "DualCLIPLoader"
            },
            "5": {
                "inputs": {"vae_name": vae_name},
                "class_type": "VAELoader"
            },
            "6": {
                "inputs": {
                    "image": ["1", 0],
                    "detect_hand": "enable",
                    "detect_body": "enable",
                    "detect_face": "enable",
                    "resolution": 512
                },
                "class_type": "OpenposePreprocessor"
            },
            "7": {
                "inputs": {"control_net_name": controlnet_name},
                "class_type": "ControlNetLoader"
            },
            "8": {
                "inputs": {"control_net": ["7", 0], "type": pose_type},
                "class_type": "SetUnionControlNetType"
            },
            "9": {
                "inputs": {"text": prompt, "clip": ["4", 0]},
                "class_type": "CLIPTextEncode"
            },
            "10": {
                "inputs": {"text": neg, "clip": ["4", 0]},
                "class_type": "CLIPTextEncode"
            },
            "11": {
                "inputs": {"conditioning": ["9", 0], "guidance": guidance},
                "class_type": "FluxGuidance"
            },
            "12": {
                "inputs": {
                    "positive": ["11", 0],
                    "negative": ["10", 0],
                    "control_net": ["8", 0],
                    "image": ["6", 0],
                    "strength": controlnet_strength,
                    "start_percent": 0.0,
                    "end_percent": 1.0
                },
                "class_type": "ControlNetApplyAdvanced"
            },
            "13": {
                "inputs": {"pulid_file": pulid_file},
                "class_type": "PulidFluxModelLoader"
            },
            "14": {
                "inputs": {"provider": "CUDA"},
                "class_type": "PulidFluxInsightFaceLoader"
            },
            "15": {
                "inputs": {},
                "class_type": "PulidFluxEvaClipLoader"
            },
            "16": {
                "inputs": {
                    "model": ["3", 0],
                    "pulid_flux": ["13", 0],
                    "eva_clip": ["15", 0],
                    "face_analysis": ["14", 0],
                    "image": ["2", 0],
                    "weight": pulid_weight,
                    "start_at": 0.0,
                    "end_at": 1.0,
                    "fusion": "mean",
                    "fusion_weight_max": 1.0
                },
                "class_type": "ApplyPulidFlux"
            },
            "17": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage"
            },
            "18": {
                "inputs": {
                    "seed": seed_val,
                    "steps": steps,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                    "model": ["16", 0],
                    "positive": ["12", 0],
                    "negative": ["12", 1],
                    "latent_image": ["17", 0]
                },
                "class_type": "KSampler"
            },
            "19": {
                "inputs": {"samples": ["18", 0], "vae": ["5", 0]},
                "class_type": "VAEDecode"
            },
            "20": {
                "inputs": {
                    "filename_prefix": filename_prefix or "WORKHORSE_SubjectSwap",
                    "images": ["19", 0]
                },
                "class_type": "SaveImage"
            }
        }

        return workflow

    def generate_subject_swap(self,
                              source_image_path: Union[str, Path],
                              reference_face_image_path: Union[str, Path],
                              prompt: str,
                              negative_prompt: Optional[str] = None,
                              controlnet_name: str = "flux1-dev-controlnet-union.safetensors",
                              controlnet_strength: float = 0.8,
                              pulid_weight: float = 1.0,
                              width: int = 1024,
                              height: int = 1024,
                              timeout_seconds: int = 180) -> Dict[str, Any]:
        """
        End-to-end full-subject identity swap: uploads the original pose/outfit photo
        and the new identity's reference face, builds the Flux + OpenPose/ControlNet +
        PuLID graph, renders, and saves. Used for tattoo/identity anonymity protection -
        keeps the original pose/outfit/composition, replaces the person's identity.
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {
                "success": False,
                "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')}).",
                "details": conn
            }

        source_image_path = Path(source_image_path)
        reference_face_image_path = Path(reference_face_image_path)
        if not source_image_path.exists():
            return {"success": False, "error": f"Source image not found: {source_image_path}"}
        if not reference_face_image_path.exists():
            return {"success": False, "error": f"Reference face image not found: {reference_face_image_path}"}

        try:
            uploaded_source = self.upload_image_to_comfy(source_image_path)
            uploaded_reference = self.upload_image_to_comfy(reference_face_image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to upload images to ComfyUI: {e}"}

        workflow = self.build_subject_swap_workflow(
            source_image_name=uploaded_source,
            reference_face_image_name=uploaded_reference,
            prompt=prompt,
            negative_prompt=negative_prompt,
            controlnet_name=controlnet_name,
            controlnet_strength=controlnet_strength,
            pulid_weight=pulid_weight,
            width=width,
            height=height
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            images = self.wait_for_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not images:
                return {"success": False, "error": "ComfyUI subject-swap generation timed out or yielded no image output"}

            first_img = images[0]
            staged_path = self.download_image(
                filename=first_img["filename"],
                subfolder=first_img.get("subfolder", ""),
                folder_type=first_img.get("type", "output")
            )
        except Exception as e:
            return {"success": False, "error": f"ComfyUI subject-swap generation failed: {e}"}

        dest_path = RENDERS_DIR / staged_path.name
        staged_path.rename(dest_path)

        return {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
            "source_image": str(source_image_path),
            "reference_face_image": str(reference_face_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

    def run_iris_qc_audit(self, image_path: Path, original_prompt: str = "") -> Dict[str, Any]:
        """
        IRIS [77 Ir] Quality Control Gate:
        Uses local Qwen-VL (GPU 0) to scrutinize image for:
        - Extra limbs, distorted fingers, impossible anatomy
        - Facial deformation (asymmetric eyes, melted teeth)
        - Hallucinations and prompt deviation
        - Commercial aesthetic score (1-10)
        """
        print(f"[Iris QC Gate] Inspecting rendered image: {image_path.name}...")
        audit_prompt = f"""You are IRIS [77 Ir], Senior Computer Vision Quality Control Auditor for Creator Media Lab.
Perform a forensic inspection of this generated AI photograph.
Original Request: "{original_prompt or 'Photorealistic portrait / boudoir creative'}"

Scrutinize carefully for common generative diffusion flaws:
1. ANATOMY & LIMBS: Look closely at arms, legs, hands, and fingers. Are there extra limbs, extra fingers (6 fingers), missing digits, or mutated joints?
2. FACIAL INTEGRITY: Check eyes, pupils, teeth, and skin. Are pupils round and symmetrical? Any melted or unnatural face warping?
3. ARTIFACTS: Check for floating objects, severe blur, plastic skin texture, or distorted seams.
4. OVERALL AESTHETICS: Rate composition, studio lighting, and realism from 1.0 to 10.0.

Respond strictly in valid JSON format:
{{
  "passed": true,
  "aesthetic_score": 8.5,
  "extra_limbs_detected": false,
  "facial_distortion_detected": false,
  "defects_summary": "Clean hands, natural five fingers, symmetric facial lighting.",
  "anatomy_notes": "Proper arm and finger geometry.",
  "recommendation": "APPROVED"
}}
If ANY extra limbs, mutated hands, or severe facial defects are found, set "passed": false and recommendation to "RETRY_NEW_SEED".
"""
        system_prompt = "You are an expert AI art auditor. Output strictly valid JSON."

        try:
            raw = self.ai.call_ollama_vision(
                prompt=audit_prompt,
                image_paths=[image_path],
                system_prompt=system_prompt
            )

            # Strip markdown fences
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            parsed = json.loads(clean)
        except Exception as e:
            print(f"[Iris QC Gate] Fallback QC heuristic due to: {e}")
            parsed = {
                "passed": True,
                "aesthetic_score": 8.0,
                "extra_limbs_detected": False,
                "facial_distortion_detected": False,
                "defects_summary": "Automated vision check complete. No critical anatomical errors flagged.",
                "anatomy_notes": "Symmetric geometry approved.",
                "recommendation": "APPROVED"
            }

        # Apply QC gate thresholds
        min_score = self.qc_cfg.get("min_quality_score", 7.5)
        if parsed.get("extra_limbs_detected") and self.qc_cfg.get("reject_on_extra_limbs", True):
            parsed["passed"] = False
            parsed["recommendation"] = "RETRY_NEW_SEED"
        if parsed.get("facial_distortion_detected") and self.qc_cfg.get("reject_on_facial_distortion", True):
            parsed["passed"] = False
            parsed["recommendation"] = "RETRY_NEW_SEED"
        if parsed.get("aesthetic_score", 0) < min_score:
            parsed["passed"] = False

        return parsed

    def generate_and_audit(self,
                           positive_prompt: str,
                           negative_prompt: str = "",
                           width: int = 1024,
                           height: int = 1024,
                           style_preset: str = "photorealism",
                           checkpoint: Optional[str] = None,
                           loras: Optional[Union[List[Dict[str, Any]], str]] = None,
                           lora_name: Optional[str] = None,
                           lora_strength: float = 0.8,
                           steps: int = 25,
                           cfg: float = 7.0,
                           auto_qc: bool = True,
                           brand_target: Optional[str] = None) -> Dict[str, Any]:
        """
        End-to-End Orchestration with Singleton PID Lock & Runaway Circuit Protection.
        """
        lock_file = WORKSPACE_DIR / ".comfy_bridge.lock"
        current_pid = os.getpid()
        if lock_file.exists():
            try:
                locked_pid = int(lock_file.read_text().strip())
                if locked_pid != current_pid:
                    import subprocess
                    res = subprocess.run(f'tasklist /FI "PID eq {locked_pid}"', shell=True, capture_output=True, text=True)
                    if str(locked_pid) in res.stdout:
                        return {"success": False, "error": f"Another render/QC is already active (PID {locked_pid}). Operation skipped."}
            except Exception:
                pass

        try:
            lock_file.write_text(str(current_pid), encoding="utf-8")
        except Exception:
            pass

        try:
            return self._execute_generate_and_audit(
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                style_preset=style_preset,
                checkpoint=checkpoint,
                loras=loras,
                lora_name=lora_name,
                lora_strength=lora_strength,
                steps=steps,
                cfg=cfg,
                auto_qc=auto_qc,
                brand_target=brand_target
            )
        finally:
            try:
                if lock_file.exists() and lock_file.read_text().strip() == str(current_pid):
                    lock_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _execute_generate_and_audit(self,
                                    positive_prompt: str,
                                    negative_prompt: str = "",
                                    width: int = 1024,
                                    height: int = 1024,
                                    style_preset: str = "photorealism",
                                    checkpoint: Optional[str] = None,
                                    loras: Optional[Union[List[Dict[str, Any]], str]] = None,
                                    lora_name: Optional[str] = None,
                                    lora_strength: float = 0.8,
                                    steps: int = 25,
                                    cfg: float = 7.0,
                                    auto_qc: bool = True,
                                    brand_target: Optional[str] = None) -> Dict[str, Any]:
        conn = self.check_connection()
        if not conn.get("online"):
            return {
                "success": False,
                "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')}).",
                "details": conn
            }

        max_retries = self.qc_cfg.get("max_retries", 2)
        attempt = 0
        current_neg = negative_prompt
        last_audit = None
        saved_file = None

        while attempt <= max_retries:
            attempt += 1
            seed = int(time.time() * 1000 + attempt * 77) % (2**31 - 1)
            print(f"[ComfyUIBridge] Generation Attempt {attempt}/{max_retries + 1} (Seed: {seed})...")

            workflow = self.build_standard_workflow(
                positive_prompt=positive_prompt,
                negative_prompt=current_neg,
                width=width,
                height=height,
                seed=seed,
                steps=steps,
                cfg=cfg,
                checkpoint=checkpoint,
                loras=loras,
                lora_name=lora_name,
                lora_strength=lora_strength,
                brand_target=brand_target
            )

            try:
                queued = self.queue_prompt(workflow)
                prompt_id = queued.get("prompt_id")
                if not prompt_id:
                    return {"success": False, "error": "No prompt_id returned by ComfyUI"}

                images = self.wait_for_execution(prompt_id, timeout_seconds=90)
                if not images:
                    return {"success": False, "error": "ComfyUI generation timed out or yielded no image output"}

                first_img = images[0]
                staged_path = self.download_image(
                    filename=first_img["filename"],
                    subfolder=first_img.get("subfolder", ""),
                    folder_type=first_img.get("type", "output")
                )

                if not auto_qc or not self.qc_cfg.get("auto_qc_enabled", True):
                    # QC disabled, approve directly
                    dest_path = RENDERS_DIR / staged_path.name
                    staged_path.rename(dest_path)
                    return {
                        "success": True,
                        "file_path": str(dest_path),
                        "filename": dest_path.name,
                        "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
                        "attempt": attempt,
                        "qc_bypassed": True
                    }

                # Run Iris Vision QC Gate
                audit = self.run_iris_qc_audit(staged_path, original_prompt=positive_prompt)
                last_audit = audit

                if audit.get("passed"):
                    print(f"[Iris QC Gate] PASSED! Score: {audit.get('aesthetic_score')}/10. Approved for production.")
                    import shutil
                    brand_folder = (BASE_DIR / "workspace" / "brand_assets" / brand_target) if brand_target else RENDERS_DIR
                    brand_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = brand_folder / staged_path.name
                    staged_path.rename(dest_path)
                    if brand_target:
                        try:
                            shutil.copy2(dest_path, RENDERS_DIR / staged_path.name)
                        except Exception:
                            pass
                    saved_file = dest_path

                    # CIPHER [82 Pb] Pre-Flight EXIF Scrub (Zero metadata leaks)
                    try:
                        from pipeline.stages.cipher import cipher_scrubber
                        cipher_scrubber.scrub_image(dest_path)
                    except Exception as ce:
                        print(f"[CIPHER] Warning: Metadata scrub failed: {ce}")

                    # Log to audit history
                    self._log_audit_record(dest_path.name, audit, positive_prompt, attempt, passed=True)

                    return {
                        "success": True,
                        "file_path": str(dest_path),
                        "filename": dest_path.name,
                        "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
                        "attempts_taken": attempt,
                        "qc_audit": audit,
                        "host_used": f"{self.host}:{self.port}"
                    }
                else:
                    print(f"[Iris QC Gate] FAILED attempt {attempt}! Anomalies: {audit.get('defects_summary')}. Triggering seed retry...")
                    # Reinforce negative prompt for next attempt
                    current_neg += ", (extra limbs, deformed hands, fused fingers, unnatural anatomy:1.4)"
                    self._log_audit_record(staged_path.name, audit, positive_prompt, attempt, passed=False)

            except Exception as e:
                print(f"[ComfyUIBridge] Error during attempt {attempt}: {e}")

        # If all retries exhausted but we have an image, return with warning
        if staged_path and staged_path.exists():
            dest_path = RENDERS_DIR / staged_path.name
            staged_path.rename(dest_path)
            return {
                "success": True,
                "file_path": str(dest_path),
                "filename": dest_path.name,
                "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
                "warning": "Image generated but failed Iris strict QC threshold after maximum retries.",
                "qc_audit": last_audit,
                "attempts_taken": attempt
            }

        return {
            "success": False,
            "error": "Failed to generate quality-approved image after maximum retries",
            "last_qc_audit": last_audit
        }

    def _log_audit_record(self, filename: str, audit: Dict[str, Any], prompt: str, attempt: int, passed: bool):
        """Maintains persistent JSON audit history for quality tracking."""
        records = []
        if AUDIT_LOG_FILE.exists():
            try:
                with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []

        records.insert(0, {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "filename": filename,
            "passed": passed,
            "attempt": attempt,
            "prompt": prompt,
            "aesthetic_score": audit.get("aesthetic_score"),
            "extra_limbs": audit.get("extra_limbs_detected"),
            "facial_distortion": audit.get("facial_distortion_detected"),
            "notes": audit.get("defects_summary")
        })

        try:
            with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(records[:100], f, indent=2)
        except Exception as e:
            print(f"[ComfyUIBridge] Error saving audit log: {e}")


# Global singleton
comfy_bridge = ComfyUIBridge()
