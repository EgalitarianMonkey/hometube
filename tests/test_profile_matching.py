"""
Tests for profile matching functionality in HomeTube.

This module tests the core profile matching logic with different scenarios:
- Auto mode (all profiles)
- Specific profile modes
- Non-existent profile handling
- Edge cases and error conditions
"""

from app.profile_utils import match_profiles_to_formats
from app.quality_profiles import QUALITY_PROFILES

# Sample yt-dlp format data for comprehensive testing
# Includes common codec combinations found in real YouTube videos
SAMPLE_FORMATS = [
    # Audio formats - opus (best quality)
    {
        "format_id": "251",
        "ext": "webm",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "opus",
        "abr": 160,
        "vbr": None,
        "tbr": 160,
        "protocol": "https",
        "format_note": "audio only",
    },
    {
        "format_id": "250",
        "ext": "webm",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "opus",
        "abr": 64,
        "vbr": None,
        "tbr": 64,
        "protocol": "https",
        "format_note": "audio only",
    },
    # Audio formats - aac (universal compatibility)
    {
        "format_id": "140",
        "ext": "m4a",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "aac",
        "abr": 128,
        "vbr": None,
        "tbr": 128,
        "protocol": "https",
        "format_note": "audio only",
    },
    {
        "format_id": "139",
        "ext": "m4a",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "aac",
        "abr": 48,
        "vbr": None,
        "tbr": 48,
        "protocol": "https",
        "format_note": "audio only",
    },
    # Video formats - AV1 4K (next-gen)
    {
        "format_id": "401",
        "ext": "mp4",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 30,
        "vcodec": "av01",
        "acodec": "none",
        "abr": None,
        "vbr": 8947,
        "tbr": 8947,
        "protocol": "https",
        "format_note": "2160p",
    },
    {
        "format_id": "400",
        "ext": "mp4",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 25,
        "vcodec": "av01",
        "acodec": "none",
        "abr": None,
        "vbr": 6500,
        "tbr": 6500,
        "protocol": "https",
        "format_note": "2160p",
    },
    # Video formats - VP9 4K (excellent quality)
    {
        "format_id": "315",
        "ext": "webm",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 30,
        "vcodec": "vp9",
        "acodec": "none",
        "abr": None,
        "vbr": 15000,
        "tbr": 15000,
        "protocol": "https",
        "format_note": "2160p",
    },
    {
        "format_id": "313",
        "ext": "webm",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 25,
        "vcodec": "vp9",
        "acodec": "none",
        "abr": None,
        "vbr": 12000,
        "tbr": 12000,
        "protocol": "https",
        "format_note": "2160p",
    },
    # Video formats - H.264 4K/1080p (maximum compatibility)
    {
        "format_id": "138",
        "ext": "mp4",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "none",
        "abr": None,
        "vbr": 15000,
        "tbr": 15000,
        "protocol": "https",
        "format_note": "2160p",
    },
    {
        "format_id": "137",
        "ext": "mp4",
        "resolution": "1080x1920",
        "height": 1080,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "none",
        "abr": None,
        "vbr": 4000,
        "tbr": 4000,
        "protocol": "https",
        "format_note": "1080p",
    },
    {
        "format_id": "136",
        "ext": "mp4",
        "resolution": "720x1280",
        "height": 720,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "none",
        "abr": None,
        "vbr": 1200,
        "tbr": 1200,
        "protocol": "https",
        "format_note": "720p",
    },
]


# =============================================================================
# CORE FUNCTIONALITY TESTS
# =============================================================================


