"""Tests for temporary file naming utilities"""

from pathlib import Path


class TestTmpFileNaming:
    """Test temporary file naming functions"""

    def test_get_video_track_path(self, tmp_path):
        """Should generate correct video track path"""
        from app.tmp_files import get_video_track_path

        path = get_video_track_path(tmp_path, "399", "webm")
        assert path == tmp_path / "video-399.webm"

        # Should handle extension with dot
        path = get_video_track_path(tmp_path, "616", ".mp4")
        assert path == tmp_path / "video-616.mp4"

    def test_get_audio_track_path(self, tmp_path):
        """Should generate correct audio track path"""
        from app.tmp_files import get_audio_track_path

        path = get_audio_track_path(tmp_path, "251", "opus")
        assert path == tmp_path / "audio-251.opus"

        path = get_audio_track_path(tmp_path, "140", ".m4a")
        assert path == tmp_path / "audio-140.m4a"

    def test_get_subtitle_path(self, tmp_path):
        """Should generate correct subtitle paths"""
        from app.tmp_files import get_subtitle_path

        # Original subtitle
        path = get_subtitle_path(tmp_path, "en")
        assert path == tmp_path / "subtitles.en.srt"

        # Cut subtitle
        path = get_subtitle_path(tmp_path, "fr", is_cut=True)
        assert path == tmp_path / "subtitles-cut.fr.srt"

    def test_get_final_path(self):
        """Should generate correct path for final file"""
        from app.tmp_files import get_final_path

        path = get_final_path(Path("/tmp/test"), "mkv")
        assert path == Path("/tmp/test/final.mkv")

        path = get_final_path(Path("/tmp/test"), "mp4")
        assert path == Path("/tmp/test/final.mp4")

    def test_get_session_log_path(self, tmp_path):
        """Should generate correct session log path"""
        from app.tmp_files import get_session_log_path

        path = get_session_log_path(tmp_path)
        assert path == tmp_path / "session.log"

    def test_find_video_tracks(self, tmp_path):
        """Should find all video track files"""
        from app.tmp_files import find_video_tracks

        # Create test files
        (tmp_path / "video-399.webm").touch()
        (tmp_path / "video-616.mp4").touch()
        (tmp_path / "audio-251.opus").touch()  # Should be ignored
        (tmp_path / "other.mkv").touch()  # Should be ignored

        tracks = find_video_tracks(tmp_path)
        assert len(tracks) >= 2  # At least our test files
        assert any("video-399.webm" in str(t) for t in tracks)
        assert any("video-616.mp4" in str(t) for t in tracks)

    def test_find_audio_tracks(self, tmp_path):
        """Should find all audio track files"""
        from app.tmp_files import find_audio_tracks

        # Create test files
        (tmp_path / "audio-251.opus").touch()
        (tmp_path / "audio-140.m4a").touch()
        (tmp_path / "video-399.webm").touch()  # Should be ignored

        tracks = find_audio_tracks(tmp_path)
        assert len(tracks) >= 2
        assert any("audio-251.opus" in str(t) for t in tracks)
        assert any("audio-140.m4a" in str(t) for t in tracks)

    def test_find_subtitles(self, tmp_path):
        """Should find subtitle files"""
        from app.tmp_files import find_subtitles

        # Create test files
        (tmp_path / "subtitles.en.srt").touch()
        (tmp_path / "subtitles.fr.srt").touch()
        (tmp_path / "subtitles-cut.en.srt").touch()
        (tmp_path / "subtitles-cut.fr.srt").touch()

        # Find original subtitles
        originals = find_subtitles(tmp_path, is_cut=False)
        assert len(originals) >= 2
        assert any("subtitles.en.srt" in str(s) for s in originals)

        # Find cut subtitles
        cuts = find_subtitles(tmp_path, is_cut=True)
        assert len(cuts) >= 2
        assert any("subtitles-cut.fr.srt" in str(s) for s in cuts)

    def test_find_final_file(self, tmp_path):
        """Should find final file"""
        from app.tmp_files import find_final_file

        # No final file yet
        assert find_final_file(tmp_path) is None

        # Create final file
        final = tmp_path / "final.mkv"
        final.touch()

        found = find_final_file(tmp_path)
        assert found is not None
        assert found.name == "final.mkv"

    def test_extract_format_id_from_filename(self):
        """Should extract format ID from filename"""
        from app.tmp_files import extract_format_id_from_filename

        assert extract_format_id_from_filename("video-399.webm") == "399"
        assert extract_format_id_from_filename("audio-251.opus") == "251"
        assert extract_format_id_from_filename("video-616+140.mkv") == "616+140"
        assert extract_format_id_from_filename("other.mkv") is None

    def test_extract_language_from_subtitle(self):
        """Should extract language from subtitle filename"""
        from app.tmp_files import extract_language_from_subtitle

        assert extract_language_from_subtitle("subtitles.en.srt") == "en"
        assert extract_language_from_subtitle("subtitles.fr.srt") == "fr"
        assert extract_language_from_subtitle("subtitles-cut.en.srt") == "en"
        assert extract_language_from_subtitle("subtitles-cut.fr.srt") == "fr"
        assert extract_language_from_subtitle("other.srt") is None

    def test_nonexistent_directory(self, tmp_path):
        """Should handle nonexistent directories gracefully"""
        from app.tmp_files import find_video_tracks, find_audio_tracks, find_final_file

        nonexistent = tmp_path / "does_not_exist"

        assert find_video_tracks(nonexistent) == []
        assert find_audio_tracks(nonexistent) == []
        assert find_final_file(nonexistent) is None


