# Code Review & Implementation Plan for Scraper Adapter & YAML Architecture

**Date**: 2026-10-19
**Scope**: Full-stack review of `src/adapters/`, `src/config_schema.py`, `src/parser.py`, `src/orchestrator.py`, `src/main.py`, `src/ui_inspector/`, and `configs/`.

---

## Part 1: Code Review Findings

### 🔴 High Severity / Functional Bugs

#### 1. Output Schema Incompatibility Between `ConfigurableScraper` and `proposal_engine.load_jobs()`
* **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L96-L103) vs. [`src/proposal_engine.py`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L211-L227)
* **Issue**:
  * In `ConfigurableScraper.run()`, combined output files are written as a **raw JSON list** (`data = [asdict(j) for j in final_jobs]`), and saved under `output/{filename_prefix}_{timestamp}.json`.
  * However, [`save_jobs()`](file:///var/www/upwork-scraper-fs/src/output.py#L14-L40) and [`proposal_engine.load_jobs()`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L211-L227) expect a **`SearchResult` envelope dictionary** (`{"query": ..., "total_jobs": ..., "jobs": [...], "page": ..., "scraped_at": ...}`) AND `load_jobs()` only globs `upwork_*.json`.
  * Furthermore, if a profile has `filename_prefix: "wordpress_latest_50"` (which does not start with `upwork_`), `load_jobs()` skips it, and if a profile has `filename_prefix: "upwork_wordpress_enriched_top20"` (which starts with `upwork_`), `load_jobs()` crashes with `AttributeError: 'list' object has no attribute 'get'` when calling `data.get("jobs", [])`!
* **Impact**: Downstream workflows (`proposal_engine.py` and `mode: "from_saved_output"`) cannot read files written by `ConfigurableScraper` or will crash if a list-formatted JSON matches `upwork_*.json`.

#### 2. Ignored Configuration Fields in `ConfigurableScraper`
* **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L180-L270) and [`src/config_schema.py`](file:///var/www/upwork-scraper-fs/src/config_schema.py#L106-L133)
* **Issue**: Several fields declared in `ScrapeProfileConfig` and set in `configs/profiles/*.yaml` are not wired into the execution logic:
  1. **`search.input_saved_file`**: Declared in `SearchWorkflowConfig`, but `_run_from_saved_output()` ignores it and always scans the entire `self.output_dir`.
  2. **`enrichment.detail_retries`**: Declared in `EnrichmentWorkflowConfig`, but `_run_enrichment()` calls `self.adapter.fetch(fetch_req)` once without passing `max_retries=self.profile.enrichment.detail_retries` (so it always uses `transport.max_retries` instead of `detail_retries`).
  3. **`enrichment.compute_proposal_scores`**: Set to `true` in `wordpress_top20_enriched.yaml`, and while `_apply_filters()` filters by `min_score`, it **does not sort** the candidate jobs by score descending before slicing `jobs[:max_jobs_to_enrich]`! In the original [`scrape_top_details.py`](file:///var/www/upwork-scraper-fs/src/scrape_top_details.py), jobs were sorted by score descending *before* taking the top 20, and re-sorted by their new enriched score *after* enrichment.

---

### 🟡 Medium Severity / Architectural & Reliability Issues

#### 3. URL Query Encoding & `normalize_job_url` Edge Cases
* **Location**: [`src/orchestrator.py`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L121-L125) and [`src/parser.py`](file:///var/www/upwork-scraper-fs/src/parser.py#L46-L70)
* **Issue**:
  * `_run_live_search()` encodes the search query with `query.replace(" ", "+")`. If a user passes a query containing `&`, `#`, or `+` (e.g., `"C++ developer"` or `"wordpress & woocommerce"`), the query string breaks the URL parameters. `urllib.parse.quote_plus(query)` should be used instead.
  * In `normalize_job_url()`, `if "?referrer_url_path=" in url:` only strips `?referrer_url_path=...`. If UpWork appends `&referrer_url_path=...` or other query parameters (`?source=...`), they remain attached. Stripping any query string on `/jobs/..._~...` canonical URLs via `url.split("?", 1)[0]` is cleaner and safer.

#### 4. Per-Request `timeout_ms` and `max_retries` Not Honored by Adapters
* **Location**: [`src/adapters/flaresolverr_adapter.py`](file:///var/www/upwork-scraper-fs/src/adapters/flaresolverr_adapter.py#L57-L115) and [`src/adapters/base.py`](file:///var/www/upwork-scraper-fs/src/adapters/base.py#L10-L20)
* **Issue**:
  * `FetchRequest` carries `timeout_ms: int = 60000`, and enrichment workflows need per-request `max_retries` overrides (`detail_retries`).
  * However, `FlareSolverrAdapter.fetch()` ignores `request.timeout_ms` (always using `self.client.max_timeout`) and has no `max_retries` field on `FetchRequest`.

#### 5. Fragile Selector Auditing in `selector_registry.py` Masks Primary Selector Health
* **Location**: [`src/ui_inspector/selector_registry.py`](file:///var/www/upwork-scraper-fs/src/ui_inspector/selector_registry.py#L81-L86)
* **Issue**:
  * In `build_registry_from_yaml()`, for `job_detail.skills`, `upwork.yaml` lists `.skills-list .air3-line-clamp` first and `section[data-v-3b2c2248] .skills-list .air3-line-clamp` fourth.
  * Because `is_fragile: true` is set on `skills`, `build_registry_from_yaml()` loops through `rule.selectors` and overrides `chosen_selector` with the `data-v-3b2c2248` selector!
  * This causes `DriftAuditor` to report `skills` as `FRAGILE` / `BROKEN` on detail pages even when the primary selector (`.skills-list .air3-line-clamp`) is healthy and first in priority.
  * Additionally, `RegisteredSelector` only stores a single `css_selector: str` instead of auditing the fallback chain `selectors: list[str]`.

---

### 🟢 Low Severity / Cleanliness & Edge Cases

#### 6. `lru_cache` on `load_selector_config` Can Return Mutated State
* **Location**: [`src/config_schema.py`](file:///var/www/upwork-scraper-fs/src/config_schema.py#L162)
* **Issue**: `load_selector_config()` is decorated with `@lru_cache(maxsize=4)` and returns a mutable Pydantic `UpWorkSelectorConfig` instance. If any caller mutates `config.views[...]` in place during tests or runtime, subsequent callers receive the mutated cached object. Returning a deep copy or removing `lru_cache` (or using `model_copy(deep=True)`) prevents shared-state bugs.

#### 7. Sticky Proxy Metadata Not Consulted by `StealthySessionAdapter`
* **Location**: [`src/adapters/stealthy_adapter.py`](file:///var/www/upwork-scraper-fs/src/adapters/stealthy_adapter.py#L48-L62)
* **Issue**: In `src/ui_inspector/cli.py`, the CLI checks `session_manager.load_session_meta()` so that if the user previously logged in with `--direct` (no proxy), subsequent runs automatically use direct mode instead of a dead proxy. `StealthySessionAdapter.__init__()` does not check `session_meta.json`, so running `--adapter stealthy_session` with `authenticated_search.yaml` (`proxy_mode: pinned`) will attempt to use `proxies.txt[0]` even if the saved session in `.session/session_meta.json` was established with `direct: true`.

---

## Part 2: Implementation Plan for Fixes

### Phase 1: Standardize Output Envelope & Backward-Compatible Job Loading
1. **Unify JSON Output Format (`src/output.py` & `src/orchestrator.py`)**:
   - Update [`ConfigurableScraper.run()`](file:///var/www/upwork-scraper-fs/src/orchestrator.py#L96-L103) to save combined results using the standard `SearchResult` envelope (`{"query": ..., "total_jobs": ..., "jobs": [...], "page": 1, "scraped_at": ...}`) via a helper in `src/output.py` (`save_jobs_with_prefix()`).
   - Update [`proposal_engine.load_jobs()`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py#L211-L227) to:
     - Support both `SearchResult` dict envelopes (`data.get("jobs", [])`) and legacy flat list JSON files (`data if isinstance(data, list) else data.get("jobs", [])`), such as `output/wordpress_latest_50_*.json`.
     - Accept an optional `input_file: str | Path | None = None` or glob `*.json` (excluding `ui_reports/`) so profiles like `wordpress_latest_50` and `wordpress_top20_enriched` interoperate seamlessly.

### Phase 2: Wire All Profile Options in `ConfigurableScraper`
1. **Honor `search.input_saved_file` (`src/orchestrator.py`)**:
   - In `_run_from_saved_output()`, if `self.profile.search.input_saved_file` is set, load jobs specifically from that file; otherwise load from `self.output_dir`.
2. **Honor `enrichment.compute_proposal_scores` & Score Sorting (`src/orchestrator.py`)**:
   - In `_apply_filters()`, when `min_score` is set or `enrichment.compute_proposal_scores` is enabled, compute `score_job()` for each candidate and sort candidates by score descending (`reverse=True`) so `_run_enrichment()` enriches the highest-scoring jobs first.
   - After `_run_enrichment()` completes, if `enrichment.compute_proposal_scores` is `True`, re-score all enriched jobs with their newly fetched client spend/hires/proposals and re-sort descending.
3. **Honor `enrichment.detail_retries` & Per-Request Retries (`src/adapters/base.py`, `src/orchestrator.py`)**:
   - Add `max_retries: int | None = None` to `FetchRequest`.
   - Update `FlareSolverrAdapter.fetch()` and `StealthySessionAdapter.fetch()` to use `request.max_retries if request.max_retries is not None else self.max_retries` and `request.timeout_ms`.
   - Pass `max_retries=self.profile.enrichment.detail_retries` in `_run_enrichment()`.

### Phase 3: URL Encoding, Normalization & Session Metadata Alignment
1. **Proper Query URL Encoding (`src/orchestrator.py`)**:
   - Replace `query.replace(" ", "+")` with `urllib.parse.quote_plus(query)` in `ConfigurableScraper._run_live_search()` and `UpWorkScraper.search()`.
2. **Clean Query Stripping in `normalize_job_url` (`src/parser.py`)**:
   - Strip any query parameters (`?referrer_url_path=...`, `?source=...`) on `/jobs/` URLs using `url.split("?", 1)[0]`.
3. **Consult `session_meta.json` in `StealthySessionAdapter` (`src/adapters/stealthy_adapter.py`)**:
   - When `proxy_mode == "pinned"` and `proxy_url is None`, check `.session/session_meta.json` (just like `ui_inspector/cli.py` does). If the persisted session was recorded with `"direct": true`, honor direct mode automatically so authenticated scraping doesn't fail on a mismatched proxy.

### Phase 4: Selector Registry Fallback Chain Auditing & Config Immutability
1. **Fallback-Aware Selector Registry (`src/ui_inspector/selector_registry.py` & `src/ui_inspector/drift_auditor.py`)**:
   - Add `fallback_selectors: tuple[str, ...] = ()` to `RegisteredSelector`.
   - Always use `rule.selectors[0]` as the primary `css_selector` in `build_registry_from_yaml()`.
   - In `DriftAuditor._audit_single_selector()`, if the primary `css_selector` matches `0` elements, check `reg.fallback_selectors`:
     - If a fallback selector matches, report status as `"DEGRADED"` (noting which fallback selector matched) rather than `"BROKEN"`.
   - In `configs/selectors/upwork.yaml`, set `is_fragile: false` on `job_detail.skills` since its primary selector (`.skills-list .air3-line-clamp`) is semantic and non-fragile, while keeping `search_listings.posted` marked `is_fragile: true` because its primary selector relies on the `job-pubilshed-date` typo.
2. **Safe Config Loading (`src/config_schema.py`)**:
   - Cache the raw parsed YAML dict in `_load_selector_yaml_dict(target_path)` with `@lru_cache` and return a fresh `UpWorkSelectorConfig.model_validate(data)` on each `load_selector_config()` call so callers cannot corrupt cached state.

### Phase 5: Verification & Regression Tests
1. Add unit tests in `tests/test_adapters_and_config.py` covering:
   - `ConfigurableScraper` output JSON compatibility with `proposal_engine.load_jobs()`.
   - `from_saved_output` mode with score sorting, `min_score` filtering, and top-N enrichment re-sorting.
   - Per-request `max_retries` (`detail_retries`) propagation to `FetchRequest`.
   - Special characters in search queries (`quote_plus`).
   - `StealthySessionAdapter` automatic `session_meta.json` direct-mode detection.
2. Run `uv run ruff check`, `uv run pyright`, and `uv run pytest -v`.
