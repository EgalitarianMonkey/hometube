"""
Tests for subtitle language configuration based on audio preferences.
"""


class TestSubtitleLanguageConfiguration:
    """Test get_default_subtitle_languages() function."""

    def test_primary_with_include_enabled(self, monkeypatch):
        """Test that primary language is included when INCLUDE=true."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "fr")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        # Clear cache to reload settings
        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == ["fr"], "Primary language should be included"

    def test_primary_with_include_disabled(self, monkeypatch):
        """Test that primary language is excluded when INCLUDE=false."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "fr")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "false")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == [], "Primary language should not be included"

    def test_secondaries_always_included(self, monkeypatch):
        """Test that secondary languages are always included."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "fr")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "en,es,de")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "false")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == [
            "en",
            "es",
            "de",
        ], "All secondary languages should be included"

    def test_primary_and_secondaries_combined(self, monkeypatch):
        """Test combination of primary and secondary languages."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "fr")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "en,es")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == [
            "fr",
            "en",
            "es",
        ], "Should include primary + all secondaries"

    def test_deduplication(self, monkeypatch):
        """Test that duplicate languages are removed."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "en")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "en,fr,en")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        # Should deduplicate 'en' and preserve order
        assert result == ["en", "fr"], "Should remove duplicates while preserving order"

    def test_case_normalization(self, monkeypatch):
        """Test that language codes are normalized to lowercase."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "FR")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "EN,ES")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == ["fr", "en", "es"], "All codes should be lowercase"

    def test_empty_primary(self, monkeypatch):
        """Test behavior with empty primary language."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "en,fr")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == ["en", "fr"], "Should only include secondaries"

    def test_whitespace_handling(self, monkeypatch):
        """Test that whitespace in language codes is stripped."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", " fr ")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", " en , es , de ")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == [
            "fr",
            "en",
            "es",
            "de",
        ], "Whitespace should be stripped"

    def test_no_languages_configured(self, monkeypatch):
        """Test behavior when no languages are configured."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        assert result == [], "Should return empty list"

    def test_order_preservation(self, monkeypatch):
        """Test that language order is preserved (primary first, then secondaries)."""
        monkeypatch.setenv("LANGUAGE_PRIMARY", "ja")
        monkeypatch.setenv("LANGUAGES_SECONDARIES", "en,fr,es,de")
        monkeypatch.setenv("LANGUAGE_PRIMARY_INCLUDE_SUBTITLES", "true")

        from app.config import get_settings, get_default_subtitle_languages

        get_settings.cache_clear()
        result = get_default_subtitle_languages()

        # Order should be: primary first, then secondaries in order
        assert result[0] == "ja", "Primary should be first"
        assert result[1:] == [
            "en",
            "fr",
            "es",
            "de",
        ], "Secondaries should follow in order"