class TestTmpFolderStructure:
    """Test that temporary files are always at root of unique video folder."""

    def test_tmp_folder_always_at_root(self, tmp_path):
        """
        Test that tmp folder structure is flat (no subfolder replication).

        Even if the user selects a subfolder like "Tech/HomeLab", all temporary files
        should be written directly to the root of the unique video folder.
        """
        from app.tmp_files import (
            get_video_track_path,
            get_subtitle_path,
            get_final_path,
        )

        tmp_video_dir = tmp_path / "youtube-abc123"
        tmp_video_dir.mkdir()

        # Create test files at the root of unique folder
        video_file = get_video_track_path(tmp_video_dir, "22", "mp4")
        video_file.parent.mkdir(parents=True, exist_ok=True)
        video_file.write_text("fake video")

        subtitle_file = get_subtitle_path(tmp_video_dir, "en", is_cut=False)
        subtitle_file.write_text("fake subtitle")

        final_file = get_final_path(tmp_video_dir, "mp4")
        final_file.write_text("fake final")

        # Verify all files are at the root of tmp_video_dir
        assert video_file.parent == tmp_video_dir, "Video should be at root"
        assert subtitle_file.parent == tmp_video_dir, "Subtitle should be at root"
        assert final_file.parent == tmp_video_dir, "Final file should be at root"

        # Verify no subfolder was created
        tech_subfolder = tmp_video_dir / "Tech"
        assert not tech_subfolder.exists(), "No subfolder should be created in tmp"

    def test_destination_subfolder_only_used_for_final_copy(self, tmp_path):
        """
        Test that the user's selected subfolder is only used when copying final file.
        """
        import shutil
        from app.tmp_files import get_final_path

        # Setup directories
        tmp_video_dir = tmp_path / "tmp" / "youtube-abc123"
        tmp_video_dir.mkdir(parents=True)

        videos_folder = tmp_path / "Videos"
        videos_folder.mkdir()

        # User selected subfolder
        video_subfolder = "Tech/HomeLab"
        dest_dir = videos_folder / video_subfolder
        dest_dir.mkdir(parents=True)

        # Temporary files are at root of unique folder
        final_source = get_final_path(tmp_video_dir, "mp4")
        final_source.write_text("final video content")

        # Move to destination WITH subfolder structure
        intended_filename = "my_video"
        final_destination = dest_dir / f"{intended_filename}.mp4"
        shutil.move(str(final_source), str(final_destination))

        # Verify structure
        assert not final_source.exists(), "Source should be moved"
        assert final_destination.parent == dest_dir
        assert final_destination.exists()


class TestResilienceScenarios:
    """Test realistic resilience scenarios for generic file naming."""

    def test_resume_after_download_interruption(self, tmp_path):
        """Test resuming after download was interrupted."""
        from app.tmp_files import find_final_file

        # Create generic file simulating interrupted download
        generic_file = tmp_path / "final.mkv"
        generic_file.write_text("downloaded content")

        # New session starts - should find existing file
        found = find_final_file(tmp_path)

        assert found is not None
        assert found == generic_file
        assert found.name == "final.mkv"

    def test_no_confusion_with_multiple_videos(self, tmp_path):
        """Test that generic files from different videos don't conflict."""
        from app.tmp_files import get_final_path, find_final_file

        # Create subdirectories for different videos
        video1_dir = tmp_path / "youtube-abc123"
        video2_dir = tmp_path / "youtube-def456"
        video1_dir.mkdir()
        video2_dir.mkdir()

        file1 = get_final_path(video1_dir, "mkv")
        file2 = get_final_path(video2_dir, "mkv")

        file1.write_text("video 1 content")
        file2.write_text("video 2 content")

        # Finding files in each directory should work independently
        found1 = find_final_file(video1_dir)
        found2 = find_final_file(video2_dir)

        assert found1 == file1
        assert found2 == file2
        assert found1.name == "final.mkv"
        assert found2.name == "final.mkv"

    def test_find_final_file_prefers_mkv_over_mp4(self, tmp_path):
        """Test that MKV is preferred when both formats exist."""
        from app.tmp_files import find_final_file

        mkv_file = tmp_path / "final.mkv"
        mp4_file = tmp_path / "final.mp4"
        mkv_file.write_text("mkv content")
        mp4_file.write_text("mp4 content")

        result = find_final_file(tmp_path)

        assert result == mkv_file  # MKV should be preferred
