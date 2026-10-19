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

## Update 2026-10-19 (typography batch complete)
Built + validated (images 9, 4 zips each, all zips <20 MB, titles <=140, 0 validation problems, 0 trademark hits):
valentines_day_quotes (135), nurse_life_quotes (247), coffee_lover_quotes (231), motivational_positive_quotes (206 after removing 'Keep calm'),
dog_mom_cat_mom_pet_quotes (214), graduation_2027_class_of_quotes (224), plus REBUILT teacher (262), mom (124), sarcasm (147) without trademark lines.
Trademark phrases purged from all corpora: Bluey, Paw Patrol, Pringle, 'Keep calm ...', Espresso Patronum, Pink Floyd lyric. Scan command:
Select-String etsy_factory\typo\niches\*_quotes.py -Pattern 'keep \*?calm|bluey|patrol|pringle|patronum' (must return 0).
New niches live in typo/niche_defs_more.py (merged by niche_defs.py). faith pack still unrebuilt (title 143 chars gets word-trimmed to 140; fine).
Batch driver idea: loop pack <key> then uild_listing <key> (about 2.5 min per niche).
Tool note: a broken telemetry hook (googlecloudtools.datacloud_telemetry/hooks.json, doubled quoted path) blocked all tools until fixed by the user.
Remaining queue: 2 tumbler wraps + key-fob patterns, 3 3D packs, 4 matting-model cut-out fix + Christmas top-up.

## Update 2026-10-19 (evening) - tumbler wrap pattern pack built
New package `etsy_factory/patterns/`: `engine.py` (13 procedural seamless pattern types x 8 palettes), `mock_tumbler.py` (headless Blender 20 oz tumbler renders),
`pack.py` (52 patterns = 13 types x 4 palettes; each as wrap 2790x2460, 12x12in paper 3600px, raw 1200px tile -> `workspace/etsy_patterns/`),
`build_listing.py` (10 photos, 1 zip 16.3 MB, PDF guide + license, listing.md/json; 0 validation problems).
Run: `-m etsy_factory.patterns.pack` then `-m etsy_factory.patterns.build_listing` (Blender render ~1 min, no ComfyUI needed). Listing: `workspace/etsy_listings/seamless_tumbler_wrap_patterns_png/`.
Patterns are original geometry (no AI art). Rolled-tile visual check confirmed all 13 types seamless; `engine.seam_error()` is NOT reliable on high-contrast patterns (false alarms on checker/stripes/gingham) - judge by rolling the tile 50% on both axes.
Only the 20 oz skinny wrap is delivered; 30/40 oz templates and key-fob PNGs not done (verify real template sizes before claiming them).
Remaining queue: key-fob/other-size wraps, 3D packs (Blender), matting-model cut-out fix + Christmas top-up, media kit v2, whole-shop bundle.

## Update 2026-10-19 (night) - matting fix applied, Valentine cutters built
- `clipart/matte_comfy.py` (ComfyUI core BiRefNet bg-removal) + `clipart/rematte.py` + `cutkey.cut_key(matte=...)` now fix the blush/cream/ground-shadow cut-out failures.
  Re-cut with `-m etsy_factory.clipart.rematte <cow|xmas|boho> name,name` (old cut kept in `png_old/`). Verified visually on all 10 problem designs.
- Re-cut: xmas 008/017/038/043/049, boho 001/052, cow 003/016/046. Christmas listing rebuilt at the full 60 (2 zips). Boho rebuilt at 59 (052_peace_blush dropped:
  the AI drew a malformed peace sign - a design flaw, not a cut flaw). Cow rebuilt at 58 (needs <=5 zips of 20 MB; builder trimmed 059/060 automatically).
- NOTE: `build_listing` titles/covers use the real delivered count - re-read each listing.md before uploading.
- Valentine cookie cutters STL/3MF pack built (`pack_valentine_cutters.py`, `shapes_valentine.py`, `workspace/etsy_listings/valentine_cookie_cutters_stl/`): 10 designs x 2 sizes + press plates.
  Its cover still uses the frosted centre panel (research says dense collage works better) - candidate for kit v2.
