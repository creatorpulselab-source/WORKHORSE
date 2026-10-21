"""Generate photorealistic ComfyUI listing media for Christmas Cookie Cutters on RTX 5070 Ti.
Produces high-end commercial lifestyle photography:
- Hero holiday baking flatlay with rolled dough, flour, and 3D printed festive cutters
- Cutter & Press plate detail stamping dough
- Two sizes (60mm & 80mm) showing razor-clean cutting edge and comfort grip flange
- Graded with Workhorse Cinematic Filmic Matte LUT
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge
from etsy_factory.davinci_color_grade import batch_grade_directory

OUT_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\christmas_cookie_cutters_stl\work_renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

NEG = "blurry, floating, hovering, fake, low resolution, distorted, extra limbs, watermark, text, signature, plastic toy look"

LIFESTYLE_CONCEPTS = [
    (
        "comfy_hero_baking_cluster.png",
        "photorealistic commercial hero product photography of a curated set of 3d printed Christmas cookie cutters in festive crimson red, evergreen pine green, and warm golden yellow matte PLA filament, arranged harmoniously on a light marble pastry board lightly dusted with white flour, alongside freshly rolled sugar cookie dough with cut-out star and tree shapes and a wooden French rolling pin, soft realistic contact shadows beneath every cutter, authentic 3d print micro layer lines, warm bakery studio key lighting, shallow depth of field, 8k commercial catalog photo"
    ),
    (
        "comfy_cutter_and_press_action.png",
        "photorealistic commercial closeup product photography of a 3d printed gingerbread man cookie cutter and matching embossed press plate stamping a clean detailed pattern into rolled cookie dough, fine flour particles scattered on a warm wooden pastry counter, crisp focus on the cutter edge and wide ergonomic comfort grip flange, authentic matte PLA 3d printed texture with subtle layer lines, soft directional lighting, 8k commercial photo"
    ),
    (
        "comfy_two_sizes_snowflake.png",
        "photorealistic commercial macro product photography of two matching 3d printed snowflake cookie cutters in 60mm and 80mm sizes, printed in frosted snow white and ice teal matte PLA filament, sitting next to a beautifully baked snowflake sugar cookie with delicate white royal icing, resting firmly on a rustic kitchen baking surface with soft natural contact shadows, razor-sharp 0.8mm cutting taper visible, commercial bakery lighting, 8k catalog photo"
    )
]

def generate_cookie_cutters_media():
    print(f"Generating {len(LIFESTYLE_CONCEPTS)} ComfyUI commercial lifestyle photos on RTX 5070 Ti...")
    for filename, prompt in LIFESTYLE_CONCEPTS:
        dest = OUT_DIR / filename
        if dest.exists() and dest.stat().st_size > 50000:
            print(f"  Already exists: {filename}")
            continue

        t0 = time.time()
        print(f"  Generating {filename}...")
        res = comfy_bridge.generate_and_audit(
            positive_prompt=prompt,
            negative_prompt=NEG,
            width=1024,
            height=1024,
            steps=24,
            cfg=6.5,
            auto_qc=False
        )
        if res.get("success") and res.get("file_path"):
            src = Path(res["file_path"])
            src.replace(dest)
            print(f"    -> Saved {filename} in {time.time()-t0:.1f}s ({dest.stat().st_size / 1024:.0f} KB)")
        else:
            print(f"    -> Failed: {res.get('error')}")

    print("Grading ComfyUI renders with Filmic Matte LUT...")
    batch_grade_directory(OUT_DIR)
    print("Done generating & grading cookie cutters media!")

if __name__ == "__main__":
    generate_cookie_cutters_media()
