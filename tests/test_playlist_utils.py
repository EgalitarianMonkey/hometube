"""
Tests for playlist utilities
"""

from app.playlist_utils import (
    is_playlist_url,
    extract_playlist_id,
    is_playlist_info,
    get_playlist_entries,
    get_playlist_video_count,
    check_existing_videos_in_destination,
    get_download_ratio,
    get_download_progress_percent,
    _normalize_for_comparison,
    create_playlist_status,
    load_playlist_status,
    update_video_status_in_playlist,
    get_playlist_progress,
    mark_video_as_skipped,
)


class TestPlaylistUrlDetection:
    """Test playlist URL detection functions"""

    def test_is_playlist_url_standard(self):
        """Test standard YouTube playlist URL"""
        url = "https://www.youtube.com/playlist?list=PLGbut4pdSxUOiO5bOUryKgE9jtVUlgFz4"
        assert is_playlist_url(url) is True

    def test_is_playlist_url_with_index(self):
        """Test playlist URL with index parameter"""
        url = "https://www.youtube.com/playlist?list=PLtest123&index=5"
        assert is_playlist_url(url) is True

    def test_is_playlist_url_video_not_playlist(self):
        """Test that regular video URL is not detected as playlist"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert is_playlist_url(url) is False

    def test_is_playlist_url_video_with_list_param(self):
        """Test video URL with list param is not detected as playlist"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        assert is_playlist_url(url) is False

    def test_is_playlist_url_empty(self):
        """Test empty URL"""
        assert is_playlist_url("") is False
        assert is_playlist_url(None) is False

    def test_extract_playlist_id(self):
        """Test playlist ID extraction"""
        url = "https://www.youtube.com/playlist?list=PLGbut4pdSxUOiO5bOUryKgE9jtVUlgFz4"
        assert extract_playlist_id(url) == "PLGbut4pdSxUOiO5bOUryKgE9jtVUlgFz4"

    def test_extract_playlist_id_not_found(self):
        """Test playlist ID extraction from non-playlist URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_playlist_id(url) is None


class TestPlaylistInfoDetection:
    """Test playlist info detection from yt-dlp data"""

    def test_is_playlist_info_with_type(self):
        """Test detection with _type field"""
        info = {"_type": "playlist", "title": "Test Playlist"}
        assert is_playlist_info(info) is True

    def test_is_playlist_info_with_entries(self):
        """Test detection with entries and playlist_count"""
        info = {
            "entries": [{"id": "abc123"}],
            "playlist_count": 10,
            "title": "Test",
        }
        assert is_playlist_info(info) is True

    def test_is_playlist_info_video(self):
        """Test that video info is not detected as playlist"""
        info = {"_type": "video", "title": "Test Video", "duration": 300}
        assert is_playlist_info(info) is False

    def test_is_playlist_info_empty(self):
        """Test empty info"""
        assert is_playlist_info({}) is False
        assert is_playlist_info(None) is False


class TestPlaylistEntries:
    """Test playlist entries extraction"""

    def test_get_playlist_entries(self):
        """Test extracting entries from playlist info"""
        info = {
            "_type": "playlist",
            "entries": [
                {"id": "vid1", "title": "Video 1"},
                {"id": "vid2", "title": "Video 2"},
            ],
        }
        entries = get_playlist_entries(info)
        assert len(entries) == 2
        assert entries[0]["id"] == "vid1"
        assert entries[1]["id"] == "vid2"

    def test_get_playlist_entries_with_none(self):
        """Test handling of None entries in list"""
        info = {
            "_type": "playlist",
            "entries": [
                {"id": "vid1", "title": "Video 1"},
                None,
                {"id": "vid3", "title": "Video 3"},
            ],
        }
        entries = get_playlist_entries(info)
        assert len(entries) == 2  # None should be filtered out

    def test_get_playlist_video_count_from_playlist_count(self):
        """Test count from playlist_count field"""
        info = {
            "_type": "playlist",
            "playlist_count": 50,
            "entries": [{"id": "vid1"}],  # Only 1 entry loaded (flat mode)
        }
        assert get_playlist_video_count(info) == 50

    def test_get_playlist_video_count_from_entries(self):
        """Test count from entries when playlist_count not available"""
        info = {
            "_type": "playlist",
            "entries": [{"id": f"vid{i}"} for i in range(10)],
        }
        assert get_playlist_video_count(info) == 10


class TestNormalization:
    """Test string normalization for comparison"""

    def test_normalize_basic(self):
        """Test basic normalization"""
        assert _normalize_for_comparison("Hello World") == "hello world"

    def test_normalize_special_chars(self):
        """Test normalization removes special characters"""
        assert _normalize_for_comparison("Video: Test (2023)") == "video test 2023"

    def test_normalize_extra_spaces(self):
        """Test normalization handles extra spaces"""
        assert _normalize_for_comparison("Hello   World") == "hello world"

    def test_normalize_empty(self):
        """Test normalization of empty string"""
        assert _normalize_for_comparison("") == ""
        assert _normalize_for_comparison(None) == ""


class TestExistingVideosCheck:
    """Test checking for existing videos in destination"""

    def test_check_empty_destination(self, tmp_path):
        """Test with non-existent destination folder"""
        dest = tmp_path / "nonexistent"
        entries = [
            {"id": "vid1", "title": "Video 1"},
            {"id": "vid2", "title": "Video 2"},
        ]

        already, to_download, total = check_existing_videos_in_destination(
            dest, entries
        )

        assert len(already) == 0
        assert len(to_download) == 2
        assert total == 2

    def test_check_some_existing(self, tmp_path):
        """Test with some videos already downloaded"""
        dest = tmp_path / "videos"
        dest.mkdir()

        # Create an existing video file
        (dest / "Video 1.mkv").touch()

        entries = [
            {"id": "vid1", "title": "Video 1"},
            {"id": "vid2", "title": "Video 2"},
            {"id": "vid3", "title": "Video 3"},
        ]

        already, to_download, total = check_existing_videos_in_destination(
            dest, entries
        )

        assert len(already) == 1
        assert len(to_download) == 2
        assert total == 3

    def test_check_by_video_id(self, tmp_path):
        """Test matching by video ID in filename"""
        dest = tmp_path / "videos"
        dest.mkdir()

        # Create file with video ID in name
        (dest / "Some Title - vid2.mp4").touch()

        entries = [
            {"id": "vid1", "title": "Video 1"},
            {"id": "vid2", "title": "Video 2"},
        ]

        already, to_download, total = check_existing_videos_in_destination(
            dest, entries
        )

        assert len(already) == 1
        assert already[0]["id"] == "vid2"


class TestDownloadRatio:
    """Test download ratio calculations"""

    def test_get_download_ratio(self):
        """Test ratio string formatting"""
        already = [{"id": "1"}, {"id": "2"}]
        to_download = [{"id": "3"}, {"id": "4"}, {"id": "5"}]

        ratio = get_download_ratio(already, to_download)
        assert ratio == "2/5"

    def test_get_download_progress_percent(self):
        """Test progress percentage calculation"""
        already = [{"id": "1"}, {"id": "2"}]
        to_download = [{"id": "3"}, {"id": "4"}]

        percent = get_download_progress_percent(already, to_download)
        assert percent == 50.0

    def test_get_download_progress_percent_all_done(self):
        """Test 100% progress"""
        already = [{"id": "1"}, {"id": "2"}]
        to_download = []

        percent = get_download_progress_percent(already, to_download)
        assert percent == 100.0

    def test_get_download_progress_percent_empty(self):
        """Test 0% progress with empty lists"""
        percent = get_download_progress_percent([], [])
        assert percent == 0.0


class TestPlaylistStatus:
    """Test playlist status management"""

    def test_create_and_load_playlist_status(self, tmp_path):
        """Test creating and loading playlist status"""
        playlist_workspace = tmp_path / "youtube-playlist-test"
        playlist_workspace.mkdir()

        entries = [
            {
                "id": "vid1",
                "title": "Video 1",
                "url": "https://youtube.com/watch?v=vid1",
            },
            {
                "id": "vid2",
                "title": "Video 2",
                "url": "https://youtube.com/watch?v=vid2",
            },
        ]

        # Create status
        status = create_playlist_status(
            playlist_workspace=playlist_workspace,
            url="https://youtube.com/playlist?list=test",
            playlist_id="test",
            playlist_title="Test Playlist",
            entries=entries,
        )

        assert status["id"] == "test"
        assert status["title"] == "Test Playlist"
        assert status["total_videos"] == 2
        assert "vid1" in status["videos"]
        assert status["videos"]["vid1"]["status"] == "pending"

        # Load status
        loaded = load_playlist_status(playlist_workspace)
        assert loaded is not None
        assert loaded["id"] == "test"

    def test_update_video_status(self, tmp_path):
        """Test updating video status within playlist"""
        playlist_workspace = tmp_path / "youtube-playlist-test"
        playlist_workspace.mkdir()

        entries = [{"id": "vid1", "title": "Video 1", "url": ""}]
        create_playlist_status(
            playlist_workspace=playlist_workspace,
            url="https://youtube.com/playlist?list=test",
            playlist_id="test",
            playlist_title="Test Playlist",
            entries=entries,
        )

        # Update status to completed
        update_video_status_in_playlist(playlist_workspace, "vid1", "completed")

        # Verify
        status = load_playlist_status(playlist_workspace)
        assert status["videos"]["vid1"]["status"] == "completed"
        assert status["videos"]["vid1"]["downloaded_at"] is not None

    def test_get_playlist_progress(self, tmp_path):
        """Test getting playlist progress"""
        playlist_workspace = tmp_path / "youtube-playlist-test"
        playlist_workspace.mkdir()

        entries = [
            {"id": "vid1", "title": "Video 1", "url": ""},
            {"id": "vid2", "title": "Video 2", "url": ""},
            {"id": "vid3", "title": "Video 3", "url": ""},
        ]
        create_playlist_status(
            playlist_workspace=playlist_workspace,
            url="https://youtube.com/playlist?list=test",
            playlist_id="test",
            playlist_title="Test Playlist",
            entries=entries,
        )

        # Update some statuses
        update_video_status_in_playlist(playlist_workspace, "vid1", "completed")
        update_video_status_in_playlist(
            playlist_workspace, "vid2", "failed", "Test error"
        )

        completed, pending, failed, total = get_playlist_progress(playlist_workspace)

        assert completed == 1
        assert pending == 1  # vid3 is still pending
        assert failed == 1
        assert total == 3

    def test_mark_video_as_skipped(self, tmp_path):
        """Test marking video as skipped"""
        playlist_workspace = tmp_path / "youtube-playlist-test"
        playlist_workspace.mkdir()

        entries = [{"id": "vid1", "title": "Video 1", "url": ""}]
        create_playlist_status(
            playlist_workspace=playlist_workspace,
            url="https://youtube.com/playlist?list=test",
            playlist_id="test",
            playlist_title="Test Playlist",
            entries=entries,
        )

        # Mark as skipped
        mark_video_as_skipped(playlist_workspace, "vid1", "Already exists")

        # Verify
        status = load_playlist_status(playlist_workspace)
        assert status["videos"]["vid1"]["status"] == "skipped"
        assert status["videos"]["vid1"]["skip_reason"] == "Already exists"
