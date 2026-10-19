"""Second batch of quote-pack niches (nurse, coffee, valentine, motivational, pets, graduation). Merged into NICHES by niche_defs."""
from __future__ import annotations

from typing import Dict

from .engine import Style
from .niches import coffee_quotes, grad_quotes, motivational_quotes, nurse_quotes, pets_quotes, valentine_quotes
from .pack import Niche

INK = (26, 26, 34)
RETRO = ["shrikhand", "luckiest", "bagel", "chewy", "titan", "bungee", "alfaslab", "passion"]

_NURSE_PAL = [
    dict(main=(20, 70, 90), accent=(236, 100, 130), orn=(120, 200, 200), frame=(20, 70, 90)),
    dict(main=(30, 50, 100), accent=(60, 180, 170), orn=(250, 150, 160), frame=(30, 50, 100)),
    dict(main=INK, accent=(236, 90, 120), orn=(80, 190, 190), frame=INK),
    dict(main=(110, 40, 80), accent=(90, 190, 180), orn=(250, 190, 120), frame=(110, 40, 80)),
    dict(main=(40, 90, 80), accent=(240, 130, 140), orn=(250, 210, 130), frame=(40, 90, 80)),
]
_COFFEE_PAL = [
    dict(main=(70, 44, 32), accent=(200, 130, 80), orn=(236, 200, 150), frame=(70, 44, 32)),
    dict(main=(52, 36, 30), accent=(220, 150, 100), orn=(180, 140, 100), frame=(52, 36, 30)),
    dict(main=(96, 58, 40), accent=(60, 120, 110), orn=(240, 200, 140), frame=(96, 58, 40)),
    dict(main=INK, accent=(214, 140, 90), orn=(236, 200, 150), frame=INK),
    dict(main=(60, 70, 60), accent=(210, 140, 90), orn=(230, 195, 140), frame=(60, 70, 60)),
]
_VAL_PAL = [
    dict(main=(168, 28, 56), accent=(250, 120, 150), orn=(250, 190, 200), frame=(168, 28, 56)),
    dict(main=(120, 30, 70), accent=(240, 100, 130), orn=(250, 200, 120), frame=(120, 30, 70)),
    dict(main=INK, accent=(240, 70, 110), orn=(250, 150, 170), frame=INK),
    dict(main=(200, 50, 80), accent=(100, 40, 70), orn=(250, 180, 190), frame=(200, 50, 80)),
    dict(main=(90, 40, 90), accent=(250, 110, 140), orn=(250, 200, 150), frame=(90, 40, 90)),
]
_MOTIV_PAL = [
    dict(main=(40, 60, 90), accent=(250, 140, 70), orn=(250, 200, 80), frame=(40, 60, 90)),
    dict(main=(50, 80, 70), accent=(240, 150, 90), orn=(250, 210, 120), frame=(50, 80, 70)),
    dict(main=INK, accent=(250, 120, 100), orn=(100, 190, 190), frame=INK),
    dict(main=(110, 50, 80), accent=(80, 180, 170), orn=(250, 190, 90), frame=(110, 50, 80)),
    dict(main=(70, 60, 120), accent=(250, 150, 100), orn=(250, 210, 110), frame=(70, 60, 120)),
]
_PET_PAL = [
    dict(main=(80, 54, 40), accent=(210, 120, 80), orn=(240, 200, 140), frame=(80, 54, 40)),
    dict(main=(40, 60, 80), accent=(240, 150, 90), orn=(130, 190, 180), frame=(40, 60, 80)),
    dict(main=INK, accent=(236, 110, 120), orn=(240, 190, 90), frame=INK),
    dict(main=(70, 90, 70), accent=(220, 140, 90), orn=(240, 205, 130), frame=(70, 90, 70)),
    dict(main=(100, 50, 60), accent=(90, 170, 170), orn=(245, 195, 110), frame=(100, 50, 60)),
]
_GRAD_PAL = [
    dict(main=(24, 40, 90), accent=(212, 160, 40), orn=(236, 200, 100), frame=(24, 40, 90)),
    dict(main=(110, 24, 44), accent=(212, 160, 40), orn=(236, 200, 120), frame=(110, 24, 44)),
    dict(main=INK, accent=(212, 160, 40), orn=(236, 200, 100), frame=INK),
    dict(main=(20, 70, 70), accent=(240, 190, 70), orn=(250, 215, 130), frame=(20, 70, 70)),
    dict(main=(70, 40, 110), accent=(240, 190, 70), orn=(250, 215, 130), frame=(70, 40, 110)),
]

_FRIENDLY_MAINS = ["lilita", "paytone", "righteous", "bagel", "chewy", "poppins", "montserrat", "spartan", "amatic", "bebas", "oswald", "passion"]
_FRIENDLY_ACCENTS = ["pacifico", "satisfy", "cookie", "courgette", "lobster", "damion", "kaushan", "dancing", "sofia", "yellowtail"]

