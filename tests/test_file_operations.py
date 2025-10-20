"""Tests for file operation utilities (copy_file, move_file, cleanup)"""

import tempfile
from pathlib import Path
import pytest


class TestFileOperations:
    """Test file copy and move operations"""

    def test_copy_file_preserves_original(self, tmp_path):
        """Test that copy_file keeps the original file"""
        from app.file_system_utils import copy_file

        # Create source file
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        src_file = src_dir / "test_video.mkv"
        src_file.write_text("test content")

        # Create destination directory
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()

        # Copy file
        copied_file = copy_file(src_file, dest_dir)

        # Verify both files exist
        assert src_file.exists(), "Original file should still exist after copy"
        assert copied_file.exists(), "Copied file should exist"
        assert copied_file.parent == dest_dir, "File should be in destination directory"
        assert copied_file.name == src_file.name, "File name should be preserved"

        # Verify content is identical
        assert src_file.read_text() == copied_file.read_text()

    def test_copy_file_preserves_metadata(self, tmp_path):
        """Test that copy_file preserves file metadata (using copy2)"""
        from app.file_system_utils import copy_file
        import os
        import time

        # Create source file with specific timestamp
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        src_file = src_dir / "test_video.mkv"
        src_file.write_text("test content")

        # Set specific modification time
        old_time = time.time() - 86400  # 1 day ago
        os.utime(src_file, (old_time, old_time))

        # Create destination directory
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()

        # Copy file
        copied_file = copy_file(src_file, dest_dir)

        # Verify metadata is preserved (within 1 second tolerance)
        src_mtime = src_file.stat().st_mtime
        copied_mtime = copied_file.stat().st_mtime
        assert (
            abs(src_mtime - copied_mtime) < 1
        ), "Modification time should be preserved"

    def test_copy_file_different_content(self, tmp_path):
        """Test that modifying one file doesn't affect the other"""
        from app.file_system_utils import copy_file

        # Create source file
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        src_file = src_dir / "test_video.mkv"
        original_content = "original content"
        src_file.write_text(original_content)

        # Create destination directory
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()

        # Copy file
        copied_file = copy_file(src_file, dest_dir)

        # Modify original
        new_content = "modified content"
        src_file.write_text(new_content)

        # Verify files are independent
        assert src_file.read_text() == new_content
        assert copied_file.read_text() == original_content

    def test_copy_file_returns_correct_path(self, tmp_path):
        """Test that copy_file returns the correct destination path"""
        from app.file_system_utils import copy_file

        src_dir = tmp_path / "source"
        src_dir.mkdir()
        src_file = src_dir / "my_video.mkv"
        src_file.write_text("test")

        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()

        result = copy_file(src_file, dest_dir)

        expected_path = dest_dir / "my_video.mkv"
        assert result == expected_path
        assert isinstance(result, Path)


class TestRemoveTmpFilesConfig:
    """Test REMOVE_TMP_FILES configuration behavior"""

    def test_default_is_false(self):
        """Test that REMOVE_TMP_FILES defaults to false (keep files)"""
        from app.config import get_settings

        settings = get_settings()
        # Should default to False to keep files for resilience
        assert (
            settings.REMOVE_TMP_FILES is False
        ), "REMOVE_TMP_FILES should default to False"

    def test_should_remove_tmp_files_respects_config(self):
        """Test that should_remove_tmp_files() reads from config"""
        from app.file_system_utils import should_remove_tmp_files
        from app.config import get_settings

        settings = get_settings()
        result = should_remove_tmp_files()

        # Should match the config default
        assert result == settings.REMOVE_TMP_FILES
