# 📝 HomeTube - To-Do List

This document outlines planned improvements and enhancements for HomeTube.


### 1. Browser Cookies Default Selection
**Status:** To Do  
**Priority:** Medium

**Issue:** When selecting "cookies from browser" in the dropdown menu, the browser selection shows Chrome as default even if `COOKIES_FROM_BROWSER` environment variable is set.

**Expected Behavior:** If `COOKIES_FROM_BROWSER` is defined in the environment, use its value as the default browser selection.

**Implementation Details:**
- Modify the browser selectbox in the cookies section
- Current code already partially implements this (lines 1949-1954 in main.py)
- Need to verify the logic works correctly for all supported browsers
- Ensure fallback to "chrome" if invalid browser is specified

**Files to modify:**
- `app/main.py` (browser selection logic around line 1957)

---

### 2. General user experience and interface refinements
**Status:** Planned  
**Priority:** Medium
**Ideas for future development:**
- Improve layout and spacing for better readability
- Refine color scheme and visual hierarchy

---

### 3. Check data statistics from Streamlit
**Status:** To Do  
**Priority:** Low
**Issue:** Streamlit might use data statistics being a concerned for privacy-focused users.

---

### 4. Download Progress Enhancements
**Status:** Planned  
**Priority:** Medium

**Ideas for future development:**
- Update progress status
- Estimated completion time improvements
- User-friendly error recovery suggestions
- Graceful handling of network timeouts
- Better error messages for common issues

---

### 5. Video Processing Optimizations
**Status:** Idea  
**Priority:** Low

**Ideas for future development:**
- Hardware acceleration support (GPU encoding)
- Advanced audio processing options
- Batch processing capabilities
- Custom processing profiles

---

### 6. Auto-Generated subtitles
**Status:** Idea
**Priority:** Low

**Description:**
Auto-generated subtitles are often very bad in any video player. Using or developing a robust process to generate clean sub directly from an audio from a video would be nice.

---

### 7. Integration Enhancements
**Status:** Idea
**Priority:** Low

**Potential integrations:**
- Webhook notifications for completed downloads
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

**Last Updated:** September 17, 2025  
**Version:** Based on current main branch