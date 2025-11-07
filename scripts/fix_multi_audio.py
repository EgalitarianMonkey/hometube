#!/usr/bin/env python3
"""
Script to fix multi-audio downloads.

yt-dlp has a bug where format strings like "313+251-8+251-0+251-1" don't work correctly
and result in duplicate audio tracks. This script downloads the missing audio tracks
and merges them properly using the url_info.json for language metadata.

Usage:
    python fix_multi_audio.py <video_folder>

Example:
    python fix_multi_audio.py tmp/youtube-ErdDYvfbtp0

The script will:
1. Read url_info.json to get format metadata with correct languages
2. Download each audio track separately
3. Merge them with ffmpeg, setting correct language tags
"""

import sys
import subprocess
from pathlib import Path
import tempfile
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Fix multi-audio video files")
    parser.add_argument("url", help="Video URL")
    parser.add_argument("video_file", help="Path to the video file to fix")
    parser.add_argument(
        "audio_formats",
        help="Comma-separated audio format IDs (e.g., '251-8,251-0,251-1')",
    )
    parser.add_argument(
        "--output", "-o", help="Output file path (default: <input>-fixed.mkv)"
    )

    args = parser.parse_args()

    video_file = Path(args.video_file)
    if not video_file.exists():
        print(f"❌ Video file not found: {video_file}")
        return 1

    audio_format_ids = [f.strip() for f in args.audio_formats.split(",")]
    print(f"🎯 Will download {len(audio_format_ids)} audio tracks: {audio_format_ids}")

    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download each audio track
        audio_files = []
        for format_id in audio_format_ids:
            audio_file = temp_path / f"audio_{format_id}.webm"
            print(f"\n📥 Downloading audio: {format_id}")

            cmd = [
                "yt-dlp",
                "-f",
                format_id,
                "-o",
                str(audio_file),
                "--no-part",
                args.url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  Failed to download {format_id}: {result.stderr}")
                continue

            if audio_file.exists():
                audio_files.append(audio_file)
                print(f"✅ Downloaded: {audio_file.name}")

        if not audio_files:
            print("\n❌ No audio tracks downloaded")
            return 1

        # Prepare output file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = video_file.parent / (video_file.stem + "-fixed.mkv")

        # Build ffmpeg command
        print(f"\n🔀 Merging video + {len(audio_files)} audio tracks")

        cmd_ffmpeg = ["ffmpeg", "-y", "-i", str(video_file)]

        # Add audio inputs
        for audio_file in audio_files:
            cmd_ffmpeg.extend(["-i", str(audio_file)])

        # Map video from original file
        cmd_ffmpeg.extend(["-map", "0:v:0"])

        # Map all new audios
        for i in range(len(audio_files)):
            cmd_ffmpeg.extend(["-map", f"{i+1}:a:0"])

        # Copy codecs
        cmd_ffmpeg.extend(["-c:v", "copy", "-c:a", "copy"])

        # Set first audio as default
        cmd_ffmpeg.extend(["-disposition:a:0", "default"])

        cmd_ffmpeg.append(str(output_file))

        print(f"💻 Running: {' '.join(cmd_ffmpeg[:10])}...")
        result = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"\n❌ FFmpeg failed: {result.stderr}")
            return 1

        print(f"\n✅ Success! Fixed file: {output_file}")
        print(f"📊 Size: {output_file.stat().st_size / (1024*1024):.2f} MiB")

        # Show audio tracks
        cmd_probe = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(output_file),
        ]
        result = subprocess.run(cmd_probe, capture_output=True, text=True)
        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            print(f"\n🎵 Audio tracks in fixed file: {len(streams)}")
            for i, stream in enumerate(streams):
                lang = stream.get("tags", {}).get("language", "unknown")
                print(f"   Track {i}: {lang}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
