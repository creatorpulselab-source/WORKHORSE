"""Download a broad set of OFL-licensed Google Fonts for the typography engine (outlines only are sold, fonts never redistributed).

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.typo.fetch_fonts
Static (non-variable) files are preferred; variable fonts are instantiated at load time by typo.fonts.
"""
from __future__ import annotations

import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/"

# (relative path in google/fonts repo)
FONTS = [
    # display / bold sans
    "ofl/bebasneue/BebasNeue-Regular.ttf", "ofl/anton/Anton-Regular.ttf", "ofl/bangers/Bangers-Regular.ttf",
    "ofl/passionone/PassionOne-Bold.ttf", "ofl/passionone/PassionOne-Black.ttf", "ofl/paytoneone/PaytoneOne-Regular.ttf",
    "ofl/titanone/TitanOne-Regular.ttf", "ofl/luckiestguy/LuckiestGuy-Regular.ttf", "ofl/chewy/Chewy-Regular.ttf",
    "ofl/archivoblack/ArchivoBlack-Regular.ttf", "ofl/bowlbyone/BowlbyOne-Regular.ttf", "ofl/righteous/Righteous-Regular.ttf",
    "ofl/bungee/Bungee-Regular.ttf", "ofl/poetsenone/PoetsenOne-Regular.ttf", "ofl/alfaslabone/AlfaSlabOne-Regular.ttf",
    "ofl/blackopsone/BlackOpsOne-Regular.ttf", "ofl/russoone/RussoOne-Regular.ttf", "ofl/leaguespartan/LeagueSpartan%5Bwght%5D.ttf",
    "ofl/oswald/Oswald%5Bwght%5D.ttf", "ofl/leaguegothic/LeagueGothic%5Bwdth%5D.ttf", "ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "ofl/poppins/Poppins-Bold.ttf", "ofl/poppins/Poppins-ExtraBold.ttf", "ofl/poppins/Poppins-SemiBold.ttf",
    "ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf", "ofl/baloo2/Baloo2%5Bwght%5D.ttf", "ofl/lilitaone/LilitaOne-Regular.ttf",
    "ofl/gasoekone/GasoekOne-Regular.ttf", "ofl/bagelfatone/BagelFatOne-Regular.ttf", "ofl/chango/Chango-Regular.ttf",
    "ofl/shrikhand/Shrikhand-Regular.ttf", "ofl/modak/Modak-Regular.ttf", "ofl/rubikmonoone/RubikMonoOne-Regular.ttf",
    # serif
    "ofl/abrilfatface/AbrilFatface-Regular.ttf", "ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf",
    "ofl/rozhaone/RozhaOne-Regular.ttf", "ofl/ultra/Ultra-Regular.ttf", "ofl/gloock/Gloock-Regular.ttf",
    "ofl/youngserif/YoungSerif-Regular.ttf", "ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "ofl/cinzel/Cinzel%5Bwght%5D.ttf", "ofl/bodonimoda/BodoniModa%5Bopsz,wght%5D.ttf",
    "ofl/rye/Rye-Regular.ttf", "ofl/pirataone/PirataOne-Regular.ttf", "ofl/unifrakturcook/UnifrakturCook-Bold.ttf",
    # script / brush
    "ofl/pacifico/Pacifico-Regular.ttf", "ofl/lobster/Lobster-Regular.ttf", "ofl/satisfy/Satisfy-Regular.ttf",
    "ofl/sacramento/Sacramento-Regular.ttf", "ofl/courgette/Courgette-Regular.ttf", "ofl/greatvibes/GreatVibes-Regular.ttf",
    "ofl/allura/Allura-Regular.ttf", "ofl/parisienne/Parisienne-Regular.ttf", "ofl/yellowtail/Yellowtail-Regular.ttf",
    "ofl/kaushanscript/KaushanScript-Regular.ttf", "ofl/marckscript/MarckScript-Regular.ttf",
    "ofl/alexbrush/AlexBrush-Regular.ttf", "ofl/arizonia/Arizonia-Regular.ttf", "ofl/norican/Norican-Regular.ttf",
    "ofl/dancingscript/DancingScript%5Bwght%5D.ttf", "ofl/caveatbrush/CaveatBrush-Regular.ttf",
    "ofl/permanentmarker/PermanentMarker-Regular.ttf", "ofl/mrdafoe/MrDafoe-Regular.ttf", "ofl/leaguescript/LeagueScript-Regular.ttf",
    "ofl/oleoscript/OleoScript-Bold.ttf", "ofl/cookie/Cookie-Regular.ttf", "ofl/rancho/Rancho-Regular.ttf",
    "ofl/damion/Damion-Regular.ttf", "ofl/molle/Molle-Regular.ttf", "ofl/playball/Playball-Regular.ttf",
    "ofl/sofia/Sofia-Regular.ttf", "ofl/tangerine/Tangerine-Bold.ttf", "ofl/petitformalscript/PetitFormalScript-Regular.ttf",
    # handwritten / casual
    "ofl/amaticsc/AmaticSC-Bold.ttf", "ofl/shadowsintolight/ShadowsIntoLight.ttf", "ofl/reeniebeanie/ReenieBeanie.ttf",
    "ofl/gochihand/GochiHand-Regular.ttf", "ofl/patrickhand/PatrickHand-Regular.ttf", "ofl/rocksalt/RockSalt-Regular.ttf",
    "ofl/gloriahallelujah/GloriaHallelujah.ttf", "ofl/caveat/Caveat%5Bwght%5D.ttf", "ofl/covered/CoveredByYourGrace.ttf",
    "ofl/kalam/Kalam-Bold.ttf", "ofl/schoolbell/Schoolbell-Regular.ttf", "ofl/specialelite/SpecialElite-Regular.ttf",
]


def main() -> int:
    DEST.mkdir(exist_ok=True)
    ok, bad = [], []
    for rel in FONTS:
        name = urllib.parse.unquote(rel.rsplit("/", 1)[1])
        out = DEST / name
        if out.exists() and out.stat().st_size > 5000:
            ok.append(name)
            continue
        try:
            data = urllib.request.urlopen(BASE + rel, timeout=60).read()
            if len(data) < 5000:
                raise ValueError("too small")
            out.write_bytes(data)
            ok.append(name)
        except Exception as e:  # noqa
            bad.append((name, str(e)[:60]))
    print(f"OK {len(ok)}  FAILED {len(bad)}")
    for b in bad:
        print("  failed:", b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
