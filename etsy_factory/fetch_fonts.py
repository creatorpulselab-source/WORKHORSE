"""Download OFL-licensed Google Fonts used for the SVG cut-file listings (outlines only are sold; fonts never redistributed)."""
import sys
import urllib.request
from pathlib import Path

DEST = Path(r"F:\WORKHORSE\etsy_factory\fonts")
DEST.mkdir(exist_ok=True)
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {
    "Pacifico-Regular.ttf": "pacifico/",
    "Lobster-Regular.ttf": "lobster/",
    "BebasNeue-Regular.ttf": "bebasneue/",
    "Anton-Regular.ttf": "anton/",
    "PermanentMarker-Regular.ttf": "permanentmarker/",
    "CaveatBrush-Regular.ttf": "caveatbrush/",
    "Satisfy-Regular.ttf": "satisfy/",
    "Oswald[wght].ttf": "oswald/",
    "Sacramento-Regular.ttf": "sacramento/",
    "Courgette-Regular.ttf": "courgette/",
}
ok, bad = [], []
for fname, folder in FONTS.items():
    out = DEST / fname.replace("[wght]", "")
    try:
        url = BASE + folder + urllib.request.quote(fname)
        data = urllib.request.urlopen(url, timeout=60).read()
        out.write_bytes(data)
        ok.append((out.name, len(data)))
    except Exception as e:  # noqa
        bad.append((fname, str(e)))
print("OK", ok)
print("FAILED", bad)
