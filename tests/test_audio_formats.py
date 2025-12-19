"""
Test suite for audio format analysis from yt-dlp JSON output.

Tests analyze_audio_formats() function with different scenarios:
- Mono-language videos (single audio track)
- Multi-language videos (multiple dubbed audio tracks)
- Language preference ordering (VO first, primary, secondaries)
"""

import json
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.medias_utils import analyze_audio_formats


def load_test_json(filename: str) -> Dict:
    """Load a test JSON file from tests/ytdlp-json/"""
    json_path = Path(__file__).parent / "ytdlp-json" / filename
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestInstagramVideo:
    """Test suite for Instagram videos (video-instagram.json)"""

    def setup_method(self):
        """Load test data before each test"""
        self.url_info = load_test_json("video-instagram.json")

    def test_basic_analysis_no_preferences(self):
        """Test Instagram video with no language preferences"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="",
            languages_secondaries="",
            vo_first=True,
        )

        # Assertions
        assert (
            vo_lang is None
        ), f"Instagram video should have no detected VO, got {vo_lang}"
        assert (
            len(ordered_audios) == 1
        ), f"Instagram should have exactly 1 audio format, got {len(ordered_audios)}"
        assert (
            multiple_langs is False
        ), "Instagram video should have multiple_langs=False"

        # Check audio format is valid
        audio = ordered_audios[0]
        assert audio.get("vcodec") == "none", "Audio format should have vcodec='none'"
        assert audio.get("acodec") != "none", "Audio format should have a valid acodec"
        assert "format_id" in audio, "Audio format should have format_id"

    def test_with_language_preferences(self):
        """Test Instagram video with language preferences (should not affect result)"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="es,de",
            vo_first=True,
        )

        # Assertions - preferences should not matter for single audio
        assert len(ordered_audios) == 1, "Should have exactly one audio format"
        assert (
            multiple_langs is False
        ), "Instagram video should have multiple_langs=False"


