"""Common transport adapter package for UpWork scraping backends."""

from __future__ import annotations

from typing import Any

from src.adapters.base import FetchRequest, FetchResponse, TransportAdapter
from src.adapters.flaresolverr_adapter import FlareSolverrAdapter
from src.adapters.stealthy_adapter import StealthySessionAdapter
from src.config import load_proxies
from src.config_schema import TransportConfig

__all__ = [
    "FetchRequest",
    "FetchResponse",
    "FlareSolverrAdapter",
    "StealthySessionAdapter",
    "TransportAdapter",
    "create_adapter",
]


def create_adapter(
    transport_config: TransportConfig,
    base_env_config: dict[str, Any] | None = None,
) -> TransportAdapter:
    """Factory creating the appropriate TransportAdapter instance from configuration."""
    env = base_env_config or {}

    if transport_config.adapter == "flaresolverr":
        flaresolverr_url = str(env.get("flaresolverr_url") or "http://localhost:8193")
        proxy_file = env.get("proxy_file")
        proxies: list[str] = load_proxies(str(proxy_file)) if proxy_file else []

        return FlareSolverrAdapter(
            base_url=flaresolverr_url,
            proxies=proxies,
            proxy_mode=transport_config.proxy_mode,
            proxy_index=transport_config.proxy_index,
            proxy_url=transport_config.proxy_url,
            max_timeout_ms=transport_config.max_timeout_ms,
            max_retries=transport_config.max_retries,
            retry_backoff_seconds=transport_config.retry_backoff_seconds,
        )

    if transport_config.adapter == "stealthy_session":
        user_data_dir = env.get("user_data_dir") or "./.session/chrome_profile"
        storage_state_file = env.get("storage_state_file") or "./.session/storage_state.json"
        proxy_file = env.get("proxy_file")
        cdp_url = env.get("cdp_url")

        return StealthySessionAdapter(
            user_data_dir=str(user_data_dir),
            storage_state_file=str(storage_state_file),
            proxy_file=proxy_file,
            proxy_mode=transport_config.proxy_mode,
            proxy_index=transport_config.proxy_index,
            proxy_url=transport_config.proxy_url or env.get("session_proxy_url"),
            cdp_url=str(cdp_url) if cdp_url else None,
            max_timeout_ms=transport_config.max_timeout_ms,
            max_retries=transport_config.max_retries,
            retry_backoff_seconds=transport_config.retry_backoff_seconds,
        )

    raise ValueError(f"Unknown transport adapter: {transport_config.adapter}")
