"""Niche definitions (style, palettes, marketplace copy) for the quote packs."""
from __future__ import annotations

from typing import Dict

from .engine import Style
from .niches import faith_quotes, mom_quotes, sarcasm_quotes, teacher_quotes
from .pack import Niche

INK = (26, 26, 34)

_SARC_PAL = [
    dict(main=INK, accent=(255, 64, 129), orn=(255, 183, 3), frame=INK),
    dict(main=INK, accent=(0, 150, 170), orn=(255, 112, 67), frame=INK),
    dict(main=(88, 36, 120), accent=(255, 112, 67), orn=(255, 183, 3), frame=(88, 36, 120)),
    dict(main=(20, 40, 80), accent=(255, 87, 100), orn=(255, 200, 60), frame=(20, 40, 80)),
    dict(main=(122, 31, 61), accent=(33, 150, 130), orn=(246, 190, 70), frame=(122, 31, 61)),
    dict(main=INK, accent=(76, 175, 80), orn=(240, 98, 146), frame=INK),
]
_FAITH_PAL = [
    dict(main=(60, 52, 48), accent=(176, 120, 90), orn=(196, 160, 110), frame=(60, 52, 48)),
    dict(main=(40, 60, 70), accent=(184, 134, 98), orn=(150, 170, 150), frame=(40, 60, 70)),
    dict(main=(88, 52, 52), accent=(200, 150, 100), orn=(120, 140, 110), frame=(88, 52, 52)),
    dict(main=INK, accent=(168, 124, 160), orn=(200, 170, 110), frame=INK),
    dict(main=(52, 74, 62), accent=(190, 140, 110), orn=(222, 190, 140), frame=(52, 74, 62)),
]
_MOM_PAL = [
    dict(main=(70, 50, 44), accent=(224, 120, 100), orn=(236, 190, 90), frame=(70, 50, 44)),
    dict(main=(60, 80, 70), accent=(236, 140, 130), orn=(240, 200, 120), frame=(60, 80, 70)),
    dict(main=(150, 60, 70), accent=(232, 170, 70), orn=(120, 150, 130), frame=(150, 60, 70)),
    dict(main=INK, accent=(240, 120, 150), orn=(250, 200, 80), frame=INK),
    dict(main=(60, 60, 100), accent=(240, 140, 110), orn=(250, 205, 110), frame=(60, 60, 100)),
]
_TEACH_PAL = [
    dict(main=(30, 58, 92), accent=(232, 84, 72), orn=(250, 190, 60), frame=(30, 58, 92)),
    dict(main=(36, 70, 60), accent=(240, 150, 60), orn=(250, 205, 100), frame=(36, 70, 60)),
    dict(main=INK, accent=(236, 90, 110), orn=(60, 170, 190), frame=INK),
    dict(main=(110, 40, 60), accent=(60, 150, 140), orn=(250, 190, 70), frame=(110, 40, 60)),
    dict(main=(70, 50, 120), accent=(250, 150, 80), orn=(250, 210, 90), frame=(70, 50, 120)),
]

RETRO = ["shrikhand", "luckiest", "bagel", "chewy", "titan", "bungee", "alfaslab", "passion"]   # heavy blobby faces (modak/chango/gasoek) removed: counters filled in and cut files weeded badly

