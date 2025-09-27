# 📖 Usage Guide

Complete guide to using the Universal Video Downloader application.

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

## 📺 Basic Video Download

### 1. Simple Download

1. **Enter URL**: Paste any video URL from supported platforms
2. **Choose Destination**: Select or create a folder for organization
3. **Click Download**: Monitor progress in real-time

### 2. Quality Selection

**Auto Mode (Default)**:
- Automatically selects best available quality
- Balances file size and quality
- Recommended for most users

**Manual Mode**:
1. Click **"Detect Formats"** to see all available options
2. Review quality, codec, and estimated file size
3. Select your preferred format
4. Download with chosen settings

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

### What Requires Authentication?

- **YouTube**: Age-restricted, private/unlisted, premium content
- **Facebook/Instagram**: Most content requires login
- **Twitch**: Some VODs and subscriber content
- **Platform-specific**: Member-only or geo-restricted content
- **General**: Live streams and premium features

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

#### 🌍 Environment Variables

You can also set default custom arguments using environment variables:

```bash
# In your .env file
YTDLP_CUSTOM_ARGS=--max-filesize 100M --write-info-json
```

#### ⚠️ Important Notes

- **Format Arguments**: Don't override `--format` as it's managed by the quality selector
- **Output Arguments**: Don't override output path arguments 
- **Safety**: Invalid arguments will be ignored with error messages
- **Priority**: UI arguments override environment variables

#### 🔄 Argument Parsing

Arguments are parsed safely using shell-style parsing:
- **Quoted Strings**: Use quotes for arguments with spaces: `--user-agent "Custom Agent 1.0"`
- **Multiple Arguments**: Separate with spaces: `--retries 3 --max-filesize 100M`
- **Complex Paths**: Quote paths with spaces: `--cookies "/path with spaces/cookies.txt"`

#### 📚 Examples

**Corporate Network**:
```bash
--proxy http://proxy.company.com:8080 --retries 5
```

**Bandwidth Limited**:
```bash
--limit-rate 1M --max-filesize 50M
```

**Archival Download**:
```bash
--write-info-json --write-description --write-thumbnail --write-sub
```

**Development/Testing**:
```bash
--verbose --print-json --simulate
```

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