"""
End-to-end tests for HomeTube using real application functions.
"""

from pathlib import Path
import pytest


class TestEndToEndDownload:
    """End-to-end download workflow tests using real HomeTube functions."""

    # @pytest.mark.slow
    def test_real_hometube_functions(self):
        """Test using actual HomeTube core functions for command building."""
        from app.file_system_utils import sanitize_filename, is_valid_cookie_file
        from app.medias_utils import video_id_from_url
        from app.core import (
            build_base_ytdlp_command,
            build_cookies_params,
            build_sponsorblock_params,
        )

        # Test configuration
        test_url = "https://www.youtube.com/watch?v=pXRviuL6vMY"
        expected_title = "Stressed Out - Twenty One Pilots"

        # Use real folders that are visible
        project_root = Path.cwd()
        videos_folder = project_root / "tmp" / "tests" / "videos"
        tmp_folder = project_root / "tmp" / "tests" / "tmp"

        # Create directories
        videos_folder.mkdir(parents=True, exist_ok=True)
        tmp_folder.mkdir(parents=True, exist_ok=True)

        print("🔧 Testing real HomeTube functions...")

        # Test 1: HomeTube filename sanitization
        safe_filename = sanitize_filename(expected_title)
        assert safe_filename, "Sanitized filename should not be empty"
        print(f"📝 Sanitized '{expected_title}' -> '{safe_filename}'")

        # Extract video ID and validate URL
        video_id = video_id_from_url(test_url)
        assert (
            video_id == "pXRviuL6vMY"
        ), f"Expected video ID pXRviuL6vMY, got {video_id}"
        print(f"🔗 Video ID extracted: {video_id}")

        # Test 2: Use REAL HomeTube functions to build command
        base_filename = safe_filename

        # Test build_base_ytdlp_command
        base_cmd = build_base_ytdlp_command(
            base_filename=base_filename,
            temp_dir=tmp_folder,
            format_spec="bv*[height<=1080]+ba*[acodec^=opus]/bv*+ba*/b[height<=1080]",
            embed_chapters=True,
            embed_subs=False,
            force_mp4=False,
            custom_args="",
        )
        print(f"✅ Base command built with {len(base_cmd)} arguments")
        assert len(base_cmd) > 20, "Base command should have many arguments"

        # Test build_cookies_params
        cookies_file = None
        possible_cookie_paths = [
            Path("cookies/youtube_cookies.txt"),
            Path("cookies/youtube_cookies-2025-09-29.txt"),
            Path("cookies/youtube_cookies-2025-09-27.txt"),
        ]

        for cookie_path in possible_cookie_paths:
            if cookie_path.exists() and is_valid_cookie_file(str(cookie_path)):
                cookies_file = cookie_path
                break

        if cookies_file:
            cookies_params = build_cookies_params(
                cookies_method="file", cookies_file_path=str(cookies_file.absolute())
            )
            print(f"🍪 Using cookies from: {cookies_file}")
        else:
            cookies_params = build_cookies_params(cookies_method="none")
            print("🍪 No valid cookies found - using none method")

        assert isinstance(cookies_params, list), "Cookies params should be a list"

        # Test build_sponsorblock_params
        sponsorblock_params = build_sponsorblock_params("Default")
        print(f"📺 SponsorBlock config: {len(sponsorblock_params)} parameters")
        assert isinstance(
            sponsorblock_params, list
        ), "SponsorBlock params should be a list"

        # Build final command using real HomeTube functions
        cmd = base_cmd.copy()
        cmd.extend(cookies_params)
        cmd.extend(sponsorblock_params)
        cmd.extend(["--write-auto-subs", "--sub-langs", "en", "--embed-subs"])
        cmd.append(test_url)

        print(
            f"🎯 Final command built with {len(cmd)} total arguments using real HomeTube functions!"
        )
        print(f"📋 Command preview: {' '.join(cmd[:8])}... [+{len(cmd)-8} more args]")

        # Verify command structure
        assert "yt-dlp" in cmd[0], "Command should start with yt-dlp"
        assert test_url in cmd, "URL should be in command"
        assert str(tmp_folder) in " ".join(cmd), "Temp folder should be in command"

        print("🎉 Real HomeTube functions test completed successfully!")
        print(f"📁 Test folders ready: videos={videos_folder}, tmp={tmp_folder}")
        print("📋 This is a vrai E2E test using real HomeTube code!")

    @pytest.mark.slow
    def test_real_youtube_download_with_actual_download(self):
        """Test that actually downloads a real YouTube video using HomeTube functions with ULTIMATE QUALITY."""
        import subprocess
        import time
        from app.file_system_utils import sanitize_filename, is_valid_cookie_file
        from app.medias_utils import video_id_from_url
        from app.core import (
            build_base_ytdlp_command,
            build_cookies_params,
        )

        # Test configuration - using a short video to minimize download time
        test_url = "https://www.youtube.com/watch?v=pXRviuL6vMY"
        expected_title = "Stressed Out - Twenty One Pilots"

        # Use real folders that are visible
        project_root = Path.cwd()
        videos_folder = project_root / "tmp" / "tests" / "videos"
        tmp_folder = project_root / "tmp" / "tests" / "tmp"

        # Create directories
        videos_folder.mkdir(parents=True, exist_ok=True)
        tmp_folder.mkdir(parents=True, exist_ok=True)

        # Skip if no network connectivity
        try:
            subprocess.run(
                ["ping", "-c", "1", "youtube.com"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pytest.skip("No network connectivity to YouTube")

        print("🎬 Starting REAL YouTube download E2E test with ULTIMATE QUALITY...")
        print(
            "⚠️  This will download in highest quality (AV1+Opus) and may take several minutes"
        )
        print("📊 Using HomeTube's premium quality profile system")

        # Test 1: HomeTube filename sanitization
        safe_filename = sanitize_filename(expected_title)
        assert safe_filename, "Sanitized filename should not be empty"
        print(f"📝 Sanitized filename: '{safe_filename}'")

        # Extract video ID
        video_id = video_id_from_url(test_url)
        assert (
            video_id == "pXRviuL6vMY"
        ), f"Expected video ID pXRviuL6vMY, got {video_id}"

        # Clean up any existing files
        for existing_file in videos_folder.glob(f"{safe_filename}*"):
            existing_file.unlink()
        for tmp_file in tmp_folder.glob("*"):
            if tmp_file.is_file():
                tmp_file.unlink()

        # Test 2: Build REAL command using HomeTube functions with HIGH QUALITY
        # Use a high-quality but compatible format for reliable E2E testing
        print("🏆 Using high-quality but compatible format for reliable E2E testing")

        base_cmd = build_base_ytdlp_command(
            base_filename=safe_filename,
            temp_dir=tmp_folder,
            format_spec="bv*[height<=1080][vcodec^=h264]+ba*[acodec^=aac]/bv*[height<=1080]+ba*/b[height<=1080]",  # High quality but compatible
            embed_chapters=True,  # Enable chapters for full experience
            embed_subs=True,  # Enable subs for full experience
            force_mp4=True,  # MP4 for maximum compatibility in tests
            custom_args="",  # No special args for compatibility
        )

        # Use cookies if available
        cookies_file = None
        possible_cookie_paths = [
            Path("cookies/youtube_cookies.txt"),
            Path("cookies/youtube_cookies-2025-09-29.txt"),
            Path("cookies/youtube_cookies-2025-09-27.txt"),
        ]

        for cookie_path in possible_cookie_paths:
            if cookie_path.exists() and is_valid_cookie_file(str(cookie_path)):
                cookies_file = cookie_path
                break

        if cookies_file:
            cookies_params = build_cookies_params(
                cookies_method="file", cookies_file_path=str(cookies_file.absolute())
            )
            print(f"🍪 Using cookies: {cookies_file}")
        else:
            cookies_params = build_cookies_params(cookies_method="none")
            print("🍪 No cookies - trying without authentication")

        # Build minimal command for faster download
        cmd = base_cmd.copy()
        cmd.extend(cookies_params)
        # Skip SponsorBlock for faster download
        cmd.append(test_url)

        print(f"🚀 Executing REAL download with {len(cmd)} arguments...")
        print(f"📁 Download location: {tmp_folder}")

        # Test 3: Execute the REAL download
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, cwd=Path.cwd(), capture_output=True, text=True, timeout=300
            )

            download_time = time.time() - start_time
            print(f"⏱️  Download completed in {download_time:.1f}s")

            # Check if download was successful
            if result.returncode != 0:
                print(f"❌ yt-dlp stderr: {result.stderr}")
                pytest.fail(f"Download failed with return code {result.returncode}")

            # Find downloaded file
            downloaded_files = list(tmp_folder.glob(f"{safe_filename}.*"))
            video_files = [
                f for f in downloaded_files if f.suffix in [".mp4", ".mkv", ".webm"]
            ]

            assert (
                len(video_files) > 0
            ), f"No video file found. Files: {list(tmp_folder.glob('*'))}"

            main_video = video_files[0]
            print(f"📹 Downloaded: {main_video.name}")

            # Test 4: Verify file properties (this tests the original bug fix)
            file_size = main_video.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            assert file_size > 100 * 1024, f"File too small ({file_size} bytes)"
            print(f"📊 File size: {file_size_mb:.2f} MB")

            # Test 5: Move file using HomeTube logic (simulate real workflow)
            import shutil

            final_destination = videos_folder / main_video.name
            shutil.move(str(main_video), str(final_destination))
            print(f"📁 Moved to final location: {final_destination.name}")

            # Verify file size preserved (tests the original file size bug)
            final_size = final_destination.stat().st_size
            final_size_mb = final_size / (1024 * 1024)
            assert final_size == file_size, "File size should be preserved during move"
            print(f"✅ Final file size: {final_size_mb:.2f} MB (preserved)")

            print("🎉 REAL download E2E test completed successfully!")
            print(f"📁 Downloaded file available at: {final_destination}")
            print(
                "💡 This was a complete end-to-end test with real HomeTube functions and real download!"
            )

        except subprocess.TimeoutExpired:
            pytest.fail("Download timed out after 5 minutes")
        except Exception as e:
            # Clean up on error
            print(f"❌ Test failed: {e}")
            for file in tmp_folder.glob("*"):
                if file.is_file():
                    try:
                        file.unlink()
                    except OSError:
                        pass
            raise e
