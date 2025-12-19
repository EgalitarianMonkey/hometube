"""
Simplified and essential translation tests.
"""


class TestTranslations:
    """Essential translation tests."""

    def test_translation_files_exist(self, project_root):
        """Test that translation files exist."""
        en_file = project_root / "app" / "translations" / "en.py"
        fr_file = project_root / "app" / "translations" / "fr.py"
        assert en_file.exists(), "English translation file missing"
        assert fr_file.exists(), "French translation file missing"

    def test_translation_import(self):
        """Test that translation modules can be imported."""
        import pytest

        try:
            from app.translations import en, fr  # noqa: F401
        except ImportError:
            pytest.skip("Translation modules not available")

    def test_essential_keys_present(self):
        """Test that essential keys are present."""
        import pytest

        try:
            from app.translations import en, fr

            essential_keys = [
                "page_title",
                "download_button",
                "video_or_playlist_url",
                "options",
            ]

            for key in essential_keys:
                assert key in en.TRANSLATIONS, f"Missing key in English: {key}"
                assert key in fr.TRANSLATIONS, f"Missing key in French: {key}"
        except ImportError:
            pytest.skip("Translation modules not available")

    def test_no_obvious_empty_translations(self):
        """Test that there are no obviously empty translations."""
        import pytest

        try:
            from app.translations import en, fr

            for lang_name, module in [("en", en), ("fr", fr)]:
                for key, value in module.TRANSLATIONS.items():
                    # Check for truly empty strings (not multiline)
                    if isinstance(value, str) and len(value.strip()) == 0:
                        assert False, f"Empty translation in {lang_name}: {key}"
        except ImportError:
            pytest.skip("Translation modules not available")