def test_auto_mode_all_profiles():
    """Test AUTO mode with all QUALITY_PROFILES."""
    print("🧪 Testing AUTO mode (all profiles)...")

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    # Should return combinations
    assert isinstance(combinations, list)
    assert len(combinations) > 0, "Auto mode should find at least one combination"

    # Should respect profile priority order
    profile_names = [combo["profile_name"] for combo in combinations]
    unique_profiles = []
    for name in profile_names:
        if name not in unique_profiles:
            unique_profiles.append(name)

    # The profiles should appear in priority order (mkv_av1_opus first, etc.)
    expected_priority_order = [
        "mkv_av1_opus",
        "mkv_vp9_opus",
        "mp4_av1_aac",
        "mp4_h264_aac",
    ]
    found_profiles = [p for p in expected_priority_order if p in unique_profiles]

    assert len(found_profiles) > 0, "Should find at least one profile"

    # Each combination should have valid structure
    for combo in combinations:
        assert "profile_name" in combo
        assert "video_format" in combo
        assert "audio_format" in combo
        assert "format_spec" in combo
        assert "+" in combo["format_spec"]

        # Verify format_spec references real format IDs
        video_id, audio_id = combo["format_spec"].split("+")
        format_ids = {f["format_id"] for f in SAMPLE_FORMATS}
        assert video_id in format_ids, f"Video format {video_id} not found"
        assert audio_id in format_ids, f"Audio format {audio_id} not found"

    print(
        f"✅ Found {len(combinations)} combinations across {len(unique_profiles)} profiles"
    )


def test_specific_profile_mkv_av1_opus():
    """Test specific profile mode - mkv_av1_opus only."""
    print("🧪 Testing specific profile: mkv_av1_opus...")

    # Find the mkv_av1_opus profile
    target_profile = None
    for profile in QUALITY_PROFILES:
        if profile["name"] == "mkv_av1_opus":
            target_profile = profile
            break

    assert target_profile is not None, "mkv_av1_opus profile should exist"

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [target_profile], "max")

    # Should find combinations for AV1+Opus
    assert len(combinations) > 0, "Should find mkv_av1_opus combinations"

    # All combinations should be for mkv_av1_opus only
    for combo in combinations:
        assert combo["profile_name"] == "mkv_av1_opus"
        assert combo["container"] == "mkv"
        assert combo["priority"] == 1
        assert combo["video_format"]["vcodec"] == "av01"
        assert combo["audio_format"]["acodec"] == "opus"

    print(f"✅ Found {len(combinations)} combinations for mkv_av1_opus profile")


def test_specific_profile_mp4_h264_aac():
    """Test specific profile mode - mp4_h264_aac only."""
    print("🧪 Testing specific profile: mp4_h264_aac...")

    # Find the mp4_h264_aac profile
    target_profile = None
    for profile in QUALITY_PROFILES:
        if profile["name"] == "mp4_h264_aac":
            target_profile = profile
            break

    assert target_profile is not None, "mp4_h264_aac profile should exist"

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [target_profile], "max")

    # Should find combinations for H.264+AAC
    assert len(combinations) > 0, "Should find mp4_h264_aac combinations"

    # All combinations should be for mp4_h264_aac only
    for combo in combinations:
        assert combo["profile_name"] == "mp4_h264_aac"
        assert combo["container"] == "mp4"
        assert combo["priority"] == 4
        assert combo["video_format"]["vcodec"] == "avc1"
        assert combo["audio_format"]["acodec"] == "aac"

    print(f"✅ Found {len(combinations)} combinations for mp4_h264_aac profile")


def test_specific_profile_mkv_vp9_opus():
    """Test specific profile mode - mkv_vp9_opus only."""
    print("🧪 Testing specific profile: mkv_vp9_opus...")

    # Find the mkv_vp9_opus profile
    target_profile = None
    for profile in QUALITY_PROFILES:
        if profile["name"] == "mkv_vp9_opus":
            target_profile = profile
            break

    assert target_profile is not None, "mkv_vp9_opus profile should exist"

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [target_profile], "max")

    # Should find combinations for VP9+Opus
    assert len(combinations) > 0, "Should find mkv_vp9_opus combinations"

    # All combinations should be for mkv_vp9_opus only
    for combo in combinations:
        assert combo["profile_name"] == "mkv_vp9_opus"
        assert combo["container"] == "mkv"
        assert combo["priority"] == 2
        assert combo["video_format"]["vcodec"] == "vp9"
        assert combo["audio_format"]["acodec"] == "opus"

    print(f"✅ Found {len(combinations)} combinations for mkv_vp9_opus profile")


