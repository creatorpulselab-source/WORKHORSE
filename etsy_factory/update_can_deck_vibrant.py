import sys
from pathlib import Path

p = Path(r"F:\WORKHORSE\etsy_factory\assemble_can_holders_deck.py")
text = p.read_text(encoding="utf-8")

s1 = text.find("def make_card_01()")
s2 = text.find("def make_card_02()")
assert s1 != -1 and s2 != -1

new_c1 = """def make_card_01() -> Image.Image:
    out_p = IMAGES_DIR / "01_cover.jpg"
    thumbs_dir = LISTING_DIR / "_work" / "thumbs"
    items = [
        '01_QuadGrip_Caddy', '02_DuoCaddy', '03_HexaCool', '04_SlimGrip',
        '05_TrailLock', '06_DualDrive', '07_Titan_16oz', '08_FlipBase'
    ]
    meta = [{'name': name} for name in items]
    ribbon_cols = [
        ((44, 120, 68), (20, 70, 38)),     # Vibrant Forest Green
        ((212, 92, 36), (140, 50, 18))     # Warm Terracotta
    ]
    vbg = (20, 44, 38) # Deep spruce green
    badges = [
        ('STL', '100% Watertight\\nZero Errors', (46, 125, 114)),
        ('PRINT', '100% Support-Free\\nFlat Bed Base', (212, 92, 36)),
        ('CAD', 'Fits 12oz & Slim\\nCar Consoles', (44, 120, 68)),
        ('SLICER', 'Bambu Prusa\\nCreality Ready', (123, 82, 148)),
        ('COMM', 'Commercial License\\nIncluded', (200, 140, 30))
    ]
    cover2.vibrant(
        meta=meta,
        thumbs_dir=thumbs_dir,
        out=out_p,
        big='8',
        kicker='HEAVY-DUTY UTILITY PACK',
        title_lines=['CAN & DRINK HOLDERS', '3D PRINT STL BUNDLE'],
        sub='4-CUP CADDY * CAN COOLERS * CAR ADAPTER * HOLSTER',
        ribbon_cols=ribbon_cols,
        ink=INK,
        bg=vbg,
        badges=badges,
        burst=('INSTANT', 'DOWNLOAD'),
        seed=8
    )
    return Image.open(out_p).convert('RGB')

"""

text = text[:s1] + new_c1 + text[s2:]

text = text.replace('out_p = IMAGES_DIR / "10_license.jpg"', 'out_p = IMAGES_DIR / "10_commercial_license.jpg"')
text = text.replace('accent=ORANGE,', 'accent=(255, 64, 129),')

if "from etsy_factory.typo import cover2" not in text:
    text = text.replace("from etsy_factory.typo import media as M", "from etsy_factory.typo import cover2, media as M")

p.write_text(text, encoding="utf-8")
print("Updated assemble_can_holders_deck.py successfully!")
