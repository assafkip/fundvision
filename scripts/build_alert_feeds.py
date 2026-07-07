#!/usr/bin/env python3
"""
Per-sector fund-move alert feeds (Phase 4 - the founder hook).

"Ping me when a fund in my sector makes a move." A founder subscribes to their
sector's feed in any RSS reader and gets pinged on every new fund move. No
backend, no sign-up - static XML files a reader polls.

A "move" is fund ACTIVITY (a deal, a raise, an exit, a fund actively looking),
not market commentary. The dashboard's subscribe control hands the founder the
right feed URL per sector.

Single writer of alerts/<vertical>.xml.

Usage: .venv/bin/python scripts/build_alert_feeds.py
Test:  .venv/bin/python scripts/test_build_alert_feeds.py
"""

import json
from datetime import datetime, timezone, date
from pathlib import Path
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).parent.parent
VERTICALS_PATH = PROJECT_ROOT / "verticals.json"
ALERTS_DIR = PROJECT_ROOT / "alerts"
FV_NS = "http://fundvision"  # namespace for the machine-readable date element

# Fund MOVES worth a ping - activity, not commentary. Mirrors the hard/deal
# categories plus exits (compute_trends / derive_fund_intent share this vocab).
MOVE_CATEGORIES = {
    "new_investment", "new_fund_raised", "new_security_investment",
    "actively_looking", "new_thesis", "new_thesis_statement", "exit_signal",
}


def _day_key(row):
    return str(row.get("source_date") or "")


def build_alert_feed(rows, sector_label, today=None, limit=50):
    """Return an RSS 2.0 XML string of fund moves for one sector, newest first."""
    today = today or datetime.now(timezone.utc).date()
    if isinstance(today, datetime):
        today = today.date()

    moves = [r for r in rows if r.get("signal_category") in MOVE_CATEGORIES]
    moves.sort(key=_day_key, reverse=True)
    moves = moves[:limit]

    ET.register_namespace("fundvision", FV_NS)  # before build so the prefix is stable
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = f"FundVision alerts - {sector_label}"
    ET.SubElement(channel, "description").text = (
        f"Fund moves in {sector_label}: deals, raises, exits. Subscribe to get pinged."
    )
    ET.SubElement(channel, "lastBuildDate").text = today.strftime("%Y-%m-%d")

    for r in moves:
        item = ET.SubElement(channel, "item")
        who = r.get("person_name") or r.get("firm") or ""
        summary = r.get("summary") or ""
        title = f"{who}: {summary}" if who and who not in summary else summary
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = r.get("source_url") or ""
        ET.SubElement(item, "guid").text = r.get("source_url") or title
        ET.SubElement(item, "category").text = r.get("signal_category") or ""
        ET.SubElement(item, "pubDate").text = str(r.get("source_date") or "")
        # machine-readable date under our namespace (kept simple + sortable)
        ET.SubElement(item, f"{{{FV_NS}}}date").text = str(r.get("source_date") or "")

    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def _load_signals(vid):
    path = PROJECT_ROOT / f"signals-{vid}.json"
    if not path.exists():
        return []
    try:
        data = json.load(open(path))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else data.get("signals", [])


def main():
    today = datetime.now(timezone.utc).date()
    verticals = json.load(open(VERTICALS_PATH)).get("verticals", [])
    ALERTS_DIR.mkdir(exist_ok=True)
    for v in verticals:
        vid, label = v["id"], v.get("label", v["id"])
        rows = _load_signals(vid)
        xml = build_alert_feed(rows, label, today)
        out = ALERTS_DIR / f"{vid}.xml"
        out.write_text(xml)
        moves = sum(1 for r in rows if r.get("signal_category") in MOVE_CATEGORIES)
        print(f"  alerts/{vid}.xml - {moves} moves")
    print(f"Wrote {len(verticals)} sector alert feeds to {ALERTS_DIR}/")


if __name__ == "__main__":
    main()
