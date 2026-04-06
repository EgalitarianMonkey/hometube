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
    add_download_attempt,
    add_audio_download,
    update_audio_status,
    get_completed_audio,
    is_audio_completed,
    mark_audio_error,
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
        assert status_data["downloaded_formats"] == {}
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

        format_entry = status_data["downloaded_formats"]["399+251"]
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
        assert (
            status_data["downloaded_formats"]["399+251"]["filesize_approx"] == 42000000
        )


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
        format_entry = status_data["downloaded_formats"]["399+251"]
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
        format_entry = status_data["downloaded_formats"]["399+251"]
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
        format_entry = status_data["downloaded_formats"]["399+251"]
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
        status_data["downloaded_formats"]["399+251"]["status"] = "completed"
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
        format_entry = status_data["downloaded_formats"]["399+251"]
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
        status_data["downloaded_formats"]["248+251"]["status"] = "completed"
        status_data["downloaded_formats"]["248+251"]["actual_filesize"] = 39673330
        save_status(tmp_url_workspace, status_data)

        # Should return the first completed format (248+251)
        result = get_first_completed_format(tmp_url_workspace)
        assert result == "248+251"

        # Mark first format as completed too
        status_data = load_status(tmp_url_workspace)
        status_data["downloaded_formats"]["399+251"]["status"] = "completed"
        status_data["downloaded_formats"]["399+251"]["actual_filesize"] = 42100000
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


# ─── Audio status tracking tests ──────────────────────────────────────────


def _create_workspace_with_status(temp_dir: str) -> Path:
    """Helper: create a workspace with initial status.json."""
    workspace = Path(temp_dir) / "youtube-abc123"
    workspace.mkdir()
    create_initial_status(
        url="https://www.youtube.com/watch?v=abc123",
        video_id="abc123",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=workspace,
    )
    return workspace


def test_add_audio_download():
    """Test marking audio format as downloading."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        success = add_audio_download(workspace, "opus")
        assert success is True

        status = load_status(workspace)
        assert "downloaded_audio" in status
        assert "opus" in status["downloaded_audio"]
        assert status["downloaded_audio"]["opus"]["status"] == "downloading"


def test_add_audio_download_duplicate_updates():
    """Test that re-adding the same audio format overwrites the entry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        add_audio_download(workspace, "opus", filesize_approx=1000)
        add_audio_download(workspace, "opus", filesize_approx=2000)

        status = load_status(workspace)
        assert len(status["downloaded_audio"]) == 1
        assert status["downloaded_audio"]["opus"]["filesize_approx"] == 2000


def test_update_audio_status_completed():
    """Test marking audio as completed after download."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        add_audio_download(workspace, "opus")

        # Create audio file
        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 5000)

        success = update_audio_status(workspace, "opus", audio_file)
        assert success is True

        status = load_status(workspace)
        entry = status["downloaded_audio"]["opus"]
        assert entry["status"] == "completed"
        assert entry["actual_filesize"] == 5000


def test_update_audio_status_file_not_found():
    """Test marking audio as incomplete when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        add_audio_download(workspace, "mp3")

        missing_file = workspace / "nonexistent.mp3"
        success = update_audio_status(workspace, "mp3", missing_file)
        assert success is True

        status = load_status(workspace)
        entry = status["downloaded_audio"]["mp3"]
        assert entry["status"] == "incomplete"
        assert entry["error"] == "File not found"


def test_update_audio_status_auto_creates_entry():
    """Test that update_audio_status creates entry if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 3000)

        # No prior add_audio_download — should auto-create
        success = update_audio_status(workspace, "opus", audio_file)
        assert success is True

        status = load_status(workspace)
        assert status["downloaded_audio"]["opus"]["status"] == "completed"


def test_get_completed_audio():
    """Test finding first completed audio format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        # No audio yet
        assert get_completed_audio(workspace) is None

        # Add downloading audio
        add_audio_download(workspace, "opus")
        assert get_completed_audio(workspace) is None

        # Mark as completed
        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 5000)
        update_audio_status(workspace, "opus", audio_file)

        result = get_completed_audio(workspace)
        assert result == "opus"