NICHES: Dict[str, Niche] = {
    "sarcasm": Niche(
        key="sarcasm", slug="sarcastic_funny_quotes_svg_png_bundle", name="Funny Sarcastic Quotes", short="Sarcastic",
        quotes=sarcasm_quotes.QUOTES,
        style=Style(mains=["anton", "bebas", "oswald", "archivo", "poppins", "marker", "bangers", "passion", "gothic", "lilita", "montserrat", "spartan"],
                    accents=["pacifico", "lobster", "kaushan", "cookie", "satisfy", "damion", "yellowtail", "oleo", "mrdafoe", "sofia", "marck", "dancing"],
                    templates={"stack": 6, "retro": 1.6, "badge": 1.1, "frame": 1.4, "banner": 0.5, "arch": 0.0},
                    orn=("sparkle", "swash", "divider", "stars", "bolt"), caps=0.6, retro=RETRO),
        palettes=_SARC_PAL, theme="sunny",
        title="Funny Sarcastic Quotes SVG Bundle, {n} Sarcasm Cut Files, Cricut Silhouette, PNG Sublimation, Sassy Shirt Mug Designs, Commercial Use",
        tags=["sarcastic svg", "funny svg bundle", "sarcasm png", "cricut cut files", "funny quotes svg", "svg bundle", "sublimation png",
              "funny shirt svg", "silhouette svg", "mug design svg", "sassy svg", "commercial use svg", "sarcasm shirt png"],
        price=4.99, list_price=7.99,
        intro="Sarcastic, funny and sassy quote designs for shirts, mugs, tumblers, totes and signs - each one hand-composed typography with matched fonts, flourishes and clean welded cut paths.",
        uses="T-shirts, sweatshirts, mugs, tumblers, tote bags, wood signs, stickers, decals, hats",
        seo=["funny quotes", "sarcasm", "sassy", "adulting", "coffee humor"]),
    "faith": Niche(
        key="faith", slug="christian_faith_quotes_svg_png_bundle", name="Christian Faith Quotes", short="Faith",
        quotes=faith_quotes.QUOTES,
        style=Style(mains=["cinzel", "playfair", "abril", "dmserif", "gloock", "bodoni", "poppins", "montserrat", "spartan", "bebas", "oswald"],
                    accents=["greatvibes", "allura", "parisienne", "dancing", "satisfy", "playball", "alexbrush", "norican", "sofia", "cookie", "yellowtail"],
                    templates={"stack": 6, "retro": 0.1, "badge": 1.3, "frame": 2.0, "banner": 0.4, "arch": 1.0},
                    orn=("cross", "divider", "sprig", "stars", "swash"), caps=0.55, retro=["alfaslab", "shrikhand"]),
        palettes=_FAITH_PAL, theme="forest",
        title="Christian Faith Quotes SVG Bundle, {n} Bible Verse Cut Files, Jesus Religious PNG, Cricut Silhouette, Sublimation Shirt Designs, Commercial Use",
        tags=["christian svg", "faith svg bundle", "bible verse svg", "jesus svg", "religious png", "scripture svg", "cricut cut files",
              "christian shirt svg", "faith png", "svg bundle", "sublimation png", "church svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Beautiful faith-based typography - scripture, encouragement and worship phrases - composed with elegant serif and script pairings and clean, cut-ready vector paths.",
        uses="T-shirts, sweatshirts, mugs, tumblers, tote bags, wood signs, church events, gifts",
        seo=["faith", "bible verse", "jesus", "scripture"]),
    "mom": Niche(
        key="mom", slug="mom_life_mama_quotes_svg_png_bundle", name="Mom Life Mama Quotes", short="Mom Life",
        quotes=mom_quotes.QUOTES,
        style=Style(mains=["lilita", "passion", "poppins", "paytone", "righteous", "bagel", "chewy", "montserrat", "spartan", "amatic", "bebas"],
                    accents=["pacifico", "satisfy", "cookie", "courgette", "lobster", "damion", "kaushan", "dancing", "sofia", "yellowtail"],
                    templates={"stack": 5, "retro": 2.4, "badge": 1.0, "frame": 1.5, "banner": 0.7, "arch": 1.6},
                    orn=("hearts", "daisy", "sparkle", "swash", "sprig", "stars"), caps=0.35, retro=RETRO),
        palettes=_MOM_PAL, theme="sunny",
        title="Mom Life SVG Bundle, {n} Mama Quotes Cut Files, Mothers Day Mom Shirt PNG, Cricut Silhouette, Sublimation, Retro Boho Designs, Commercial Use",
        tags=["mom svg", "mama svg bundle", "mom life svg", "mothers day svg", "mom shirt png", "boy mom svg", "girl mom svg",
              "cricut cut files", "svg bundle", "sublimation png", "mama png", "sports mom svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Retro, boho and playful mom-life designs - mama, boy mom, girl mom, sports mom, grandma and more - composed with matched fonts and cheerful flourishes, ready to cut or press.",
        uses="T-shirts, sweatshirts, mugs, tumblers, tote bags, Mother's Day gifts, baby shower gifts, signs",
        seo=["mom life", "mama", "mothers day", "boy mom"]),
    "teacher": Niche(
        key="teacher", slug="teacher_life_quotes_svg_png_bundle", name="Teacher Life Quotes", short="Teacher",
        quotes=teacher_quotes.QUOTES,
        style=Style(mains=["lilita", "paytone", "righteous", "bagel", "chewy", "poppins", "montserrat", "spartan", "amatic", "bebas", "oswald", "passion"],
                    accents=["pacifico", "satisfy", "cookie", "courgette", "lobster", "damion", "kaushan", "dancing", "sofia", "yellowtail"],
                    templates={"stack": 5, "retro": 2.2, "badge": 1.3, "frame": 1.6, "banner": 0.8, "arch": 1.2},
                    orn=("stars", "sparkle", "hearts", "daisy", "sprig", "swash"), caps=0.4, retro=RETRO),
        palettes=_TEACH_PAL, theme="sunny",
        title="Teacher SVG Bundle, {n} Teacher Life Quotes Cut Files, Back to School Teacher Shirt PNG, Cricut Silhouette, Sublimation, Commercial Use",
        tags=["teacher svg", "teacher svg bundle", "teacher life svg", "back to school svg", "teacher shirt png", "teacher png",
              "cricut cut files", "svg bundle", "sublimation png", "teacher quotes svg", "school svg", "teacher gift svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Cheerful teacher-life typography - grade levels, school staff, back to school, appreciation week and end of year - composed with matched fonts and playful flourishes, ready to cut or press.",
        uses="Teacher T-shirts, sweatshirts, tote bags, mugs, tumblers, classroom signs, teacher appreciation gifts, school staff shirts",
        seo=["teacher", "back to school", "teacher appreciation", "classroom"]),
}


from .niche_defs_more import MORE  # noqa: E402  (second batch of niches)
NICHES.update(MORE)
