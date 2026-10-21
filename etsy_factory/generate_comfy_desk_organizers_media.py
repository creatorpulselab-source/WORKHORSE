"""Generate photorealistic ComfyUI listing media for 10 Desk Organizers + Hero Desk Setup Cluster.
Executed on remote ComfyUI (RTX 5070 Ti at 192.168.1.74:8188) with authentic matte PLA textures,
realistic contact shadows, warm oak desktop surface, and natural workspace grounding (ZERO floating).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge
from etsy_factory.davinci_color_grade import batch_grade_directory

DESK_CONCEPTS = [
    (
        "01_Round_Pen_Cup",
        "photorealistic commercial studio product photography of a modern 3d printed cylindrical round pen cup with fluted top lip, holding a neat collection of metallic drafting pens and wooden pencils, printed in warm desert almond sand matte PLA filament with fine authentic 3d print micro layer lines, resting firmly on a warm light oak office desk, soft realistic contact occlusion shadow beneath base, studio key light, shallow depth of field, 8k commercial catalog photo"
    ),
    (
        "02_Hex_Pen_Cup",
        "photorealistic commercial studio product photography of a modern 3d printed faceted hexagonal geometric pen cup, holding black fineliner pens and scissors, printed in earthy forest moss green matte PLA filament with authentic 3d print layer line texture, resting firmly on a modern wooden desktop, natural contact shadow beneath base, soft studio side lighting, 8k commercial catalog photo"
    ),
    (
        "03_Square_Pencil_Holder",
        "photorealistic commercial studio product photography of a contemporary 3d printed architectural square pencil holder cup, holding artist brushes and pens, printed in warm terracotta clay matte PLA filament with subtle print layer lines, resting firmly on a Scandinavian wood desk, natural contact shadow, clean commercial lighting, 8k catalog photo"
    ),
    (
        "04_Phone_Stand",
        "photorealistic commercial studio product photography of an ergonomic 3d printed desk phone stand dock holding a sleek modern smartphone at a 65 degree viewing angle, printed in stealth matte charcoal graphite PLA filament with fine authentic layer lines, resting firmly on an office desk next to a mechanical keyboard, soft contact occlusion shadow, 8k commercial photo"
    ),
    (
        "05_Cable_Clips_x4",
        "photorealistic commercial studio product photography of a set of 4 modern 3d printed modular desk cable wire clips neatly organizing black and braided charging cords, printed in ocean slate teal matte PLA filament with micro layer texture, adhered to a light oak desk edge, realistic soft shadow, crisp focus, 8k catalog photo"
    ),
    (
        "06_Business_Card_Holder",
        "photorealistic commercial studio product photography of a minimalist 3d printed angled business card holder display neatly presenting a stack of premium textured white business cards, printed in denim slate blue matte PLA filament with authentic 3d print layer lines, resting firmly on a wood desk, soft contact shadow, 8k commercial photo"
    ),
    (
        "07_Sticky_Note_Tray",
        "photorealistic commercial studio product photography of a low-profile 3d printed square sticky note tray holding a fresh pad of 3x3 inch pastel yellow Post-it notes with front finger notch, printed in warm amber honey ochre matte PLA filament, resting on an office tabletop, natural contact shadow, 8k commercial photo"
    ),
    (
        "08_4-Compartment_Desk_Tray",
        "photorealistic commercial studio product photography of a modular 3d printed 4-compartment desk organizer tray with separate sections holding silver paper clips, binder clips, USB flash drives, and an eraser, printed in warm desert almond matte PLA filament with authentic print layer lines, resting on an oak desk, 8k commercial photo"
    ),
    (
        "09_Pen_and_Pencil_Tray",
        "photorealistic commercial studio product photography of a long horizontal 3d printed pen and pencil desk tray holding a luxury fountain pen and an Apple Pencil stylus, printed in muted sage grey green matte PLA filament with authentic layer lines, resting flat under a computer monitor on a clean desk, soft contact shadow, 8k catalog photo"
    ),
    (
        "10_Desk_Dish",
        "photorealistic commercial studio product photography of a rounded 3d printed valet catchall desk dish bowl holding brass keys, coins, and paper clips, printed in warm stone clay matte PLA filament with subtle print texture, resting on a clean wooden desk surface, soft contact shadow, 8k commercial photo"
    )
]

HERO_CLUSTER_PROMPT = (
    "photorealistic commercial studio hero photography of a stunning complete curated matching 3d printed desk organizer set: "
    "a charcoal phone stand holding a smartphone, a forest green hex pen cup filled with pens, an almond 4-compartment tray holding paper clips, and an amber sticky note tray, "
    "harmoniously arranged together resting firmly on a clean warm oak office desk surface with a soft blurred laptop in background, "
    "natural FDM 3d printed matte PLA texture with micro layer lines, soft realistic contact occlusion shadows beneath every item, warm studio lighting, 8k commercial catalog hero photo"
)

OUT_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\desk_organizers_stl\work_renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

NEG = "blurry, floating, hovering, fake, oversaturated neon, plastic toy look, bad geometry, cropped, low quality, distorted, extra limbs, watermark, text, signature"


def generate_and_grade_media():
    print(f"Starting ComfyUI media generation for {len(DESK_CONCEPTS)} desk organizers + hero cluster...")

    for idx, (name, prompt) in enumerate(DESK_CONCEPTS, 1):
        dest_img = OUT_DIR / f"comfy_single_{idx:02d}.png"
        if dest_img.exists() and dest_img.stat().st_size > 50000:
            print(f"  [{idx}/10] Already exists: {dest_img.name}")
            continue

        t0 = time.time()
        print(f"  [{idx}/10] Generating {name} on ComfyUI RTX 5070 Ti...")
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

    # Generate Hero Cluster
    hero_dest = OUT_DIR / "comfy_cluster_hero.png"
    if not (hero_dest.exists() and hero_dest.stat().st_size > 50000):
        t0 = time.time()
        print("  [Hero] Generating Desk Setup Hero Cluster on ComfyUI RTX 5070 Ti...")
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

    print("\n[DaVinci Resolve] Running 3D LUT Color Grading...")
    batch_grade_directory(OUT_DIR, pattern="comfy_*.png")
    print("\nComfyUI + DaVinci Media Generation Pipeline Complete!")


if __name__ == "__main__":
    generate_and_grade_media()
