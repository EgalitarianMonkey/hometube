"""Tests for url_info.json reuse logic with integrity check"""

import json


class TestShouldReuseUrlInfo:
    """Test should_reuse_url_info logic (pure function, no Streamlit)"""

    def test_file_not_exists_returns_false(self, tmp_path):
        """Should return (False, None) if file doesn't exist"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "nonexistent" / "url_info.json"

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is False
        assert data is None

    def test_reuses_video_with_premium_formats(self, tmp_path):
        """Should return (True, data) for video with AV1 formats"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Video with premium AV1 codec
        mock_info = {
            "_type": "video",
            "title": "Test Video",
            "duration": 120,
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.05M.08", "height": 1080},
                {"format_id": "251", "acodec": "opus", "vcodec": "none"},
            ],
        }

        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is True
        assert data is not None
        assert data["title"] == "Test Video"
        assert len(data["formats"]) == 2

    def test_does_not_reuse_video_with_only_h264(self, tmp_path):
        """Should return (False, None) for video with only h264 formats"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Video with only h264 codec
        mock_info = {
            "_type": "video",
            "title": "Limited Video",
            "duration": 120,
            "formats": [
                {"format_id": "22", "vcodec": "avc1.64001F", "height": 720},
                {"format_id": "140", "acodec": "mp4a.40.2", "vcodec": "none"},
            ],
        }

        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is False
        assert data is None

    def test_reuses_video_with_vp9_formats(self, tmp_path):
        """Should return (True, data) for video with VP9 formats"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Video with VP9 codec
        mock_info = {
            "_type": "video",
            "title": "VP9 Video",
            "duration": 150,
            "formats": [
                {"format_id": "248", "vcodec": "vp9", "height": 1080},
                {"format_id": "251", "acodec": "opus", "vcodec": "none"},
            ],
        }

        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is True
        assert data is not None
        assert data["title"] == "VP9 Video"

    def test_always_reuses_playlist(self, tmp_path):
        """Should return (True, data) for playlists regardless of formats"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Playlist (no format check needed)
        mock_playlist = {
            "_type": "playlist",
            "title": "Test Playlist",
            "entries": [{"id": "video1"}, {"id": "video2"}],
        }

        with open(json_path, "w") as f:
            json.dump(mock_playlist, f)

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is True
        assert data is not None
        assert data["_type"] == "playlist"
        assert len(data["entries"]) == 2

    def test_handles_corrupted_json(self, tmp_path):
        """Should return (False, None) for corrupted JSON"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Write invalid JSON
        with open(json_path, "w") as f:
            f.write("{invalid json content")

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is False
        assert data is None

    def test_handles_missing_type_field(self, tmp_path):
        """Should return (False, None) for JSON without _type or duration"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # JSON without _type or duration
        mock_info = {
            "title": "Incomplete Info",
            "formats": [],
        }

        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = should_reuse_url_info(json_path)

        # Should be safe and not reuse
        assert should_reuse is False
        assert data is None

    def test_video_detected_by_duration_field(self, tmp_path):
        """Should detect video type by presence of duration field"""
        from app.url_utils import should_reuse_url_info

        json_path = tmp_path / "url_info.json"

        # Video without explicit _type but with duration
        mock_info = {
            "title": "Video with Duration",
            "duration": 300,
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.05M.08", "height": 1080},
            ],
        }

        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = should_reuse_url_info(json_path)

        assert should_reuse is True
        assert data is not None


class TestSaveUrlInfo:
    """Test save_url_info function"""

    def test_saves_json_successfully(self, tmp_path):
        """Should save URL info to JSON file"""
        from app.url_utils import save_url_info

        json_path = tmp_path / "test_folder" / "url_info.json"

        mock_info = {
            "_type": "video",
            "title": "Test Save",
            "duration": 100,
        }

        success = save_url_info(json_path, mock_info)

        assert success is True
        assert json_path.exists()

        # Verify content
        with open(json_path, "r") as f:
            loaded = json.load(f)

        assert loaded["title"] == "Test Save"
        assert loaded["duration"] == 100

    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories if they don't exist"""
        from app.url_utils import save_url_info

        json_path = tmp_path / "level1" / "level2" / "level3" / "url_info.json"

        mock_info = {"title": "Deep Folder"}

        success = save_url_info(json_path, mock_info)

        assert success is True
        assert json_path.exists()
        assert json_path.parent.exists()

    def test_handles_write_errors_gracefully(self, tmp_path):
        """Should return False if cannot write file"""
        from app.url_utils import save_url_info
        from unittest.mock import patch

        json_path = tmp_path / "url_info.json"
        mock_info = {"title": "Test"}

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            success = save_url_info(json_path, mock_info)

        assert success is False
