"""
Tests for Jellyfin integration helpers.
"""

import os
from typing import Any, Dict

import pytest

from app.integrations_utils import trigger_jellyfin_library_scan


pytestmark = pytest.mark.skipif(
    not (os.getenv("JELLYFIN_BASE_URL") and os.getenv("JELLYFIN_API_KEY")),
    reason="Jellyfin integration not configured",
)


class DummyResponse:
    """Minimal response object to emulate requests.Response."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class DummySession:
    """Simple session stub capturing POST calls."""

    def __init__(self, post_response: DummyResponse):
        self._post_response = post_response
        self.post_kwargs: Dict[str, Any] = {}

    def post(self, url: str, **kwargs: Any) -> DummyResponse:
        self.post_kwargs = {"url": url, **kwargs}
        return self._post_response


def test_trigger_scan_successful():
    session = DummySession(DummyResponse(status_code=204))
    logs = []

    result = trigger_jellyfin_library_scan(
        base_url="https://media.local:8096",
        api_key="token",
        session=session,
        log=logs.append,
    )

    assert result.success is True
    assert session.post_kwargs["url"].endswith("/Library/Refresh")
    headers = session.post_kwargs["headers"]
    assert headers["X-Emby-Token"] == "token"
    assert "full library scan" in logs[0]


def test_trigger_scan_missing_config():
    result = trigger_jellyfin_library_scan(base_url="", api_key="")
    assert result.success is False
    assert "Missing Jellyfin" in result.message


def test_trigger_scan_http_error():
    session = DummySession(DummyResponse(status_code=500, text="Server error"))

    result = trigger_jellyfin_library_scan(
        base_url="https://media.local",
        api_key="token",
        session=session,
    )

    assert result.success is False
    assert result.status_code == 500
    assert "failed" in result.message.lower()
