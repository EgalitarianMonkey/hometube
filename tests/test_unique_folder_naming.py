"""
Tests for unique video folder naming from URLs
"""

from app.file_system_utils import get_unique_video_folder_name_from_url


class TestGetUniqueFolderName:
    """Test unique folder name generation from various URL formats"""

    def test_youtube_standard_url(self):
        """Test standard YouTube watch URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-dQw4w9WgXcQ"

    def test_youtube_with_extra_params(self):
        """Test YouTube URL with extra parameters"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLtest"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-dQw4w9WgXcQ"

    def test_youtube_short_url(self):
        """Test YouTube short URL (youtu.be)"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-dQw4w9WgXcQ"

    def test_youtube_short_url_with_params(self):
        """Test YouTube short URL with timestamp"""
        url = "https://youtu.be/dQw4w9WgXcQ?t=42"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-dQw4w9WgXcQ"

    def test_youtube_shorts(self):
        """Test YouTube Shorts URL"""
        url = "https://www.youtube.com/shorts/abc123XYZ"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-shorts-abc123XYZ"

    def test_youtube_mobile_url(self):
        """Test YouTube mobile URL"""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-dQw4w9WgXcQ"

    def test_instagram_post(self):
        """Test Instagram post URL"""
        url = "https://www.instagram.com/p/ABC123def456/"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "instagram-ABC123def456"

    def test_instagram_reel(self):
        """Test Instagram reel URL"""
        url = "https://www.instagram.com/reel/XYZ789abc012/"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "instagram-XYZ789abc012"

    def test_instagram_tv(self):
        """Test Instagram TV URL"""
        url = "https://www.instagram.com/tv/QWE456rty789/"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "instagram-QWE456rty789"

    def test_tiktok_standard(self):
        """Test TikTok video URL"""
        url = "https://www.tiktok.com/@username/video/1234567890123456789"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "tiktok-1234567890123456789"

    def test_tiktok_short_vm(self):
        """Test TikTok short URL (vm.tiktok.com)"""
        url = "https://vm.tiktok.com/ZMeAbCdEf/"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "tiktok-ZMeAbCdEf"

    def test_tiktok_short_vt(self):
        """Test TikTok short URL (vt.tiktok.com)"""
        url = "https://vt.tiktok.com/XYZ123abc/"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "tiktok-XYZ123abc"

    def test_vimeo(self):
        """Test Vimeo URL"""
        url = "https://vimeo.com/123456789"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "vimeo-123456789"

    def test_dailymotion(self):
        """Test Dailymotion URL"""
        url = "https://www.dailymotion.com/video/x8abc123"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "dailymotion-x8abc123"

    def test_unknown_platform_same_url(self):
        """Test that unknown platforms generate consistent hashes"""
        url = "https://example.com/some/video/path"
        result1 = get_unique_video_folder_name_from_url(url)
        result2 = get_unique_video_folder_name_from_url(url)

        # Should start with generic-
        assert result1.startswith("generic-")
        # Same URL should produce same result
        assert result1 == result2

    def test_unknown_platform_different_urls(self):
        """Test that different unknown URLs generate different hashes"""
        url1 = "https://example.com/video/1"
        url2 = "https://example.com/video/2"
        result1 = get_unique_video_folder_name_from_url(url1)
        result2 = get_unique_video_folder_name_from_url(url2)

        # Different URLs should produce different results
        assert result1 != result2

    def test_empty_url(self):
        """Test handling of empty URL"""
        result = get_unique_video_folder_name_from_url("")
        assert result == "unknown"

    def test_none_url(self):
        """Test handling of None URL"""
        result = get_unique_video_folder_name_from_url(None)
        assert result == "unknown"

    def test_consistency(self):
        """Test that same URL always produces same folder name"""
        url = "https://www.youtube.com/watch?v=0icDTxgKu44"
        results = [get_unique_video_folder_name_from_url(url) for _ in range(5)]

        # All results should be identical
        assert len(set(results)) == 1
        assert results[0] == "youtube-0icDTxgKu44"

    def test_real_world_youtube_example(self):
        """Test with the example from user's request"""
        url = "https://www.youtube.com/watch?v=0icDTxgKu44"
        result = get_unique_video_folder_name_from_url(url)
        assert result == "youtube-0icDTxgKu44"

    def test_folder_name_is_filesystem_safe(self):
        """Test that generated folder names are filesystem safe"""
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.instagram.com/p/ABC123/",
            "https://www.tiktok.com/@user/video/123456",
            "https://vimeo.com/987654321",
        ]

        for url in test_urls:
            result = get_unique_video_folder_name_from_url(url)
            # Should not contain problematic characters
            assert not any(char in result for char in '<>:"/\\|?*')
            # Should not be empty
            assert len(result) > 0
            # Should only contain safe characters
            assert all(char.isalnum() or char in "-_" for char in result)
