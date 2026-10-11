"""Task-specific runtime grounding from the Commander's local ComfyUI curriculum."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Literal

GUIDE_PATH = Path(__file__).resolve().parents[1] / "LLM training" / "comfyui_llm_learning_guide.md"
MAX_CONTEXT_CHARS = 14000
LOGGER = logging.getLogger(__name__)

ComfyTask = Literal["operator", "image_prompt", "video_prompt", "pose_prompt", "inspiration", "qc"]

TASK_MODULES: dict[ComfyTask, tuple[int, ...]] = {
    "operator": (1, 17),
    "image_prompt": (6, 3, 13),
    "video_prompt": (6, 11, 3),
    "pose_prompt": (6, 14),
    "inspiration": (6, 3, 13),
    "qc": (2, 18),
}

TOPIC_MODULES = (
    (("inpaint", "outpaint", "mask", "sam2", "segment anything"), (8, 9)),
    (("relight", "ic-light"), (10,)),
    (("trellis", "pixal", "3d", "mesh", "pbr", "ltx", "minimax", "hailuo", "flux"), (12,)),
    (("lora", "adapter"), (13,)),
    (("upscal", "hi-res", "hires", "controlnet", "regional", "faceid", "gguf", "fp8", "freeu", "pag", "wildcard", "liveportrait", "in-graph"), (14,)),
    (("video", "wan", "svd", "animate", "motion"), (11, 6, 3)),
    (("img2img", "image-to-image", "i2i"), (7,)),
    (("flux", "sdxl", "sd3", "sd 3", "sd1.5"), (3, 6)),
    (("sampler", "sampling", "scheduler"), (5,)),
    (("loader", "decoder", "saver", "node classes"), (4,)),
    (("invariant", "anti-pattern", "verification rules"), (16,)),
)

SECTION_TOPICS = {
    12: {
        "12.1": ("flux",),
        "12.2": ("ltx",),
        "12.3": ("minimax", "hailuo"),
        "12.4": ("trellis", "pixal", "3d", "mesh", "pbr"),
    },
    13: {
        "13.1": ("math", "rank"),
        "13.2": ("strength", "lora"),
        "13.3": ("identity", "style", "acceleration"),
        "13.4": ("chain", "stack", "lora"),
        "13.5": ("block",),
    },
    14: {
        "14.1": ("upscal", "hi-res", "hires", "tiled"),
        "14.2": ("controlnet",),
        "14.3": ("regional", "multi-subject", "pose"),
        "14.4": ("faceid", "ip-adapter"),
        "14.5": ("freeu", "pag"),
        "14.6": ("gguf", "fp8", "quantiz", "vram"),
        "14.7": ("wildcard", "in-graph", "llm"),
        "14.8": ("audio", "liveportrait"),
    },
}

BLUEPRINT_TOPICS = (
    ("M", ("gguf", "freeu", "pag")),
    ("G", ("trellis", "pixal", "3d", "mesh", "pbr")),
    ("E", ("relight", "ic-light")),
    ("D", ("inpaint", "sam2", "mask")),
    ("I", ("upscal", "hi-res", "hires")),
    ("J", ("controlnet",)),
    ("K", ("regional", "multi-subject")),
    ("L", ("faceid",)),
    ("H", ("lora",)),
    ("F", ("reference-to-video", "ref-to-video")),
    ("C", ("svd",)),
    ("B", ("flux",)),
    ("A", ("sdxl",)),
)

OPERATING_RULES = """--- WORKHORSE COMFYUI KNOWLEDGE ---
This is runtime reference material, NOT fine-tuning or proof of installed capabilities.
Keep your WORKHORSE agent identity, tool names, authorization gates and response contract.
For image/video prompt tasks, return prompt text in the requested format, NOT workflow JSON.
For requested execution graphs, use API prompt JSON, not canvas/UI workflow JSON.
Treat examples and numeric settings as model/version-dependent guidance, not universal laws.
Live ComfyUI /object_info schemas, model inventory, configured templates and tool results
take precedence over this reference. Never invent installed nodes, models or output slots.
Check required inputs, link IDs/slots/types, acyclic connectivity and an output node.
Distinguish FLUX guidance from SDXL CFG/negative conditioning; match latent, VAE and encoders
to the actual model. Preserve existing tested client workflows and their identity LoRAs.
Do not change QC pass/fail policy, expose private media, bypass authorization or claim a
render/validation succeeded without tool evidence. Pixel QC cannot prove graph correctness.
"""


def _modules(text: str) -> dict[int, str]:
    headings = list(re.finditer(r"^## Module (\d+):[^\n]*", text, re.MULTILINE))
    return {
        int(match.group(1)): text[match.start():headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip()
        for index, match in enumerate(headings)
    }


def _excerpts(number: int, module: str, query: str) -> list[str]:
    if number not in SECTION_TOPICS:
        return [module]
    headings = list(re.finditer(r"^### (\d+\.\d+)[^\n]*", module, re.MULTILINE))
    topics = SECTION_TOPICS[number]
    selected = [key for key, words in topics.items() if any(word in query for word in words)]
    if not selected:
        selected = {12: ["12.1"], 13: ["13.2", "13.4"], 14: ["14.3"]}[number]
    return [
        module[match.start():headings[index + 1].start() if index + 1 < len(headings) else len(module)].strip()
        for index, match in enumerate(headings)
        if match.group(1) in selected
    ]


def get_comfyui_context(task: ComfyTask, query: str = "") -> str:
    """Return bounded, fresh excerpts; report unavailable guidance explicitly."""
    if task not in TASK_MODULES:
        raise ValueError(f"Unknown ComfyUI knowledge task: {task}")

    try:
        text = GUIDE_PATH.read_text(encoding="utf-8-sig")
        modules = _modules(text)
        missing = set(range(1, 19)) - modules.keys()
        if missing:
            raise ValueError(f"Missing curriculum modules: {sorted(missing)}")
        if any(not module.partition("\n")[2].strip() for module in modules.values()):
            raise ValueError("Curriculum contains an empty module")
    except (OSError, UnicodeError, ValueError) as exc:
        LOGGER.warning("ComfyUI training guide unavailable at %s: %s", GUIDE_PATH, exc)
        return (
            OPERATING_RULES
            + "COMFYUI TRAINING GUIDE UNAVAILABLE: " + str(exc) + "\n"
            + "Tell the Commander this reference could not be loaded; do not claim guide-backed expertise.\n"
            + "--- END COMFYUI KNOWLEDGE ---"
        )[:MAX_CONTEXT_CHARS]

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    context = OPERATING_RULES + f"Source: LLM training/comfyui_llm_learning_guide.md | SHA256: {digest}\n"
    lowered = query.casefold()
    selected = list(TASK_MODULES[task])
    if task != "qc":
        for keywords, numbers in TOPIC_MODULES:
            if any(keyword in lowered for keyword in keywords):
                selected.extend(numbers)
    if task == "operator":
        selected.extend((2, 18))

    excerpts = [
        excerpt
        for number in dict.fromkeys(selected)
        for excerpt in _excerpts(number, modules[number], lowered)
    ]
    if task == "operator" and any(word in lowered for word in ("workflow", "graph", "blueprint", "api json")):
        blueprint = next(
            (letter for letter, words in BLUEPRINT_TOPICS if any(word in lowered for word in words)),
            None
        )
        if blueprint:
            headings = list(re.finditer(r"^### Blueprint ([A-M]):[^\n]*", modules[15], re.MULTILINE))
            for index, match in enumerate(headings):
                if match.group(1) == blueprint:
                    excerpt = modules[15][match.start():headings[index + 1].start() if index + 1 < len(headings) else len(modules[15])].strip()
                    excerpts.insert(2, excerpt)
                    break

    # Keep excerpts whole: truncating an API JSON example can teach an invalid graph.
    omitted = False
    for section in excerpts:
        excerpt = "\n\n" + section
        if len(context) + len(excerpt) > MAX_CONTEXT_CHARS - 250:
            omitted = True
        else:
            context += excerpt
    if omitted:
        context += "\n\nContext budget: additional sections omitted; consult the local guide for full details."
    context += "\n\nWORKHORSE response format and live schemas override reference examples above.\n"
    return context + "--- END COMFYUI KNOWLEDGE ---"
