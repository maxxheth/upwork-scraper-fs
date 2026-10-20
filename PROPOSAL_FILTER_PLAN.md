# UpWork Scraper: Proposal Count Research, Extraction & Filtering Plan

## 1. UI Research Findings (`src/ui_inspector/`)

Using [`UpWorkUIEngine`](file:///var/www/upwork-scraper-fs/src/ui_inspector/engine.py) and [`DriftAuditor`](file:///var/www/upwork-scraper-fs/src/ui_inspector/drift_auditor.py) against live UpWork search and job detail views revealed three critical behaviors:

1. **Search URL Facet (`&proposals=...`) Requires Authentication**:
   - Navigating to `https://www.upwork.com/nx/search/jobs/?q=wordpress&proposals=0-4,5-9,10-14` without an authenticated session triggers an HTTP redirect to `/ab/account-security/login?redir=...` (`0` cards returned).
   - Unauthenticated search pages (`/nx/search/jobs/?q=...`) render job cards without proposal counts (`proposals: null`), whereas authenticated sessions render `[data-test='proposals-tier']` directly on search cards.
2. **Job Detail Pages Always Render Proposal Tiers Publicly**:
   - Public job detail pages (`/jobs/..._~<id>/` $\rightarrow$ `/freelance-jobs/apply/...`) consistently render the `"Activity on this job"` section:
     ```html
     <ul class="visitor client-activity-items list-unstyled">
       <li class="ca-item">
         <span class="title">Proposals:</span>
         <span class="help-icon">
           <span data-test="popper" class="air3-popper air3-popover">Close the tooltip...</span>
         </span>
         <span class="value">15 to 20</span>
       </li>
     </ul>
     ```
3. **Drift Auditor `ca_item_value` Resolution**:
   - [`RegisteredSelector`](file:///var/www/upwork-scraper-fs/src/ui_inspector/selector_registry.py) and [`DriftAuditor._extract_sample_value`](file:///var/www/upwork-scraper-fs/src/ui_inspector/drift_auditor.py) now support `extract_mode="ca_item_value"` and `label_contains="Proposals"`, isolating `span.value` from the adjacent `span[data-test='popper']` tooltip text.

---

## 2. Upper-Bound Proposal Tier Normalization

[`parse_proposal_count()`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py) normalizes UpWork's text tiers into an **upper-bound integer** (`proposals_count` on [`UpWorkJob`](file:///var/www/upwork-scraper-fs/src/models.py)):

| UpWork Proposal Tier | Upper-Bound (`proposals_count`) | Included by `--max-proposals 10`? | Included by `--max-proposals 15`? | Included by `--max-proposals 50`? |
| :--- | :---: | :---: | :---: | :---: |
| `"Less than 5"` | `4` | ✅ Yes | ✅ Yes | ✅ Yes |
| `"5 to 10"` | `10` | ✅ Yes | ✅ Yes | ✅ Yes |
| `"10 to 15"` | `15` | ❌ No | ✅ Yes | ✅ Yes |
| `"15 to 20"` | `20` | ❌ No | ❌ No | ✅ Yes |
| `"20 to 50"` | `50` | ❌ No | ❌ No | ✅ Yes |
| `"50+"` | `999` | ❌ No | ❌ No | ❌ No |

---

## 3. Multi-Stage Filtering & Auto-Enrichment Pipeline

In [`ConfigurableScraper.run()`](file:///var/www/upwork-scraper-fs/src/orchestrator.py):
1. **Stage 2 (Pre-Enrichment Card Filter)**:
   - Any job card that already has a known `proposals` tier exceeding `filters.max_proposals` (e.g., from an authenticated `stealthy_session` or saved JSON file) is discarded immediately before detail-page requests are made.
   - Cards with `proposals=None` are retained (`include_unknown=True`) so Stage 3 can resolve their proposal count.
2. **Stage 3 (Auto-Enrichment & Post-Enrichment Filter)**:
   - When `filters.max_proposals` is set and any candidate job has `proposals=None`, the orchestrator **automatically enables detail-page enrichment** (`should_enrich = True`) even if `--with-details` / `enrichment.enabled` was not explicitly set.
   - After scraping the detail pages and merging `detail.proposals` + `detail.proposals_count`, [`job_meets_proposal_threshold(..., include_unknown=False)`](file:///var/www/upwork-scraper-fs/src/proposal_engine.py) filters out any job whose upper-bound proposal count exceeds `max_proposals`.

---

## 4. Agent & CLI Usage

### Scraper CLI (`src/main.py`)
```bash
# Scrape jobs and keep only those with <= 15 proposals (auto-enriches detail pages if needed)
uv run python -m src.main --query "wordpress developer" --max-proposals 15

# Authenticated session search with proposal threshold
uv run python -m src.main --adapter stealthy_session --query "python" --max-proposals 10
```

### Proposal Engine CLI (`src/proposal_engine.py`)
```bash
# Score and generate proposals only for saved jobs with <= 15 proposals
uv run python -m src.proposal_engine --query "wordpress" --max-proposals 15 --generate
```

### Declarative YAML Profile (`configs/profiles/*.yaml`)
```yaml
filters:
  required_keywords:
    - "wordpress"
  min_score: 40
  max_posted_age_days: 21
  max_proposals: 15
```
