"""Normalized request/response types and Protocol definition for scraping transport adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class FetchRequest:
    """Normalized request payload for any scraping transport backend."""

    url: str
    wait_selector: str | None = None
    auto_scroll: bool = False
    max_scrolls: int = 4
    scroll_delay_ms: int = 1200
    timeout_ms: int = 60000
    max_retries: int | None = None
    return_raw_html: bool = True


@dataclass
class FetchResponse:
    """Normalized response returned by a TransportAdapter."""

    url: str
    status: int
    html: str
    error: str | None = None
    session_id: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    adapter_name: str = ""

    @property
    def ok(self) -> bool:
        """True if the request completed without an adapter error, HTTP 2xx, and non-empty HTML."""
        return self.error is None and 200 <= self.status < 300 and bool(self.html.strip())


@runtime_checkable
class TransportAdapter(Protocol):
    """Common interface that all scraping transport backends must implement."""

    adapter_name: str

    def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a target URL and return rendered HTML."""
        ...

    def close(self) -> None:
        """Release underlying browser sessions or HTTP clients."""
        ...
