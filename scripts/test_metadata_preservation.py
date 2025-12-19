#!/usr/bin/env python3
"""
Test script to verify metadata preservation through FFmpeg operations.
This simulates what happens during video processing with subtitles.
"""

import subprocess
import json
import tempfile
from pathlib import Path


def run_ffmpeg(cmd):
    """Run FFmpeg command and return result."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def get_metadata(video_path):
    """Extract metadata from video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format_tags",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return data.get("format", {}).get("tags", {})
    return {}


def create_test_video(output_path):
    """Create a simple test video with FFmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=1280x720:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=1",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        str(output_path),
    ]
    success, error = run_ffmpeg(cmd)
    if not success:
        print(f"❌ Failed to create test video: {error}")
        return False
    print(f"✅ Created test video: {output_path}")
    return True


def add_custom_metadata(input_path, output_path):
    """Add custom metadata like VIDEO_ID, SOURCE, etc."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-c",
        "copy",
        "-map_metadata",
        "0",
        "-metadata",
        "title=Test Video - Test Channel",
        "-metadata",
        "VIDEO_ID=test123",
        "-metadata",
        "SOURCE=youtube",
        "-metadata",
        "PLAYLIST_ID=PL_test",
        "-metadata",
        "PURL=https://www.youtube.com/watch?v=test123",
        "-metadata",
        "artist=Test Channel",
        str(output_path),
    ]
    success, error = run_ffmpeg(cmd)
    if not success:
        print(f"❌ Failed to add metadata: {error}")
        return False
    print(f"✅ Added custom metadata")
    return True


def simulate_subtitle_embed(input_path, output_path):
    """Simulate subtitle embedding with metadata preservation."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v",
        "-map",
        "0:a",
        "-map_metadata",
        "0",  # This is critical!
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        str(output_path),
    ]
    success, error = run_ffmpeg(cmd)
    if not success:
        print(f"❌ Failed to simulate subtitle embed: {error}")
        return False
    print(f"✅ Simulated subtitle embedding with -map_metadata 0")
    return True


def main():
    """Run the metadata preservation test."""
    print("🧪 Testing metadata preservation through FFmpeg operations\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Step 1: Create test video
        video1 = tmpdir / "test_original.mkv"
        if not create_test_video(video1):
            return 1

        # Step 2: Add custom metadata (simulates customize_video_metadata)
        video2 = tmpdir / "test_with_metadata.mkv"
        if not add_custom_metadata(video1, video2):
            return 1

        # Check metadata after adding
        metadata_after_add = get_metadata(video2)
        print("\n📋 Metadata after adding custom fields:")
        for key, value in metadata_after_add.items():
            print(f"   {key}: {value}")

        # Verify critical fields are present
        critical_fields = ["VIDEO_ID", "SOURCE", "PLAYLIST_ID", "PURL"]
        missing_after_add = [f for f in critical_fields if f not in metadata_after_add]

        if missing_after_add:
            print(f"\n❌ Missing metadata after adding: {', '.join(missing_after_add)}")
            return 1
        else:
            print(f"\n✅ All critical metadata fields present after adding")

        # Step 3: Simulate subtitle embedding (simulates embed_subtitles_manually)
        video3 = tmpdir / "test_after_subtitle.mkv"
        if not simulate_subtitle_embed(video2, video3):
            return 1

        # Check metadata after subtitle operation
        metadata_after_sub = get_metadata(video3)
        print("\n📋 Metadata after subtitle embedding simulation:")
        for key, value in metadata_after_sub.items():
            print(f"   {key}: {value}")

        # Verify critical fields are STILL present
        missing_after_sub = [f for f in critical_fields if f not in metadata_after_sub]

        if missing_after_sub:
            print(
                f"\n❌ LOST metadata after subtitle embedding: {', '.join(missing_after_sub)}"
            )
            print("⚠️  This means -map_metadata 0 is NOT working correctly!")
            return 1
        else:
            print(
                f"\n✅ All critical metadata fields PRESERVED after subtitle embedding"
            )
            print("✅ Metadata preservation is working correctly!")

        # Final comparison
        print("\n📊 Comparison:")
        print(f"   Metadata fields after adding: {len(metadata_after_add)}")
        print(f"   Metadata fields after subtitle: {len(metadata_after_sub)}")

        if len(metadata_after_sub) >= len(metadata_after_add):
            print("✅ No metadata loss detected!")
            return 0
        else:
            lost_count = len(metadata_after_add) - len(metadata_after_sub)
            print(f"⚠️  Lost {lost_count} metadata fields")
            return 1


if __name__ == "__main__":
    exit(main())
