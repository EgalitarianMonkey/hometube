"""Tests for the notification engine."""

from contextlib import contextmanager
from unittest.mock import patch

from app.notifications import (
    parse_version,
    is_major_or_minor_update,
    Notification,
    NotificationType,
    load_notification_state,
    save_notification_state,
    is_notification_dismissed,
    dismiss_notification,
    check_update_notification,
    check_cleanup_notification_v260,
    check_content_announcement,
    get_content_announcement_id,
    get_content_angle,
    get_active_notifications,
    CONTENT_ANGLES,
    CONTENT_REPO_URL,
)


class TestVersionParsing:
    """Tests for version parsing functions."""

    def test_parse_version_standard(self):
        """Test parsing standard version strings."""
        assert parse_version("2.5.0") == (2, 5, 0)
        assert parse_version("2.6.1") == (2, 6, 1)
        assert parse_version("3.0.0") == (3, 0, 0)

    def test_parse_version_with_v_prefix(self):
        """Test parsing versions with 'v' prefix."""
        assert parse_version("v2.5.0") == (2, 5, 0)
        assert parse_version("v2.6.1") == (2, 6, 1)

    def test_parse_version_without_patch(self):
        """Test parsing versions without patch number."""
        assert parse_version("2.5") == (2, 5, 0)
        assert parse_version("v3.0") == (3, 0, 0)

    def test_parse_version_invalid(self):
        """Test parsing invalid version strings."""
        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("") == (0, 0, 0)


class TestMajorMinorUpdate:
    """Tests for major/minor update detection."""

    def test_minor_update_detected(self):
        """Test that minor updates are detected."""
        assert is_major_or_minor_update("2.5.0", "2.6.0") is True
        assert is_major_or_minor_update("2.5.1", "2.6.0") is True
        assert is_major_or_minor_update("2.5.0", "2.7.0") is True

    def test_major_update_detected(self):
        """Test that major updates are detected."""
        assert is_major_or_minor_update("2.5.0", "3.0.0") is True
        assert is_major_or_minor_update("1.9.9", "2.0.0") is True

    def test_patch_update_not_detected(self):
        """Test that patch-only updates are not detected."""
        assert is_major_or_minor_update("2.5.0", "2.5.1") is False
        assert is_major_or_minor_update("2.5.0", "2.5.99") is False

    def test_same_version(self):
        """Test same version returns False."""
        assert is_major_or_minor_update("2.5.0", "2.5.0") is False

    def test_older_version(self):
        """Test older version returns False."""
        assert is_major_or_minor_update("2.6.0", "2.5.0") is False
        assert is_major_or_minor_update("3.0.0", "2.9.9") is False


class TestNotificationState:
    """Tests for notification state persistence."""

    def test_load_empty_state(self, tmp_path):
        """Test loading state when file doesn't exist."""
        with patch(
            "app.notifications.get_notifications_file_path",
            return_value=tmp_path / "notifications.json",
        ):
            state = load_notification_state()
            assert state == {"dismissed": {}, "shown": {}}

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            # Save state
            state = {"dismissed": {"test_id": "2024-01-01T00:00:00"}, "shown": {}}
            save_notification_state(state)

            # Load it back
            loaded = load_notification_state()
            assert loaded == state

    def test_dismiss_notification(self, tmp_path):
        """Test dismissing a notification."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            # Initially not dismissed
            assert is_notification_dismissed("test_notif") is False

            # Dismiss it
            dismiss_notification("test_notif")

            # Now should be dismissed
            assert is_notification_dismissed("test_notif") is True


class TestUpdateNotification:
    """Tests for update notification generation."""

    def test_update_notification_for_minor_update(self, tmp_path):
        """Test notification is generated for minor update."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch("app.notifications.get_current_version", return_value="2.5.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.6.0"
                ):
                    notif = check_update_notification()

                    assert notif is not None
                    assert notif.id == "update_2.6.0"
                    assert "2.6.0" in notif.message
                    assert notif.notification_type == NotificationType.SUCCESS

    def test_no_notification_for_patch_update(self, tmp_path):
        """Test no notification for patch-only updates."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch("app.notifications.get_current_version", return_value="2.5.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.5.1"
                ):
                    notif = check_update_notification()
                    assert notif is None

    def test_no_notification_when_dismissed(self, tmp_path):
        """Test no notification when already dismissed."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch("app.notifications.get_current_version", return_value="2.5.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.6.0"
                ):
                    # First time - should get notification
                    notif = check_update_notification()
                    assert notif is not None

                    # Dismiss it
                    dismiss_notification(notif.id)

                    # Second time - should not get notification
                    notif = check_update_notification()
                    assert notif is None


