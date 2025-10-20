# 📖 Usage Guide

Complete guide to using the Universal Video Downloader application.

## � Quick Start

1. **Enter URL**: Paste any supported video URL.
2. **Choose Destination**: Pick or create a folder for the download.
3. **Start Download**: Follow progress directly in the web interface.

## 🏆 Quality System & Download Strategies

HomeTube analyses the available video/audio formats for every URL and keeps things simple: it builds **at most two quality profiles** per video.

- **Profile 1** → Best format actually available (highest resolution + modern codecs).
- **Profile 2** → Fallback profile using the next-best format when a download fails or a device is less compatible.

This approach avoids the old 4-profile matrix. The app now focuses on **real formats detected on the video**, so you always download what the platform truly exposes.

### 🔍 How It Works

1. **Scan formats** with yt-dlp to list all video and audio tracks.
2. **Rank** the available codecs (AV1 > VP9 > H.264, Opus > AAC) and resolutions.
3. **Build up to two profiles** that pair the best video/audio combinations available for that video.
4. **Download** using the first profile; if that fails and fallback is allowed, try the second profile.

> Some videos expose only one good combination. In that case the system just uses that single profile.

### 📦 Output Containers

- **MKV** (default): full codec support, ideal for Plex/Jellyfin and archival.
- **MP4**: choose when you need maximum device compatibility; limited to AAC audio.
- **WebM**: only used internally when needed, not recommended as final output.

### 🎯 Download Modes

- **Auto Best (default)** → Tries Profile 1, then Profile 2 if needed. Balanced quality and success rate.
- **Best Only** → Only uses Profile 1. Stops immediately if the best combination is unavailable.
- **Choose Profile** → Lets you force Profile 1 or Profile 2 manually.
- **Choose Formats** → Advanced mode; pick exact yt-dlp format IDs and bypass the profile builder.

### 💡 Choosing a Mode

- Pick **Auto Best** when you just want the best possible quality with automatic fallback.
- Pick **Best Only** when you prefer to fail rather than download a fallback profile.
- Pick **Choose Profile** for deterministic behaviour (e.g. always VP9 fallback).
- Pick **Choose Formats** when you already know the format IDs you want.

### 🛠️ Manual Override (Advanced)

If you want complete control, you can inspect all formats, pick any combination manually, and download without the profile system. This is useful for troubleshooting or niche devices.

---

✅ **Summary**: HomeTube now relies on a **2-profile maximum strategy** driven by real format detection. The default behaviour gives you the best quality available with a single fallback attempt.


## 🌐 Supported Video Sources

This application supports **1800+ video platforms** through yt-dlp integration:

### 🎥 **Major Video Platforms**
- **YouTube** - Individual videos (with SponsorBlock)
- **Vimeo** - Standard and premium videos
- **Dailymotion** - Individual videos
- **Twitch** - VODs, clips, live streams
- **TikTok** - Individual videos, user profiles
- **Facebook** - Videos, reels (authentication required)
- **Instagram** - Videos, stories (authentication may be required)

### 📺 **TV & Streaming**
- **Arte** - European cultural content
- **France TV** - French public television
- **BBC iPlayer** - UK content (geo-restricted)
- **ZDF** - German public television
- **RAI** - Italian public television

### 🎵 **Audio Platforms**
- **SoundCloud** - Individual tracks
- **Bandcamp** - Albums and individual tracks
- **Mixcloud** - DJ sets and radio shows

### 🎮 **Gaming & Tech**
- **Kick** - Live streams and VODs
- **Odysee** - Decentralized video platform
- **PeerTube** - Federated video instances

### 🔗 **Other Sources**
- **Reddit** - Video posts
- **Archive.org** - Historical video content
- **Bitchute** - Alternative video platform
- **And 1790+ more platforms...**

> **💡 Quick Test**: Paste any video URL to check compatibility. Most video sites are supported automatically.

## 🎯 Getting Started

Once installed, access the web interface at:
- **Local**: http://localhost:8501
- **Network**: http://your-server-ip:8501


### 3. File Organization

**Smart Folder Structure**:
```
downloads/
├── Tech/                    # Auto-categorized
│   ├── Python Tutorial.mp4
│   └── Docker Guide.mp4
├── Music/                   # Manual organization
│   └── My Downloads/
└── Documentaries/           # Custom folders
    └── Nature Series/
```

