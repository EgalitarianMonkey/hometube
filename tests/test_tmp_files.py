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
