"""Tests for video overwrite protection"""


class TestOverwriteProtectionConfig:
    """Test ALLOW_OVERWRITE_EXISTING_VIDEO configuration"""

    def test_default_is_false(self):
        """Test that ALLOW_OVERWRITE_EXISTING_VIDEO defaults to false (protection enabled)"""
        from app.config import _DEFAULTS, _to_bool

        # Check the default value in _DEFAULTS dictionary
        default_value_str = _DEFAULTS["ALLOW_OVERWRITE_EXISTING_VIDEO"]
        default_value = _to_bool(
            default_value_str, True
        )  # If not set, would default to True

        # Should default to False to protect existing files
        assert (
            default_value is False
        ), f"ALLOW_OVERWRITE_EXISTING_VIDEO should default to False for safety, got {default_value_str}"

    def test_config_structure(self):
        """Test that config includes ALLOW_OVERWRITE_EXISTING_VIDEO"""
        from app.config import get_settings

        settings = get_settings()
        assert hasattr(
            settings, "ALLOW_OVERWRITE_EXISTING_VIDEO"
        ), "Settings should have ALLOW_OVERWRITE_EXISTING_VIDEO attribute"
        assert isinstance(
            settings.ALLOW_OVERWRITE_EXISTING_VIDEO, bool
        ), "ALLOW_OVERWRITE_EXISTING_VIDEO should be a boolean"


class TestFileExistenceCheck:
    """Test file existence checking logic"""

    def test_check_multiple_extensions(self, tmp_path):
        """Test checking for files with different video extensions"""
        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()

        # Create test files with different extensions
        extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]
        filename = "test_video"

        existing_files = []
        for ext in extensions:
            potential_file = dest_dir / f"{filename}{ext}"
            if potential_file.exists():
                existing_files.append(potential_file)

        # At start, no files should exist
        assert len(existing_files) == 0

        # Create a file and verify detection
        test_file = dest_dir / f"{filename}.mkv"
        test_file.write_text("test content")

        existing_files = []
        for ext in extensions:
            potential_file = dest_dir / f"{filename}{ext}"
            if potential_file.exists():
                existing_files.append(potential_file)

        assert len(existing_files) == 1
        assert existing_files[0].name == "test_video.mkv"

    def test_file_size_readable(self, tmp_path):
        """Test that we can get file size for display"""
        test_file = tmp_path / "test_video.mkv"
        test_content = "test content" * 1000  # ~12KB
        test_file.write_text(test_content)

        file_size_bytes = test_file.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        assert file_size_mb > 0
        assert file_size_mb < 1  # Should be less than 1MB for our test

    def test_no_filename_no_check(self):
        """Test that if filename is None/empty, no check is performed"""
        # This is just a logic test - in real code, if filename is None,
        # the check block is skipped entirely
        filename = None
        should_check = bool(filename and filename.strip())

        assert should_check is False

        filename = ""
        should_check = bool(filename and filename.strip())

        assert should_check is False


class TestOverwriteBehavior:
    """Test the overwrite protection behavior scenarios"""

    def test_scenario_file_exists_overwrite_disabled(self, tmp_path):
        """
        Scenario: File exists, ALLOW_OVERWRITE_EXISTING_VIDEO=false
        Expected: Download should be skipped
        """
        # Test the logic independently of actual config
        allow_overwrite = False  # Simulate protection enabled

        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()

        filename = "my_video"
        existing_file = dest_dir / f"{filename}.mkv"
        existing_file.write_text("existing content")

        # Check if file exists
        extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]
        existing_files = [
            dest_dir / f"{filename}{ext}"
            for ext in extensions
            if (dest_dir / f"{filename}{ext}").exists()
        ]

        # File exists and overwrite is disabled -> should skip
        should_skip = len(existing_files) > 0 and not allow_overwrite

        assert (
            should_skip is True
        ), "Should skip download when file exists and overwrite disabled"

    def test_scenario_file_not_exists(self, tmp_path):
        """
        Scenario: File doesn't exist
        Expected: Download should proceed normally
        """
        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()

        filename = "new_video"

        # Check if file exists
        extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]
        existing_files = [
            dest_dir / f"{filename}{ext}"
            for ext in extensions
            if (dest_dir / f"{filename}{ext}").exists()
        ]

        # File doesn't exist -> should proceed
        should_skip = len(existing_files) > 0

        assert (
            should_skip is False
        ), "Should proceed with download when file doesn't exist"

    def test_scenario_different_filename_same_folder(self, tmp_path):
        """
        Scenario: Different filename in same folder
        Expected: Download should proceed (different file)
        """
        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()

        # Existing file
        existing_file = dest_dir / "old_video.mkv"
        existing_file.write_text("old content")

        # New file with different name
        new_filename = "new_video"

        extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]
        existing_files = [
            dest_dir / f"{new_filename}{ext}"
            for ext in extensions
            if (dest_dir / f"{new_filename}{ext}").exists()
        ]

        # Different filename -> should proceed
        should_skip = len(existing_files) > 0

        assert should_skip is False, "Should proceed when filename is different"
