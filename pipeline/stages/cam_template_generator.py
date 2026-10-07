import os
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

class CamTemplateGenerator:
    """
    CAM TEMPLATE GENERATOR & TIP MENU MAKER (AGENT: ECHO [26 Fe] & AURA [79 Au])
    Generates high-converting, personalized profiles, tip menus, and OBS stream overlays
    for Chaturbate, MyFreeCams (MFC), Fansly, and OBS Studio.
    Includes high-level visual personalization:
      - Creator Hero Banners & Avatar Image Slots
      - 4-Photo Glamour Teaser Carousel / Gallery
      - Top Tipper of the Week Crown Badges
      - Lovense Lush Interactive Vibration Indicators
      - Dynamic Animated Token Goal Progress Bars
    """
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/cam_templates"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

        self.theme_colors = {
            "neon_cyber": {
                "name": "Neon Cyber",
                "bg": "#090d16",
                "card": "#111827",
                "accent": "#00f2fe",
                "secondary": "#f72585",
                "text": "#f3f4f6",
                "border": "#00f2fe",
                "glow": "rgba(0, 242, 254, 0.4)"
            },
            "velvet_boudoir": {
                "name": "Velvet Boudoir",
                "bg": "#12080c",
                "card": "#1e0e15",
                "accent": "#ffd166",
                "secondary": "#e63946",
                "text": "#fdf2f4",
                "border": "#ffd166",
                "glow": "rgba(255, 209, 102, 0.35)"
            },
            "pastel_dream": {
                "name": "Pastel Dream",
                "bg": "#13091f",
                "card": "#1f1033",
                "accent": "#f72585",
                "secondary": "#7209b7",
                "text": "#ffffff",
                "border": "#f72585",
                "glow": "rgba(247, 37, 133, 0.35)"
            },
            "gothic_noir": {
                "name": "Gothic Noir",
                "bg": "#050505",
                "card": "#121212",
                "accent": "#e63946",
                "secondary": "#a8dadc",
                "text": "#e5e5e5",
                "border": "#404040",
                "glow": "rgba(230, 57, 70, 0.35)"
            },
            "emerald_luxe": {
                "name": "Emerald Luxe",
                "bg": "#04140e",
                "card": "#09241a",
                "accent": "#06d6a0",
                "secondary": "#ffd166",
                "text": "#eefcf6",
                "border": "#06d6a0",
                "glow": "rgba(6, 214, 160, 0.35)"
            }
        }

    # =========================================================================
    # HIGH-LEVEL TEMPLATE 1: VIP CREATOR SHOWCASE PROFILE (WITH HERO BANNER & AVATAR)
    # =========================================================================
    def generate_vip_creator_showcase(
        self,
        model_name: str = "Goddess Aura",
        tagline: str = "Your VIP Uncensored Oasis · High Energy · Lovense Lush Synced",
        theme: str = "neon_cyber",
        avatar_url: str = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",
        banner_url: str = "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1200&q=80",
        gallery_images: Optional[List[str]] = None,
        top_tipper: str = "👑 King_Vip_99 (12,450 tks)",
        schedule: str = "Live Daily 9:00 PM – 2:00 AM EST",
        tip_menu: Optional[List[Dict[str, str]]] = None,
        goal_text: str = "Tonight's Goal: 2,500 / 5,000 Tokens — Full Lingerie Strip & Sensual Oil Show",
        goal_pct: int = 50
    ) -> str:
        """High-level customized profile with hero banner, avatar, teaser gallery, and categorized tip menu."""
        pal = self.theme_colors.get(theme, self.theme_colors["neon_cyber"])
        gallery = gallery_images or [
            "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80",
            "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80"
        ]

        menu_items = tip_menu or [
            {"tokens": "25 tks", "action": "Flash & Smile / Flirty Wink", "tier": "Quick Tease"},
            {"tokens": "50 tks", "action": "Blow Kisses & Shiver / Spank", "tier": "Quick Tease"},
            {"tokens": "100 tks", "action": "Sensual Body Oil on Décolletage", "tier": "Sensual"},
            {"tokens": "250 tks", "action": "Topless Tease / Slow Dance Routine", "tier": "Sensual"},
            {"tokens": "500 tks", "action": "Lovense Max Vibration (5 mins)", "tier": "Interactive Toy"},
            {"tokens": "1000 tks", "action": "Private Snapchat & VIP Room Access", "tier": "VIP Club"}
        ]

        html = f"""<!-- VIP CREATOR SHOWCASE PROFILE: {theme.upper()} -->
<div style="max-width: 820px; margin: 0 auto; background: {pal['bg']}; color: {pal['text']}; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; border: 2px solid {pal['border']}; border-radius: 20px; overflow: hidden; box-shadow: 0 15px 40px rgba(0,0,0,0.9);">

  <!-- 1. HERO BANNER WITH DYNAMIC CREATOR HEADER -->
  <div style="position: relative; height: 220px; background-image: url('{banner_url}'); background-size: cover; background-position: center; border-bottom: 2px solid {pal['border']};">
    <div style="position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(9,13,22,0.92) 100%);"></div>
    <div style="position: absolute; top: 16px; right: 16px; background: rgba(0,0,0,0.75); border: 1px solid {pal['border']}; border-radius: 20px; padding: 6px 14px; font-size: 11px; font-weight: bold; color: {pal['accent']}; box-shadow: 0 0 12px {pal['glow']};">
      ⚡ {schedule}
    </div>
  </div>

  <!-- 2. CREATOR AVATAR & IDENTITY DOCK -->
  <div style="position: relative; padding: 0 28px; margin-top: -65px; display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
    <div style="display: flex; align-items: flex-end; gap: 18px;">
      <!-- Glowing Circular Avatar -->
      <div style="position: relative; width: 120px; height: 120px; border-radius: 50%; padding: 4px; background: linear-gradient(135deg, {pal['accent']}, {pal['secondary']}); box-shadow: 0 0 25px {pal['glow']}; flex-shrink: 0;">
        <img src="{avatar_url}" alt="{model_name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: block; border: 3px solid {pal['bg']};" />
        <span style="position: absolute; bottom: 4px; right: 4px; background: #06d6a0; border: 2px solid #000; color: #000; font-size: 9px; font-weight: 900; padding: 2px 6px; border-radius: 10px; text-transform: uppercase;">LIVE</span>
      </div>
      <div style="margin-bottom: 8px;">
        <h1 style="margin: 0; font-size: 28px; font-weight: 900; color: #fff; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 16px {pal['glow']};">
          {model_name}
        </h1>
        <div style="font-size: 13px; color: {pal['accent']}; font-weight: 600; margin-top: 4px;">
          {tagline}
        </div>
      </div>
    </div>

    <!-- Top Tipper Crown Badge -->
    <div style="background: rgba(0,0,0,0.6); border: 1px solid rgba(255,209,102,0.4); border-radius: 12px; padding: 8px 16px; margin-bottom: 8px; text-align: right; box-shadow: 0 4px 15px rgba(255,209,102,0.15);">
      <div style="font-size: 10px; color: #ffd166; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;">TOP ROOM KING</div>
      <div style="font-size: 13px; font-weight: bold; color: #fff; margin-top: 2px;">{top_tipper}</div>
    </div>
  </div>

  <div style="padding: 24px 28px;">

    <!-- 3. INTERACTIVE TOKEN GOAL BAR -->
    <div style="background: {pal['card']}; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px 18px; margin-bottom: 22px; box-shadow: 0 6px 20px rgba(0,0,0,0.5);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 13px; font-weight: 800; color: {pal['accent']}; letter-spacing: 0.5px;">🎯 {goal_text}</span>
        <span style="font-size: 12px; font-weight: 900; color: #fff; background: rgba(0,0,0,0.5); padding: 2px 8px; border-radius: 6px;">{goal_pct}%</span>
      </div>
      <div style="height: 12px; background: rgba(0,0,0,0.6); border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08);">
        <div style="width: {goal_pct}%; height: 100%; background: linear-gradient(90deg, {pal['accent']}, {pal['secondary']}); box-shadow: 0 0 14px {pal['accent']};"></div>
      </div>
    </div>

    <!-- 4. 4-PHOTO GLAMOUR TEASER CAROUSEL -->
    <div style="margin-bottom: 24px;">
      <div style="font-size: 12px; font-weight: 800; color: {pal['accent']}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;">📸 EXCLUSIVE PHOTO TEASERS (CLICK TO EXPAND)</div>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
"""
        for img in gallery:
            html += f"""        <div style="border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15); aspect-ratio: 1; box-shadow: 0 4px 12px rgba(0,0,0,0.6);">
          <img src="{img}" alt="Teaser" style="width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.3s;" />
        </div>
"""

        html += f"""      </div>
    </div>

    <!-- 5. ABOUT ME & LOVENSE TOY STATUS -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
      <div style="background: {pal['card']}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;">
        <h3 style="color: {pal['accent']}; margin: 0 0 8px 0; font-size: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">💋 ABOUT ME</h3>
        <p style="font-size: 12.5px; line-height: 1.6; margin: 0; opacity: 0.9;">
          Hey loves! I'm {model_name}. I love high-energy conversations, playful lingerie, and teasing until you can't take it anymore. Tippers get direct audio voice notes & priority VIP attention!
        </p>
      </div>

      <div style="background: {pal['card']}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;">
        <h3 style="color: {pal['accent']}; margin: 0 0 8px 0; font-size: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">⚡ LOVENSE TOY SYNC</h3>
        <div style="display: flex; gap: 10px; margin-top: 10px;">
          <div style="flex: 1; background: rgba(0,0,0,0.4); border: 1px solid {pal['accent']}; border-radius: 8px; padding: 8px; text-align: center;">
            <div style="font-size: 18px;">🔥</div>
            <div style="font-size: 11px; font-weight: bold; color: {pal['accent']};">LUSH 3 ACTIVE</div>
          </div>
          <div style="flex: 1; background: rgba(0,0,0,0.4); border: 1px solid {pal['secondary']}; border-radius: 8px; padding: 8px; text-align: center;">
            <div style="font-size: 18px;">✨</div>
            <div style="font-size: 11px; font-weight: bold; color: {pal['secondary']};">DOMI 2 CONNECTED</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 6. HIGH-CONVERTING CATEGORIZED TIP MENU -->
    <div style="background: {pal['card']}; border: 2px solid {pal['border']}; border-radius: 16px; padding: 20px; margin-bottom: 24px; box-shadow: 0 0 25px {pal['glow']};">
      <div style="text-align: center; margin-bottom: 16px;">
        <h2 style="color: {pal['accent']}; font-size: 22px; margin: 0; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 12px {pal['glow']};">💎 INTERACTIVE REWARD MENU 💎</h2>
        <div style="font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 4px;">Tip exact tokens to trigger actions automatically in live stream</div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
"""
        for item in menu_items:
            tier_badge = item.get("tier", "Reward")
            html += f"""        <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <div>
            <div style="font-size: 10px; font-weight: 700; color: {pal['secondary']}; text-transform: uppercase;">{tier_badge}</div>
            <div style="font-size: 13px; font-weight: 600; color: #fff; margin-top: 2px;">{item['action']}</div>
          </div>
          <div style="background: {pal['accent']}; color: #000; font-weight: 900; font-size: 13px; padding: 5px 10px; border-radius: 6px; font-family: monospace; white-space: nowrap;">
            {item['tokens']}
          </div>
        </div>
"""

        html += f"""      </div>
    </div>

    <!-- 7. VIP VAULTS & SOCIAL LINKS -->
    <div style="text-align: center; padding: 18px; background: rgba(0,0,0,0.5); border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
      <div style="font-size: 11px; font-weight: 800; color: {pal['accent']}; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px;">FOLLOW MY UNCENSORED VIP VAULTS</div>
      <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 8px;">
        <a href="#" style="background: {pal['accent']}; color: #000; font-weight: 800; font-size: 12px; padding: 8px 18px; border-radius: 20px; text-decoration: none;">OnlyFans VIP</a>
        <a href="#" style="background: {pal['secondary']}; color: #fff; font-weight: 800; font-size: 12px; padding: 8px 18px; border-radius: 20px; text-decoration: none;">Fansly Wall</a>
        <a href="#" style="background: rgba(255,255,255,0.12); color: #fff; font-weight: 800; font-size: 12px; padding: 8px 18px; border-radius: 20px; text-decoration: none; border: 1px solid rgba(255,255,255,0.2);">Twitter / X</a>
        <a href="#" style="background: rgba(255,255,255,0.12); color: #fff; font-weight: 800; font-size: 12px; padding: 8px 18px; border-radius: 20px; text-decoration: none; border: 1px solid rgba(255,255,255,0.2);">Amazon Wishlist</a>
      </div>
    </div>

  </div>
</div>
"""
        return html

    # =========================================================================
    # HIGH-LEVEL TEMPLATE 2: OBS BROADCAST WEBCAM STREAM OVERLAY HUD
    # =========================================================================
    def generate_obs_broadcast_hud(
        self,
        model_name: str = "Goddess Aura",
        theme: str = "neon_cyber",
        items: Optional[List[Dict[str, str]]] = None,
        goal_text: str = "OIL SHOW: 1450 / 3000 TKS",
        top_tipper: str = "King_Vip_99 (500 tks)"
    ) -> str:
        """Transparent, glassmorphic broadcast HUD for OBS Studio Browser Source."""
        pal = self.theme_colors.get(theme, self.theme_colors["neon_cyber"])
        menu_items = items or [
            {"tokens": "25 tks", "action": "Flash & Smile"},
            {"tokens": "50 tks", "action": "Spank & Shiver"},
            {"tokens": "100 tks", "action": "Sensual Oil"},
            {"tokens": "250 tks", "action": "Dance Tease"},
            {"tokens": "500 tks", "action": "Lush Max (5m)"},
            {"tokens": "1000 tks", "action": "VIP Snapchat"}
        ]

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    margin: 0;
    padding: 20px;
    background: transparent;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    color: #fff;
    overflow: hidden;
  }}
  .obs-hud-container {{
    width: 340px;
    background: rgba(8, 12, 22, 0.88);
    backdrop-filter: blur(16px);
    border: 2px solid {pal['accent']};
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 0 30px {pal['glow']}, inset 0 0 15px rgba(0,0,0,0.8);
  }}
  .obs-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    padding-bottom: 10px;
    margin-bottom: 12px;
  }}
  .obs-name {{
    font-size: 15px;
    font-weight: 900;
    color: {pal['accent']};
    text-transform: uppercase;
    letter-spacing: 1px;
    text-shadow: 0 0 10px {pal['glow']};
  }}
  .obs-live-tag {{
    font-size: 10px;
    background: #06d6a0;
    color: #000;
    font-weight: 900;
    padding: 2px 7px;
    border-radius: 10px;
  }}
  .obs-goal-box {{
    background: rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 12px;
  }}
  .obs-goal-title {{
    font-size: 11px;
    font-weight: 800;
    color: {pal['secondary']};
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }}
  .obs-goal-bar {{
    height: 8px;
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    overflow: hidden;
  }}
  .obs-goal-fill {{
    width: 48%;
    height: 100%;
    background: linear-gradient(90deg, {pal['accent']}, {pal['secondary']});
    box-shadow: 0 0 10px {pal['accent']};
  }}
  .obs-tipper {{
    font-size: 10.5px;
    color: #ffd166;
    margin-bottom: 12px;
    background: rgba(255,209,102,0.1);
    border: 1px solid rgba(255,209,102,0.3);
    border-radius: 6px;
    padding: 5px 8px;
  }}
  .obs-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 12px;
  }}
  .obs-item-tokens {{
    background: {pal['accent']};
    color: #000;
    font-weight: 800;
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 4px;
    font-family: monospace;
  }}
  .obs-item-action {{
    font-weight: 600;
    color: #fff;
    text-align: right;
    max-width: 210px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
</style>
</head>
<body>
  <div class="obs-hud-container">
    <div class="obs-header">
      <span class="obs-name">{model_name}</span>
      <span class="obs-live-tag">● LIVE</span>
    </div>

    <div class="obs-goal-box">
      <div class="obs-goal-title">
        <span>🎯 {goal_text}</span>
        <span>48%</span>
      </div>
      <div class="obs-goal-bar">
        <div class="obs-goal-fill"></div>
      </div>
    </div>

    <div class="obs-tipper">
      👑 Top Tipper: <strong>{top_tipper}</strong>
    </div>

    <div class="obs-items-list">
"""
        for it in menu_items:
            html += f"""      <div class="obs-item">
        <span class="obs-item-tokens">{it['tokens']}</span>
        <span class="obs-item-action">{it['action']}</span>
      </div>
"""

        html += f"""    </div>
  </div>
</body>
</html>"""
        return html

    # =========================================================================
    # CLASSIC BIO & TABLE TEMPLATES
    # =========================================================================
    def generate_chaturbate_profile(
        self,
        model_name: str = "GoddessAura",
        theme: str = "neon_cyber",
        tip_menu: Optional[List[Dict[str, str]]] = None,
        socials: Optional[Dict[str, str]] = None
    ) -> str:
        """Classic profile format."""
        return self.generate_vip_creator_showcase(model_name=model_name, theme=theme, tip_menu=tip_menu)

    def generate_mfc_bio(self, model_name: str = "GoddessAura", theme: str = "velvet_boudoir", tip_menu: Optional[List[Dict[str, str]]] = None) -> str:
        """MFC format with velvet styling."""
        return self.generate_vip_creator_showcase(model_name=model_name, theme=theme, tip_menu=tip_menu)

    def generate_tip_menu_standalone(
        self,
        title: str = "✨ Goddess Aura's Interactive Tip Menu ✨",
        subtitle: str = "⚡ Lovense Lush & Domi Active · High Vibration ⚡",
        theme: str = "neon_cyber",
        layout_style: str = "vip_showcase",  # 'vip_showcase', 'table', 'cards', 'obs_overlay'
        items: Optional[List[Dict[str, str]]] = None,
        goal_text: str = "Tonight's Goal: 1500 / 3000 Tokens — Hot Oil & Dance Show",
        avatar_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        top_tipper: Optional[str] = None,
        schedule: Optional[str] = None
    ) -> str:
        """Generate standalone specialized Tip Menu in VIP Showcase, Table, Cards, or OBS Overlay style."""
        pal = self.theme_colors.get(theme, self.theme_colors["neon_cyber"])

        menu_items = items or [
            {"tokens": "25 tks", "action": "Flash & Smile / Flirty Wink"},
            {"tokens": "50 tks", "action": "Blow Kisses / Spank / Shiver"},
            {"tokens": "100 tks", "action": "Remove Top / Sensual Body Oil"},
            {"tokens": "250 tks", "action": "Dance Tease / Lap Dance"},
            {"tokens": "500 tks", "action": "Control Toy / 5 Min High Vibration"},
            {"tokens": "1000 tks", "action": "Exclusive Snap / VIP Tier Unlock"}
        ]

        if layout_style == "vip_showcase":
            kwargs = {
                "model_name": title.replace("✨", "").strip(),
                "tagline": subtitle,
                "theme": theme,
                "tip_menu": menu_items,
                "goal_text": goal_text
            }
            if avatar_url:
                kwargs["avatar_url"] = avatar_url
            if banner_url:
                kwargs["banner_url"] = banner_url
            if top_tipper:
                kwargs["top_tipper"] = top_tipper
            if schedule:
                kwargs["schedule"] = schedule
            return self.generate_vip_creator_showcase(**kwargs)
        elif layout_style == "cards":
            return self._render_cards_layout(title, subtitle, pal, menu_items, goal_text)
        elif layout_style == "obs_overlay":
            return self.generate_obs_broadcast_hud(model_name=title.replace("✨", "").strip(), theme=theme, items=menu_items, goal_text=goal_text)
        else:
            return self._render_table_layout(title, subtitle, pal, menu_items, goal_text)

    def _render_table_layout(self, title: str, subtitle: str, pal: Dict[str, str], items: List[Dict[str, str]], goal_text: str) -> str:
        html = f"""<!-- TIP MENU MAKER: TABLE STYLE -->
<div style="max-width: 680px; margin: 0 auto; background: {pal['bg']}; color: {pal['text']}; font-family: 'Segoe UI', Tahoma, sans-serif; border: 2px solid {pal['border']}; border-radius: 16px; padding: 22px; box-shadow: 0 10px 30px rgba(0,0,0,0.85);">
  <div style="text-align: center; margin-bottom: 16px;">
    <h2 style="color: {pal['accent']}; font-size: 24px; margin: 0 0 4px 0; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 12px {pal['glow']};">{title}</h2>
    <div style="font-size: 12px; color: {pal['secondary']}; letter-spacing: 0.5px; font-weight: bold;">{subtitle}</div>
  </div>

  <!-- Goal Progress Bar -->
  <div style="background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px 14px; margin-bottom: 16px;">
    <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px; font-weight: bold; color: {pal['accent']};">
      <span>{goal_text}</span>
      <span>50%</span>
    </div>
    <div style="height: 10px; background: rgba(255,255,255,0.08); border-radius: 5px; overflow: hidden;">
      <div style="width: 50%; height: 100%; background: linear-gradient(90deg, {pal['accent']}, {pal['secondary']}); box-shadow: 0 0 10px {pal['accent']};"></div>
    </div>
  </div>

  <!-- Menu Table -->
  <div style="background: {pal['card']}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; overflow: hidden;">
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
      <thead>
        <tr style="background: rgba(0,0,0,0.3); border-bottom: 1px solid rgba(255,255,255,0.12); color: {pal['accent']};">
          <th style="padding: 10px 14px; text-align: left; width: 130px;">TOKENS</th>
          <th style="padding: 10px 14px; text-align: left;">PERFORMER ACTION</th>
        </tr>
      </thead>
      <tbody>
"""
        for i, item in enumerate(items):
            bg = f"background: rgba(0,0,0,0.15);" if i % 2 == 1 else ""
            html += f"""        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); {bg}">
          <td style="padding: 10px 14px; font-weight: 800; font-family: monospace; font-size: 14px; color: {pal['accent']};">{item['tokens']}</td>
          <td style="padding: 10px 14px; color: {pal['text']}; font-weight: 500;">{item['action']}</td>
        </tr>
"""

        html += f"""      </tbody>
    </table>
  </div>
  <div style="text-align: center; margin-top: 14px; font-size: 11px; color: rgba(255,255,255,0.5);">
    ⚡ Tip the exact amount to trigger action automatically! ⚡
  </div>
</div>
"""
        return html

    def _render_cards_layout(self, title: str, subtitle: str, pal: Dict[str, str], items: List[Dict[str, str]], goal_text: str) -> str:
        html = f"""<!-- TIP MENU MAKER: BADGE CARDS STYLE -->
<div style="max-width: 720px; margin: 0 auto; background: {pal['bg']}; color: {pal['text']}; font-family: 'Segoe UI', Tahoma, sans-serif; border: 2px solid {pal['border']}; border-radius: 16px; padding: 22px; box-shadow: 0 10px 30px rgba(0,0,0,0.85);">
  <div style="text-align: center; margin-bottom: 18px;">
    <h2 style="color: {pal['accent']}; font-size: 24px; margin: 0 0 4px 0; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 12px {pal['glow']};">{title}</h2>
    <div style="font-size: 12px; color: {pal['secondary']}; letter-spacing: 0.5px; font-weight: bold;">{subtitle}</div>
  </div>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
"""
        for item in items:
            html += f"""    <div style="background: {pal['card']}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px; transition: transform 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
      <div style="display: inline-block; background: {pal['accent']}; color: #000; font-weight: 800; font-size: 12px; padding: 3px 8px; border-radius: 4px; margin-bottom: 6px; font-family: monospace;">
        {item['tokens']}
      </div>
      <div style="font-size: 13px; font-weight: 600; color: {pal['text']}; line-height: 1.4;">
        {item['action']}
      </div>
    </div>
"""

        html += f"""  </div>
</div>
"""
        return html

    def generate_chatbot_text(self, title: str, items: List[Dict[str, str]]) -> str:
        """Generate formatted plain text copy string for Chaturbate Notice Bots."""
        lines = [
            f"✨ {title.upper()} ✨",
            "--------------------------------------"
        ]
        for item in items:
            lines.append(f"💎 {item['tokens']} ➔ {item['action']}")
        lines.append("--------------------------------------")
        lines.append("Tip exact tokens to trigger actions automatically!")
        return "\n".join(lines)

    
    def bundle_digital_product(self, bundle_name: str = "CAM_BIO_KIT", theme: str = "neon_cyber", tip_menu: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        return self.bundle_tip_menu_product(bundle_name=bundle_name, theme=theme, items=tip_menu)

    def bundle_tip_menu_product(
        self,
        bundle_name: str = "GLAMOUR_TIP_MENU_PACK",
        theme: str = "neon_cyber",
        items: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Bundle a dedicated tip menu package with VIP Showcase, Table, Cards, OBS Overlay & Chatbot text."""
        pkg_dir = self.output_base / bundle_name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        menu_items = items or [
            {"tokens": "25 tks", "action": "Flash & Smile / Flirty Pose"},
            {"tokens": "50 tks", "action": "Blow Kisses / Spank / Shiver"},
            {"tokens": "100 tks", "action": "Remove Top / Sensual Oil"},
            {"tokens": "250 tks", "action": "Dance / Private Tease"},
            {"tokens": "500 tks", "action": "Control Toy / 5 Min Vibration"},
            {"tokens": "1000 tks", "action": "Exclusive Snap / VIP Tier Unlock"}
        ]

        vip_html = self.generate_vip_creator_showcase(theme=theme, tip_menu=menu_items)
        table_html = self.generate_tip_menu_standalone(theme=theme, layout_style="table", items=menu_items)
        cards_html = self.generate_tip_menu_standalone(theme=theme, layout_style="cards", items=menu_items)
        obs_html = self.generate_obs_broadcast_hud(theme=theme, items=menu_items)
        bot_text = self.generate_chatbot_text("INTERACTIVE TIP MENU", menu_items)

        # 1. Save HTML / Text files
        (pkg_dir / "VIP_Creator_Showcase_Profile.html").write_text(vip_html, encoding="utf-8")
        (pkg_dir / "Tip_Menu_Table_Style.html").write_text(table_html, encoding="utf-8")
        (pkg_dir / "Tip_Menu_Badge_Cards_Style.html").write_text(cards_html, encoding="utf-8")
        (pkg_dir / "OBS_Broadcast_Webcam_Overlay.html").write_text(obs_html, encoding="utf-8")
        (pkg_dir / "Chatbot_Notice_Text.txt").write_text(bot_text, encoding="utf-8")

        # 2. Save Installation Guide
        guide = f"""================================================================
  {bundle_name} — VIP CAM SUITE & TIP MENU INSTALLATION GUIDE
  (Etsy & Fiverr Digital Product Delivery)
================================================================

Thank you for purchasing this premium Cam Tip Menu & Profile Suite!

WHAT IS INCLUDED:
1. 'VIP_Creator_Showcase_Profile.html' - Ultra-VIP profile with banner, avatar, 4-photo teaser gallery, Lovense sync, and categorized tip menu.
2. 'OBS_Broadcast_Webcam_Overlay.html' - Transparent live stream overlay for your OBS Studio broadcast.
3. 'Tip_Menu_Table_Style.html' - Clean 2-column classic converting table.
4. 'Tip_Menu_Badge_Cards_Style.html' - Modern grid cards with neon token badges.
5. 'Chatbot_Notice_Text.txt' - Formatted copy-paste text for room notice bots.

HOW TO INSTALL ON CHATURBATE:
1. Open 'VIP_Creator_Showcase_Profile.html' or 'Tip_Menu_Table_Style.html' in Notepad.
2. Select all (Ctrl+A) and Copy (Ctrl+C).
3. In Chaturbate, go to your Profile Settings -> 'Bio / About Me'.
4. Paste (Ctrl+V) directly into the box and click Save!

HOW TO USE AS OBS WEBCAM OVERLAY:
1. Open OBS Studio.
2. Under 'Sources', click (+) -> 'Browser'.
3. Name it 'Tip Menu Overlay'.
4. Check 'Local file' and Browse to 'OBS_Broadcast_Webcam_Overlay.html'.
5. Set Width: 380, Height: 550. Click OK.
6. Position the floating menu anywhere on your webcam screen!

================================================================"""
        (pkg_dir / "INSTALLATION_GUIDE.txt").write_text(guide, encoding="utf-8")

        # 3. Create ZIP
        zip_path = self.output_base / f"{bundle_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in pkg_dir.iterdir():
                if f.is_file():
                    zipf.write(f, arcname=f.name)

        return {
            "status": "ok",
            "bundle_name": bundle_name,
            "zip_path": str(zip_path),
            "zip_name": zip_path.name,
            "zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
            "files": [f.name for f in pkg_dir.iterdir() if f.is_file()]
        }

    def generate_full_bundle(
        self,
        model_name: str = "GoddessAura",
        theme: str = "neon_cyber",
        tip_menu: Optional[List[Dict[str, str]]] = None,
        avatar_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        gallery_images: Optional[List[str]] = None,
        goal_text: Optional[str] = None,
        top_tipper: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bundle all templates into zip for client delivery."""
        cb_html = self.generate_vip_creator_showcase(
            model_name=model_name,
            theme=theme,
            avatar_url=avatar_url or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",
            banner_url=banner_url or "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1200&q=80",
            gallery_images=gallery_images,
            tip_menu=tip_menu,
            goal_text=goal_text or "Tonight's Goal: 2,500 / 5,000 Tokens — Full Lingerie Strip",
            top_tipper=top_tipper or "👑 King_Vip_99 (12,450 tks)"
        )
        mfc_html = self.generate_mfc_bio(model_name=model_name, theme=theme, tip_menu=tip_menu)
        tip_pack = self.bundle_tip_menu_product(bundle_name=f"Cam_Suite_{model_name}_{theme}", theme=theme, items=tip_menu)

        return {
            "status": "ok",
            "model_name": model_name,
            "theme": theme,
            "chaturbate_html": cb_html,
            "mfc_html": mfc_html,
            "zip_name": tip_pack["zip_name"],
            "zip_size_kb": tip_pack["zip_size_kb"],
            "bundle": tip_pack
        }

if __name__ == "__main__":
    gen = CamTemplateGenerator()
    print("Cam Template Generator ready with VIP Creator Showcase & OBS Overlays.")
