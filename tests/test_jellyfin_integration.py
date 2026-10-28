"""Tests for the optional Jellyfin hand-off.

The behaviour that matters here is restraint: the integration must stay silent
when unconfigured, and must never let a media server's problems surface as a
download failure. It must also actually authenticate: Jellyfin 12.4 rejects the
legacy ``X-Emby-Token`` header, so the modern ``Authorization: MediaBrowser``
scheme is used, with the legacy header kept only as a fallback.
"""

from types import SimpleNamespace
from unittest.mock import patch

import requests

from app.integrations_utils import (
    JELLYFIN_AUTH_HEADER,
    JELLYFIN_AUTHORIZATION_HEADER,
    JELLYFIN_TIMEOUT_SECONDS,
    _jellyfin_authorization_value,
    jellyfin_is_configured,
    post_download_actions,
    trigger_jellyfin_library_scan,
)


def _settings(base_url="", api_key=""):
    return SimpleNamespace(JELLYFIN_BASE_URL=base_url, JELLYFIN_API_KEY=api_key)


def _resp(status_code):
    """A minimal stand-in for a requests.Response (only status_code is read)."""
    return SimpleNamespace(status_code=status_code)


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
    def test_posts_to_the_refresh_endpoint_with_the_mediabrowser_header(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post", return_value=_resp(204)
            ) as post:
                assert trigger_jellyfin_library_scan() is True

        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        assert url == "https://jellyfin.local:8096/Library/Refresh"
        # Modern auth: the key rides in the Authorization header, MediaBrowser
        # scheme — not the legacy X-Emby-Token that Jellyfin 12.4 rejects.
        assert kwargs["headers"] == {
            JELLYFIN_AUTHORIZATION_HEADER: 'MediaBrowser Token="secret"'
        }
        assert kwargs["timeout"] == JELLYFIN_TIMEOUT_SECONDS
        assert "secret" not in url, "the token must not travel in the URL"
        # A single request is enough when the server accepts the first header.
        assert post.call_count == 1

    def test_authorization_value_format(self):
        assert _jellyfin_authorization_value("abc") == 'MediaBrowser Token="abc"'

    def test_falls_back_to_legacy_header_on_auth_rejection(self):
        # Server refuses the modern header (401) but accepts the legacy one.
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post",
                side_effect=[_resp(401), _resp(204)],
            ) as post:
                assert trigger_jellyfin_library_scan() is True

        assert post.call_count == 2
        assert post.call_args_list[1].kwargs["headers"] == {
            JELLYFIN_AUTH_HEADER: "secret"
        }

    def test_trailing_slash_does_not_double_up(self):
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096/", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post", return_value=_resp(204)
            ) as post:
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

    def test_a_persistent_auth_failure_is_logged_not_raised(self):
        # Both the modern and the legacy header are refused: log the status once.
        logged = []
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "bad-key"),
        ):
            with patch(
                "app.integrations_utils.requests.post",
                side_effect=[_resp(401), _resp(401)],
            ):
                assert trigger_jellyfin_library_scan(logged.append) is False

        assert any("401" in line for line in logged)
        assert any("Jellyfin" in line for line in logged)

    def test_a_non_auth_error_is_not_retried(self):
        # A 404 will not change with a different header, so there is one call.
        logged = []
        with patch(
            "app.integrations_utils.get_settings",
            return_value=_settings("https://jellyfin.local:8096", "secret"),
        ):
            with patch(
                "app.integrations_utils.requests.post", return_value=_resp(404)
            ) as post:
                assert trigger_jellyfin_library_scan(logged.append) is False

        assert post.call_count == 1
        assert any("404" in line for line in logged)


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
            with patch("app.integrations_utils.requests.post", return_value=_resp(204)):
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
