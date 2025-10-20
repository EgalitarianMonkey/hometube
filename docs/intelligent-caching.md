# Intelligent URL Analysis Caching

## Overview

HomeTube now includes intelligent caching for URL analysis results (`url_info.json`). This feature prevents unnecessary re-downloads of video metadata and protects high-quality cached data from being overwritten with lower-quality responses.

## Problem Statement

YouTube's API sometimes returns incomplete format information, providing only basic H.264 formats even when premium formats (AV1, VP9) are available. This can happen due to:

- Rate limiting
- Geographic restrictions
- API instability
- Bot detection

Previously, HomeTube would blindly overwrite existing metadata, potentially replacing a complete format list with a limited one.

## Solution

### Intelligent Reuse Logic

When analyzing a URL, HomeTube now:

1. **Checks if `url_info.json` already exists** in the video's unique folder
2. **Validates the integrity** of the existing file using `check_url_info_integrity()`
3. **Makes smart decisions**:
   - ✅ **Reuse** if file contains premium formats (AV1/VP9)
   - ✅ **Reuse** if file is a playlist (no quality check needed)
   - ❌ **Re-download** if file only has H.264 formats (limited quality)
   - ❌ **Re-download** if file is corrupted or invalid
   - ❌ **Re-download** if file doesn't exist

### Code Architecture

The logic is implemented in pure functions without Streamlit dependencies:

**`app/url_utils.py`**:
```python
def should_reuse_url_info(json_path: Path) -> Tuple[bool, Optional[Dict]]:
    """
    Check if existing url_info.json should be reused based on integrity.
    
    Returns:
        (True, data) - if should reuse existing file
        (False, None) - if should re-download
    """
```

**`app/main.py`**:
```python
def url_analysis(url: str) -> Optional[Dict]:
    """
    Analyze URL with intelligent caching.
    
    1. Check for existing url_info.json
    2. Validate integrity if exists
    3. Reuse or re-download based on quality
    """
```

## Benefits

### 🚀 Performance
- **Faster repeated downloads**: Skip metadata fetching when already cached
- **Reduced API calls**: Fewer requests to video platforms
- **Network savings**: No redundant data transfers

### 🎯 Quality Protection
- **Preserve premium formats**: Never downgrade from AV1/VP9 to H.264
- **Resilient to API issues**: Keep working even if platform returns limited data
- **Smart retry**: Only re-download when quality improves

### 🔒 Reliability
- **Handle corrupted files**: Gracefully recover from invalid JSON
- **Playlist optimization**: Always reuse playlist metadata (no quality concerns)
- **Safe defaults**: Re-download when in doubt

## Implementation Details

### Format Quality Detection

Uses `check_url_info_integrity()` from `medias_utils.py`:

```python
def check_url_info_integrity(url_info: Dict) -> bool:
    """
    Check if url_info contains premium formats (AV1 or VP9).
    
    Returns:
        True - if AV1 or VP9 found in video formats
        False - if only H.264/AVC found
    """
```

Detection criteria:
- **Premium codecs**: `av01`, `av1`, `vp9`, `vp09`
- **Limited codecs**: `avc1`, `h264`
- **Ignored**: Audio-only formats (`vcodec='none'`)

### Decision Matrix

| File Status | Type | Has Premium | Action |
|------------|------|-------------|--------|
| ❌ Not exists | - | - | **Download** |
| ✅ Exists | Video | ✅ Yes (AV1/VP9) | **Reuse** |
| ✅ Exists | Video | ❌ No (H.264 only) | **Download** |
| ✅ Exists | Playlist | - | **Reuse** (no check) |
| ⚠️ Corrupted | - | - | **Download** |

### Test Coverage

**11 unit tests** in `tests/test_url_info_reuse.py`:

- ✅ File existence checks
- ✅ Premium format detection (AV1, VP9)
- ✅ Limited format handling (H.264)
- ✅ Playlist handling
- ✅ Corrupted JSON recovery
- ✅ Edge cases (missing fields, unknown types)
- ✅ File saving with directory creation

## User Experience

### Visible Behavior

Users will see different log messages based on the caching decision:

**✅ Reusing cached data (premium formats)**:
```
📋 Found existing url_info.json, checking integrity...
✅ Existing url_info.json has premium formats - reusing it
```

**❌ Re-downloading (limited formats)**:
```
📋 Found existing url_info.json, checking integrity...
⚠️ Existing url_info.json has limited formats (h264 only) - will re-download
```

**✅ Reusing playlist**:
```
📋 Found existing url_info.json, checking integrity...
✅ Existing url_info.json (playlist) - reusing it
```

### Transparent to User

The feature works automatically without requiring any configuration or user interaction. Users benefit from:

- **Faster downloads** when re-downloading the same video
- **Better quality** by protecting premium format metadata
- **More reliability** when platforms have API issues

## Configuration

No configuration needed - the feature is always enabled and works intelligently based on content analysis.

## Future Enhancements

Possible improvements for future versions:

- **TTL (Time-To-Live)**: Add expiration for cached metadata (e.g., 24 hours)
- **Force refresh**: UI option to bypass cache and force re-download
- **Cache statistics**: Show cache hit/miss rates
- **Format preference**: Allow users to define minimum acceptable quality

## Related Features

This feature works in conjunction with:

- **URL Analysis Retry Logic**: Still retries with `--no-cache-dir` if initial analysis yields limited formats
- **Unique Video Folders**: Each video has isolated cache in `tmp/youtube-{VIDEO_ID}/`
- **Temporary File Preservation**: Files kept by default (`REMOVE_TMP_FILES=false`)
