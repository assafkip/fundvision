# CLAUDE.md — The Signal (VC Investment Feed)

Standalone VC-signal feed. A Python monitor aggregates feeds and writes
`signals-data.json`; `index.html` renders it. Any free, ToS-clean feed or API is
fair game (RSS, JSON/news APIs, Crunchbase free tier, SEC/gov filings, firm blogs,
newsletters). No backend.

## The one rule

`signals-data.json` has exactly one writer: `scripts/live_monitor.py`. Never
hand-edit it. To change what shows up, edit the `data/*.json` source lists and re-run.

## Sources: free-first, social case-by-case

Add any free, aggregatable, ToS-clean feed or API. Prefer structured feeds
(RSS/JSON/APIs) over scraping. Social scraping (LinkedIn/X, Apify actors, browser
automation) is NOT banned but is NOT the default: use it only for a specific target
reachable no other way, and justify that source in the same change. Cost matters —
"free to aggregate" is the bar; a paid scraper needs a reason.

Scar (2026-07-06): the X/YouTube/Pinterest posters + their Apify actors were
archived because they didn't work here. Social-only sources carry that history;
weigh it before adding one.

## Common tasks

- **Add/remove a source** → edit `data/vc_watchlist.json`,
  `data/cyber_media_voices.json`, or `data/industry_sources.json`, then
  `python scripts/live_monitor.py --verbose`.
- **Dry run** → `--dry-run`.
- **Change hard/soft classification** → the keyword tables at the top of
  `scripts/live_monitor.py` (HARD_SIGNAL_KEYWORDS, SOFT_SIGNAL_KEYWORDS, PRIORITY_KEYWORDS).
- **Change the dashboard** → `index.html` is self-contained (inline CSS/JS).

## Data contract (index.html depends on these fields)

`person_name`, `firm`, `signal_type` (hard|soft), `signal_category`, `summary`,
`excerpt`, `source_url`, `source_type`, `source_date` (YYYY-MM-DD), `confidence`.
If you rename any of these in the engine, update `index.html` too.

## Known behavior

Industry sources (publications) fill `person_name` with the outlet name and `firm`
with the source type (e.g. "The Hacker News — news"). That is intentional — those
are outlet-attributed market signals, not a named partner. Filter by the "All firms"
dropdown to focus on named VC partners.

## Automation

`.github/workflows/monitor.yml` runs hourly and commits `signals-data.json` if it
changed. Deploy target is Vercel (static, redeploys on push). No secrets required.
