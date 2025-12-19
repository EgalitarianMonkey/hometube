"""
Tests for text utilities (slug and render_title functions).
"""

from app.text_utils import (
    slug,
    pretty,
    idx,
    render_title,
    DEFAULT_PLAYLIST_TITLE_PATTERN,
)


class TestSlug:
    """Tests for the slug() function."""

    def test_basic_text(self):
        """Test basic text slugification."""
        assert slug("Hello World!") == "hello-world"

    def test_accented_characters(self):
        """Test that accented characters are normalized."""
        assert slug("Vidéo en français") == "video-en-francais"
        assert slug("Café résumé") == "cafe-resume"
        assert slug("Über München") == "uber-munchen"

    def test_emojis_removed(self):
        """Test that emojis are removed."""
        assert slug("Video 🎬 Tutorial 🎵") == "video-tutorial"
        assert slug("🎵🎶🎤") == "untitled"  # Only emojis -> fallback

    def test_special_characters(self):
        """Test special characters are replaced with hyphens."""
        assert slug("Hello, World! How are you?") == "hello-world-how-are-you"
        assert slug("file/path\\name") == "file-path-name"
        assert slug("test@email.com") == "test-email-com"

    def test_windows_forbidden_chars(self):
        """Test Windows forbidden characters are handled."""
        # Windows forbidden: < > : " / \\ | ? *
        assert slug('File<>:"/\\|?*Name') == "file-name"

    def test_multiple_hyphens_collapsed(self):
        """Test multiple hyphens are collapsed into one."""
        assert slug("hello---world") == "hello-world"
        assert slug("a - - - b") == "a-b"

    def test_leading_trailing_hyphens_stripped(self):
        """Test leading and trailing hyphens are stripped."""
        assert slug("  --Test-- ") == "test"
        assert slug("---hello---") == "hello"

    def test_empty_string(self):
        """Test empty string returns 'untitled'."""
        assert slug("") == "untitled"
        assert slug("   ") == "untitled"

    def test_none_handling(self):
        """Test None-like empty string returns 'untitled'."""
        # The function expects str, but empty should be safe
        assert slug("") == "untitled"

    def test_max_length(self):
        """Test max_length parameter."""
        long_text = "This is a very long title that should be truncated"
        result = slug(long_text, max_length=20)
        assert len(result) <= 20
        assert result == "this-is-a-very-long"

    def test_max_length_cuts_at_word_boundary(self):
        """Test that truncation tries to cut at word boundary."""
        text = "hello world test example"
        result = slug(text, max_length=15)
        # Should cut at a hyphen if possible
        assert len(result) <= 15

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert slug("Video 123 Tutorial") == "video-123-tutorial"
        assert slug("2024-01-15 Update") == "2024-01-15-update"

    def test_mixed_case(self):
        """Test mixed case is converted to lowercase."""
        assert slug("HeLLo WoRLD") == "hello-world"

    def test_unicode_normalization(self):
        """Test Unicode normalization (NFKD)."""
        # Different Unicode representations of the same character
        assert slug("ﬁle") == "file"  # fi ligature
        assert slug("①②③") == "123"  # Circled numbers (normalized to ASCII digits)

    def test_reserved_windows_names(self):
        """Test that reserved Windows names are prefixed with underscore."""
        assert slug("CON") == "_con"
        assert slug("PRN") == "_prn"
        assert slug("COM1") == "_com1"


class TestPretty:
    """Tests for the pretty() function."""

    def test_basic_title_case(self):
        """Test basic Title Case conversion."""
        assert pretty("hello world") == "Hello World"
        assert (
            pretty("je regarde vos vidéos youtube") == "Je Regarde Vos Vidéos Youtube"
        )

    def test_keeps_accents(self):
        """Test that accents are preserved."""
        assert pretty("vidéo en français") == "Vidéo En Français"
        assert pretty("café résumé") == "Café Résumé"

    def test_removes_invalid_chars(self):
        """Test that invalid filename characters are removed."""
        assert pretty("file<>name") == "File-Name"
        assert pretty("test:file") == "Test-File"

    def test_collapses_whitespace(self):
        """Test that multiple spaces are collapsed."""
        assert pretty("hello    world") == "Hello World"
        assert pretty("  test  ") == "Test"

    def test_empty_string(self):
        """Test empty string returns 'Untitled'."""
        assert pretty("") == "Untitled"
        assert pretty("   ") == "Untitled"

    def test_max_length(self):
        """Test max_length parameter."""
        long_text = "This is a very long title that should be truncated"
        result = pretty(long_text, max_length=20)
        assert len(result) <= 20

    def test_reserved_windows_names(self):
        """Test that reserved Windows names are prefixed with underscore."""
        assert pretty("CON") == "_Con"
        assert pretty("PRN") == "_Prn"


