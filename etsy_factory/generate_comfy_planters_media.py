"""Generate photorealistic ComfyUI listing media for 8 Geometric Planters with Saucers + Hero Cluster.
Executed on remote ComfyUI (RTX 5070 Ti) with authentic matte PLA textures,
realistic contact shadows, living succulents, potting soil, and natural tabletop grounding (ZERO floating).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge

PLANTER_CONCEPTS = [
    (
        "01_Hex_Taper",
        "photorealistic commercial studio product photography of a modern 3d printed hexagonal tapered geometric planter pot with matching saucer base, potted with a lush green echeveria succulent in dark potting soil, printed in warm terracotta clay matte PLA filament with fine authentic 3d print layer line texture, resting firmly on a clean light oak tabletop, soft realistic contact occlusion shadow under saucer, crisp studio key light, shallow depth of field, 8k commercial catalog photo"
    ),
    (
        "02_Octagon_Taper",
        "photorealistic commercial studio product photography of a modern 3d printed octagonal tapered geometric planter with matching saucer base, potted with a miniature jade succulent plant in dark soil, printed in forest sage moss green matte PLA filament with fine 3d print layer line texture, resting firmly on a modern tabletop surface, natural contact shadow beneath saucer, soft studio window light, 8k catalog photo"
    ),
    (
        "03_Twisted_Hex",
        "photorealistic commercial studio product photography of an architectural 3d printed twisted hexagonal spiral geometric planter with matching saucer, potted with a healthy trailing string of pearls succulent, printed in desert warm almond sand matte PLA filament with micro layer line texture, resting firmly on clean wooden desk surface, soft contact shadow beneath product, 8k commercial photo"
    ),
    (
        "04_Twisted_Square",
        "photorealistic commercial studio product photography of a contemporary 3d printed twisted square spiral faceted geometric planter with matching saucer, potted with a spiky haworthia zebra succulent in rich soil, printed in matte stealth charcoal graphite PLA filament with subtle print layer lines, resting firmly on tabletop surface, natural contact shadow beneath product, studio lighting, 8k catalog photo"
    ),
    (
        "05_Twisted_Triangle",
        "photorealistic commercial studio product photography of a minimalist 3d printed twisted triangular spiral geometric planter with matching saucer, potted with a blooming sedum succulent, printed in matte denim slate blue PLA filament with authentic fine layer line texture, resting firmly on Scandinavian birch wood surface, soft realistic contact shadow, dramatic soft key light, 8k catalog photo"
    ),
    (
        "06_Faceted_Round",
        "photorealistic commercial studio product photography of a modern 3d printed multifaceted diamond round geometric planter with matching saucer, potted with a plump pastel moonstone succulent, printed in matte warm ochre honey gold PLA filament with fine 3d print layer lines, resting firmly on clean modern tabletop, soft contact shadow beneath product, 8k commercial catalog photo"
    ),
    (
        "07_Tall_Hex_Vase",
        "photorealistic commercial studio product photography of an elegant tall 3d printed hexagonal faceted vase planter with matching saucer, potted with a dwarf snake plant shoot, printed in matte dusty rose clay PLA filament with subtle fine layer line texture, resting firmly on clean oak tabletop, natural contact shadow beneath saucer, studio lighting, 8k commercial photo"
    ),
    (
        "08_Wide_Bowl",
        "photorealistic commercial studio product photography of a 3d printed wide low-profile faceted bowl geometric planter with matching saucer, potted as a miniature desktop succulent rock garden with dark soil, printed in matte bone white silk PLA filament with authentic fine print layer lines, resting firmly on clean tabletop, soft contact shadow, 8k commercial catalog photo"
    )
]

HERO_CLUSTER_PROMPT = (
    "photorealistic commercial studio product photography of a stunning curated cluster of three 3d printed geometric faceted planters with matching saucers: "
    "a warm terracotta hexagonal planter with a green echeveria succulent, a forest sage green octagonal planter with a jade plant, and a bone white faceted bowl planter, "
    "arranged together resting firmly on a clean warm wooden tabletop, soft realistic contact occlusion shadows beneath each saucer, "
    "natural FDM 3d printed matte PLA texture with micro layer lines, warm studio lighting, 8k commercial catalog hero photo"
)

OUT_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\geometric_planters_stl_3mf_glb\work_renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

NEG = "blurry, floating, hovering, fake, oversaturated neon, plastic toy look, bad geometry, cropped, low quality, distorted, extra limbs, watermark, text, signature"


def generate_all_media():
    print(f"Starting ComfyUI media generation for {len(PLANTER_CONCEPTS)} planters + hero cluster...")

    # 1. Generate the 8 single product media images
    for idx, (name, prompt) in enumerate(PLANTER_CONCEPTS, 1):
        dest_img = OUT_DIR / f"comfy_single_{idx:02d}.png"
        if dest_img.exists() and dest_img.stat().st_size > 50000:
            print(f"  [{idx}/8] Already exists: {dest_img.name}")
            continue

        t0 = time.time()
        print(f"  [{idx}/8] Generating {name} on ComfyUI RTX 5070 Ti...")
        res = comfy_bridge.generate_and_audit(
            positive_prompt=prompt,
            negative_prompt=NEG,
            width=1024,
            height=1024,
            steps=22,
            cfg=6.0,
            auto_qc=False
        )
        if res.get("success") and res.get("file_path"):
            src = Path(res["file_path"])
            src.replace(dest_img)
            print(f"    -> Saved {dest_img.name} in {time.time()-t0:.1f}s ({dest_img.stat().st_size / 1024:.0f} KB)")
        else:
            print(f"    -> FAILED: {res.get('error')}")

    # 2. Generate the Hero Cluster media image
    hero_dest = OUT_DIR / "comfy_cluster_hero.png"
    if not (hero_dest.exists() and hero_dest.stat().st_size > 50000):
        t0 = time.time()
        print("  [Hero] Generating Hero Cluster on ComfyUI RTX 5070 Ti...")
        res_hero = comfy_bridge.generate_and_audit(
            positive_prompt=HERO_CLUSTER_PROMPT,
            negative_prompt=NEG,
            width=1024,
            height=1024,
            steps=24,
            cfg=6.0,
            auto_qc=False
        )
        if res_hero.get("success") and res_hero.get("file_path"):
            src = Path(res_hero["file_path"])
            src.replace(hero_dest)
            print(f"    -> Saved {hero_dest.name} in {time.time()-t0:.1f}s ({hero_dest.stat().st_size / 1024:.0f} KB)")
        else:
            print(f"    -> FAILED: {res_hero.get('error')}")

    print("\nComfyUI Planters Media Generation Complete!")


if __name__ == "__main__":
    generate_all_media()
