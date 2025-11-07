#!/usr/bin/env python3
"""
Test script to verify yt-dlp command generation for multi-audio downloads.
Compares HomeTube's generated command with a working manual command.
"""


def build_test_command():
    """Build the yt-dlp command as HomeTube would"""
    format_spec = "313+251-8+251-0+251-1"

    # Base command (similar to build_base_ytdlp_command)
    base_cmd = [
        "yt-dlp",
        "--newline",
        "-o",
        "Multi-audio.%(ext)s",
        "--merge-output-format",
        "mkv",
        "-f",
        format_spec,
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--ignore-errors",
        "--force-overwrites",
        "--concurrent-fragments",
        "1",
        "--sleep-requests",
        "1",
        "--retries",
        "15",
        "--retry-sleep",
        "3",
    ]

    # Detect multi-audio (lines 60-64 in core.py)
    parts = format_spec.split("+")
    if len(parts) > 2:
        base_cmd.append("--audio-multistreams")
        print(f"✅ Multi-audio detected: {len(parts)} parts ({parts})")
    else:
        print(f"❌ Multi-audio NOT detected: {len(parts)} parts")

    # Add chapters
    base_cmd.append("--embed-chapters")

    # Add subtitles
    base_cmd.extend(
        [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "en,es",
            "--convert-subs",
            "srt",
            "--embed-subs",
        ]
    )

    # Add SponsorBlock
    base_cmd.extend(
        [
            "--sponsorblock-remove",
            "sponsor,interaction,selfpromo",
            "--no-force-keyframes-at-cuts",
            "--sponsorblock-mark",
            "intro,preview,outro",
        ]
    )

    # Add cookies
    base_cmd.extend(["--cookies", "/Users/yo/Dev/hometube/cookies/youtube_cookies.txt"])

    # Add URL
    base_cmd.append("https://www.youtube.com/watch?v=ErdDYvfbtp0")

    return base_cmd


def main():
    print("=" * 80)
    print("HOMETUBE COMMAND GENERATION TEST")
    print("=" * 80)
    print()

    # Generate command
    cmd = build_test_command()

    print()
    print("=" * 80)
    print("GENERATED COMMAND:")
    print("=" * 80)
    print(" ".join(cmd))
    print()

    # Verification
    print("=" * 80)
    print("VERIFICATIONS:")
    print("=" * 80)
    print(f"✓ --audio-multistreams present: {('--audio-multistreams' in cmd)}")
    print(f"✓ Format spec: {cmd[cmd.index('-f') + 1] if '-f' in cmd else 'NOT FOUND'}")
    print(f"✓ Cookies present: {('--cookies' in cmd)}")
    print(f"✓ Chapters embedded: {('--embed-chapters' in cmd)}")
    print(f"✓ Subtitles embedded: {('--embed-subs' in cmd)}")
    print()

    # Compare with working manual command
    print("=" * 80)
    print("COMPARISON WITH WORKING MANUAL COMMAND:")
    print("=" * 80)

    manual_flags = [
        "--audio-multistreams",
        "--embed-chapters",
        "--embed-subs",
        "--cookies",
        "-f 313+251-8+251-0+251-1",
    ]

    for flag in manual_flags:
        if flag.startswith("-f "):
            # Check format separately
            expected_format = flag.split()[1]
            actual_format = cmd[cmd.index("-f") + 1] if "-f" in cmd else None
            status = "✅" if actual_format == expected_format else "❌"
            print(
                f"{status} Format: expected '{expected_format}', got '{actual_format}'"
            )
        else:
            status = "✅" if flag in cmd else "❌"
            print(f"{status} {flag}")

    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Compare this generated command with your actual HomeTube logs")
    print("2. Look for the line: '💻 Full yt-dlp command:'")
    print("3. Check if --audio-multistreams is present in the actual command")
    print("4. Verify the format string is exactly: 313+251-8+251-0+251-1")
    print()


if __name__ == "__main__":
    main()
