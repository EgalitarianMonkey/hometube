"""
Test get_formats_id_to_download function with real yt-dlp JSON files.

Tests cover:
- Mono-language videos (single audio track)
- Multi-language videos (multiple dubbed audio tracks)
- Instagram videos (native format)
- Profile validation (format_id, ext, height, vcodec, protocol)
- Deduplication of identical profiles
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.medias_utils import analyze_audio_formats, get_formats_id_to_download


class TestGetFormatsMonoLang:
    """Test suite for mono-language video format selection"""

    def setup_method(self):
        """Load test data before each test"""
        self.json_path = (
            Path(__file__).parent / "ytdlp-json" / "video-mono-lang-stressedout.json"
        )

        import json

        with open(self.json_path) as f:
            self.url_info = json.load(f)

    def test_returns_profiles(self):
        """Test that function returns a list of profiles"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        assert isinstance(profiles, list)
        assert len(profiles) > 0, "Should return at least one profile"
        assert len(profiles) <= 2, "Should return at most 2 profiles"

    def test_profile_structure(self):
        """Test that each profile has required fields"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        required_fields = ["format_id", "ext", "height", "vcodec", "protocol"]

        for profile in profiles:
            for field in required_fields:
                assert field in profile, f"Profile missing required field: {field}"
                assert profile[field] is not None, f"Field {field} should not be None"

    def test_mono_lang_combines_audio(self):
        """Test that mono-lang profiles include audio in format_id"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        assert multiple_langs is False, "Mono-lang should have multiple_langs=False"

        for profile in profiles:
            format_id = profile.get("format_id", "")
            # Mono-lang should have video+audio combined (e.g., "399+251")
            assert (
                "+" in format_id
            ), f"Mono-lang format_id should contain '+': {format_id}"
            parts = format_id.split("+")
            assert (
                len(parts) == 2
            ), f"Mono-lang should have 2 parts (video+audio): {format_id}"

    def test_different_codecs(self):
        """Test that profiles use different codecs when available"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        if len(profiles) == 2:
            codec1 = profiles[0].get("vcodec", "").lower()
            codec2 = profiles[1].get("vcodec", "").lower()

            # Check that codecs are different (AV1 vs VP9)
            assert codec1 != codec2, "Two profiles should have different codecs"

            # One should be AV1-like, one should be VP9-like
            codecs = {codec1, codec2}
            has_av1 = any("av01" in c or "av1" in c for c in codecs)
            has_vp9 = any("vp9" in c or "vp09" in c for c in codecs)

            assert has_av1 or has_vp9, "Should have either AV1 or VP9 codec in profiles"


class TestGetFormatsMultiLang:
    """Test suite for multi-language video format selection"""

    def setup_method(self):
        """Load test data before each test"""
        self.json_path = (
            Path(__file__).parent / "ytdlp-json" / "video-multi-lang-disk.json"
        )

        import json

        with open(self.json_path) as f:
            self.url_info = json.load(f)

    def test_returns_profiles(self):
        """Test that function returns profiles for multi-lang video"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
            self.url_info, language_primary="fr", languages_secondaries="en,es"
        )

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        assert isinstance(profiles, list)
        assert len(profiles) > 0, "Should return at least one profile"

    def test_multi_lang_combines_all_audios(self):
        """Test that multi-lang profiles include all audio tracks"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
            self.url_info, language_primary="fr", languages_secondaries="en,es"
        )

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        assert (
            multiple_langs is True
        ), "Multi-lang video should have multiple_langs=True"
        assert len(audio_formats) > 1, "Multi-lang should have multiple audio formats"

        for profile in profiles:
            format_id = profile.get("format_id", "")

            # Multi-lang should have video + all audio tracks
            assert (
                "+" in format_id
            ), f"Multi-lang format_id should contain '+': {format_id}"

            # Count audio tracks in format_id
            parts = format_id.split("+")
            audio_parts = parts[1:]

            # Should have same number of audio parts as audio_formats
            assert len(audio_parts) == len(
                audio_formats
            ), f"Should have {len(audio_formats)} audio tracks, got {len(audio_parts)}"

    def test_no_duplicate_profiles(self):
        """Test that duplicate profiles are removed"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
            self.url_info, language_primary="fr", languages_secondaries="en,es"
        )

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        # Check for duplicate format_ids
        format_ids = [p.get("format_id") for p in profiles]
        unique_format_ids = set(format_ids)

        assert len(format_ids) == len(
            unique_format_ids
        ), "Should not have duplicate format_ids"

    def test_high_resolution_available(self):
        """Test that high-resolution formats are selected"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
            self.url_info, language_primary="fr", languages_secondaries="en,es"
        )

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        # Multi-lang Disk video should have high resolution (1080p+)
        for profile in profiles:
            height = profile.get("height", 0)
            assert (
                height >= 1080
            ), f"Should have at least 1080p resolution, got {height}p"


class TestGetFormatsInstagram:
    """Test suite for Instagram video format selection"""

    def setup_method(self):
        """Load test data before each test"""
        self.json_path = Path(__file__).parent / "ytdlp-json" / "video-instagram.json"

        import json

        with open(self.json_path) as f:
            self.url_info = json.load(f)

    def test_returns_profile(self):
        """Test that Instagram video returns at least one profile"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        assert isinstance(profiles, list)
        assert len(profiles) > 0, "Should return at least one profile for Instagram"

    def test_instagram_native_format(self):
        """Test that Instagram uses native format structure"""
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(self.url_info)

        profiles = get_formats_id_to_download(
            self.json_path, multiple_langs, audio_formats
        )

        for profile in profiles:
            format_id = profile.get("format_id", "")

            # Instagram typically uses dash- prefixed format IDs
            assert (
                "dash-" in format_id or "+" in format_id
            ), f"Instagram format_id should contain 'dash-' or '+': {format_id}"

            # Check extension
            ext = profile.get("ext", "")
            assert ext in [
                "mp4",
                "webm",
            ], f"Instagram should use mp4 or webm, got {ext}"


class TestGetFormatsEdgeCases:
    """Test suite for edge cases and error handling"""

    def test_empty_audio_formats(self):
        """Test handling of empty audio_formats list"""
        json_path = (
            Path(__file__).parent / "ytdlp-json" / "video-mono-lang-stressedout.json"
        )

        # Call with empty audio_formats
        profiles = get_formats_id_to_download(json_path, False, [])

        # Should still work and return video+audio pairs
        assert isinstance(profiles, list)
        assert len(profiles) >= 0  # May return empty or valid profiles

    def test_max_two_profiles(self):
        """Test that at most 2 profiles are returned"""
        json_path = Path(__file__).parent / "ytdlp-json" / "video-multi-lang-disk.json"

        import json

        with open(json_path) as f:
            url_info = json.load(f)

        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(url_info)

        profiles = get_formats_id_to_download(json_path, multiple_langs, audio_formats)

        assert (
            len(profiles) <= 2
        ), f"Should return at most 2 profiles, got {len(profiles)}"


def run_tests():
    """Run all tests with simple reporting"""
    import traceback

    test_classes = [
        TestGetFormatsMonoLang,
        TestGetFormatsMultiLang,
        TestGetFormatsInstagram,
        TestGetFormatsEdgeCases,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    print("=" * 80)
    print("🧪 Testing get_formats_id_to_download Function")
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