**Naming Options**:
- Keep original video title
- Custom filename with sanitization
- Automatic duplicate handling

## 🔒 Authentication & Private Content

**🚨 Cookies are essential for reliable video downloads**, not just for restricted videos. Modern platforms like YouTube use sophisticated protection mechanisms:

### Why Cookies Are Critical

- **🔐 Encrypted Signatures**: Video streams use encrypted signatures (n-sig) requiring authentication
- **🛡️ Anti-Bot Measures**: Platforms detect and block automated access without proper authentication
- **📺 Stream Protection**: Even public videos may have signature-protected audio/video streams
- **⚡ Error Prevention**: Prevents "signature extraction failed" and "format unavailable" errors

### What You Can Access With Cookies

- **✅ Public Videos**: Reliable access to all quality formats and streams
- **🔓 Restricted Content**: Age-restricted, member-only, and region-locked videos
- **🎵 High-Quality Audio**: Signature-protected audio formats
- **🚀 Better Performance**: Reduced throttling and connection issues

YouTube expects updated cookies and will raise errors when cookies are expired.

There are several methods to setup cookies, depending on your HomeTube service configuration.

### Browser Cookie Method

Browser Cookie Method is recommended on a machine sharing directly a browser like a personal computer.

1. **Select Browser**: Choose from Chrome, Firefox, Safari, Edge, etc.
2. **Login Verification**: Ensure you're logged into YouTube in that browser
3. **Automatic Extraction**: Cookies are extracted securely
4. **Download**: Access age-restricted and private content

**Supported Browsers**:
- Google Chrome / Chromium
- Mozilla Firefox
- Safari (macOS)
- Microsoft Edge
- Opera
- Brave

### Cookie File Method

Cookie File Method is recommended on machines without a browser such as a HomeLab.

1. **Install Extension**: Use [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/ekhagklcjbdpajgpjgmbionohlpdbjgc)
2. **Export Cookies**: Visit YouTube and export cookies
3. **Upload File**: Place in configured cookies directory
4. **Automatic Detection**: Application loads cookies automatically

### Update HomeLab Cookies

For HomeLab setups not having a browser, we want to easily update cookies file. We can do it easily, manually, when it's necessary, from personal computer with :

1. **Extract cookies** on your personal computer using "Get cookies.txt"
2. **Sync on HomeLab** via rsync when necessary
```bash
# From your personal computer, sync cookies to your HomeLab
rsync -avz ~/Downloads/cookies.txt user@homelab-ip:/path/to/hometube/cookies/
```

**With specific permissions:**
```bash
# From your personal computer, sync cookies to your HomeLab with specific remote permissions
rsync -avz --chown=100000:100996 --chmod=ug=rwX,o=r ~/Downloads/cookies.txt user@homelab-ip:/path/to/hometube/cookies/
```

### What Requires Authentication?

- **YouTube**: Age-restricted, private/unlisted, premium content
- **Facebook/Instagram**: Most content requires login
- **Twitch**: Some VODs and subscriber content
- **Platform-specific**: Member-only or geo-restricted content
- **General**: Live streams and premium features

## 🛠️ Technical: How the 2-Profile Builder Works

The quality selector keeps the implementation simple while staying robust:

1. **Collect formats**: yt-dlp returns the exact list of video/audio tracks available for the URL.
2. **Filter noise**: unusable entries (missing codecs, DRM protected, audio-only for video jobs) are ignored.
3. **Score combinations**: resolutions and codecs are ranked so that modern formats win.
4. **Build up to two profiles**:
  - `profile-1` → best score.
  - `profile-2` → next best score (optional, only if clearly different).
5. **Download logic**:
  - Auto Best tries `profile-1`, then `profile-2` if allowed.
  - Best Only tries `profile-1` only.
  - Refuse Downgrade stops after the first failure.

Because the list is derived from a real probe, there is no static matrix to maintain—each download reflects the exact formats exposed by the platform.

## 🎵 Audio & Subtitles

### Subtitle Options

**Download Types**:
- **Embedded**: Burned into video (cannot be disabled)
- **Separate Files**: .srt/.vtt files alongside video
- **Both**: Maximum compatibility

**Language Selection**:
- Automatic detection of available languages
- Multiple subtitle tracks supported
- Auto-generated captions when available
- Manual language override

