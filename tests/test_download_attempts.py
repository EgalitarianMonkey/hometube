"""
Tests for download attempt tracking in status.json.

This test suite verifies that:
1. Download attempts are recorded with all required fields
2. Multiple attempts are stored in chronological order (newest first)
3. The status.json structure is correct
"""

import json
from datetime import datetime


def test_add_download_attempt_creates_entry(tmp_path):
    """Test that add_download_attempt creates a proper entry."""
    from app.status_utils import (
        create_initial_status,
        add_download_attempt,
        load_status,
    )

    # Create initial status
    tmp_url_workspace = tmp_path / "youtube-test123"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=test123",
        video_id="test123",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # Add a download attempt
    success = add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="My Custom Title",
        video_location="Tech/HomeLab",
    )

    assert success is True

    # Load and verify
    status_data = load_status(tmp_url_workspace)
    assert status_data is not None
    assert "download_attempts" in status_data
    assert len(status_data["download_attempts"]) == 1

    attempt = status_data["download_attempts"][0]
    assert attempt["custom_title"] == "My Custom Title"
    assert attempt["video_location"] == "Tech/HomeLab"
    assert "date" in attempt

    # Verify date is valid ISO format
    parsed_date = datetime.fromisoformat(attempt["date"])
    assert parsed_date.tzinfo is not None  # Should have timezone


def test_multiple_attempts_ordered_newest_first(tmp_path):
    """Test that multiple attempts are ordered with newest first."""
    from app.status_utils import (
        create_initial_status,
        add_download_attempt,
        load_status,
    )
    import time

    tmp_url_workspace = tmp_path / "youtube-test456"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=test456",
        video_id="test456",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # Add first attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="First Attempt",
        video_location="Videos",
    )

    # Small delay to ensure different timestamps
    time.sleep(0.01)

    # Add second attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Second Attempt",
        video_location="Music",
    )

    # Small delay
    time.sleep(0.01)

    # Add third attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Third Attempt",
        video_location="Clips",
    )

    # Load and verify order
    status_data = load_status(tmp_url_workspace)
    assert len(status_data["download_attempts"]) == 3

    # Newest should be first (position 0)
    assert status_data["download_attempts"][0]["custom_title"] == "Third Attempt"
    assert status_data["download_attempts"][1]["custom_title"] == "Second Attempt"
    assert status_data["download_attempts"][2]["custom_title"] == "First Attempt"

    # Verify timestamps are in descending order
    dates = [
        datetime.fromisoformat(a["date"]) for a in status_data["download_attempts"]
    ]
    assert dates[0] > dates[1] > dates[2], "Timestamps should be in descending order"


def test_download_attempt_without_status_file(tmp_path):
    """Test that add_download_attempt fails gracefully without status file."""
    from app.status_utils import add_download_attempt

    tmp_url_workspace = tmp_path / "nonexistent"

    success = add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Test",
        video_location="Videos",
    )

    assert success is False


def test_download_attempt_with_special_characters(tmp_path):
    """Test that special characters in title and location are preserved."""
    from app.status_utils import (
        create_initial_status,
        add_download_attempt,
        load_status,
    )

    tmp_url_workspace = tmp_path / "youtube-test789"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=test789",
        video_id="test789",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # Add attempt with special characters
    special_title = "Test: Video (2025) - Part 1 [HD]"
    special_location = "Tech/HomeLab/Tutoriels"

    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title=special_title,
        video_location=special_location,
    )

    # Load and verify special characters are preserved
    status_data = load_status(tmp_url_workspace)
    attempt = status_data["download_attempts"][0]

    assert attempt["custom_title"] == special_title
    assert attempt["video_location"] == special_location


