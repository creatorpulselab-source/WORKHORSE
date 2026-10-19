# Etsy top-seller analysis from Carey's screenshots (2026-10-18)

Source: 9 phone screenshots of Etsy "best selling STL files", "best selling SVG", "best selling glow/laser" searches
(archived in `etsy_top_seller_screens_2026-10-18/`). This is REAL market data and overrides the web-research guesses
where they differ.

## 1. What actually sells, by file type

### STL / 3MF (3D printing)
| Winning pattern | Examples seen | Price | Social proof |
|---|---|---|---|
| Mega bundles with a giant count | 1000TB, 800TB+, 500TB+ "mega STL", 1200+ / 1400+ functional, 350+ organizers, 2000+ / 500+ / 200+ Christmas, 9000+ / 8000+ keychains, 4000+ / 10,000+ flexi animals, 1400+ Halloween | list $3-$40, shown $1.50-$9.75 (25-75% "off") | 20-235 reviews, many ads |
| Cute/collectible characters | kawaii can-opener keychains (axolotl, panda, avocado, mushroom, strawberry), highland-cow articulated, reindeer lantern, twisted-dumpling fidget | $2-$7 | 20-200 reviews |
| Humor figures | "middle finger animals" 5 stars | $7.20 (best price in set) | 207 reviews |
| Seasonal | Christmas (Santa, snowman, elf, reindeer, village, ornaments, cookie cutters), Halloween coolers/skulls | $3-$10 | 100-220 reviews |
| Functional (home/office/workshop) | pegboard, desk caddies, phone stands, cable mgmt, drawers | $1.80-$4.90 | 235 reviews on the 1200+ pack |
| Can/cooler holders as themed sets | 100+ cooler can holder pack, Halloween can cooler | $5.49-$6 | 29-116 reviews |
| IP-based (Pokemon) | 1200+ Pokemon pack | $5.87 | AVOID - trademark/suspension risk |

Cover style (STL): giant number as the headline, dense collage of the REAL contents filling the frame (no big empty
panel), glossy/high-contrast look, a badge strip (STL & 3MF, Commercial licence, Instant download, Lifetime access,
Print-ready / no supports, Multi-colour). Functional packs use charcoal/black prints with ONE orange accent on a real
workbench / pegboard / wood desk with props (plants, phone, headphones). Character packs use glossy saturated cute
renders with sticker-style outlines. Nothing is flat, neon or floating - objects look photographed in a setting.

### SVG / PNG (cut files, sublimation, T-shirt)
| Winning pattern | Examples | Price | Social proof |
|---|---|---|---|
| "Whole shop" / mega bundles | 7000+, 35,000, 100,000+, 170,000+, 250,000+, 1M+ graphics | $1.20-$16 (slate coaster set $46.99) | 57-853 reviews, "Bestseller" badges |
| Typography quote bundles (B&W grid cover) | Funny/sarcastic quotes (250+, 6.8k reviews, $5!), 100+ sarcasm PNG, motivational, mom life | $1.20-$5 | up to 6.8k reviews |
| Faith / Christian | Jesus/faith SVG-PNG, oversized-tee mockups on models | $5.59 | 1.1k reviews |
| Illustrated sublimation PNG | highland cow 800+ (776 reviews), spooky Halloween 48, boho leopard motivational 22 (14.8k reviews!), sweary-skeleton humor 110, retro Christmas clipart 13,500+ | $1.60-$3 | 100s-14k reviews |
| Tumbler / laser designs | 160 laser designs for 40oz tumbler (4.3k reviews, $48.66!), key-fob PNG patterns 10,000+ ($7.70, 1.8k) | $7-$49 | thousands |
| Coasters / engraving | 7000+ slate coaster designs $46.99 | $47 | 57 |
| Embroidery | 800,000 embroidery files | - | skip |

Formats shown on covers: SVG, PNG, DXF, EPS (+ AI, PDF, JPG), "Cricut friendly", "300 DPI transparent",
"commercial use", "free future updates". Many cover thumbnails literally show the contents (a dense B&W text grid) so the
buyer sees the variety instantly.

## 2. Media-kit rules extracted
1. Giant count number is the hero. It must be true to our pack (no fake "9,000,000 models").
2. Cover = dense collage of the actual designs/products, edge to edge; text sits on top in outlined chunky type, never in a big panel that hides the product.
3. Badge strip with formats/licence/instant download at the bottom.
4. Products look photographed: real material shading, sitting on a surface with contact shadows, matched lighting, props in context. Muted realistic colours (charcoal, white, wood, sage, terracotta) + at most one accent. Saturated colour is reserved for cute characters and sublimation art.
5. Apparel/typography packs: B&W grid cover + on-model or flat-lay shirt/tumbler/mug mockups.
6. Show scale and use-cases (organizer filled with items, keychain on a bag/keys).
7. Price anchoring: list $3-$15, discount 30-70%, final $1.50-$9.99.

## 3. Gap vs. what the factory built so far
- Pack size: we made 8-12 items; market leaders are 100-10,000. Procedural types can scale to 100-500 honestly.
- Look: neon flat-colour products floating on busy backdrops; market uses realistic dark/neutral materials in scenes.
- Content: no typography, sublimation, flexi, cute-character or Christmas/Halloween packs yet.
- Cover: our frosted panel hides the products.

## 4. Build order (revised from the screenshots)
1. Typography quote bundles (sarcasm/funny, faith, motivational, mom, teacher, nurse, coffee, pets...) - SVG+PNG+DXF+EPS, 100-250 per pack. Fully procedural.
2. Illustrated sublimation / clipart PNG packs via ComfyUI (highland cow, spooky Halloween, retro Christmas, boho/groovy, cute animals) + rembg transparency, 300 DPI - with AI disclosure line.
3. Tumbler-wrap / laser-engrave pattern packs (procedural + AI patterns) and key-fob PNG patterns.
4. 3D: Gridfinity-style functional organizers (100+), parametric desk/workshop sets, cookie cutters (Christmas/Halloween/Valentine themed), flexi articulated animals (procedural), cute character keychains via ComfyUI image-to-3D (Trellis/Hunyuan3D) + loop, can-cooler sets, Christmas ornaments/lanterns.
5. Media kit v2: dense-collage covers, realistic scene integration (table-view backdrops, shadow catcher, Cycles GPU, AgX), IC-Light/img2img unify pass, mockups (shirt/mug/tumbler/tote) generated with ComfyUI.
6. Mega "whole shop" tier built from the above once there are enough packs.
7. Avoid: IP characters (Pokemon etc.), fake counts, untestable embroidery.
