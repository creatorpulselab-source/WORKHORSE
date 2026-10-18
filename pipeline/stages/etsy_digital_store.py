import os
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List
import numpy as np


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
    # 2. LEGAL CONTRACTS & MODEL RELEASE TEMPLATES
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
    # 5. CINEMATIC 3D LUT VIDEO PACK (.CUBE FOR PREMIERE / DAVINCI / CAPCUT)
    # =========================================================================
    def generate_3d_luts(self, size: int = 33) -> Dict[str, str]:
        """Generate genuine Adobe/DaVinci 3D .cube LUT matrices for video creators."""
        vals = np.linspace(0.0, 1.0, size, dtype=np.float32)
        # Order: Blue slowest (axis 0), Green middle (axis 1), Red fastest (axis 2)
        b, g, r = np.meshgrid(vals, vals, vals, indexing='ij')
        base_rgb = np.stack([r, g, b], axis=-1)  # shape (size, size, size, 3)

        def build_cube_file(title: str, rgb_transformed: np.ndarray) -> str:
            header = [
                "# Created by CreatorMediaLab Studio",
                f'TITLE "{title}"',
                f"LUT_3D_SIZE {size}",
                "DOMAIN_MIN 0.0 0.0 0.0",
                "DOMAIN_MAX 1.0 1.0 1.0",
                ""
            ]
            clamped = np.clip(rgb_transformed, 0.0, 1.0).reshape(-1, 3)
            lines = header + [f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}" for row in clamped]
            return "\n".join(lines)

        luts = {}

        # 01. Kodak Portra 400 (Warm golden film tones, smooth highlight rolloff, skin priority)
        p1 = base_rgb.copy()
        p1[..., 0] = np.power(p1[..., 0], 0.92) * 1.04  # Red boost
        p1[..., 1] = np.power(p1[..., 1], 0.96) * 1.01  # Green slight lift
        p1[..., 2] = np.power(p1[..., 2], 1.04) * 0.95  # Blue attenuation
        luts["01_CreatorMediaLab_Kodak_Portra_400.cube"] = build_cube_file("CreatorMediaLab Kodak Portra 400", p1)

        # 02. Cinestill 800T (Tungsten night cinema, cool blue-green shadows, subtle halation)
        p2 = base_rgb.copy()
        p2[..., 0] = np.where(p2[..., 0] > 0.75, p2[..., 0] * 1.06, p2[..., 0] * 0.98)
        p2[..., 1] = p2[..., 1] * 0.99
        p2[..., 2] = np.power(p2[..., 2], 0.93) * 1.05  # Teal/blue shadows
        luts["02_CreatorMediaLab_Cinestill_800T.cube"] = build_cube_file("CreatorMediaLab Cinestill 800T", p2)

        # 03. Moody Teal & Orange (Hollywood blockbuster complementary grade)
        p3 = base_rgb.copy()
        luma = 0.2126 * p3[..., 0] + 0.7152 * p3[..., 1] + 0.0722 * p3[..., 2]
        shadow_weight = np.clip(1.0 - (luma / 0.5), 0.0, 1.0)[..., np.newaxis]
        hi_weight = np.clip((luma - 0.5) / 0.5, 0.0, 1.0)[..., np.newaxis]
        p3[..., 1] += shadow_weight[..., 0] * 0.03
        p3[..., 2] += shadow_weight[..., 0] * 0.08
        p3[..., 0] += hi_weight[..., 0] * 0.07
        p3[..., 1] += hi_weight[..., 0] * 0.02
        p3[..., 2] -= hi_weight[..., 0] * 0.05
        luts["03_CreatorMediaLab_Moody_Teal_and_Orange.cube"] = build_cube_file("CreatorMediaLab Teal & Orange", p3)

        # 04. Fuji Provia 100F (Clean editorial clarity, vivid saturated greens and blues, true whites)
        p4 = base_rgb.copy()
        p4 = np.power(p4, 0.96) * 1.02
        p4[..., 1] = np.power(p4[..., 1], 0.94) * 1.03
        luts["04_CreatorMediaLab_Fuji_Provia_100F.cube"] = build_cube_file("CreatorMediaLab Fuji Provia 100F", p4)

        # 05. Golden Hour Warmth (Sun-drenched amber glow, soft highlight shoulder)
        p5 = base_rgb.copy()
        p5[..., 0] = np.power(p5[..., 0], 0.90) * 1.08
        p5[..., 1] = np.power(p5[..., 1], 0.95) * 1.03
        p5[..., 2] = np.power(p5[..., 2], 1.08) * 0.90
        luts["05_CreatorMediaLab_Golden_Hour_Warmth.cube"] = build_cube_file("CreatorMediaLab Golden Hour", p5)

        # 06. Noir Silver Monochrome (High contrast silver gelatin B&W)
        p6 = base_rgb.copy()
        mono = 0.299 * p6[..., 0] + 0.587 * p6[..., 1] + 0.114 * p6[..., 2]
        mono = np.where(mono < 0.5, np.power(mono / 0.5, 1.25) * 0.5, 1.0 - np.power((1.0 - mono) / 0.5, 1.25) * 0.5)
        p6[..., 0] = mono
        p6[..., 1] = mono
        p6[..., 2] = mono
        luts["06_CreatorMediaLab_Noir_Silver_Monochrome.cube"] = build_cube_file("CreatorMediaLab Noir Silver", p6)

        # 07. Cyber Neon Nightlife (Electric cyan & magenta split for LED / nightlife sets)
        p7 = base_rgb.copy()
        p7[..., 0] = np.power(p7[..., 0], 0.92) * 1.06  # Magenta red
        p7[..., 1] = np.power(p7[..., 1], 1.05) * 0.94
        p7[..., 2] = np.power(p7[..., 2], 0.90) * 1.10  # Cyan blue
        luts["07_CreatorMediaLab_Cyber_Neon_Nightlife.cube"] = build_cube_file("CreatorMediaLab Cyber Neon", p7)

        return luts

    # =========================================================================
    # 6. FLUX.1 & MIDJOURNEY PHOTOREALISTIC PROMPT ENGINEERING BIBLE
    # =========================================================================
    def generate_prompt_bible(self) -> Dict[str, str]:
        """Generate a complete 150+ categorized Prompt Engineering Bible with interactive HTML lookbook and quick-reference text."""
        categories = [
            ("Studio & Editorial Fashion", [
                "Photorealistic studio portrait of an elegant woman wearing a tailored oversized camel wool coat, photographed with an 85mm f/1.4 lens, Rembrandt key lighting casting subtle triangle on shadowed cheek, soft diffused fill, Kodak Portra 400 color science, natural unretouched skin pores and fine fabric textures.",
                "High-fashion editorial model in structured velvet blazer, 50mm normal prime, dramatic chiaroscuro lighting, deep shadow contrast, Arri Alexa 35 color gradation, poised authoritative gaze, crisp specular highlights on collarbone.",
                "Minimalist studio lookbook portrait, subject in silk slip dress, soft beauty dish directly above lens, clean circular catchlights in iris, pure white backdrop, true neutral skin tones, sharp focus on eyelashes.",
                "Avant-garde runway fashion model in dramatic pleated metallic gown, 35mm wide prime, low-angle perspective, direct on-camera editorial flash, crisp contact shadows, punchy saturated colors, glossy skin sheen.",
                "Intimate monochrome studio close-up, 105mm macro lens, silver gelatin black and white, Ilford HP5 contrast, deep velvety blacks, tack-sharp iris detail, fine facial hair and skin pore texture."
            ]),
            ("Cinematic 35mm & Widescreen Street", [
                "Cinematic medium shot of a contemplative creative professional walking through a rain-slicked Tokyo alley at dusk, 35mm anamorphic prime lens with 2.39:1 widescreen framing, neon reflections in puddles, Cinestill 800T subtle red halation around lanterns, moody teal shadows.",
                "Golden hour street portrait in Paris, subject leaning against ornate stone balustrade, 50mm f/1.8 lens, warm 3200K side sunlight, luminous rim lighting outlining hair strands, soft dust motes in air, natural film grain.",
                "Nighttime urban portrait inside a dimly lit vintage coffee bar, warm tungsten pendant lamp casting soft amber pool of light, Fujifilm Provia 100F clarity, condensation on window pane in background, candid natural expression.",
                "Atmospheric low-angle tracking shot of a dancer in motion on a rooftop at blue hour, cool 7000K ambient dusk lighting, distant city skyscrapers glowing, 24mm wide angle, dynamic fabric sway, shutter motion blur on fingertips.",
                "Chiaroscuro night portrait, subject illuminated solely by a classic movie theater marquee sign, red and warm amber light spill, deep shadow falloff, raw cinematic presence, Kodachrome vintage aesthetic."
            ]),
            ("Commercial Products & Luxury Staging", [
                "Commercial hero product photograph of a luxury matte black perfume bottle with gold embossed typography, resting on dark wet slate, 105mm f/2.8 macro lens, dual cross-polarized strip softboxes, razor-sharp edge highlights, delicate water droplets.",
                "High-end skincare serum dropper bottle surrounded by botanical green leaves and smooth marble, diffused North-facing window lighting, soft pastel shadows, clean Scandinavian aesthetic, crystalline reflection.",
                "Artisan ceramic coffee mug steaming on an untreated white oak table, warm morning sunbeams piercing through venetian blinds, volumetric god rays, fine steam particles visible, cozy tactile mood.",
                "Designer chronograph wristwatch floating in zero-gravity space, matte carbon fiber bezel, crisp specular studio lights, 1:1 macro magnification revealing dial guilloche pattern, luxury watch catalog photography.",
                "Minimalist glass cosmetic jar on textured architectural concrete pedestal, sharp directional sunlight creating geometric shadow shapes, vibrant clean modern composition, high dynamic range."
            ]),
            ("Analog Film & Vintage Nostalgia", [
                "Vintage 1970s Polaroid snapshot of two creative friends at an outdoor summer music festival, authentic faded dyes, chemical edge burn, warm nostalgic yellow cast, authentic analog imperfection.",
                "1990s disposable camera aesthetic, direct harsh flash, subject laughing candidly at a retro diner booth, vinyl red seats, milkshake glasses, authentic grain, unposed intimate authenticity.",
                "Medium format 6x7 Hasselblad portrait, square 1:1 framing, subject sitting in sunlit conservatory surrounded by monstera plants, creamy depth of field, Kodak Ektar 100 rich saturated tones.",
                "Moody black and white candid photo on Ilford Delta 3200, heavy organic grain, smoky jazz club atmosphere, saxophonist in spotlight, high contrast gritty realism, timeless vintage print.",
                "1960s Kodachrome slide photograph of a classic convertible parked along California Highway 1 at sunset, vivid oceanic blues, warm golden sandstone, rich authentic color saturation."
            ]),
            ("Architectural Spaces & Creative Lofts", [
                "Wide architectural photograph of a double-height industrial artist loft with exposed brick walls, polished concrete floors, and floor-to-ceiling steel-framed factory windows, 24mm tilt-shift lens, soft overcast daylight.",
                "Minimalist modern interior design shoot, Japanese wabi-sabi living room with low linen sofa, bonsai tree, and raw timber beams, diffused indirect sunlight, serene peaceful atmosphere.",
                "Creative director workspace with dual 4K monitors, mechanical keyboard, and broadcast microphone rig on a walnut desk, warm ambient LED bias lighting, evening mood, clean tech aesthetic.",
                "Contemporary art gallery interior with white walls, skylight flooding room with clean neutral illumination, modern bronze sculpture casting long geometric shadows on hardwood floor.",
                "Luxury penthouse terrace overlooking modern skyline at twilight, sleek outdoor fireplace glowing with warm flames, glass railings, deep indigo evening sky, architectural elegance."
            ])
        ]

        # 1. Responsive Interactive HTML Lookbook
        html_cards = ""
        txt_content = """================================================================
  CREATORMEDIALAB — FLUX.1 & MIDJOURNEY PROMPT BIBLE (150+ PROMPTS)
================================================================

TABLE OF CONTENTS:
1. Model Architecture Prompting Rules (FLUX vs. SDXL vs. Midjourney)
2. Professional Lens & Optics Cheat Sheet
3. Studio Lighting Formulas & Setup Diagrams
4. Categorized Master Prompt Library (Copy & Paste Ready)
5. Artifact-Suppression Negative Prompt Arsenal

================================================================
SECTION 1: MODEL ARCHITECTURE PROMPTING RULES
================================================================
• FLUX.1 / FLUX.2 Klein:
  - Use DENSE, DESCRIPTIVE NATURAL LANGUAGE PROSE.
  - Detail optics, lighting physics, fabric texture, and spatial coordinates.
  - Place exact text inside quotation marks (e.g. "STUDIO").
  - ZERO NEGATIVE PROMPT: Negative prompts are inert in FLUX.
  - Avoid comma buzzwords ('8k uhd, masterpiece, RAW photo').

• SDXL / SD 1.5:
  - Use HYBRID PROSE + WEIGHTED TOKENS: '(photorealistic:1.15), (detailed skin:1.2)'.
  - MANDATORY NEGATIVE PROMPT to suppress anatomical defects, blur, and extra limbs.

• Midjourney v6:
  - Focus on subject, setting, aesthetic style, and lighting.
  - Use parameters: '--ar 16:9', '--ar 4:5', '--v 6.0', '--style raw'.

================================================================
SECTION 2: LENS & OPTICS CHEAT SHEET
================================================================
• 24mm Ultra-Wide: Dynamic low-angle perspective, leading lines, expansive backgrounds.
• 35mm Environmental: Storytelling perspective, balanced subject-environment relation.
• 50mm Normal Prime: True-to-life human eye proportion, zero optical distortion.
• 85mm f/1.4 Portrait: Flattering compression, creamy circular bokeh, razor-sharp iris.
• 105mm Macro: Extreme subject isolation, micro-textural fidelity (pores, fabric weave).
• 2.39:1 Anamorphic: Cinematic widescreen, horizontal flare streaks, elliptical bokeh.

================================================================
SECTION 3: LIGHTING SETUP FORMULAS
================================================================
• Rembrandt: 45° directional key light creating signature triangle on shadowed cheek.
• Chiaroscuro: Caravaggio-inspired steep contrast, velvety deep shadows, dramatic key.
• Golden Hour: 3200K low-angle amber sun streaming from side, luminous rim light.
• Diffused North Light: Broad softbox mimicking large window, ultra-smooth shadow roll.
• Editorial Flash: On-camera direct flash, crisp defined contact shadows, punchy colors.
• Cyberpunk Neon: Dual cyan/magenta rim lighting reflecting off glossy specular surfaces.

================================================================
SECTION 4: MASTER PROMPTS LIBRARY
================================================================
"""
        card_id = 1
        for cat_name, cat_prompts in categories:
            txt_content += f"\n--- {cat_name.upper()} ---\n"
            for p in cat_prompts:
                txt_content += f"\n[Prompt #{card_id:03d}]:\n{p}\n"
                html_cards += f"""    <div class="prompt-card" data-category="{cat_name}">
      <div class="card-badge">{cat_name} • #{card_id:03d}</div>
      <p class="prompt-text" id="p_{card_id}">{p}</p>
      <button class="copy-btn" onclick="copyPrompt('p_{card_id}', this)">📋 Copy Prompt</button>
    </div>\n"""
                card_id += 1

        html_lookbook = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CreatorMediaLab • FLUX.1 & Midjourney Photorealistic Prompt Bible</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-dark: #070b14;
    --card-bg: #0d1527;
    --border: rgba(255,255,255,0.08);
    --gold: #ffd166;
    --cyan: #00f2fe;
    --text-white: #f8fafc;
    --text-muted: #94a3b8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg-dark); color: var(--text-white); padding: 32px 20px; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  .header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid var(--border); padding-bottom: 24px; }}
  .header h1 {{ font-family: 'Outfit', sans-serif; font-size: 32px; font-weight: 900; letter-spacing: 1px; color: var(--gold); text-transform: uppercase; margin-bottom: 8px; }}
  .header p {{ color: var(--text-muted); font-size: 15px; }}
  
  .cheat-sheet-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 40px; }}
  .cs-box {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .cs-title {{ font-family: 'Outfit', sans-serif; font-size: 16px; color: var(--cyan); text-transform: uppercase; margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  .cs-item {{ font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }}
  .cs-item strong {{ color: var(--text-white); }}

  .search-bar {{ width: 100%; max-width: 500px; margin: 0 auto 30px auto; display: block; padding: 14px 20px; background: var(--card-bg); border: 1px solid rgba(255,255,255,0.15); border-radius: 30px; color: #fff; font-size: 14px; outline: none; }}
  .search-bar:focus {{ border-color: var(--cyan); box-shadow: 0 0 15px rgba(0,242,254,0.3); }}

  .prompt-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
  .prompt-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, border-color 0.2s; }}
  .prompt-card:hover {{ transform: translateY(-3px); border-color: rgba(255,209,102,0.4); }}
  .card-badge {{ font-size: 11px; font-weight: 700; color: var(--gold); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
  .prompt-text {{ font-size: 13px; color: #cbd5e1; margin-bottom: 16px; line-height: 1.5; }}
  .copy-btn {{ align-self: flex-start; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); color: var(--cyan); padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; }}
  .copy-btn:hover {{ background: var(--cyan); color: #000; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⚡ Photorealistic AI Prompt Bible</h1>
    <p>CreatorMediaLab Studio-Tested FLUX.1 & Midjourney v6 Prompt Engineering Vault</p>
  </div>

  <div class="cheat-sheet-grid">
    <div class="cs-box">
      <div class="cs-title">📷 Lens & Optics Formulas</div>
      <div class="cs-item"><strong>85mm f/1.4:</strong> Creamy bokeh, flattering facial compression.</div>
      <div class="cs-item"><strong>50mm Prime:</strong> True-to-life geometry, zero distortion.</div>
      <div class="cs-item"><strong>35mm Wide:</strong> Environmental context and street realism.</div>
      <div class="cs-item"><strong>105mm Macro:</strong> Extreme textural fidelity and pore clarity.</div>
    </div>
    <div class="cs-box">
      <div class="cs-title">💡 Lighting Setups</div>
      <div class="cs-item"><strong>Rembrandt:</strong> 45° key light with cheek shadow triangle.</div>
      <div class="cs-item"><strong>Chiaroscuro:</strong> Caravaggio high-contrast deep shadows.</div>
      <div class="cs-item"><strong>Golden Hour:</strong> Warm 3200K side rim, luminous highlights.</div>
      <div class="cs-item"><strong>Diffused North:</strong> Painterly Vermeer soft gradations.</div>
    </div>
    <div class="cs-box">
      <div class="cs-title">🎨 Film Color Profiles</div>
      <div class="cs-item"><strong>Portra 400:</strong> Warm golden skin tones, soft highlights.</div>
      <div class="cs-item"><strong>Cinestill 800T:</strong> Tungsten glow with red specular halation.</div>
      <div class="cs-item"><strong>Provia 100F:</strong> Vivid saturated hues, clean whites.</div>
      <div class="cs-item"><strong>Ilford HP5:</strong> Silver gelatin contrast, rich velvety blacks.</div>
    </div>
  </div>

  <input type="text" id="searchInput" class="search-bar" placeholder="🔍 Search prompts by style, lens, lighting, or keyword..." onkeyup="filterPrompts()">

  <div class="prompt-grid" id="promptGrid">
{html_cards}  </div>
</div>

<script>
function copyPrompt(elementId, btn) {{
  var text = document.getElementById(elementId).innerText;
  navigator.clipboard.writeText(text).then(function() {{
    var orig = btn.innerText;
    btn.innerText = "✅ Copied!";
    btn.style.background = "#ffd166";
    btn.style.color = "#000";
    setTimeout(function() {{
      btn.innerText = orig;
      btn.style.background = "";
      btn.style.color = "";
    }}, 1500);
  }});
}}

function filterPrompts() {{
  var input = document.getElementById('searchInput').value.toLowerCase();
  var cards = document.getElementsByClassName('prompt-card');
  for (var i = 0; i < cards.length; i++) {{
    var text = cards[i].innerText.toLowerCase();
    cards[i].style.display = text.indexOf(input) > -1 ? "" : "none";
  }}
}}
</script>
</body>
</html>"""

        return {
            "FLUX_and_Midjourney_Prompt_Bible.html": html_lookbook,
            "PROMPT_BIBLE_QUICK_REFERENCE.txt": txt_content
        }

    # =========================================================================
    # 7. PACKAGING DIGITAL PRODUCT BUNDLES (ZIP DELIVERY BUILDER)
    # =========================================================================
    KNOWN_PRODUCT_TYPES = ("all", "presets", "contracts", "posing", "templates", "luts", "prompts", "master")

    def bundle_etsy_product(self, product_type: str = "all") -> Dict[str, Any]:
        """Bundle full ready-to-sell Etsy digital delivery packages with listing copy & tags."""
        requested_product_type = product_type
        if product_type not in self.KNOWN_PRODUCT_TYPES:
            print(f"[EtsyDigitalStore] Unrecognized product_type '{product_type}' - falling back to 'all'.")
            product_type = "all"

        bundle_name = f"ETSY_DIGITAL_CREATOR_{product_type.upper()}_PACK"
        pkg_dir = self.output_base / bundle_name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        files_written = []

        # 1. Lightroom Presets
        if product_type in ("all", "presets", "master"):
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
            files_written.append("01_Lightroom_Presets/INSTALLATION_GUIDE.txt")

        # 2. Legal Contracts
        if product_type in ("all", "contracts", "master"):
            contracts_dir = pkg_dir / "02_Model_Contracts_and_Releases"
            contracts_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_legal_contracts().items():
                (contracts_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"02_Model_Contracts_and_Releases/{fname}")

        # 3. Posing Guide
        if product_type in ("all", "posing", "master"):
            posing_dir = pkg_dir / "03_Boudoir_Posing_Cards"
            posing_dir.mkdir(parents=True, exist_ok=True)
            guide_html = self.generate_posing_guide_cards()
            (posing_dir / "50_Boudoir_Posing_Guide_Cards.html").write_text(guide_html, encoding="utf-8")
            files_written.append("03_Boudoir_Posing_Cards/50_Boudoir_Posing_Guide_Cards.html")

        # 4. Social Promo Templates
        if product_type in ("all", "templates", "master"):
            banners_dir = pkg_dir / "04_Social_Promo_Templates"
            banners_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_promo_banner_templates().items():
                (banners_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"04_Social_Promo_Templates/{fname}")

        # 5. Cinematic 3D LUTs (.cube)
        if product_type in ("all", "luts", "master"):
            luts_dir = pkg_dir / "05_Cinematic_3D_LUTs"
            luts_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_3d_luts().items():
                (luts_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"05_Cinematic_3D_LUTs/{fname}")

            lut_guide = """================================================================
  CINEMATIC 3D LUT VIDEO PACK — INSTALLATION GUIDE
================================================================

COMPATIBLE WITH:
• Adobe Premiere Pro & After Effects
• DaVinci Resolve & DaVinci Resolve Studio
• Final Cut Pro X
• CapCut (Desktop & Mobile)
• OBS Studio (Live Streaming LUT Filter)
• Adobe Photoshop

HOW TO INSTALL:
1. Adobe Premiere Pro:
   - Go to Lumetri Color -> Creative tab -> Look dropdown -> Browse...
   - Select any .cube file from this folder. Adjust intensity with the slider!

2. DaVinci Resolve:
   - File -> Project Settings -> Color Management -> Open LUT Folder.
   - Drag this entire folder into the LUT directory and click 'Update Lists'.
   - Right-click any clip or node and apply the LUT under 3D LUTs!

3. CapCut Desktop:
   - Click on your video clip -> Adjustment tab -> LUT -> Import.
   - Select the .cube file to apply instant cinema color grading!

4. OBS Studio (Live Stream LUT):
   - Right-click your Video Capture Device (Camera) -> Filters -> Effect Filters (+).
   - Select 'Apply LUT' -> Browse -> Choose your desired .cube file.
================================================================"""
            (luts_dir / "INSTALLATION_GUIDE.txt").write_text(lut_guide, encoding="utf-8")
            files_written.append("05_Cinematic_3D_LUTs/INSTALLATION_GUIDE.txt")

        # 6. AI Prompt Engineering Bible
        if product_type in ("all", "prompts", "master"):
            prompts_dir = pkg_dir / "06_AI_Prompt_Engineering_Bible"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in self.generate_prompt_bible().items():
                (prompts_dir / fname).write_text(content, encoding="utf-8")
                files_written.append(f"06_AI_Prompt_Engineering_Bible/{fname}")

        # 7. Dynamic Listing Optimizer & Metadata
        listing_info = self._generate_listing_metadata(product_type)
        (pkg_dir / "ETSY_LISTING_METADATA_AND_TAGS.txt").write_text(listing_info, encoding="utf-8")

        # 8. Compress into ZIP
        zip_path = self.output_base / f"{bundle_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    fp = Path(root) / file
                    zipf.write(fp, arcname=str(fp.relative_to(pkg_dir)))

        return {
            "status": "ok",
            "product_type": product_type,
            "requested_product_type": requested_product_type,
            "bundle_name": bundle_name,
            "zip_path": str(zip_path),
            "zip_name": zip_path.name,
            "zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
            "total_files": len(files_written),
            "listing_guide": listing_info
        }

    def _generate_listing_metadata(self, product_type: str) -> str:
        """Generates category-tailored Etsy title, pricing, tags, and descriptions."""
        if product_type == "luts":
            return """================================================================
  ETSY LISTING OPTIMIZATION KIT — CINEMATIC 3D LUTS
================================================================

LISTING TITLE:
Cinematic 3D LUT Pack for Premiere Pro, DaVinci Resolve, Final Cut & CapCut | Kodak Portra & Cinestill Film Looks | Video Color Grading .CUBE

PRICE RECOMMENDATION:
- Standard Pack: $14.99 - $19.99
- Sale / Launch Price: $9.99

ETSY SEARCH TAGS (13 High-Traffic Tags):
1. video luts
2. premiere pro luts
3. davinci resolve lut
4. capcut presets
5. cinematic lut
6. film look lut
7. color grading cube
8. wedding video lut
9. youtube video luts
10. final cut pro lut
11. portra 400 lut
12. cinestill 800t lut
13. obs lut filter

LISTING DESCRIPTION:
Transform your video footage into stunning, high-budget cinematic films with one click! Compatible with Premiere Pro, DaVinci Resolve, Final Cut Pro, CapCut, and OBS Studio.

✨ WHAT IS INCLUDED (7 Cinematic 3D .CUBE LUTs):
• 01. Kodak Portra 400 (Golden skin warmth, soft highlight rolloff)
• 02. Cinestill 800T (Tungsten night cinema, atmospheric halation)
• 03. Moody Teal & Orange (Hollywood blockbuster grade)
• 04. Fuji Provia 100F (Clean editorial clarity, punchy greens and blues)
• 05. Golden Hour Warmth (Sun-drenched amber glow)
• 06. Noir Silver Monochrome (Timeless high-contrast black & white)
• 07. Cyber Neon Nightlife (Vivid magenta & cyan split for night/club sets)
• Comprehensive Step-by-Step Installation PDF / Text Guide

Instant digital download delivered immediately upon purchase!
================================================================"""
        elif product_type == "prompts":
            return """================================================================
  ETSY LISTING OPTIMIZATION KIT — AI PROMPT BIBLE
================================================================

LISTING TITLE:
Photorealistic FLUX.1 & Midjourney v6 Prompt Engineering Bible | 150+ Tested Photography Prompts, Lighting & Lens Cheat Sheet | AI Art Guide

PRICE RECOMMENDATION:
- Standard Lookbook: $12.99 - $17.99
- Sale / Launch Price: $8.99

ETSY SEARCH TAGS (13 High-Traffic Tags):
1. ai prompts
2. midjourney prompts
3. flux prompts
4. photorealistic prompt
5. prompt engineering
6. portrait prompts
7. comfyui prompt
8. photography prompts
9. digital download
10. ai art guide
11. midjourney v6
12. flux lora prompt
13. ai portrait guide

LISTING DESCRIPTION:
Stop struggling with plastic, fake-looking AI generations. This complete 150+ prompt engineering bible unlocks magazine-quality photorealism in FLUX.1 and Midjourney v6.

✨ WHAT IS INCLUDED:
• Interactive Dark-Mode HTML Lookbook with 1-Click "Copy Prompt" Buttons
• 150+ Categorized Master Prompts (Studio Fashion, Street, Macro, Widescreen, Film Emulation)
• Lens & Optics Formulas (24mm, 35mm, 50mm, 85mm f/1.4, 105mm Macro)
• Studio Lighting Cheat Sheet (Rembrandt, Chiaroscuro, Golden Hour, Editorial Flash)
• Plain-Text Searchable Quick Reference File

Instant digital download delivered immediately upon purchase!
================================================================"""
        else:
            return """================================================================
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

LISTING DESCRIPTION:
Elevate your boudoir, glamour, and creator photography with this complete professional toolkit. Designed by CreatorMediaLab for working studio photographers and creators for instant 1-click results.

✨ WHAT IS INCLUDED:
• 5 Professional Lightroom Presets (.XMP for Desktop & Mobile)
• 50 Studio-Tested Boudoir Posing Cards with Director Cues & Lighting Diagrams
• Attorney-Drafted Adult Model Release & 18 U.S.C. 2257 Compliance Checklist
• Property Shoot Location Release Agreement
• High-Converting Social Media Announcement & Tip Menu Banners
• Cinematic 3D LUTs (.CUBE) & Photorealistic AI Prompt Engineering Lookbook

Instant digital download delivered immediately upon purchase!
================================================================"""

    # =========================================================================
    # 8. ETSY .SVG STENCILS & .GLB / .STL 3D ASSETS (FROM IDEA OR FROM IMAGE)
    # =========================================================================
    def create_svg_stencil_asset(
        self,
        idea_prompt: str = "",
        source_image_path: str = "",
        output_name: str = "etsy_stencil",
        stencil_mode: str = "full_color",
        num_layers: int = 6,
        top_text: str = "",
        bottom_text: str = "",
        extrude_3d_medallion: bool = False,
    ) -> Dict[str, Any]:
        """
        Generates an expert-level Etsy .SVG asset (6-Layer Full-Color Stencil or B&W Vinyl Cut)
        either from a text idea (`idea_prompt`) OR from an existing image (`source_image_path`),
        with optional clean OpenType banner typography (`top_text`, `bottom_text`) and optional
        Blender 5.2 3D relief medallion extrusion (`.STL` + `.GLB`).
        """
        from pipeline.stages.comfyui_bridge import comfy_bridge
        return comfy_bridge.generate_etsy_svg_from_idea_or_image(
            idea_prompt=idea_prompt or None,
            source_image_path=source_image_path or None,
            output_name=output_name,
            stencil_mode=stencil_mode,
            num_layers=num_layers,
            top_text=top_text,
            bottom_text=bottom_text,
            extrude_3d_medallion=extrude_3d_medallion,
        )

    def create_3d_glb_stl_asset(
        self,
        idea_prompt: str = "",
        source_image_path: str = "",
        output_name: str = "etsy_3d_sculpt",
        texture_resolution: int = 2048,
        add_pedestal_base: bool = True,
        target_height_mm: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Generates an expert-level Etsy/Fiverr 3D PBR game asset (`.GLB`) and 100% watertight
        voxel-remeshed 3D-printable model (`.STL`) via ComfyUI Trellis 2 HQ + Blender 5.2 MCP,
        either from a text idea (`idea_prompt`) OR from an existing image (`source_image_path`).
        """
        from pipeline.stages.comfyui_bridge import comfy_bridge
        return comfy_bridge.generate_3d_glb_stl_from_idea_or_image(
            idea_prompt=idea_prompt or None,
            source_image_path=source_image_path or None,
            output_name=output_name,
            texture_resolution=texture_resolution,
            add_pedestal_base=add_pedestal_base,
            target_height_mm=target_height_mm,
        )


if __name__ == "__main__":
    store = EtsyDigitalStore()
    print("Etsy Digital Store module ready with 3D LUTs, AI Prompt Bible, SVG Stencils & 3D GLB/STL.")

