"""Tests for file operation utilities (copy_file, move_file, cleanup)"""

from pathlib import Path


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
    """Test REMOVE_TMP_FILES_AFTER_DOWNLOAD configuration behavior"""

    def test_default_is_false(self):
        """Test that REMOVE_TMP_FILES_AFTER_DOWNLOAD defaults to false (keep files)"""
        from app.config import get_settings

        settings = get_settings()
        # Should default to False to keep files for resilience
        assert (
            settings.REMOVE_TMP_FILES_AFTER_DOWNLOAD is False
        ), "REMOVE_TMP_FILES_AFTER_DOWNLOAD should default to False"

    def test_should_remove_tmp_files_respects_config(self):
        """Test that should_remove_tmp_files() reads from config"""
        from app.file_system_utils import should_remove_tmp_files
        from app.config import get_settings

        settings = get_settings()
        result = should_remove_tmp_files()

        # Should match the config default
        assert result == settings.REMOVE_TMP_FILES_AFTER_DOWNLOAD


class TestMoveFinalToDestination:
    """Test move_final_to_destination function for disk space optimization"""

    def test_move_removes_source_file(self, tmp_path):
        """Test that move_final_to_destination removes the source file"""
        from app.file_system_utils import move_final_to_destination

        # Create source file
        src_dir = tmp_path / "tmp" / "youtube-abc123"
        src_dir.mkdir(parents=True)
        src_file = src_dir / "final.mkv"
        src_file.write_text("video content")

        # Create destination
        dest_dir = tmp_path / "videos"
        dest_dir.mkdir()
        dest_file = dest_dir / "My Video.mkv"

        # Move file
        result = move_final_to_destination(src_file, dest_file)

        # Source should no longer exist (moved, not copied)
        assert not src_file.exists(), "Source file should be removed after move"
        assert result.exists(), "Destination file should exist"
        assert result == dest_file

    def test_move_preserves_content(self, tmp_path):
        """Test that move_final_to_destination preserves file content"""
        from app.file_system_utils import move_final_to_destination

        # Create source file with specific content
        src_dir = tmp_path / "tmp"
        src_dir.mkdir()
        src_file = src_dir / "final.mkv"
        original_content = "original video content"
        src_file.write_text(original_content)

        # Create destination
        dest_file = tmp_path / "videos" / "My Video.mkv"

        # Move file (destination dir will be created)
        result = move_final_to_destination(src_file, dest_file)

        # Content should be preserved
        assert result.read_text() == original_content

    def test_move_creates_destination_directory(self, tmp_path):
        """Test that move_final_to_destination creates destination dir if needed"""
        from app.file_system_utils import move_final_to_destination

        # Create source file
        src_dir = tmp_path / "tmp"
        src_dir.mkdir()
        src_file = src_dir / "final.mkv"
        src_file.write_text("content")

        # Destination dir doesn't exist yet
        dest_file = tmp_path / "videos" / "subfolder" / "My Video.mkv"
        assert not dest_file.parent.exists()

        # Move file
        result = move_final_to_destination(src_file, dest_file)

        # Directory should be created
        assert dest_file.parent.exists()
        assert result.exists()

    def test_move_with_logging(self, tmp_path):
        """Test that move_final_to_destination calls log function"""
        from app.file_system_utils import move_final_to_destination

        # Create source file
        src_dir = tmp_path / "tmp"
        src_dir.mkdir()
        src_file = src_dir / "final.mkv"
        src_file.write_text("content")

        dest_file = tmp_path / "videos" / "My Video.mkv"

        # Track log calls
        log_messages = []

        def mock_log(msg):
            log_messages.append(msg)

        # Move with logging
        move_final_to_destination(src_file, dest_file, log_fn=mock_log)

        # Should have logged the move
        assert len(log_messages) == 2
        assert "Moved to:" in log_messages[0]
        assert "Disk space saved" in log_messages[1]

    def test_move_raises_on_missing_source(self, tmp_path):
        """Test that move_final_to_destination raises error for missing source"""
        import pytest
        from app.file_system_utils import move_final_to_destination

        src_file = tmp_path / "nonexistent.mkv"
        dest_file = tmp_path / "dest.mkv"

        with pytest.raises(FileNotFoundError):
            move_final_to_destination(src_file, dest_file)

    def test_move_with_different_filename(self, tmp_path):
        """Test that move allows renaming during move"""
        from app.file_system_utils import move_final_to_destination

        # Create source file with generic name
        src_dir = tmp_path / "tmp"
        src_dir.mkdir()
        src_file = src_dir / "final.mkv"
        src_file.write_text("content")

        # Move with a different name
        dest_file = tmp_path / "videos" / "Beautiful Video Title.mkv"

        result = move_final_to_destination(src_file, dest_file)

        assert result.name == "Beautiful Video Title.mkv"
        assert result.exists()
