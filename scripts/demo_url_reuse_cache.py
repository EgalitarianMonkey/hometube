#!/usr/bin/env python3
"""
Manual test script for url_info.json reuse logic.

This script demonstrates the new intelligent caching behavior:
1. Creates a mock url_info.json with limited formats (h264 only)
2. Verifies it's NOT reused (should_reuse returns False)
3. Creates a mock url_info.json with premium formats (AV1)
4. Verifies it IS reused (should_reuse returns True)
"""

import tempfile
from pathlib import Path

from app.url_utils import should_reuse_url_info, save_url_info


def test_scenario(description: str, mock_data: dict, expected_reuse: bool):
    """Test a scenario"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "url_info.json"

        # Save mock data
        save_url_info(json_path, mock_data)
        print(f"✅ Created {json_path}")
        print(f"   Type: {mock_data.get('_type', 'unknown')}")
        print(f"   Title: {mock_data.get('title', 'N/A')}")

        if "formats" in mock_data:
            print(f"   Formats count: {len(mock_data['formats'])}")
            for fmt in mock_data["formats"][:3]:  # Show first 3
                vcodec = fmt.get("vcodec", "none")
                format_id = fmt.get("format_id", "?")
                print(f"     - {format_id}: {vcodec}")

        # Test reuse logic
        should_reuse, data = should_reuse_url_info(json_path)

        print("\n🔍 Result:")
        print(f"   Should reuse: {should_reuse}")
        print(f"   Data loaded: {data is not None}")

        # Verify expectation
        if should_reuse == expected_reuse:
            print("✅ PASS - Behavior matches expectation")
        else:
            print(f"❌ FAIL - Expected {expected_reuse}, got {should_reuse}")


def main():
    print("\n" + "=" * 60)
    print("🧪 Testing url_info.json Intelligent Reuse Logic")
    print("=" * 60)

    # Scenario 1: Video with only h264 (should NOT reuse)
    test_scenario(
        "Video with h264 only (limited formats)",
        {
            "_type": "video",
            "title": "Limited Video",
            "duration": 120,
            "formats": [
                {"format_id": "22", "vcodec": "avc1.64001F", "height": 720},
                {"format_id": "140", "acodec": "mp4a.40.2", "vcodec": "none"},
            ],
        },
        expected_reuse=False,
    )

    # Scenario 2: Video with AV1 (should reuse)
    test_scenario(
        "Video with AV1 (premium formats)",
        {
            "_type": "video",
            "title": "Premium AV1 Video",
            "duration": 180,
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.05M.08", "height": 1080},
                {"format_id": "251", "acodec": "opus", "vcodec": "none"},
            ],
        },
        expected_reuse=True,
    )

    # Scenario 3: Video with VP9 (should reuse)
    test_scenario(
        "Video with VP9 (premium formats)",
        {
            "_type": "video",
            "title": "Premium VP9 Video",
            "duration": 200,
            "formats": [
                {"format_id": "248", "vcodec": "vp9", "height": 1080},
                {"format_id": "251", "acodec": "opus", "vcodec": "none"},
            ],
        },
        expected_reuse=True,
    )

    # Scenario 4: Playlist (always reuse)
    test_scenario(
        "Playlist (always reused)",
        {
            "_type": "playlist",
            "title": "Test Playlist",
            "entries": [
                {"id": "video1", "title": "Video 1"},
                {"id": "video2", "title": "Video 2"},
            ],
        },
        expected_reuse=True,
    )

    # Scenario 5: Mixed formats with premium (should reuse)
    test_scenario(
        "Video with mixed formats including AV1",
        {
            "_type": "video",
            "title": "Mixed Quality Video",
            "duration": 240,
            "formats": [
                {"format_id": "399", "vcodec": "av01.0.05M.08", "height": 1080},
                {"format_id": "22", "vcodec": "avc1.64001F", "height": 720},
                {"format_id": "140", "acodec": "mp4a.40.2", "vcodec": "none"},
            ],
        },
        expected_reuse=True,
    )

    print("\n" + "=" * 60)
    print("✅ All scenarios tested!")
    print("=" * 60)


if __name__ == "__main__":
    main()