MORE: Dict[str, Niche] = {
    "nurse": Niche(
        key="nurse", slug="nurse_life_quotes_svg_png_bundle", name="Nurse Life Quotes", short="Nurse",
        quotes=nurse_quotes.QUOTES,
        style=Style(mains=_FRIENDLY_MAINS + ["anton"], accents=_FRIENDLY_ACCENTS,
                    templates={"stack": 5, "retro": 2.0, "badge": 1.4, "frame": 1.6, "banner": 0.8, "arch": 1.0},
                    orn=("hearts", "stars", "sparkle", "sprig", "swash", "cross"), caps=0.45, retro=RETRO),
        palettes=_NURSE_PAL, theme="sunny",
        title="Nurse SVG Bundle, {n} Nurse Life Quotes Cut Files, Nurse Shirt PNG, Cricut Silhouette, Sublimation, Nurses Week Gift Designs, Commercial Use",
        tags=["nurse svg", "nurse svg bundle", "nurse life svg", "nurse shirt png", "nurse png", "nurses week svg", "cricut cut files",
              "svg bundle", "sublimation png", "nursing svg", "scrub life svg", "nurse gift svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Cheerful nurse-life typography - nurse specialties, CNA, LPN, RN, healthcare heroes, scrub life and nurses week - composed with matched fonts and playful flourishes, ready to cut or press.",
        uses="Nurse T-shirts, scrub tops, tote bags, mugs, tumblers, badge reels, nurse graduation and appreciation gifts",
        seo=["nurse", "nurses week", "healthcare", "scrubs"]),
    "coffee": Niche(
        key="coffee", slug="coffee_lover_quotes_svg_png_bundle", name="Coffee Lover Quotes", short="Coffee",
        quotes=coffee_quotes.QUOTES,
        style=Style(mains=_FRIENDLY_MAINS, accents=_FRIENDLY_ACCENTS,
                    templates={"stack": 5, "retro": 2.4, "badge": 1.2, "frame": 1.2, "banner": 0.8, "arch": 1.2},
                    orn=("sparkle", "stars", "swash", "sprig", "hearts", "daisy"), caps=0.4, retro=RETRO),
        palettes=_COFFEE_PAL, theme="sunny",
        title="Coffee SVG Bundle, {n} Coffee Lover Quotes Cut Files, Funny Coffee Mug PNG, Cricut, Sublimation, Latte Iced Coffee, Commercial Use",
        tags=["coffee svg", "coffee svg bundle", "coffee quotes svg", "coffee mug svg", "coffee png", "latte svg", "iced coffee svg",
              "cricut cut files", "svg bundle", "sublimation png", "coffee lover svg", "funny coffee svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Coffee-lover typography for mugs, tumblers, tees and kitchen signs - latte, iced coffee, caffeine and cafe quotes - composed with matched fonts and cheerful flourishes, ready to cut or press.",
        uses="Coffee mugs, tumblers, T-shirts, tote bags, kitchen signs, coffee bar decor, gifts for coffee lovers",
        seo=["coffee", "latte", "caffeine", "mug"]),
    "valentine": Niche(
        key="valentine", slug="valentines_day_quotes_svg_png_bundle", name="Valentines Day Quotes", short="Valentine's",
        quotes=valentine_quotes.QUOTES,
        style=Style(mains=["shrikhand", "luckiest"] + _FRIENDLY_MAINS[:10], accents=_FRIENDLY_ACCENTS + ["greatvibes"],
                    templates={"stack": 5, "retro": 2.6, "badge": 1.2, "frame": 1.4, "banner": 0.8, "arch": 1.4},
                    orn=("hearts", "sparkle", "stars", "swash", "daisy"), caps=0.35, retro=RETRO),
        palettes=_VAL_PAL, theme="sunny",
        title="Valentines Day SVG Bundle, {n} Valentine Quotes Cut Files, Love Heart PNG, Cricut, Sublimation, Galentine, Anti Valentine, Commercial Use",
        tags=["valentines svg", "valentine svg bundle", "valentines day svg", "love svg", "heart svg", "galentines svg", "valentine shirt png",
              "cricut cut files", "svg bundle", "sublimation png", "valentine png", "kids valentine svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Sweet, sassy and silly Valentine's Day typography - be mine, love bug, galentine, anti-valentine and pet valentines - composed with matched fonts and heart flourishes, ready to cut or press.",
        uses="Valentine T-shirts, sweatshirts, mugs, tumblers, tote bags, kids valentine shirts, gift bags, wood signs, galentine party favors",
        seo=["valentines", "love", "galentine", "heart"]),
    "motivational": Niche(
        key="motivational", slug="motivational_positive_quotes_svg_png_bundle", name="Motivational Positive Quotes", short="Motivational",
        quotes=motivational_quotes.QUOTES,
        style=Style(mains=["anton", "bebas", "oswald", "archivo", "poppins", "montserrat", "spartan", "lilita", "paytone", "righteous", "amatic", "passion"],
                    accents=["pacifico", "lobster", "kaushan", "cookie", "satisfy", "damion", "yellowtail", "oleo", "sofia", "marck", "dancing"],
                    templates={"stack": 6, "retro": 1.6, "badge": 1.2, "frame": 1.4, "banner": 0.6, "arch": 1.2},
                    orn=("sparkle", "stars", "swash", "divider", "sprig", "bolt"), caps=0.5, retro=RETRO),
        palettes=_MOTIV_PAL, theme="sunny",
        title="Motivational Quotes SVG Bundle, {n} Positive Inspirational Cut Files, Self Love PNG, Cricut, Sublimation Shirt Mug, Commercial Use",
        tags=["motivational svg", "positive svg bundle", "inspirational svg", "quotes svg", "good vibes svg", "self love svg", "cricut cut files",
              "svg bundle", "sublimation png", "motivation shirt svg", "positive vibes png", "affirmation svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Uplifting motivational and positive-vibes typography - you got this, stay kind, dream big, bloom where you are planted - composed with matched fonts and bright flourishes, ready to cut or press.",
        uses="T-shirts, sweatshirts, mugs, tumblers, tote bags, wood signs, planners, classroom and office decor",
        seo=["motivational", "positive", "inspirational", "good vibes"]),
    "pets": Niche(
        key="pets", slug="dog_mom_cat_mom_pet_quotes_svg_png_bundle", name="Dog Mom Cat Mom Pet Quotes", short="Pet Lover",
        quotes=pets_quotes.QUOTES,
        style=Style(mains=_FRIENDLY_MAINS, accents=_FRIENDLY_ACCENTS,
                    templates={"stack": 5, "retro": 2.2, "badge": 1.4, "frame": 1.4, "banner": 0.8, "arch": 1.2},
                    orn=("hearts", "stars", "sparkle", "daisy", "sprig", "swash"), caps=0.4, retro=RETRO),
        palettes=_PET_PAL, theme="sunny",
        title="Dog Mom SVG Bundle, {n} Dog Mom Cat Mom Pet Lover Quotes Cut Files, Dog Dad PNG, Cricut, Sublimation Shirt Mug, Commercial Use",
        tags=["dog mom svg", "dog mom svg bundle", "cat mom svg", "dog dad svg", "pet lover svg", "dog quotes svg", "rescue dog svg",
              "cricut cut files", "svg bundle", "sublimation png", "dog mom shirt png", "cat lady svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Dog mom, dog dad, cat mom and rescue-love typography with paw-print charm - composed with matched fonts and cheerful flourishes, ready to cut or press.",
        uses="Dog mom and cat mom T-shirts, sweatshirts, mugs, tumblers, tote bags, pet bandana shirts, signs, gifts for pet lovers",
        seo=["dog mom", "cat mom", "pet lover", "rescue"]),
    "grad": Niche(
        key="grad", slug="graduation_2027_class_of_quotes_svg_png_bundle", name="Graduation 2027 Quotes", short="Graduation",
        quotes=grad_quotes.QUOTES,
        style=Style(mains=["anton", "bebas", "oswald", "archivo", "poppins", "montserrat", "spartan", "alfaslab", "titan", "bungee", "lilita", "passion"],
                    accents=["pacifico", "lobster", "kaushan", "cookie", "satisfy", "damion", "yellowtail", "oleo", "sofia", "marck", "dancing", "greatvibes"],
                    templates={"stack": 5, "retro": 1.6, "badge": 1.6, "frame": 1.6, "banner": 1.0, "arch": 1.4},
                    orn=("stars", "sparkle", "swash", "divider", "sprig"), caps=0.6, retro=["alfaslab", "shrikhand", "titan", "bungee"]),
        palettes=_GRAD_PAL, theme="sunny",
        title="Graduation 2027 SVG Bundle, {n} Class of 2027 Senior Grad Cut Files, Graduate PNG, Cricut, Sublimation Shirt Designs, Commercial Use",
        tags=["graduation svg", "class of 2027 svg", "senior 2027 svg", "grad svg bundle", "graduation png", "graduate svg", "grad shirt svg",
              "cricut cut files", "svg bundle", "sublimation png", "senior mom svg", "proud grad svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Class of 2027 graduation typography - senior, grad, proud mom and dad, kindergarten through college - composed with bold fonts, script accents and gold-star flourishes, ready to cut or press.",
        uses="Graduation T-shirts, sweatshirts, cap decorations, mugs, tumblers, tote bags, banners, yard signs, grad party gifts",
        seo=["graduation", "class of 2027", "senior", "grad"]),
}
