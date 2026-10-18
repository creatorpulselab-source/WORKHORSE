import os
import sys
import json
import time
import uuid
import math
import random
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

sys.path.insert(0, "F:/WORKHORSE")
from shared.ai_providers import AIProviderService
from shared.comfyui_knowledge import get_comfyui_context

BASE_DIR = Path("F:/WORKHORSE")
CONFIG_FILE = Path("F:/WORKHORSE/config.json")
WORKSPACE_DIR = Path("F:/WORKHORSE/workspace")
STAGING_DIR = WORKSPACE_DIR / "comfy_staging"
RENDERS_DIR = WORKSPACE_DIR / "brand_assets" / "comfy_renders"
VIDEO_RENDERS_DIR = WORKSPACE_DIR / "brand_assets" / "comfy_video_renders"
PBR_3D_RENDERS_DIR = WORKSPACE_DIR / "brand_assets" / "comfy_3d_pbr_renders"
AUDIT_LOG_FILE = WORKSPACE_DIR / "comfy_qc_audit.json"
WORKFLOW_TEMPLATES_DIR = BASE_DIR / "pipeline" / "stages" / "workflow_templates"

STAGING_DIR.mkdir(parents=True, exist_ok=True)
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
PBR_3D_RENDERS_DIR.mkdir(parents=True, exist_ok=True)

# Client-specific character LoRA generation workflows (flux_dev + a trained identity LoRA
# per client, provided and pre-tested by the Commander himself in ComfyUI - submitted
# exactly as exported, no node changes). CLIENT_CHARACTER_RENDERS_DIR is deliberately
# separate from brand_assets/comfy_renders (the marketing/postable content folder) and
# from client_inbox (customer-uploaded files) - these are the Commander's own test
# generations of his clients' licensed likenesses, and must never be mistaken for
# postable content, swept into Herald's posting pipeline, or mixed between clients.
# Gated behind explicit Adult Mode authorization in ai_operator.py, enforced in code,
# not just by the tool description - same non-bypassable pattern as the MiniMax H3
# adult-tuned video LoRAs.
CLIENT_CHARACTER_RENDERS_DIR = WORKSPACE_DIR / "client_character_renders"
CLIENT_CHARACTER_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
CLIENT_CHARACTER_PROFILES: Dict[str, str] = {
    "charlette": "client_character_charlette_template.json",
    "margo": "client_character_margo_template.json",
    "melissa": "client_character_melissa_template.json",
}

# Expert-level quality boosters, keyed by style_preset - injected into every render
# so "high-end realistic images" is the default output, not an opt-in.
QUALITY_PRESETS = {
    "photorealism": "professional photography, shot on full-frame DSLR, 85mm f/1.4 lens, "
                    "natural skin texture with visible pores, soft directional studio lighting, "
                    "shallow depth of field, hyper-detailed, photorealistic, 8k uhd, award-winning photography",
    "cinematic": "cinematic film still, dramatic volumetric lighting, color graded like a feature film, "
                 "shallow depth of field, anamorphic lens characteristics, subtle film grain, "
                 "ultra high production value, photorealistic",
    "graphic_design": "professional graphic design, clean vector composition, balanced negative space, "
                       "studio-quality rendering, ultra high resolution",
    "glamour": "high-end glamour photography, beauty-dish studio lighting, flawless skin retouch look, "
               "luxury editorial fashion photography, hyper-detailed, photorealistic, 8k uhd",
}
QUALITY_NEGATIVE_BOOST = (
    "deformed, extra limbs, bad anatomy, bad hands, 6 fingers, missing fingers, fused limbs, "
    "distorted face, asymmetrical eyes, blurry, low quality, artifacts, plastic skin, overly airbrushed, "
    "waxy skin, cartoon, 3d render, cgi, overexposed, underexposed, watermark, text, logo, grainy, jpeg artifacts"
)

