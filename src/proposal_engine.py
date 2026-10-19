"""UpWork Proposal Engine — score jobs, generate proposals, create implementation plans.

Usage:
    uv run python -m src.proposal_engine --score-only
    uv run python -m src.proposal_engine --generate
    uv run python -m src.proposal_engine --top 3
    uv run python -m src.proposal_engine --query "wordpress" --generate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Recency Filter ─────────────────────────────────────────────────────

def parse_posted_age(posted: str | None) -> int | None:
    """Parse a human-readable posted string into approximate days old.

    Handles formats like:
      - "Posted 1 hour ago" / "Posted 2 hours ago"
      - "Posted 3 days ago" / "Posted 5 days ago"
      - "Posted 1 week ago" / "Posted 2 weeks ago"
      - "Posted 1 month ago" / "Posted 3 months ago"
      - "Just now" / "Today"
      - "Yesterday"

    Returns:
        Approximate days since posted, or None if unparseable.
    """
    if not posted:
        return None

    text = posted.lower().replace("posted ", "").strip()

    if text in ("just now", "today", "moments ago", "a few seconds ago", "a minute ago"):
        return 0
    if text == "yesterday":
        return 1

    m = re.search(r"(\d+)\s*hour", text)
    if m:
        return max(1, int(m.group(1)) // 24)

    m = re.search(r"(\d+)\s*day", text)
    if m:
        return int(m.group(1))

    m = re.search(r"(\d+)\s*week", text)
    if m:
        return int(m.group(1)) * 7

    m = re.search(r"(\d+)\s*month", text)
    if m:
        return int(m.group(1)) * 30

    m = re.search(r"(\d+)\s*year", text)
    if m:
        return int(m.group(1)) * 365

    return None


# ── Scoring ──────────────────────────────────────────────────────────────

# Your portfolio keywords for skill matching
PORTFOLIO_KEYWORDS = [
    "wordpress", "php", "python", "golang", "react", "javascript",
    "sage", "docker", "api", "postgresql", "mysql", "aws", "devops",
    "tailwind", "typescript", "vue", "laravel", "acf", "gutenberg",
    "css", "html", "rest", "graphql", "nginx", "redis", "linux",
    "scrapy", "selenium", "playwright", "puppeteer", "pandas",
    "fastapi", "flask", "django", "next.js", "nuxt",
]

PORTFOLIO_REFERENCES = [
    {
        "title": "Sandoval Landscaping",
        "url": "https://sandovallandscaping.com",
        "keywords": ["wordpress", "sage", "acf", "tailwind", "php", "css", "html", "gutenberg"],
        "description": "Custom production WordPress/Sage theme from design mockups.",
    },
    {
        "title": "Groundhogs TX",
        "url": "https://groundhogstx.com",
        "keywords": ["wordpress", "woocommerce", "performance", "maintenance", "css", "php"],
        "description": "Production WordPress site with ongoing maintenance and optimization.",
    },
    {
        "title": "UpWork Scraper",
        "url": "",
        "keywords": ["python", "scraper", "scrapy", "selenium", "playwright", "puppeteer", "api", "proxy"],
        "description": "Python scraping pipeline for JS-rendered pages, Cloudflare bypass, and proxy rotation.",
    },
    {
        "title": "UpWork Buddy",
        "url": "",
        "keywords": ["golang", "go", "postgresql", "api", "typescript", "react", "docker"],
        "description": "Go/PostgreSQL backend and TypeScript browser assistant for job analysis workflow.",
    },
]

PROPOSAL_SCHEMA_VERSION = "1.0"


def score_job(job: dict[str, Any]) -> int:
    """Score a single job on 0-100 scale."""
    score = 0

    # Rate match (25 pts)
    rate = job.get("hourly_rate", "") or ""
    if any(f"${n}" in rate for n in ["50", "60", "70", "80", "90"]):
        score += 25
    elif any(f"${n}" in rate for n in ["100", "110", "125", "150"]):
        score += 20
    elif any(f"${n}" in rate for n in ["30", "40"]):
        score += 10
    elif "Fixed" in rate:
        score += 5

    # Skill match (25 pts)
    skills = [s.lower() for s in job.get("skills", [])]
    matches = sum(1 for k in PORTFOLIO_KEYWORDS if any(k in s for s in skills))
    score += min(25, matches * 5)

    # Client spend (15 pts)
    spend = job.get("client_spent", "") or ""
    if spend:
        spend_num = _parse_spend(spend)
        if spend_num >= 100_000:
            score += 15
        elif spend_num >= 10_000:
            score += 12
        elif spend_num >= 1_000:
            score += 8

    # Client hires (10 pts)
    hires = job.get("client_hires") or 0
    if hires >= 50:
        score += 10
    elif hires >= 10:
        score += 8
    elif hires >= 5:
        score += 5

    # Proposal count (10 pts — lower is better)
    proposals = job.get("proposals", "") or ""
    if "10 to 15" in proposals or "5 to 10" in proposals:
        score += 10
    elif "20 to 50" in proposals:
        score += 5
    elif "50+" in proposals:
        score += 2
    elif not proposals:
        score += 8

    # Recency (10 pts)
    posted = (job.get("posted") or "").lower()
    age_days = parse_posted_age(posted)
    if age_days is not None:
        if age_days <= 0:
            score += 10
        elif age_days <= 1:
            score += 8
        elif age_days <= 3:
            score += 6
        elif age_days <= 7:
            score += 4
        elif age_days <= 14:
            score += 2
        # >14 days: 0 pts
    else:
        # Unparseable — assume old, no points
        pass

    # Description quality (5 pts)
    desc = job.get("description", "") or ""
    if len(desc) > 500:
        score += 5
    elif len(desc) > 200:
        score += 3

    return score


def _parse_spend(spend: str) -> float:
    """Parse spend string like '$1.9K' or '$580K' to float."""
    s = spend.replace("$", "").strip()
    if "M" in s:
        return float(s.replace("M", "")) * 1_000_000
    if "K" in s:
        return float(s.replace("K", "")) * 1_000
    try:
        return float(s)
    except ValueError:
        return 0.0


# ── Job Loading ──────────────────────────────────────────────────────────

def load_jobs(output_dir: str | Path = "/var/www/upwork-scraper-fs/output") -> list[dict[str, Any]]:
    """Load all jobs from upwork_*.json files, deduplicating by URL."""
    path = Path(output_dir)
    seen_urls: set[str] = set()
    jobs: list[dict[str, Any]] = []

    for f in sorted(path.glob("upwork_*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        for job in data.get("jobs", []):
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                job["_source_file"] = f.name
                job["_query"] = data.get("query", "")
                job["_score"] = score_job(job)
                jobs.append(job)

    return jobs


# ── Display ──────────────────────────────────────────────────────────────

def _score_label(score: int) -> str:
    if score >= 80:
        return "🔥 HOT"
    if score >= 60:
        return "👍 WARM"
    if score >= 40:
        return "👎 LUKEWARM"
    return "❌ SKIP"


def print_job(job: dict[str, Any], index: int = 0) -> None:
    """Print a single job summary."""
    score = job.get("_score", 0)
    label = _score_label(score)
    title = job.get("title", "?")[:80]
    rate = job.get("hourly_rate") or job.get("budget") or "?"
    skills = ", ".join(job.get("skills", [])[:4]) or "?"
    spend = job.get("client_spent") or "?"
    hires = job.get("client_hires") or "?"
    proposals = job.get("proposals") or "?"
    posted = job.get("posted") or "?"
    desc = (job.get("description") or "")[:100].replace("\n", " ")

    prefix = f"  {index}. " if index else ""
    print(f"{prefix}{label} ({score}/100) — {title}")
    print(f"     Rate: {rate} | Skills: {skills}")
    print(f"     Client: ${spend} spent, {hires} hires | Proposals: {proposals} | Posted: {posted}")
    if desc:
        print(f"     {desc}...")
    print()


# ── Proposal Generation ─────────────────────────────────────────────────

def generate_proposal(job: dict[str, Any]) -> str:
    """Generate a proposal for a job based on its type and your portfolio."""
    title = job.get("title", "this project")
    skills = [s.lower() for s in job.get("skills", [])]
    desc = job.get("description", "") or ""

    # Determine job category
    is_wp = any("wordpress" in s for s in skills)
    is_python = any("python" in s for s in skills)
    is_golang = any("golang" in s or "go " in s for s in skills)
    is_audit = any(w in desc.lower() for w in ["audit", "review", "fix", "bug", "issue"])

    # Extract a specific problem from the description
    problem = _extract_problem(desc, title)

    if is_wp and is_audit:
        return _proposal_wp_fix(title, problem)
    if is_wp:
        return _proposal_wp_theme(title, problem)
    if is_python:
        return _proposal_python(title, problem)
    if is_golang:
        return _proposal_golang(title, problem)
    return _proposal_generic(title, problem)


def _extract_problem(desc: str, title: str) -> str:
    """Extract a specific problem statement from the description."""
    # Look for sentences that describe the core problem
    sentences = re.split(r'(?<=[.!?])\s+', desc)
    for s in sentences[:5]:
        if any(w in s.lower() for w in ["need", "want", "looking", "problem", "issue", "fix", "build", "create", "develop"]):
            return s[:150]
    return title


def _proposal_wp_fix(title: str, problem: str) -> str:
    return f"""Subject: WordPress Fix — {title[:60]}

