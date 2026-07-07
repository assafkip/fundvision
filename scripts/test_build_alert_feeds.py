#!/usr/bin/env python3
"""
Reproducer for build_alert_feeds.py - per-sector fund-move alert feeds (Phase 4).

"Ping me when a fund in my sector makes a move." A founder subscribes to their
sector's feed in any RSS reader and gets pinged on every new fund move. Static
files, no backend.

A "move" is fund ACTIVITY (a deal, a raise, an exit, actively-looking), not
market commentary. The feed must carry only moves, newest first, and be valid,
parseable RSS.

Run: .venv/bin/python scripts/test_build_alert_feeds.py   (or: pytest -q)
"""

import sys
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from build_alert_feeds import build_alert_feed, MOVE_CATEGORIES

TODAY = date(2026, 7, 7)


def _rows():
    return [
        {"signal_category": "new_investment", "summary": "Fund A led Acme's seed",
         "source_url": "https://x/1", "source_date": "2026-07-05", "person_name": "Fund A", "firm": "Fund A"},
        {"signal_category": "market_commentary", "summary": "AI is overhyped",
         "source_url": "https://x/2", "source_date": "2026-07-06", "person_name": "Pundit", "firm": "news"},
        {"signal_category": "exit_signal", "summary": "BigCo acquires SmallCo",
         "source_url": "https://x/3", "source_date": "2026-07-07", "person_name": "BigCo", "firm": "news"},
    ]


def test_feed_carries_only_moves():
    xml = build_alert_feed(_rows(), "Cybersecurity", TODAY)
    root = ET.fromstring(xml)  # raises if malformed
    titles = [i.findtext("title") for i in root.iter("item")]
    joined = " ".join(titles)
    assert "Acme" in joined, titles          # deal kept
    assert "acquires" in joined, titles      # exit kept
    assert "overhyped" not in joined, titles # commentary dropped
    assert len(titles) == 2, titles


def test_feed_is_valid_rss_with_sector_title():
    xml = build_alert_feed(_rows(), "Fintech / Payments", TODAY)
    root = ET.fromstring(xml)
    assert root.tag == "rss", root.tag
    chan_title = root.find("./channel/title").text
    assert "Fintech / Payments" in chan_title, chan_title


def test_items_sorted_newest_first():
    xml = build_alert_feed(_rows(), "Cybersecurity", TODAY)
    root = ET.fromstring(xml)
    dates = [i.findtext("{http://fundvision}date") for i in root.iter("item")]
    # exit (07-07) before deal (07-05)
    assert dates == sorted(dates, reverse=True), dates


def test_move_categories_include_deals_and_exits():
    assert "new_investment" in MOVE_CATEGORIES
    assert "exit_signal" in MOVE_CATEGORIES
    assert "market_commentary" not in MOVE_CATEGORIES


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
