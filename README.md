# UpWork Scraper (FlareSolverr)

Scrapes UpWork job listings using **FlareSolverr** (headless Chrome) to bypass Cloudflare, with **Decodo ISP proxy rotation** and **Scrapling** for HTML parsing.

## Architecture

```
Decodo proxy pool (10 ports)
        │
        ▼
FlareSolverr (headless Chrome) ──► Renders Nuxt JS ──► Full HTML
        │
        ▼
Scrapling Selector ──► Structured job data ──► JSON output
```

- **FlareSolverr** runs a real Chrome browser that executes JavaScript, so Nuxt SSR content is fully rendered
- **10 Decodo ISP proxies** are rotated round-robin, each pinned to its own FlareSolverr session
- **Scrapling** parses the rendered HTML with CSS selectors
- Sessions persist cookies across requests within the same proxy

## Setup

```bash
# Install deps
uv sync

# Copy env and proxies
cp .env.example .env
# Edit .env if needed
# Copy proxies.txt from the Go project or create your own

# Run
uv run python -m src.main --query "golang developer"
uv run python -m src.main --query "python" --page 2 --verbose
```

## Requirements

- FlareSolverr running on `localhost:8193` (or set `FLARESOLVERR_URL` in `.env`)
- Proxy file at `./proxies.txt` (one `http://user:pass@host:port` per line)

## Linting & Type Checking

```bash
uv run ruff check src/
uv run pyright src/
```