**Subtitle Sources**:
- Original creator subtitles (highest quality)
- Community contributions
- YouTube auto-generated
- Translated versions

### ⚠️ Auto-Generated Subtitles Limitations

**Important considerations for auto-generated subtitles:**

Auto-generated subtitles have significant limitations that users should be aware of:

- **Poor Formatting**: Auto-generated subtitles often lack proper sentence breaks and punctuation
- **Readability Issues**: Text tends to stick together and chain in an illegible way
- **Display Problems**: Most video players cannot properly format these subtitles for optimal reading
- **YouTube Client Exception**: Only the official YouTube client can display auto-generated subtitles correctly

**Our Approach**:
- We keep the `write-auto-subs` option enabled by default
- **Rationale**: Having imperfect subtitles is better than having no subtitles at all
- **Recommendation**: Use manual or community-contributed subtitles when available for better quality

**Best Practices**:
1. **Check for manual subtitles first** - Look for creator-provided or community subtitles
2. **Use auto-generated as fallback** - Only when no other options are available
3. **Consider post-processing** - You may want to edit auto-generated subtitles for better readability
4. **Test playback** - Verify subtitle quality in your preferred video player

### Audio Processing

**Quality Options**:
- Best available audio quality
- Specific bitrate selection
- Audio-only downloads
- Audio format conversion

## 🚫 SponsorBlock Integration (YouTube)

> **Note**: SponsorBlock is specifically for YouTube videos. Other platforms don't have this feature.

### Automatic Sponsor Detection

**What Gets Detected**:
- Sponsor segments
- Self-promotion
- Interaction reminders (like/subscribe)
- Intro/outro sections
- Music/off-topic segments
- Filler content

### Sponsor Handling Options

**Removal Methods**:
- **Skip**: Remove segments entirely (default)
- **Mark**: Add chapter markers for manual skipping
- **Keep**: Download complete video with timestamps

**Processing Modes**:
- **Aggressive**: Remove all detected segments
- **Conservative**: Only remove clear sponsorships
- **Custom**: Choose specific segment types
- **Disabled**: No sponsor processing

### Manual Review

1. **Preview Segments**: Review detected sponsors before processing
2. **Custom Selection**: Choose which segments to remove
3. **Time Adjustment**: Fine-tune segment boundaries
4. **Save Preferences**: Remember settings for future downloads

## ✂️ Video Cutting & Editing

### Time Range Selection

**Flexible Time Formats**:
```
30          # 30 seconds
1:30        # 1 minute 30 seconds
12:45:30    # 12 hours 45 minutes 30 seconds
2h15m       # 2 hours 15 minutes
90s         # 90 seconds
```

**Selection Methods**:
- Manual time input
- Chapter-based selection
- Sponsor-segment boundaries
- Custom ranges

### Cutting Modes

**Keyframe Mode (Fast)**:
- No re-encoding required
- Instant processing
- May not be frame-accurate
- Preserves original quality

**Precise Mode (Accurate)**:
- Frame-accurate cutting
- Re-encoding required
- Slower processing
- Customizable quality settings

**Batch Cutting**:
- Multiple time ranges
- Automatic segment joining
- Consistent quality settings

### Video Processing Options

**Quality Settings**:
- Maintain original quality
- Custom resolution/bitrate
- Compression level adjustment
- Format conversion

## 📁 Advanced Features

### Custom Output Settings

**File Naming**:
- Template-based naming
- Variable substitution (title, date, quality)
- Sanitization for filesystem compatibility
- Duplicate handling strategies

**Format Options**:
- Video format selection (MP4, WebM, MKV)
- Audio format preference
- Subtitle format choice
- Metadata preservation

### Progress Monitoring

**Real-time Information**:
- Download speed and ETA
- Fragment progress for segmented downloads
- Post-processing status
- Error notifications

**Detailed Logging**:
- Download history
- Error diagnostics
- Performance metrics
- Debug information

## 🏠 HomeLab Integration

### Media Server Compatibility

**Plex Integration**:
- Optimized folder structure
- Metadata preservation
- Automatic library scanning
- Subtitle compatibility

**Jellyfin/Emby Support**:
- Open-source media server compatibility
- Chapter preservation
- Multiple audio tracks
- Thumbnail generation

### Network Access

**Multi-device Usage**:
- Access from any device on your network
- Mobile-friendly interface
- Concurrent downloads
- Shared download queue

