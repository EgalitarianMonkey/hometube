"""Tests for URL utilities (url_utils.py)

This module tests:
- URL info integrity checking (check_url_info_integrity)
- URL info reuse logic (is_url_info_complet)
- URL info save/load functions
"""

import json

from app.url_utils import check_url_info_integrity


class TestCheckUrlInfoIntegrity:
    """Test check_url_info_integrity - detects premium vs limited formats"""

    def test_with_av1_formats(self):
        """Test that AV1 formats are detected as premium"""
        url_info = {
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.08M.08", "height": 1080},
                {"format_id": "248", "vcodec": "vp9", "height": 1080},
                {"format_id": "137", "vcodec": "avc1.640028", "height": 1080},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_with_vp9_formats(self):
        """Test that VP9 formats are detected as premium"""
        url_info = {
            "formats": [
                {"format_id": "248", "vcodec": "vp9", "height": 1080},
                {"format_id": "137", "vcodec": "avc1.640028", "height": 1080},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_vp09_variant(self):
        """Test VP9 with vp09 codec string variant"""
        url_info = {
            "formats": [
                {"format_id": "337", "vcodec": "vp09.00.50.08", "height": 2160},
                {"format_id": "136", "vcodec": "avc1.4d401f", "height": 720},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_with_only_h264(self):
        """Test that h264-only is detected as limited"""
        url_info = {
            "formats": [
                {"format_id": "137", "vcodec": "avc1.640028", "height": 1080},
                {"format_id": "136", "vcodec": "avc1.4d401f", "height": 720},
                {"format_id": "135", "vcodec": "avc1.4d401e", "height": 480},
            ]
        }
        assert check_url_info_integrity(url_info) is False

    def test_with_mixed_formats(self):
        """Test with mix of video and audio formats"""
        url_info = {
            "formats": [
                # Video formats
                {"format_id": "399", "vcodec": "av01.0.08M.08", "height": 1080},
                {"format_id": "137", "vcodec": "avc1.640028", "height": 1080},
                # Audio formats (should be ignored)
                {"format_id": "251", "vcodec": "none", "acodec": "opus"},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2"},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_with_audio_only(self):
        """Test with audio-only formats"""
        url_info = {
            "formats": [
                {"format_id": "251", "vcodec": "none", "acodec": "opus"},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2"},
            ]
        }
        # Should return False as no video formats with premium codecs
        assert check_url_info_integrity(url_info) is False

    def test_with_empty_formats(self):
        """Test with empty formats list"""
        url_info = {"formats": []}
        assert check_url_info_integrity(url_info) is False

    def test_with_no_formats_key(self):
        """Test with missing formats key"""
        url_info = {"title": "Test Video"}
        assert check_url_info_integrity(url_info) is False

    def test_with_error_in_info(self):
        """Test with error in url_info"""
        url_info = {"error": "Some error message"}
        assert check_url_info_integrity(url_info) is False

    def test_with_none_input(self):
        """Test with None input"""
        assert check_url_info_integrity(None) is False

    def test_case_insensitive_codec_check(self):
        """Test that codec check is case-insensitive"""
        url_info = {
            "formats": [
                {"format_id": "399", "vcodec": "AV01.0.08M.08", "height": 1080},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_instagram_formats(self):
        """Test with Instagram video formats (typically no premium codecs)"""
        url_info = {
            "formats": [
                {
                    "format_id": "dash-Base+Aud",
                    "vcodec": "avc1.4D401E",
                    "height": 480,
                },
            ]
        }
        assert check_url_info_integrity(url_info) is False

    def test_real_world_youtube_premium(self):
        """Test with realistic YouTube premium formats"""
        url_info = {
            "formats": [
                # Premium formats
                {"format_id": "701", "vcodec": "av01.0.12M.08", "height": 2160},
                {"format_id": "337", "vcodec": "vp9.2", "height": 2160},
                # Standard formats
                {"format_id": "299", "vcodec": "avc1.64002a", "height": 1080},
                # Audio
                {"format_id": "251", "vcodec": "none", "acodec": "opus"},
            ]
        }
        assert check_url_info_integrity(url_info) is True

    def test_real_world_youtube_limited(self):
        """Test with realistic YouTube limited response (h264 only)"""
        url_info = {
            "formats": [
                {"format_id": "299", "vcodec": "avc1.64002a", "height": 1080},
                {"format_id": "298", "vcodec": "avc1.640028", "height": 720},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2"},
            ]
        }
        assert check_url_info_integrity(url_info) is False


class TestIsUrlInfoComplet:
    """Test is_url_info_complet logic (pure function, no Streamlit)"""

    def test_file_not_exists_returns_false(self, tmp_path):
        """Should return (False, None) if file doesn't exist"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "nonexistent" / "url_info.json"
        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is False
        assert data is None

    def test_reuses_video_with_premium_formats(self, tmp_path):
        """Should return (True, data) for video with AV1 formats"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
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

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is True
        assert data is not None
        assert data["title"] == "Test Video"

    def test_does_not_reuse_video_with_only_h264(self, tmp_path):
        """Should return (False, None) for video with only h264 formats"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
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

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is False
        assert data is None

    def test_reuses_video_with_vp9_formats(self, tmp_path):
        """Should return (True, data) for video with VP9 formats"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
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

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is True
        assert data is not None

    def test_always_reuses_playlist(self, tmp_path):
        """Should return (True, data) for playlists regardless of formats"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
        mock_playlist = {
            "_type": "playlist",
            "title": "Test Playlist",
            "entries": [{"id": "video1"}, {"id": "video2"}],
        }
        with open(json_path, "w") as f:
            json.dump(mock_playlist, f)

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is True
        assert data is not None
        assert data["_type"] == "playlist"

    def test_handles_corrupted_json(self, tmp_path):
        """Should return (False, None) for corrupted JSON"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
        with open(json_path, "w") as f:
            f.write("{invalid json content")

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is False
        assert data is None

    def test_handles_missing_type_field(self, tmp_path):
        """Should return (False, None) for JSON without _type or duration"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
        mock_info = {"title": "Incomplete Info", "formats": []}
        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is False
        assert data is None

    def test_video_detected_by_duration_field(self, tmp_path):
        """Should detect video type by presence of duration field"""
        from app.url_utils import is_url_info_complet

        json_path = tmp_path / "url_info.json"
        mock_info = {
            "title": "Video with Duration",
            "duration": 300,
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.05M.08", "height": 1080},
            ],
        }
        with open(json_path, "w") as f:
            json.dump(mock_info, f)

        should_reuse, data = is_url_info_complet(json_path)

        assert should_reuse is True
        assert data is not None


class TestSaveUrlInfo:
    """Test save_url_info function"""

    def test_saves_json_successfully(self, tmp_path):
        """Should save URL info to JSON file"""
        from app.url_utils import save_url_info

        json_path = tmp_path / "test_folder" / "url_info.json"
        mock_info = {"_type": "video", "title": "Test Save", "duration": 100}

        success = save_url_info(json_path, mock_info)

        assert success is True
        assert json_path.exists()

        with open(json_path, "r") as f:
            loaded = json.load(f)
        assert loaded["title"] == "Test Save"

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

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            success = save_url_info(json_path, mock_info)

        assert success is False