def test_get_completed_audio_multiple_formats():
    """Test finding first completed audio when multiple formats exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        # Add two formats: mp3 is error, opus is completed
        add_audio_download(workspace, "mp3")
        mark_audio_error(workspace, "mp3", "Failed")

        add_audio_download(workspace, "opus")
        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 5000)
        update_audio_status(workspace, "opus", audio_file)

        result = get_completed_audio(workspace)
        assert result == "opus"


def test_is_audio_completed():
    """Test checking if specific audio format is completed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        assert is_audio_completed(workspace, "opus") is False

        add_audio_download(workspace, "opus")
        assert is_audio_completed(workspace, "opus") is False

        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 5000)
        update_audio_status(workspace, "opus", audio_file)

        assert is_audio_completed(workspace, "opus") is True
        assert is_audio_completed(workspace, "mp3") is False


def test_mark_audio_error():
    """Test marking audio as error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        add_audio_download(workspace, "opus")
        success = mark_audio_error(workspace, "opus", "Connection timeout")
        assert success is True

        status = load_status(workspace)
        entry = status["downloaded_audio"]["opus"]
        assert entry["status"] == "error"
        assert entry["error"] == "Connection timeout"


def test_mark_audio_error_nonexistent():
    """Test marking error on audio format that doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        success = mark_audio_error(workspace, "flac", "Some error")
        assert success is False


def test_audio_and_video_coexist_in_status():
    """Test that audio and video status coexist independently in status.json."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        # Add video format (existing workflow)
        add_selected_format(
            tmp_url_workspace=workspace,
            video_format="399+251",
            subtitles=["subtitles.en.srt"],
            filesize_approx=41943040,
        )

        # Add audio format (new workflow)
        add_audio_download(workspace, "opus")

        # Both should exist independently
        status = load_status(workspace)
        assert "downloaded_formats" in status
        assert "downloaded_audio" in status
        assert "399+251" in status["downloaded_formats"]
        assert "opus" in status["downloaded_audio"]

        # Video completed
        video_file = workspace / "video-399+251.mp4"
        video_file.write_bytes(b"x" * 41943040)
        update_format_status(workspace, "399+251", video_file)

        # Audio completed
        audio_file = workspace / "audio-best.opus"
        audio_file.write_bytes(b"x" * 5000)
        update_audio_status(workspace, "opus", audio_file)

        # Verify both are completed
        status = load_status(workspace)
        assert status["downloaded_formats"]["399+251"]["status"] == "completed"
        assert status["downloaded_audio"]["opus"]["status"] == "completed"

        # Both lookup functions should work independently
        assert get_first_completed_format(workspace) == "399+251"
        assert get_completed_audio(workspace) == "opus"


def test_download_attempt_with_media_type():
    """Test that download attempts record media_type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        # Video download attempt
        add_download_attempt(
            tmp_url_workspace=workspace,
            custom_title="My Video",
            video_location="Tech",
            media_type="video",
        )

        status = load_status(workspace)
        assert status["download_attempts"][0]["media_type"] == "video"

        # Audio download attempt
        add_download_attempt(
            tmp_url_workspace=workspace,
            custom_title="My Audio",
            video_location="Music",
            media_type="audio",
        )

        status = load_status(workspace)
        assert status["download_attempts"][0]["media_type"] == "audio"
        assert status["download_attempts"][1]["media_type"] == "video"


def test_download_attempt_default_media_type():
    """Test that media_type defaults to 'video' for backward compat."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = _create_workspace_with_status(temp_dir)

        add_download_attempt(
            tmp_url_workspace=workspace,
            custom_title="My Video",
            video_location="Tech",
        )

        status = load_status(workspace)
        assert status["download_attempts"][0]["media_type"] == "video"


def test_audio_resilience_no_status_file():
    """Test audio functions handle missing status.json gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "youtube-xyz"
        workspace.mkdir()

        # All should return gracefully without status.json
        assert get_completed_audio(workspace) is None
        assert is_audio_completed(workspace, "opus") is False
        assert add_audio_download(workspace, "opus") is False
        assert mark_audio_error(workspace, "opus") is False
