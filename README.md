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

# Start FlareSolverr container
./flaresolverr.sh start
# Verify readiness: ./flaresolverr.sh status

# Copy env and proxies
cp .env.example .env
# Edit .env if needed
# Copy proxies.txt from the Go project or create your own

# Run
uv run python -m src.main --query "golang developer"
uv run python -m src.main --query "python" --page 2 --verbose
```

## FlareSolverr Management

Manage the container lifecycle via the helper script:

```bash
./flaresolverr.sh start     # Start container (creates if not existing)
./flaresolverr.sh stop      # Stop container
./flaresolverr.sh restart   # Restart container & poll readiness
./flaresolverr.sh status    # Check container state & HTTP health check
./flaresolverr.sh logs -f   # Tail container logs
./flaresolverr.sh rm        # Stop & remove container
```

Overrides can be configured in `.env` or set as environment variables:
- `FLARESOLVERR_PORT` (default: 8193)
- `FLARESOLVERR_CONTAINER_NAME` (default: `flaresolverr`)
- `FLARESOLVERR_IMAGE` (default: `ghcr.io/flaresolverr/flaresolverr:latest`)
- `FLARESOLVERR_LOG_LEVEL` (default: `info`)

## Requirements

- FlareSolverr running on `localhost:8193` (or set `FLARESOLVERR_URL` in `.env`)
- Proxy file at `./proxies.txt` (one `http://user:pass@host:port` per line)

## Linting & Type Checking

```bash
uv run ruff check src/ tests/
uv run pyright src/ tests/
uv run pytest -v
```
