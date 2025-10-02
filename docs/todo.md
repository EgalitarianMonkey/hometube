# 📝 HomeTube - To-Do List

This document outlines planned improvements and enhancements for HomeTube.

## Direct download

**Status:** Idea
**Priority:** Low

**Description:**
Add a direct download option to download directly from the browser in the local Download folder..

---

## Add yt-dlp extra args

**Status:** ✅ Completed
**Priority:** High

**Description:**
Have an advanced settings section to add extra yt-dlp args for power users directly from the UI.
Then, proxy, --max-filesize SIZE, etc., can be added easily.

**Implementation:** Advanced Options section added with custom yt-dlp arguments support, environment variable configuration, and full translation support.

---

## Playlist Support & Batch Operations

**Status:** Planned
**Priority:** High

**Description:**
Add comprehensive playlist support for YouTube, SoundCloud, and other platforms with advanced batch processing capabilities.

**Features to implement:**
- **Playlist Detection**: Automatic detection of playlist URLs from supported platforms
- **Batch Download**: Download entire playlists with progress tracking per video
- **Individual Selection**: Allow users to select specific videos from playlists
- **Folder Organization**: Automatic folder creation by playlist name/creator
- **Bulk Renaming**: Advanced renaming patterns for batch operations
  - Pattern templates: `{playlist_title}/{index:02d} - {title}.{ext}`
  - Variable substitution: `{uploader}`, `{upload_date}`, `{duration}`, `{view_count}`
  - Custom numbering: Zero-padded indices, custom start numbers
  - Sanitization: Automatic filename cleaning for different filesystems
- **Quality Control**: Apply same quality settings to all playlist videos
- **Resume Support**: Resume interrupted playlist downloads
- **Progress Tracking**: Individual video progress within playlist context
- **Filtering Options**: Skip videos by duration, size, or upload date

**Technical considerations:**
- Extend UI with playlist-specific controls
- Add playlist metadata extraction
- Implement batch processing queue system
- Add pattern validation and preview
- Support for nested folder structures

---

## General user experience and interface refinements
**Status:** Planned  
**Priority:** Medium
**Ideas for future development:**
- Improve layout and spacing for better readability
- Refine color scheme and visual hierarchy

---

## Multiple audio tracks selection
**Status:** Idea
**Priority:** Low

**Description:**
Download and embed the default audio track along all available audio tracks matching the AUDIO_LANGUAGES environment variables.

---

## Download Progress Enhancements
**Status:** Planned  
**Priority:** Medium

**Ideas for future development:**
- Update progress status
- Estimated completion time improvements
- User-friendly error recovery suggestions
- Graceful handling of network timeouts
- Better error messages for common issues

---

## Video Processing Optimizations
**Status:** Idea  
**Priority:** Low

**Ideas for future development:**
- Hardware acceleration support (GPU encoding)
- Advanced audio processing options
- Batch processing capabilities
- Custom processing profiles

---

## Auto-Generated subtitles
**Status:** Idea
**Priority:** Low

**Description:**
Auto-generated subtitles are often very bad in any video player except Youtube itself. Adding a better subtitles generator to HomeTube would permit good subtitles for any downloaded videos in any interested languages (Whisper?).

---

## Integration Enhancements
**Status:** Idea
**Priority:** Low

**Potential integrations:**
- Webhook actions for notifications, scans for completed downloads
- API endpoints for automation
- Plugin system for custom processing
- Integration with more media servers

---

## 📋 Notes

- Priority levels: High (critical/blocking), Medium (important), Low (nice to have)
- Status: To Do, In Progress, Planned, Idea, Done
- Always test changes in development environment before deployment
- Consider backward compatibility when making changes
- Update documentation after implementing features

---

**Last Updated:** September 19, 2025  
**Version:** Based on current main branch