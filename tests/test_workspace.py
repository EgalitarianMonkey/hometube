"""Tests for workspace module - centralized workspace management."""

from app.workspace import (
    parse_url,
    get_video_workspace,
    get_playlist_workspace,
    get_workspace_from_url,
    ensure_video_workspace,
    ensure_playlist_workspace,
    ensure_workspace_from_url,
    get_legacy_folder_name,
    extract_platform_and_id,
)


class TestParseUrl:
    """Test URL parsing functionality."""

    def test_youtube_video(self):
        """Test parsing YouTube video URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        info = parse_url(url)
        assert info.platform == "youtube"
        assert info.id == "dQw4w9WgXcQ"
        assert info.type == "video"

    def test_youtube_short_url(self):
        """Test parsing youtu.be short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        info = parse_url(url)
        assert info.platform == "youtube"
        assert info.id == "dQw4w9WgXcQ"
        assert info.type == "video"

    def test_youtube_shorts(self):
        """Test parsing YouTube Shorts URL."""
        url = "https://www.youtube.com/shorts/abc123XYZ"
        info = parse_url(url)
        assert info.platform == "youtube"
        assert info.id == "abc123XYZ"
        assert info.type == "video"

    def test_youtube_playlist(self):
        """Test parsing YouTube playlist URL."""
        url = "https://www.youtube.com/playlist?list=PLxxxxxx"
        info = parse_url(url)
        assert info.platform == "youtube"
        assert info.id == "PLxxxxxx"
        assert info.type == "playlist"

    def test_instagram(self):
        """Test parsing Instagram URL."""
        url = "https://www.instagram.com/p/ABC123/"
        info = parse_url(url)
        assert info.platform == "instagram"
        assert info.id == "ABC123"
        assert info.type == "video"

    def test_tiktok(self):
        """Test parsing TikTok URL."""
        url = "https://www.tiktok.com/@user/video/1234567890"
        info = parse_url(url)
        assert info.platform == "tiktok"
        assert info.id == "1234567890"
        assert info.type == "video"

    def test_vimeo(self):
        """Test parsing Vimeo URL."""
        url = "https://vimeo.com/123456789"
        info = parse_url(url)
        assert info.platform == "vimeo"
        assert info.id == "123456789"
        assert info.type == "video"

    def test_empty_url(self):
        """Test parsing empty URL."""
        info = parse_url("")
        assert info.platform == "unknown"
        assert info.id == "unknown"
        assert info.type == "video"

    def test_none_url(self):
        """Test parsing None URL."""
        info = parse_url(None)
        assert info.platform == "unknown"
        assert info.id == "unknown"
        assert info.type == "video"


class TestWorkspacePaths:
    """Test workspace path generation."""

    def test_video_workspace_path(self, tmp_path):
        """Test video workspace path generation."""
        workspace = get_video_workspace(tmp_path, "youtube", "abc123")
        expected = tmp_path / "videos" / "youtube" / "abc123"
        assert workspace == expected

    def test_playlist_workspace_path(self, tmp_path):
        """Test playlist workspace path generation."""
        workspace = get_playlist_workspace(tmp_path, "youtube", "PLxxx")
        expected = tmp_path / "playlists" / "youtube" / "PLxxx"
        assert workspace == expected

    def test_workspace_from_video_url(self, tmp_path):
        """Test getting workspace from video URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        workspace = get_workspace_from_url(tmp_path, url)
        expected = tmp_path / "videos" / "youtube" / "dQw4w9WgXcQ"
        assert workspace == expected

    def test_workspace_from_playlist_url(self, tmp_path):
        """Test getting workspace from playlist URL."""
        url = "https://www.youtube.com/playlist?list=PLxxx"
        workspace = get_workspace_from_url(tmp_path, url)
        expected = tmp_path / "playlists" / "youtube" / "PLxxx"
        assert workspace == expected


class TestEnsureWorkspace:
    """Test workspace creation functionality."""

    def test_ensure_video_workspace_creates_directory(self, tmp_path):
        """Test that ensure_video_workspace creates the directory."""
        workspace = ensure_video_workspace(tmp_path, "youtube", "abc123")
        assert workspace.exists()
        assert workspace.is_dir()
        assert workspace == tmp_path / "videos" / "youtube" / "abc123"

    def test_ensure_playlist_workspace_creates_directory(self, tmp_path):
        """Test that ensure_playlist_workspace creates the directory."""
        workspace = ensure_playlist_workspace(tmp_path, "youtube", "PLxxx")
        assert workspace.exists()
        assert workspace.is_dir()
        assert workspace == tmp_path / "playlists" / "youtube" / "PLxxx"

    def test_ensure_workspace_from_url(self, tmp_path):
        """Test ensure_workspace_from_url for video."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        workspace, info = ensure_workspace_from_url(tmp_path, url)
        assert workspace.exists()
        assert info.platform == "youtube"
        assert info.id == "dQw4w9WgXcQ"
        assert info.type == "video"

    def test_ensure_workspace_from_playlist_url(self, tmp_path):
        """Test ensure_workspace_from_url for playlist."""
        url = "https://www.youtube.com/playlist?list=PLxxx"
        workspace, info = ensure_workspace_from_url(tmp_path, url)
        assert workspace.exists()
        assert info.type == "playlist"


