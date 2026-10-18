import sys
from pathlib import Path
from PIL import Image
slug = sys.argv[1] if len(sys.argv) > 1 else "christmas_cookie_cutters_stl"
d = Path(r"F:\WORKHORSE\workspace\etsy_listings") / slug / "images"
fs = sorted(d.glob("[0-9][0-9]_*.jpg"))
W = 640
cols = 5
rows = (len(fs) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, W * rows), "white")
for i, f in enumerate(fs):
    sheet.paste(Image.open(f).convert("RGB").resize((W, W)), ((i % cols) * W, (i // cols) * W))
out = Path(r"F:\WORKHORSE\workspace\etsy_listings") / slug / "_work" / "contact_sheet.jpg"
sheet.save(out, quality=88)
print(out)
