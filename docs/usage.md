# 📖 Usage Guide

Complete guide to using the Universal Video Downloader application.

## 📺 Basic Video Download

1. **Enter URL**: Paste any video URL from supported platforms
2. **Choose Destination**: Select or create a folder for organization
3. **Click Download**: Monitor progress in real-time

## 🏆 Quality Profiles & Download Modes

HomeTube uses a **professional 4-tier quality matrix** designed specifically for homelab and media server use (Plex, Jellyfin, Emby).  
Instead of relying on the generic `best` option from yt-dlp (which can give unpredictable results), HomeTube applies carefully curated **codec + audio + container combinations** that balance **quality, compatibility, and future-proofing**.

---

### 🏆 Quality Profiles Matrix

| Priority | Profile | Video Codec | Audio Codec | Output Container | Best For |
|----------|---------|-------------|-------------|-----------------|----------|
| **🏆 Ultimate** | AV1 + Opus | AV1 | Opus | **MKV** | Archival quality, desktop playback, Plex/Jellyfin |
| **🥇 Premium** | VP9 + Opus | VP9 | Opus | **MKV** | Excellent fallback, strong compression, wide support |
| **🥈 Compatible** | AV1 + AAC | AV1 | AAC | **MP4** | Mobile devices, smart TVs with modern codec support |
| **🥉 Universal** | H.264 + AAC | H.264 | AAC | **MP4** | Maximum compatibility, older hardware, legacy apps |

---

### 📦 Why These Containers?
- **MKV (Matroska)** → Best default for homelab: robust, supports subtitles, chapters, multiple audio tracks. Fully supported by Plex/Jellyfin.  
- **MP4** → Maximum compatibility: supported everywhere, but limited (no Opus support, AV1 only on recent devices).  
- **WebM** → Used internally by YouTube, but not ideal as final output (limited codec support, metadata handling weaker than MKV/MP4).  

👉 **Default recommendation**:  
Use **MKV** unless you specifically need MP4 for mobile/TV playback.

---

### 📋 Download Modes

#### 🔄 Auto Mode (Recommended)
- Tries each profile in priority order until one succeeds  
- **Smart fallback**: Always ensures the best possible quality available  
- Ideal for **most users and homelab scenarios**

#### 🎯 Forced Mode (Expert)
- Uses **only** the selected profile  
- **No fallback** → if unavailable, download fails  
- Perfect when you need **strict control** (e.g. “only AV1 or nothing”)

#### 🚫 Refuse Quality Downgrade
- Works with Auto **or** Forced mode  
- Stops at the **first failure** instead of downgrading  
- For **quality-first users**: better to fail than accept lower quality

---

### 🎯 How It Works

**Auto Mode Process**  
1. 🔍 Probes available formats on YouTube  
2. 🎯 Filters only the formats relevant to the 4 profiles  
3. 🏆 Attempts profiles in priority order (Ultimate → Universal)  
4. ✅ Stops at the first success  

**Forced Mode Process**  
1. 🎯 Uses the single profile you selected  
2. 🔍 Verifies codecs are available  
3. ⚡ Downloads immediately  
4. ❌ Fails fast if the profile is not available  

---

### 💡 Choosing the Right Mode

- **Use Auto Mode when:**  
  ✅ You want best quality possible  
  ✅ You don’t want to worry about codec details  
  ✅ You’re integrating with Plex/Jellyfin  

- **Use Forced Mode when:**  
  🎯 You require strict codecs (e.g. only AV1 + Opus in MKV)  
  🎯 You’re preparing content for devices with known limitations  

- **Enable “Refuse Quality Downgrade” when:**  
  🚫 Quality > success rate  
  🚫 You prefer failures over lower quality  
  🚫 You want predictable archival files  

---

### 🛠️ Manual Override (Advanced)

For maximum control, you can bypass profiles entirely:

1. 🔍 List all available formats with yt-dlp  
2. 📊 Review codecs, resolutions, file sizes  
3. 🎯 Select exactly the stream combination you want  
4. ⚡ Download directly (no fallback, no remux rules)  

---

✅ **Summary:**  
HomeTube’s profiles are designed to give you the **best balance of quality and compatibility**. By default, you get AV1+Opus in MKV if possible, with intelligent fallbacks ensuring success. Expert users can lock profiles or override formats entirely.


<!-- ### 2. Quality Profiles & Download Modes

HomeTube features a **professional 4-tier quality matrix** that intelligently balances quality, compatibility, and file size.

#### 🏆 Quality Profiles Matrix