class TestVideoSharing:
    """Test that videos are shared between playlist and individual downloads."""

    def test_same_video_same_workspace(self, tmp_path):
        """Test that the same video always gets the same workspace."""
        video_id = "dQw4w9WgXcQ"

        # Simulate individual video download
        individual_workspace = ensure_video_workspace(tmp_path, "youtube", video_id)

        # Simulate playlist video download (same video)
        playlist_workspace = ensure_video_workspace(tmp_path, "youtube", video_id)

        # They should be the same path
        assert individual_workspace == playlist_workspace

    def test_video_in_playlist_uses_videos_folder(self, tmp_path):
        """Test that videos in playlists are stored in videos/ not playlists/."""
        video_id = "dQw4w9WgXcQ"
        workspace = ensure_video_workspace(tmp_path, "youtube", video_id)

        # Should be in videos/, not playlists/
        assert "videos" in str(workspace)
        assert "playlists" not in str(workspace)


class TestLegacyCompatibility:
    """Test legacy folder name generation for backward compatibility."""

    def test_legacy_youtube_video(self):
        """Test legacy folder name for YouTube video."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        name = get_legacy_folder_name(url)
        assert name == "youtube-dQw4w9WgXcQ"

    def test_legacy_youtube_playlist(self):
        """Test legacy folder name for YouTube playlist."""
        url = "https://www.youtube.com/playlist?list=PLxxx"
        name = get_legacy_folder_name(url)
        assert name == "youtube-playlist-PLxxx"

    def test_legacy_youtube_shorts(self):
        """Test legacy folder name for YouTube Shorts."""
        url = "https://www.youtube.com/shorts/abc123"
        name = get_legacy_folder_name(url)
        assert name == "youtube-shorts-abc123"

    def test_legacy_empty_url(self):
        """Test legacy folder name for empty URL."""
        name = get_legacy_folder_name("")
        assert name == "unknown"

    def test_legacy_none_url(self):
        """Test legacy folder name for None URL."""
        name = get_legacy_folder_name(None)
        assert name == "unknown"

    def test_extract_platform_and_id_video(self):
        """Test extracting platform and ID from legacy video folder name."""
        result = extract_platform_and_id("youtube-dQw4w9WgXcQ")
        assert result == ("youtube", "dQw4w9WgXcQ", "video")

    def test_extract_platform_and_id_playlist(self):
        """Test extracting platform and ID from legacy playlist folder name."""
        result = extract_platform_and_id("youtube-playlist-PLxxx")
        assert result == ("youtube", "PLxxx", "playlist")

    def test_extract_platform_and_id_shorts(self):
        """Test extracting platform and ID from legacy shorts folder name."""
        result = extract_platform_and_id("youtube-shorts-abc123")
        # youtube-shorts gets normalized to youtube
        assert result == ("youtube", "abc123", "video")