def test_multiple_specific_profiles():
    """Test with multiple specific profiles."""
    print("🧪 Testing multiple specific profiles...")

    # Select 2 profiles
    selected_profiles = []
    for profile in QUALITY_PROFILES:
        if profile["name"] in ["mkv_av1_opus", "mp4_h264_aac"]:
            selected_profiles.append(profile)

    assert len(selected_profiles) == 2, "Should find both profiles"

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, selected_profiles, "max")

    assert len(combinations) > 0, "Should find combinations for multiple profiles"

    # Should only contain the selected profiles
    profile_names = {combo["profile_name"] for combo in combinations}
    expected_names = {"mkv_av1_opus", "mp4_h264_aac"}
    assert profile_names.issubset(
        expected_names
    ), f"Unexpected profiles: {profile_names - expected_names}"

    print(
        f"✅ Found {len(combinations)} combinations across {len(profile_names)} selected profiles"
    )


def test_nonexistent_profile():
    """Test with a profile that doesn't exist in formats."""
    print("🧪 Testing non-existent profile...")

    # Create fake profile with impossible requirements
    fake_profile = {
        "name": "fake_impossible_profile",
        "label": "🧪 Fake Impossible Profile",
        "video_codec_ext": [
            {"vcodec": ["nonexistent_video_codec"], "ext": ["mp4"]},
        ],
        "audio_codec_ext": [
            {"acodec": ["nonexistent_audio_codec"], "ext": ["mp4"]},
        ],
        "container": "mp4",
        "extra_args": [],
        "priority": 999,
    }

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [fake_profile], "max")

    # Should return empty list since no compatible formats exist
    assert len(combinations) == 0, "Non-existent profile should return no combinations"

    print("✅ Non-existent profile correctly returned no combinations")


def test_empty_formats():
    """Test with empty format list."""
    combinations = match_profiles_to_formats([], QUALITY_PROFILES, "max")
    assert combinations == [], "Empty formats should return empty list"


def test_empty_profiles():
    """Test with empty profile list."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [], "max")
    assert combinations == [], "Empty profiles should return empty list"


def test_invalid_inputs():
    """Test with invalid inputs."""
    # None inputs
    assert match_profiles_to_formats(None, QUALITY_PROFILES, "max") == []
    assert match_profiles_to_formats(SAMPLE_FORMATS, None, "max") == []
    assert match_profiles_to_formats(None, None, "max") == []


# =============================================================================
# QUALITY AND LOGIC TESTS
# =============================================================================


def test_combination_structure():
    """Test that combinations have correct structure and data types."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    assert len(combinations) > 0, "Should find at least one combination"

    required_keys = [
        "profile_name",
        "profile_label",
        "video_format",
        "audio_format",
        "format_spec",
        "container",
        "extra_args",
        "priority",
        "target_resolution",
    ]

    for combo in combinations:
        for key in required_keys:
            assert key in combo, f"Missing required key: {key}"

        # Check data types
        assert isinstance(combo["profile_name"], str)
        assert isinstance(combo["profile_label"], str)
        assert isinstance(combo["video_format"], dict)
        assert isinstance(combo["audio_format"], dict)
        assert isinstance(combo["format_spec"], str)
        assert isinstance(combo["container"], str)
        assert isinstance(combo["extra_args"], list)
        assert isinstance(combo["priority"], int)
        assert isinstance(combo["target_resolution"], int)

        # Verify format_spec structure
        assert "+" in combo["format_spec"], "format_spec should contain +"
        video_id, audio_id = combo["format_spec"].split("+")
        assert video_id == combo["video_format"]["format_id"]
        assert audio_id == combo["audio_format"]["format_id"]


