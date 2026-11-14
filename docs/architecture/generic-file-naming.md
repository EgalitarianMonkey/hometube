# Generic File Naming System

## Overview

HomeTube uses a **generic file naming system** for temporary files to ensure **resilience** and **independence from video titles**. This allows the system to resume interrupted downloads and handle special characters or title changes gracefully.

## File Structure

```
TMP_DOWNLOAD_FOLDER/
└── youtube-{VIDEO_ID}/
    ├── url_info.json              # Video metadata from yt-dlp
    ├── status.json                # Download status and progress tracking
    ├── video-{FORMAT_ID}.{ext}    # Downloaded video (e.g., video-399.mkv)
    ├── subtitles.{lang}.srt       # Original subtitles (e.g., subtitles.en.srt)
    ├── subtitles-cut.{lang}.srt   # Cut subtitles (e.g., subtitles-cut.en.srt)
    ├── session.log                # Processing logs
    └── final.{ext}                # Final processed file (e.g., final.mkv)
```

## Download & Rename Strategy

### Why This Approach?

yt-dlp requires a filename template for downloads. We use a **pragmatic two-step approach**:

1. **Download with readable name** (yt-dlp compatibility)
   - yt-dlp uses the video title: `"My Video Title.mkv"`
   - This is required by yt-dlp's `-o` option
   - Logs show meaningful names during download

2. **Immediate rename to generic names** (resilience)
   - Video: `"My Video Title.mkv"` → `"video-399.mkv"`
   - Subtitles: `"My Video Title.en.srt"` → `"subtitles.en.srt"`
   - Atomic operation right after download completes

3. **Resume support** (intelligent caching)
   - Before downloading, check if `video-*.{ext}` exists
   - If found, skip download and reuse existing file
   - No re-download needed for interrupted processing

### Benefits

✅ **yt-dlp Compatibility** - Works naturally with yt-dlp's design  
✅ **Simple & Maintainable** - Just rename operations, no complex hacks  
✅ **Readable Logs** - Video titles visible during download  
✅ **Fast Resume** - Instant detection of existing files  
✅ **Title Independence** - Files work even if title changes  
✅ **Format Visibility** - `video-399.mkv` shows format ID used  

### Workflow Example

```
1. Download Request: "Amazing Video Tutorial"
   📥 yt-dlp downloads as: "Amazing Video Tutorial.mkv"
   
2. Immediate Rename:
   📦 "Amazing Video Tutorial.mkv" → "video-399.mkv"
   📝 "Amazing Video Tutorial.en.srt" → "subtitles.en.srt"
   📝 "Amazing Video Tutorial.fr.srt" → "subtitles.fr.srt"
   
3. Processing:
   🎬 Cut video: "video-399.mkv" → "final.mkv"
   📝 Cut subs: "subtitles.en.srt" → "subtitles-cut.en.srt"
   
4. Final Copy:
   💾 "final.mkv" → "/videos/Amazing Video Tutorial.mkv"
   (Original name from user input or video title)
```

## Status Tracking

The `status.json` file tracks download progress and completion:

```json
{
  "url": "https://youtube.com/watch?v=...",
  "id": "abc123",
  "title": "Amazing Video Tutorial",
  "type": "video",
  "downloaded_formats": [
    {
      "video_format": "399+251",
      "subtitles": ["subtitles.en.srt", "subtitles.fr.srt"],
      "filesize_approx": 41943040,
      "status": "completed",
      "actual_filesize": 41993040,
      "downloaded_at": "2024-01-15T10:30:00Z"
    }
  ],
  "last_updated": "2024-01-15T10:30:00Z"
}
```

This is used for:
- Tracking download progress across sessions
- Verifying file integrity after download
- Resume capability for interrupted downloads
- Tracking what video this temporary folder belongs to
- Resume support across sessions

## Subtitle Naming

### Original Subtitles
- Format: `subtitles.{lang}.srt`
- Examples: `subtitles.en.srt`, `subtitles.fr.srt`, `subtitles.es.srt`

### Cut Subtitles  
- Format: `subtitles-cut.{lang}.srt`
- Examples: `subtitles-cut.en.srt`, `subtitles-cut.fr.srt`
- Created by `process_subtitles_for_cutting()`

### Backward Compatibility

The subtitle search functions (`find_subtitle_files_optimized`) check in this order:

1. Generic names (preferred): `subtitles.{lang}.srt`
2. Video title names (legacy): `{video_title}.{lang}.srt`
3. Other patterns: `{video_title}_{lang}.srt`, etc.

This ensures compatibility with existing downloads.

## Video Track Naming

### Format
`video-{FORMAT_ID}.{ext}`

### Examples
- `video-399.mkv` - Video format 399 in MKV container
- `video-298.mp4` - Video format 298 in MP4 container
- `video-616.webm` - Video format 616 in WebM container

### Format ID Information
The format ID comes from yt-dlp and indicates:
- Video resolution
- Codec used (AV1, VP9, H.264, etc.)
- Bitrate and quality level

