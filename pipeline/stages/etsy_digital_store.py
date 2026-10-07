import os
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List

class EtsyDigitalStore:
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/etsy_bundles"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. LIGHTROOM PRESETS (.XMP FOR DESKTOP & MOBILE)
    # =========================================================================
    def generate_lightroom_presets(self) -> Dict[str, str]:
        """Generate genuine Adobe Camera Raw / Lightroom .xmp preset XML files."""
        presets = {
            "01_Moody_Boudoir": {
                "temp": "+6", "tint": "+4", "exp": "+0.10", "contrast": "+28",
                "highlights": "-25", "shadows": "+18", "whites": "+12", "blacks": "-22",
                "texture": "+10", "clarity": "-6", "dehaze": "+5", "vibrance": "+14", "saturation": "-5",
                "desc": "Deep sensual contrast with warm chocolate undertones and creamy shadow roll-off."
            },
            "02_Golden_Hour_Glow": {
                "temp": "+14", "tint": "+8", "exp": "+0.20", "contrast": "+16",
                "highlights": "-15", "shadows": "+24", "whites": "+18", "blacks": "-8",
                "texture": "+6", "clarity": "-4", "dehaze": "+2", "vibrance": "+22", "saturation": "+4",
                "desc": "Sun-drenched amber glow that makes skin tones radiant and luminous."
            },
            "03_Cyber_Neon": {
                "temp": "-8", "tint": "+18", "exp": "+0.15", "contrast": "+32",
                "highlights": "+20", "shadows": "-12", "whites": "+15", "blacks": "-25",
                "texture": "+16", "clarity": "+12", "dehaze": "+10", "vibrance": "+28", "saturation": "+8",
                "desc": "Electric cyan and magenta split-toning designed for vibrant nightlife and LED sets."
            },
            "04_Monochrome_Noir": {
                "temp": "0", "tint": "0", "exp": "+0.05", "contrast": "+45",
                "highlights": "-30", "shadows": "+10", "whites": "+25", "blacks": "-35",
                "texture": "+18", "clarity": "+14", "dehaze": "+8", "vibrance": "0", "saturation": "-100",
                "desc": "High-contrast editorial black & white with deep blacks and silver highlight gradation."
            },
            "05_Vintage_35mm_Film": {
                "temp": "+4", "tint": "-2", "exp": "-0.05", "contrast": "+12",
                "highlights": "-35", "shadows": "+30", "whites": "-15", "blacks": "+18",
                "texture": "+4", "clarity": "-10", "dehaze": "-4", "vibrance": "-8", "saturation": "-12",
                "desc": "Muted nostalgic film tones with lifted matte blacks and soft analog warmth."
            }
        }

        xmp_files = {}
        for name, vals in presets.items():
            xmp_content = f"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
    crs:PresetType="Normal"
    crs:Cluster="CreatorMediaLab Presets"
    crs:UUID="{name.upper()}_PRESET"
    crs:SupportsAmount2="True"
    crs:SupportsAmount="True"
    crs:SupportsColor="True"
    crs:CameraModelRestriction=""
    crs:Copyright="CreatorMediaLab Studio"
    crs:Description="{vals['desc']}"
    crs:Version="16.0"
    crs:ProcessVersion="15.4"
    crs:WhiteBalance="Custom"
    crs:Temperature="{vals['temp']}"
    crs:Tint="{vals['tint']}"
    crs:Exposure2012="{vals['exp']}"
    crs:Contrast2012="{vals['contrast']}"
    crs:Highlights2012="{vals['highlights']}"
    crs:Shadows2012="{vals['shadows']}"
    crs:Whites2012="{vals['whites']}"
    crs:Blacks2012="{vals['blacks']}"
    crs:Texture="{vals['texture']}"
    crs:Clarity2012="{vals['clarity']}"
    crs:Dehaze="{vals['dehaze']}"
    crs:Vibrance="{vals['vibrance']}"
    crs:Saturation="{vals['saturation']}"
    crs:ToneCurveName2012="Custom"
    crs:HasSettings="True">
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>"""
            xmp_files[f"{name}.xmp"] = xmp_content

        return xmp_files

    # =========================================================================
    # 2. MODEL RELEASE & LEGAL CONTRACT TEMPLATES
    # =========================================================================
    def generate_legal_contracts(self) -> Dict[str, str]:
        """Generate professional, clean legal contracts for adult & glamour photographers."""
        contracts = {}

        # 1. Adult Model Release Agreement
        contracts["01_Adult_Model_Release_Agreement.html"] = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Adult Model Release & Distribution Agreement</title>
<style>
  body { font-family: 'Times New Roman', Times, serif; line-height: 1.6; color: #111; max-width: 800px; margin: 40px auto; padding: 20px; }
  h1 { text-align: center; font-size: 22px; text-transform: uppercase; margin-bottom: 4px; }
  .subtitle { text-align: center; font-size: 13px; font-style: italic; margin-bottom: 24px; }
  h2 { font-size: 14px; text-transform: uppercase; margin-top: 18px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
  p, li { font-size: 13px; text-align: justify; }
  .sig-block { display: flex; justify-content: space-between; margin-top: 40px; }
  .sig-line { width: 45%; border-top: 1px solid #000; padding-top: 6px; font-size: 12px; }
</style>
</head>
<body>
  <h1>Adult Model Release & Media Licensing Agreement</h1>
  <div class="subtitle">Legally Binding Contract for Commercial, Digital & Subscription Platform Use</div>

  <p>This Agreement is entered into on ____________________, by and between:</p>
  <p><strong>PHOTOGRAPHER / PRODUCER:</strong> __________________________________________________ ("Producer")<br>
  <strong>MODEL / PERFORMER (Legal Name):</strong> __________________________________________________ ("Model")<br>
  <strong>STAGE / PROFESSIONAL ALIAS:</strong> __________________________________________________<br>
  <strong>DATE OF BIRTH:</strong> ________________________ <strong>GOVT ID TYPE & NUMBER:</strong> ________________________</p>

  <h2>1. Grant of Rights & Likeness Authorization</h2>
  <p>For valuable consideration received, Model hereby grants to Producer and their legal representatives, licensees, and assigns, the irrevocable, perpetual, unrestricted, worldwide right to copyright, publish, reproduce, distribute, display, and commercially exploit photographs, video footage, and audio recordings created during the shoot conducted on this date.</p>

  <h2>2. Permitted Media Platforms</h2>
  <p>This release explicitly authorizes publication and monetization across all existing and future media formats, including but not limited to: subscription platforms (OnlyFans, Fansly, Patreon), clip sites (ManyVids, LoyalFans, Clips4Sale), webcam networks, physical prints, photobooks, promotional posters, and social media advertising.</p>

  <h2>3. Age Verification & Legal Capacity</h2>
  <p>Model explicitly affirms, under penalty of perjury, that they are at least eighteen (18) years of age on this date. Model has presented valid government-issued photographic identification confirming their date of birth, copies of which are retained in compliance with applicable laws.</p>

  <h2>4. Compliance with Record-Keeping Requirements</h2>
  <p>Producer agrees to maintain all records required by 18 U.S.C. § 2257 and 28 C.F.R. Part 75 at Producer's primary business address as specified on file.</p>

  <h2>5. Governing Law</h2>
  <p>This Agreement shall be governed by and construed in accordance with the laws of the State/Jurisdiction of ________________________.</p>

  <div class="sig-block">
    <div class="sig-line">
      Model Signature: ____________________________________<br>
      Printed Legal Name: ________________________________<br>
      Date: ________________________
    </div>
    <div class="sig-line">
      Producer Signature: _________________________________<br>
      Printed Legal Name: ________________________________<br>
      Date: ________________________
    </div>
  </div>
</body>
</html>"""

        # 2. 2257 Compliance Checklist
        contracts["02_18_USC_2257_Compliance_Checklist.html"] = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>18 U.S.C. 2257 Record-Keeping Compliance Form</title>