Remaining queue: key-fob/other-size wraps, more 3D packs (Gridfinity organizers, flexi animals, Halloween cutters, ornaments), Cow top-up to 60 via downscale, media kit v2, whole-shop bundle.

## Update 2026-10-19 (late evening) - mockups re-centred, Valentine cover v2, remock tool
- PROBLEM: shirt/tote mockups had the art off-centre on every listing. Cause: fixed print boxes assumed the garment centre was x=0.50, but the cached
  ComfyUI blank photos are not (oat tee chest centre x=0.46, tote body centre x=0.455, black tee 0.495; the tote art also overlapped the open top).
- FIX: boxes measured from the BiRefNet matte of each cached photo and stored once in `typo/media.py` `MOCKUP_BOXES`; both builders use it.
  `etsy_factory/remock.py` regenerates ONLY the mockup photos in place: `-m etsy_factory.remock all` (done for 10 typography + 3 clipart listings = 39 images)
  or `typo:<key>` / `clip:<key>`. If a mockup photo or seed ever changes, re-measure (see the comment above MOCKUP_BOXES).
- Valentine cutters: new `kit.cover_open()` (no opaque panel, soft vignette, all products visible); cover render is 5x5 bigger cutters on a dimmed backdrop;
  hero camera pulled back so the teddy is no longer clipped. Redo only these two with `-m etsy_factory.pack_valentine_cutters --covers`.
  Other STL listings (Christmas cutters etc.) still use the old panel `kit.cover()` - switch them to `cover_open` when next rebuilt.

## PLAYBOOK - making a new design/pack is now mostly config
| Product | What you add | Command(s) | Time |
|---|---|---|---|
| Typography quote pack | `typo/niches/<name>_quotes.py` + entry in `niche_defs(_more).py` + MEDIA entry in `typo/build_listing.py` | `-m etsy_factory.typo.pack <key>` then `-m etsy_factory.typo.build_listing <key>` | ~2.5 min, CPU |
| AI clipart pack | `Pack` in `clipart/packs.py` + `LOOK` in `clipart/build_listing.py` | `clipart.run_pack <key> 2`, QC sheets, `clipart.rematte <key> names` for bad cuts, `clipart.build_listing <key> [--drop ...]` | ~15 min, ComfyUI |
| Seamless pattern pack | new pattern types/palettes in `patterns/engine.py` | `patterns.pack` then `patterns.build_listing` | ~5 min, Blender |
| 3D cutter / STL pack | shapes file (`shapes_<theme>.py`) + a `pack_<theme>_cutters.py` copied from the Valentine one | `-m etsy_factory.pack_<theme>_cutters` (+ `--covers` to redo only cover/hero) | ~5 min, Blender+ComfyUI |
Reusable now: BiRefNet cut-out fixer, shared mockup boxes, `remock`, open cover layout, ComfyUI backdrop presets (`comfy_backgrounds.py`), Blender headless renders,
Etsy validator (title <=140, tags <=20 chars, <=5 files x 20 MB, auto bin-packed zips). Still manual: choosing niches/prompts, eyeballing images, uploading to Etsy.

## NEXT STEPS (updated)
1. Everything above is committed locally in git. Re-read each `listing.md` + flip through `images/` for the 3 rebuilt clipart packs and Valentine before uploading
   (choose Etsy "AI generated" for clipart; mention AI backdrops for STL photos).
2. Store identity: pick a new store name, check Etsy + trademark (USPTO TESS/search) + domain + handles, then create matching socials (see chat notes).
3. New runs (queue): Halloween cutters + Christmas cutters cover refresh (use `cover_open`); Gridfinity-style organizers; flexi animals; key-fob + 30/40 oz tumbler wraps
   (verify real template sizes first); cow pack top-up to 60 (downscale instead of dropping); media kit v2 for typography covers; whole-shop bundle.
4. Avoid: IP characters, fake counts, embroidery.
