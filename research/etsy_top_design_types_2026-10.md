# Etsy top digital-download design types - Oct 2026 (condensed; research agent, sources unverified at page level)

Legend: [V] consistent across sources/official; [U] unverified. P = fully procedural, P+ = procedural + optional AI, AI = needs AI illustration.

## Etsy rules that shape the pipeline
- Max 5 files per listing, 20 MB each. Filenames <= 70 chars, alnum . _ - only. SVG/DXF/EPS/3MF/OTF are NOT native upload types -> ship in .zip. STL, PNG, PDF, JPG native.
- Photos: up to 20 (+1 video) [verify in editor]. >= 2000 px short side, sRGB JPEG, keep key content in central ~70%.
- AI: seller-prompted AI = "Designed by a seller"; the DESCRIPTION must disclose AI use. Procedural vector output is plainly original. Add a one-liner when ComfyUI backgrounds/mockups are used.
- No trademarked/fan content (Disney, sports teams, anime, brands) in files, titles or tags. No resold PLR/MRR bundles.
- Fees: $0.20 listing, 6.5% transaction, 3%+$0.25 processing.

## Cross-cutting
- Mega bundles win (50-200 designs, $3-15). Cover: bold headline + "Digital Download" badge + collage of 6-12 designs + 1-2 real-looking mockups. Then contact sheets, mockups (Comfort Colors shirt, mug, wood sign, tote, tumbler), formats image, how-it-works, license image.
- Title: [Theme] [Product] Bundle, [use-case], [Machine: Cricut/Silhouette/Glowforge], [purpose]. Use all 13 tags (broad + long-tail). Put the year in ornament/grad titles.
- License wording: "Small business commercial use included" (up to ~500 units), no resale/redistribution/POD upload, extended license tier, PDF license in the zip.

## Buyer complaints to engineer around
1. Unwelded script text -> union all glyphs into one compound shape.
2. Too many nodes (auto-trace) -> simplify (Douglas-Peucker), keep paths low.
3. One flat layer or hundreds of loose pieces -> group by colour, named layers, back-to-front order.
4. Wrong size on import -> SVG width/height in in/mm with matching viewBox; state size in PDF.
5. SVG vs PNG confusion -> PDF "how to use" with exact scale + Cricut/Silhouette steps.
6. Tiny islands/slivers/overlaps, bad laser kerf -> min feature size, kerf parameter, consistent cut/engrave colours.
7. Low-quality AI-looking vector conversions -> avoid; keep vectors procedural.

## Roster (ranked by fit to the factory)
| # | Type | Contents | Price | Fit |
|---|------|----------|-------|-----|
| 1 | Seasonal SVG/PNG mega-bundle (shirt/mug/sign) | 50-200 designs; SVG+PNG300+DXF+EPS+PDF in 3-5 zips | $3-15 | P+ (typography, badges, frames, hearts, snowflakes = P) |
| 2 | Sublimation PNG bundles | 10-50 PNG 300dpi transparent, 10-12 in | $2.5-7 | P+ (type/pattern P; illustration AI) |
| 3 | Tumbler wraps (20oz skinny ~9.3x8.2in, 30/40oz, mug) | PNG 300dpi templates, seamless patterns | $2-6 single, $7-15 packs | P/P+ |
| 4 | Alphabet / monogram / split-monogram / font packs | A-Z, numerals, 3-10 styles; SVG/DXF/EPS/PNG (+OTF/TTF) | $3-12 | P (strongest) |
| 5 | Laser-cut SVG (Glowforge/xTool): ornaments, earrings, signs, coasters, name plaques | SVG+DXF+EPS+PDF, colour-coded layers, kerf notes | $3-10 | P+ |
| 6 | Layered paper-cut / shadow-box / light-box | 5-10 layers per design + assembly PDF | $3-10 | P+ |
| 7 | Printable / digital sticker sheets | PNG sheets 300dpi + PDF + cut lines | $1.5-3.5 / $5-15 | P/P+ |
| 8 | Digital paper & seamless patterns | 10-50 JPG/PNG 12x12 @300dpi + tileable | $2-15 | P (geometric) / AI (illustrated) |
| 9 | Digital planners / printables (PDF) | hyperlinked 2027 planners + stickers | $7-40 | P |
| 10 | Wall art printables | JPG/PNG/PDF in 5 ratios | $3-25 | P+ / AI |
| 11 | STL/3MF 3D-print files | STL native; 3MF in zip | $3-25 | P/P+ |
| 12 | Machine embroidery | multi-format zips | $1.5-20 | SKIP (untestable) |

## Seasonal calendar (upload ~8-12 weeks before holiday)
- Now-mid Nov 2026: Christmas (retro/groovy, nutcracker/coquette, gothmas, 2026 ornaments, laser ornaments, winter village), teacher/nurse, 2027 planners, cookie cutters.
- Late Nov-Dec 2026: Valentine 2027 (coquette, checkerboard hearts, anti-Valentine, teacher valentines), Class of 2027, New Year, winter.
- Jan-Feb 2027: Easter/spring, St Patrick's. Mar-Apr: Mother's Day, teacher appreciation, grad. May-Jul: summer, 4th of July, back-to-school. Jul-Sep: Halloween 2027, fall, Christmas 2027.

## Factory build order recommended
1 monogram/alphabet/font packs -> 2 laser-cut geometric/ornament -> 3 seasonal typography SVG bundles with frames -> 4 seamless patterns + tumbler wraps -> 5 shadow-box/layered -> 6 planners -> 7 parametric STL -> 8 illustrated clipart/sublimation (AI + disclosure).

## Engineering checklist
- shapely unary_union for welding; one compound path per colour layer; simplify pass; min feature size; SVG size in in/mm + viewBox; stroke-free fills; named layers.
- Ship SVG, DXF (flattened curves), EPS, PNG 300dpi transparent, PDF guide, LICENSE.pdf; <= 5 zips <= 20 MB.
- Auto contact sheet + mockups; verify via headless render + node-count/closed-path checks.
- Write AI-disclosure line into descriptions where ComfyUI content is used.

## Open questions
- Real search rankings / unit sales (need EtsyHunt/eRank/Marmalead). Whether the 20-photo limit and "visible watermark" guidance apply to the shop. Cricut's actual path limits (test in Design Space).