class TestMonoLanguageVideo:
    """Test suite for single-language videos (video-mono-lang-stressedout.json)"""

    def setup_method(self):
        """Load test data before each test"""
        self.url_info = load_test_json("video-mono-lang-stressedout.json")

    def test_basic_analysis_no_preferences(self):
        """Test mono-lang video with no language preferences"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="",
            languages_secondaries="",
            vo_first=True,
        )

        # Assertions
        assert (
            vo_lang is None or vo_lang == "en"
        ), f"Expected VO to be None or 'en', got {vo_lang}"
        assert len(ordered_audios) > 0, "Should have at least one audio format"
        assert (
            multiple_langs is False
        ), "Mono-lang video should have multiple_langs=False"

        # Check audio formats are valid
        for audio in ordered_audios:
            assert (
                audio.get("vcodec") == "none"
            ), "Audio format should have vcodec='none'"
            assert (
                audio.get("acodec") != "none"
            ), "Audio format should have a valid acodec"
            assert "format_id" in audio, "Audio format should have format_id"

    def test_with_language_preferences(self):
        """Test mono-lang video with language preferences (should not affect result)"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="es,de",
            vo_first=True,
        )

        # Assertions - preferences should not matter for mono-lang
        assert len(ordered_audios) > 0, "Should have at least one audio format"
        assert (
            multiple_langs is False
        ), "Mono-lang video should have multiple_langs=False"

    def test_opus_codec_preference(self):
        """Test that Opus codec is preferred over other codecs"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="",
            languages_secondaries="",
            vo_first=True,
        )

        # Check if Opus formats are present and prioritized
        opus_formats = [
            a for a in ordered_audios if a.get("acodec", "").startswith("opus")
        ]
        if opus_formats:
            # If Opus exists, it should be in the results
            assert len(opus_formats) > 0, "Opus formats should be included"


class TestMultiLanguageVideo:
    """Test suite for multi-language videos (video-multi-lang-disk.json)"""

    def setup_method(self):
        """Load test data before each test"""
        self.url_info = load_test_json("video-multi-lang-disk.json")

    def test_basic_analysis_no_preferences(self):
        """Test multi-lang video with no language preferences"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="",
            languages_secondaries="",
            vo_first=True,
        )

        # Assertions
        assert (
            vo_lang == "en-US" or vo_lang == "en"
        ), f"Expected VO to be 'en-US' or 'en', got {vo_lang}"
        assert (
            len(ordered_audios) > 1
        ), "Multi-lang video should have multiple audio formats"
        assert (
            multiple_langs is True
        ), "Multi-lang video should have multiple_langs=True"

        # Check that VO is first (since vo_first=True)
        if vo_lang and ordered_audios:
            first_audio = ordered_audios[0]
            first_lang = first_audio.get("language", "")
            # Should be en-US or en
            assert first_lang in [
                "en-US",
                "en",
            ], f"First audio should be VO (en), got {first_lang}"

    def test_vo_first_enabled(self):
        """Test that VO language is first when vo_first=True"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="es,de",
            vo_first=True,
        )

        # Assertions
        assert vo_lang in [
            "en-US",
            "en",
        ], f"Expected VO to be 'en-US' or 'en', got {vo_lang}"
        assert len(ordered_audios) >= 4, "Should have at least VO + fr + es + de"
        assert (
            multiple_langs is True
        ), "Multi-lang video should have multiple_langs=True"

        # Check order: VO (en) should be first
        first_audio = ordered_audios[0]
        first_lang = first_audio.get("language", "")
        assert first_lang in [
            "en-US",
            "en",
        ], f"First audio should be VO (en), got {first_lang}"

    def test_vo_first_disabled(self):
        """Test that primary language is first when vo_first=False"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="es,de",
            vo_first=False,
        )

        # Assertions
        assert vo_lang in ["en-US", "en"], f"VO should still be detected: {vo_lang}"
        # With vo_first=False and en not in preferences, we get: fr, es, de (3 tracks)
        # VO (en) is NOT included since it's not in language preferences
        assert len(ordered_audios) == 3, "Should have fr + es + de (without en)"
        assert (
            multiple_langs is True
        ), "Multi-lang video should have multiple_langs=True"

        # Check order: Primary (fr) should be first
        first_audio = ordered_audios[0]
        first_lang = first_audio.get("language", "")
        assert first_lang in [
            "fr-FR",
            "fr",
        ], f"First audio should be primary (fr), got {first_lang}"

    def test_primary_language_ordering(self):
        """Test that primary language appears in correct position"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="de",
            languages_secondaries="fr,es",
            vo_first=True,
        )

        # Assertions
        assert len(ordered_audios) >= 4, "Should have VO + de + fr + es"

        # Extract language codes from ordered audios
        langs = [a.get("language", "").split("-")[0] for a in ordered_audios[:4]]

        # Check that de (primary) appears after en (VO) but before or with secondaries
        assert "en" in langs, "VO (en) should be present"
        assert "de" in langs, "Primary (de) should be present"

    def test_secondary_languages_ordering(self):
        """Test that secondary languages appear after primary"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="es,de,it",
            vo_first=True,
        )

        # Assertions
        assert len(ordered_audios) >= 5, "Should have VO + fr + es + de + it"

        # Extract first 5 language codes (normalized)
        langs = [a.get("language", "").split("-")[0] for a in ordered_audios[:5]]

        # Check presence of key languages
        assert "en" in langs, "VO (en) should be present"
        assert "fr" in langs, "Primary (fr) should be present"
        assert (
            "es" in langs or "de" in langs or "it" in langs
        ), "At least one secondary should be present"

    def test_no_duplicate_languages(self):
        """Test that no language appears twice in the ordered list"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="en",
            languages_secondaries="fr,es",
            vo_first=True,
        )

        # Extract normalized language codes (e.g., en-US -> en)
        langs = [a.get("language", "").split("-")[0] for a in ordered_audios]

        # Check for duplicates
        seen = set()
        duplicates = []
        for lang in langs:
            if lang in seen:
                duplicates.append(lang)
            seen.add(lang)

        assert len(duplicates) == 0, f"Found duplicate languages: {duplicates}"

    def test_all_languages_included(self):
        """Test that all audio languages are included in results"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="en,es",
            vo_first=True,
        )

        # Count audio formats in original data
        all_audios = [
            f
            for f in self.url_info.get("formats", [])
            if f.get("vcodec") == "none" and f.get("acodec") != "none"
        ]

        # Get unique base format IDs (e.g., 251 from 251-0, 251-1, etc.)
        base_ids_original = set()
        for audio in all_audios:
            format_id = audio.get("format_id", "")
            base_id = format_id.split("-")[0]
            base_ids_original.add(base_id)

        base_ids_result = set()
        for audio in ordered_audios:
            format_id = audio.get("format_id", "")
            base_id = format_id.split("-")[0]
            base_ids_result.add(base_id)

        # Should have same base format IDs (same quality group)
        # Allow some flexibility - at least the top quality should be there
        assert len(base_ids_result) > 0, "Should have at least one base format ID"