Hi there,

I read about your issue with {problem[:100].lower()}. I've dealt with this exact type of problem before — I maintain several production WordPress sites and know the common failure points.

Here's what I'd do:
1. Diagnose the root cause (check logs, test configurations)
2. Fix the immediate issue
3. Verify everything works end-to-end
4. Document what was changed so you can maintain it

I've built production WordPress sites including sandovallandscaping.com and groundhogstx.com — both custom Sage themes running in production today.

This looks like a quick fix. Happy to start with a diagnostic call to confirm the scope.

Best,
Maxx"""


def _proposal_wp_theme(title: str, problem: str) -> str:
    return f"""Subject: WordPress Developer — {title[:60]}

Hi there,

I read your post about {problem[:100].lower()}. I specialize in custom WordPress development — I build production sites with Sage, ACF, and Tailwind, no page builders.

Relevant experience:
- sandovallandscaping.com — custom Sage theme from design mockups
- groundhogstx.com — custom theme with brand implementation

My approach:
1. Set up a custom theme matching your exact design
2. Build ACF blocks for structured content
3. Ensure Gutenberg compatibility for easy editing
4. Optimize for performance (PageSpeed 75+)

I prefer to start with a small proof of concept — the most complex page or component — to make sure we're aligned before committing to the full build.