class TestCleanupNotification:
    """Tests for cleanup notification."""

    def test_cleanup_notification_with_old_files(self, tmp_path):
        """Test cleanup notification when old tmp files exist."""
        state_file = tmp_path / "notifications.json"
        tmp_folder = tmp_path / "tmp"
        tmp_folder.mkdir()

        # Create some old-style folders
        (tmp_folder / "old_video_folder").mkdir()
        (tmp_folder / "another_old_folder").mkdir()

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch(
                "app.config.ensure_folders_exist",
                return_value=(tmp_path / "videos", tmp_folder),
            ):
                notif = check_cleanup_notification_v260()

                assert notif is not None
                assert notif.id == "cleanup_v260_new_tmp_structure"
                assert "2.6" in notif.message
                assert notif.notification_type == NotificationType.INFO

    def test_no_cleanup_notification_when_empty(self, tmp_path):
        """Test no cleanup notification when tmp is empty."""
        state_file = tmp_path / "notifications.json"
        tmp_folder = tmp_path / "tmp"
        tmp_folder.mkdir()

        # Only new-style folders exist
        (tmp_folder / "videos").mkdir()
        (tmp_folder / "playlists").mkdir()

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch(
                "app.config.ensure_folders_exist",
                return_value=(tmp_path / "videos", tmp_folder),
            ):
                notif = check_cleanup_notification_v260()
                assert notif is None

    def test_no_cleanup_notification_when_dismissed(self, tmp_path):
        """Test no cleanup notification when dismissed."""
        state_file = tmp_path / "notifications.json"
        tmp_folder = tmp_path / "tmp"
        tmp_folder.mkdir()
        (tmp_folder / "old_folder").mkdir()

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch(
                "app.config.ensure_folders_exist",
                return_value=(tmp_path / "videos", tmp_folder),
            ):
                # Dismiss first
                dismiss_notification("cleanup_v260_new_tmp_structure")

                notif = check_cleanup_notification_v260()
                assert notif is None


class TestContentAnnouncement:
    """Tests for the Content announcement."""

    def test_announcement_shown_by_default(self, tmp_path):
        """The announcement is offered until the user dismisses it."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            notif = check_content_announcement()

            assert notif is not None
            assert notif.id == get_content_announcement_id()
            assert notif.action_url == CONTENT_REPO_URL
            assert notif.notification_type == NotificationType.INFO

    def test_no_announcement_when_dismissed(self, tmp_path):
        """Dismissing the announcement keeps it hidden."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            dismiss_notification(get_content_announcement_id())

            assert check_content_announcement() is None

    def test_id_tracks_the_minor_version(self):
        """The id carries major.minor, so patches share it and minors do not."""
        assert get_content_announcement_id("2.11.0") == "content_announcement_v2.11"
        assert get_content_announcement_id("2.11.4") == get_content_announcement_id(
            "2.11.0"
        )
        assert get_content_announcement_id("2.12.0") != get_content_announcement_id(
            "2.11.0"
        )
        assert get_content_announcement_id("3.0.0") != get_content_announcement_id(
            "2.11.0"
        )

    def test_reappears_after_a_feature_release(self, tmp_path):
        """A dismissal covers its own release and its patches, not the next minor."""
        state_file = tmp_path / "notifications.json"

        with patch(
            "app.notifications.get_notifications_file_path", return_value=state_file
        ):
            with patch("app.notifications.get_current_version", return_value="2.11.0"):
                dismiss_notification(get_content_announcement_id())
                assert check_content_announcement() is None

            # A patch on top of it stays silent.
            with patch("app.notifications.get_current_version", return_value="2.11.3"):
                assert check_content_announcement() is None

            # The next feature release offers it again.
            with patch("app.notifications.get_current_version", return_value="2.12.0"):
                notif = check_content_announcement()
                assert notif is not None
                assert notif.id == "content_announcement_v2.12"

    def test_no_angle_deprecates_hometube(self):
        """HomeTube stays maintained, so no angle may read as an EOL notice."""
        for angle in CONTENT_ANGLES:
            lowered = angle.lower()
            for word in (
                "deprecated",
                "end of life",
                "sunset",
                "discontinued",
                "migrate",
                "instead of hometube",
                "replaces",
            ):
                assert word not in lowered, f"{word!r} in {angle!r}"

    def test_angles_stay_glanceable(self):
        """Short enough to read without deciding to — one sentence, no list.

        The cap is the whole point of the note: past roughly a line it stops
        being a detail in passing and starts being a paragraph asking for
        attention, which is the thing that makes a header feel like an ad.
        """
        for angle in CONTENT_ANGLES:
            assert len(angle) <= 60, f"{len(angle)} chars: {angle!r}"
            assert angle.count(".") <= 2, f"more than one sentence: {angle!r}"

    def test_enough_angles_to_stay_fresh(self):
        """A line should not come back before the user has forgotten it."""
        assert len(CONTENT_ANGLES) >= 4
        assert len(set(CONTENT_ANGLES)) == len(CONTENT_ANGLES)

    def test_angle_rotates_with_the_release(self):
        """A returning user meets a new detail, not the banner they already read."""
        seen = [get_content_angle(f"2.{minor}.0") for minor in range(11, 17)]

        assert len(set(seen)) == len(CONTENT_ANGLES)
        assert get_content_angle("2.11.0") == get_content_angle("2.11.9")
        assert get_content_angle("2.11.0") != get_content_angle("2.12.0")


