"""Proxy management and session-pinned proxy resolution for UpWork UI Inspector."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from src.config import load_proxies

logger = logging.getLogger(__name__)


def redact_proxy_url(proxy_url: str) -> str:
    """Mask credentials in a proxy URL for safe logging."""
    if not proxy_url:
        return ""
    try:
        parsed = urlparse(proxy_url)
        if parsed.password:
            masked = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                masked += f":{parsed.port}"
            return masked
        if parsed.username:
            masked = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}"
            if parsed.port:
                masked += f":{parsed.port}"
            return masked
        return proxy_url
    except Exception:
        return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", proxy_url)


class PinnedProxyConfig:
    """Encapsulates a sticky proxy for consistent IP session persistence."""

    def __init__(self, proxy_url: str | None = None, proxy_index: int = 0) -> None:
        self.proxy_url = proxy_url
        self.proxy_index = proxy_index

    @property
    def has_proxy(self) -> bool:
        return bool(self.proxy_url)

    def get_display_summary(self) -> str:
        if not self.has_proxy or not self.proxy_url:
            return "Direct (No Proxy)"
        return f"Pinned Proxy [Index {self.proxy_index}]: {redact_proxy_url(self.proxy_url)}"


def resolve_pinned_proxy(
    explicit_proxy: str | None = None,
    proxy_index: int | None = None,
    proxy_file: str | None = None,
    direct: bool = False,
) -> PinnedProxyConfig:
    """Resolve a single sticky proxy URL to maintain consistent session IP.

    If direct is True, no proxy is used.
    """
    if direct:
        return PinnedProxyConfig(proxy_url=None)

    if explicit_proxy:
        return PinnedProxyConfig(proxy_url=explicit_proxy, proxy_index=0)

    # Check proxy file
    resolved_file = proxy_file or "./proxies.txt"
    proxies = load_proxies(resolved_file)
    if not proxies:
        # Check standard CWD
        cwd_proxies = Path.cwd() / "proxies.txt"
        if cwd_proxies.is_file():
            proxies = load_proxies(str(cwd_proxies))

    if proxies:
        idx = proxy_index if proxy_index is not None else 0
        if 0 <= idx < len(proxies):
            chosen = proxies[idx]
            return PinnedProxyConfig(proxy_url=chosen, proxy_index=idx)
        logger.warning(
            "Proxy index %d out of range (total %d). Defaulting to index 0.",
            idx,
            len(proxies),
        )
        return PinnedProxyConfig(proxy_url=proxies[0], proxy_index=0)

    return PinnedProxyConfig(proxy_url=None)
