"""Third batch of quote-pack niches: military mom / wife (homefront) and magical family vacation. Merged into NICHES by niche_defs."""
from __future__ import annotations

from typing import Dict

from .engine import Style
from .niches import military_quotes, vacation_quotes
from .pack import Niche

INK = (26, 26, 34)
RETRO = ["shrikhand", "luckiest", "bagel", "chewy", "titan", "bungee", "alfaslab", "passion"]

_MIL_PAL = [
    dict(main=(34, 52, 90), accent=(176, 36, 48), orn=(120, 130, 90), frame=(34, 52, 90)),        # navy / red / olive
    dict(main=(64, 72, 44), accent=(176, 140, 70), orn=(44, 54, 34), frame=(64, 72, 44)),         # olive / tan
    dict(main=INK, accent=(176, 36, 48), orn=(34, 52, 90), frame=INK),                            # black / red / navy
    dict(main=(88, 74, 52), accent=(40, 62, 100), orn=(150, 120, 80), frame=(88, 74, 52)),        # khaki / navy
    dict(main=(28, 44, 76), accent=(200, 60, 60), orn=(160, 170, 190), frame=(28, 44, 76)),       # deep navy / red / steel
]
_VAC_PAL = [
    dict(main=(90, 40, 120), accent=(236, 100, 160), orn=(246, 190, 70), frame=(90, 40, 120)),    # purple / pink / gold
    dict(main=(30, 70, 120), accent=(240, 120, 170), orn=(250, 205, 90), frame=(30, 70, 120)),    # blue / pink / gold
    dict(main=INK, accent=(236, 90, 150), orn=(250, 195, 70), frame=INK),
    dict(main=(20, 110, 120), accent=(240, 130, 150), orn=(250, 205, 100), frame=(20, 110, 120)),  # teal / coral / gold
    dict(main=(150, 50, 110), accent=(90, 150, 210), orn=(250, 200, 90), frame=(150, 50, 110)),   # berry / sky / gold
]

_FRIENDLY_MAINS = ["lilita", "paytone", "righteous", "bagel", "chewy", "poppins", "montserrat", "spartan", "amatic", "bebas", "oswald", "passion"]
_FRIENDLY_ACCENTS = ["pacifico", "satisfy", "cookie", "courgette", "lobster", "damion", "kaushan", "dancing", "sofia", "yellowtail", "greatvibes"]
_MIL_MAINS = ["bebas", "oswald", "anton", "alfaslab", "titan", "bungee", "spartan", "montserrat", "poppins", "archivo"]

MORE3: Dict[str, Niche] = {
    "military": Niche(
        key="military", slug="military_mom_wife_homefront_quotes_svg_png_bundle", name="Military Mom and Wife Quotes", short="Military",
        quotes=military_quotes.QUOTES,
        style=Style(mains=_MIL_MAINS, accents=_FRIENDLY_ACCENTS,
                    templates={"stack": 3, "emblem": 3.5, "heart": 2.0, "badge": 1.5, "banner": 0.8, "frame": 1.0, "retro": 0.8},
                    orn=("dogtag", "stars", "sparkle", "hearts", "swash"), caps=0.6, retro=["alfaslab", "titan", "bungee", "shrikhand"]),
        palettes=_MIL_PAL, theme="sunny",
        title="Military Mom SVG Bundle, {n} Military Wife Quotes Cut Files, Army Navy Air Force Marine Mom Shirt PNG, Cricut, Sublimation, Deployment",
        tags=["military mom svg", "military wife svg", "army mom svg", "navy mom svg", "air force mom svg", "marine mom svg", "deployment svg",
              "military svg bundle", "cricut cut files", "military shirt png", "sublimation png", "homefront svg", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Proud military mom, wife and family typography - Army, Navy, Air Force, Marine, Coast Guard and National Guard, deployment, homecoming and home-front phrases - "
              "composed with matched fonts and dog tag, boot, anchor and star flourishes, ready to cut or press.",
        uses="Military mom and wife T-shirts, sweatshirts, tumblers, mugs, tote bags, deployment care-package gifts, homecoming signs, graduation and send-off shirts",
        seo=["military mom", "military wife", "deployment", "homefront"]),
    "vacation": Niche(
        key="vacation", slug="magical_family_vacation_quotes_svg_png_bundle", name="Magical Family Vacation Quotes", short="Magical vacation",
        quotes=vacation_quotes.QUOTES,
        style=Style(mains=_FRIENDLY_MAINS + ["shrikhand", "luckiest"], accents=_FRIENDLY_ACCENTS,
                    templates={"stack": 3, "emblem": 4.0, "heart": 2.5, "retro": 1.5, "badge": 0.8, "frame": 0.6},
                    orn=("castle", "wand", "balloon", "sparkle", "stars", "hearts", "swash", "sparkle"), caps=0.35, retro=RETRO),
        palettes=_VAC_PAL, theme="sunny",
        title="Magical Family Vacation SVG Bundle, {n} Trip Quotes Cut Files, Castle Sparkle PNG, Matching Family Shirts, Cricut, Sublimation, Commercial Use",
        tags=["family vacation svg", "magical vacation svg", "family trip svg", "vacation shirt png", "castle svg", "matching shirts svg", "theme park svg",
              "girls trip svg", "cricut cut files", "svg bundle", "sublimation png", "vacation svg bundle", "commercial use svg"],
        price=4.99, list_price=7.99,
        intro="Magical family vacation typography - first trips, birthday trips, girls trips, matching family crews, castle days, sparkle, sunshine and fireworks - "
              "composed with matched fonts and castle, wand, balloon and sparkle flourishes, ready to cut or press.",
        uses="Matching family vacation T-shirts, sweatshirts, tumblers, mugs, tote bags, birthday trip shirts, girls trip and cousin crew shirts, travel gifts",
        seo=["family vacation", "magical", "castle", "theme park"]),
}