**Remote Access**:
- VPN-compatible
- Reverse proxy support
- SSL/HTTPS configuration
- Authentication options

## 🌐 Platform-Specific Tips

### YouTube
- **SponsorBlock**: Full integration for ad/sponsor removal
- **Cookies**: Required for age-restricted and private content
- **Live Streams**: Can download ongoing streams

### Vimeo
- **Quality**: Often provides high-quality originals
- **Privacy**: Respect password-protected videos
- **Embeds**: Can extract from embedded players

### TikTok
- **Watermarks**: May include TikTok watermarks
- **Quality**: Usually mobile-optimized formats
- **Trending**: Popular videos may have higher success rates

### Twitch
- **VODs**: Past broadcasts with chat replay
- **Clips**: Short highlights and moments
- **Authentication**: Required for subscriber-only content

### Facebook/Instagram
- **Authentication**: Most content requires login cookies
- **Stories**: Time-limited content may expire
- **Quality**: Variable based on original upload

### Dailymotion/Vimeo
- **European Content**: Good alternative sources
- **Professional**: Often higher production quality
- **Geo-restrictions**: Some content may be region-locked

> **💡 Testing New Sites**: Try any video URL! The application will automatically detect if the platform is supported.

## ⚙️ Advanced Options

### Custom yt-dlp Arguments

For power users who need specific functionality, HomeTube supports custom yt-dlp arguments through the **Advanced Options** section.

#### 🔧 How to Use

1. **Expand Advanced Options**: Click the expander in the main interface
2. **Enter Arguments**: Add custom yt-dlp arguments in the text field
3. **Apply**: Arguments are automatically applied to all downloads

#### 📝 Common Use Cases

**Network Configuration**:
```bash
--proxy http://your-proxy-server:8080
--proxy socks5://127.0.0.1:1080
```

**File Size Management**:
```bash
--max-filesize 500M
--min-filesize 10M
```

**Download Control**:
```bash
--retries 10
--fragment-retries 10
--retry-sleep 5
```

**Authentication**:
```bash
--cookies /path/to/cookies.txt
--username your_username --password your_password
```

**Output Control**:
```bash
--write-info-json
--write-description
--write-thumbnail
```

**Quality Override**:
```bash
--format-sort "res:720,fps:30"
--max-downloads 5
```

### 🌍 Environment Variables Configuration

HomeTube supports comprehensive environment variable configuration for all its features, including custom yt-dlp arguments and system defaults:

#### 📊 Quality & Download Preferences

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `VIDEO_QUALITY_MAX` | `max` | Maximum video resolution limit | `max`, `2160`, `1440`, `1080`, `720`, `480`, `360` |
| `QUALITY_DOWNGRADE` | `true` | Allow fallback to second-best profile on failure | `true`, `false` |
| `EMBED_CHAPTERS` | `true` | Embed chapters by default | `true`, `false` |  
| `EMBED_SUBTITLES` | `true` | Embed subtitles by default | `true`, `false` |
| `CUTTING_MODE` | `keyframes` | Video cutting precision | `keyframes`, `precise` |

#### 🎵 Audio Language Preferences

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `LANGUAGE_PRIMARY` | `en` | Primary audio language preference | `en`, `fr`, `es`, `de`, `ja`, etc. |
| `LANGUAGES_SECONDARIES` | *(empty)* | Secondary audio languages (comma-separated) | `en,es,de` |
| `LANGUAGE_PRIMARY_INCLUDE_SUBTITLES` | `true` | Include subtitles for primary language | `true`, `false` |
| `VO_FIRST` | `true` | Prioritize original voice (VO) before primary language | `true`, `false` |

#### 🌐 Browser Configuration

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `BROWSER_SELECT` | `chrome` | Default browser for cookies | `chrome`, `firefox`, `edge`, `safari`, `chromium` |

#### 🎯 Core Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DOWNLOAD_FOLDER` | `/data/downloads` | Main download directory | `/home/user/Videos` |
| `TMP_DOWNLOAD_FOLDER` | `/data/tmp` | Temporary processing folder | `/tmp/hometube` |
| `HOMETUBE_LANGUAGE` | `en` | Interface language | `en`, `fr` |
| `YTDLP_CUSTOM_ARGS` | *(empty)* | Default yt-dlp arguments | `--max-filesize 100M` |
| `DEBUG` | `false` | Enable debug mode | `true`, `false` |

