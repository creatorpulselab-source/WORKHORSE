# New store - pack plan (2026-10-19)

Store mix: mostly **SVG** (cute and crafty) and **STL** (cute functional prints), some **GLB**, a little of everything. Not one look:
leopard/sarcasm is only ONE collection (a proven seller), the rest is cute, crafty and functional.

## Status
| # | Pack | Format | Status | Needs |
|---|---|---|---|---|
| 1 | Sarcastic leopard animals, 60 shirt designs | PNG (sublimation/DTF) | art + captions generating (`clipart/sass_pack.py`) | cover, mockups, trademark scan, listing |
| 2 | Cute animal pencil cups x8 | STL + 3MF + GLB | geometry built + validated + previewed (`shapes_cute.py`) | spec/listing run (ComfyUI backdrops) |
| 3 | Cute animal faces layered cut files (20 animals x 3 versions) | SVG + DXF + PNG | BUILT 2026-10-19: `faces/animals.py`, `faces/pack.py`, `faces/build_listing.py` (9 images, 3 zips + PDF, 0 validation problems) | eyeball images, then upload |
| 4 | Cute alphabet / monogram packs | SVG DXF EPS PNG | planned (research: strongest fit, procedural) | fonts + welded glyphs |
| 5 | Layered paper-cut / shadow-box (cute themes) | SVG + PDF assembly | planned | layer exporter |
| 6 | Cute functional pack 2: kawaii cable holders, phone stands with ears, plant pot faces | STL + 3MF + GLB | planned | new builders |
| 7 | Laser-cut ornaments / keychains / earrings | SVG DXF | planned | kerf + layer colours |
| 8 | Sticker sheets (cute animals) | PNG + PDF cut lines | planned | reuse #3 faces |

## Rules for every pack
- Original shapes/phrases only (run the trademark scan on captions/names), no IP characters.
- Listing images: cover with the REAL contents visible (`kit.cover_open`), mockups via `remock` boxes, honest counts.
- Deliver STL + 3MF + GLB for 3D packs (GLB = coloured preview/AR + Blender users). Etsy: <=5 files x 20 MB.
- Build CPU-only parts while the ComfyUI GPU is busy; run backdrops/mockups when it is free (serial queue).
