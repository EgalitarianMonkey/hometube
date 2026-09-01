"""Tests for the optional Jellyfin hand-off.

The behaviour that matters here is restraint: the integration must stay silent
when unconfigured, and must never let a media server's problems surface as a
download failure.
"""

from types import SimpleNamespace
from unittest.mock import patch

import requests

from app.integrations_utils import (
    JELLYFIN_AUTH_HEADER,
    JELLYFIN_TIMEOUT_SECONDS,
    jellyfin_is_configured,
    post_download_actions,
    trigger_jellyfin_library_scan,
)


def _settings(base_url="", api_key=""):
    return SimpleNamespace(JELLYFIN_BASE_URL=base_url, JELLYFIN_API_KEY=api_key)


class TestConfigurationDetection:
    def test_needs_both_url_and_key(self):
        cases = {
            ("", ""): False,
            ("https://jellyfin.local:8096", ""): False,
            ("", "key"): False,
            ("https://jellyfin.local:8096", "key"): True,
        }
        for (url, key), expected in cases.items():
            with patch(
                "app.integrations_utils.get_settings",
                return_value=_settings(url, key),
            ):
                assert jellyfin_is_configured() is expected, (url, key)

    def test_whitespace_only_is_not_configuration(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("   ", "  "),
        ):
            assert jellyfin_is_configured() is False


class TestLibraryScan:
    def test_posts_to_the_refresh_endpoint_with_the_token_in_a_header(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch("app.integrations_utils.requests.post") as post:
                assert trigger_jellyfin_library_scan() is True

        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        assert url == "https://jellyfin.local:8096/Library/Refresh"
        assert kwargs["headers"] == {JELLYFIN_AUTH_HEADER: "secret"}
        assert kwargs["timeout"] == JELLYFIN_TIMEOUT_SECONDS
        assert "secret" not in url, "the token must not travel in the URL"

    def test_trailing_slash_does_not_double_up(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096/", "secret"),
        ):
            with patch("app.integrations_utils.requests.post") as post:
                trigger_jellyfin_library_scan()

        assert post.call_args.args[0] == "https://jellyfin.local:8096/Library/Refresh"

    def test_no_call_at_all_when_unconfigured(self):
        with patch("app.integrations_utils.get_settings", return_value=_settings()):
            with patch("app.integrations_utils.requests.post") as post:
                assert trigger_jellyfin_library_scan() is False

        post.assert_not_called()

    def test_an_unreachable_server_is_logged_not_raised(self):
        logged = []
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post",
                side_effect=requests.ConnectionError("no route to host"),
            ):
                assert trigger_jellyfin_library_scan(logged.append) is False

        assert any("Jellyfin" in line for line in logged)

    def test_an_http_error_is_logged_not_raised(self):
        response = SimpleNamespace(
            raise_for_status=lambda: (_ for _ in ()).throw(
                requests.HTTPError("401 Unauthorized")
            )
        )
        logged = []
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "bad-key"),
        ):
            with patch("app.integrations_utils.requests.post", return_value=response):
                assert trigger_jellyfin_library_scan(logged.append) is False

        assert any("401" in line for line in logged)


class TestPostDownloadActions:
    def test_silent_when_nothing_is_configured(self):
        logged, titles = [], []
        with patch("app.integrations_utils.get_settings", return_value=_settings()):
            with patch("app.integrations_utils.requests.post") as post:
                post_download_actions(logged.append, titles.append)

        post.assert_not_called()
        assert logged == []
        assert titles == [], "no section header for a feature nobody enabled"

    def test_announces_and_runs_when_configured(self):
        logged, titles = [], []
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch("app.integrations_utils.requests.post"):
                post_download_actions(logged.append, titles.append)

        assert titles == ["Post-download actions"]
        assert any("Jellyfin" in line for line in logged)

    def test_a_failing_server_does_not_propagate(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post",
                side_effect=requests.Timeout("timed out"),
            ):
                post_download_actions()  # must not raise
