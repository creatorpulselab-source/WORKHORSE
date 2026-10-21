# Reference Image -> Etsy Design Process (SVG / PNG)
### Learning file for WORKHORSE agents, written 2026-10-19 from the build session

Purpose: when the user drops reference images into `F:\WORKHORSE\etsy_ideas\` and says "make something like this", follow this process.
It records what worked, what broke and how it was fixed, so the next run does not repeat the mistakes.

> **Scope note.** There is **no automatic image-to-SVG tracing** in WORKHORSE. A reference image is used as a *layout and style brief*;
> the design is then rebuilt from parts (AI-painted elements + real font text + procedural vector shapes).
> Vector (SVG/DXF) output comes from **procedural geometry**, never from tracing an AI image. The existing
> `build_full_color_and_clean_svg_kit.py` (LAB k-means layers) and `pipeline/stages/svg_cricut_optimizer.py` (confetti removal, Douglas-Peucker)
> exist for converting art to cut files, but they were not used in this session.

---

## 1. Decide the product type first

| Reference shows | Build as | Output | Where the code is |
|---|---|---|---|
| Painted animal/object + caption text (shirt designs) | AI art + procedural text | transparent 300 dpi PNG (sublimation / DTF) | `etsy_factory/clipart/sass_pack.py` |
| Camo lettering + script + small painted icons | AI-painted elements + font lettering | transparent PNG | `etsy_factory/clipart/military_pack.py` |
| Flat quote/typography, badges, ornaments | procedural vector | SVG + DXF + EPS + PNG | `etsy_factory/typo/` |
| Layered cute shapes for Cricut/laser | procedural geometry (shapely) | SVG (one compound path per colour layer) + DXF + PNG | `etsy_factory/faces/` |
| 3D object | parametric mesh + headless Blender | STL / 3MF / GLB | `etsy_factory/shapes*.py` |

Rule of thumb: **text is always real font glyphs** (`etsy_factory/fonts/`, 84 font files); **never ask the AI to draw letters**.
**Cut files (SVG/DXF) must be geometry**, because layers have to be aligned, welded and low-node for the blade.

## 2. Read the reference image (do this before generating anything)

Open each reference with the image viewer and write down, per design:
1. **Layout** - where the headline, subject and second line sit (stacked, arched, flanking).
2. **Text treatment** - block caps vs script; outlined; filled with a texture (camo, leopard print); halo/sticker edge.
3. **Subject** - what is painted vs. what is text. Painted parts become AI elements.
4. **Palette and garment** - dark text needs light garments in mockups.
5. **Trademark check** - reject IP characters, brand logos, branch emblems/insignia/seals. Generic shapes only.

Reference examples used on 2026-10-19: `etsy_ideas/Shirt Ideas.jpg` (animal portrait + two caption lines, one arched, leopard-filled bottom line),
`6ce3bb24-...jpg` (T-rex / astronaut in leopard print), `Untitled Project - Artboard NN.png` (layered camo word + script + icons).

## 3. Build pipeline (clipart / shirt designs)

```
reference -> brief -> ELEMENT PROMPTS -> ComfyUI (FLUX Krea / Z-Image) on a flat KEY colour
          -> BiRefNet matte (ComfyUI) + colour-key edge clean + despill -> cut/*.png
          -> COMPOSE on a roomy canvas (fonts, textures, shadows) -> crop to content -> png/*.png
          -> contact sheets -> EYEBALL -> fix -> build_listing -> zips + mockups + listing.md
```

### 3.1 Generate elements, not whole designs
- One isolated object per image, `centered on a plain flat pure magenta (#FF00FF) background ... the magenta is not used anywhere on the object ... no text, no logo, no insignia, no cast shadow`.
- Use a different key colour when the subject is pink/blush (`packs.key_for`: pinks -> cyan, pinks+teal -> green).
- Generate **2 variants per element** (`_v1`, `_v2`) and alternate them across designs.
- ComfyUI at `http://192.168.1.74:8188` runs **one job at a time**; never start a second image-heavy job while one is running (check `/queue`).
- Results are cached by (name, seed), so an interrupted run resumes. `--redo` re-seeds **once** (+1000); a second redo repeats the same seed.

### 3.2 Cut out
- Colour-key alone fails on blush/cream/pink subjects and subjects with a ground shadow.
- Use the BiRefNet matte (`clipart/matte_comfy.py`) and then `cutkey.cut_key(src, dst, matte=mask)` for the edge refinement.
- **Despill on load** (added 2026-10-19 in `military_pack.load_element`): subtract `min(R,B) - G - 25` from R and B so the magenta tint on boots and dog tags disappears. Genuine reds and blues are not touched because min(R,B) is small for them.

### 3.3 Compose
- Text: `fit_mask()` binary-searches the font size to fit a box. Camo/leopard fill is a texture clipped to the glyph mask, with a dark outline (MaxFilter) and a white halo for the sticker look.
- Elements get a soft drop shadow (`with_shadow`) and are placed beside the word, never over it.
- Always draw on a **large canvas, then crop to the alpha bounding box** and add padding. Nothing may touch the canvas edge.

## 4. Lessons learned (bugs we actually hit)

| Symptom | Cause | Fix |
|---|---|---|
| Branch name unreadable ("MARI", "COAS") | hero element placed over the word, word 2500 px wide on a 3000 px canvas | narrow the word (1900 px one line / 1450 px two lines) and put the element column **beside** it; layout C became a mirror of A |
| Script cut off at the right ("Proud Mon", "Proud Wif") and bottom elements clipped | script allowed 3200 px on a 3000 px canvas; elements ran past the canvas height | canvas 3600 x 3200; script width capped (`max_w=2900`); for the "Mom Life / Wife Life" lines `max_w = word.width + 40` |
| Purple/magenta fringe and shadow on boots, dog tags | key colour bleeding into the cut | despill step (3.2) |
| Pink, cream, blush clipart with holes or halos | colour-key fails | BiRefNet matte |
| Wrong filename pattern in the listing builder | `build_listing` expects `{idx:03d}_{subject}_{style}.png` | give the composer the same naming (here the `_mil` suffix is the single style key) |
| `[IO.File]::ReadAllText` / `WriteAllText` failed with "path not found" | .NET resolves relative paths against the process cwd, not PowerShell's location | use absolute paths, or the edit tool |
| Misleading validator results | validator checks sizes/titles, not looks | **always view the contact sheets and the cover + one mockup** |

## 5. Quality gate (every pack, in order)
1. Generate contact sheets (`sheets/*.jpg`, 12 designs each) and **look at every sheet**.
2. Check: text spelled exactly as written in the data file; nothing overlapping or clipped; no halo or fringe; consistent look.
3. Drop or redo bad designs by name (`--redo`, `--drop`). Honest counts only: titles and covers use the delivered count.
4. Trademark scan on all captions and names (command in `etsy_factory/STATUS_AND_NEXT_STEPS.md`; must return 0 hits).
5. Build the listing; read `listing.md`; validator must report 0 problems.

## 6. Etsy rules baked into the builders
- Title <= 140 characters, tags <= 20 characters, max 13 tags used here.
- Max **5 files x 20 MB** per listing; zips are bin-packed automatically; the PDF guide and licence go in part 1.
- Clipart listings: choose the **"AI generated"** creation process and name the tool. Typography, pattern and STL packs are procedural.
- Use real counts; no IP characters; no insignia/seals/logos; avoid embroidery.
- Dark-text designs: use only light garments in mockups (`tee_oat`, `tee_white`, `tote`).

## 7. Commands (run from `F:\WORKHORSE`, interpreter `.venv\Scripts\python.exe`)
```
-m etsy_factory.clipart.military_pack --elements      # generate + cut elements (GPU, ~12 s/image)
-m etsy_factory.clipart.military_pack --compose       # compose 48 designs (CPU, ~5 min) + contact sheets
-m etsy_factory.clipart.military_pack --only 1,4,7    # re-compose some designs
-m etsy_factory.clipart.build_listing military        # zips, cover, mockups, listing.md/json
-m etsy_factory.clipart.sass_pack [--only N] [--recompose] [--redo name]
-m etsy_factory.remock all                            # regenerate only mockup photos
```
To add a new pack: register a `Pack` in `clipart/packs.py` and a `LOOK` entry in `clipart/build_listing.py`.
Test layouts on 8-12 designs in `workspace/scratch/` before composing the full set.

## 8. Case study: military mom / wife pack (2026-10-19)
- Reference: layered camo word + script + icon cluster. 22 AI elements (boots + tags, dog tags, flags, helmet, caps, anchor, wheel, life ring, jet, wings, aviators, compass, ribbon, sunflower, camo cup) x 2 variants = 44 cuts, none using insignia.
- 6 branches (army, navy, air force, marine, coast guard, generic military) x {Proud Mom, Proud Wife} x 3 layouts + 12 "Mom Life / Wife Life" variants = **48 designs**.
- First compose failed the visual check (overlaps, clipping, fringe). Three code changes fixed it (section 4); a 12-design test sheet was approved before re-running all 48.
- Known cosmetic flaw: a few AI dog-tag images show a grey tie-dye smear; acceptable but re-seed (`--redo dogtags_flag`) if a buyer-facing cover shows it.

## 9. Open gaps (not yet built)
- True **SVG from a reference image** (trace + simplify + layer by colour + Cricut grouping) as a one-command tool. Today it would mean running the AI image through `build_full_color_and_clean_svg_kit.py` / `svg_cricut_optimizer.py` by hand.
- Key-fob and 30/40 oz tumbler wraps (verify real template sizes first).
- Cover refresh (`kit.cover_open`) for older STL listings.

---

## 10. Mandatory Media Suite: ComfyUI, Blender 5.2, DaVinci Resolve Studio

*Mandated 2026-10-20 by Commander Directive: Use ComfyUI, Blender, and DaVinci Resolve Studio for any and all media that needs to be created. Everything needs to be expert level quality in design and in products.*

See detailed specifications in `F:\WORKHORSE\LLM training\WORKHORSE_MEDIA_CREATION_AND_ETSY_MOCKUP_STANDARDS.md`.

### Summary of Media Rules:
1. **ComfyUI (`http://192.168.1.74:8188`)**:
   - Mandatory for all photographic product backdrops, flat-lays, apparel, stationery, and e-commerce staging.
   - **Zero Flat PIL Drawings**: Never use PIL geometric rectangles or artificial shapes for mockups.
   - **Physical Realism**: Stickers belong on closed laptops, insulated tumblers, paper journals/planners, and cutting mats—never pasted floating on an iPad screen. Apply realistic directional contact shadows, cylindrical curvature, and optional harmonizing img2img passes.
2. **Blender 5.2 LTS (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`)**:
   - Engine for 3D products (cookie cutters, organizers, planters, keychains).
   - Physically based shaders (FDM layer-line bump for PLA, subsurface scattering for dough, realistic wood grain) rendered headless via `etsy_factory/blender_render.py` in Cycles or EEVEE Next.
   - Manifold watertight STL verification.
3. **DaVinci Resolve Studio 21.1+ (`ResolvePython.exe` / `ResolveMCP.exe`)**:
   - Engine for listing video previews (5-15s) and short-form marketing reels.
   - Neural Engine Super Scale (3x) + Optical Flow + 33x33x33 Cinema 3D LUT grading + NVENC GPU hardware export.
4. **Mandatory Visual QC**:
   - Always view every generated listing card via `read_file` to verify layout, zero clipping, balanced margins, and realistic material integration before presenting to the Commander.
