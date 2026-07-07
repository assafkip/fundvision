# Plan: derive_fund_intent — revealed thesis from announced deals

Date: 2026-07-07 · Repo: `projects/vc-signals-feed` · Status: PLAN (not built)
Decisions locked this session (all `[USER-DIRECTED]`):
- Target = **DO** (deals per fund), not SAY (thesis posts).
- Source rule loosened: any free ToS-clean feed/API; social case-by-case (CLAUDE.md updated).
- Buyer = founders raising. "Deal alpha / quietly circling" stays rejected.

## What / why

Replace the hand-typed "What funds want" panel (`derive_fund_criteria.py`, reads
prose in `vc_watchlist.json`) with a layer that DERIVES each fund's thesis from
its **announced deals in the live feed** — revealed preference, not typed
conclusions. Roll a fund's deal events up by sector + time; the pattern IS the
intent. Same engine shape as `compute_trends.py`, aimed at funds instead of volume.

## The hard blocker (must clear before the compute is worth writing)

Today the feed names ~0 investors: 5 of 1,666 rows carry a firm name, 3 of those 5
are garbage. RSS funding headlines are company-forward ("Quaise raises $134M"), the
investor lives in the article body. **No attribution = no per-fund rollup.** So the
plan gates on source-recon FIRST.

## Approach

### Step 0 — Source recon (time-boxed, ~60–90 min, gates everything)

Answer one question with evidence, not memory: **which free source names the
investor on a deal?** Check, in order, stopping when one clears the bar:

- **A — Crunchbase free / news API** (e.g. Crunchbase RSS, a free news API tier):
  does the feed/record expose `investors` / `lead_investor` fields for free?
- **B — Firm self-announcement feeds**: funds that blog their own deals
  ("Bridges invested in X"). Investor-forward by definition. Coverage = funds with
  a blog RSS (~2 today: Takwin, Bridges).
- **C — Enrich existing rows by fetching the linked article, then Haiku-extract the
  investor.** Highest coverage; now allowed under the loosened rule (public news
  page, not social). Cost = one fetch per funding row + one cheap LLM call.

Bar to clear: a source that yields **≥1 fund with ≥3 attributed deals** from real
data, free, ToS-clean. Write findings to this file's "Recon results" section.

### The cheap-LLM unlock (investor extraction) — the reason C now beats regex

Regex got 5/1,666 because it can't read "the round was led by Prelude Ventures
with participation from...". A **Haiku** call reads one excerpt/body and returns
structured `{company, investors[], lead, stage, amount}`. This is the difference
between DO being buildable and not. Model tier = Haiku (data extraction, per
`model-allocation.md`).

**Bounded cheap** (this is why it fits "very inexpensive"):
- Runs only on the ~9% funding-ish rows, never all 1,666.
- **Regex-first**: the LLM fires only on rows regex missed.
- **Cache by `source_url`**: each row extracted once, never re-run → steady state ≈ 0.
- Small input, tiny JSON out. Pennies per full refresh; near-zero after cache warms.

**Hallucination-gated (holds the no-invented-conclusions line):** LLM proposes, a
deterministic check disposes. Reject any investor name not present **literally** in
the source text. Invented firm → dropped. The LLM extracts; it never concludes.
Same shape as research-mode citation-enforcement.

**The reproducer is defined AFTER recon** — against whatever shape the winning
source actually returns. No reproducer written against a guessed schema.

### Step 1 — Build `scripts/derive_fund_intent.py` (mirrors compute_trends.py)

Deterministic, no LLM. Reads `signals-<vertical>.json` (+ whatever recon adds),
writes `fund-intent.json`. Single writer for that file (the `trends.json ←
compute_trends.py` pattern; the "one writer" rule).

Per fund it names:
- deal events attributed to the firm (category in a DEAL set:
  `new_investment`, `new_fund_raised`, `new_security_investment`)
- sector distribution of those deals (which verticals, weighted by recency)
- cadence / momentum (deals last 30/90d vs prior)
- derived one-line thesis = top sectors + stage signal, with the deal count behind it.
  **Templated over the deterministic counts — NOT an LLM paraphrase.** LLM does
  extraction only; the thesis sentence stays a template, or it re-grows the
  hand-typed-conclusions smell the panel was killed for.
- `coverage`: n deals seen — so a 3-deal read never poses as a 30-deal read

### Step 2 — Surface + honest ceiling

`index.html` renders `fund-intent.json` where the hand-typed panel was. Every card
shows its evidence count. Funds with no press/blog presence are stated as invisible,
not hidden. No overclaim.

