"""Data models for UpWork job listings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UpWorkJob:
    """A single UpWork job listing."""

    title: str
    url: str
    description: str
    budget: str | None = None
    experience_level: str | None = None
    duration: str | None = None
    hourly_rate: str | None = None
    skills: list[str] = field(default_factory=list)
    posted: str | None = None
    country: str | None = None
    proposals: str | None = None
    proposals_count: int | None = None
    client_rating: float | None = None
    client_reviews: int | None = None
    client_hires: int | None = None
    client_spent: str | None = None
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())  # noqa: UP017
    session_id: str | None = None
    proxy_port: int | None = None


@dataclass
class SearchResult:
    """Results from a search query."""

    query: str
    total_jobs: int | None = None
    jobs: list[UpWorkJob] = field(default_factory=list)
    page: int = 1
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())  # noqa: UP017