| Priority | Profile | Video | Audio | Container | Best For |
|----------|---------|-------|-------|-----------|----------|
| **🏆 Ultimate** | AV1 + Opus | AV1 | Opus | MKV | Desktop viewing, archival quality |
| **🥇 Premium** | VP9 + Opus | VP9 | Opus | MKV | Premium streaming, good device support |
| **🥈 Compatible** | AV1 + AAC | AV1 | AAC | MP4 | Mobile devices, smart TVs |
| **🥉 Universal** | H.264 + AAC | H.264 | AAC | MP4 | Maximum compatibility, older devices |

#### 📋 Download Modes

**🔄 Auto Mode (Recommended)**
- Tries each profile in priority order until one succeeds
- **Smart fallback**: Automatically moves to next profile if current fails
- **Maximum success rate**: Ensures you get the best quality possible
- **Intelligent codec detection**: Only tries profiles with available codecs

**🎯 Forced Mode (Expert)**
- Uses **only** your selected quality profile
- **No fallback**: If the profile fails, download stops
- **Precise control**: Perfect for specific quality requirements
- **Best when**: You know exactly what quality you want

**🚫 Refuse Quality Downgrade**
- Stops at the **first failure** instead of trying lower quality
- Works with both Auto and Forced modes
- **Quality-first approach**: Get the best quality or nothing
- **Useful when**: Storage space isn't a concern, quality is paramount

#### 🎯 How Profile Selection Works

**Auto Mode Process:**
1. 🔍 **Codec Detection**: Probes video to check available formats
2. 🎯 **Profile Filtering**: Only tries profiles with available codecs
3. 🏆 **Quality Priority**: Starts with Ultimate, works down to Universal
4. ✅ **Success**: Stops at first successful download

**Forced Mode Process:**
1. 🎯 **Single Target**: Uses only your selected profile
2. 🔍 **Format Check**: Verifies the profile's codecs are available
3. ⚡ **Direct Attempt**: Downloads immediately, no fallback
4. ❌ **Fail Fast**: Stops if the specific profile fails

#### 💡 Choosing the Right Mode

**Use Auto Mode When:**
- You want the best quality possible ✅
- Download reliability is important ✅  
- You're not sure about codec availability ✅
- **Most common scenario** ✅

**Use Forced Mode When:**
- You need a specific codec/container combination 🎯
- File size constraints require exact format 🎯
- You're batch downloading with consistent requirements 🎯
- You're an expert user with specific needs 🎯

**Enable "Refuse Quality Downgrade" When:**
- Quality is more important than success rate 🚫
- You prefer failed downloads over lower quality 🚫
- Storage limitations require high-quality files only 🚫

#### 🛠️ Manual Format Override

For ultimate control, you can override the profile system entirely:

1. **🔍 Detect Formats**: Click to probe all available video formats
2. **📊 Review Options**: See quality, codec, file size estimates
3. **🎯 Select Format**: Choose your preferred format manually
4. **⚡ Download**: Uses your exact selection, bypasses profile system -->


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

## 🛠️ Technical: How Profile System Works

### Advanced Profile Architecture

HomeTube uses a **professional 4-tier matrix** with intelligent codec detection and systematic fallback:

#### 🔍 Profile Detection Process

**1. Codec Availability Probing**
```
🔍 Step 1: Probe video for available codecs
   → Check AV1, VP9, H.264 video availability
   → Check Opus, AAC audio availability
   → Filter profiles to only viable combinations
```

**2. Profile Priority Ordering**
```
🏆 Priority 1: MKV – AV1 + Opus (Ultimate Quality)
🥇 Priority 2: MKV – VP9 + Opus (Premium Fallback)  
🥈 Priority 3: MP4 – AV1 + AAC (Mobile Compatible)
🥉 Priority 4: MP4 – H.264 + AAC (Universal)
```

#### 🔄 Auto Mode Execution

**Multi-Layer Fallback System**:
```
For each viable profile (in priority order):
  For each YouTube client (default, android, ios, web):
    If cookies available:
      → Try profile + client + cookies
    → Try profile + client (no auth)
    → If SUCCESS: Complete download and stop
    → If FAILED: Continue to next client
  → If all clients failed: Try next profile
```

#### 🎯 Forced Mode Execution

**Direct Profile Targeting**:
```
🎯 Single Profile Mode:
  1. Verify target profile codecs are available
  2. Use only the specified profile
  3. Try all clients (default → android → ios → web)
  4. SUCCESS or FAIL (no fallback to other profiles)
```

#### 🚫 Refuse Quality Downgrade

**Quality-First Approach**:
```
🚫 Enhanced Strict Mode:
  → Try first available profile (highest quality)
  → If FAILED: Stop immediately, no lower quality attempts
  → Works with both Auto and Forced modes
  → Ensures maximum quality or no download
```

#### 💡 Key Technical Benefits

