"""FlareSolverr transport adapter supporting proxy rotation, sticky pinned proxies, and direct connections."""

from __future__ import annotations

import logging
import time
from typing import Literal

from src.adapters.base import FetchRequest, FetchResponse
from src.flaresolverr_client import FlareSolverrClient

logger = logging.getLogger(__name__)


class FlareSolverrAdapter:
    """Transport adapter delegating requests to a FlareSolverr daemon."""

    adapter_name: str = "flaresolverr"

    def __init__(
        self,
        base_url: str = "http://localhost:8193",
        proxies: list[str] | None = None,
        proxy_mode: Literal["rotation", "pinned", "direct"] = "rotation",
        proxy_index: int = 0,
        proxy_url: str | None = None,
        max_timeout_ms: int = 60000,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        self.proxy_mode = proxy_mode
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_timeout_ms = max_timeout_ms

        client_proxies = proxies or []
        if proxy_mode == "direct":
            client_proxies = []

        self.client = FlareSolverrClient(
            base_url=base_url,
            proxies=client_proxies,
            max_timeout=max_timeout_ms,
        )

        self._pinned_proxy: str | None = None
        if proxy_mode == "pinned":
            if proxy_url:
                self._pinned_proxy = proxy_url
            elif client_proxies and 0 <= proxy_index < len(client_proxies):
                self._pinned_proxy = client_proxies[proxy_index]
            else:
                logger.warning(
                    "Pinned proxy requested but index %d invalid for %d proxies; falling back to direct",
                    proxy_index,
                    len(client_proxies),
                )

    def fetch(self, request: FetchRequest) -> FetchResponse:
        """Execute request with retries and return normalized FetchResponse."""
        start_time = time.time()
        last_error: str | None = None
        last_status: int = 0

        effective_retries = (
            request.max_retries if request.max_retries is not None else self.max_retries
        )
        if request.timeout_ms and request.timeout_ms != self.client.max_timeout:
            self.client.max_timeout = request.timeout_ms

        for attempt in range(1, effective_retries + 1):
            try:
                if self.proxy_mode == "rotation":
                    fs_resp = self.client.request_with_rotation(
                        url=request.url,
                        return_raw_html=request.return_raw_html,
                    )
                elif self.proxy_mode == "pinned":
                    fs_resp = self.client.request(
                        url=request.url,
                        proxy_url=self._pinned_proxy,
                        return_raw_html=request.return_raw_html,
                    )
                else:  # direct
                    fs_resp = self.client.request(
                        url=request.url,
                        proxy_url=None,
                        return_raw_html=request.return_raw_html,
                    )

                last_status = fs_resp.status
                if fs_resp.error:
                    last_error = fs_resp.error
                    logger.warning(
                        "[%s] Attempt %d/%d failed for %s: %s",
                        self.adapter_name,
                        attempt,
                        effective_retries,
                        request.url,
                        fs_resp.error,
                    )
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue

                if fs_resp.status != 200:
                    last_error = f"HTTP {fs_resp.status}"
                    logger.warning(
                        "[%s] Attempt %d/%d HTTP %d for %s",
                        self.adapter_name,
                        attempt,
                        effective_retries,
                        fs_resp.status,
                        request.url,
                    )
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue

                elapsed = time.time() - start_time
                return FetchResponse(
                    url=request.url,
                    status=fs_resp.status,
                    html=fs_resp.html,
                    error=None,
                    session_id=fs_resp.session_id,
                    cookies=fs_resp.cookies,
                    elapsed_seconds=elapsed,
                    adapter_name=self.adapter_name,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "[%s] Attempt %d/%d exception for %s: %s",
                    self.adapter_name,
                    attempt,
                    effective_retries,
                    request.url,
                    e,
                )
                time.sleep(self.retry_backoff_seconds * attempt)

        elapsed = time.time() - start_time
        return FetchResponse(
            url=request.url,
            status=last_status,
            html="",
            error=last_error or "All fetch attempts failed",
            elapsed_seconds=elapsed,
            adapter_name=self.adapter_name,
        )

    def close(self) -> None:
        """Tear down FlareSolverr sessions and close HTTP client."""
        self.client.close()