#### 🛠️ Custom yt-dlp Arguments

You can set default custom arguments using the `YTDLP_CUSTOM_ARGS` environment variable:

```bash
# In your .env file
YTDLP_CUSTOM_ARGS=--max-filesize 100M --write-info-json
```

**⚠️ Important Notes:**

- **Format Arguments**: Don't override `--format` as it's managed by the quality selector
- **Output Arguments**: Don't override output path arguments
- **Safety**: Invalid arguments will be ignored with error messages
- **Priority**: UI arguments override environment variables

**🔄 Argument Parsing:**

Arguments are parsed safely using shell-style parsing:

- **Quoted Strings**: Use quotes for arguments with spaces: `--user-agent "Custom Agent 1.0"`
- **Multiple Arguments**: Separate with spaces: `--retries 3 --max-filesize 100M`
- **Complex Paths**: Quote paths with spaces: `--cookies "/path with spaces/cookies.txt"`

**📚 yt-dlp Examples:**

*Corporate Network:*

```bash
YTDLP_CUSTOM_ARGS=--proxy http://proxy.company.com:8080 --retries 5
```

*Bandwidth Limited:*

```bash
YTDLP_CUSTOM_ARGS=--limit-rate 1M --max-filesize 50M
```

*Archival Download:*

```bash
YTDLP_CUSTOM_ARGS=--write-info-json --write-description --write-thumbnail --write-sub
```

*Development/Testing:*

```bash
YTDLP_CUSTOM_ARGS=--verbose --print-json --simulate
```

#### 🔧 Usage Examples

**Best Quality Setup**:

```bash
# Maximum quality with fallback allowed
VIDEO_QUALITY_MAX=max
QUALITY_DOWNGRADE=true
EMBED_CHAPTERS=true
EMBED_SUBTITLES=true
CUTTING_MODE=precise
```

**Fast Download Setup**:

```bash
# Quick downloads with 1080p limit
VIDEO_QUALITY_MAX=1080
QUALITY_DOWNGRADE=true
CUTTING_MODE=keyframes
```

**Strict Quality Control**:

```bash
# Best quality only, no fallback
VIDEO_QUALITY_MAX=2160
QUALITY_DOWNGRADE=false
```

#### 📝 Configuration Notes

- **Priority**: UI selections always override environment defaults
- **Auto Selection**: System automatically selects 2 best profiles based on available formats
- **Fallback Behavior**: When `QUALITY_DOWNGRADE=true`, tries Profile 2 if Profile 1 fails
- **Resolution Limit**: `VIDEO_QUALITY_MAX` caps the maximum resolution (e.g., `1080` limits to 1080p even if 4K is available)

## 🔧 Troubleshooting

### Common Issues

**Download Failures**:
- Check internet connection
- Verify URL validity and platform support
- Try different quality settings
- Check authentication status for platform

**Quality Issues**:
- Video quality lower than expected → Check manual format selection
- Audio sync problems → Try different cutting modes
- Large file sizes → Adjust quality settings

**Authentication Problems**:
- Cookies expired → Re-extract browser cookies
- Private video access denied → Verify account permissions
- Age restrictions → Ensure proper authentication

**Performance Issues**:
- Slow downloads → Check network speed and server load
- High CPU usage → Reduce concurrent downloads
- Storage issues → Monitor disk space

### Error Messages

**"No formats available"**:
- Video may be private or deleted
- Try with authentication
- Check URL format

**"FFmpeg not found"**:
- Install FFmpeg system-wide
- Check PATH configuration
- Verify installation

**"Disk space insufficient"**:
- Free up storage space
- Choose lower quality settings
- Use temporary directory on different drive

## 📊 Best Practices

### For Best Quality
- Use manual format selection
- Choose highest bitrate options
- Preserve original audio
- Keep subtitles embedded

### For Storage Efficiency
- Use auto quality selection
- Enable sponsor removal
- Choose efficient codecs (H.264)
- Regular cleanup of downloads

### For Performance
- Limit concurrent downloads
- Use SSD for temporary files
- Close unused browser tabs
- Monitor system resources

### For Organization
- Use consistent folder structure
- Enable automatic categorization
- Set up meaningful naming patterns
- Regular backup of important downloads

---

**Next: [Docker Guide](docker.md)** - Container deployment options