## Files to touch

- NEW `scripts/derive_fund_intent.py` — the engine.
- NEW `scripts/extract_investors.py` — Haiku extractor: regex-first, LLM-fallback,
  string-verify against source, cache by `source_url`. Only touched if recon picks C.
- NEW `scripts/test_derive_fund_intent.py` — the reproducer (defined post-recon).
- NEW output `fund-intent.json` (git-committed like `trends.json`).
- MAYBE `data/**/vc_watchlist.json` or a new `data/**/deal_sources.json` — if recon
  picks A/B (add investor-forward feeds).
- MAYBE `scripts/live_monitor.py` — only if recon picks C (wire the extractor in).
- `index.html` — swap panel source (LAST, after the engine proves out).
- `README.md` — update "pure RSS" description IN this change if a non-RSS source lands.
- `derive_fund_criteria.py` / `compute_fund_criteria.py` — leave running in parallel;
  retire only after intent proves out (no silent removal of the current panel).

## Acceptance criteria (checkboxes — reproducer defines done)

- [x] Recon done: Option C clears the bar; findings + 3-article test in Recon block.
- [x] `extract_investors.py` runs regex-first, cached by `source_url`, LLM fallback injected (verify-gated). Haiku CLIENT not yet wired — injection point + verify/filter proven offline. `scripts/test_extract_investors.py` 9/9 green.
- [x] Extractor hallucination gate: **zero** investors survive that don't appear literally in the source text (`test_verify_gate_drops_name_absent_from_source`).
- [x] Extractor noise filter: law firms + person-name tokens dropped (`test_noise_filter_*`); generic-head phrases dropped (`test_generic_head_phrases_dropped`).
- [x] Fetchable rate measured: **94%** (48/51 rows; only finextra + thepaymentsassociation 403). Honest coverage number.

### Known limit (captured, not orphaned) — for the derive_fund_intent slice
Regex-first precision ceiling: title-case headlines where "Partners"/"VC"/"Capital"
are common words leak fragments ("Klarna Partners with…", "Ransomware Gang Partners",
"London-Based Tapestry VC"). Regex can't resolve title-case ambiguity. The engine
fixes this two ways: (a) LLM-fallback runs on the article BODY (sentence-case, high
precision), (b) a **min-recurrence + canonicalization** pass — a firm must appear
≥N times and collapse aliases ("London-Based Tapestry VC" → "Tapestry VC"), so
one-off title-case garbage never becomes a tracked fund.

### Built (all 4 phases shipped 2026-07-07, branch feat/derive-fund-intent)
- [x] `derive_fund_intent.py` — rollup engine (recurrence filter + geo-prefix canonicalization live here). Single writer of `fund-intent.json`.
- [x] `test_derive_fund_intent.py` 6/6 — intent-derives-from-rows, notes-negative (commentary yields no intent), recurrence filter, canonicalization + alias-merge, LLM-fallback-fires (verify gate drops a hallucinated name).
- [x] Haiku client wired into the extractor's fallback (`make_haiku_extractor` + `fetch_article_text`, stdlib urllib, no SDK). Degrades to regex-only with no `ANTHROPIC_API_KEY` (CI-safe). Fixed a caching bug: a regex-miss with no LLM no longer caches `[]` (would have blocked the LLM forever).
- [x] `derive_fund_intent.py` runs on real `signals-*.json`, writes `fund-intent.json`, prints coverage per fund.
- [x] intent comes from FEED ROWS, not `vc_watchlist.json` notes (engine never opens the watchlist; proven by the notes-negative test).
- [x] `fund-intent.json` shows honest coverage counts; low-evidence funds marked, not inflated. Live fetchable rate is measured (null when regex-only), never hardcoded.
- [x] `index.html` renders it ("What these funds actually do" panel with evidence counts + honest empty state); old "What funds want" panel kept in parallel. Browser-verified, zero console errors.

### Honest ceiling (open, not a blocker)
- Regex-only recovers 6/61 deal rows, all singletons -> 0 funds clear the 2-deal bar. The ≥3-deal bar is `{{NEEDS_PROOF}}` until a keyed run: body-level Haiku attribution (needs `ANTHROPIC_API_KEY` as a CI secret) is what populates multi-deal funds. Engine + wiring proven; only the key is missing. Cole stages, Assaf adds the secret.

