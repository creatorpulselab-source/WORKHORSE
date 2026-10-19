# Etsy factory - status and next steps (saved 2026-10-18 night)

Outputs live in `F:\WORKHORSE\workspace\` (git-ignored). Code lives in `F:\WORKHORSE\etsy_factory\` (committed).
Python: `F:\WORKHORSE\.venv\Scripts\python.exe` (run from `F:\WORKHORSE`). ComfyUI server: `http://192.168.1.74:8188`
(serial GPU queue - run only one image-heavy job at a time, mockup photos also use it).

Market research that drives the build order: `research/etsy_top_seller_analysis_2026-10-18.md` (real screenshots) and
`research/etsy_top_design_types_2026-10.md`.

## Listings finished (folder = `workspace/etsy_listings/<slug>/`: images/, etsy_upload/, listing.md, listing.json)
| Slug | What | Notes |
|---|---|---|
| cookie cutters / desk organizers / can holders / keychains / planters (STL) | 3D print packs | built earlier, procedural + headless Blender renders |
| sarcastic_funny_quotes_svg_png_bundle | typography | procedural |
| christian_faith_quotes_svg_png_bundle | typography | procedural (KJV public domain) |
| mom_life_mama_quotes_svg_png_bundle | typography | procedural |
| teacher_life_quotes_svg_png_bundle | typography, 262 designs x 6 formats | procedural |
| highland_cow_sublimation_clipart_png | AI clipart, 57 | ComfyUI Z-Image Turbo + colour-key cutout |
| retro_christmas_sublimation_clipart_png | AI clipart, 55 of 60 | 5 dropped: angel/star/peppermint/2 gift boxes (cut-out flaws) |
| boho_retro_sublimation_clipart_png | AI clipart, 58 of 60 | dropped 052_peace_blush, 001_rainbow_terracotta |

Before uploading any listing: flip through its `images/`, choose Etsy's "AI generated" creation process for the clipart packs,
and set the sale price from `listing.md`. Typography and STL packs are procedural (no AI disclosure needed unless ComfyUI
backgrounds/mockups are described in the text - the mockup photos are AI-made scenery, so mention it if you want to be safe).

## How to build a pack
- Typography: add `typo/niches/<name>_quotes.py`, register in `typo/niche_defs.py`, add a MEDIA entry in `typo/build_listing.py`, then
  `-m etsy_factory.typo.pack <key>` (CPU, ~1.5 min) and `-m etsy_factory.typo.build_listing <key>` (mockups need ComfyUI).
- Clipart: add a Pack in `clipart/packs.py` + LOOK in `clipart/build_listing.py`; `-m etsy_factory.clipart.run_pack <key> 2`
  (generate + cut, ~12 s/image), then QC `workspace/etsy_clipart/<slug>/sheets/*.jpg`; `--redo name,name` to regenerate;
  `-m etsy_factory.clipart.build_listing <key> --drop name,name`.
- 3D/STL: `etsy_factory/listings_stl.py`, `stl_listing.py`, `shapes3d.py`, `shapes_keychain.py`, `blender_render.py` (Blender headless).

## Lessons learned
- Colour-key cut-out (`clipart/cutkey.py`) fails on blush / cream / pink subjects and on subjects with a ground shadow: the AI paints a
  pink shadow or the key colour bleeds into the art, leaving holes or a halo. `--redo` re-seeds only once (+1000), so a second redo
  repeats the same seed. Cure candidates: per-subject key colour, a real matting model (rembg / BiRefNet in ComfyUI), add "no ground
  shadow" to the prompt tail, and re-seed with a counter.
- Etsy limits: max 5 files x 20 MB, tags <= 20 chars, title <= 140 chars. Zips are bin-packed automatically.
- Always eyeball cover + one mockup + the QC sheets; the validator does not catch visual defects.

## Queue (in order)
1. Rest of the typography niches (CPU only): nurse, coffee, Valentine 2027 (timely), motivational, pets/dog mom, graduation 2027 / class of,
   christmas/holiday typography, retro mama variants, teacher-staff add-on.
2. Tumbler wraps + key-fob PNG pattern packs (seamless patterns, 20/30/40 oz templates).
3. 3D packs (Blender): Gridfinity-style organizers, flexi animals, themed cookie cutters (Valentine/Halloween), Christmas ornaments, can-cooler sets.
4. Cut-out fix (matting model) then top up Christmas to 60 designs; rebuild its listing.
5. Media kit v2 (dense collage covers, realistic scene integration); mega "whole shop" bundle once enough packs exist.
6. Avoid: IP characters (Pokemon etc.), fake counts, embroidery.