**Smart Resource Management**:
- **Codec Detection**: Only tries profiles with available formats
- **Efficient Fallback**: Systematic testing, stops on first success
- **Flexible Authentication**: Cookies first, graceful fallback without

**Professional Quality Control**:
- **Container Optimization**: MKV for quality, MP4 for compatibility
- **Codec Selection**: Next-gen (AV1/VP9) prioritized over legacy (H.264)
- **Audio Quality**: Opus (superior) preferred over AAC (compatible)

**Example Auto Mode Flow**:
```
🔍 Probing video formats...
✅ Available: AV1, VP9, H.264, Opus, AAC

🏆 Profile 1: MKV AV1+Opus
   🍪 default+cookies → ❌ Failed
   🚀 default (no auth) → ❌ Failed
   🍪 android+cookies → ✅ SUCCESS!
   
✅ Download complete: Ultimate quality achieved
```

**Example Forced Mode Flow**:
```
🎯 Forced Mode: MP4 H.264+AAC selected
🔍 Verifying H.264 and AAC availability... ✅
🎯 Single profile mode: No fallback allowed

🥉 Profile: MP4 H.264+AAC
   🍪 default+cookies → ❌ Failed
   🍪 android+cookies → ✅ SUCCESS!
   
✅ Download complete: Exact profile delivered
```

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
| `DEFAULT_DOWNLOAD_MODE` | `auto` | Download strategy | `auto`, `forced` |
| `DEFAULT_QUALITY_PROFILE` | *(empty)* | Default quality profile | `mkv_av1_opus`, `mkv_vp9_opus`, `mp4_av1_aac`, `mp4_h264_aac` |
| `VIDEO_QUALITY_MAX` | `max` | Maximum video resolution limit | `max`, `2160`, `1440`, `1080`, `720`, `480`, `360` |
| `DEFAULT_REFUSE_QUALITY_DOWNGRADE` | `false` | Stop at first failure | `true`, `false` |
| `DEFAULT_EMBED_CHAPTERS` | `true` | Embed chapters by default | `true`, `false` |  
| `DEFAULT_EMBED_SUBS` | `true` | Embed subtitles by default | `true`, `false` |
| `DEFAULT_CUTTING_MODE` | `keyframes` | Video cutting precision | `keyframes`, `precise` |

#### 🌐 Browser Configuration

| Variable | Default | Description | Options |
|----------|---------|-------------|---------|
| `DEFAULT_BROWSER_SELECT` | `chrome` | Default browser for cookies | `chrome`, `firefox`, `edge`, `safari`, `chromium` |

#### 🎯 Core Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DOWNLOAD_FOLDER` | `/data/downloads` | Main download directory | `/home/user/Videos` |
| `TMP_DOWNLOAD_FOLDER` | `/data/tmp` | Temporary processing folder | `/tmp/hometube` |
| `HOMETUBE_LANGUAGE` | `en` | Interface language | `en`, `fr` |
| `YTDLP_CUSTOM_ARGS` | *(empty)* | Default yt-dlp arguments | `--max-filesize 100M` |

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

#### �🔧 Usage Examples

**Batch Processing Setup**:

```bash
# High-quality archival configuration
DEFAULT_DOWNLOAD_MODE=auto
DEFAULT_QUALITY_PROFILE=mkv_av1_opus
VIDEO_QUALITY_MAX=max
DEFAULT_REFUSE_QUALITY_DOWNGRADE=false
DEFAULT_EMBED_CHAPTERS=true
DEFAULT_EMBED_SUBS=true
DEFAULT_CUTTING_MODE=precise
```

**Fast Download Setup**:

```bash
# Quick downloads with fallbacks
DEFAULT_DOWNLOAD_MODE=auto
DEFAULT_QUALITY_PROFILE=mp4_h264_aac
VIDEO_QUALITY_MAX=1080
DEFAULT_REFUSE_QUALITY_DOWNGRADE=false
DEFAULT_CUTTING_MODE=keyframes
```

**Strict Quality Control**:

```bash
# No quality compromises
DEFAULT_DOWNLOAD_MODE=forced
DEFAULT_QUALITY_PROFILE=mkv_av1_opus
VIDEO_QUALITY_MAX=2160
DEFAULT_REFUSE_QUALITY_DOWNGRADE=true
```

#### 📝 Configuration Notes

- **Priority**: UI selections always override environment defaults
- **Profile Selection**: Empty `DEFAULT_QUALITY_PROFILE` enables automatic selection
- **Mode Impact**: `auto` mode tries all profiles, `forced` uses only the specified profile
- **Fallback Behavior**: `DEFAULT_REFUSE_QUALITY_DOWNGRADE=false` allows trying lower quality profiles
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