Happy to discuss your specific requirements.

Best,
Maxx"""


def _proposal_python(title: str, problem: str) -> str:
    return f"""Subject: Python Developer — {title[:60]}

Hi there,

I read your post about {problem[:100].lower()}. I build production Python applications — data pipelines, scrapers, APIs, and automation tools.

Relevant experience:
- Production web scraper handling Cloudflare + JS-rendered pages with proxy rotation
- Data processing pipelines for business intelligence

My approach:
1. Start with a working MVP for the core use case
2. Add error handling and edge cases
3. Document and hand off with clear instructions

I prefer to start small and iterate based on what actually works. Happy to discuss your specific needs.

Best,
Maxx"""


def _proposal_golang(title: str, problem: str) -> str:
    return f"""Subject: Golang Developer — {title[:60]}

Hi there,

I read your post about {problem[:100].lower()}. I build production systems in Go — APIs, CLIs, and backend services.

My approach to this type of work:
1. Start with a clear audit of the existing codebase
2. Identify the critical issues and prioritize fixes
3. Build incrementally with tests at each step

I prefer to start with a small, well-defined scope and prove the approach works before expanding.

Happy to discuss your specific requirements.

Best,
Maxx"""


def _proposal_generic(title: str, problem: str) -> str:
    return f"""Subject: {title[:60]}

Hi there,

I read your post about {problem[:100].lower()}. I build production software across the full stack — WordPress, Python, Go, and frontend applications.

My approach:
1. Understand the core problem before writing any code
2. Build a minimal working version first
3. Iterate based on real feedback

I prefer to start small and prove value before scaling up. Happy to discuss your specific needs.

