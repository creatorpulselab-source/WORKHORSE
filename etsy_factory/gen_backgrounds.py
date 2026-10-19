import sys
import time
sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import comfy_backgrounds as cb

# usage: gen_backgrounds.py name[@seed] ...
names = sys.argv[1:] or list(cb.BACKGROUNDS)
print("comfy available:", cb.available(), flush=True)
for item in names:
    n, _, s = item.partition("@")
    t = time.time()
    p = cb.generate(n, seed=int(s) if s else 20261018)
    print(item, "->", p, f"{time.time() - t:.1f}s", flush=True)
