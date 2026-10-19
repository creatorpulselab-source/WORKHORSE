"""Curated font registry for the typography engine: roles, weights, embolden (so hairline scripts cut cleanly) and pairings."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .text import FONT_DIR, Face, load_face


@dataclass(frozen=True)
class FontSpec:
    key: str
    file: str
    role: str                    # display | serif | script | brush | retro | hand
    weight: Optional[int] = None  # variable-font weight
    width: Optional[int] = None
    embolden: float = 0.0        # em fraction added to every stroke (thin scripts)
    track: float = 0.0           # default tracking (em)
    upper: bool = False          # looks best in ALL CAPS
    moods: Tuple[str, ...] = ()

    def face(self) -> Face:
        return load_face(self.file, self.weight, self.width)

    def exists(self) -> bool:
        return (FONT_DIR / self.file).exists()


def _f(key, file, role, weight=None, width=None, embolden=0.0, track=0.0, upper=False, moods=()):
    return FontSpec(key, file, role, weight, width, embolden, track, upper, tuple(moods))


FONTS: Dict[str, FontSpec] = {s.key: s for s in [
    # ---- display sans (heavy, tight)
    _f("anton", "Anton-Regular.ttf", "display", upper=True, moods=("bold", "modern")),
    _f("bebas", "BebasNeue-Regular.ttf", "display", upper=True, track=0.02, moods=("clean", "modern")),
    _f("oswald", "Oswald[wght].ttf", "display", weight=700, upper=True, moods=("bold", "modern")),
    _f("gothic", "LeagueGothic[wdth].ttf", "display", weight=None, width=100, upper=True, moods=("tall", "modern")),
    _f("passion", "PassionOne-Black.ttf", "display", moods=("bold", "friendly")),
    _f("archivo", "ArchivoBlack-Regular.ttf", "display", upper=True, moods=("bold", "modern")),
    _f("poppins", "Poppins-ExtraBold.ttf", "display", moods=("clean", "friendly")),
    _f("russo", "RussoOne-Regular.ttf", "display", upper=True, moods=("bold",)),
    _f("montserrat", "Montserrat[wght].ttf", "display", weight=800, moods=("clean",)),
    _f("spartan", "LeagueSpartan[wght].ttf", "display", weight=800, moods=("clean", "modern")),
    _f("bangers", "Bangers-Regular.ttf", "display", upper=True, moods=("comic", "funny")),
    _f("lilita", "LilitaOne-Regular.ttf", "display", moods=("friendly", "funny")),
    _f("righteous", "Righteous-Regular.ttf", "display", moods=("retro", "friendly")),
    _f("paytone", "PaytoneOne-Regular.ttf", "display", moods=("friendly", "bold")),
    # ---- serif
    _f("abril", "AbrilFatface-Regular.ttf", "serif", moods=("elegant", "bold")),
    _f("dmserif", "DMSerifDisplay-Regular.ttf", "serif", moods=("elegant",)),
    _f("gloock", "Gloock-Regular.ttf", "serif", moods=("elegant", "bold")),
    _f("young", "YoungSerif-Regular.ttf", "serif", moods=("warm",)),
    _f("rozha", "RozhaOne-Regular.ttf", "serif", moods=("elegant", "bold")),
    _f("playfair", "PlayfairDisplay[wght].ttf", "serif", weight=800, moods=("elegant",)),
    _f("bodoni", "BodoniModa[opsz,wght].ttf", "serif", weight=700, moods=("elegant",)),
    _f("cinzel", "Cinzel[wght].ttf", "serif", weight=800, upper=True, moods=("elegant", "faith")),
    _f("alfaslab", "AlfaSlabOne-Regular.ttf", "serif", moods=("bold", "retro")),
    # ---- script
    _f("pacifico", "Pacifico-Regular.ttf", "script", moods=("retro", "friendly")),
    _f("lobster", "Lobster-Regular.ttf", "script", moods=("retro", "bold")),
    _f("satisfy", "Satisfy-Regular.ttf", "script", embolden=0.006, moods=("friendly",)),
    _f("courgette", "Courgette-Regular.ttf", "script", embolden=0.004, moods=("friendly",)),
    _f("kaushan", "KaushanScript-Regular.ttf", "script", moods=("bold", "brush")),
    _f("marck", "MarckScript-Regular.ttf", "script", embolden=0.012, moods=("casual",)),
    _f("dancing", "DancingScript[wght].ttf", "script", weight=700, embolden=0.004, moods=("friendly", "elegant")),
    _f("cookie", "Cookie-Regular.ttf", "script", embolden=0.012, moods=("friendly", "retro")),
    _f("damion", "Damion-Regular.ttf", "script", embolden=0.006, moods=("retro",)),
    _f("playball", "Playball-Regular.ttf", "script", embolden=0.008, moods=("elegant",)),
    _f("sofia", "Sofia-Regular.ttf", "script", embolden=0.012, moods=("friendly",)),
    _f("mrdafoe", "MrDafoe-Regular.ttf", "script", moods=("retro", "bold")),
    _f("oleo", "OleoScript-Bold.ttf", "script", moods=("friendly", "bold")),
    _f("yellowtail", "Yellowtail-Regular.ttf", "script", embolden=0.006, moods=("retro",)),
    _f("norican", "Norican-Regular.ttf", "script", embolden=0.006, moods=("elegant",)),
    _f("allura", "Allura-Regular.ttf", "script", embolden=0.018, moods=("elegant", "wedding")),
    _f("greatvibes", "GreatVibes-Regular.ttf", "script", embolden=0.016, moods=("elegant", "wedding")),
    _f("parisienne", "Parisienne-Regular.ttf", "script", embolden=0.012, moods=("elegant",)),
    _f("alexbrush", "AlexBrush-Regular.ttf", "script", embolden=0.016, moods=("elegant",)),
    _f("sacramento", "Sacramento-Regular.ttf", "script", embolden=0.024, moods=("airy",)),
    # ---- brush / marker / hand
    _f("marker", "PermanentMarker-Regular.ttf", "brush", moods=("funny", "bold")),
    _f("brush", "CaveatBrush-Regular.ttf", "brush", embolden=0.006, moods=("casual",)),
    _f("caveat", "Caveat[wght].ttf", "hand", weight=700, embolden=0.004, moods=("casual",)),
    _f("rocksalt", "RockSalt-Regular.ttf", "brush", moods=("funny", "rough")),
    _f("amatic", "AmaticSC-Bold.ttf", "hand", upper=True, embolden=0.012, moods=("boho", "airy")),
    _f("gloria", "GloriaHallelujah.ttf", "hand", embolden=0.004, moods=("casual", "funny")),
    _f("gochi", "GochiHand-Regular.ttf", "hand", moods=("funny", "casual")),
    _f("kalam", "Kalam-Bold.ttf", "hand", moods=("casual",)),
    _f("patrick", "PatrickHand-Regular.ttf", "hand", embolden=0.006, moods=("casual",)),
    # ---- retro / western / gothic
    _f("shrikhand", "Shrikhand-Regular.ttf", "retro", moods=("groovy", "retro")),
    _f("chango", "Chango-Regular.ttf", "retro", moods=("groovy", "bold")),
    _f("modak", "Modak-Regular.ttf", "retro", moods=("groovy", "bubble")),
    _f("luckiest", "LuckiestGuy-Regular.ttf", "retro", upper=True, moods=("comic", "groovy")),
    _f("bagel", "BagelFatOne-Regular.ttf", "retro", moods=("groovy", "bubble")),
    _f("gasoek", "GasoekOne-Regular.ttf", "retro", moods=("bold", "modern")),
    _f("chewy", "Chewy-Regular.ttf", "retro", moods=("funny", "bubble")),
    _f("titan", "TitanOne-Regular.ttf", "retro", moods=("bubble", "friendly")),
    _f("rye", "Rye-Regular.ttf", "retro", upper=True, moods=("western",)),
    _f("pirata", "PirataOne-Regular.ttf", "retro", moods=("gothic", "faith")),
    _f("fraktur", "UnifrakturCook-Bold.ttf", "retro", moods=("gothic",)),
    _f("bungee", "Bungee-Regular.ttf", "retro", upper=True, moods=("sign", "bold")),
    _f("special", "SpecialElite-Regular.ttf", "hand", moods=("typewriter",)),
]}


def available() -> Dict[str, FontSpec]:
    return {k: v for k, v in FONTS.items() if v.exists()}


def by_role(role: str) -> List[FontSpec]:
    return [v for v in available().values() if v.role == role]


def get(key: str) -> FontSpec:
    return FONTS[key]
