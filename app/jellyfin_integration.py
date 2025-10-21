"""
Utilities for interacting with a Jellyfin server.

Provides helper functions to trigger a library scan after downloads complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import requests


DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class JellyfinScanResult:
    """Result of a Jellyfin library refresh attempt."""

    success: bool
    message: str
    status_code: Optional[int] = None


def _normalize_base_url(base_url: str) -> str:
    """Ensure the Jellyfin base URL does not end with a trailing slash."""
    return base_url.rstrip("/") if base_url else base_url


def trigger_jellyfin_library_scan(
    base_url: str,
    api_key: str,
    session: Optional[requests.Session] = None,
    log: Optional[Callable[[str], None]] = None,
) -> JellyfinScanResult:
    """
    Trigger a Jellyfin library scan (all libraries).

    Args:
        base_url: Base URL of the Jellyfin server (e.g., https://jellyfin.local:8096).
        api_key: Jellyfin API key (X-Emby-Token).
        session: Optional pre-configured requests Session (helps testing).
        log: Optional callable used for diagnostic logging.

    Returns:
        JellyfinScanResult indicating success or failure.
    """
    if not base_url or not api_key:
        return JellyfinScanResult(
            success=False,
            message="Missing Jellyfin base URL or API key.",
        )

    logger = log or (lambda _: None)
    client = session or requests.Session()
    normalized_url = _normalize_base_url(base_url)
    headers = {
        "X-Emby-Token": api_key.strip(),
    }

    refresh_endpoint = f"{normalized_url}/Library/Refresh"
    try:
        logger(f"POST {refresh_endpoint} (full library scan)")
        response = client.post(
            refresh_endpoint,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        error_message = f"Jellyfin refresh request failed: {exc}"
        logger(error_message)
        return JellyfinScanResult(
            success=False,
            message=error_message,
        )

    if 200 <= response.status_code < 300:
        return JellyfinScanResult(
            success=True,
            message="Jellyfin library refresh triggered successfully.",
            status_code=response.status_code,
        )

    try:
        response_text = response.text.strip()
    except Exception:  # noqa: broad-except
        response_text = ""

    failure_message = (
        f"Jellyfin refresh failed with status {response.status_code}. {response_text}"
    ).strip()
    logger(failure_message)
    return JellyfinScanResult(
        success=False,
        message=failure_message,
        status_code=response.status_code,
    )