class TestOneNotificationAtATime:
    """Stacked banners are what makes a header invasive — only one may show."""

    @contextmanager
    def _state(self, tmp_path):
        """Isolate both the dismissal file and the tmp folder.

        The cleanup notification inspects the real configured tmp folder, so
        without pinning it here this suite would see whatever other tests left
        behind and the ranking assertions would depend on execution order.
        """
        tmp_folder = tmp_path / "tmp"
        tmp_folder.mkdir()

        with patch(
            "app.notifications.get_notifications_file_path",
            return_value=tmp_path / "notifications.json",
        ):
            with patch(
                "app.config.ensure_folders_exist",
                return_value=(tmp_path / "videos", tmp_folder),
            ):
                yield

    def test_update_outranks_the_content_note(self, tmp_path):
        """A pending update is time-sensitive, so it wins and Content waits."""
        with self._state(tmp_path):
            with patch("app.notifications.get_current_version", return_value="2.11.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.12.0"
                ):
                    active = get_active_notifications()

                    assert len(active) == 1
                    assert active[0].id == "update_2.12.0"

    def test_content_note_surfaces_once_the_update_is_dismissed(self, tmp_path):
        """Nothing is lost — what was outranked appears next."""
        with self._state(tmp_path):
            with patch("app.notifications.get_current_version", return_value="2.11.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.12.0"
                ):
                    dismiss_notification("update_2.12.0")

                    active = get_active_notifications()

                    assert len(active) == 1
                    assert active[0].id == "content_announcement_v2.11"

    def test_content_note_after_upgrading(self, tmp_path):
        """On the visit after an upgrade there is no update left, so Content shows."""
        with self._state(tmp_path):
            with patch("app.notifications.get_current_version", return_value="2.12.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.12.0"
                ):
                    active = get_active_notifications()

                    assert len(active) == 1
                    assert active[0].id == "content_announcement_v2.12"

    def test_nothing_when_everything_is_dismissed(self, tmp_path):
        """A quiet header is the normal state."""
        with self._state(tmp_path):
            with patch("app.notifications.get_current_version", return_value="2.12.0"):
                with patch(
                    "app.notifications.get_latest_version", return_value="2.12.0"
                ):
                    dismiss_notification("content_announcement_v2.12")

                    assert get_active_notifications() == []


class TestNotificationDataclass:
    """Tests for Notification dataclass."""

    def test_notification_creation(self):
        """Test creating a notification."""
        notif = Notification(
            id="test",
            title="Test Title",
            message="Test message",
            notification_type=NotificationType.SUCCESS,
            icon="🎉",
        )

        assert notif.id == "test"
        assert notif.title == "Test Title"
        assert notif.message == "Test message"
        assert notif.notification_type == NotificationType.SUCCESS
        assert notif.icon == "🎉"

    def test_notification_defaults(self):
        """Test notification default values."""
        notif = Notification(
            id="test",
            title="Title",
            message="Message",
        )

        assert notif.notification_type == NotificationType.INFO
        assert notif.action_label is None
        assert notif.action_url is None
        assert notif.icon == "ℹ️"
