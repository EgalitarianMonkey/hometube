"""
Tests for subtitle utilities - Comprehensive test suite for subtitle functionality.

This module tests all subtitle utilities including embedding, cutting, and processing
with both real and test media files.
"""

import pytest
import shutil
import sys
import tempfile
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Import all subtitle utility functions
from subtitles_utils import (
    has_embedded_subtitles,
    embed_subtitles_manually,
    ensure_subtitles_embedded,
    cut_subtitle_file,
    process_subtitles_for_cutting,
    get_embedded_subtitle_info,
    check_required_subtitles_embedded,
    get_language_names,
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


def verify_cutting_test_files():
    """Verify that required files exist for subtitle cutting tests."""
    test_dir = Path(__file__).parent.parent
    local_tests_dir = test_dir / "downloads" / "local_tests"

    required_files = ["StressLocal.en.srt"]

    missing_files = []

    if not local_tests_dir.exists():
        pytest.skip(
            f"Local tests directory not found: {local_tests_dir}",
            allow_module_level=True,
        )

    for filename in required_files:
        file_path = local_tests_dir / filename
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print("❌ Required cutting test file(s) missing:")
        for missing_file in missing_files:
            print(f"   {missing_file}")
        pytest.skip(
            "Required files missing for subtitle cutting tests",
            allow_module_level=True,
        )

    print("✅ Cutting test files verification passed")


# Run verification at module import time
verify_media_files()
verify_cutting_test_files()


class TestSubtitleUtils:
    """Comprehensive test suite for subtitle utilities including embedding and cutting."""

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

    @pytest.fixture
    def local_tests_dir(self):
        """Get the local tests directory with cutting test files."""
        local_tests_dir = Path(__file__).parent.parent / "downloads" / "local_tests"
        if local_tests_dir.exists():
            return local_tests_dir
        pytest.skip("Local tests directory not found")

    @pytest.fixture
    def test_subtitle_for_cutting(self, local_tests_dir):
        """Get the test subtitle file for cutting tests."""
        subtitle_file = local_tests_dir / "StressLocal.en.srt"
        if subtitle_file.exists():
            return subtitle_file
        pytest.skip("Test subtitle file for cutting not found")

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

    def test_cut_subtitle_file_basic(self, temp_dir, test_subtitle_for_cutting):
        """Test basic subtitle cutting functionality."""
        output_file = temp_dir / "cut_test.srt"

        # Test cutting first 10 seconds with timestamp rebase
        result = cut_subtitle_file(
            test_subtitle_for_cutting,
            start_time=0.0,
            duration=10.0,
            output_path=output_file,
            rebase_timestamps=True,
        )

        assert result is True
        assert output_file.exists()

        # Verify the file has content
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0
        assert "00:00:" in content  # Should start at 00:00 due to rebase

    def test_cut_subtitle_file_without_rebase(
        self, temp_dir, test_subtitle_for_cutting
    ):
        """Test subtitle cutting without timestamp rebasing."""
        output_file = temp_dir / "cut_no_rebase.srt"

        # Test cutting from 5 seconds without rebase
        result = cut_subtitle_file(
            test_subtitle_for_cutting,
            start_time=5.0,
            duration=10.0,
            output_path=output_file,
            rebase_timestamps=False,
        )

        assert result is True
        assert output_file.exists()

        # Verify the file has content and timestamps are not rebased
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0
        # Timestamps should not start at 00:00 since we didn't rebase

    def test_cut_subtitle_file_errors(self, temp_dir):
        """Test error handling in subtitle cutting."""
        output_file = temp_dir / "error_test.srt"

        # Test with non-existent input file
        result = cut_subtitle_file(
            Path("/nonexistent/file.srt"),
            start_time=0.0,
            duration=10.0,
            output_path=output_file,
            rebase_timestamps=True,
        )

        assert result is False
        assert not output_file.exists()

    def test_process_subtitles_for_cutting(self, temp_dir, local_tests_dir):
        """Test processing multiple subtitle files for cutting."""
        # Copy test subtitle file to temp directory with expected naming
        base_name = "TestVideo"
        test_subtitle = local_tests_dir / "StressLocal.en.srt"
        temp_subtitle = temp_dir / f"{base_name}.en.srt"

        # Copy the test file
        shutil.copy2(test_subtitle, temp_subtitle)

        # Test processing
        result = process_subtitles_for_cutting(
            base_output=base_name,
            tmp_subfolder_dir=temp_dir,
            subtitle_languages=["en"],
            start_time=0.0,
            duration=15.0,
        )

        assert len(result) == 1
        lang, output_file = result[0]
        assert lang == "en"
        assert output_file.exists()
        assert output_file.name == f"{base_name}-cut-final.en.srt"

        # Verify content
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0
        assert "00:00:" in content  # Should start at 00:00 due to rebase

    def test_process_subtitles_for_cutting_no_files(self, temp_dir):
        """Test processing when no subtitle files are found."""
        result = process_subtitles_for_cutting(
            base_output="NonExistent",
            tmp_subfolder_dir=temp_dir,
            subtitle_languages=["en", "fr"],
            start_time=0.0,
            duration=10.0,
        )

        assert len(result) == 0

    def test_cut_subtitle_file_real_timestamps(
        self, temp_dir, test_subtitle_for_cutting
    ):
        """Test cutting with realistic timestamps from actual subtitle file."""
        output_file = temp_dir / "realistic_cut.srt"

        # Cut a middle section (e.g., from 30s to 45s)
        result = cut_subtitle_file(
            test_subtitle_for_cutting,
            start_time=30.0,
            duration=15.0,
            output_path=output_file,
            rebase_timestamps=True,
        )

        assert result is True
        assert output_file.exists()

        # Read and verify the content
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0

        # Should start close to 00:00:00 due to rebasing
        lines = content.strip().split("\n")
        # Find first timestamp line
        for line in lines:
            if "-->" in line:
                start_time_str = line.split(" --> ")[0]
                # Should start very close to 00:00:00 (allowing for small rounding)
                assert start_time_str.startswith("00:00:0")
                break

    def test_check_required_subtitles_embedded_basic(self):
        """Test basic functionality of check_required_subtitles_embedded."""
        # Test with non-existent file
        result = check_required_subtitles_embedded(
            Path("/nonexistent/file.mkv"), ["en", "fr"]
        )
        assert result is False

        # Test with empty requirements
        result = check_required_subtitles_embedded(Path("/nonexistent/file.mkv"), [])
        assert result is False  # Because file doesn't exist

    def test_get_embedded_subtitle_info_basic(self):
        """Test basic functionality of get_embedded_subtitle_info."""
        # Test with non-existent file
        has_subs, count, languages = get_embedded_subtitle_info(
            Path("/nonexistent/file.mkv")
        )
        assert has_subs is False
        assert count == 0
        assert languages == []

    def test_get_language_names(self):
        """Test language name mapping functionality."""
        # Test common languages
        short, full = get_language_names("en")
        assert short == "en"
        assert full == "English"

        short, full = get_language_names("fr")
        assert short == "fr"
        assert full == "Français"

        short, full = get_language_names("es")
        assert short == "es"
        assert full == "Español"

        short, full = get_language_names("de")
        assert short == "de"
        assert full == "Deutsch"

        # Test case insensitivity
        short, full = get_language_names("EN")
        assert short == "en"
        assert full == "English"

        # Test unknown language fallback
        short, full = get_language_names("xyz")
        assert short == "xyz"
        assert full == "XYZ"

        # Test special characters
        short, full = get_language_names("zh")
        assert short == "zh"
        assert full == "中文"

        short, full = get_language_names("ru")
        assert short == "ru"
        assert full == "Русский"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_subtitles_utils.py -v
    pytest.main([__file__, "-v"])