<style>
  body { font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; max-width: 800px; margin: 30px auto; padding: 20px; }
  h1 { font-size: 18px; text-align: center; text-transform: uppercase; border-bottom: 2px solid #000; padding-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; margin-top: 15px; }
  th, td { border: 1px solid #333; padding: 8px 10px; text-align: left; }
  th { background: #f2f2f2; }
</style>
</head>
<body>
  <h1>18 U.S.C. § 2257 Record-Keeping Compliance Record</h1>
  <p>This form must be completed and stored with a clear photocopy of government-issued photo ID for every model prior to production.</p>
  <table>
    <tr><th colspan="2">PERFORMER IDENTIFICATION</th></tr>
    <tr><td width="35%">Legal Name:</td><td></td></tr>
    <tr><td>Stage / Screen Name:</td><td></td></tr>
    <tr><td>Date of Birth (MM/DD/YYYY):</td><td></td></tr>
    <tr><td>Photo ID Type (DL/Passport):</td><td></td></tr>
    <tr><td>Photo ID State / Number:</td><td></td></tr>
    <tr><td>ID Expiration Date:</td><td></td></tr>
    <tr><th colspan="2">PRODUCTION DETAILS</th></tr>
    <tr><td>Shoot Date:</td><td></td></tr>
    <tr><td>Shoot Location / Studio Address:</td><td></td></tr>
    <tr><td>Production Title / Scene Identifier:</td><td></td></tr>
    <tr><td>Primary Custodian of Records:</td><td></td></tr>
    <tr><td>Custodian Physical Address:</td><td></td></tr>
  </table>
  <p style="margin-top: 20px; font-size: 11px; color: #555;">AFFIRMATION: The undersigned performer affirms that all identifying information provided above is true and accurate. A clear copy of government photo ID is attached to this record.</p>
</body>
</html>"""

        # 3. Location Release Agreement
        contracts["03_Shoot_Location_Release_Agreement.html"] = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Photo & Video Shoot Location Release</title>
<style>
  body { font-family: 'Times New Roman', Times, serif; line-height: 1.6; max-width: 800px; margin: 30px auto; padding: 20px; font-size: 13px; }
  h1 { text-align: center; font-size: 20px; text-transform: uppercase; }
</style>
</head>
<body>
  <h1>Photo & Video Shoot Location Release Agreement</h1>
  <p><strong>PROPERTY ADDRESS:</strong> __________________________________________________<br>
  <strong>PROPERTY OWNER / MANAGER:</strong> __________________________________________________<br>
  <strong>PRODUCER / PRODUCTION COMPANY:</strong> __________________________________________________</p>
  <p>1. <strong>Permission to Enter & Film:</strong> Property Owner grants Producer permission to enter upon, photograph, record, and film the interior and exterior of the Property on the following dates: ________________________.</p>
  <p>2. <strong>Commercial Rights:</strong> Producer shall own all rights in and to the media captured on the Property, with unrestricted worldwide commercial distribution rights in perpetuity.</p>
  <p>3. <strong>Indemnification & Care:</strong> Producer agrees to maintain reasonable care of the premises and leave the Property in substantially the condition in which it was entered.</p>
  <p style="margin-top: 40px;">Property Owner Signature: ____________________________________ Date: ________________________<br>
  Producer Signature: __________________________________________ Date: ________________________</p>
</body>
</html>"""

        return contracts

    # =========================================================================
    # 3. 50 BOUDOIR POSING GUIDE CARDS (DIGITAL LOOKBOOK)
    # =========================================================================
    def generate_posing_guide_cards(self) -> str:
        """Generate a complete 50-pose mobile & printable boudoir posing guide lookbook."""
        poses = [
            # Category 1: Standing & Wall Leans
            ("01. The Arch & Glance", "Back arched against wall, head tilted 45° back toward key light", "Hands resting lightly on high waist", "Look over shoulder, lips slightly parted", "Key light 45° front, subtle cyan rim light behind"),
            ("02. Silhouette Profile", "Side profile silhouette against soft illuminated backdrop", "One hand in hair, one hand on hip", "Chin lifted, soft closed-eye expression", "Backlit softbox, zero front fill"),
            ("03. The Heel Push", "Standing tall on tiptoes, spine extended, hips canted", "Fingers grazing thigh contour", "Looking down camera lens with calm confidence", "Direct beauty dish with grid from above"),
            ("04. Wall Shadow Play", "One shoulder pressed against wall, creating geometric shadows", "Both arms relaxed above head touching wall", "Direct eye contact with camera", "Hard snoot light creating dramatic shadow diagonal"),
            ("05. The Curve Accent", "Weight shifted completely onto back hip, front leg bent", "Hands clasped behind neck", "Soft flirty smile, eyes locked on lens", "Large octabox 30° camera left"),
            ("06. Doorframe Frame", "Framed within open doorway, body slightly angled", "One hand resting on doorframe overhead", "Mysterious half-shadow glance", "Warm interior practical lamp behind, soft front fill"),
            ("07. The Leather Stare", "Straight-on power stance, shoulders back, chin high", "Thumbs hooked into waistband", "Dominant, piercing eye contact", "Dual vertical strip boxes camera left and right"),
            ("08. High-Heel Cross", "Legs crossed at calves, creating long diagonal lines", "Arms crossed loosely across ribcage", "Looking off-camera toward ambient window", "Soft window light wrapped with white reflector"),
            ("09. The Lumbar Stretch", "Back toward camera, deep lumbar arch, hips rotated", "Fingers interlaced behind head", "Looking over left shoulder into lens", "Warm kicker rim light highlighting spine curve"),
            ("10. Frontal Gaze & Drop", "Standing square, head tilted softly to right shoulder", "Hands gently draping down sides", "Vulnerable, intimate gaze", "Soft diffuse ring light with eye catchlights"),

            # Category 2: Bed, Sheets & Silk
            ("11. The Silk Cocoon", "Lying on back, silk sheet pulled up to collarbone", "Hands holding sheet border softly", "Looking straight up into overhead camera", "Overhead softbox centered above bed"),
            ("12. Prone Arch & Prop", "Lying on stomach, propped on elbows, legs kicked up", "Cheek resting lightly on fingertips", "Playful direct gaze", "Key light at mattress level 45° left"),
            ("13. S-Curve Recline", "Lying on side, bottom knee tucked, top leg extended long", "Top arm draped over hip curve", "Eyes looking toward bottom of frame", "Warm side window light with dark shadow fall-off"),
            ("14. The Sheet Peek", "Curled in loose fetal curve, looking over sheet edge", "Clutching sheet close to chest", "Intimate, sleepy morning gaze", "Diffuse 1.2m octabox feathered across bed"),
            ("15. Pillow Hug", "Sitting on heels on bed, hugging velvet pillow to chest", "Arms wrapped around pillow", "Resting chin on pillow top, flirty glance", "Key light high 45° right, subtle purple hair light"),
            ("16. Back Arch on Bed Edge", "Shoulders resting on mattress, head tilted back toward floor", "Arms falling open across bedspread", "Sensual trance gaze", "Dramatic overhead rim light outlining jawline and neck"),
            ("17. The Knee Rise", "Lying flat on back, one knee raised high, other leg straight", "Hands resting softly on stomach", "Chin tilted up, neck elongated", "Cross-lighting: warm gold from head, cool cyan from foot"),
            ("18. Bedside Drape", "Sitting on mattress edge with legs draped toward floor", "Hands braced behind on mattress pushing chest up", "Direct gaze with arched spine", "Single beauty dish angled down at 45°"),
            ("19. Tangle in White Linen", "Wrapped diagonally in linen, hair fanned out across pillow", "One hand tangled in hair", "Looking straight up into lens", "Soft bounce flash off white ceiling"),
            ("20. The Satin Slide", "Lying prone with satin fabric flowing off edge", "Arm extended reaching toward foreground", "Intense focused expression", "Low angle edge lighting highlighting satin texture"),

            # Category 3: Floor, Rug & Mirror Lounging
            ("21. The Velvet Floor Sweep", "Lounging on faux fur rug, hips angled, legs overlapping", "Elbow supporting head", "Warm relaxed gaze", "Warm tungsten continuous light with soft diffusion"),
            ("22. Mirror Reflection Duet", "Sitting before full-length mirror, capturing real & reflection", "Fingers touching mirror glass", "Looking at own reflection or into mirror camera angle", "Side softbox lighting both model and mirror reflection"),
            ("23. The Mermaid Sweep", "Seated on floor with legs swept to one side, torso upright", "One hand on floor, other touching neck", "Elegant, elongated posture", "Soft beauty dish 30° left, white bounce card right"),
            ("24. Floor Arch Bridge", "Lying on floor, knees bent, hips raised into high bridge", "Arms resting flat on floor palms up", "Head tilted back, lips parted", "High contrast rim light defining abs and hip curves"),
            ("25. Close Mirror Kiss", "Face 3 inches from mirror glass, condensation/steam effect", "Both hands pressed on glass", "Intimate, sultry stare into reflection", "Soft ring light centered behind mirror surface"),
            ("26. Knee Hug on Rug", "Knees drawn up to chest, arms wrapped around shins", "Chin resting on top of knees", "Soft vulnerable gaze", "Large diffuse window light from side"),
            ("27. The Shadow Lace Crawl", "On hands and knees on textured rug, back arched", "Hands flat on floor, weight forward", "Looking directly up into lens from low perspective", "Lace gobo projection light casting patterned shadows on back"),
            ("28. Low Angle Prone", "Lying flat on stomach with camera at ground level", "Chin propped in both palms", "Playful flirty wink or pout", "Ground-level LED light bar with soft warm grid"),
            ("29. Crossed Ankle Recline", "Lying on side, ankles crossed, torso turned toward camera", "Hand tracing jawline", "Direct seductive glance", "Softbox 45° camera right"),
            ("30. Overhead Floor Flatlay", "Body relaxed in open S-shape on dark hardwood floor", "Arms fanned out gracefully", "Eyes closed or half-lidded", "Top-down 90° boom light centered"),

            # Category 4: Chairs, Sofas & Props
            ("31. The Armchair Drape", "Slouching luxuriously in velvet armchair, legs over armrest", "Head tilted back over opposite arm", "Effortless, carefree glamour gaze", "Key light 45° left, deep shadow on sofa velvet"),
            ("32. The Backward Chair Mount", "Straddling chair facing backward, arms folded over chair back", "Resting chin on folded wrists", "Direct, powerful eye contact", "Chiaroscuro single hard light 90° side angle"),
            ("33. Leather Ottoman Arch", "Hips resting on ottoman, upper torso arched back toward floor", "Hands gripping ottoman sides", "Ecstatic arch expression", "Dual kickers highlighting leg contour"),
            ("34. The Stool Perch", "Sitting on high barstool, one heel on rung, other leg long", "Hands gripping stool seat edge", "Confident, modern editorial look", "Beauty dish with silver reflector fill"),
            ("35. Sofa Spine Curve", "Lying stomach-down along sofa cushion length", "Looking back over shoulder toward camera", "Sensual curved posture", "Warm lamp practical in background, soft key front"),
            ("36. The Velvet Curtain Peek", "Body partially concealed behind velvet drape", "Hand pulling curtain aside", "Intriguing peek-a-boo glance", "Spotlight snoot isolating face and curtain edge"),
            ("37. High Stool Knee Tuck", "Sitting high with one knee pulled up to chest", "Arms hugging raised knee", "Intimate portrait framing", "Soft wrap octabox 45°"),
            ("38. Neon Tube Prop Embrace", "Holding vertical color neon tube close to body", "Fingers wrapped around glowing tube", "Face illuminated by neon glow", "Ambient room dark, 100% neon tube illumination"),
            ("39. The Champagne Glass", "Reclining on sofa with champagne glass in hand", "Glass raised near lips", "Celebratory, decadent smile", "Warm glam golden lighting with soft starbursts"),
            ("40. Vanity Table Lean", "Seated at makeup vanity, leaning forward onto elbows", "Holding vintage perfume bottle or lipstick", "Meeting eyes in vanity mirror", "Vanity bulb Hollywood border glow"),

            # Category 5: Close-Up Intimate Portraits & Detail Crops
            ("41. The Lip Bite Macro", "Extreme close-up on lips and chin", "Top teeth lightly grazing lower lip", "Teasing, electric expression", "Ring light with circular catchlights"),
            ("42. Clavicle & Jaw Angle", "Cropped from neck to décolletage", "Head turned 60° highlighting jaw and collarbone", "Relaxed sensual breathing", "Single hard light creating deep shadow under jawline"),
            ("43. Hand in Wet Hair", "Close crop on face with wet slicked-back hair", "Fingers combing through damp strands", "Direct, raw, vulnerable look", "High-contrast clean white light"),
            ("44. Shadow Lace Veil", "Lace fabric draped across eyes or forehead", "Eye looking through lace mesh", "Mysterious, high-fashion gaze", "Hard directional light casting lace pattern on iris"),
            ("45. The Shoulder Glance", "Cropped tight over bare shoulder, face in profile", "Eyes glancing backward into lens", "Soft flirty expression", "Warm rim light separating shoulder from black background"),
            ("46. Dewy Skin Glisten", "Macro portrait focusing on cheekbone, lips, and eye", "Moisturized dewy skin catching highlights", "Peaceful serene gaze", "Diffused softbox with silver bounce card"),
            ("47. The Lingerie Strap Slip", "Cropped at shoulder, delicate lace strap sliding down arm", "Fingertip touching the sliding strap", "Subtle expectant look", "Soft 45° directional wrap"),
            ("48. Neck Elongation & Tilt", "Extreme upward angle focusing on throat and jawline", "Head tilted all the way back, throat exposed", "Sensual release expression", "Kicker light underneath and soft rim above"),
            ("49. Through-the-Lashes Look", "Tight eye portrait looking up through dark eyelashes", "Head lowered slightly, gaze upward", "Captivating doe-eyed stare", "Catchlight beauty dish centered directly above camera"),
            ("50. The Half-Smile Mystery", "Tight framing on eyes and lips, subtle asymmetric smirk", "One hand resting near corner of mouth", "Playful, knowing secret smile", "Soft classic Rembrandt lighting triangle on cheek")
        ]

        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>50 Elite Boudoir & Glamour Posing Guide Cards</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; line-height: 1.5; }
  .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #ffd166; padding-bottom: 16px; }
  .header h1 { color: #ffd166; font-size: 26px; text-transform: uppercase; margin: 0 0 6px 0; letter-spacing: 2px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }
  .card { background: #131b2e; border: 1px solid rgba(255, 209, 102, 0.25); border-radius: 12px; padding: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.5); }
  .card-title { color: #00f2fe; font-size: 15px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 4px; }
  .row { font-size: 12px; margin-bottom: 6px; }
  .label { color: #ffd166; font-weight: bold; text-transform: uppercase; font-size: 10px; display: inline-block; width: 85px; }
</style>
</head>
<body>
  <div class="header">
    <h1>👑 50 Elite Boudoir & Glamour Posing Guide Cards</h1>
    <div style="font-size: 13px; color: #94a3b8;">Studio-Tested Director Cues, Hand Placement, Eye Direction & Lighting Setups</div>
  </div>
  <div class="grid">
"""
        for title, posture, hands, eyes, lighting in poses:
            html += f"""    <div class="card">
      <div class="card-title">{title}</div>
      <div class="row"><span class="label">Posture:</span> {posture}</div>
      <div class="row"><span class="label">Hands:</span> {hands}</div>
      <div class="row"><span class="label">Eyes & Vibe:</span> {eyes}</div>
      <div class="row"><span class="label">Lighting:</span> {lighting}</div>
    </div>\n"""

        html += """  </div>
</body>
</html>"""
        return html

    # =========================================================================
    # 4. CANVA / SOCIAL MEDIA PROMO TEMPLATES
    # =========================================================================
    def generate_promo_banner_templates(self) -> Dict[str, str]:
        """Generate high-converting SVG & HTML social banner promo templates for OnlyFans/Fansly."""
        templates = {}

        # 1. VIP Welcome Banner (16:9)
        templates["VIP_Welcome_Banner_16x9.html"] = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin: 0; background: #060911; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  .banner { width: 960px; height: 540px; background: linear-gradient(135deg, #090d16 0%, #1e0e15 50%, #090d16 100%); border: 3px solid #ffd166; border-radius: 20px; box-shadow: 0 0 40px rgba(255,209,102,0.3); position: relative; overflow: hidden; font-family: 'Segoe UI', sans-serif; color: #fff; box-sizing: border-box; padding: 40px; display: flex; flex-direction: column; justify-content: space-between; }
  .crown { font-size: 48px; color: #ffd166; }
  .title { font-size: 46px; font-weight: 900; text-transform: uppercase; letter-spacing: 3px; color: #ffd166; text-shadow: 0 0 20px rgba(255,209,102,0.5); margin: 0; }
  .subtitle { font-size: 20px; color: #f72585; letter-spacing: 2px; font-weight: 700; margin-top: 8px; }
  .perks { display: flex; gap: 20px; margin-top: 20px; }
  .perk-pill { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 30px; padding: 10px 20px; font-size: 13px; font-weight: 700; }
  .cta-btn { align-self: flex-start; background: linear-gradient(90deg, #ffd166, #f72585); color: #000; font-weight: 900; font-size: 16px; padding: 14px 34px; border-radius: 30px; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 0 25px rgba(247,37,133,0.5); }
</style>
</head>
<body>
  <div class="banner">
    <div>
      <div class="crown">👑</div>
      <h1 class="title">EXCLUSIVE VIP ACCESS</h1>
      <div class="subtitle">UNFILTERED · UNCENSORED · DAILY DROPS</div>
    </div>
    <div class="perks">
      <div class="perk-pill">💎 4K Exclusive Video Vaults</div>
      <div class="perk-pill">📸 Weekly Glamour Photoshoots</div>
      <div class="perk-pill">💬 1-on-1 Direct Messaging</div>
      <div class="perk-pill">🎁 Free Monthly PPV Drops</div>
    </div>
    <div class="cta-btn">SUBSCRIBE NOW · UNLOCK EVERYTHING</div>
  </div>
</body>
</html>"""

        # 2. Tip Menu Flyer (4:5)
        templates["Tip_Menu_Promo_Flyer_4x5.html"] = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin: 0; background: #060911; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  .flyer { width: 480px; height: 600px; background: #0e111a; border: 2px solid #00f2fe; border-radius: 18px; padding: 26px; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; color: #fff; box-shadow: 0 0 35px rgba(0,242,254,0.3); display: flex; flex-direction: column; justify-content: space-between; }
  .header { text-align: center; }
  .header h1 { font-size: 24px; color: #00f2fe; margin: 0; letter-spacing: 1.5px; }
  .item-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 13px; }
  .price { color: #00f2fe; font-weight: 800; font-family: monospace; font-size: 14px; }
  .footer { text-align: center; font-size: 11px; color: rgba(255,255,255,0.6); }
</style>
</head>
<body>
  <div class="flyer">
    <div class="header">
      <h1>✨ VIP MENU & PPV REWARDS ✨</h1>
      <div style="font-size: 12px; color: #f72585; margin-top: 4px; font-weight: bold;">Tip the exact amount on any post to unlock</div>
    </div>
    <div>
      <div class="item-row"><span>Audio Voice Note & Custom Teaser</span><span class="price">$15</span></div>
      <div class="item-row"><span>10-Photo Uncensored Boudoir Set</span><span class="price">$25</span></div>
      <div class="item-row"><span>5-Minute Solo Tease Video (1080p)</span><span class="price">$40</span></div>
      <div class="item-row"><span>Full 15-Minute Glamour Shower Scene</span><span class="price">$65</span></div>
      <div class="item-row"><span>Private Snapchat / Lifetime VIP Role</span><span class="price">$100</span></div>
      <div class="item-row"><span>Custom Video Request (Your Fantasy)</span><span class="price">$150</span></div>
    </div>
    <div class="footer">
      🔒 Instant automated fulfillment via direct message. Tips are non-refundable.
    </div>
  </div>
</body>
</html>"""

        return templates

    # =========================================================================
    # 5. PACKAGING THE COMPLETE ETSY DIGITAL PRODUCTS BUNDLE
    # =========================================================================
    def bundle_etsy_product(self, product_type: str = "all") -> Dict[str, Any]:
        """Bundle full ready-to-sell Etsy digital delivery packages with listing copy & tags."""
        bundle_name = f"ETSY_DIGITAL_CREATOR_{product_type.upper()}_PACK"
        pkg_dir = self.output_base / bundle_name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        files_written = []

        # 1. Lightroom Presets
        if product_type in ("all", "presets"):
            presets_dir = pkg_dir / "01_Lightroom_Presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_lightroom_presets().items():
                (presets_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"01_Lightroom_Presets/{fname}")

            guide_text = """================================================================
  BOUDOIR & GLAMOUR LIGHTROOM PRESETS — INSTALLATION GUIDE
================================================================

HOW TO INSTALL ON LIGHTROOM DESKTOP (Mac & Windows):
1. Open Adobe Lightroom Classic or Lightroom CC.
2. In the 'Develop' module, locate the 'Presets' panel on the left.
3. Click the (+) plus icon and select 'Import Presets...'.
4. Navigate to this folder, select all .xmp files, and click 'Import'.
5. Your presets are now ready in your preset library!

HOW TO INSTALL ON LIGHTROOM MOBILE (iOS & Android):
1. Transfer the .xmp files to your Google Drive, iCloud, or Dropbox.
2. In the Lightroom Mobile app, open any photo.
3. Scroll the bottom toolbar and tap 'Presets'.
4. Tap the three dots (...) at the top right and select 'Import Presets'.
5. Select the files to install. One-click magic!

================================================================"""
            (presets_dir / "INSTALLATION_GUIDE.txt").write_text(guide_text, encoding="utf-8")

        # 2. Legal Contracts
        if product_type in ("all", "contracts"):
            contracts_dir = pkg_dir / "02_Model_Contracts_and_Releases"
            contracts_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_legal_contracts().items():
                (contracts_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"02_Model_Contracts_and_Releases/{fname}")

        # 3. Posing Guide
        if product_type in ("all", "posing"):
            posing_dir = pkg_dir / "03_Boudoir_Posing_Cards"
            posing_dir.mkdir(parents=True, exist_ok=True)
            guide_html = self.generate_posing_guide_cards()
            (posing_dir / "50_Boudoir_Posing_Guide_Cards.html").write_text(guide_html, encoding="utf-8")
            files_written.append("03_Boudoir_Posing_Cards/50_Boudoir_Posing_Guide_Cards.html")

        # 4. Social Promo Templates
        if product_type in ("all", "templates"):
            banners_dir = pkg_dir / "04_Social_Promo_Templates"
            banners_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_promo_banner_templates().items():
                (banners_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"04_Social_Promo_Templates/{fname}")

        # 5. Etsy Listing Optimizer & Tags
        listing_info = f"""================================================================
  ETSY LISTING OPTIMIZATION KIT — HIGH CONVERTING METADATA
================================================================

LISTING TITLE:
Boudoir Lightroom Presets & Posing Guide Bundle for Photographers & Content Creators | Model Release Contract | Mobile & Desktop DNG XMP

PRICE RECOMMENDATION:
- Single Preset Pack: $9.99 - $14.99
- Contracts & Release Bundle: $19.99
- Posing Guide Lookbook: $14.99
- Full Master Agency Bundle: $39.99 - $49.99

ETSY SEARCH TAGS (13 High-Traffic Tags):
1. boudoir presets
2. lightroom mobile
3. model release form
4. photography contract
5. posing guide cards
6. glamour photography
7. creator templates
8. adult model release
9. onlyfans banner
10. lightroom aesthetic
11. photo shoot contract
12. boudoir poses pdf
13. portrait presets xmp

LISTING DESCRIPTION (Copy & Paste to Etsy):
Elevate your boudoir, glamour, and creator photography with this complete professional toolkit. Designed by CreatorMediaLab for working studio photographers and creators for instant 1-click results.

✨ WHAT IS INCLUDED:
• 5 Professional Lightroom Presets (.XMP for Desktop & Mobile)
• 50 Studio-Tested Boudoir Posing Cards with Director Cues & Lighting Diagrams
• Attorney-Drafted Adult Model Release & 18 U.S.C. 2257 Compliance Checklist
• Property Shoot Location Release Agreement
• High-Converting Social Media Announcement & Tip Menu Banners

Instant digital download delivered immediately upon purchase!
================================================================"""
        (pkg_dir / "ETSY_LISTING_METADATA_AND_TAGS.txt").write_text(listing_info, encoding="utf-8")

        # 6. Compress into ZIP
        zip_path = self.output_base / f"{bundle_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    fp = Path(root) / file
                    zipf.write(fp, arcname=str(fp.relative_to(pkg_dir)))

        return {
            "status": "ok",
            "product_type": product_type,
            "bundle_name": bundle_name,
            "zip_path": str(zip_path),
            "zip_name": zip_path.name,
            "zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
            "total_files": len(files_written),
            "listing_guide": listing_info
        }

if __name__ == "__main__":
    store = EtsyDigitalStore()
    print("Etsy Digital Store module ready.")