Best,
Maxx"""


# ── Structured Proposal Output ──────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _slugify(value: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return (slug or "proposal")[:max_len].strip("-")


def _stable_job_id(job: dict[str, Any]) -> str:
    """Return a stable ID for a job, preferring the Upwork URL."""
    source = job.get("url") or f"{job.get('title', '')}:{job.get('description', '')[:160]}"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    upwork_match = re.search(r"~[0-9a-fA-F]+", source)
    if upwork_match:
        return upwork_match.group(0).lstrip("~")
    return digest


def _split_subject_body(proposal_text: str, fallback_title: str) -> tuple[str, str]:
    """Extract the subject line from generated proposal text."""
    lines = proposal_text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).lstrip()
        return subject, body
    return fallback_title[:80], proposal_text


def _match_portfolio_references(job: dict[str, Any]) -> list[dict[str, str]]:
    skills_text = " ".join(job.get("skills", [])).lower()
    haystack = f"{job.get('title', '')} {job.get('description', '')} {skills_text}".lower()
    matches: list[dict[str, str]] = []
    for ref in PORTFOLIO_REFERENCES:
        if any(keyword in haystack for keyword in ref["keywords"]):
            matches.append({
                "title": ref["title"],
                "url": ref["url"],
                "description": ref["description"],
            })
    return matches[:3]


def _score_reasoning(job: dict[str, Any]) -> list[str]:
    """Generate concise human/machine-readable reasons for a job score."""
    reasons: list[str] = []
    score = int(job.get("_score", 0))
    rate = job.get("hourly_rate") or job.get("budget") or ""
    skills = [s.lower() for s in job.get("skills", [])]
    matching_skills = sorted({k for k in PORTFOLIO_KEYWORDS if any(k in s for s in skills)})
    spend = job.get("client_spent") or ""
    hires = job.get("client_hires")
    posted = job.get("posted") or ""
    proposals = job.get("proposals") or ""

    reasons.append(f"Overall score is {score}/100 ({_score_label(score)}).")
    if rate:
        reasons.append(f"Rate/budget signal: {rate}.")
    if matching_skills:
        reasons.append(f"Portfolio skill matches: {', '.join(matching_skills[:8])}.")
    if spend:
        reasons.append(f"Client spend signal: {spend}.")
    if hires:
        reasons.append(f"Client hire history: {hires} hires.")
    if proposals:
        reasons.append(f"Competition signal: {proposals} proposals.")
    if posted:
        age = parse_posted_age(posted)
        if age is None:
            reasons.append(f"Recency signal: {posted}.")
        else:
            reasons.append(f"Recency signal: approximately {age} day(s) old.")
    return reasons


def _fit_assessment(score: int) -> str:
    if score >= 80:
        return "hot"
    if score >= 60:
        return "ready"
    if score >= 40:
        return "review"
    return "skip"


def _contract_type(job: dict[str, Any]) -> str:
    if job.get("hourly_rate"):
        return "hourly"
    if job.get("budget"):
        return "fixed"
    return ""


def build_structured_proposal(
    job: dict[str, Any],
    proposal_text: str,
    *,
    status: str = "ready",
) -> dict[str, Any]:
    """Build the self-contained JSON proposal document consumed by UpWork Buddy."""
    now = _now_iso()
    score = int(job.get("_score", 0))
    subject, body = _split_subject_body(proposal_text, job.get("title", "UpWork Proposal"))
    references = _match_portfolio_references(job)
    job_id = _stable_job_id(job)

    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "id": job_id,
        "source": {
            "system": "upwork-scraper-fs",
            "source_file": job.get("_source_file"),
            "query": job.get("_query"),
        },
        "job": {
            "id": job_id,
            "title": job.get("title", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "contract_type": _contract_type(job),
            "budget": job.get("budget") or "",
            "hourly_rate": job.get("hourly_rate") or "",
            "rate_range": job.get("hourly_rate") or "",
            "experience_level": job.get("experience_level") or "",
            "duration": job.get("duration") or "",
            "skills": job.get("skills", []),
            "posted": job.get("posted") or "",
            "proposals": job.get("proposals") or "",
        },
        "client": {
            "country": job.get("country") or "",
            "rating": job.get("client_rating"),
            "reviews": job.get("client_reviews"),
            "hires": job.get("client_hires"),
            "spent": job.get("client_spent") or "",
        },
        "analysis": {
            "score": score,
            "label": _score_label(score),
            "fit": _fit_assessment(score),
            "reasoning": _score_reasoning(job),
        },
        "proposal": {
            "subject": subject,
            "body": body,
            "full_text": proposal_text,
            "tone": "professional, concise, technical",
        },
        "portfolio_references": references,
        "status": status,
        "timestamps": {
            "created_at": now,
            "updated_at": now,
            "submitted_at": None,
            "rejected_at": None,
        },
    }


def proposal_to_markdown(payload: dict[str, Any]) -> str:
    """Render a structured proposal payload as human-readable Markdown."""
    job = payload["job"]
    analysis = payload["analysis"]
    client = payload["client"]
    proposal = payload["proposal"]
    refs = payload.get("portfolio_references", [])

    refs_md = "\n".join(
        f"- **{ref['title']}**{' — ' + ref['url'] if ref.get('url') else ''}: {ref['description']}"
        for ref in refs
    ) or "- None matched"

    reasoning_md = "\n".join(f"- {reason}" for reason in analysis.get("reasoning", []))

    return f"""# {job.get("title") or "UpWork Proposal"}

