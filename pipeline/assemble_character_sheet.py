"""
WORKHORSE Automated Character Sheet Generator
Assembles multi-angle character reference sheets from client photos
for MiniMax H3 / Qwen-VL Character Swap pipelines.
"""

import os
import sys
from PIL import Image

def build_character_sheets(input_dir, output_dir, bg_color=(237, 239, 242)):
    os.makedirs(output_dir, exist_ok=True)
    files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    if len(files) < 4:
        raise ValueError(f"Need at least 4 photos for character sheet turnaround, found {len(files)} in {input_dir}")
        
    print(f"Processing {len(files)} photos from {input_dir}...")
    
    # 1. Select 4 full body angles (Front, Left Profile, Right 3/4, Back)
    # If standard naming exists, use those; otherwise pick first 4
    fb_files = files[:4]
    
    # Standard 4-Angle Turnaround Sheet (2560 x 1280)
    canvas_w, canvas_h = 2560, 1280
    sheet_4a = Image.new('RGB', (canvas_w, canvas_h), bg_color)
    h_4a = 1200
    
    fb_imgs = []
    for f in fb_files:
        im = Image.open(os.path.join(input_dir, f))
        s = h_4a / im.height
        w = int(im.width * s)
        fb_imgs.append(im.resize((w, h_4a), Image.Resampling.LANCZOS))
        
    tot_w = sum(im.width for im in fb_imgs)
    gap = max(20, (canvas_w - tot_w) // (len(fb_imgs) + 1))
    x = gap
    for im in fb_imgs:
        sheet_4a.paste(im, (x, (canvas_h - h_4a) // 2))
        x += im.width + gap
        
    out_4a = os.path.join(output_dir, "character_card_4angles.png")
    sheet_4a.save(out_4a, quality=95)
    print(f"Saved: {out_4a}")
    
    # 2. Master Dual-Tier Sheet (3840 x 2160)
    sheet_master = Image.new('RGB', (3840, 2160), bg_color)
    row1_h = 1400
    row1_imgs = []
    for f in fb_files:
        im = Image.open(os.path.join(input_dir, f))
        s = row1_h / im.height
        w = int(im.width * s)
        row1_imgs.append(im.resize((w, row1_h), Image.Resampling.LANCZOS))
        
    tot_row1_w = sum(im.width for im in row1_imgs)
    gap1 = max(20, (3840 - tot_row1_w) // (len(row1_imgs) + 1))
    x1 = gap1
    for im in row1_imgs:
        sheet_master.paste(im, (x1, 60))
        x1 += im.width + gap1
        
    # Row 2: Closeups (if available)
    cu_files = files[4:8] if len(files) >= 8 else files[:4]
    row2_h = 560
    row2_imgs = []
    for f in cu_files:
        im = Image.open(os.path.join(input_dir, f))
        s = row2_h / im.height
        w = int(im.width * s)
        row2_imgs.append(im.resize((w, row2_h), Image.Resampling.LANCZOS))
        
    tot_row2_w = sum(im.width for im in row2_imgs)
    gap2 = max(20, (3840 - tot_row2_w) // (len(row2_imgs) + 1))
    x2 = gap2
    for im in row2_imgs:
        sheet_master.paste(im, (x2, 1520))
        x2 += im.width + gap2
        
    out_master = os.path.join(output_dir, "character_card_master.png")
    sheet_master.save(out_master, quality=95)
    print(f"Saved: {out_master}")
    
    # 3. Lightweight 2K Sheet (2048 x 1152)
    sheet_2k = sheet_master.resize((2048, 1152), Image.Resampling.LANCZOS)
    out_2k = os.path.join(output_dir, "character_card_2k.png")
    sheet_2k.save(out_2k, quality=95)
    print(f"Saved: {out_2k}")
    
    return {
        "master": out_master,
        "4angles": out_4a,
        "2k": out_2k
    }

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\User\Pictures\Melissa Charater Sheet"
    dst = sys.argv[2] if len(sys.argv) > 2 else r"F:\WORKHORSE\workspace\brand_assets"
    build_character_sheets(src, dst)
