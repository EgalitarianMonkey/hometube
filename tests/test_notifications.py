"""Tests for the notification engine."""

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
