"""FlareSolverr HTTP client — bypass Cloudflare via headless Chrome.

Architecture:
  - Maintains a pool of FlareSolverr sessions, each pinned to a different
    Decodo proxy port for IP rotation.
  - Sessions are created lazily and reused across requests (cookies persist).
  - FlareSolverr runs a real Chrome browser that executes JS, so Nuxt SSR
    content is fully rendered before the response is returned.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# FlareSolverr API endpoints
ENDPOINT_CREATE_SESSION = "/v1"
ENDPOINT_DESTROY_SESSION = "/v1"
ENDPOINT_REQUEST = "/v1"


@dataclass
class FlareSolverrResponse:
    """Parsed response from FlareSolverr."""

    solution: dict[str, Any] | None = None
    status: int = 0
    error: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    html: str = ""
    session_id: str | None = None


class FlareSolverrClient:
    """Client for FlareSolverr API with proxy rotation."""

    def __init__(
        self,
        base_url: str = "http://localhost:8193",
        proxies: list[str] | None = None,
        max_timeout: int = 60000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.proxies = proxies or []
        self.max_timeout = max_timeout
        self._sessions: dict[str, str] = {}  # proxy_url -> session_id
        self._http = httpx.Client(timeout=httpx.Timeout(120.0))
        self._next_proxy_idx = 0

    def _get_next_proxy(self) -> str | None:
        """Round-robin proxy selection."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._next_proxy_idx]
        self._next_proxy_idx = (self._next_proxy_idx + 1) % len(self.proxies)
        return proxy

    def _proxy_to_flaresolverr(self, proxy_url: str) -> dict[str, str]:
        """Convert a proxy URL to FlareSolverr's proxy format.

        FlareSolverr expects:
          {
            "url": "http://isp.decodo.com:10001",
            "username": "sp98ilsn7j",
            "password": "..."
          }
        """
        # Parse http://user:pass@host:port
        rest = proxy_url
        if rest.startswith("http://"):
            rest = rest[7:]
        elif rest.startswith("https://"):
            rest = rest[8:]

        user_pass, host_port = rest.split("@", 1)
        username, password = user_pass.split(":", 1)

        return {
            "url": f"http://{host_port}",
            "username": username,
            "password": password,
        }

    def create_session(self, proxy_url: str | None = None) -> str:
        """Create a new FlareSolverr session pinned to a proxy.

        Returns the session ID.
        """
        payload: dict[str, Any] = {
            "cmd": "sessions.create",
        }

        if proxy_url:
            payload["proxy"] = self._proxy_to_flaresolverr(proxy_url)

        resp = self._http.post(
            f"{self.base_url}{ENDPOINT_CREATE_SESSION}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            msg = data.get("message", str(data))
            raise RuntimeError(f"FlareSolverr session creation failed: {msg}")

        session_id: str = data["session"]
        logger.info("Created FlareSolverr session %s (proxy=%s)", session_id, proxy_url)
        return session_id

    def destroy_session(self, session_id: str) -> None:
        """Destroy a FlareSolverr session."""
        try:
            self._http.post(
                f"{self.base_url}{ENDPOINT_DESTROY_SESSION}",
                json={
                    "cmd": "sessions.destroy",
                    "session": session_id,
                },
            )
        except Exception:
            logger.warning("Failed to destroy session %s", session_id, exc_info=True)

    def _get_or_create_session(self, proxy_url: str | None) -> str:
        """Get existing session for a proxy, or create one."""
        key = proxy_url or "__direct__"
        if key in self._sessions:
            return self._sessions[key]

        session_id = self.create_session(proxy_url)
        self._sessions[key] = session_id
        return session_id

    def request(
        self,
        url: str,
        session_id: str | None = None,
        proxy_url: str | None = None,
        return_raw_html: bool = False,
    ) -> FlareSolverrResponse:
        """Make a request through FlareSolverr.

        If session_id is provided, uses that session (cookies persist).
        If proxy_url is provided, creates/pins a session to that proxy.
        If neither is provided, uses round-robin proxy from the pool.
        """
        if session_id is None:
            effective_proxy = proxy_url or self._get_next_proxy()
            session_id = self._get_or_create_session(effective_proxy)

        payload: dict[str, Any] = {
            "cmd": "request.get",
            "url": url,
            "session": session_id,
            "maxTimeout": self.max_timeout,
        }

        if return_raw_html:
            payload["returnRawHtml"] = True

        resp = self._http.post(
            f"{self.base_url}{ENDPOINT_REQUEST}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        result = FlareSolverrResponse(session_id=session_id)

        if data.get("status") != "ok":
            result.error = data.get("message", str(data))
            logger.warning("FlareSolverr request failed: %s", result.error)
            return result

        solution = data.get("solution", {})
        result.solution = solution
        result.status = solution.get("status", 0)
        result.cookies = solution.get("cookies", [])
        result.html = solution.get("response", "")

        return result

    def request_with_rotation(
        self,
        url: str,
        return_raw_html: bool = False,
    ) -> FlareSolverrResponse:
        """Make a request using the next proxy in rotation.

        Each call uses a different proxy (round-robin), creating a new
        FlareSolverr session for that proxy if needed.
        """
        proxy = self._get_next_proxy()
        return self.request(url=url, proxy_url=proxy, return_raw_html=return_raw_html)

    def close(self) -> None:
        """Clean up all sessions and HTTP client."""
        for _key, session_id in list(self._sessions.items()):
            with suppress(Exception):
                self.destroy_session(session_id)
        self._sessions.clear()
        self._http.close()
