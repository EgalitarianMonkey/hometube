"""
Simplified tests for HomeTube main functions.
Focus on non-regression with essential tests.
"""

import tempfile
from pathlib import Path


class TestCoreFunctions:
    """Main utility function tests."""

    def test_sanitize_filename(self):
        """Test sanitize_filename function."""
        from app.file_system_utils import sanitize_filename

        # Normal cases
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file with spaces.mp4") == "file with spaces.mp4"

        # Forbidden characters
        assert sanitize_filename('file<>:"/\\|?*.txt') == "file_________.txt"

        # Edge cases
        assert sanitize_filename("") == ""
        assert (
            sanitize_filename("   ") == "unnamed"
        )  # Function returns "unnamed" for spaces
        assert sanitize_filename("...") == "unnamed"

    def test_parse_time_like(self):
        """Test parse_time_like function."""
        from app.display_utils import parse_time_like

        # Simple formats
        assert parse_time_like("60") == 60
        assert parse_time_like("1:30") == 90
        assert parse_time_like("1:23:45") == 5025

        # Edge cases
        assert parse_time_like("") is None
        assert parse_time_like("invalid") is None

        # Spaces
        assert parse_time_like("  1:30  ") == 90

    def test_fmt_hhmmss(self):
        """Test fmt_hhmmss function."""
        from app.display_utils import fmt_hhmmss

        assert fmt_hhmmss(0) == "00:00:00"
        assert fmt_hhmmss(60) == "00:01:00"
        assert fmt_hhmmss(3661) == "01:01:01"
        assert fmt_hhmmss(-1) == "00:00:00"

    def test_is_valid_browser(self):
        """Test is_valid_browser function."""
        from app.file_system_utils import is_valid_browser

        # Valid browsers
        assert is_valid_browser("chrome") is True
        assert is_valid_browser("firefox") is True
        assert is_valid_browser("CHROME") is True  # Case insensitive

        # Invalid browsers
        assert is_valid_browser("invalid") is False
        assert is_valid_browser("") is False
        assert is_valid_browser("   ") is False

    # test_extract_resolution_value REMOVED - function deprecated and removed from codebase

    def test_video_id_from_url(self):
        """Test video_id_from_url function."""
        from app.medias_utils import video_id_from_url

        # Valid YouTube URLs
        assert (
            video_id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )
        assert video_id_from_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # Invalid URLs
        assert video_id_from_url("") == ""
        assert video_id_from_url("https://example.com") == ""

    def test_sanitize_url(self):
        """Test sanitize_url function."""
        from app.url_utils import sanitize_url

        assert sanitize_url("example.com") == "https://example.com"
        assert sanitize_url("https://example.com") == "https://example.com"
        assert sanitize_url("") == ""
        assert sanitize_url("   example.com   ") == "https://example.com"

    def test_invert_segments_basic(self):
        """Basic test of invert_segments function."""
        from app.cut_utils import invert_segments_tuples

        # Simple test
        segments = [(10, 20), (30, 40)]
        result = invert_segments_tuples(segments, 50)
        expected = [(0, 10), (20, 30), (40, 50)]
        assert result == expected

        # Contiguous segments
        segments = [(0, 10), (10, 20)]
        result = invert_segments_tuples(segments, 30)
        expected = [(20, 30)]
        assert result == expected

    def test_invert_segments_empty(self):
        """Test invert_segments with edge cases."""
        from app.cut_utils import invert_segments_tuples

        # Empty list
        assert invert_segments_tuples([], 100) == [(0, 100)]

        # Zero duration
        assert invert_segments_tuples([(10, 20)], 0) == []

    def test_is_valid_cookie_file(self):
        """Test is_valid_cookie_file function."""
        from app.file_system_utils import is_valid_cookie_file

        # Basic cases
        assert is_valid_cookie_file("") is False
        assert is_valid_cookie_file("/nonexistent/file.txt") is False

        # Test with temporary file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"# Cookie file content")
            tmp.flush()
            assert is_valid_cookie_file(tmp.name) is True

        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    def test_build_base_ytdlp_command_regression(self):
        """Test build_base_ytdlp_command to prevent regressions in command building."""
        import pytest

        # Skip this test due to Streamlit dependencies in main.py
        # The functionality is covered by end-to-end tests instead
        pytest.skip("Skipping due to Streamligt dependencies - tested in e2e tests")

    def test_sponsorblock_segments_processing_regression(self):
        """Test SponsorBlock segments processing to prevent regressions."""
        import pytest

        # Skip this test due to Streamlit dependencies in main.py
        pytest.skip("Skipping due to Streamlit dependencies - tested in e2e tests")

    def test_time_parsing_edge_cases_regression(self):
        """Test time parsing edge cases to prevent regressions."""
        from app.display_utils import parse_time_like, fmt_hhmmss

        # Test edge cases that could break
        edge_cases = [
            ("0", 0),
            ("59", 59),
            ("1:00", 60),
            ("1:59", 119),
            ("59:59", 3599),
            ("1:00:00", 3600),
            ("1:01:01", 3661),
            ("10:30:45", 37845),
        ]

        for time_str, expected_seconds in edge_cases:
            result = parse_time_like(time_str)
            assert (
                result == expected_seconds
            ), f"'{time_str}' should parse to {expected_seconds}s, got {result}s"

            # Test reverse conversion
            formatted = fmt_hhmmss(expected_seconds)
            # Should be able to parse back (allowing for format differences)
            reparsed = parse_time_like(formatted)
            assert reparsed == expected_seconds, f"Round-trip failed for {time_str}"

    def test_filename_sanitization_edge_cases_regression(self):
        """Test filename sanitization edge cases to prevent regressions."""
        from app.file_system_utils import sanitize_filename

        # Critical edge cases that could break file operations
        edge_cases = [
            # (input, description, custom_check)
            (
                "file" + "." * 100,
                "Too many dots",
                lambda r: r != "",
            ),  # Should handle gracefully
            (
                "A" * 300,
                "Very long name",
                lambda r: len(r) <= 200,
            ),  # Should be truncated
            (
                "файл.mp4",
                "Unicode characters",
                lambda r: r != "",
            ),  # Should not be empty
            ("🎬🎵video🔥.mkv", "Emojis", lambda r: r != ""),  # Should not be empty
            (
                " . .. ... .... ",
                "Only dots and spaces",
                lambda r: r != "",
            ),  # Should handle gracefully
            (
                "normal-file_name.mp4",
                "Normal case",
                lambda r: "normal" in r and "file" in r,
            ),  # Should preserve normal parts
            # Note: Windows reserved names like CON, PRN are platform-specific issues
            # Current implementation doesn't handle them, but could be enhanced later
        ]

        for test_input, description, custom_check in edge_cases:
            result = sanitize_filename(test_input)

            # Should not be empty (unless input was empty)
            if test_input.strip():
                assert (
                    result
                ), f"Non-empty input '{test_input}' ({description}) should not produce empty result"

            # Apply custom check if provided
            if custom_check:
                assert custom_check(
                    result
                ), f"Input '{test_input}' ({description}) failed custom check. Got: '{result}'"

            # Result should be safe for filesystem
            forbidden_chars = '<>:"/\\|?*'
            for char in forbidden_chars:
                assert (
                    char not in result
                ), f"Result '{result}' should not contain forbidden char '{char}'"

            # Should not be too long (filesystem limits)
            assert (
                len(result) <= 255
            ), f"Result '{result}' should not exceed 255 characters"