**Status:** {payload.get("status", "ready")}
**Score:** {analysis.get("score")}/100 — {analysis.get("label")}
**Fit:** {analysis.get("fit")}
**Rate/Budget:** {job.get("rate_range") or job.get("budget") or "Not specified"}
**Client:** {client.get("spent") or "Unknown"} spent, {client.get("hires") or "?"} hires
**Posted:** {job.get("posted") or "Unknown"}
**URL:** {job.get("url") or "Unknown"}

## Subject

{proposal.get("subject", "")}

## Cover Letter

{proposal.get("body", "")}

## Portfolio References Used

{refs_md}

## Score Reasoning

{reasoning_md}

## Machine JSON

```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```
"""


def write_proposal_files(payload: dict[str, Any], proposal_dir: str | Path) -> tuple[Path, Path]:
    """Write both Markdown and JSON proposal files."""
    out_dir = Path(proposal_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    score = payload["analysis"]["score"]
    slug = _slugify(payload["job"]["title"])
    proposal_id = payload["id"]
    base = f"{score:03d}-{slug}-{proposal_id}"
    md_path = out_dir / f"{base}.md"
    json_path = out_dir / f"{base}.json"
    md_path.write_text(proposal_to_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path


def proposal_to_buddy_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Map the structured proposal JSON to UpWork Buddy's /api/jobs payload."""
    job = payload["job"]
    proposal = payload["proposal"]
    analysis = payload["analysis"]
    client = payload["client"]

    skills = job.get("skills") or []
    skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
    budget = job.get("rate_range") or job.get("budget") or job.get("hourly_rate") or ""

    return {
        "job_title": job.get("title", ""),
        "job_description": job.get("description", ""),
        "url": job.get("url", ""),
        "job_url": job.get("url", ""),
        "source": "upwork-scraper-fs",
        "status": payload.get("status", "ready"),
        "contract_type": job.get("contract_type", ""),
        "budget": budget,
        "rate_range": job.get("rate_range") or job.get("hourly_rate") or "",
        "rate_min": "",
        "rate_max": "",
        "budget_amount": job.get("budget") or "",
        "experience_level": job.get("experience_level", ""),
        "skills": skills_text,
        "proposal": proposal.get("full_text") or proposal.get("body") or "",
        "proposal_subject": proposal.get("subject", ""),
        "proposal_tone": proposal.get("tone", ""),
        "proposal_json": json.dumps(payload, ensure_ascii=False),
        "score": analysis.get("score", 0),
        "score_reasoning": "\n".join(analysis.get("reasoning", [])),
        "fit_assessment": analysis.get("fit", ""),
        "portfolio_references": json.dumps(payload.get("portfolio_references", []), ensure_ascii=False),
        "time_estimate": "",
        "execution_prompt": f"Fit: {analysis.get('fit', '')}. Client: {client.get('spent') or 'unknown'} spent.",
        "tone_analysis": proposal.get("tone", ""),
    }


