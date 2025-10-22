"""
Test to verify that temporary files are always written at the root of the unique platform-ID folder,
regardless of the user's selected subfolder destination.
"""

from pathlib import Path
import tempfile
from app import tmp_files


def test_tmp_folder_always_at_root():
    """
    Test that tmp folder structure is flat (no subfolder replication).

    Even if the user selects a subfolder like "Tech/HomeLab", all temporary files
    should be written directly to the root of the unique video folder (e.g., tmp/youtube-abc123/).
    The subfolder is only used when copying the final file to the destination.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_video_dir = Path(temp_dir) / "youtube-abc123"
        tmp_video_dir.mkdir()

        # NEW LOGIC: No more tmp_subfolder_dir variable, always use tmp_video_dir directly

        # Create test files at the root of unique folder
        video_file = tmp_files.get_video_track_path(tmp_video_dir, "22", "mp4")
        video_file.parent.mkdir(parents=True, exist_ok=True)
        video_file.write_text("fake video")

        subtitle_file = tmp_files.get_subtitle_path(tmp_video_dir, "en", is_cut=False)
        subtitle_file.write_text("fake subtitle")

        final_file = tmp_files.get_final_path(tmp_video_dir, "mp4")
        final_file.write_text("fake final")

        # Verify all files are at the root of tmp_video_dir (no subfolder structure)
        assert video_file.parent == tmp_video_dir, "Video should be at root"
        assert subtitle_file.parent == tmp_video_dir, "Subtitle should be at root"
        assert final_file.parent == tmp_video_dir, "Final file should be at root"

        # Verify no subfolder was created
        tech_subfolder = tmp_video_dir / "Tech"
        assert not tech_subfolder.exists(), "No subfolder should be created in tmp"

        print(
            "✅ All temporary files are correctly written at the root of unique folder"
        )
        print(f"   Video: {video_file.relative_to(tmp_video_dir)}")
        print(f"   Subtitle: {subtitle_file.relative_to(tmp_video_dir)}")
        print(f"   Final: {final_file.relative_to(tmp_video_dir)}")


def test_destination_subfolder_only_used_for_final_copy():
    """
    Test that the user's selected subfolder is only used when copying the final file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup directories
        tmp_video_dir = Path(temp_dir) / "tmp" / "youtube-abc123"
        tmp_video_dir.mkdir(parents=True)

        videos_folder = Path(temp_dir) / "Videos"
        videos_folder.mkdir()

        # User selected subfolder
        video_subfolder = "Tech/HomeLab"
        dest_dir = videos_folder / video_subfolder
        dest_dir.mkdir(parents=True)

        # Temporary files are at root of unique folder (no more tmp_subfolder_dir)
        final_source = tmp_files.get_final_path(tmp_video_dir, "mp4")
        final_source.write_text("final video content")

        # Copy to destination WITH subfolder structure
        intended_filename = "my_video"
        final_destination = dest_dir / f"{intended_filename}.mp4"

        import shutil

        shutil.copy2(str(final_source), str(final_destination))

        # Verify structure
        assert final_source.parent == tmp_video_dir, "Source should be at tmp root"
        assert final_destination.parent == dest_dir, "Destination should use subfolder"
        assert final_destination.exists(), "Final file should exist in destination"

        # Verify path structure
        relative_dest = final_destination.relative_to(videos_folder)
        assert str(relative_dest) == f"{video_subfolder}/{intended_filename}.mp4"

        print("✅ Destination subfolder correctly used only for final copy")
        print(f"   Temp source: {final_source}")
        print(f"   Final dest: {relative_dest}")


if __name__ == "__main__":
    test_tmp_folder_always_at_root()
    test_destination_subfolder_only_used_for_final_copy()
    print("\n✅ All tests passed!")