This makes it easy to identify which format was actually downloaded.

## Final File

### During Processing
`final.{ext}` - The processed file ready for copying

### Extension Determination
- If cutting: matches source extension (`.mkv`, `.mp4`)
- If not cutting: uses downloaded file extension
- WebM files are converted to MKV for better subtitle support

### Move to Destination
When moving to the final location (saves disk space):
1. Use the filename from user input or video title
2. Combine with file extension
3. Move: `final.mkv` → `/videos/{filename}.mkv`

## Resilience Features

### Interrupted Download
✅ Generic files persist in tmp folder  
✅ Next run detects `video-*.{ext}` and skips download  
✅ Processing resumes from where it stopped  

### Title Changes
✅ Files are independent of video title  
✅ Re-running with different title still works  
✅ Filename from user input remains consistent  

### Special Characters
✅ No issues with Unicode, emojis, etc.  
✅ Generic names are filesystem-safe  
✅ User-provided filename used for final copy  

### Cache Preservation
✅ **`video-{FORMAT_ID}.{ext}` is always preserved** for future reuse  
✅ **`final.{ext}` is MOVED to destination** (saves disk space, no duplicate)  
✅ No automatic cleanup in normal workflow  
✅ Manual cleanup available via configuration options  

This ensures that:
- Re-downloading the same video skips download instantly
- Processing can be re-run without re-downloading
- Debugging is possible with all intermediate files available

### Debugging
✅ Clear file names show purpose  
✅ Format ID visible in video filename  
✅ Easy to inspect tmp folder contents  
✅ All intermediate files preserved by default  

## Configuration

### Temporary File Management

HomeTube provides two options for managing temporary files:

#### 1. Automatic Cleanup After Download

By default, **temporary files are preserved** for resilience and caching:

```bash
# Default behavior (recommended for development/debugging)
REMOVE_TMP_FILES_AFTER_DOWNLOAD=false
```

This ensures:
- ✅ Fast resume on interrupted downloads
- ✅ Instant skip when re-downloading same video
- ✅ Debugging with all intermediate files
- ✅ No wasted bandwidth re-downloading

To enable automatic cleanup after successful download:

```bash
# Enable cleanup (recommended for production/limited disk space)
REMOVE_TMP_FILES_AFTER_DOWNLOAD=true
```

**Note**: Even with cleanup enabled, files are only removed after successful completion. Failed downloads always preserve files for resume.

#### 2. Fresh Start for Each Download

By default, **existing tmp files are reused** for intelligent caching:

```bash
# Default behavior (recommended for resilience)
NEW_DOWNLOAD_WITHOUT_TMP_FILES=false
```

To force a clean slate before each download:

```bash
# Enable fresh download (useful after errors or corruption)
NEW_DOWNLOAD_WITHOUT_TMP_FILES=true
```

**Use case**: When you encounter errors or want to ensure a completely fresh download without any cached artifacts.

### Disk Space Management

If disk space is a concern:

1. **Monitor tmp folder size**: `du -sh tmp/`
2. **Manual cleanup**: Remove old video folders when done
3. **Selective cleanup**: Keep only recent downloads in cache
4. **Use SSD**: Fast storage improves overall performance

The tmp folder size grows with the number of processed videos, but enables instant resume and cache benefits.

## Code Example

### Finding Existing Files
```python
# Check for cached video
existing_videos = tmp_files.find_video_tracks(tmp_subfolder_dir)
if existing_videos:
    print(f"Found cached: {existing_videos[0].name}")
    # Skip download
```

### Renaming After Download
```python
# After yt-dlp downloads with video title
downloaded = tmp_subfolder_dir / f"{video_title}.mkv"

# Rename to generic name
format_id = st.session_state["downloaded_format_id"]
generic = tmp_files.get_video_track_path(tmp_subfolder_dir, format_id, "mkv")
downloaded.rename(generic)

print(f"Renamed: {downloaded.name} → {generic.name}")
```

### Getting Final Filename
```python
# When moving to destination
job_config = tmp_files.load_job_config(tmp_subfolder_dir)
intended_name = job_config["filename"]

# Move with original name (saves disk space)
final_path = dest_dir / f"{intended_name}.mkv"
shutil.move(source, final_path)
```

## Related Documentation

- [Intelligent URL Caching](./intelligent-caching.md) - How url_info.json caching works
- [Unique Folder Naming](../README.md#unique-video-folders) - How video IDs are extracted
- [File System Utils](../app/file_system_utils.py) - Filesystem operations
- [Temporary Files Utils](../app/tmp_files.py) - Generic naming functions

## Testing

The generic file naming system is comprehensively tested:

```bash
# Run all tests
pytest tests/

# Test specific functionality
pytest tests/test_tmp_files.py
pytest tests/test_subtitles_utils.py
```

**Test Coverage**: see `make test-coverage`; the naming behaviour itself is covered by `tests/test_tmp_files.py` ✅
