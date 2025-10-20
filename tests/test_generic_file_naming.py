"""
Test the generic file naming and resilience logic.
"""

from app import tmp_files


class TestGenericFileNaming:
    """Test generic file naming for download resilience."""

    def test_get_final_path_format(self, tmp_path):
        """Test that final paths follow the correct format."""
        result = tmp_files.get_final_path(tmp_path, "mkv")

        assert result.name == "final.mkv"
        assert result.parent == tmp_path

    def test_get_final_path_different_extensions(self, tmp_path):
        """Test that different extensions are handled correctly."""
        result_mkv = tmp_files.get_final_path(tmp_path, "mkv")
        result_mp4 = tmp_files.get_final_path(tmp_path, "mp4")

        assert result_mkv.name == "final.mkv"
        assert result_mp4.name == "final.mp4"

    def test_find_final_file_returns_none_when_not_exists(self, tmp_path):
        """Test that find_final_file returns None when no file exists."""
        result = tmp_files.find_final_file(tmp_path)

        assert result is None

    def test_find_final_file_finds_mkv(self, tmp_path):
        """Test that find_final_file can find MKV files."""
        test_file = tmp_path / "final.mkv"
        test_file.write_text("test content")

        result = tmp_files.find_final_file(tmp_path)

        assert result is not None
        assert result == test_file

    def test_find_final_file_finds_mp4(self, tmp_path):
        """Test that find_final_file can find MP4 files."""
        test_file = tmp_path / "final.mp4"
        test_file.write_text("test content")

        result = tmp_files.find_final_file(tmp_path)

        assert result is not None
        assert result == test_file

    def test_find_final_file_prefers_mkv_over_mp4(self, tmp_path):
        """Test that MKV is preferred when both formats exist."""
        mkv_file = tmp_path / "final.mkv"
        mp4_file = tmp_path / "final.mp4"
        mkv_file.write_text("mkv content")
        mp4_file.write_text("mp4 content")

        result = tmp_files.find_final_file(tmp_path)

        assert result == mkv_file  # MKV should be preferred

    def test_save_and_load_job_config(self, tmp_path):
        """Test saving and loading job configuration."""
        config = {
            "filename": "My Amazing Video",
            "url": "https://youtube.com/watch?v=test",
            "format": "mkv",
        }

        # Save config
        success = tmp_files.save_job_config(tmp_path, config)
        assert success

        # Load config
        loaded = tmp_files.load_job_config(tmp_path)
        assert loaded is not None
        assert loaded["filename"] == "My Amazing Video"
        assert loaded["url"] == "https://youtube.com/watch?v=test"
        assert loaded["format"] == "mkv"

    def test_load_job_config_nonexistent(self, tmp_path):
        """Test loading job config when it doesn't exist."""
        result = tmp_files.load_job_config(tmp_path)
        assert result is None

    def test_round_trip_with_job_config(self, tmp_path):
        """Test complete workflow with job config and generic file."""
        original_name = "My Test Video - Episode 1"
        extension = "mkv"

        # Save job config with intended filename
        job_config = {"filename": original_name}
        tmp_files.save_job_config(tmp_path, job_config)

        # Create generic final file
        generic_path = tmp_files.get_final_path(tmp_path, extension)
        generic_path.write_text("test content")

        # Find it
        found_path = tmp_files.find_final_file(tmp_path)
        assert found_path is not None
        assert found_path.name == "final.mkv"

        # Load intended filename from job config
        loaded_config = tmp_files.load_job_config(tmp_path)
        assert loaded_config["filename"] == original_name


class TestResilienceScenarios:
    """Test realistic resilience scenarios."""

    def test_resume_after_download_interruption(self, tmp_path):
        """Test resuming after download was interrupted."""
        # Simulate a downloaded file that was renamed to generic
        original_name = "MyVideo"

        # Save job config with original name
        tmp_files.save_job_config(tmp_path, {"filename": original_name})

        # Create generic file
        generic_file = tmp_path / "final.mkv"
        generic_file.write_text("downloaded content")

        # New session starts - should find existing file
        found = tmp_files.find_final_file(tmp_path)

        assert found is not None
        assert found == generic_file
        assert found.name == "final.mkv"

        # Verify we can get the original name from job config
        job_config = tmp_files.load_job_config(tmp_path)
        assert job_config["filename"] == original_name

    def test_no_confusion_with_multiple_videos(self, tmp_path):
        """Test that generic files from different videos don't conflict."""
        # Create subdirectories for different videos (realistic structure)
        video1_dir = tmp_path / "youtube-abc123"
        video2_dir = tmp_path / "youtube-def456"
        video1_dir.mkdir()
        video2_dir.mkdir()

        # Each video has its own job config and generic file
        tmp_files.save_job_config(video1_dir, {"filename": "FirstVideo"})
        tmp_files.save_job_config(video2_dir, {"filename": "SecondVideo"})

        file1 = tmp_files.get_final_path(video1_dir, "mkv")
        file2 = tmp_files.get_final_path(video2_dir, "mkv")

        file1.write_text("video 1 content")
        file2.write_text("video 2 content")

        # Finding files in each directory should work independently
        found1 = tmp_files.find_final_file(video1_dir)
        found2 = tmp_files.find_final_file(video2_dir)

        assert found1 == file1
        assert found2 == file2

        # Both files have the same generic name but different configs
        assert found1.name == "final.mkv"
        assert found2.name == "final.mkv"

        # But different intended names from job configs
        config1 = tmp_files.load_job_config(video1_dir)
        config2 = tmp_files.load_job_config(video2_dir)
        assert config1["filename"] == "FirstVideo"
        assert config2["filename"] == "SecondVideo"

    def test_skip_redownload_if_generic_exists(self, tmp_path):
        """Test the logic for skipping redownload."""
        # Simulate existing generic file from previous session
        existing_file = tmp_path / "final.mkv"
        existing_file.write_text("already downloaded")

        # Check if file exists (what the main logic does)
        found = tmp_files.find_final_file(tmp_path)

        # Should find the existing file
        assert found is not None
        assert found.exists()
        assert found.name == "final.mkv"

        # This would trigger the skip logic in main.py
        # No actual download would happen
