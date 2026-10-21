"""Generate photorealistic ComfyUI listing media for 8 sculpted high-demand keychains.
Executed on remote ComfyUI (RTX 5070 Ti) with authentic matte PLA textures,
realistic contact shadows, and natural tabletop grounding (ZERO floating).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge

KEYCHAIN_CONCEPTS = [
    (
        "01_Baby_Crystal_Dragon",
        "photorealistic commercial studio product photography of a 3d printed cute baby crystal dragon keychain with folded wings and crystal horns, printed in matte sage green PLA filament with authentic fine layer line texture, resting firmly on a modern clean oak desk surface, soft contact occlusion shadow beneath the product, crisp studio key light, soft fill, shallow depth of field, 8k commercial catalog photo"
    ),
    (
        "02_Chubby_Axolotl",
        "photorealistic commercial studio product photography of a 3d printed chubby kawaii axolotl keychain with cute external gills, printed in matte dusty rose pink PLA filament with authentic fine layer line texture, resting firmly on a warm modern tabletop surface, natural soft contact shadow beneath product, studio lighting, 8k catalog photo"
    ),
    (
        "03_Kawaii_Baby_Octopus",
        "photorealistic commercial studio product photography of a 3d printed cute kawaii baby octopus keychain with curled tentacles, printed in matte ocean slate teal PLA filament with fine 3d print layer line texture, resting firmly on clean modern wooden tabletop, soft contact shadow beneath product, 8k commercial photo"
    ),
    (
        "04_LowPoly_French_Bulldog",
        "photorealistic commercial studio product photography of a 3d printed geometric low-poly french bulldog puppy keychain with faceted planes, printed in matte stealth charcoal PLA filament with fine 3d print layer line texture, resting firmly on warm tabletop surface, natural contact shadow beneath product, studio lighting, 8k catalog photo"
    ),
    (
        "05_Pirate_Skull",
        "photorealistic commercial studio product photography of a 3d printed detailed pirate skull keychain with bandana and eyepatch, printed in matte bone white silk PLA filament with authentic fine 3d print layer lines, resting firmly on rustic dark oak tabletop surface, natural contact shadow beneath product, dramatic side lighting, 8k catalog photo"
    ),
    (
        "06_Retro_HighTop_Sneaker",
        "photorealistic commercial studio product photography of a 3d printed detailed retro high-top basketball sneaker keychain with laces and textured sole, printed in matte royal blue and white PLA filament with fine layer line texture, resting firmly on tabletop surface, natural contact shadow beneath product, 8k commercial catalog photo"
    ),
    (
        "07_Lucky_Maneki_Neko",
        "photorealistic commercial studio product photography of a 3d printed cute lucky maneki-neko cat keychain with raised waving paw and collar bell, printed in matte warm amber honey PLA filament with fine 3d print layer lines, resting firmly on warm modern tabletop, soft contact shadow beneath product, studio lighting, 8k catalog photo"
    ),
    (
        "08_Chibi_Astronaut",
        "photorealistic commercial studio product photography of a 3d printed cute chibi space astronaut keychain in spacesuit with bubble visor, printed in matte sand almond PLA filament with fine 3d print layer lines, resting firmly on clean modern tabletop, soft contact shadow beneath product, 8k commercial catalog photo"
    )
]

# Hero Cluster concept
HERO_CLUSTER_PROMPT = (
    "photorealistic commercial studio product photography of a cluster of three 3d printed keychains: "
    "a cute baby crystal dragon in matte sage green, a chubby axolotl in dusty rose, and a baby octopus in teal, "
    "arranged together resting firmly on a clean warm wooden tabletop, soft realistic contact occlusion shadows beneath each item, "
    "natural FDM 3d printed matte PLA texture with micro layer lines, studio warm lighting, 8k commercial catalog hero photo"
)

OUT_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\work_renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

NEG = "blurry, floating, hovering, fake, oversaturated neon, plastic toy look, bad geometry, cropped, low quality, distorted, extra limbs, watermark, text, signature"


def generate_all_media():
    print(f"Starting ComfyUI media generation for {len(KEYCHAIN_CONCEPTS)} keychains + hero cluster...")

    # 1. Generate the 8 single product media images
    for idx, (name, prompt) in enumerate(KEYCHAIN_CONCEPTS, 1):
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
            cfg=6.5,
            auto_qc=False
        )
        if res_hero.get("success") and res_hero.get("file_path"):
            src = Path(res_hero["file_path"])
            src.replace(hero_dest)
            print(f"    -> Saved {hero_dest.name} in {time.time()-t0:.1f}s ({hero_dest.stat().st_size / 1024:.0f} KB)")
        else:
            print(f"    -> Hero FAILED: {res_hero.get('error')}")

    print("ComfyUI media generation complete!")


if __name__ == "__main__":
    generate_all_media()