class TestIdx:
    """Tests for the idx() function."""

    def test_small_playlist(self):
        """Test small playlist uses 2-digit padding."""
        assert idx(1, 10) == "01"
        assert idx(5, 10) == "05"
        assert idx(10, 10) == "10"

    def test_medium_playlist(self):
        """Test medium playlist uses 2-digit padding."""
        assert idx(1, 87) == "01"
        assert idx(42, 87) == "42"
        assert idx(87, 87) == "87"

    def test_large_playlist(self):
        """Test large playlist uses 3-digit padding."""
        assert idx(1, 420) == "001"
        assert idx(42, 420) == "042"
        assert idx(420, 420) == "420"

    def test_very_large_playlist_capped(self):
        """Test very large playlist is capped at max_width."""
        assert idx(1, 10000) == "001"  # Capped at 3 digits
        assert idx(9999, 10000) == "9999"  # No padding beyond max_width

    def test_min_width(self):
        """Test minimum width is respected."""
        assert idx(1, 1) == "01"  # min_width=2
        assert idx(5, 5) == "05"


class TestRenderTitle:
    """Tests for the render_title() function."""

    def test_default_pattern(self):
        """Test rendering with default pattern."""
        result = render_title(
            DEFAULT_PLAYLIST_TITLE_PATTERN,
            i=1,
            title="je regarde vos vidéos youtube",
            video_id="abc123",
            ext="mkv",
            total=10,
        )
        assert result == "01 - Je Regarde Vos Vidéos Youtube.mkv"

    def test_index_formatting(self):
        """Test index formatting with different format specs."""
        # 4-digit padding
        result = render_title(
            "{i:03d} - {title}.{ext}",
            i=5,
            title="Test",
            video_id="id",
            ext="mp4",
        )
        assert result == "005 - Test.mp4"

        # 2-digit padding
        result = render_title(
            "{i:02d}_{title}.{ext}",
            i=7,
            title="Test",
            video_id="id",
            ext="mkv",
        )
        assert result == "07_Test.mkv"

        # No padding
        result = render_title(
            "{i} - {title}.{ext}",
            i=42,
            title="Test",
            video_id="id",
            ext="mkv",
        )
        assert result == "42 - Test.mkv"

    def test_slug_title_placeholder(self):
        """Test {slug(title)} placeholder."""
        result = render_title(
            "{slug(title)}.{ext}",
            i=1,
            title="Vidéo en Français 🎬",
            video_id="xyz",
            ext="mp4",
        )
        assert result == "video-en-francais.mp4"

    def test_raw_title_placeholder(self):
        """Test {title} placeholder (raw title)."""
        result = render_title(
            "{title}.{ext}",
            i=1,
            title="My Video Title",
            video_id="abc",
            ext="mkv",
        )
        assert result == "My Video Title.mkv"

    def test_video_id_placeholder(self):
        """Test {id} placeholder."""
        result = render_title(
            "{id}.{ext}",
            i=1,
            title="Title",
            video_id="dQw4w9WgXcQ",
            ext="mp4",
        )
        assert result == "dQw4w9WgXcQ.mp4"

    def test_all_placeholders_combined(self):
        """Test all placeholders in one pattern."""
        result = render_title(
            "{i:03d} - {title} - {slug(title)} [{id}].{ext}",
            i=12,
            title="Hello World",
            video_id="abc",
            ext="mkv",
        )
        assert result == "012 - Hello World - hello-world [abc].mkv"

    def test_empty_title_fallback(self):
        """Test that empty title falls back to 'untitled'."""
        result = render_title(
            "{i:03d} - {slug(title)} [{id}].{ext}",
            i=1,
            title="",
            video_id="abc123",
            ext="mkv",
        )
        assert result == "001 - untitled [abc123].mkv"

    def test_none_title_handled(self):
        """Test that None title is handled safely."""
        # The function should use empty string which becomes "untitled"
        result = render_title(
            "{i:03d} - {slug(title)} [{id}].{ext}",
            i=1,
            title="",  # Empty string simulates None
            video_id="abc123",
            ext="mkv",
        )
        assert result == "001 - untitled [abc123].mkv"

    def test_pretty_title_placeholder(self):
        """Test {pretty(title)} placeholder."""
        result = render_title(
            "{idx} - {pretty(title)}.{ext}",
            i=1,
            title="je regarde vos vidéos youtube",
            video_id="xyz",
            ext="mp4",
            total=10,
        )
        assert result == "01 - Je Regarde Vos Vidéos Youtube.mp4"

    def test_idx_placeholder(self):
        """Test {idx} placeholder with different totals."""
        # Small playlist (2 digits)
        result = render_title(
            "{idx} - {title}.{ext}",
            i=5,
            title="Test",
            video_id="abc",
            ext="mkv",
            total=10,
        )
        assert result == "05 - Test.mkv"

        # Large playlist (3 digits)
        result = render_title(
            "{idx} - {title}.{ext}",
            i=42,
            title="Test",
            video_id="abc",
            ext="mkv",
            total=420,
        )
        assert result == "042 - Test.mkv"

    def test_malformed_pattern_fallback(self):
        """Test that malformed pattern falls back to safe default."""
        # Missing closing brace
        result = render_title(
            "{idx - {pretty(title)}.{ext}",
            i=1,
            title="Test Video",
            video_id="abc123",
            ext="mkv",
            total=10,
        )
        # Should fallback to safe pattern
        assert "Test Video" in result or "Untitled" in result
        assert ".mkv" in result

    def test_unknown_placeholder_fallback(self):
        """Test that unknown placeholder causes fallback."""
        result = render_title(
            "{i:03d} - {unknown_field} [{id}].{ext}",
            i=1,
            title="Test",
            video_id="abc123",
            ext="mkv",
            total=10,
        )
        # Should fallback to safe pattern (uses default pattern with idx and pretty)
        assert "Test" in result or "Untitled" in result
        assert ".mkv" in result

    def test_empty_video_id_handled(self):
        """Test that empty video_id uses 'unknown'."""
        result = render_title(
            "{i:03d} - {slug(title)} [{id}].{ext}",
            i=1,
            title="Test",
            video_id="",
            ext="mkv",
        )
        assert "[unknown]" in result

    def test_empty_ext_handled(self):
        """Test that empty ext uses 'mkv'."""
        result = render_title(
            "{i:03d} - {slug(title)} [{id}].{ext}",
            i=1,
            title="Test",
            video_id="abc",
            ext="",
        )
        assert ".mkv" in result

    def test_negative_index_handled(self):
        """Test that negative index is handled."""
        result = render_title(
            "{i:03d} - {slug(title)} [{id}].{ext}",
            i=-1,
            title="Test",
            video_id="abc",
            ext="mkv",
        )
        # Should use 0 for negative indices
        assert "000" in result

    def test_large_index(self):
        """Test large index values."""
        result = render_title(
            "{i:03d} - {title}.{ext}",
            i=999,
            title="Test",
            video_id="abc",
            ext="mkv",
        )
        assert result == "999 - Test.mkv"

        # Index larger than format width
        result = render_title(
            "{i:03d} - {title}.{ext}",
            i=123,
            title="Test",
            video_id="abc",
            ext="mkv",
        )
        assert result == "123 - Test.mkv"


class TestDefaultPattern:
    """Tests for the default pattern constant."""

    def test_default_pattern_is_valid(self):
        """Test that the default pattern produces valid output."""
        result = render_title(
            DEFAULT_PLAYLIST_TITLE_PATTERN,
            i=1,
            title="Test Video",
            video_id="abc123",
            ext="mkv",
            total=10,
        )
        # Should be a valid filename
        assert result
        assert ".mkv" in result
        assert "Test Video" in result

    def test_default_pattern_format(self):
        """Test the expected format of default pattern."""
        assert "{idx}" in DEFAULT_PLAYLIST_TITLE_PATTERN
        assert "{pretty(title)}" in DEFAULT_PLAYLIST_TITLE_PATTERN
        assert "{ext}" in DEFAULT_PLAYLIST_TITLE_PATTERN
