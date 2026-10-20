# Code Review & Implementation Plan for Fixes

**Date**: 2026-10-20
**Status**: Ready for Review & Execution
**Target Repository**: `/var/www/upwork-scraper-fs`

---

## 1. Executive Summary

Following the implementation of the multi-query search architecture, native UpWork search URL facets (`per_page=50`, `contractor_tier`, `contract_type`), negative keyword filtering (`exclude_keywords`), expanded stack profile triads, and proposal engine enhancements, a full codebase audit was performed across [`src/`](file:///var/www/upwork-scraper-fs/src/), [`configs/`](file:///var/www/upwork-scraper-fs/configs/), and [`tests/`](file:///var/www/upwork-scraper-fs/tests/).

While all 26 unit tests, `ruff`, and `pyright` checks currently pass, the review identified **7 concrete issues** ranging from subtle edge-case bugs in CLI query overrides and skill-based keyword filtering to substring false positives and detail-page enrichment safety when `max_proposals` auto-enrichment is triggered on large wide-net runs.

---

## 2. Code Review Findings

### Finding 1 (High): `--query` CLI Override Ignored When Profile Defines `queries: list[str]`
- **Location**: [`src/main.py`](file:///var/www/upwork-scraper-fs/src/main.py#L171-L174) and [`src/config_schema.py`](file:///var/www/upwork-scraper-fs/src/config_schema.py#L94-L98)
- **Problem**: `SearchWorkflowConfig.effective_queries()` prioritizes `self.queries` whenever it is non-empty (`if self.queries: return ...`). In `src/main.py`:
  ```python
  if args.query is not None:
      profile.search.query = args.query
  ```
  If a user runs a multi-query profile (such as `python_latest_50.yaml` or `all_stacks_wide_harvester.yaml`) and passes `--query "custom query"` on the CLI to override the search, `profile.search.queries` remains populated from the YAML file, causing `--query` to be silently ignored!
- **Fix**: When `args.query is not None` and `args.queries is None`, clear `profile.search.queries = []` so the explicit CLI `--query` override takes precedence.

---

### Finding 2 (High): `required_keywords` and `exclude_keywords` Ignore `job.skills`
- **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L310-L327)
- **Problem**: In `ConfigurableScraper._apply_filters()`, both `required_keywords` and `exclude_keywords` only inspect `j.title.lower()` and `j.description.lower()`:
  ```python
  if any(k in j.title.lower() or k in j.description.lower() for k in keywords)
  ```
  On UpWork search cards, the description snippet is truncated, and critical technology tags (e.g., `"FastAPI"`, `"Terraform"`, `"PostgreSQL"`, `"Playwright"`, `"WordPress"`) frequently appear only in the `job.skills` token badges (`data-test="token"`). Ignoring `j.skills` causes valid jobs to be falsely dropped by `required_keywords` in `*_top20_enriched.yaml` profiles, and allows excluded skills to slip past `exclude_keywords`.
- **Fix**: Build a combined haystack per job (`f"{j.title} {j.description} {' '.join(j.skills)}".lower()`) and evaluate both `required_keywords` and `exclude_keywords` against it.

---

### Finding 3 (Medium): Substring False Positives in Short Keywords (`"go"`, `"ai"`, `"rag"`, `"c#"`)
- **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L310-L327) and [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L387-L398)
- **Problem**:
  1. In [`golang_top20_enriched.yaml`](file:///var/www/upwork-scraper-fs/configs/profiles/golang_top20_enriched.yaml#L24-L30), `"go"` is in `required_keywords`. Substring matching (`"go" in haystack`) matches `"good"`, `"google"`, `"category"`, `"django"`, `"logo"`, `"negotiate"`, etc., rendering the filter ineffective.
  2. In [`ai_integration_top20_enriched.yaml`](file:///var/www/upwork-scraper-fs/configs/profiles/ai_integration_top20_enriched.yaml#L24-L33), `"ai"` and `"rag"` are in `required_keywords`. Substring matching (`"ai" in haystack`, `"rag" in haystack`) matches `"email"`, `"main"`, `"tailwind"`, `"domain"`, `"drag"`, `"storage"`, `"average"`, etc.
  3. In [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L390-L396) and `score_job()`, short keywords like `"agent"`, `"rag"`, `"api"`, `"css"`, `"vue"` use raw substring `in`, which can match `"management"` (`"agent"`), `"storage"` (`"rag"`), etc.
- **Fix**:
  - Introduce a helper `keyword_matches(keyword: str, haystack: str) -> bool` that uses word-boundary regex (`\b`) for short or alphanumeric keywords (while still supporting punctuation-bearing terms like `"c#"`, `".net"`, `"ci/cd"`, `"next.js"` via custom boundary patterns `(?<![a-z0-9])...(?![a-z0-9])`).
  - Use this boundary-aware matcher in `_apply_filters()`, `score_job()`, `match_portfolio_references()`, and `generate_proposal()`.

---

### Finding 4 (Medium): Unbounded Detail-Page Requests When Auto-Enriching for `max_proposals`
- **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L118-L134) and [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L365-L370)
- **Problem**: When `max_proposals` is set on a profile or CLI run where `enrichment.enabled` is `False` and `enrichment.max_jobs_to_enrich` is `None` (for example: `uv run python -m src.main --config configs/profiles/all_stacks_wide_harvester.yaml --max-proposals 15`), Stage 3 auto-enables detail enrichment to resolve missing proposal counts. Because `max_jobs_to_enrich` is `None`, `_run_enrichment()` will attempt to fetch detail pages for **all 400 harvested jobs** sequentially. Furthermore, any job beyond `max_jobs_to_enrich` (`remaining = jobs[max_enrich:]`) retains `proposals=None` and is subsequently dropped by the post-enrichment `include_unknown=False` filter, meaning `max_jobs_to_enrich` acts as the true ceiling on returned jobs when `max_proposals` is active.
- **Fix**:
  1. When auto-enabling enrichment solely for `max_proposals` and `max_jobs_to_enrich is None`, apply a sensible default cap (e.g., `25` jobs, or `profile.search.target_jobs` if `<= 50`) and log a clear message so wide-net profiles don't accidentally launch hundreds of detail requests.
  2. Pre-score and sort candidates before auto-enrichment so the top candidates are enriched first.

---

### Finding 5 (Medium): `parse_posted_age("Posted 1 hour ago")` Returns `1` Day Instead of `0` Days
- **Location**: [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L49-L51)
- **Problem**:
  ```python
  m = re.search(r"(\d+)\s*hour", text)
  if m:
      return max(1, int(m.group(1)) // 24)
  ```
  Also, `"Posted 15 minutes ago"` is not matched by any regex and returns `None`!
  - Because `"15 minutes ago"` returns `None`, `score_job()` awards **0 recency points** (`else: pass # Unparseable — assume old, no points`) to the freshest jobs on UpWork (posted minutes ago)!
  - Because `"2 hours ago"` returns `max(1, 2 // 24) == 1`, it is treated as 1 day old (8 pts) instead of `<24 hours / 0 days old` (10 pts).
- **Fix**:
  - Add regex matching for `(\d+)\s*(?:minute|min|second|sec)` returning `0` days.
  - Change `(\d+)\s*hour` to return `int(m.group(1)) // 24` (so `<24 hours` returns `0` days, earning the full 10 recency points in `score_job()`).

---

### Finding 6 (Low): `load_jobs()` Skips Valid Saved Files When `save_jobs_with_prefix` Is Used or Non-`upwork_` Files Exist
- **Location**: [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L298-L320) and [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L261-L270)
- **Problem**:
  In `load_jobs()`, files are iterated in ascending alphabetical order (`sorted(...)`), and `if url and url not in seen_urls:` keeps the **first** (oldest) occurrence of a job rather than the **newest** (most recently scraped or enriched) occurrence!
  For example, if a job was first scraped by `all_stacks_wide_harvester` (with a truncated search description and `proposals=None`) into `upwork_wide_harvest_20261020_090000.json`, and later enriched by `all_stacks_sniper_enriched` into `upwork_all_stacks_sniper_top25_20261020_090500.json`, `load_jobs()` reads files alphabetically or chronologically and if the unenriched file comes first, it ignores the enriched version of the same URL!
- **Fix**:
  - In `load_jobs()`, sort files by modification time descending (`key=lambda p: p.stat().st_mtime, reverse=True`) or merge enriched fields when a duplicate URL is encountered so that a job with `client_spent` / `proposals` / longer `description` always takes precedence over an unenriched card.

---

### Finding 7 (Low): `score_job()` Fixed-Price Detection Only Checks `hourly_rate`
- **Location**: [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L208-L216)
- **Problem**:
  ```python
  rate = job.get("hourly_rate", "") or ""
  ...
  elif "Fixed" in rate:
      score += 5
  ```
  In `ConfigurableDomParser.parse_job_listings()`, fixed-price jobs have `hourly_rate=None` and `budget="$150.00"` or `budget="Fixed price"`. Thus `rate` is `""`, and fixed-price jobs receive `0` rate points even when they have a generous fixed budget (e.g., `$1,500.00`).
- **Fix**: Check `budget = job.get("budget", "") or ""` when `hourly_rate` is empty: award points based on parsed fixed-price budget tiers (e.g., `>= $1,000` -> 20 pts, `>= $500` -> 15 pts, `>= $200` -> 10 pts, other fixed -> 5 pts).

---

## 3. Implementation Plan

### Phase 1: Keyword Boundary Matcher & Filter Enhancements
1. **Add `keyword_matches(keyword: str, text: str) -> bool` in [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py)**:
   - Use regex `(?<![a-z0-9_]){re.escape(keyword.lower())}(?![a-z0-9_])` so `"go"`, `"ai"`, `"rag"`, `"c#"`, `".net"`, `"ci/cd"`, and `"next.js"` all match accurately on token boundaries without false-matching inside words like `"google"`, `"email"`, `"storage"`, or `"management"`.
2. **Update `ConfigurableScraper._apply_filters()` in [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py)**:
   - Include `j.skills` in the haystack alongside `j.title` and `j.description`.
   - Use `keyword_matches()` for both `required_keywords` and `exclude_keywords`.
3. **Update `score_job()`, `match_portfolio_references()`, and `generate_proposal()` in [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py)**:
   - Use `keyword_matches()` when matching `PORTFOLIO_KEYWORDS`, `PORTFOLIO_REFERENCES`, and category triggers.

### Phase 2: Recency & Fixed-Price Scoring Fixes in `src/proposal_engine.py`
1. **Fix `parse_posted_age()`**:
   - Match `minute` / `min` / `second` / `sec` $\rightarrow$ `0` days.
   - Match `hour` / `hr` $\rightarrow$ `int(hours) // 24` (`0` days for `<24` hours).
2. **Fix Fixed-Price Budget Scoring in `score_job()`**:
   - Parse numeric budget values from `job.get("budget")` when `hourly_rate` is absent (`>= $1,000`: 20 pts, `>= $500`: 15 pts, `>= $200`: 10 pts, fallback fixed: 5 pts).
3. **Upgrade `load_jobs()` Deduplication**:
   - When a duplicate URL is encountered across saved JSON files, merge/prefer the record that has richer metadata (`proposals`, `client_spent`, or longer `description`).

### Phase 3: Orchestrator Auto-Enrichment Guard & CLI Override Fix
1. **Fix `--query` Override in [`src/main.py`](file:///var/www/upwork-scraper-fs/src/main.py)**:
   - When `args.query is not None` and `args.queries is None`, reset `profile.search.queries = []`.
2. **Cap Unbounded Auto-Enrichment in [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py)**:
   - When `needs_proposal_enrichment` triggers on a profile where `enrichment.enabled` was `False`, pre-sort `filtered_jobs` by `score_job()` descending and default `max_jobs_to_enrich` to `25` if it was `None`.

### Phase 4: Verification & Regression Tests
1. Add unit tests in [`tests/test_adapters_and_config.py`](file:///var/www/upwork-scraper-fs/tests/test_adapters_and_config.py) covering:
   - Word-boundary matching (`"go"` does not match `"google"` or `"django"`, `"ai"` does not match `"tailwind"` or `"email"`, `"c#"` and `".net"` match properly).
   - `required_keywords` and `exclude_keywords` matching against `job.skills`.
   - `parse_posted_age` for minutes (`"Posted 14 minutes ago"` $\rightarrow$ `0`) and hours (`"Posted 3 hours ago"` $\rightarrow$ `0`).
   - Fixed-price budget scoring in `score_job()`.
   - CLI `--query` overriding a profile that has `queries: [...]`.
   - `load_jobs()` preferring enriched job records over unenriched records with the same URL.
2. Run `uv run pytest -v`, `uv run ruff check src/ tests/`, and `uv run pyright src/ tests/`.