def test_no_duplicate_combinations():
    """Test that there are no duplicate format_spec combinations."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    format_specs = [combo["format_spec"] for combo in combinations]
    unique_specs = set(format_specs)

    assert len(format_specs) == len(
        unique_specs
    ), "Should not have duplicate format_spec"


def test_max_combinations_per_profile():
    """Test that each profile generates maximum 4 combinations (2×2)."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    # Group by profile
    by_profile = {}
    for combo in combinations:
        profile_name = combo["profile_name"]
        if profile_name not in by_profile:
            by_profile[profile_name] = []
        by_profile[profile_name].append(combo)

    # Each profile should have max 4 combinations (2 video × 2 audio)
    for profile_name, profile_combos in by_profile.items():
        assert (
            len(profile_combos) <= 4
        ), f"Profile {profile_name} has too many combinations: {len(profile_combos)}"


def test_priority_consistency():
    """Test that combinations maintain profile priority consistency."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    # Group by profile and check priorities
    profile_priorities = {}
    for combo in combinations:
        profile_name = combo["profile_name"]
        priority = combo["priority"]

        if profile_name in profile_priorities:
            assert (
                profile_priorities[profile_name] == priority
            ), f"Inconsistent priority for {profile_name}"
        else:
            profile_priorities[profile_name] = priority

    # Verify known priorities
    expected_priorities = {
        "mkv_av1_opus": 1,
        "mkv_vp9_opus": 2,
        "mp4_av1_aac": 3,
        "mp4_h264_aac": 4,
    }

    for profile, expected_priority in expected_priorities.items():
        if profile in profile_priorities:
            assert (
                profile_priorities[profile] == expected_priority
            ), f"Wrong priority for {profile}"


def test_codec_constraints():
    """Test that combinations respect profile codec constraints."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    for combo in combinations:
        profile_name = combo["profile_name"]
        video_codec = combo["video_format"]["vcodec"]
        audio_codec = combo["audio_format"]["acodec"]

        # Find the profile definition
        profile = None
        for p in QUALITY_PROFILES:
            if p["name"] == profile_name:
                profile = p
                break

        assert profile is not None, f"Profile {profile_name} not found"

        # Check video codec constraints
        if "video_codec_ext" in profile:
            expected_video_codecs = []
            for spec in profile["video_codec_ext"]:
                expected_video_codecs.extend(spec.get("vcodec", []))

            # Handle codec aliases (h264 -> avc1)
            codec_matches = video_codec in expected_video_codecs or (
                video_codec == "avc1" and "h264" in expected_video_codecs
            )
            assert (
                codec_matches
            ), f"Video codec {video_codec} not allowed for {profile_name}. Expected: {expected_video_codecs}"

        # Check audio codec constraints
        if "audio_codec_ext" in profile:
            expected_audio_codecs = []
            for spec in profile["audio_codec_ext"]:
                expected_audio_codecs.extend(spec.get("acodec", []))

            # Handle codec aliases (aac -> mp4a)
            codec_matches = audio_codec in expected_audio_codecs or (
                audio_codec == "aac" and "mp4a" in expected_audio_codecs
            )
            assert (
                codec_matches
            ), f"Audio codec {audio_codec} not allowed for {profile_name}. Expected: {expected_audio_codecs}"


if __name__ == "__main__":
    print("🧪 Running HomeTube Profile Matching Tests")
    print("=" * 60)

    # Core functionality tests
    test_auto_mode_all_profiles()
    test_specific_profile_mkv_av1_opus()
    test_specific_profile_mp4_h264_aac()
    test_specific_profile_mkv_vp9_opus()
    test_multiple_specific_profiles()
    test_nonexistent_profile()

    # Edge case tests
    test_empty_formats()
    test_empty_profiles()
    test_invalid_inputs()

    # Quality and logic tests
    test_combination_structure()
    test_no_duplicate_combinations()
    test_max_combinations_per_profile()
    test_priority_consistency()
    test_codec_constraints()

    print("\n✅ All tests passed!")
    print("=" * 60)
