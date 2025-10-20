"""Tests for URL info integrity checking"""


class TestCheckUrlInfoIntegrity:
    """Test check_url_info_integrity"""

    def test_with_av1_formats(self):
        """Test that AV1 formats are detected as premium"""
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

        url_info = {
            "formats": [
                {"format_id": "248", "vcodec": "vp9", "height": 1080},
                {"format_id": "137", "vcodec": "avc1.640028", "height": 1080},
            ]
        }

        assert check_url_info_integrity(url_info) is True

    def test_with_only_h264(self):
        """Test that h264-only is detected as limited"""
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

        url_info = {"formats": []}

        assert check_url_info_integrity(url_info) is False

    def test_with_no_formats_key(self):
        """Test with missing formats key"""
        from app.medias_utils import check_url_info_integrity

        url_info = {"title": "Test Video"}

        assert check_url_info_integrity(url_info) is False

    def test_with_error_in_info(self):
        """Test with error in url_info"""
        from app.medias_utils import check_url_info_integrity

        url_info = {"error": "Some error message"}

        assert check_url_info_integrity(url_info) is False

    def test_with_none_input(self):
        """Test with None input"""
        from app.medias_utils import check_url_info_integrity

        assert check_url_info_integrity(None) is False

    def test_vp09_variant(self):
        """Test VP9 with vp09 codec string variant"""
        from app.medias_utils import check_url_info_integrity

        url_info = {
            "formats": [
                {"format_id": "337", "vcodec": "vp09.00.50.08", "height": 2160},
                {"format_id": "136", "vcodec": "avc1.4d401f", "height": 720},
            ]
        }

        assert check_url_info_integrity(url_info) is True

    def test_case_insensitive_codec_check(self):
        """Test that codec check is case-insensitive"""
        from app.medias_utils import check_url_info_integrity

        url_info = {
            "formats": [
                {"format_id": "399", "vcodec": "AV01.0.08M.08", "height": 1080},
            ]
        }

        assert check_url_info_integrity(url_info) is True

    def test_instagram_formats(self):
        """Test with Instagram video formats (typically no premium codecs)"""
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

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
        from app.medias_utils import check_url_info_integrity

        url_info = {
            "formats": [
                {"format_id": "299", "vcodec": "avc1.64002a", "height": 1080},
                {"format_id": "298", "vcodec": "avc1.640028", "height": 720},
                {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2"},
            ]
        }

        assert check_url_info_integrity(url_info) is False