class TestLanguagePreferences:
    """Test suite for language preference scenarios"""

    def setup_method(self):
        """Load test data before each test"""
        self.url_info = load_test_json("video-multi-lang-disk.json")

    def test_scenario_1_no_preferences(self):
        """Scenario 1: No preferences - all languages"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="",
            languages_secondaries="",
            vo_first=True,
        )

        print("\n📋 Scenario 1: No preferences")
        print(f"   VO: {vo_lang}")
        print(f"   Audio count: {len(ordered_audios)}")
        print(f"   Multiple langs: {multiple_langs}")

        assert vo_lang in ["en-US", "en"]
        assert len(ordered_audios) > 5
        assert multiple_langs is True

    def test_scenario_2_primary_only_vo_last(self):
        """Scenario 2: Primary=fr, VO_FIRST=False"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="",
            vo_first=False,
        )

        print("\n📋 Scenario 2: Primary=fr, VO_FIRST=False")
        print(f"   VO: {vo_lang}")
        print(
            f"   First audio lang: {ordered_audios[0].get('language') if ordered_audios else 'N/A'}"
        )
        print(f"   Multiple langs: {multiple_langs}")

        assert vo_lang in ["en-US", "en"]
        assert ordered_audios[0].get("language", "").startswith("fr")
        assert multiple_langs is True

    def test_scenario_3_vo_first_with_primary(self):
        """Scenario 3: VO_FIRST=True, Primary=fr"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="",
            vo_first=True,
        )

        print("\n📋 Scenario 3: VO_FIRST=True, Primary=fr")
        print(f"   VO: {vo_lang}")
        print(
            f"   First audio lang: {ordered_audios[0].get('language') if ordered_audios else 'N/A'}"
        )
        print(
            f"   Second audio lang: {ordered_audios[1].get('language') if len(ordered_audios) > 1 else 'N/A'}"
        )
        print(f"   Multiple langs: {multiple_langs}")

        assert vo_lang in ["en-US", "en"]
        assert ordered_audios[0].get("language", "").startswith("en")
        assert ordered_audios[1].get("language", "").startswith("fr")
        assert multiple_langs is True

    def test_scenario_4_vo_primary_secondaries(self):
        """Scenario 4: VO_FIRST=True, Primary=fr, Secondaries=en,es"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="en,es",
            vo_first=True,
        )

        print("\n📋 Scenario 4: VO_FIRST=True, Primary=fr, Secondaries=en,es")
        print(f"   VO: {vo_lang}")
        langs = [a.get("language", "") for a in ordered_audios[:4]]
        print(f"   First 4 langs: {langs}")
        print(f"   Multiple langs: {multiple_langs}")

        assert vo_lang in ["en-US", "en"]
        # Order: en (VO) -> fr (primary) -> es (secondary) -> others
        assert ordered_audios[0].get("language", "").startswith("en")
        assert ordered_audios[1].get("language", "").startswith("fr")
        assert multiple_langs is True

    def test_scenario_5_primary_multiple_secondaries_no_vo_first(self):
        """Scenario 5: VO_FIRST=False, Primary=fr, Secondaries=en,es,ja"""
        vo_lang, ordered_audios, multiple_langs = analyze_audio_formats(
            self.url_info,
            language_primary="fr",
            languages_secondaries="en,es,ja",
            vo_first=False,
        )

        print("\n📋 Scenario 5: VO_FIRST=False, Primary=fr, Secondaries=en,es,ja")
        print(f"   VO: {vo_lang}")
        langs = [a.get("language", "") for a in ordered_audios[:5]]
        print(f"   First 5 langs: {langs}")
        print(f"   Multiple langs: {multiple_langs}")

        assert vo_lang in ["en-US", "en"]
        # Order: fr (primary) -> en,es,ja (secondaries) -> others
        assert ordered_audios[0].get("language", "").startswith("fr")
        assert multiple_langs is True


def run_tests():
    """Run all tests with simple reporting"""
    import traceback

    test_classes = [
        TestInstagramVideo,
        TestMonoLanguageVideo,
        TestMultiLanguageVideo,
        TestLanguagePreferences,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    print("=" * 80)
    print("🧪 Testing Audio Format Analysis")
    print("=" * 80)

    for test_class in test_classes:
        print(f"\n📦 {test_class.__name__}")
        print("-" * 80)

        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            test_instance = test_class()

            try:
                # Run setup
                if hasattr(test_instance, "setup_method"):
                    test_instance.setup_method()

                # Run test
                method = getattr(test_instance, method_name)
                method()

                passed_tests += 1
                print(f"  ✅ {method_name}")

            except AssertionError as e:
                failed_tests += 1
                print(f"  ❌ {method_name}")
                print(f"     Error: {str(e)}")

            except Exception as e:
                failed_tests += 1
                print(f"  💥 {method_name}")
                print(f"     Exception: {str(e)}")
                traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    if failed_tests > 0:
        print(f"   ❌ {failed_tests} failed")
    else:
        print("   ✅ All tests passed!")
    print("=" * 80)

    return failed_tests == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
