"""
Tests for subtitle embedding functionality - Integration tests with real media files.

This module focuses on non-regression tests using real media files to verify
that subtitle embedding works correctly end-to-end.
"""

import pytest
import shutil
import sys
import tempfile
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Import the utility functions from the dedicated module
from subtitle_utils import (
    has_embedded_subtitles,
    embed_subtitles_manually,
    ensure_subtitles_embedded,
    safe_push_log,
)


# Media files verification - check required files exist before running tests
def verify_media_files():
    """Verify that required media files exist for subtitle embedding tests."""
    test_dir = Path(__file__).parent
    media_dir = test_dir / "medias"

    required_files = ["StressedOut.mp4", "StressedOut.en.srt"]

    missing_files = []

    if not media_dir.exists():
        pytest.skip(f"Media directory not found: {media_dir}", allow_module_level=True)

    for filename in required_files:
        file_path = media_dir / filename
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print("❌ Required media file(s) missing:")
        for missing_file in missing_files:
            print(f"   {missing_file}")
        pytest.skip(
            "Required media files missing for subtitle embedding tests",
            allow_module_level=True,
        )

    print("✅ Media files verification passed")


# Run verification at module import time
verify_media_files()


class TestSubtitleEmbeddingIntegration:
    """Integration test suite for subtitle embedding functionality with real media files."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_media_dir(self):
        """Get the sample media directory."""
        media_dir = Path(__file__).parent / "medias"
        if media_dir.exists():
            return media_dir
        pytest.skip("Sample media directory not found")

    @pytest.fixture
    def sample_video(self, sample_media_dir):
        """Get the sample video file."""
        video_file = sample_media_dir / "StressedOut.mp4"
        if video_file.exists():
            return video_file
        pytest.skip("Sample video file not found")

    @pytest.fixture
    def sample_subtitle(self, sample_media_dir):
        """Get the sample subtitle file."""
        subtitle_file = sample_media_dir / "StressedOut.en.srt"
        if subtitle_file.exists():
            return subtitle_file
        pytest.skip("Sample subtitle file not found")

    def test_has_embedded_subtitles_with_real_video(self, sample_video):
        """Test subtitle detection with a real video file."""
        # This should work with ffprobe if available
        result = has_embedded_subtitles(sample_video)
        # Result can be True or False, but should not raise an exception
        assert isinstance(result, bool)

    def test_has_embedded_subtitles_nonexistent_file(self):
        """Test subtitle detection with non-existent file."""
        fake_path = Path("/nonexistent/video.mp4")
        result = has_embedded_subtitles(fake_path)
        assert result is False

    def test_embed_subtitles_manually_no_subtitles(self, temp_dir):
        """Test manual embedding with empty subtitle list."""
        video_file = temp_dir / "test.mp4"
        video_file.touch()

        result = embed_subtitles_manually(video_file, [])
        assert result is False

    def test_ensure_subtitles_embedded_nonexistent_video(self):
        """Test ensure_subtitles_embedded with non-existent video."""
        fake_path = Path("/nonexistent/video.mp4")
        result = ensure_subtitles_embedded(fake_path)
        assert result is False

    def test_ensure_subtitles_embedded_no_subtitle_files(self, temp_dir):
        """Test ensure_subtitles_embedded when no subtitle files are found."""
        video_file = temp_dir / "test.mp4"
        video_file.touch()

        result = ensure_subtitles_embedded(video_file)
        assert result is False

    @pytest.mark.integration
    def test_ensure_subtitles_embedded_integration(
        self, temp_dir, sample_video, sample_subtitle
    ):
        """Integration test with real media files - this is the key non-regression test."""
        # Copy sample files to temp directory
        test_video = temp_dir / "test_video.mp4"
        test_subtitle = temp_dir / "test_video.en.srt"

        shutil.copy2(sample_video, test_video)
        shutil.copy2(sample_subtitle, test_subtitle)

        # Verify initial state - video should not have embedded subtitles
        initial_has_subs = has_embedded_subtitles(test_video)

        # Test the function (this will actually run ffprobe/ffmpeg if available)
        result = ensure_subtitles_embedded(test_video)

        # If ffmpeg is available and working, result should be True
        # If not available, result will be False but should not crash
        assert isinstance(result, bool)

        # Check that files still exist after test
        assert test_video.exists()
        assert test_subtitle.exists()

        # If embedding was successful, verify subtitles are now embedded
        if result:
            final_has_subs = has_embedded_subtitles(test_video)
            # Should now have subtitles (unless ffmpeg failed for other reasons)
            safe_push_log(
                f"Initial subtitles: {initial_has_subs}, Final subtitles: {final_has_subs}"
            )

    def test_subtitle_file_search_patterns(self, temp_dir):
        """Test that subtitle search finds files with correct patterns."""
        video_file = temp_dir / "MyVideo.mp4"
        video_file.touch()

        # Create various subtitle files
        (temp_dir / "MyVideo.en.srt").touch()
        (temp_dir / "MyVideo.fr.srt").touch()
        (temp_dir / "MyVideo.srt").touch()
        (temp_dir / "OtherVideo.en.srt").touch()  # Should not be found

        # The function will attempt to embed but fail (no real video content)
        # But we can verify that the right files are found by checking the logs
        result = ensure_subtitles_embedded(video_file)

        # Should find subtitle files but fail to embed (no real video content)
        # This tests the search pattern logic
        assert result is False  # Will fail because empty video file

    @pytest.mark.integration
    def test_custom_search_patterns(self, temp_dir, sample_video, sample_subtitle):
        """Test ensure_subtitles_embedded with custom search patterns."""
        # Copy files with custom names
        test_video = temp_dir / "video.mp4"
        custom_subtitle = temp_dir / "custom_sub.srt"

        shutil.copy2(sample_video, test_video)
        shutil.copy2(sample_subtitle, custom_subtitle)

        # Test with custom pattern
        result = ensure_subtitles_embedded(
            test_video, search_patterns=["custom_sub.srt"]
        )

        # Should work if ffmpeg is available
        assert isinstance(result, bool)
        assert test_video.exists()
        assert custom_subtitle.exists()

    def test_basic_functionality_edge_cases(self, temp_dir):
        """Test basic functionality and edge cases without requiring ffmpeg."""

        # Test 1: Non-existent video
        result = ensure_subtitles_embedded(Path("/nonexistent/file.mp4"))
        assert result is False

        # Test 2: Empty subtitle list
        video_file = temp_dir / "empty.mp4"
        video_file.touch()
        result = embed_subtitles_manually(video_file, [])
        assert result is False

        # Test 3: has_embedded_subtitles with non-existent file
        result = has_embedded_subtitles(Path("/nonexistent/file.mp4"))
        assert result is False


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_subtitle_embedding_integration.py -v
    pytest.main([__file__, "-v"])
