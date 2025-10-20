# Generic File Naming System

## Overview

HomeTube uses a **generic file naming system** for temporary files to ensure **resilience** and **independence from video titles**. This allows the system to resume interrupted downloads and handle special characters or title changes gracefully.

## File Structure

```
TMP_DOWNLOAD_FOLDER/
└── youtube-{VIDEO_ID}/
    ├── url_info.json              # Video metadata from yt-dlp
    ├── job.json                   # Processing job configuration
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
   (Original name restored from job.json)
```

## Job Configuration

The `job.json` file stores metadata about the intended output:

```json
{
  "filename": "Amazing Video Tutorial",
  "url": "https://youtube.com/watch?v=...",
  "timestamp": 1729435200.0
}
```

This allows:
- Restoring the original filename when copying to final destination
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

### Copy to Destination
When copying to the final location:
1. Read intended filename from `job.json`
2. Combine with file extension
3. Copy: `final.mkv` → `/videos/{intended_name}.mkv`

## Resilience Features

### Interrupted Download
✅ Generic files persist in tmp folder  
✅ Next run detects `video-*.{ext}` and skips download  
✅ Processing resumes from where it stopped  

### Title Changes
✅ Files are independent of video title  
✅ Re-running with different title still works  
✅ Original name comes from `job.json`  

### Special Characters
✅ No issues with Unicode, emojis, etc.  
✅ Generic names are filesystem-safe  
✅ Original name preserved in `job.json`  

### Debugging
✅ Clear file names show purpose  
✅ Format ID visible in video filename  
✅ Easy to inspect tmp folder contents  

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
# When copying to destination
job_config = tmp_files.load_job_config(tmp_subfolder_dir)
intended_name = job_config["filename"]

# Copy with original name
final_path = dest_dir / f"{intended_name}.mkv"
shutil.copy2(source, final_path)
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
pytest tests/test_generic_file_naming.py
pytest tests/test_subtitles_utils.py
```

**Test Coverage**: 188 tests passing ✅
