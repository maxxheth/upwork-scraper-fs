"""Output serialization for scraped job data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.models import SearchResult, UpWorkJob

logger = logging.getLogger(__name__)


def save_jobs(
    jobs: list[UpWorkJob],
    output_dir: str | Path,
    query: str = "search",
    page: int = 1,
) -> Path:
    """Save job listings to a JSON file.

    Returns the path to the saved file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")  # noqa: UP017
    safe_query = query.replace(" ", "_").replace('"', "")[:40]
    filename = f"upwork_{safe_query}_p{page}_{timestamp}.json"

    result = SearchResult(
        query=query,
        total_jobs=len(jobs),
        jobs=jobs,
        page=page,
    )

    filepath = output_path / filename
    with open(filepath, "w") as f:
        json.dump(_to_dict(result), f, indent=2, default=str)

    logger.info("Saved %d jobs to %s", len(jobs), filepath)
    return filepath


def _to_dict(obj: object) -> object:
    """Convert dataclass to dict recursively."""
    if isinstance(obj, (UpWorkJob, SearchResult)):
        return {k: _to_dict(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj
