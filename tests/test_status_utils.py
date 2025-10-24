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
    mark_format_error,
    get_first_completed_format,
)


def test_create_initial_status():
    """Test creating initial status.json file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        status_data = create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Verify returned data
        assert status_data["url"] == "https://www.youtube.com/watch?v=abc123"
        assert status_data["id"] == "abc123"
        assert status_data["title"] == "Test Video"
        assert status_data["type"] == "video"
        assert status_data["downloaded_formats"] == []
        assert "last_updated" in status_data

        # Verify file was created
        status_file = tmp_url_workspace / "status.json"
        assert status_file.exists()

        # Verify file content
        with open(status_file, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        assert file_data == status_data


def test_load_status():
    """Test loading status from file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        # Create status file
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Load status
        loaded_status = load_status(tmp_url_workspace)
        assert loaded_status is not None
        assert loaded_status["id"] == "abc123"
        assert loaded_status["title"] == "Test Video"


def test_load_status_nonexistent():
    """Test loading status when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        loaded_status = load_status(tmp_url_workspace)
        assert loaded_status is None


def test_save_status():
    """Test saving status updates."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        # Create initial status
        status_data = create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Modify and save
        status_data["title"] = "Updated Title"
        success = save_status(tmp_url_workspace, status_data)
        assert success is True

        # Verify update
        loaded_status = load_status(tmp_url_workspace)
        assert loaded_status["title"] == "Updated Title"


def test_add_selected_format():
    """Test adding a selected format for download."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        # Create initial status
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Add format
        success = add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt", "subtitles.fr.srt"],
            filesize_approx=41943040,
        )
        assert success is True

        # Verify format was added
        status_data = load_status(tmp_url_workspace)
        assert len(status_data["downloaded_formats"]) == 1

        format_entry = status_data["downloaded_formats"][0]
        assert format_entry["video_format"] == "399+251"
        assert format_entry["subtitles"] == ["subtitles.en.srt", "subtitles.fr.srt"]
        assert format_entry["filesize_approx"] == 41943040
        assert format_entry["status"] == "downloading"


def test_add_selected_format_duplicate():
    """Test updating an existing format instead of duplicating."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Add format twice
        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt", "subtitles.fr.srt"],
            filesize_approx=42000000,
        )

        # Should have only one entry (updated)
        status_data = load_status(tmp_url_workspace)
        assert len(status_data["downloaded_formats"]) == 1
        assert status_data["downloaded_formats"][0]["filesize_approx"] == 42000000


def test_update_format_status_completed():
    """Test marking format as completed when file size is within tolerance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        # Create initial status and add format
        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        expected_size = 41943040  # ~40MB
        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=expected_size,
        )

        # Create a test file with size within tolerance
        final_file = tmp_url_workspace / "final.mp4"
        final_file.write_bytes(b"x" * (expected_size + 50000))  # +50KB (within 1%)

        # Update status
        success = update_format_status(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is completed
        status_data = load_status(tmp_url_workspace)
        format_entry = status_data["downloaded_formats"][0]
        assert format_entry["status"] == "completed"
        assert "actual_filesize" in format_entry


def test_update_format_status_incomplete():
    """Test marking format as incomplete when file size exceeds tolerance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        expected_size = 41943040  # ~40MB
        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=expected_size,
        )

        # Create a test file with size far from expected (>1%)
        final_file = tmp_url_workspace / "final.mp4"
        final_file.write_bytes(
            b"x" * (expected_size + 1000000)
        )  # +1MB (exceeds tolerance)

        # Update status
        success = update_format_status(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is incomplete
        status_data = load_status(tmp_url_workspace)
        format_entry = status_data["downloaded_formats"][0]
        assert format_entry["status"] == "incomplete"
        assert "actual_filesize" in format_entry
        assert "size_difference" in format_entry


def test_update_format_status_file_not_found():
    """Test marking format as incomplete when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Try to update with nonexistent file
        final_file = tmp_url_workspace / "nonexistent.mp4"

        success = update_format_status(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            final_file=final_file,
        )
        assert success is True

        # Verify status is incomplete with error
        status_data = load_status(tmp_url_workspace)
        format_entry = status_data["downloaded_formats"][0]
        assert format_entry["status"] == "incomplete"
        assert format_entry["error"] == "File not found"


def test_get_format_status():
    """Test retrieving format status."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Get status
        status = get_format_status(tmp_url_workspace, "399+251")
        assert status == "downloading"

        # Get status of non-existent format
        status = get_format_status(tmp_url_workspace, "999+999")
        assert status is None


def test_is_format_completed():
    """Test checking if format is completed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Should not be completed yet (status is "downloading")
        assert is_format_completed(tmp_url_workspace, "399+251") is False

        # Mark as completed
        status_data = load_status(tmp_url_workspace)
        status_data["downloaded_formats"][0]["status"] = "completed"
        save_status(tmp_url_workspace, status_data)

        # Now should be completed
        assert is_format_completed(tmp_url_workspace, "399+251") is True


def test_mark_format_error():
    """Test marking format as error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Mark as error
        success = mark_format_error(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            error_message="Authentication required",
        )
        assert success is True

        # Verify error status
        status_data = load_status(tmp_url_workspace)
        format_entry = status_data["downloaded_formats"][0]
        assert format_entry["status"] == "error"
        assert format_entry["error"] == "Authentication required"


def test_mark_format_error_nonexistent():
    """Test marking nonexistent format as error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # Try to mark nonexistent format
        success = mark_format_error(
            tmp_url_workspace=tmp_url_workspace,
            video_format="999+999",
            error_message="Some error",
        )
        assert success is False


def test_get_first_completed_format():
    """Test getting first completed format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        create_initial_status(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="Test Video",
            content_type="video",
            tmp_url_workspace=tmp_url_workspace,
        )

        # No completed formats yet
        result = get_first_completed_format(tmp_url_workspace)
        assert result is None

        # Add multiple formats with different statuses
        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=42000000,
        )

        add_selected_format(
            tmp_url_workspace=tmp_url_workspace,
            video_format="248+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=39500000,
        )

        # Still no completed formats
        result = get_first_completed_format(tmp_url_workspace)
        assert result is None

        # Mark second format as completed
        status_data = load_status(tmp_url_workspace)
        status_data["downloaded_formats"][1]["status"] = "completed"
        status_data["downloaded_formats"][1]["actual_filesize"] = 39673330
        save_status(tmp_url_workspace, status_data)

        # Should return the first completed format (248+251)
        result = get_first_completed_format(tmp_url_workspace)
        assert result == "248+251"

        # Mark first format as completed too
        status_data = load_status(tmp_url_workspace)
        status_data["downloaded_formats"][0]["status"] = "completed"
        status_data["downloaded_formats"][0]["actual_filesize"] = 42100000
        save_status(tmp_url_workspace, status_data)

        # Should still return the first one in the list (399+251)
        result = get_first_completed_format(tmp_url_workspace)
        assert result == "399+251"


def test_get_first_completed_format_no_status_file():
    """Test getting completed format when status.json doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_url_workspace = Path(temp_dir) / "youtube-abc123"
        tmp_url_workspace.mkdir()

        # No status.json file
        result = get_first_completed_format(tmp_url_workspace)
        assert result is None
