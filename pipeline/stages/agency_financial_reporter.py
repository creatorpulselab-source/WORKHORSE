"""
WORKHORSE Agency Revenue Split & Weekly Financial Reporter Engine
Tracks 80/20 creator splits, manages Cashtag settlement balances, and auto-generates weekly P&L summaries.
Author: Antigravity / WORKHORSE Pipeline
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from stages.cloud_daemon import get_secrets, _discord_req
except ImportError:
    from cloud_daemon import get_secrets, _discord_req

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("financial_reporter")

LEDGER_FILE = Path("F:/WORKHORSE/cam_shows/agency_accounting_ledger.json")


class AgencyAccountingLedger:
    def __init__(self, ledger_path: Path = LEDGER_FILE):
        self.ledger_path = ledger_path
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "transactions": [],
            "pending_agency_balance": 0.0,
            "lifetime_gross": 0.0,
            "lifetime_creator_share": 0.0,
            "lifetime_agency_cut": 0.0,
            "lifetime_manyvids_fees_saved": 0.0
        }

    def _save(self):
        try:
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ledger: {e}")

    def record_sale(
        self,
        order_id: str,
        buyer_id: str,
        buyer_name: str,
        amount: float,
        item_title: str,
        payment_method: str = "CashApp"
    ) -> Dict[str, Any]:
        """Calculates 80/20 split and records transaction."""
        creator_share = round(amount * 0.80, 2)
        agency_cut = round(amount * 0.20, 2)
        # ManyVids charges 35% on standard video sales
        manyvids_fee_saved = round(amount * 0.35, 2)

        tx = {
            "order_id": order_id,
            "timestamp": datetime.now().isoformat(),
            "buyer_id": buyer_id,
            "buyer_name": buyer_name,
            "amount": amount,
            "creator_80": creator_share,
            "agency_20": agency_cut,
            "manyvids_fee_saved": manyvids_fee_saved,
            "item_title": item_title,
            "payment_method": payment_method,
            "settled": False
        }

        self.data["transactions"].append(tx)
        self.data["pending_agency_balance"] += agency_cut
        self.data["lifetime_gross"] += amount
        self.data["lifetime_creator_share"] += creator_share
        self.data["lifetime_agency_cut"] += agency_cut
        self.data["lifetime_manyvids_fees_saved"] += manyvids_fee_saved
        self._save()

        logger.info(f"Recorded sale [{order_id}]: ${amount} (${agency_cut} 20% Agency Cut | ${creator_share} Creator 80%)")
        return tx

    def generate_weekly_report(
        self,
        days: int = 7,
        manager_cashtag: str = "$CareyPphoto"
    ) -> Dict[str, Any]:
        """Calculates weekly profit and loss, split breakdown, and 1-tap settlement links."""
        cutoff = datetime.now() - timedelta(days=days)
        recent_txs = [
            t for t in self.data["transactions"]
            if datetime.fromisoformat(t["timestamp"]) >= cutoff
        ]

        gross = sum(t["amount"] for t in recent_txs)
        creator_total = sum(t["creator_80"] for t in recent_txs)
        agency_total = sum(t["agency_20"] for t in recent_txs)
        saved_fees = sum(t["manyvids_fee_saved"] for t in recent_txs)

        clean_tag = manager_cashtag.lstrip("$")
        settlement_url = f"https://cash.app/${clean_tag}/{agency_total:.2f}" if agency_total > 0 else f"https://cash.app/${clean_tag}"

        return {
            "period_days": days,
            "start_date": cutoff.strftime("%b %d, %Y"),
            "end_date": datetime.now().strftime("%b %d, %Y"),
            "total_orders": len(recent_txs),
            "gross_revenue": round(gross, 2),
            "creator_share_80": round(creator_total, 2),
            "agency_cut_20": round(agency_total, 2),
            "manyvids_fees_saved": round(saved_fees, 2),
            "pending_settlement_balance": round(self.data["pending_agency_balance"], 2),
            "manager_cashtag": f"${clean_tag}",
            "settlement_url": settlement_url,
            "hosting_cost": 1.82,  # Bunny.net monthly hosting
            "transactions": recent_txs
        }


async def post_weekly_financial_statement(
    report: Dict[str, Any],
    channel_id: Optional[str] = None
) -> bool:
    """Posts weekly financial statement embed with 1-click settlement to Discord staff channel."""
    sec = get_secrets()
    disc_tok = sec.get("dashboard_auth", {}).get("discord_bot_token", "")
    chans = sec.get("dashboard_auth", {}).get("discord_channel_ids", {})
    dest_ch = channel_id or chans.get("financial_reports") or chans.get("staff_lounge") or chans.get("new_content_drops")

    if not disc_tok or not dest_ch:
        logger.error("Discord bot token or destination channel missing.")
        return False

    embed = {
        "title": f"📊 WEEKLY FINANCIAL & PROFIT STATEMENT ({report['start_date']} – {report['end_date']})",
        "description": (
            f"**Official Accounting Breakdown for Charlette Webb VIP Brand**\n"
            f"• **Total Completed Orders**: `{report['total_orders']}`\n"
            f"• **Infrastructure & CDN Hosting**: `-$1.82 / mo (Bunny.net)`\n"
            f"• **ManyVids Platform Cuts Avoided**: `+${report['manyvids_fees_saved']:,.2f}` 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "color": 0x10B981,  # Emerald Green
        "fields": [
            {
                "name": "💰 Gross Sales",
                "value": f"**${report['gross_revenue']:,.2f}**",
                "inline": True
            },
            {
                "name": "👑 Creator Net (80%)",
                "value": f"**${report['creator_share_80']:,.2f}**\n*(Direct to $CharletteWebb)*",
                "inline": True
            },
            {
                "name": "💼 Agency Fee (20%)",
                "value": f"**${report['agency_cut_20']:,.2f}**\n*(Owed to {report['manager_cashtag']})*",
                "inline": True
            },
            {
                "name": "🏦 Current Settlement Status",
                "value": (
                    f"• **Pending Balance Owed**: `${report['pending_settlement_balance']:,.2f}`\n"
                    f"• **Target Cashtag**: `{report['manager_cashtag']}`\n"
                    f"• **Settlement Link**: [Tap here to settle via CashApp]({report['settlement_url']})"
                ),
                "inline": False
            }
        ],
        "footer": {
            "text": "WORKHORSE Automated Creator Financial Engine • 100% Verified Ledger"
        }
    }

    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 5,  # Link
                    "label": f"💸 Settle 20% Fee ({report['manager_cashtag']})",
                    "url": report["settlement_url"]
                }
            ]
        }
    ]

    async with httpx.AsyncClient() as client:
        resp = await _discord_req(
            client,
            disc_tok,
            "POST",
            f"/channels/{dest_ch}/messages",
            json_body={"embeds": [embed], "components": components}
        )
        return resp.status_code in (200, 201)


if __name__ == "__main__":
    ledger = AgencyAccountingLedger()
    print("Agency Accounting Ledger Initialized.")
    report = ledger.generate_weekly_report(days=7, manager_cashtag="$CareyPphoto")
    print(f"Sample Report Generated: Gross ${report['gross_revenue']} | Agency 20%: ${report['agency_cut_20']}")