def push_to_buddy(
    payload: dict[str, Any],
    *,
    buddy_url: str,
    token: str | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    """POST one structured proposal to UpWork Buddy."""
    endpoint = buddy_url.rstrip("/") + "/api/jobs"
    body = json.dumps(proposal_to_buddy_job(payload)).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_body = resp.read().decode("utf-8")
            if not response_body:
                return {"status": resp.status}
            return json.loads(response_body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"UpWork Buddy returned HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach UpWork Buddy at {endpoint}: {exc.reason}") from exc


# ── CLI ──────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="UpWork Proposal Engine — score jobs, generate proposals",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Only score jobs, don't generate proposals",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Score + generate proposals for top jobs",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Show only top N jobs (default: all)",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Filter by search query (e.g., 'wordpress')",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=40,
        help="Minimum score to include (default: 40)",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=21,
        help="Maximum age in days for a job to be considered (default: 21, 0=no filter)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/var/www/upwork-scraper-fs/output",
        help="Directory with upwork_*.json files",
    )
    parser.add_argument(
        "--proposal-dir",
        type=str,
        default="/var/www/upwork-scraper-fs/proposals",
        help="Directory to write structured proposal files (JSON + Markdown)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push structured proposals to UpWork Buddy API",
    )
    parser.add_argument(
        "--buddy-url",
        type=str,
        default="http://localhost:8080",
        help="UpWork Buddy base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Bearer token for UpWork Buddy API auth",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)

    jobs = load_jobs(args.output_dir)
    if not jobs:
        print("No jobs found. Run the scraper first:")
        print("  cd /var/www/upwork-scraper-fs && uv run python -m src.main --query 'wordpress developer' --with-details")
        return 1

    # Filter by query
    if args.query:
        q = args.query.lower()
        jobs = [j for j in jobs if q in j.get("title", "").lower() or q in j.get("_query", "").lower()]

    # Sort by score descending
    jobs.sort(key=lambda j: j.get("_score", 0), reverse=True)

    # Filter by min score
    jobs = [j for j in jobs if j.get("_score", 0) >= args.min_score]

    # Filter by max age (default 21 days = 3 weeks)
    if args.max_age > 0:
        before = len(jobs)
        jobs = [
            j for j in jobs
            if (age := parse_posted_age(j.get("posted"))) is None or age <= args.max_age
        ]
        filtered = before - len(jobs)
        if filtered:
            print(f"   🗑️ Filtered {filtered} jobs older than {args.max_age} days")

    # Limit
    if args.top > 0:
        jobs = jobs[:args.top]

    if not jobs:
        print("No jobs meet the minimum score threshold.")
        return 0

    # Print summary
    hot = sum(1 for j in jobs if j.get("_score", 0) >= 80)
    warm = sum(1 for j in jobs if 60 <= j.get("_score", 0) < 80)
    lukewarm = sum(1 for j in jobs if 40 <= j.get("_score", 0) < 60)

    print(f"\n📊 Job Analysis — {len(jobs)} jobs")
    print(f"   🔥 Hot: {hot} | 👍 Warm: {warm} | 👎 Lukewarm: {lukewarm}")
    print()

    for i, job in enumerate(jobs, 1):
        print_job(job, i)

        if args.generate and job.get("_score", 0) >= 60:
            proposal_text = generate_proposal(job)
            print("   ── Proposal ──")
            print(proposal_text)
            print()

            # Build structured proposal (JSON + Markdown)
            payload = build_structured_proposal(job, proposal_text)
            md_path, json_path = write_proposal_files(payload, args.proposal_dir)
            print(f"   📄 Markdown: {md_path}")
            print(f"   📄 JSON:     {json_path}")

            if args.push:
                try:
                    result = push_to_buddy(payload, buddy_url=args.buddy_url, token=args.token)
                    print(f"   📤 Pushed to UpWork Buddy: id={result.get('id', '?')}")
                except RuntimeError as e:
                    print(f"   ❌ Push failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
