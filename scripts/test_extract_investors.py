#!/usr/bin/env python3
"""
Reproducer for extract_investors.py — the DO-attribution unlock.

Proves the deterministic core before any LLM spend:
- regex recovers real investors from deal text (free path, no fetch)
- the noise filter drops law firms + person-name individuals
- the verify gate drops any name not literally in the source (LLM hallucination guard)
- non-deal text yields nothing (no fabrication)

Run: .venv/bin/python scripts/test_extract_investors.py   (or: pytest -q)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_investors import (
    extract_from_text,
    filter_noise,
    verify_against_source,
    normalize_firm,
)


def test_regex_recovers_suffixed_lead():
    text = "AI law startup Norm raises $120M, led by Khosla Ventures and Craft Ventures"
    names = extract_from_text(text)
    assert "Khosla Ventures" in names, names
    assert "Craft Ventures" in names, names


def test_regex_recovers_suffixless_backer_from_headline():
    text = "Google backs Proxima Fusion in €411m raise"
    names = extract_from_text(text)
    assert "Google" in names, names


def test_noise_filter_drops_law_firm():
    kept = filter_noise(["Khosla Ventures", "Fenwick LLP"])
    assert "Fenwick LLP" not in kept
    assert "Khosla Ventures" in kept


def test_noise_filter_drops_individual_but_keeps_eponymous_firm():
    kept = filter_noise(["Tony James", "Andreessen Horowitz", "Khosla Ventures"])
    assert "Tony James" not in kept, "person-shaped name must be dropped"
    assert "Andreessen Horowitz" in kept, "known eponymous firm must survive"
    assert "Khosla Ventures" in kept


def test_verify_gate_drops_name_absent_from_source():
    source = "Norm raises $120M led by Khosla Ventures"
    candidates = ["Khosla Ventures", "Imaginary Capital"]  # second is hallucinated
    kept = verify_against_source(candidates, source)
    assert kept == ["Khosla Ventures"], kept


def test_non_deal_text_yields_nothing():
    text = "Iran-Linked Hackers Use New Cavern C2 Framework to Target Israeli Organizations"
    assert extract_from_text(text) == []


def test_verb_trigger_does_not_capture_lowercase_phrase():
    # regression: re.I on LED_RE used to capture "the fossil fuel industry"
    text = "The gas industry is sneaking into kids' classes, backed by the fossil fuel industry"
    assert extract_from_text(text) == []


def test_generic_head_phrases_dropped():
    # "Fresh Capital", "Venture Capital", "Global Equity" are prose, not firms
    for phrase in ["Fresh Capital", "Venture Capital", "Global Equity"]:
        assert filter_noise([phrase]) == [], phrase
    # a real firm with the same suffix survives
    assert filter_noise(["Air Street Capital"]) == ["Air Street Capital"]


def test_normalize_trims_and_dedupes_shape():
    assert normalize_firm("  Khosla Ventures.  ") == "Khosla Ventures"
    assert normalize_firm("Khosla   Ventures") == "Khosla Ventures"


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
