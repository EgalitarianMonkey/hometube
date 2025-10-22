"""
Tests for status tracking utilities.
"""

import json
import tempfile
from pathlib import Path

from app.status_utils import (
    create_initial_status,
    load_status,
    save_status,
    add_selected_format,
    update_format_status,
    get_format_status,
    is_format_completed,
)


def test_create_initial_status():
    """Test creating initial status.json file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        status_data = create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        # Verify returned data
        assert status_data["url"] == "https://www.youtube.com/watch?v=abc123"
        assert status_data["id"] == "abc123"
        assert status_data["title"] == "Test Video"
        assert status_data["type"] == "video"
        assert status_data["selected_formats"] == []
        assert "last_updated" in status_data

        # Verify file was created
        status_file = tmp_video_dir / "status.json"
        assert status_file.exists()

        # Verify file content
        with open(status_file, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        assert file_data == status_data


def test_load_status():
    """Test loading status from file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        # Create status file
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        # Load status
        loaded_status = load_status(tmp_video_dir)
        assert loaded_status is not None
        assert loaded_status["id"] == "abc123"
        assert loaded_status["title"] == "Test Video"


def test_load_status_nonexistent():
    """Test loading status when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        loaded_status = load_status(tmp_video_dir)
        assert loaded_status is None


def test_save_status():
    """Test saving status updates."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        # Create initial status
        status_data = create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        # Modify and save
        status_data["title"] = "Updated Title"
        success = save_status(tmp_video_dir, status_data)
        assert success is True

        # Verify update
        loaded_status = load_status(tmp_video_dir)
        assert loaded_status["title"] == "Updated Title"


def test_add_selected_format():
    """Test adding a selected format for download."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        # Create initial status
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        # Add format
        success = add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt", "subtitles.fr.srt"],
            filesize_approx=41943040,
        )
        assert success is True

        # Verify format was added
        status_data = load_status(tmp_video_dir)
        assert len(status_data["selected_formats"]) == 1

        format_entry = status_data["selected_formats"][0]
        assert format_entry["video_format"] == "399+251"
        assert format_entry["subtitles"] == ["subtitles.en.srt", "subtitles.fr.srt"]
        assert format_entry["filesize_approx"] == 41943040
        assert format_entry["status"] == "downloading"


def test_add_selected_format_duplicate():
    """Test updating an existing format instead of duplicating."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        # Add format twice
        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt", "subtitles.fr.srt"],
            filesize_approx=42000000,
        )

        # Should have only one entry (updated)
        status_data = load_status(tmp_video_dir)
        assert len(status_data["selected_formats"]) == 1
        assert status_data["selected_formats"][0]["filesize_approx"] == 42000000


def test_update_format_status_completed():
    """Test marking format as completed when file size is within tolerance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        # Create initial status and add format
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        expected_size = 41943040  # ~40MB
        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=expected_size,
        )

        # Create a test file with size within tolerance
        final_file = tmp_video_dir / "final.mp4"
        final_file.write_bytes(b"x" * (expected_size + 50000))  # +50KB (within 1%)

        # Update status
        success = update_format_status(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is completed
        status_data = load_status(tmp_video_dir)
        format_entry = status_data["selected_formats"][0]
        assert format_entry["status"] == "completed"
        assert "actual_filesize" in format_entry


def test_update_format_status_incomplete():
    """Test marking format as incomplete when file size exceeds tolerance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        expected_size = 41943040  # ~40MB
        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=expected_size,
        )

        # Create a test file with size far from expected (>1%)
        final_file = tmp_video_dir / "final.mp4"
        final_file.write_bytes(
            b"x" * (expected_size + 1000000)
        )  # +1MB (exceeds tolerance)

        # Update status
        success = update_format_status(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is incomplete
        status_data = load_status(tmp_video_dir)
        format_entry = status_data["selected_formats"][0]
        assert format_entry["status"] == "incomplete"
        assert "actual_filesize" in format_entry
        assert "size_difference" in format_entry


def test_update_format_status_file_not_found():
    """Test marking format as incomplete when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Try to update with nonexistent file
        final_file = tmp_video_dir / "nonexistent.mp4"

        success = update_format_status(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is incomplete with error
        status_data = load_status(tmp_video_dir)
        format_entry = status_data["selected_formats"][0]
        assert format_entry["status"] == "incomplete"
        assert format_entry["error"] == "File not found"


def test_get_format_status():
    """Test retrieving format status."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Get status
        status = get_format_status(tmp_video_dir, "399+251")
        assert status == "downloading"

        # Get status of non-existent format
        status = get_format_status(tmp_video_dir, "999+999")
        assert status is None


def test_is_format_completed():
    """Test checking if format is completed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_video_dir=tmp_video_dir,
        )

        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Should not be completed yet (status is "downloading")
        assert is_format_completed(tmp_video_dir, "399+251") is False

        # Mark as completed
        status_data = load_status(tmp_video_dir)
        status_data["selected_formats"][0]["status"] = "completed"
        save_status(tmp_video_dir, status_data)

        # Now should be completed
        assert is_format_completed(tmp_video_dir, "399+251") is True
