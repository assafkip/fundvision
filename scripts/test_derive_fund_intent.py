#!/usr/bin/env python3
"""
Reproducer for derive_fund_intent.py - the DO (deals-per-fund) rollup.

Proves the revealed-thesis engine before it touches real data:
- intent derives from FEED ROWS: a named investor's deals roll up into a thesis
  whose sectors match where the deals actually landed (not typed prose).
- notes-negative: a firm named only in a NON-DEAL row (commentary) yields NO
  intent. The engine reads deal events, never watchlist notes, so it cannot
  fall back to hand-typed conclusions.
- recurrence filter: a one-off firm (appears once) is dropped below min_recurrence.
- canonicalization: "London-Based Tapestry VC" collapses to "Tapestry VC" so a
  geo-prefixed alias never becomes a separate tracked fund.

Run: .venv/bin/python scripts/test_derive_fund_intent.py   (or: pytest -q)
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from derive_fund_intent import derive_intents, canonicalize


TODAY = date(2026, 7, 7)


def test_intent_derives_from_feed_rows():
    # Khosla makes two cyber deals + one fintech deal. The derived thesis must
    # reflect those sectors, ranked by where the deals landed - not any notes.
    rows_by_sector = {
        "Cybersecurity": [
            {"signal_category": "new_investment",
             "summary": "Acme Security raises $10M led by Khosla Ventures",
             "source_date": "2026-07-01", "source_url": "u1"},
            {"signal_category": "new_investment",
             "summary": "Beta Defense raises $5M led by Khosla Ventures",
             "source_date": "2026-06-20", "source_url": "u2"},
        ],
        "Fintech / Payments": [
            {"signal_category": "new_fund_raised",
             "summary": "Gamma Pay round led by Khosla Ventures",
             "source_date": "2026-05-15", "source_url": "u3"},
        ],
    }
    res = derive_intents(rows_by_sector, TODAY, min_recurrence=2)
    funds = {f["fund"]: f for f in res["funds"]}
    assert "Khosla Ventures" in funds, funds.keys()
    kf = funds["Khosla Ventures"]
    assert kf["coverage"] == 3, kf["coverage"]
    # top sector = Cybersecurity (2 deals beats fintech's 1)
    assert kf["sectors"][0]["label"] == "Cybersecurity", kf["sectors"]
    # thesis is a template over counts, and names the top sector
    assert "Cybersecurity" in kf["thesis"], kf["thesis"]


def test_notes_negative_commentary_yields_no_intent():
    # A firm named only in a commentary row (SAY, not DO) must not derive intent.
    rows_by_sector = {
        "Cybersecurity": [
            {"signal_category": "market_commentary",
             "summary": "Ghost Capital thinks AI security is overhyped",
             "source_date": "2026-07-01", "source_url": "c1"},
        ],
    }
    res = derive_intents(rows_by_sector, TODAY, min_recurrence=2)
    assert res["funds"] == [], res["funds"]


def test_recurrence_filter_drops_one_off_firm():
    # One deal for a firm, min_recurrence=2 -> dropped (kills title-case one-offs).
    rows_by_sector = {
        "Cybersecurity": [
            {"signal_category": "new_investment",
             "summary": "Solo raise led by Oneshot Ventures",
             "source_date": "2026-07-01", "source_url": "s1"},
        ],
    }
    res = derive_intents(rows_by_sector, TODAY, min_recurrence=2)
    assert res["funds"] == [], res["funds"]
    # same input, threshold of 1 -> it appears
    res1 = derive_intents(rows_by_sector, TODAY, min_recurrence=1)
    assert any(f["fund"] == "Oneshot Ventures" for f in res1["funds"]), res1["funds"]


def test_canonicalize_collapses_geo_prefixed_alias():
    assert canonicalize("London-Based Tapestry VC") == "Tapestry VC"
    assert canonicalize("SF-based Tapestry VC") == "Tapestry VC"
    assert canonicalize("  Khosla   Ventures.  ") == "Khosla Ventures"


def test_canonical_alias_merges_deals():
    # geo-prefixed and clean names for the same firm must roll into ONE fund.
    rows_by_sector = {
        "Climate / Energy": [
            {"signal_category": "new_investment",
             "summary": "Deal one led by London-Based Tapestry VC",
             "source_date": "2026-07-01", "source_url": "t1"},
            {"signal_category": "new_investment",
             "summary": "Deal two led by Tapestry VC",
             "source_date": "2026-06-25", "source_url": "t2"},
        ],
    }
    res = derive_intents(rows_by_sector, TODAY, min_recurrence=2)
    funds = {f["fund"]: f for f in res["funds"]}
    assert "Tapestry VC" in funds, funds.keys()
    assert funds["Tapestry VC"]["coverage"] == 2, funds["Tapestry VC"]


def test_llm_fallback_fires_when_regex_misses():
    # Headline names no investor (regex misses); the body does. A wired
    # fetcher+llm must recover it, and the verify gate must survive a real name
    # while dropping a hallucinated one.
    body = "The round was led by Prelude Ventures with participation from Congruent."

    def fetcher(url):
        return body

    def llm(text):
        # model returns one real name (in body) + one hallucinated (not in body)
        return ["Prelude Ventures", "Congruent", "Imaginary Capital"]

    rows_by_sector = {
        "Climate / Energy": [
            {"signal_category": "new_investment",
             "summary": "Fusion startup raises $50M",  # no firm in headline
             "source_date": "2026-07-02", "source_url": "b1"},
            {"signal_category": "new_investment",
             "summary": "Grid startup raises $20M",
             "source_date": "2026-06-28", "source_url": "b2"},
        ],
    }
    res = derive_intents(rows_by_sector, TODAY, min_recurrence=2,
                         cache={}, fetcher=fetcher, llm=llm)
    funds = {f["fund"]: f for f in res["funds"]}
    assert "Prelude Ventures" in funds, funds.keys()
    assert funds["Prelude Ventures"]["coverage"] == 2
    # hallucinated name never appears (verify gate held)
    assert "Imaginary Capital" not in funds, funds.keys()


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