def test_download_attempt_preserves_other_status_fields(tmp_path):
    """Test that adding attempts doesn't affect other status fields."""
    from app.status_utils import (
        create_initial_status,
        add_download_attempt,
        add_selected_format,
        load_status,
    )

    tmp_url_workspace = tmp_path / "youtube-testABC"
    tmp_url_workspace.mkdir()

    # Create initial status
    create_initial_status(
        url="https://youtube.com/watch?v=testABC",
        video_id="testABC",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # Add a format
    add_selected_format(
        tmp_url_workspace=tmp_url_workspace,
        video_format="399+251",
        subtitles=["subtitles.en.srt"],
        filesize_approx=100000000,
    )

    # Add a download attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Test Title",
        video_location="Videos",
    )

    # Verify all fields are intact
    status_data = load_status(tmp_url_workspace)

    assert status_data["url"] == "https://youtube.com/watch?v=testABC"
    assert status_data["id"] == "testABC"
    assert status_data["title"] == "Test Video"
    assert len(status_data["downloaded_formats"]) == 1
    assert "399+251" in status_data["downloaded_formats"]
    assert status_data["downloaded_formats"]["399+251"]["status"] == "downloading"
    assert len(status_data["download_attempts"]) == 1


def test_download_attempt_json_structure(tmp_path):
    """Test that the JSON structure matches the specification."""
    from app.status_utils import create_initial_status, add_download_attempt

    tmp_url_workspace = tmp_path / "youtube-testDEF"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=testDEF",
        video_id="testDEF",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Stress",
        video_location="Clip",
    )

    # Read raw JSON to verify structure
    status_path = tmp_url_workspace / "status.json"
    with open(status_path, "r") as f:
        raw_json = json.load(f)

    # Verify exact structure
    assert "download_attempts" in raw_json
    assert isinstance(raw_json["download_attempts"], list)
    assert len(raw_json["download_attempts"]) == 1

    attempt = raw_json["download_attempts"][0]
    assert set(attempt.keys()) == {"custom_title", "video_location", "date"}
    assert attempt["custom_title"] == "Stress"
    assert attempt["video_location"] == "Clip"

    # Verify date format (ISO 8601 with timezone)
    date_str = attempt["date"]
    assert "T" in date_str
    assert "+00:00" in date_str or "Z" in date_str or date_str.endswith("+00:00")


def test_get_last_download_attempt(tmp_path):
    """Test that get_last_download_attempt returns the most recent attempt."""
    from app.status_utils import (
        create_initial_status,
        add_download_attempt,
        get_last_download_attempt,
    )
    import time

    tmp_url_workspace = tmp_path / "youtube-testGHI"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=testGHI",
        video_id="testGHI",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # Add first attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="First Title",
        video_location="Tech",
    )

    time.sleep(0.01)

    # Add second attempt
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title="Second Title",
        video_location="Music",
    )

    # Get last attempt
    last_attempt = get_last_download_attempt(tmp_url_workspace)

    assert last_attempt is not None
    assert last_attempt["custom_title"] == "Second Title"
    assert last_attempt["video_location"] == "Music"
    assert "date" in last_attempt


def test_get_last_download_attempt_no_attempts(tmp_path):
    """Test that get_last_download_attempt returns None when no attempts exist."""
    from app.status_utils import create_initial_status, get_last_download_attempt

    tmp_url_workspace = tmp_path / "youtube-testJKL"
    tmp_url_workspace.mkdir()

    create_initial_status(
        url="https://youtube.com/watch?v=testJKL",
        video_id="testJKL",
        title="Test Video",
        content_type="video",
        tmp_url_workspace=tmp_url_workspace,
    )

    # No attempts added
    last_attempt = get_last_download_attempt(tmp_url_workspace)

    assert last_attempt is None


def test_get_last_download_attempt_no_status_file(tmp_path):
    """Test that get_last_download_attempt returns None when no status file exists."""
    from app.status_utils import get_last_download_attempt

    tmp_url_workspace = tmp_path / "nonexistent"

    last_attempt = get_last_download_attempt(tmp_url_workspace)

    assert last_attempt is None
