"""Tests for the version-check module.

`app/ytdlp_version_check.py` is live code with no test of its own: it is
imported by `app/main.py` (the sidebar "Check for updates" panel) and by
`app/notifications.py`, which turns `get_latest_hometube_version()` into the
"New version available!" banner every user sees. The existing
`test_ytdlp_version_detection.py` does *not* cover it — that one compares OCI
image labels through crane and only shares a name.

Every lookup here talks to the network or to a subprocess, so each is driven
through the module's own seams: the `TEST_LATEST_*_VERSION` environment
variables it already honours, and patched `requests.get` / `subprocess.run`.
"""

import subprocess
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

import app
from app.ytdlp_version_check import (
    HOMETUBE_GITHUB_REPO,
    STATUS_UNKNOWN,
    STATUS_UP_TO_DATE,
    STATUS_UPDATE_AVAILABLE,
    UNKNOWN_VERSION,
    check_and_show_updates,
    describe_version_status,
    get_current_hometube_version,
    get_current_ytdlp_version,
    get_latest_hometube_version,
    get_latest_ytdlp_version,
)


def fake_response(status_code, payload=None):
    """A requests-like response carrying just what the module reads."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else {}
    return response


@pytest.fixture(autouse=True)
def clear_version_env(monkeypatch):
    """Drop the test seams unless a test sets them itself.

    Both `get_latest_*` functions short-circuit on an environment variable. A
    value inherited from the shell would make the network tests below assert
    nothing at all, silently.
    """
    monkeypatch.delenv("TEST_LATEST_YTDLP_VERSION", raising=False)
    monkeypatch.delenv("TEST_LATEST_HOMETUBE_VERSION", raising=False)


class TestCurrentYtdlpVersion:
    """`yt-dlp --version`, which is absent on a bare development machine."""

    def test_returns_the_trimmed_version(self):
        completed = subprocess.CompletedProcess(
            args=["yt-dlp", "--version"], returncode=0, stdout="2025.09.23\n"
        )

        with patch("app.ytdlp_version_check.subprocess.run", return_value=completed):
            assert get_current_ytdlp_version() == "2025.09.23"

    def test_non_zero_exit_yields_none(self):
        completed = subprocess.CompletedProcess(
            args=["yt-dlp", "--version"], returncode=1, stdout=""
        )

        with patch("app.ytdlp_version_check.subprocess.run", return_value=completed):
            assert get_current_ytdlp_version() is None

    def test_missing_binary_yields_none(self):
        """The common case outside Docker: yt-dlp is simply not installed."""
        with patch(
            "app.ytdlp_version_check.subprocess.run", side_effect=FileNotFoundError
        ):
            assert get_current_ytdlp_version() is None

    def test_timeout_yields_none(self):
        with patch(
            "app.ytdlp_version_check.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="yt-dlp", timeout=10),
        ):
            assert get_current_ytdlp_version() is None


class TestLatestYtdlpVersion:
    """The upstream release lookup against the yt-dlp GitHub API."""

    def test_environment_seam_wins_without_a_request(self, monkeypatch):
        monkeypatch.setenv("TEST_LATEST_YTDLP_VERSION", "2030.01.01")

        with patch("app.ytdlp_version_check.requests.get") as get:
            assert get_latest_ytdlp_version() == "2030.01.01"

        get.assert_not_called()

    def test_strips_the_v_prefix_from_the_tag(self):
        response = fake_response(200, {"tag_name": "v2025.09.23"})

        with patch("app.ytdlp_version_check.requests.get", return_value=response):
            assert get_latest_ytdlp_version() == "2025.09.23"

    def test_error_status_yields_none(self):
        """Rate limiting is the realistic one: the API is called unauthenticated."""
        with patch(
            "app.ytdlp_version_check.requests.get", return_value=fake_response(403)
        ):
            assert get_latest_ytdlp_version() is None

    def test_network_failure_yields_none(self):
        with patch(
            "app.ytdlp_version_check.requests.get",
            side_effect=requests.RequestException("no route to host"),
        ):
            assert get_latest_ytdlp_version() is None


class TestCurrentHometubeVersion:
    """Read from `pyproject.toml`, which ships to /app in the Docker image."""

    def test_matches_pyproject(self):
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as handle:
            expected = tomllib.load(handle)["project"]["version"]

        assert get_current_hometube_version() == expected

    def test_missing_pyproject_yields_none(self):
        """Both the tomllib path and the line-scanning fallback must give up."""
        with (
            patch("app.ytdlp_version_check.open", side_effect=FileNotFoundError),
            patch("tomllib.load", side_effect=FileNotFoundError),
        ):
            assert get_current_hometube_version() is None

    def test_unparseable_toml_falls_back_to_scanning_the_file(self):
        """The fallback's stated reason — "Python < 3.11" — is obsolete, since
        `requires-python` is >=3.11 and tomllib is always importable. What it
        still buys is a version number out of a `pyproject.toml` that tomllib
        refuses, so that is the behaviour pinned here.
        """
        contents = '[project]\nname = "hometube"\nversion = "9.9.9"\n'

        with (
            patch("tomllib.load", side_effect=ValueError("invalid TOML")),
            patch("app.ytdlp_version_check.open", mock_open(read_data=contents)),
        ):
            assert get_current_hometube_version() == "9.9.9"


class TestLatestHometubeVersion:
    """The lookup that feeds the update banner in `app/notifications.py`."""

    def test_environment_seam_wins_without_a_request(self, monkeypatch):
        monkeypatch.setenv("TEST_LATEST_HOMETUBE_VERSION", "9.9.9")

        with patch("app.ytdlp_version_check.requests.get") as get:
            assert get_latest_hometube_version() == "9.9.9"

        get.assert_not_called()

    def test_strips_the_v_prefix_from_the_release_tag(self):
        response = fake_response(200, {"tag_name": "v2.13.0"})

        with patch("app.ytdlp_version_check.requests.get", return_value=response):
            assert get_latest_hometube_version() == "2.13.0"

    def test_queries_the_hometube_repository(self):
        response = fake_response(200, {"tag_name": "v2.13.0"})

        with patch(
            "app.ytdlp_version_check.requests.get", return_value=response
        ) as get:
            get_latest_hometube_version()

        assert HOMETUBE_GITHUB_REPO in get.call_args.args[0]

    def test_falls_back_to_tags_when_there_is_no_release(self):
        """A fork with tags but no published release still gets a version."""
        responses = [
            fake_response(404),
            fake_response(200, [{"name": "v2.12.3"}, {"name": "v2.12.2"}]),
        ]

        with patch("app.ytdlp_version_check.requests.get", side_effect=responses):
            assert get_latest_hometube_version() == "2.12.3"

    def test_no_release_and_no_tags_yields_none(self):
        responses = [fake_response(404), fake_response(200, [])]

        with patch("app.ytdlp_version_check.requests.get", side_effect=responses):
            assert get_latest_hometube_version() is None

    def test_network_failure_yields_none(self):
        with patch(
            "app.ytdlp_version_check.requests.get",
            side_effect=requests.RequestException("offline"),
        ):
            assert get_latest_hometube_version() is None


class TestVersionSourcesAgree:
    """`app.__version__` and `pyproject.toml` must carry the same number.

    The two live side by side and are bumped together by `make version-update`,
    but nothing enforces it. They are read by *different* consumers:
    `notifications.get_current_version()` reads `app.__version__`, while the
    sidebar panel reads `pyproject.toml`. So a release that bumped only
    `pyproject.toml` would leave every user's `app.__version__` behind the
    published release, and `check_update_notification()` compares exactly those
    two numbers — every user would be told to upgrade to the version they are
    already running, with no way to dismiss it permanently.
    """

    def test_dunder_version_matches_pyproject(self):
        assert app.__version__ == get_current_hometube_version()


class TestDescribeVersionStatus:
    """The panel's verdict used to be `current == latest`, which is wrong.

    An inequality says "newer" when all it knows is "different", and the two
    strings are different in three situations that have nothing to do with an
    available update. Each test below is one of them, and each was measured on
    the panel before the comparison was fixed.
    """

    def test_a_newer_release_is_an_update(self):
        assert describe_version_status("2.13.0", "2.14.0") == STATUS_UPDATE_AVAILABLE

    def test_a_newer_patch_is_an_update(self):
        """The one case equality got right; it must keep working."""
        assert describe_version_status("2.13.2", "2.13.3") == STATUS_UPDATE_AVAILABLE

    def test_the_same_version_is_up_to_date(self):
        assert describe_version_status("2.13.3", "2.13.3") == STATUS_UP_TO_DATE

    def test_running_ahead_of_the_latest_release_is_up_to_date(self):
        """🔴 Live on 2026-10-31: `v2.13.3` was tagged, built and pushed to
        `:latest`, but its GitHub release was left a draft — and a draft is
        invisible to `/releases/latest`, which kept answering `v2.13.2`.

        So every user on `:latest` who opened the panel was told an update was
        available, and sent to a release *older* than the one they were
        running. The app must never advertise a downgrade as an upgrade.
        """
        assert describe_version_status("2.13.3", "2.13.2") == STATUS_UP_TO_DATE

    def test_both_versions_unknown_is_not_up_to_date(self):
        """🔴 The sharpest one: `"unknown" == "unknown"` reported ✅ *Up to
        date*.

        Offline, or with GitHub rate-limiting, every lookup returns None and
        the panel substitutes `unknown` on both sides. The old test asserted
        `"unknown" in panel` and never looked at the status line, so a check
        that reached nothing claimed success — this repository's recurring
        defect, a thing that silently does nothing instead of failing.
        """
        assert (
            describe_version_status(UNKNOWN_VERSION, UNKNOWN_VERSION) == STATUS_UNKNOWN
        )

    def test_an_unknown_latest_is_not_an_update(self):
        """The other half of a failed lookup: it offered an update to `unknown`."""
        assert describe_version_status("2.13.3", UNKNOWN_VERSION) == STATUS_UNKNOWN

    def test_an_unknown_current_is_not_an_update(self):
        assert describe_version_status(UNKNOWN_VERSION, "2.13.3") == STATUS_UNKNOWN

    @pytest.mark.parametrize("value", [None, ""])
    def test_a_missing_version_is_not_an_update(self, value):
        assert describe_version_status(value, "2.13.3") == STATUS_UNKNOWN
        assert describe_version_status("2.13.3", value) == STATUS_UNKNOWN

    def test_an_unparseable_version_is_not_an_update(self):
        """`parse_version` answers `(0, 0, 0)` for anything it cannot read, so
        comparing its output blindly would call two unreadable strings equal —
        the `unknown` defect again, one layer down."""
        assert describe_version_status("not-a-version", "2.13.3") == STATUS_UNKNOWN
        assert describe_version_status("2.13.3", "garbage") == STATUS_UNKNOWN

    def test_ytdlp_dotted_dates_compare_numerically_not_lexically(self):
        """yt-dlp numbers releases by date, and `"2026.9.1" > "2026.10.26"` as
        strings — so a string comparison reads the newer release as older."""
        assert (
            describe_version_status("2026.9.1", "2026.10.26") == STATUS_UPDATE_AVAILABLE
        )
        assert describe_version_status("2026.10.26", "2026.9.1") == STATUS_UP_TO_DATE

    def test_a_v_prefix_is_not_a_difference(self):
        """`get_latest_*` strips the prefix, but nothing guarantees every
        caller does."""
        assert describe_version_status("2.13.3", "v2.13.3") == STATUS_UP_TO_DATE

    def test_the_three_statuses_are_distinct(self):
        """Guards the tests above: identical constants would make them vacuous."""
        assert len({STATUS_UP_TO_DATE, STATUS_UPDATE_AVAILABLE, STATUS_UNKNOWN}) == 3


class TestUpdatePanelNeverBreaksTheApp:
    """`check_and_show_updates` is wired to a sidebar button in `app/main.py`.

    It swallows everything on purpose — an unreachable GitHub must not take the
    page down mid-download — so the contract worth pinning is that it reports
    rather than raises.
    """

    def test_renders_the_panel_with_every_version_known(self):
        """The "up to date" branch, pinned against the version the app ships.

        Hard-coding the released tag here made this test fail on every single
        version bump: `make version-update` moved `app.__version__` forward, the
        fake "latest" stayed behind, and the panel correctly reported "Update
        available" while the assertion still demanded "Up to date". A release
        PR could therefore never go green, which is exactly what held 2.13.1
        back for thirty days. The fake release must follow the app.
        """
        completed = subprocess.CompletedProcess(
            args=["yt-dlp", "--version"], returncode=0, stdout="2025.09.23\n"
        )

        with (
            patch("app.ytdlp_version_check.subprocess.run", return_value=completed),
            patch(
                "app.ytdlp_version_check.requests.get",
                return_value=fake_response(200, {"tag_name": f"v{app.__version__}"}),
            ),
            patch("app.ytdlp_version_check.st") as st,
        ):
            check_and_show_updates()

        st.info.assert_called_once()
        panel = st.info.call_args.args[0]
        assert "2025.09.23" in panel
        assert app.__version__ in panel
        assert "✅ Up to date" in panel

    def test_reports_unknown_versions_instead_of_failing(self):
        """Offline, and without yt-dlp: the panel still renders.

        The status assertions are the half this test was missing. It checked
        only that `unknown` appeared somewhere, so it passed just as happily
        while the panel told an offline user ✅ *Up to date* — a verdict it had
        no information to reach.
        """
        with (
            patch(
                "app.ytdlp_version_check.subprocess.run", side_effect=FileNotFoundError
            ),
            patch(
                "app.ytdlp_version_check.requests.get",
                side_effect=requests.RequestException("offline"),
            ),
            patch("app.ytdlp_version_check.st") as st,
        ):
            check_and_show_updates()

        st.error.assert_not_called()
        panel = st.info.call_args.args[0]
        assert "unknown" in panel
        assert STATUS_UNKNOWN in panel
        assert STATUS_UP_TO_DATE not in panel
        assert STATUS_UPDATE_AVAILABLE not in panel

    def test_a_release_behind_the_running_build_is_not_an_update(self):
        """The panel on 2026-10-31, with `v2.13.3`'s release still a draft.

        `/releases/latest` answered `v2.13.2` while the image ran 2.13.3, and
        the panel offered the older release as an upgrade. The fake release is
        derived from the running version rather than hard-coded, for the reason
        written on `test_renders_the_panel_with_every_version_known`: a literal
        tag here fails on every version bump.
        """
        major = int(app.__version__.split(".")[0])
        older_release = f"{major - 1}.0.0"
        completed = subprocess.CompletedProcess(
            args=["yt-dlp", "--version"], returncode=0, stdout="2026.10.26\n"
        )

        with (
            patch("app.ytdlp_version_check.subprocess.run", return_value=completed),
            patch(
                "app.ytdlp_version_check.requests.get",
                return_value=fake_response(200, {"tag_name": f"v{older_release}"}),
            ),
            patch("app.ytdlp_version_check.st") as st,
        ):
            check_and_show_updates()

        panel = st.info.call_args.args[0]
        assert older_release in panel
        assert STATUS_UPDATE_AVAILABLE not in panel

    def test_an_unexpected_failure_is_shown_not_raised(self):
        with (
            patch(
                "app.ytdlp_version_check.get_current_ytdlp_version",
                side_effect=RuntimeError("boom"),
            ),
            patch("app.ytdlp_version_check.st") as st,
        ):
            check_and_show_updates()

        st.error.assert_called_once()
        assert "boom" in st.error.call_args.args[0]