### Phase 2-4 (shipped same session)
- [x] Phase 2 — honest coverage stats on the dashboard (deal rows, attributed, funds, hourly, live fetchable %). Parked positioning copy (`positioning-parked.md`) through assaf-voice, ships only when the DO panel populates.
- [x] Phase 3a — `exit_signal` category: M&A/IPO mined from feeds we already read (VC appetite). Dedicated hard category, tight phrases, excluded from DEAL_CATEGORIES + deal heat. `test_exit_classifier.py` 5/5.
- [x] Phase 3b — SEC EDGAR Form D dry-powder signal (new free gov source). `fetch_form_d.py`, single writer of `form-d-signals.json`, fixture-tested 4/4. Live run recovered 46 private-fund filings. `{{NEEDS_PROOF}}` on attribution (Form D names the fund, not its deals) — excluded from the deals rollup by design. Dashboard "Fresh dry powder" panel.
- [x] Phase 4 — per-sector alert feeds (`build_alert_feeds.py`, `alerts/<vertical>.xml`, 4/4). "Copy alert feed" subscribe control per sector. Email capture parked behind `ALERT_CAPTURE_ENDPOINT` until a form provider is chosen.
- [x] CI (`monitor.yml`) runs all four new steps hourly and commits their outputs. All 28 tests green.

### Cut permanently (as directed)
public API/MCP server, raw stock-market pipeline, backtested strategies, competing on data volume/latency.

## Patterns to follow (from this repo, not generic)

- `compute_trends.py` `highlights` block (lines ~208–228): deal-first, `source_kind=="vc"`, dedupe by firm, recency sort. The rollup extends this.
- `HARD_CATEGORIES` (compute_trends.py:33) already defines deal categories — reuse, don't redefine.
- `days_ago()` + 7-day bucket momentum (compute_trends.py:84–108) — reuse for cadence.
- Single-writer output: `trends.json ← compute_trends.py`. `fund-intent.json` gets exactly one writer.
- `test_fund_criteria.py` — existing test shape to match for the reproducer.

## Recon results (Step 0 — ran 2026-07-07)

**Verdict: Option C clears the bar. Build it.** Investors live in article bodies;
cheap extraction recovers them; the verify gate is confirmed necessary.

### What was measured
- 140 funding-ish rows across all verticals (recon regex is noisy — caught non-VC
  money news like an antitrust ruling + a treasury hack; the DEAL classifier in the
  engine must be tighter than `raise|$`).
- Top deal domains: techcrunch (17), space-capital substack (9), electrek (7),
  **news.crunchbase (6)**, pymnts (4), sifted, finextra, crowdfundinsider.

### Fetch + extract test (3 real deal articles)
| Source | Result | Investors recovered |
|---|---|---|
| techcrunch.com (Norm $120M) | ✅ clean | lead **Khosla Ventures** + Coatue, Craft, Bain, Vanguard… |
| sifted.eu (Proxima €411m) | ✅ clean | lead **XTX Ventures + East X**, + Google, Balderton, Cherry… |
| finextra.com (Stoa £1.8m) | ❌ 403 Forbidden | none — publication blocks automated fetch |

### Findings that change the build
1. **Attribution present: YES.** Article bodies name the lead + syndicate reliably
   on the two that fetched. Extraction (WebFetch's small model, literal-only prompt)
   returned structured, real firm names.
2. **Verify gate is mandatory, not belt-and-suspenders.** The raw extract leaked
   `Fenwick LLP` (law firm) and two individuals (Tony James, Jeff Hammes) into the
   investor list. So the engine needs: string-verify against source AND an
   investor-vs-noise filter (drop `LLP`/`Law`/person-name-shaped tokens).
3. **Coverage ceiling is real: some domains 403.** finextra blocked. Fetchable rate
   across the 140 rows is unmeasured — **measure it as the first build step** and
   surface it as the honest coverage number. Don't assume 100%.
4. **Cheaper path exists for part of the volume:** crunchbase-news + some headlines
   already name the investor in the RSS summary ("Google backs Proxima…"). Regex
   those first (free, no fetch), fetch+extract only the rest. Reinforces regex-first.

### Bar check (≥1 fund, ≥3 attributed deals)
Not yet provable — needs the extractor run across all 140 rows (that's build, not
recon). Directionally clears: Khosla appeared in both a cyber row and the TC row;
high-volume funds will recur across a month of feed. Prove it with the first real run.

```
source tried:      techcrunch, sifted, finextra (+ domain census of 140 rows)
attribution present: YES (bodies name lead + syndicate; 1 of 3 domains 403'd)
funds with ≥3 deals: unproven until extractor runs feed-wide (directionally yes)
verdict:           BUILD Option C — fetch + Haiku-extract + verify/filter,
                   regex-first on headlines/crunchbase summaries
```