# Per-agent PBR color + idle/working kinetic tuning, mirrored from the CHARACTERS table in
# dashboard/static/js/character3d.js so the real 3D mesh and its Idle/Working GLB animation
# match the same color + motion 'personality' already used by the 2D WebGL parallax card.
AGENT_VISUAL_THEMES = {
    "synapse": {"color": (0.0, 0.95, 1.0), "idle_speed": 0.85, "idle_yaw": 0.08, "idle_bob": 0.08, "working_speed": 2.8, "working_yaw": 0.22, "working_bob": 0.14},
    "iris":    {"color": (0.97, 0.15, 0.52), "idle_speed": 0.90, "idle_yaw": 0.18, "idle_bob": 0.06, "working_speed": 3.2, "working_yaw": 0.35, "working_bob": 0.12},
    "aura":    {"color": (1.0, 0.82, 0.40), "idle_speed": 0.70, "idle_yaw": 0.12, "idle_bob": 0.07, "working_speed": 2.2, "working_yaw": 0.26, "working_bob": 0.14},
    "echo":    {"color": (0.30, 0.79, 0.94), "idle_speed": 1.30, "idle_yaw": 0.12, "idle_bob": 0.09, "working_speed": 3.8, "working_yaw": 0.24, "working_bob": 0.18},
    "forge":   {"color": (1.0, 0.42, 0.21), "idle_speed": 1.0, "idle_yaw": 0.08, "idle_bob": 0.08, "working_speed": 3.0, "working_yaw": 0.20, "working_bob": 0.16},
    "cipher":  {"color": (0.65, 0.72, 0.82), "idle_speed": 0.80, "idle_yaw": 0.12, "idle_bob": 0.11, "working_speed": 3.0, "working_yaw": 0.26, "working_bob": 0.16},
    "herald":  {"color": (0.06, 0.73, 0.51), "idle_speed": 0.90, "idle_yaw": 0.12, "idle_bob": 0.07, "working_speed": 3.4, "working_yaw": 0.30, "working_bob": 0.15},
    "mercury": {"color": (0.66, 0.33, 0.97), "idle_speed": 1.10, "idle_yaw": 0.15, "idle_bob": 0.09, "working_speed": 3.2, "working_yaw": 0.28, "working_bob": 0.16},
    "scribe":  {"color": (0.94, 0.27, 0.27), "idle_speed": 1.00, "idle_yaw": 0.14, "idle_bob": 0.075, "working_speed": 3.4, "working_yaw": 0.32, "working_bob": 0.15},
}
DEFAULT_VISUAL_THEME = {"color": (0.8, 0.8, 0.85), "idle_speed": 0.9, "idle_yaw": 0.12, "idle_bob": 0.08, "working_speed": 3.0, "working_yaw": 0.25, "working_bob": 0.15}


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

    def is_server_available(self) -> bool:
        """Returns True if ComfyUI is online and responsive on Main PC."""
        return bool(self.check_connection().get("online", False))

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
        End-to-end real 3D character pipeline on the Main PC:
          1. Renders a clean, plain-background front-facing concept plate (Iris QC-gated).
          2. Converts it to a real textured 3D mesh via the local Hunyuan3D (Hy3D*) node
             pack, PBR-tinted to this agent's theme color.
          3. Injects real 'Idle'/'Working' glTF animation clips (rotation sway + bob + pulse,
             tuned per-agent to match character3d.js's kinetic personality) via pygltflib.
        Requires the Hunyuan3D shape model + VAE to be present in ComfyUI/models/diffusion_models
        and ComfyUI/models/vae on the Main PC - if missing, falls back to concept-art-only and
        reports the gap clearly instead of failing silently.
        """
        clean_name = agent_name.lower().strip()
        models_dir = Path("F:/WORKHORSE/dashboard/static/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        target_glb = models_dir / f"{clean_name}.glb"
        theme = AGENT_VISUAL_THEMES.get(clean_name, DEFAULT_VISUAL_THEME)

        pos_prompt = prompt or (
            f"A hyperrealistic sci-fi video game character bust of {clean_name.capitalize()}, elemental "
            f"cyberpunk armor, plain flat neutral grey background, centered, full bust visible, orthographic "
            f"front-facing view, even studio lighting, highly detailed 3D model reference asset"
        )

        # 1. Generate concept base plate on 5070 Ti (plain-background front view converts to mesh best)
        render_res = self.generate_and_audit(
            positive_prompt=pos_prompt,
            negative_prompt="low quality, deformed, extra limbs, blurry, pixelated, 2d cartoon, cluttered background, side profile",
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

        base_image = render_res.get("file_path")

        # 2. Convert concept plate into a real textured mesh via local Hunyuan3D
        mesh_res = self.generate_3d_character_mesh(
            agent_name=clean_name,
            source_image_path=base_image,
            base_color=theme["color"]
        )

        if not mesh_res.get("success"):
            return {
                "success": True,
                "agent": clean_name,
                "base_image": base_image,
                "glb_path": str(target_glb) if target_glb.exists() else None,
                "glb_ready": target_glb.exists(),
                "mesh_error": mesh_res.get("error"),
                "status": "Concept reference art rendered; real 3D mesh generation failed.",
                "message": (
                    f"Reference concept art for {clean_name.capitalize()} generated at {render_res.get('url_path')}, "
                    f"but converting it into a real 3D mesh failed: {mesh_res.get('error')}. If this mentions a "
                    f"missing checkpoint, the Hunyuan3D shape model/VAE still need to be downloaded onto the "
                    f"Main PC's ComfyUI/models/diffusion_models and ComfyUI/models/vae folders."
                )
            }

        # 3. Inject real Idle/Working animation clips into the freshly exported mesh
        anim_res = self.inject_kinetic_animation(target_glb, agent_name=clean_name)

        return {
            "success": True,
            "agent": clean_name,
            "base_image": base_image,
            "glb_path": str(target_glb),
            "glb_ready": True,
            "animated": anim_res.get("success", False),
            "status": "Real textured 3D model generated and animated.",
            "message": (
                f"Interactive 3D model for {clean_name.capitalize()} generated from a real Hunyuan3D mesh, "
                f"tinted to its theme color, with Idle/Working animation clips, and is now active in the "
                f"dashboard viewport."
            )
        }

    def _fetch_object_info(self, node_class: str) -> Dict[str, Any]:
        """Fetches live schema/inputs for a single ComfyUI node class (cheaper than the full /object_info dump)."""
        url = f"{self.get_base_url()}/object_info/{node_class}"
        req = urllib.request.Request(url, headers={"User-Agent": "WORKHORSE-Bridge"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get(node_class, {})

    def resolve_hy3d_models(self) -> str:
        """
        Picks the installed Hunyuan3D shape model off the live ComfyUI node's combo list.
        Raises a clear, actionable error if it hasn't been downloaded yet. Only a single
        "hunyuan3d-dit-v2-1" checkpoint is needed - the Hy3D_2_1SimpleMeshGen node loads its
        own matching v2.1 config internally and needs no separate VAE file (unlike the older
        v2.0 Hy3DModelLoader/Hy3DVAELoader pair, which expects a different checkpoint
        architecture and fails with a missing 'latent_in.weight' key on a v2.1 file).
        """
        loader_info = self._fetch_object_info("Hy3D_2_1SimpleMeshGen")
        model_choices = loader_info.get("input", {}).get("required", {}).get("model", [[]])[0]

        def _pick(choices: List[str]) -> Optional[str]:
            for c in choices:
                if "hunyuan3d" in c.lower() or "hy3d" in c.lower():
                    return c
            return None

        shape_model = _pick(model_choices)

        if not shape_model:
            raise RuntimeError(
                "Hunyuan3D shape model not found on the Main PC's ComfyUI install. "
                "Download hunyuan3d-dit-v2-1.safetensors into ComfyUI/models/diffusion_models "
                "(see ComfyUI-Hunyuan3DWrapper's README for current download links), then retry."
            )

        return shape_model

    def build_image_to_3d_mesh_workflow(self,
                                        source_image_name: str,
                                        shape_model: str,
                                        base_color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                                        emissive: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                                        metallic: float = 0.75,
                                        roughness: float = 0.2,
                                        steps: int = 30,
                                        guidance_scale: float = 5.5,
                                        octree_resolution: int = 384,
                                        max_facenum: int = 24000,
                                        seed: Optional[int] = None,
                                        filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph for local image-to-3D-mesh generation via Hunyuan3D 2.1:
        LoadImage -> Hy3D_2_1SimpleMeshGen -> Hy3DPostprocessMesh -> Hy3DMeshUVWrap ->
        Hy3DSetMeshPBRAttributes -> Hy3DExportMesh.
        Texture baking (multi-view render/delight/bake) is intentionally skipped - the mesh is
        tinted with a flat PBR material matching the agent's theme color instead, which keeps
        the graph simple/robust while still producing a real, correctly-shaped 3D asset.
        """
        workflow: Dict[str, Any] = {
            "1": {
                "inputs": {"image": source_image_name},
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {
                    "model": shape_model,
                    "image": ["1", 0],
                    "steps": steps,
                    "guidance_scale": guidance_scale,
                    "octree_resolution": octree_resolution
                },
                "class_type": "Hy3D_2_1SimpleMeshGen"
            },
            "6": {
                "inputs": {
                    "trimesh": ["2", 0],
                    "remove_floaters": True,
                    "remove_degenerate_faces": True,
                    "reduce_faces": True,
                    "max_facenum": max_facenum,
                    "smooth_normals": True
                },
                "class_type": "Hy3DPostprocessMesh"
            },
            "7": {
                "inputs": {"trimesh": ["6", 0]},
                "class_type": "Hy3DMeshUVWrap"
            },
            "8": {
                "inputs": {
                    "trimesh": ["7", 0],
                    "baseColorFactor": sum(base_color) / 3.0,
                    "emissiveFactor": sum(emissive) / 3.0 if any(emissive) else 0.0,
                    "metallicFactor": metallic,
                    "roughnessFactor": roughness,
                    "doubleSided": True
                },
                "class_type": "Hy3DSetMeshPBRAttributes"
            },
            "9": {
                "inputs": {
                    "trimesh": ["8", 0],
                    "filename_prefix": filename_prefix or "3D/WORKHORSE_Hy3D",
                    "file_format": "glb",
                    "save_file": True
                },
                "class_type": "Hy3DExportMesh"
            }
        }
        return workflow

    def wait_for_mesh_execution(self, prompt_id: str, timeout_seconds: int = 600) -> Optional[Dict[str, str]]:
        """
        Polls /history/{prompt_id} until a mesh export finishes or times out. Mesh/3D-export
        nodes aren't standardized on a single UI output key the way images/videos are, so this
        defensively scans all node outputs for any dict with a '.glb' filename or bare string
        ending in '.glb' under any key name.
        """
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
                        if not status.get("completed", True) and status.get("status_str") not in ("success",):
                            time.sleep(2)
                            continue
                        outputs = history[prompt_id].get("outputs", {})
                        # Prioritize Node "322" (Save3DAdvanced final PBR result) and any type=="output" .glb
                        # over intermediate preview nodes (e.g. Node "246" rough voxel blob in type=="temp").
                        output_glbs = []
                        temp_glbs = []
                        ordered_nodes = []
                        if "322" in outputs:
                            ordered_nodes.append(("322", outputs["322"]))
                        for nid, nout in outputs.items():
                            if nid != "322":
                                ordered_nodes.append((nid, nout))
                        for nid, node_output in ordered_nodes:
                            for key, value in node_output.items():
                                if isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and str(item.get("filename", "")).lower().endswith(".glb"):
                                            if item.get("type", "output") == "output" or nid == "322":
                                                output_glbs.append(item)
                                            else:
                                                temp_glbs.append(item)
                                        elif isinstance(item, str) and item.lower().endswith(".glb"):
                                            output_glbs.append({
                                                "filename": Path(item).name,
                                                "subfolder": str(Path(item).parent) if Path(item).parent != Path(".") else "",
                                                "type": "output"
                                            })
                        if output_glbs:
                            return output_glbs[0]
                        if temp_glbs:
                            return temp_glbs[-1]
                        if outputs:
                            # Execution completed but no .glb reference surfaced in history UI data.
                            return None
            except RuntimeError:
                raise
            except Exception:
                pass
            time.sleep(3)

        return None

    def download_mesh(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Path:
        """Pulls an exported mesh (.glb) from ComfyUI's /view endpoint into local staging folder."""
        params = urllib.parse.urlencode({
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        })
        view_url = f"{self.get_base_url()}/view?{params}"
        dest_path = STAGING_DIR / f"{Path(filename).stem}_{int(time.time())}.glb"

        req = urllib.request.Request(view_url, headers={"User-Agent": "WORKHORSE-Bridge"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())

        return dest_path

    def build_pixal3d_trellis2_workflow(self,
                                        source_image_name: str,
                                        texture_resolution: int = 2048,
                                        upsample_resolution: str = "1024",
                                        remesh_resolution: int = 512,
                                        target_face_count: int = 200000,
                                        use_trellis2: bool = True,
                                        filename_prefix: Optional[str] = None,
                                        seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph for full-PBR image-to-3D generation, based on the
        Commander's own exported "Pixal3D & TRELLIS.2" workflow template.
        It bakes REAL multi-channel PBR texture maps (base color, metallic, roughness,
        normal, ambient occlusion) onto the mesh via MoGe geometry estimation + a
        3-stage Trellis2 shape/texture/upsample pipeline.
        """
        template_path = WORKFLOW_TEMPLATES_DIR / "pixal3d_trellis2_img23d_template.json"
        with open(template_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        seed_base = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)

        workflow["122"]["inputs"]["image"] = source_image_name
        workflow["288"]["inputs"]["value"] = texture_resolution
        if "94" in workflow and "target_resolution" in workflow["94"].get("inputs", {}):
            workflow["94"]["inputs"]["target_resolution"] = str(upsample_resolution)
        if "241" in workflow and "resolution" in workflow["241"].get("inputs", {}):
            workflow["241"]["inputs"]["resolution"] = int(remesh_resolution)
        if "186" in workflow and "target_face_count" in workflow["186"].get("inputs", {}):
            workflow["186"]["inputs"]["target_face_count"] = int(target_face_count)
        workflow["316"]["inputs"]["value"] = use_trellis2
        workflow["322"]["inputs"]["filename_prefix"] = filename_prefix or f"3D/WORKHORSE_PBR_{seed_base}"
        for node_id, offset in (("3", 0), ("12", 1), ("18", 2), ("23", 2)):
            workflow[node_id]["inputs"]["seed"] = (seed_base + offset) % (2**31 - 1)

        return workflow

    def generate_image_to_3d_pbr(self,
                                 source_image_path: Union[str, Path],
                                 output_name: Optional[str] = None,
                                 texture_resolution: int = 2048,
                                 upsample_resolution: str = "1024",
                                 remesh_resolution: int = 512,
                                 target_face_count: int = 200000,
                                 use_trellis2: bool = True,
                                 export_stl_via_blender: bool = True,
                                 timeout_seconds: int = 900) -> Dict[str, Any]:
        """
        End-to-end full-PBR image-to-3D conversion: uploads a reference image, runs it
        through the Pixal3D/Trellis2 pipeline on the Main PC (RTX 5070 Ti), saves
        the resulting textured .glb to workspace/brand_assets/comfy_3d_pbr_renders/,
        and optionally post-processes via Blender 5.2 MCP to generate a watertight
        3D-printable .stl and studio preview renders.
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {"success": False, "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')})."}

        source_image_path = Path(source_image_path)
        if not source_image_path.exists():
            return {"success": False, "error": f"Source image not found: {source_image_path}"}

        template_path = WORKFLOW_TEMPLATES_DIR / "pixal3d_trellis2_img23d_template.json"
        if not template_path.exists():
            return {"success": False, "error": f"Workflow template not found: {template_path}"}

        try:
            uploaded_name = self.upload_image_to_comfy(source_image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to upload source image to ComfyUI: {e}"}

        clean_name = (output_name or source_image_path.stem).strip().replace(" ", "_")
        workflow = self.build_pixal3d_trellis2_workflow(
            source_image_name=uploaded_name,
            texture_resolution=texture_resolution,
            upsample_resolution=upsample_resolution,
            remesh_resolution=remesh_resolution,
            target_face_count=target_face_count,
            use_trellis2=use_trellis2,
            filename_prefix=f"3D/WORKHORSE_PBR_{clean_name}"
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            mesh_ref = self.wait_for_mesh_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not mesh_ref:
                return {"success": False, "error": "ComfyUI PBR 3D generation timed out or yielded no .glb output"}

            staged_path = self.download_mesh(
                filename=mesh_ref["filename"],
                subfolder=mesh_ref.get("subfolder", ""),
                folder_type=mesh_ref.get("type", "output")
            )
        except RuntimeError as e:
            return {"success": False, "error": f"ComfyUI PBR 3D generation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"ComfyUI PBR 3D generation failed: {e}"}

        PBR_3D_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        dest_path = PBR_3D_RENDERS_DIR / f"{clean_name}_{ts}.glb"
        staged_path.rename(dest_path)

        result: Dict[str, Any] = {
            "success": True,
            "glb_path": str(dest_path),
            "source_image": str(source_image_path),
            "engine": "trellis2" if use_trellis2 else "pixal3d",
            "texture_resolution": texture_resolution,
            "host_used": f"{self.host}:{self.port}"
        }

        if export_stl_via_blender:
            try:
                from pipeline.stages.blender_bridge import blender_bridge
                stl_dest = PBR_3D_RENDERS_DIR / f"{clean_name}_{ts}.stl"
                blender_res = blender_bridge.process_glb_to_printable_stl_and_renders(
                    input_glb_path=dest_path,
                    output_glb_path=dest_path,
                    output_stl_path=stl_dest,
                    preview_dir=PBR_3D_RENDERS_DIR / "previews",
                    asset_prefix=clean_name,
                    add_pedestal_base=True
                )
                result["stl_path"] = str(stl_dest)
                result["blender_postprocess"] = blender_res
            except Exception as be:
                result["blender_error"] = str(be)

        return result

    def generate_3d_glb_stl_from_idea_or_image(
        self,
        idea_prompt: Optional[str] = None,
        source_image_path: Optional[Union[str, Path]] = None,
        output_name: Optional[str] = None,
        texture_resolution: int = 2048,
        add_pedestal_base: bool = True,
        target_height_mm: float = 100.0,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Unified Etsy/Fiverr 3D (.GLB + Watertight .STL) Generator:
        Supports creating expert-level 3D PBR game assets (.GLB) and 100% watertight
        3D-printable sculptures (.STL) either:
          - FROM AN IMAGE (`source_image_path` provided), OR
          - FROM AN IDEA (`idea_prompt` provided -> automatically renders an isolated
            three-quarter studio 3D concept plate on ComfyUI first, then runs Trellis 2
            HQ + PBR and Blender 5.2 Voxel-Remesh STL post-processing).
        """
        mode = "from_image"
        img_path = Path(source_image_path) if source_image_path else None

        if img_path is None or not img_path.exists():
            if not idea_prompt or not str(idea_prompt).strip():
                return {
                    "success": False,
                    "error": "Provide either an existing source_image_path or an idea_prompt to generate a 3D .GLB + .STL asset.",
                }
            mode = "from_idea"
            clean_idea = str(idea_prompt).strip()
            concept_prompt = (
                f"three-quarter front view of {clean_idea}, centered complete object visible, "
                "isolated on solid neutral grey studio background, soft even studio product lighting, "
                "ultra detailed 3d sculpt render, no text, no watermark"
            )
            concept_neg = (
                "text, letters, words, watermark, signature, cluttered background, cropped, cut off, "
                "multiple objects, blurry, flat 2d, harsh cast shadows, frame, border"
            )
            gen_concept = self.generate_and_audit(
                positive_prompt=concept_prompt,
                negative_prompt=concept_neg,
                width=1024,
                height=1024,
                steps=24,
                cfg=6.5,
                seed=seed,
                auto_qc=False,
            )
            if not gen_concept.get("success") or not gen_concept.get("file_path"):
                return {
                    "success": False,
                    "mode": mode,
                    "error": f"Failed to render 3D concept plate from idea: {gen_concept.get('error')}",
                }
            img_path = Path(gen_concept["file_path"])

        res = self.generate_image_to_3d_pbr(
            source_image_path=img_path,
            output_name=output_name or (img_path.stem if img_path else "etsy_3d_asset"),
            texture_resolution=texture_resolution,
            use_trellis2=True,
            export_stl_via_blender=True,
        )
        res["creation_mode"] = mode
        res["concept_image"] = str(img_path)
        return res

    def generate_etsy_svg_from_idea_or_image(
        self,
        idea_prompt: Optional[str] = None,
        source_image_path: Optional[Union[str, Path]] = None,
        output_name: str = "custom_etsy_stencil",
        stencil_mode: str = "full_color",
        num_layers: int = 6,
        top_text: str = "",
        bottom_text: str = "",
        extrude_3d_medallion: bool = False,
        output_dir: Optional[Union[str, Path]] = None,
        seed: int = 910500,
    ) -> Dict[str, Any]:
        """
        Unified Etsy/Fiverr .SVG Stencil Generator (Full-Color Layered Stencil OR B&W Vinyl Cut):
        Supports creating Cricut/Silhouette/Glowforge-ready .SVG + 300 DPI .PNG assets either:
          - FROM AN IMAGE (`source_image_path` provided), OR
          - FROM AN IDEA (`idea_prompt` provided -> renders a text-free stencil illustration on
            ComfyUI first, adds optional crisp OpenType vector banner typography so zero AI
            gibberish text ever appears, and vectorizes into clean closed SVG paths).
        Optionally also extrudes the resulting .SVG in Blender 5.2 into a 100mm watertight 3D
        relief medallion (.STL + .GLB) when `extrude_3d_medallion=True`.
        """
        from PIL import Image
        import build_full_color_and_clean_svg_kit as svg_builder

        out_dir = Path(output_dir) if output_dir else (BASE_DIR / "workspace" / "media_kits" / "06_SVG_TShirt_Vinyl_Cut_Files")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = output_name.strip().replace(" ", "_").lower()

        creation_mode = "from_image"
        img_path = Path(source_image_path) if source_image_path else None

        if img_path and img_path.exists():
            pil_img = Image.open(img_path).convert("RGB")
        else:
            if not idea_prompt or not str(idea_prompt).strip():
                return {
                    "success": False,
                    "error": "Provide either an existing source_image_path or an idea_prompt to generate an Etsy .SVG asset.",
                }
            creation_mode = "from_idea"
            clean_idea = str(idea_prompt).strip()
            neg_strict_no_text = (
                "text, letters, words, typography, font, writing, alphabet, numbers, watermark, signature, "
                "banner text, gibberish, logo letters, blurry, photorealistic, 3d shading, gradient, grey background"
            )
            if stencil_mode.lower() in ("bw", "b&w", "black_and_white", "bw_cut", "vinyl_cut"):
                pos_prompt = (
                    f"pure black and white vector stencil line art of {clean_idea}, stark solid black ink on pure "
                    "white background, crisp bold woodcut screenprint stencil outlines, no text, no letters, no words, "
                    "center isolated graphic"
                )
            else:
                pos_prompt = (
                    f"flat vector screenprint stencil illustration of {clean_idea}, {num_layers} solid flat colors, "
                    "crisp clean color blocks, isolated on solid background, zero gradients, no text, no letters, "
                    "no words, cricut layered vinyl stencil style"
                )
            pil_img = svg_builder.render_comfy_sdxl(
                positive=pos_prompt,
                negative=neg_strict_no_text,
                seed=seed,
                prefix=f"SVG_Custom_{slug}",
            )

        if top_text or bottom_text:
            pil_img = svg_builder.add_clean_vector_banner_text(
                pil_img,
                top_text=top_text or "",
                bottom_text=bottom_text or "",
                is_bw=(stencil_mode.lower() in ("bw", "b&w", "black_and_white", "bw_cut", "vinyl_cut")),
            )

        master_png = out_dir / f"{slug}_master.png"
        svg_path = out_dir / f"{slug}.svg"
        preview_png = out_dir / f"{slug}_vector_preview.png"
        pil_img.save(master_png)

        if stencil_mode.lower() in ("bw", "b&w", "black_and_white", "bw_cut", "vinyl_cut"):
            stats = svg_builder.vectorize_bw_to_svg(
                pil_img,
                svg_path=svg_path,
                preview_png_path=preview_png,
                title_text=f"{output_name} - B&W Cut SVG",
            )
            strip_png = None
        else:
            strip_png = out_dir / f"{slug}_layers_strip.png"
            stats = svg_builder.vectorize_full_color_stencil_to_svg(
                pil_img,
                svg_path=svg_path,
                preview_png_path=preview_png,
                layer_strip_png_path=strip_png,
                num_layers=num_layers,
                title_text=f"{output_name} - Full-Color Stencil SVG",
            )

        result: Dict[str, Any] = {
            "success": svg_path.exists() and svg_path.stat().st_size > 500,
            "creation_mode": creation_mode,
            "stencil_mode": stencil_mode,
            "svg_path": str(svg_path),
            "master_png": str(master_png),
            "vector_preview_png": str(preview_png),
            "layers_strip_png": str(strip_png) if strip_png else None,
            "stats": stats,
        }

        if extrude_3d_medallion and svg_path.exists():
            from pipeline.stages.blender_bridge import blender_bridge
            med_glb = out_dir / f"{slug}_3d_medallion.glb"
            med_stl = out_dir / f"{slug}_3d_medallion.stl"
            med_prev = out_dir / f"{slug}_3d_medallion_render.png"
            b_res = blender_bridge.extrude_svg_to_3d_stl_and_glb(
                svg_path=svg_path,
                output_glb_path=med_glb,
                output_stl_path=med_stl,
                preview_png_path=med_prev,
                target_diameter_mm=100.0,
            )
            result["medallion_3d"] = b_res

        return result

    def build_client_character_workflow(self,
                                        character_name: str,
                                        prompt: Optional[str] = None,
                                        seed: Optional[int] = None,
                                        filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Loads one of the Commander's own pre-tested, pre-tuned flux_dev + client-identity-
        LoRA workflows (Charlette/Margo/Melissa) exactly as exported - every node, LoRA
        stack, and sampler setting is left untouched per the Commander's explicit
        instruction, since he already validated these directly in ComfyUI. Only patches
        the prompt text (if a new one is given - otherwise keeps the template's own),
        the generation seed (for variety across calls), and both SaveImage nodes'
        filename_prefix, tagged CLIENT_CHARACTER_<name> so this is never mistaken for
        postable marketing content or mixed up with a different client's renders.
        """
        template_name = CLIENT_CHARACTER_PROFILES.get(character_name.lower().strip())
        if not template_name:
            raise ValueError(
                f"Unknown client character '{character_name}'. Available: "
                f"{', '.join(CLIENT_CHARACTER_PROFILES.keys())}"
            )
        template_path = WORKFLOW_TEMPLATES_DIR / template_name
        with open(template_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        if prompt:
            workflow["41:45"]["inputs"]["text"] = prompt

        seed_base = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)
        workflow["41:31"]["inputs"]["seed"] = seed_base
        workflow["41:54"]["inputs"]["seed"] = (seed_base + 1) % (2**31 - 1)

        tag = filename_prefix or f"CLIENT_CHARACTER_{character_name.upper()}"
        workflow["9"]["inputs"]["filename_prefix"] = f"{tag}_base"
        workflow["42"]["inputs"]["filename_prefix"] = f"{tag}_final"

        return workflow

    def generate_client_character_image(self,
                                        character_name: str,
                                        prompt: Optional[str] = None,
                                        seed: Optional[int] = None,
                                        adult_allowed: bool = False,
                                        timeout_seconds: int = 240) -> Dict[str, Any]:
        """
        Generates an image of one of the Commander's own licensed client character
        LoRAs (Charlette/Margo/Melissa) for his own testing - NEVER for posting, and
        NEVER usable without adult_allowed=True. This flag must be computed upstream
        from the Commander's actual Adult Content Mode toggle or an explicit request in
        his own message (see ai_operator.py's chat()/_detect_explicit_adult_request) -
        never trusted from a tool-call's JSON alone. Hard-gated here in code (not just
        omitted from a tool description) so this can never fire by accident.
        """
        if not adult_allowed:
            return {
                "success": False,
                "error": "Client character generation requires Adult Content Mode to be "
                         "on (or an explicit adult-content request this turn) - these are "
                         "licensed client identity LoRAs, not general-purpose content."
            }

        clean_name = character_name.lower().strip()
        if clean_name not in CLIENT_CHARACTER_PROFILES:
            return {
                "success": False,
                "error": f"Unknown client character '{character_name}'. Available: "
                         f"{', '.join(CLIENT_CHARACTER_PROFILES.keys())}"
            }

        conn = self.check_connection()
        if not conn.get("online"):
            return {"success": False, "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')})."}

        try:
            workflow = self.build_client_character_workflow(clean_name, prompt=prompt, seed=seed)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            # Pull the final hi-res/refined pass (SaveImage node "42") specifically,
            # rather than the generic "first image found anywhere" collector - this
            # graph has two SaveImage nodes (base pass + upscale-refine pass) and the
            # refined one is the actual deliverable.
            history_url = f"{self.get_base_url()}/history/{prompt_id}"
            start_time = time.time()
            image_ref = None
            while time.time() - start_time < timeout_seconds:
                req = urllib.request.Request(history_url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    history = json.loads(resp.read().decode("utf-8"))
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    final_images = outputs.get("42", {}).get("images", [])
                    base_images = outputs.get("9", {}).get("images", [])
                    if final_images:
                        image_ref = final_images[0]
                        break
                    if base_images and not outputs.get("42"):
                        # Final refine node hasn't produced output for some reason but
                        # the base pass has - fall back to it rather than hanging.
                        image_ref = base_images[0]
                time.sleep(1.5)

            if not image_ref:
                return {"success": False, "error": "ComfyUI client character generation timed out or yielded no image output"}

            staged_path = self.download_image(
                filename=image_ref["filename"],
                subfolder=image_ref.get("subfolder", ""),
                folder_type=image_ref.get("type", "output")
            )
        except Exception as e:
            return {"success": False, "error": f"ComfyUI client character generation failed: {e}"}

        char_dir = CLIENT_CHARACTER_RENDERS_DIR / clean_name
        char_dir.mkdir(parents=True, exist_ok=True)
        dest_path = char_dir / f"{clean_name}_{int(time.time())}.png"
        staged_path.rename(dest_path)

        return {
            "success": True,
            "character": clean_name,
            "image_path": str(dest_path),
            "tag": "CLIENT_CHARACTER_ASSET",
            "host_used": f"{self.host}:{self.port}"
        }

    def generate_3d_character_mesh(self,
                                   agent_name: str,
                                   source_image_path: Union[str, Path],
                                   base_color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                                   emissive: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                                   timeout_seconds: int = 600) -> Dict[str, Any]:
        """
        End-to-end: uploads a reference image, converts it to a real textured mesh via the
        local Hunyuan3D node pack, and writes the result straight to
        dashboard/static/models/<agent>.glb (no animation yet - see inject_kinetic_animation).
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {"success": False, "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')})."}

        source_image_path = Path(source_image_path)
        if not source_image_path.exists():
            return {"success": False, "error": f"Source image not found: {source_image_path}"}

        try:
            shape_model = self.resolve_hy3d_models()
        except RuntimeError as e:
            return {"success": False, "error": str(e)}

        try:
            uploaded_name = self.upload_image_to_comfy(source_image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to upload source image to ComfyUI: {e}"}

        clean_name = agent_name.lower().strip()
        workflow = self.build_image_to_3d_mesh_workflow(
            source_image_name=uploaded_name,
            shape_model=shape_model,
            base_color=base_color,
            emissive=emissive,
            filename_prefix=f"3D/Hy3D_{clean_name}"
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            mesh_ref = self.wait_for_mesh_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not mesh_ref:
                return {"success": False, "error": "ComfyUI mesh generation timed out or yielded no .glb output"}

            staged_path = self.download_mesh(
                filename=mesh_ref["filename"],
                subfolder=mesh_ref.get("subfolder", ""),
                folder_type=mesh_ref.get("type", "output")
            )
        except RuntimeError as e:
            return {"success": False, "error": f"ComfyUI mesh generation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"ComfyUI mesh generation failed: {e}"}

        models_dir = Path("F:/WORKHORSE/dashboard/static/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        dest_path = models_dir / f"{clean_name}.glb"
        if dest_path.exists():
            dest_path.unlink()
        staged_path.rename(dest_path)

        return {
            "success": True,
            "agent": clean_name,
            "glb_path": str(dest_path),
            "source_image": str(source_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

    def inject_kinetic_animation(self, glb_path: Union[str, Path], agent_name: str = "") -> Dict[str, Any]:
        """
        Appends real glTF 'Idle' and 'Working' animation clips (gentle Y-axis rotation sway +
        vertical bob for Idle; faster rotation + bigger bob + a scale pulse for Working) onto
        the mesh's root node, tuned per-agent from AGENT_VISUAL_THEMES so the 3D viewer moves
        with the same 'feel' as the 2D WebGL card. Safe to run on any valid GLB.
        """
        import struct
        from pygltflib import GLTF2, Animation, AnimationSampler, AnimationChannel, AnimationChannelTarget, Accessor, BufferView, FLOAT, VEC3, VEC4, SCALAR

        glb_path = Path(glb_path)
        theme = AGENT_VISUAL_THEMES.get(agent_name.lower().strip(), DEFAULT_VISUAL_THEME)

        try:
            gltf = GLTF2.load(str(glb_path))
        except Exception as e:
            return {"success": False, "error": f"Failed to load GLB for animation: {e}"}

        if not gltf.nodes:
            return {"success": False, "error": "GLB has no nodes to animate"}

        target_node = 0
        blob = bytearray(gltf.binary_blob() or b"")

        def _quat_y(angle_rad: float):
            return (0.0, math.sin(angle_rad / 2.0), 0.0, math.cos(angle_rad / 2.0))

        def _push_accessor(values: List[Tuple[float, ...]], fmt: str, accessor_type: str, set_bounds: bool = False) -> int:
            data = b"".join(struct.pack(fmt, *v) for v in values)
            pad = (-len(blob)) % 4
            blob.extend(b"\x00" * pad)
            offset = len(blob)
            blob.extend(data)
            bv_index = len(gltf.bufferViews)
            gltf.bufferViews.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(data)))
            acc = Accessor(bufferView=bv_index, componentType=FLOAT, count=len(values), type=accessor_type)
            if set_bounds:
                flat = [list(v) for v in values]
                acc.min = [min(col) for col in zip(*flat)]
                acc.max = [max(col) for col in zip(*flat)]
            acc_index = len(gltf.accessors)
            gltf.accessors.append(acc)
            return acc_index

        def _add_clip(name: str, duration: float, yaw_amp: float, bob_amp: float, scale_pulse: float) -> None:
            times = [(t,) for t in (0.0, duration * 0.25, duration * 0.5, duration * 0.75, duration)]
            rotations = [_quat_y(a) for a in (0.0, yaw_amp, 0.0, -yaw_amp, 0.0)]
            translations = [(0.0, b, 0.0) for b in (0.0, bob_amp, 0.0, -bob_amp * 0.6, 0.0)]
            scales = [(1.0 + s, 1.0 + s, 1.0 + s) for s in (0.0, scale_pulse, 0.0, scale_pulse * 0.5, 0.0)]

            time_acc = _push_accessor(times, "<f", SCALAR, set_bounds=True)
            rot_acc = _push_accessor(rotations, "<4f", VEC4)
            trans_acc = _push_accessor(translations, "<3f", VEC3)
            scale_acc = _push_accessor(scales, "<3f", VEC3)

            anim = Animation(name=name)
            for acc_index, path in ((rot_acc, "rotation"), (trans_acc, "translation"), (scale_acc, "scale")):
                sampler_index = len(anim.samplers)
                anim.samplers.append(AnimationSampler(input=time_acc, output=acc_index, interpolation="LINEAR"))
                anim.channels.append(AnimationChannel(sampler=sampler_index, target=AnimationChannelTarget(node=target_node, path=path)))
            gltf.animations.append(anim)

        _add_clip("Idle", duration=max(2.0, 3.0 / theme["idle_speed"]), yaw_amp=theme["idle_yaw"], bob_amp=theme["idle_bob"], scale_pulse=0.02)
        _add_clip("Working", duration=max(0.6, 2.4 / theme["working_speed"]), yaw_amp=theme["working_yaw"], bob_amp=theme["working_bob"], scale_pulse=0.08)

        gltf.set_binary_blob(bytes(blob))
        gltf.buffers[0].byteLength = len(blob)
        try:
            gltf.save(str(glb_path))
        except Exception as e:
            return {"success": False, "error": f"Failed to save animated GLB: {e}"}

        return {"success": True, "glb_path": str(glb_path), "clips": ["Idle", "Working"]}

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
                                         filename_prefix: Optional[str] = None,
                                         brand_target: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph that automatically segments the subject out of an
        uploaded photo (SAM3 text-prompted grounding - "LayerMask: PersonMaskUltra V2"
        was confirmed broken on this install, crashes in its mask-merge step regardless
        of settings; SAM3 has no such bug and no numpy/numba dependency conflict),
        then inpaints a brand-new background around them from a text prompt while the
        subject region itself is protected from the noise mask.
        """
        # Automated brand visual generations must strictly use clean SFW photorealism checkpoint
        if brand_target and not checkpoint:
            ckpt_resolved = self.resolve_checkpoint_name("epicrealismXL_vxviiCrystalclear.safetensors")
        else:
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
            "19": {
                "inputs": {
                    "model": ["2", 0],
                    "sage_attention": "auto"
                },
                "class_type": "PathchSageAttentionKJ"
            },
            "8": {
                "inputs": {
                    "seed": seed_val,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": denoise,
                    "model": ["19", 0],
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
            from pipeline.stages.scrubber import metadata_scrubber
            metadata_scrubber.scrub_image(dest_path)
        except Exception as ce:
            print(f"[SCRUBBER] Warning: Metadata scrub failed: {ce}")

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
                                style_preset: str = "photorealism",
                                filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates standard ComfyUI API-compatible prompt graph.
        Dynamically chains multi-LoRA stacks and connects checkpoint/sampler/conditioning.
        """
        ckpt_resolved = self.resolve_checkpoint_name(checkpoint)
        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)

        quality_tag = QUALITY_PRESETS.get(style_preset, QUALITY_PRESETS["photorealism"])
        full_positive = positive_prompt if quality_tag in positive_prompt else f"{positive_prompt}, {quality_tag}"

        neg = negative_prompt or ""
        neg = neg if QUALITY_NEGATIVE_BOOST in neg else (f"{neg}, {QUALITY_NEGATIVE_BOOST}" if neg else QUALITY_NEGATIVE_BOOST)

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
                    "filename_prefix": filename_prefix or ("CPL_Creator" if brand_target and "pulse" in brand_target.lower() else ("CML_Studio" if brand_target and "media" in brand_target.lower() else "WORKHORSE_Render")),
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

        # SageAttention patch (RTX 5070 Ti speed optimization) - always applied as the last
        # step on the model chain, right before it's handed to the sampler.
        sage_node_key = str(next_node_id)
        workflow[sage_node_key] = {
            "inputs": {
                "model": current_model,
                "sage_attention": "auto"
            },
            "class_type": "PathchSageAttentionKJ"
        }
        current_model = [sage_node_key, 0]
        next_node_id += 1

        # Text conditioning
        workflow["6"] = {
            "inputs": {
                "text": full_positive,
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

    def get_queue_status(self) -> Dict[str, Any]:
        """Queries ComfyUI /queue for currently running and pending prompts."""
        try:
            req = urllib.request.Request(f"{self.get_base_url()}/queue")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                running = data.get("queue_running", [])
                pending = data.get("queue_pending", [])
                return {
                    "online": True,
                    "executing": len(running) > 0,
                    "running_count": len(running),
                    "pending_count": len(pending),
                    "running_prompt_id": running[0][1] if running and len(running[0]) > 1 else None
                }
        except Exception as e:
            return {"online": False, "executing": False, "running_count": 0, "pending_count": 0, "error": str(e)}

    def interrupt(self) -> Dict[str, Any]:
        """Sends interrupt signal to ComfyUI /interrupt to abort currently executing workflow."""
        try:
            req = urllib.request.Request(f"{self.get_base_url()}/interrupt", data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"success": True, "code": resp.getcode()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_queue(self) -> Dict[str, Any]:
        """Clears pending execution queue on ComfyUI."""
        try:
            payload = json.dumps({"clear": True}).encode("utf-8")
            req = urllib.request.Request(f"{self.get_base_url()}/queue", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"success": True, "code": resp.getcode()}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
                            for key in ("videos", "gifs", "images", "mp4", "video"):
                                if key in node_output and isinstance(node_output[key], list):
                                    videos.extend(node_output[key])
                            for val in node_output.values():
                                if isinstance(val, list):
                                    for item in val:
                                        if isinstance(item, dict) and str(item.get("filename", "")).lower().endswith(".mp4") and item not in videos:
                                            videos.append(item)
                                        elif isinstance(item, str) and item.lower().endswith(".mp4"):
                                            videos.append({"filename": Path(item).name, "subfolder": str(Path(item).parent) if Path(item).parent != Path(".") else "", "type": "output"})
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
                                      filename_prefix: Optional[str] = None,
                                      audio_mode: str = "music") -> Dict[str, Any]:
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

        cinematic_tag = "cinematic motion, smooth natural movement, film-quality motion dynamics, photorealistic, high production value"
        # Neutral on purpose: this builder also serves SFW brand/social/family videos (Herald, client photos).
        # It used to append "sensual chill melodic electronic beat" to EVERY video that didn't name music.
        # A prompt that wants a sensual soundtrack says so itself and then no default tag is added at all.
        music_tag = "smooth ambient background music, soft melodic electronic beat, rhythmic synth pads"

        prompt_clean = prompt.strip()
        is_silent = audio_mode == "silent" or any(w in prompt_clean.lower() for w in ["silent", "mute", "no audio", "no sound"])

        prompt_parts = [prompt_clean]
        if cinematic_tag not in prompt_clean:
            prompt_parts.append(cinematic_tag)
        if not is_silent and not any(w in prompt_clean.lower() for w in ["music", "beat", "melody", "soundtrack", "synth", "lo-fi", "jazz", "bass"]):
            prompt_parts.append(music_tag)
        full_prompt = ", ".join(prompt_parts)

        video_negative_default = (
            "jittery motion, flickering, morphing, warped limbs, distorted face, static image, "
            "frozen frame, low quality, blurry, artifacts, watermark, text, "
            "screaming, shouting, yelling, loud voice, vocal screams, crying, chaotic noise, "
            "distorted vocals, talking, speech, harsh static, obnoxious vocal sounds, loud mouth noise"
        )
        full_negative = negative_prompt or ""
        full_negative = full_negative if video_negative_default in full_negative else (
            f"{full_negative}, {video_negative_default}" if full_negative else video_negative_default
        )

        workflow["269"]["inputs"]["image"] = source_image_name
        workflow["267:266"]["inputs"]["value"] = full_prompt
        workflow["267:247"]["inputs"]["text"] = full_negative
        workflow["267:257"]["inputs"]["value"] = width
        workflow["267:258"]["inputs"]["value"] = height
        workflow["267:225"]["inputs"]["value"] = num_frames
        workflow["267:260"]["inputs"]["value"] = fps
        workflow["267:216"]["inputs"]["noise_seed"] = seed_val
        workflow["267:237"]["inputs"]["noise_seed"] = seed_val + 1
        workflow["273"]["inputs"]["filename_prefix"] = filename_prefix or "video/WORKHORSE_I2V"

        # If silent video is requested, detach the audio input from CreateVideo to avoid audio synthesis
        if is_silent and "267:242" in workflow and "audio" in workflow["267:242"].get("inputs", {}):
            del workflow["267:242"]["inputs"]["audio"]

        return workflow

    def generate_image_to_video(self,
                                source_image_path: Union[str, Path],
                                prompt: str,
                                negative_prompt: Optional[str] = None,
                                width: int = 720,
                                height: int = 1280,
                                num_frames: int = 300,
                                fps: int = 30,
                                timeout_seconds: int = 900,
                                dest_subdir: Optional[str] = None,
                                audio_mode: str = "music") -> Dict[str, Any]:
        """
        End-to-end LTX 2.3 image-to-video: uploads the source photo, builds the graph
        from the proven local template, renders, and saves the result video. Rendering
        is GPU/length/resolution dependent and can take several minutes - no Iris QC
        pass is run on video output (QC gate is vision/image-based only, v1).

        dest_subdir: optional brand subfolder (e.g. "creator_pulse_lab") under
        comfy_video_renders/ - used by Herald's scheduled social posts so those videos
        land in a dedicated per-brand folder, cleanly separated from ad-hoc Synapse
        chat-requested videos (which keep the default top-level location). Never set
        by the chat tool itself.
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
            fps=fps,
            audio_mode=audio_mode
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

        video_dir = (VIDEO_RENDERS_DIR / dest_subdir) if dest_subdir else VIDEO_RENDERS_DIR
        video_dir.mkdir(parents=True, exist_ok=True)
        dest_path = video_dir / staged_path.name
        staged_path.rename(dest_path)

        return {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_video_renders/{(dest_subdir + '/') if dest_subdir else ''}{dest_path.name}",
            "source_image": str(source_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

    def build_minimax_h3_i2v_workflow(self,
                                      source_image_name: str,
                                      prompt: str,
                                      duration_seconds: float = 10.0,
                                      seed: Optional[int] = None,
                                      filename_prefix: Optional[str] = None,
                                      lora_config: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Builds a ComfyUI API graph for MiniMax H3 image-to-video generation, based on the
        user's own confirmed-working local workflow template. A custom "AI Video
        Cinematography Director" node auto-generates the actual motion prompt from the
        source image and style settings - the caller's prompt is fed into its
        extra_custom_tags field rather than a plain prompt widget.

        The template ships with 3 chained LoRAs tuned for adult/boudoir content by
        default. LoRAs can be freely swapped or disabled on any ComfyUI workflow, so
        pass lora_config (a list of up to 3 {"lora_name":..., "strength_model":...}
        dicts) to override them - e.g. an empty list zeroes out all 3 for clean,
        general-brand/SFW generation. Leaving lora_config=None keeps the shipped adult
        defaults, which must ONLY ever be used for the adult_creator_brand content line.
        """
        template_path = WORKFLOW_TEMPLATES_DIR / "minimax_h3_i2v_template.json"
        with open(template_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)

        workflow["114"]["inputs"]["image"] = source_image_name
        workflow["141"]["inputs"]["extra_custom_tags"] = prompt
        # The exported template's Director node (141) had several fields land in the wrong
        # slot - confirmed via ComfyUI's own validation errors (an IP under lighting_preset,
        # a port number under secondary_pc_ip, a model name under port, a small int under
        # model_name), almost certainly from the custom node's widget order shifting after
        # an update post-dating when this workflow was last saved. Patch them to valid
        # values so the graph actually passes validation.
        workflow["141"]["inputs"]["lighting_preset"] = "Auto-Match Original Image"
        workflow["141"]["inputs"]["secondary_pc_ip"] = "192.168.1.50"
        workflow["141"]["inputs"]["port"] = 11434
        workflow["141"]["inputs"]["model_name"] = "huihui_ai/qwen3-vl-abliterated:8b-instruct"
        workflow["141"]["inputs"]["idle_vram_timeout_min"] = 5
        workflow["141"]["inputs"]["seed"] = seed_val
        workflow["105:111"]["inputs"]["value"] = duration_seconds
        workflow["105:15"]["inputs"]["noise_seed"] = seed_val
        workflow["92"]["inputs"]["filename_prefix"] = filename_prefix or "video/WORKHORSE_MiniMax_H3"

        # LoRA chain (model flows 105:140 -> 105:138 -> 105:137). lora_config=None keeps
        # the template's shipped defaults; an explicit list lets the caller replace or
        # disable (strength 0) each slot.
        lora_node_ids = ["105:140", "105:138", "105:137"]
        if lora_config is not None:
            for i, node_id in enumerate(lora_node_ids):
                if i < len(lora_config):
                    cfg = lora_config[i]
                    workflow[node_id]["inputs"]["lora_name"] = cfg.get("lora_name", workflow[node_id]["inputs"]["lora_name"])
                    workflow[node_id]["inputs"]["strength_model"] = cfg.get("strength_model", 0)
                else:
                    workflow[node_id]["inputs"]["strength_model"] = 0

        return workflow

    def generate_image_to_video_minimax(self,
                                        source_image_path: Union[str, Path],
                                        prompt: str,
                                        duration_seconds: float = 10.0,
                                        lora_config: Optional[List[Dict[str, Any]]] = None,
                                        timeout_seconds: int = 900,
                                        dest_subdir: Optional[str] = None) -> Dict[str, Any]:
        """
        End-to-end MiniMax H3 image-to-video: uploads the source photo, builds the graph
        from the user's proven local template, renders, and saves the result video.
        Rendering is GPU/length dependent and can take several minutes.

        dest_subdir: see generate_image_to_video() - same per-brand social-post folder
        separation, never set by the chat tool itself.
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

        workflow = self.build_minimax_h3_i2v_workflow(
            source_image_name=uploaded_name,
            prompt=prompt,
            duration_seconds=duration_seconds,
            lora_config=lora_config
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            videos = self.wait_for_video_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not videos:
                return {"success": False, "error": "ComfyUI MiniMax H3 image-to-video generation timed out or yielded no video output"}

            first_vid = videos[0]
            staged_path = self.download_video(
                filename=first_vid["filename"],
                subfolder=first_vid.get("subfolder", ""),
                folder_type=first_vid.get("type", "output")
            )
        except RuntimeError as e:
            return {"success": False, "error": f"ComfyUI MiniMax H3 image-to-video generation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"ComfyUI MiniMax H3 image-to-video generation failed: {e}"}

        video_dir = (VIDEO_RENDERS_DIR / dest_subdir) if dest_subdir else VIDEO_RENDERS_DIR
        video_dir.mkdir(parents=True, exist_ok=True)
        dest_path = video_dir / staged_path.name
        staged_path.rename(dest_path)

        return {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_video_renders/{(dest_subdir + '/') if dest_subdir else ''}{dest_path.name}",
            "source_image": str(source_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

    def list_available_workflow_templates(self) -> Dict[str, List[str]]:
        """Scans WORKFLOW_TEMPLATES_DIR and returns an inventory grouped by category."""
        results: Dict[str, List[str]] = {}
        if not WORKFLOW_TEMPLATES_DIR.exists():
            return results
        for root, _, files in os.walk(WORKFLOW_TEMPLATES_DIR):
            rel_dir = os.path.relpath(root, WORKFLOW_TEMPLATES_DIR)
            category = "root" if rel_dir == "." else rel_dir.replace("\\", "/")
            json_files = [f for f in files if f.endswith(".json")]
            if json_files:
                results[category] = sorted(json_files)
        return results

    def load_workflow_template(self, template_name_or_rel_path: str) -> Dict[str, Any]:
        """Loads a workflow template by exact name, subpath, or fuzzy search across templates."""
        target = WORKFLOW_TEMPLATES_DIR / template_name_or_rel_path
        if target.exists() and target.is_file():
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        for path in WORKFLOW_TEMPLATES_DIR.rglob("*.json"):
            if path.name.lower() == template_name_or_rel_path.lower() or template_name_or_rel_path.lower() in str(path).lower():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        raise FileNotFoundError(f"Workflow template '{template_name_or_rel_path}' not found in {WORKFLOW_TEMPLATES_DIR}")

    def build_minimax_fasth3_workflow(self,
                                      prompt: str,
                                      mode: str = "t2v",
                                      first_frame_image_name: Optional[str] = None,
                                      last_frame_image_name: Optional[str] = None,
                                      longest_side: int = 864,
                                      duration_seconds: int = 5,
                                      width: int = 1024,
                                      height: int = 576,
                                      length: int = 124,
                                      seed: Optional[int] = None,
                                      filename_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds an ultra-fast 8-step MiniMax FastH3 workflow using Kitchen/Sparse Attention.
        mode can be:
          - 't2v': Text to Video
          - 'first_frame' or 'i2v': FirstFrame to Video
          - 'interpolation' or 'first_last': First and Last Frame Interpolation
        """
        if mode in ("first_frame", "i2v"):
            template_file = "video_fasth3/2. Minimax FastH3 - FirstFrame to Video.json"
        elif mode in ("interpolation", "first_last"):
            template_file = "video_fasth3/3. Minimax FastH3 - First and Last Frame.json"
        else:
            template_file = "video_fasth3/1. Minimax FastH3 - Text to Video.json"

        workflow = self.load_workflow_template(template_file)
        seed_val = seed if seed is not None else int(time.time() * 1000) % (2**31 - 1)

        # Patch First Frame (node 236) and Last Frame (node 244) on PixaromaLoadImageMini
        if first_frame_image_name and "236" in workflow and workflow["236"].get("class_type") == "PixaromaLoadImageMini":
            workflow["236"]["inputs"]["image"] = first_frame_image_name
            try:
                st = json.loads(workflow["236"]["inputs"].get("LoadImageMiniState", "{}"))
                st["orig_name"] = first_frame_image_name
                workflow["236"]["inputs"]["LoadImageMiniState"] = json.dumps(st)
            except Exception:
                pass

        if last_frame_image_name and "244" in workflow and workflow["244"].get("class_type") == "PixaromaLoadImageMini":
            workflow["244"]["inputs"]["image"] = last_frame_image_name
            try:
                st = json.loads(workflow["244"]["inputs"].get("LoadImageMiniState", "{}"))
                st["orig_name"] = last_frame_image_name
                workflow["244"]["inputs"]["LoadImageMiniState"] = json.dumps(st)
            except Exception:
                pass

        for nid, nval in workflow.items():
            ctype = nval.get("class_type", "")
            inputs = nval.get("inputs", {})
            if ctype == "CLIPTextEncode" and "text" in inputs:
                inputs["text"] = prompt
            elif ctype == "PixaromaPrompt":
                inputs["PromptState"] = json.dumps({"text": prompt, "order": "mine", "sep": ", "})
            elif ctype == "PixaromaLongestSide":
                inputs["LongestSideState"] = json.dumps({
                    "size": longest_side,
                    "ratio": "keep",
                    "step": 32,
                    "anchor": "center",
                    "allow_upscale": True,
                    "resample": "auto"
                })
            elif ctype == "PixaromaDuration":
                inputs["DurationState"] = json.dumps({
                    "seconds": duration_seconds,
                    "fps": 24,
                    "step": 17,
                    "plus": 5,
                    "minFrames": 5,
                    "mode": "recipe",
                    "formula": ""
                })
            elif ctype == "PixaromaSeed":
                inputs["SeedState"] = json.dumps({"runSeed": seed_val})
                inputs["seed"] = seed_val
            elif ctype == "MiniMaxH3ImageToVideo":
                if "width" in inputs and not isinstance(inputs["width"], list):
                    inputs["width"] = width
                if "height" in inputs and not isinstance(inputs["height"], list):
                    inputs["height"] = height
                if "length" in inputs and not isinstance(inputs["length"], list):
                    inputs["length"] = length
            elif ctype == "KSampler":
                if not isinstance(inputs.get("seed"), list):
                    inputs["seed"] = seed_val
            elif ctype in ("PixaromaSaveMp4", "SaveImage", "VHS_VideoCombine"):
                if "filename_prefix" in inputs:
                    inputs["filename_prefix"] = filename_prefix or f"video/FastH3_{mode}_{seed_val}"

        return workflow

    def generate_video_fasth3(self,
                              first_frame_path: Union[str, Path],
                              prompt: str,
                              last_frame_path: Optional[Union[str, Path]] = None,
                              duration_seconds: int = 5,
                              longest_side: int = 864,
                              seed: Optional[int] = None,
                              timeout_seconds: int = 600,
                              dest_subdir: Optional[str] = None) -> Dict[str, Any]:
        """
        End-to-end 8-step MiniMax FastH3 FirstFrame-to-Video (or First-and-Last-Frame)
        generation on ComfyUI (RTX 5070 Ti).
        """
        conn = self.check_connection()
        if not conn.get("online"):
            return {"success": False, "error": f"ComfyUI on Main PC is offline ({conn.get('host')}:{conn.get('port')})."}

        first_frame_path = Path(first_frame_path)
        if not first_frame_path.exists():
            return {"success": False, "error": f"First frame image not found: {first_frame_path}"}

        try:
            up_first = self.upload_image_to_comfy(first_frame_path)
            up_last = self.upload_image_to_comfy(Path(last_frame_path)) if last_frame_path else None
        except Exception as e:
            return {"success": False, "error": f"Failed to upload frame image(s) to ComfyUI: {e}"}

        mode = "first_last" if up_last else "first_frame"
        workflow = self.build_minimax_fasth3_workflow(
            prompt=prompt,
            mode=mode,
            first_frame_image_name=up_first,
            last_frame_image_name=up_last,
            longest_side=longest_side,
            duration_seconds=duration_seconds,
            seed=seed,
            filename_prefix=f"video/FastH3_{first_frame_path.stem}"
        )

        try:
            queued = self.queue_prompt(workflow)
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": f"No prompt_id returned by ComfyUI. node_errors: {queued.get('node_errors')}"}

            videos = self.wait_for_video_execution(prompt_id, timeout_seconds=timeout_seconds)
            if not videos:
                return {"success": False, "error": "ComfyUI FastH3 video generation timed out or yielded no video output"}

            first_vid = videos[0]
            staged_path = self.download_video(
                filename=first_vid["filename"],
                subfolder=first_vid.get("subfolder", ""),
                folder_type=first_vid.get("type", "output")
            )
        except Exception as e:
            return {"success": False, "error": f"ComfyUI FastH3 video generation failed: {e}"}

        video_dir = (VIDEO_RENDERS_DIR / dest_subdir) if dest_subdir else VIDEO_RENDERS_DIR
        video_dir.mkdir(parents=True, exist_ok=True)
        dest_path = video_dir / staged_path.name
        staged_path.rename(dest_path)

        return {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "mode": mode,
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
                    "vae": ["5", 0],
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
                    "fusion_weight_max": 1.0,
                    "fusion_weight_min": 0.0,
                    "train_step": 1000,
                    "use_gray": True
                },
                "class_type": "ApplyPulidFlux"
            },
            "17": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage"
            },
            "21": {
                "inputs": {
                    "model": ["16", 0],
                    "sage_attention": "auto"
                },
                "class_type": "PathchSageAttentionKJ"
            },
            "18": {
                "inputs": {
                    "seed": seed_val,
                    "steps": steps,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                    "model": ["21", 0],
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

        result: Dict[str, Any] = {
            "success": True,
            "file_path": str(dest_path),
            "filename": dest_path.name,
            "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
            "source_image": str(source_image_path),
            "reference_face_image": str(reference_face_image_path),
            "host_used": f"{self.host}:{self.port}"
        }

        if self.qc_cfg.get("auto_qc_enabled", True):
            audit = self.run_iris_qc_audit(dest_path, original_prompt=prompt)
            result["qc_audit"] = audit
            self._log_audit_record(dest_path.name, audit, f"[SUBJECT SWAP] {prompt}", 1, passed=audit.get("passed", True))

        try:
            from pipeline.stages.scrubber import metadata_scrubber
            metadata_scrubber.scrub_image(dest_path)
        except Exception as ce:
            print(f"[SCRUBBER] Warning: Metadata scrub failed: {ce}")

        return result

    def run_iris_qc_audit(self, image_path: Path, original_prompt: str = "") -> Dict[str, Any]:
        """
        IRIS [77 Ir] Quality Control Gate:
        Uses local Qwen-VL (GPU 0) to scrutinize image for:
        - Extra limbs, distorted fingers, impossible anatomy
        - Facial deformation (asymmetric eyes, melted teeth)
        - Hallucinations and prompt deviation
        - Commercial aesthetic score (1-10)
        - Strict 100% SFW compliance (zero nudity, lingerie, boudoir, or suggestive content)
        """
        print(f"[Iris QC Gate] Inspecting rendered image: {image_path.name}...")
        audit_prompt = f"""You are IRIS [77 Ir], Senior Computer Vision Quality Control Auditor for Creator Media Lab.
Perform a forensic inspection of this generated AI photograph.
Original Request: "{original_prompt or 'Photorealistic commercial studio portrait / creator creative'}"

Scrutinize carefully for common generative diffusion flaws:
1. ANATOMY & LIMBS: Look closely at arms, legs, hands, and fingers. Are there extra limbs, extra fingers (6 fingers), missing digits, or mutated joints?
2. FACIAL INTEGRITY: Check eyes, pupils, teeth, and skin. Are pupils round and symmetrical? Any melted or unnatural face warping?
3. ARTIFACTS: Check for floating objects, severe blur, plastic skin texture, or distorted seams.
4. OVERALL AESTHETICS: Rate composition, studio lighting, and realism from 1.0 to 10.0.
5. SFW VERIFICATION - SEXY & ALLURING IS WELCOME, GENUINE NUDITY IS STRICTLY FORBIDDEN:
- PERMITTED & ENCOURAGED: Bikinis, swimsuits, sexy dresses, tight bodycon dresses, cute low-cut tops with tasteful cleavage, little tank tops, crop tops, sleeveless cocktail dresses, backless dresses, and alluring summer fashion. These are 100% commercial social-media approved and should PASS.
- STRICTLY FORBIDDEN (REJECT): Genuine toplessness (bare breasts or bare nipples with no top on), exposed genitals/buttocks, fully transparent/sheer fabric clearly revealing nipples, or explicit adult sexual acts.
6. FOREGROUND OCCLUSION & UNWANTED OBJECTS (CRITICAL): Look closely at what is in front of the subject. Are there unwanted objects, camera gear, microphone boom arms, tripod legs, floating artifacts, poles, or messy clutter awkwardly blocking or cutting across the subject's face, eyes, neck, or body? The subject must be cleanly visible with zero obstructing objects in front of them.

Respond strictly in valid JSON format:
{{
  "passed": true,
  "is_sfw": true,
  "aesthetic_score": 8.5,
  "extra_limbs_detected": false,
  "facial_distortion_detected": false,
  "nudity_or_nsfw_detected": false,
  "foreground_occlusion_detected": false,
  "defects_summary": "Clean hands, natural five fingers, symmetric facial lighting, unobstructed subject.",
  "anatomy_notes": "Proper arm and finger geometry.",
  "modesty_notes": "Subject is tastefully attired in commercial fashion (bikini, dress, cute top, or casual wear) with zero explicit nudity. 100% SFW.",
  "occlusion_notes": "Clean direct sightline to subject without obstructing foreground objects.",
  "recommendation": "APPROVED"
}}
If ANY extra limbs, mutated hands, or severe facial defects are found, set "passed": false and recommendation to "RETRY_NEW_SEED".
If the subject is genuinely topless (bare breasts/nipples exposed with no top), has exposed genitals, or has completely sheer transparent fabric showing nipples, set "passed": false, "is_sfw": false, "nudity_or_nsfw_detected": true, and recommendation to "REJECT_NSFW_CONTENT".
If the subject is wearing a bikini, cute low-cut top, tight dress, little tank top, or sexy attire where breasts are covered by fabric, mark "is_sfw": true, "nudity_or_nsfw_detected": false, and approve!
If ANY unwanted objects, microphones, gear, or clutter in front of the subject block or obscure their face or body, set "passed": false, "foreground_occlusion_detected": true, and recommendation to "RETRY_NEW_PROMPT".
"""
        system_prompt = (
            "You are Iris, an expert AI art auditor. Output strictly valid QC JSON.\n"
            + get_comfyui_context("qc")
            + "\nInspect pixels only; return the QC JSON schema requested, never an execution graph."
        )

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
            if isinstance(parsed, dict) and parsed.get("error"):
                raise RuntimeError(str(parsed["error"]))
        except Exception as e:
            print(f"[Iris QC Gate] Fallback QC heuristic due to: {e}")
            # Per Commander's decision: QC stays fail-open for internal draft review when infra is down,
            # but is_sfw is strictly False so that public social posters (Herald, Pinterest) fail closed.
            parsed = {
                "passed": True,
                "is_sfw": False,
                "aesthetic_score": 8.0,
                "extra_limbs_detected": False,
                "facial_distortion_detected": False,
                "nudity_or_nsfw_detected": False,
                "foreground_occlusion_detected": False,
                "defects_summary": "Vision QC check could not be completed (model unavailable/error) - approved by fail-open policy for internal draft, NOT certified SFW.",
                "anatomy_notes": "Not inspected - QC infrastructure unavailable.",
                "recommendation": "APPROVED_QC_UNAVAILABLE",
                "qc_infra_unavailable": True,
                "qc_infra_error": str(e)
            }

        # Secondary prompt-level guardrail: quarantine any image generated from explicit adult prompt
        nsfw_prompt_keywords = [
            "nude", "nudity", "naked", "topless", "bare breasts", "exposed nipples",
            "genitals", "porn", "fetish", "camgirl", "sex work", "xxx", "boudoir", "lingerie"
        ]
        if any(k in (original_prompt or "").lower() for k in nsfw_prompt_keywords):
            parsed["nudity_or_nsfw_detected"] = True
            parsed["is_sfw"] = False
            parsed["passed"] = False
            parsed["recommendation"] = "REJECT_NSFW_CONTENT"
            parsed["modesty_notes"] = "Prompt contains adult/nude keywords. Quarantined by strict anti-nudity policy."
            print(f"[Iris QC Alert] STRICT NSFW REJECTION: Prompt contains adult keyword ({image_path.name})")

        # Tertiary deterministic pixel-level skin density firewall (Unbypassable mathematical check)
        try:
            from pipeline.stages.nsfw_firewall import evaluate_image_sfw
            is_sfw_pixel, pixel_reason, metrics = evaluate_image_sfw(image_path)
            if not is_sfw_pixel:
                parsed["nudity_or_nsfw_detected"] = True
                parsed["is_sfw"] = False
                parsed["passed"] = False
                parsed["recommendation"] = "REJECT_NSFW_CONTENT"
                parsed["modesty_notes"] = f"Deterministic pixel firewall rejection: {pixel_reason}"
                print(f"[Iris QC Alert] DETERMINISTIC PIXEL REJECTION: {pixel_reason} ({image_path.name})")
        except Exception as pfe:
            print(f"[Iris QC Warning] Pixel firewall check error: {pfe}")

        # Apply QC gate thresholds
        min_score = self.qc_cfg.get("min_quality_score", 7.5)
        if not parsed.get("qc_infra_unavailable"):
            if parsed.get("nudity_or_nsfw_detected") or parsed.get("is_sfw") is False:
                parsed["passed"] = False
                parsed["is_sfw"] = False
                parsed["recommendation"] = "REJECT_NSFW_CONTENT"
                print(f"[Iris QC Alert] STRICT NSFW REJECTION: Nudity or adult content detected in {image_path.name}")
            else:
                parsed["is_sfw"] = True
        else:
            # QC infra unavailable: fail-open for internal draft, but is_sfw stays False
            parsed["is_sfw"] = False

        if parsed.get("extra_limbs_detected") and self.qc_cfg.get("reject_on_extra_limbs", True):
            parsed["passed"] = False
            parsed["recommendation"] = "RETRY_NEW_SEED"
        if parsed.get("facial_distortion_detected") and self.qc_cfg.get("reject_on_facial_distortion", True):
            parsed["passed"] = False
            parsed["recommendation"] = "RETRY_NEW_SEED"
        if parsed.get("foreground_occlusion_detected") and self.qc_cfg.get("reject_on_foreground_occlusion", True):
            parsed["passed"] = False
            parsed["recommendation"] = "RETRY_NEW_PROMPT"
            print(f"[Iris QC Alert] FOREGROUND OCCLUSION REJECTION: Unwanted objects blocking subject in {image_path.name}")
        score_val = parsed.get("aesthetic_score")
        if (float(score_val) if score_val is not None else 0.0) < min_score:
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
                           brand_target: Optional[str] = None,
                           prompt_alternatives: Optional[List[str]] = None) -> Dict[str, Any]:
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
                brand_target=brand_target,
                prompt_alternatives=prompt_alternatives
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
                                    brand_target: Optional[str] = None,
                                    prompt_alternatives: Optional[List[str]] = None) -> Dict[str, Any]:
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
        staged_path = None

        # Prepare queue of alternative prompts for retry re-rolls if Iris rejects
        alternatives_pool = list(prompt_alternatives) if prompt_alternatives else []
        quarantine_dir = STAGING_DIR / "qc_rejected"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        brand_quarantine_dir = BASE_DIR / "workspace" / "brand_assets" / "qc_rejected"
        brand_quarantine_dir.mkdir(parents=True, exist_ok=True)
        last_quarantined_path = None

        while attempt <= max_retries:
            attempt += 1
            seed = int(time.time() * 1000 + attempt * 77) % (2**31 - 1)
            
            # Use original prompt for attempt 1; pick fresh new prompt for retries
            if attempt == 1:
                active_prompt = positive_prompt
            else:
                if alternatives_pool:
                    active_prompt = alternatives_pool.pop(0)
                    print(f"[ComfyUIBridge] Re-rolling fresh prompt variant for attempt {attempt}: '{active_prompt[:60]}...'")
                else:
                    active_prompt = self._mutate_prompt_for_mood_variety(positive_prompt, attempt)
                    print(f"[ComfyUIBridge] Generated diverse mood prompt variant for attempt {attempt}: '{active_prompt[:60]}...'")

            print(f"[ComfyUIBridge] Generation Attempt {attempt}/{max_retries + 1} (Seed: {seed})...")

            workflow = self.build_standard_workflow(
                positive_prompt=active_prompt,
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
                brand_target=brand_target,
                style_preset=style_preset
            )

            task_id = f"comfy_attempt_{attempt}_{seed}"
            try:
                from pipeline.stages.ai_operator import active_task_tracker
                active_task_tracker.start_task(
                    agent="muse",
                    sub_agent="forge",
                    task_desc=f"Muse [34 Se] & Forge [28 Ni]: Rendering visual on ComfyUI (RTX 5070 Ti) Attempt {attempt}/{max_retries + 1}...",
                    task_id=task_id,
                    progress=30
                )
            except Exception:
                active_task_tracker = None

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
                    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
                    dest_path = RENDERS_DIR / staged_path.name
                    shutil.move(str(staged_path), str(dest_path))

                    try:
                        from pipeline.stages.scrubber import metadata_scrubber
                        metadata_scrubber.scrub_image(dest_path)
                    except Exception as ce:
                        print(f"[SCRUBBER] Warning: Metadata scrub failed: {ce}")

                    return {
                        "success": True,
                        "file_path": str(dest_path),
                        "filename": dest_path.name,
                        "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
                        "attempt": attempt,
                        "qc_bypassed": True
                    }

                # Run Iris Vision QC Gate
                if active_task_tracker:
                    active_task_tracker.start_task(
                        agent="iris",
                        task_desc=f"Iris [77 Ir]: Forensically auditing visual render on GPU 0 (Qwen 8B-VL)...",
                        task_id=task_id,
                        progress=70
                    )

                audit = self.run_iris_qc_audit(staged_path, original_prompt=active_prompt)
                last_audit = audit

                if audit.get("passed"):
                    print(f"[Iris QC Gate] PASSED! Score: {audit.get('aesthetic_score')}/10. Approved for production.")
                    brand_folder = (BASE_DIR / "workspace" / "brand_assets" / brand_target) if brand_target else RENDERS_DIR
                    brand_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = brand_folder / staged_path.name
                    shutil.move(str(staged_path), str(dest_path))
                    if brand_target:
                        try:
                            shutil.copy2(dest_path, RENDERS_DIR / staged_path.name)
                        except Exception:
                            pass
                    saved_file = dest_path

                    # SCRUBBER [82 Pb] Pre-Flight EXIF Scrub (Zero metadata leaks)
                    if active_task_tracker:
                        active_task_tracker.start_task(
                            agent="scrubber",
                            task_desc="Scrubber [82 Pb]: Scrubbing EXIF metadata & certifying clean binary...",
                            task_id=task_id,
                            progress=95
                        )
                    try:
                        from pipeline.stages.scrubber import metadata_scrubber
                        metadata_scrubber.scrub_image(dest_path)
                    except Exception as ce:
                        print(f"[SCRUBBER] Warning: Metadata scrub failed: {ce}")

                    # Log to audit history
                    self._log_audit_record(dest_path.name, audit, active_prompt, attempt, passed=True)

                    return {
                        "success": True,
                        "file_path": str(dest_path),
                        "filename": dest_path.name,
                        "url_path": f"/static/brand_assets/comfy_renders/{dest_path.name}",
                        "attempts_taken": attempt,
                        "qc_audit": audit,
                        "is_sfw": audit.get("is_sfw", False),
                        "host_used": f"{self.host}:{self.port}"
                    }
                else:
                    rejection_reason = audit.get("defects_summary") or audit.get("recommendation")
                    print(f"[Iris QC Gate] FAILED attempt {attempt}! Anomalies: {rejection_reason}. Quarantining to qc_rejected and restarting with fresh prompt...")
                    
                    # IMMEDIATELY QUARANTINE REJECTED RENDER TO qc_rejected/
                    if staged_path and staged_path.exists():
                        quarantine_dest = quarantine_dir / staged_path.name
                        try:
                            shutil.move(str(staged_path), str(quarantine_dest))
                            try:
                                shutil.copy2(str(quarantine_dest), str(brand_quarantine_dir / staged_path.name))
                            except Exception:
                                pass
                            last_quarantined_path = quarantine_dest
                            print(f"[Iris QC Quarantine] Moved unapproved render to: {quarantine_dest}")
                        except Exception as qe:
                            print(f"[Iris QC Quarantine] Failed to move {staged_path.name}: {qe}")

                    # Reinforce negative prompt for next attempt to suppress defects & occlusions
                    current_neg += ", (extra limbs, deformed hands, fused fingers, unnatural anatomy, objects blocking subject, microphone in front of face, tripod obscuring body:1.4)"
                    self._log_audit_record(staged_path.name if staged_path else "unknown", audit, active_prompt, attempt, passed=False)

            except Exception as e:
                print(f"[ComfyUIBridge] Error during attempt {attempt}: {e}")
            finally:
                if active_task_tracker:
                    active_task_tracker.finish_task(task_id)

        # All retries exhausted and Iris genuinely rejected every attempt
        return {
            "success": False,
            "error": "Image failed Iris strict QC threshold after maximum retries - all attempts quarantined to qc_rejected.",
            "quarantined_file_path": str(last_quarantined_path) if last_quarantined_path else (str(quarantine_dir / staged_path.name) if staged_path else ""),
            "qc_audit": last_audit,
            "last_qc_audit": last_audit,
            "is_sfw": False,
            "attempts_taken": attempt
        }

    def _mutate_prompt_for_mood_variety(self, base_prompt: str, attempt: int) -> str:
        """
        When Iris rejects an image (e.g. for anatomy, occlusion, or modesty flaws)
        and no explicit alternatives were passed, this helper synthesizes a fresh,
        high-converting prompt variant across the 5 approved commercial moods
        (Sexy/Alluring, Playful, Cute, Cozy, High-Fashion Action) rather than repeating
        the same failed prompt with a new seed.
        """
        mood_variants = [
            "Alluring commercial fashion photograph, gorgeous creator wearing an elegant emerald satin cowl-neck slip dress with delicate gold jewelry, warm ambient candlelight, soft rim lighting, confident inviting expression, professional 85mm portrait, 8k resolution, raw photo quality",
            "Cute sunlit studio portrait, radiant creator wearing a white ribbed crop tank top and high-waisted shorts, natural unretouched skin, warm window light, playful confident smile, clear line of sight with zero occluding objects, crisp 50mm lens",
            "Playful golden hour lifestyle photo, attractive creator wearing a stylish yellow summer sundress spinning gracefully on a sun-drenched terrace, radiant backlit hair glow, laughing candid expression, cinematic motion, 50mm f/1.8 prime",
            "Cozy morning creative portrait, creator in an oversized chunky oat cable-knit off-shoulder sweater holding a warm ceramic coffee mug, sitting beside sunlit loft window, serene inviting smile, warm amber light, authentic 35mm film aesthetic",
            "Vibrant luxury resort photography, attractive creator wearing a chic bronze-accented string bikini relaxing poolside on a teak lounger, sun-kissed radiant skin, turquoise water reflection, beautiful tropical day, 85mm commercial lens",
            "Creative photographer in a chic black camisole actively adjusting dials on an ergonomic color-grading console, glowing dual monitors displaying vivid film palettes, warm tungsten desk lamp, high production value, 50mm lens"
        ]
        idx = (attempt - 2) % len(mood_variants) if attempt > 1 else random.randint(0, len(mood_variants) - 1)
        return mood_variants[idx]

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
            "is_sfw": audit.get("is_sfw", False) if passed else False,
            "attempt": attempt,
            "prompt": prompt,
            "aesthetic_score": audit.get("aesthetic_score"),
            "extra_limbs": audit.get("extra_limbs_detected"),
            "facial_distortion": audit.get("facial_distortion_detected"),
            "nudity_or_nsfw": audit.get("nudity_or_nsfw_detected", False),
            "recommendation": audit.get("recommendation"),
            "notes": audit.get("defects_summary")
        })

        try:
            with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(records[:100], f, indent=2)
        except Exception as e:
            print(f"[ComfyUIBridge] Error saving audit log: {e}")


# Global singleton
comfy_bridge = ComfyUIBridge()
