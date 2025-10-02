<div align="center">

<br/>

# 🎬 HomeTube

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.49+-red.svg)](https://streamlit.io)
[![Latest Release](https://img.shields.io/github/v/release/EgalitarianMonkey/hometube)](https://github.com/EgalitarianMonkey/hometube/releases)
[![Docker Image](https://ghcr-badge.egpl.dev/egalitarianmonkey/hometube/latest_tag?trim=major&label=Docker)](https://github.com/EgalitarianMonkey/hometube/pkgs/container/hometube)
[![License](https://img.shields.io/badge/License-AGPL--3.0-green.svg)](LICENSE)

<br/>

**🌐 Universal Video Downloader for your HomeLab**

*Download, process and organize videos at Home*

<br/>

</div>

<br/>
<br/>

<!-- --- -->

<!-- ## 🎯 What is HomeTube? -->


🎬 HomeTube is a simple web UI for downloading single videos from the internet with the highest quality available and moving them to specific local locations automatically managed and integrated by media server such as Plex or Jellyfin.

A simple friendly solution for easily integrating preferred videos from Youtube and others platforms to local media server.

## 🏠 **HomeLab Integration**

- **🎬 Media server Ready**: Download best quality videos with explicit name and location directly in your HomeLab media server structure and get automatic watch experience on Plex, Jellyfin, Emby or even on your PC
- **📱 Network Access**: Web interface videos download accessible from any device on your network

## ⚡ **Features**

- **🎯 One-Click Downloads**: Paste URL → Get perfectly organized video
- **🚫 Ad-Free Content**: Block videos' sponsors and ads
- **🎬 Advanced Processing**: Cut clips, embed subtitles, convert formats
- **⚙️ Advanced configurations**: Set any custom yt-dlp arguments (proxy, max-filesize, etc.)
- **🔐 Cookies Authentication**: Essential for reliable downloads - unlocks restricted content and prevents signature errors
- **📊 Quality Control**: Auto-select best quality or manual override
- **🎥 Video Sources**: **YouTube**, Reddit, Vimeo, Dailymotion, TikTok, Twitch, Facebook, Instagra, etc. [See complete list (1800+)](docs/supported-platforms.md)

<!-- ## ⚡ Technical Highlights

<div align="center">

| 🎯 **Easy to Use** | 🔧 **Powerful** | 🏠 **HomeLab Ready** |
|:---:|:---:|:---:|
| Web interface | 1800+ platforms | Docker deployment |
| One-click downloads | Advanced processing | Network accessible |
| Auto-organization | Cookie authentication | Plex/Jellyfin ready |

</div> -->

<!-- --- -->

<br/>
<br/>

![Application Demo](./docs/images/simple_ui_demo.gif)

<br/>
<br/>

<!-- --- -->

## 🛠️ HomeTube Options

### 🏠 HomeLab Integration

**Automatic integration with self-hosted setup**:

- **🐳 Docker Ready**: One-command deployment with Docker Compose
- **🎬 Media Server Integration**: Direct integration with media server thanks to well named video files automatically moved to chosen locations watched by media server such as Plex, Jellyfin, or Emby.
- **🆕 Create new folder from the UI**: Create organized new folder structures when necessary from the "🆕 Create New Folder" option at the bottom of the "Destination folder" field listing menu (e.g., `Tech/Python/Advanced`)
- **📱 Network Access**: Web interface accessible from any device on your network
- **🔐 Secure**: No cloud dependencies, everything runs locally
- **⚙️ Configurable**: Extensive customization through environment variables

[Setup your HomeLab integration](docs/deployment.md).

### 🚫 Block all ads and sponsors

**Automatically skip sponsors, ads, and promotional content** with built-in SponsorBlock support. Just download your video and sponsors segments are automatically detected and marked.

- ✅ **Auto-detection**: Sponsors segments automatically identified
- ✅ **Manage sponsors to block**: Sponsors segments to block or mark can be managed in the UI
- ✅ **Community-driven**: Powered by SponsorBlock's crowd-sourced database
- ✅ **Zero configuration**: Works out of the box for YouTube videos

[Learn more about SponsorBlock features](docs/usage.md#-sponsorblock-integration).

### 🍪 Cookies Authentication (Highly Recommended)

**Cookies authentication should be setup** for optimal video downloading experience and to avoid common download failures.

#### 🚨 **Why Cookies Are Essential**

**Even for public videos**, cookies are often required due to modern platform protections:

- **🔐 Encrypted Signatures**: Video streams use encrypted signatures (n-sig) that require authentication
- **🛡️ Anti-Bot Protection**: Platforms implement sophisticated anti-automation measures
- **📺 Stream Access**: Audio/video streams may be signature-protected even for public content
- **⚡ Download Reliability**: Prevents common "signature extraction" and "format unavailable" errors

#### 🎯 **What Cookies Unlock**

- **🔓 Private Content**: Age-restricted, member-only, and region-locked videos
- **✅ Public Videos**: Reliable access to all quality formats and streams
- **🎵 Audio Streams**: High-quality audio formats that may be signature-protected
- **🚀 Better Performance**: Reduced throttling and connection issues

#### 🛠️ **Setup Options**

We can use **Browser cookies** if on a machine sharing a browser, otherwise **Cookies File** in HomeLab setup.

[More details about Cookies authentication setup](docs/usage.md#-authentication--private-content).

### ✂️ Advanced Video Processing

Transform your downloads with **powerful built-in video processing tools**:

- **🎬 Clip Extraction**: Cut specific segments from videos with precision timing
- **📝 Subtitle Embedding**: Automatically embed subtitles in multiple languages
- **🔄 Format Conversion**: Convert between video formats (MP4, MKV, WebM, etc.)
- **🎵 Audio Extraction**: Extract audio-only versions in high quality
- **📱 Mobile Optimization**: Optimize videos for mobile devices

[Explore all processing options](docs/usage.md#-video-processing).

### 🔧 Advanced configurations

Custom yt-dlp arguments support offers **full flexibility** for advanced users to tailor downloads to specific needs.

- **📱 Network configuration**: `--proxy http://proxy.company.com:8080 --retries 5`
- **📂 File size limits**: `--max-filesize 500M --min-filesize 100M`
- **📋 Enhanced metadata**: `--write-info-json --write-description --write-thumbnail`
- **🛜 Bandwidth control**: `--limit-rate 1M --fragment-retries 10`
- **➕ More options**: `yt-dlp --options variable`

Custom yt-dlp arguments can be added directly from the UI or set by default for any download with the `YTDLP_CUSTOM_ARGS` environment variable.

**🔀 Smart Conflict Resolution**: HomeTube automatically detects and resolves conflicts between base settings and custom arguments, giving priority to your custom preferences while maintaining system stability.

### 🎯 Smart Quality Profiles System

**Professional 4-tier quality matrix** with intelligent fallback:

- **🏆 MKV – AV1 + Opus**: Ultimate quality with next-gen codecs
- **🥇 MKV – VP9 + Opus**: Premium fallback with excellent compression
- **🥈 MP4 – AV1 + AAC**: Mobile/TV compatible with modern video codec
- **🥉 MP4 – H.264 + AAC**: Maximum compatibility, works everywhere

**🔄 Auto Mode (Recommended)**: Tries each profile until one succeeds  
**🎯 Forced Mode**: Uses only your selected profile, no fallback  
**🚫 Refuse Quality Downgrade**: Stop at first failure instead of trying lower quality

[Learn more about quality strategies](docs/usage.md#-quality-profiles--download-modes).

### 🎯 Smart Download Management

**Intelligent download system** that adapts to your needs:

- **📁 Auto-Organization**: Videos organized by channel/creator automatically
- **⚡ Resume Support**: Interrupted downloads automatically resume
- **💾 Storage Optimization**: Duplicate detection and space management

[Learn more about download features](docs/usage.md#-basic-video-download).

### 🌐 Universal Platform Support

**1800+ supported platforms** - way beyond just YouTube:

- **📺 Major Platforms**: YouTube, Twitch, Vimeo, Dailymotion, TikTok
- **🎭 Social Media**: Instagram, Facebook, Twitter, Reddit
- **🎓 Educational**: Coursera, Khan Academy, edX
- **🏢 Professional**: LinkedIn Learning, Udemy, Skillshare
- **📺 Streaming**: Netflix previews, Hulu trailers, Disney+ clips

[See complete platform list](docs/supported-platforms.md).

<br/><br/>
![Application Demo](./docs/images/options_ui_demo.gif)
<br/><br/>

## 🚀 Quick Start

### ⚙️ Essential Configuration

**📋 HomeTube uses environment variables for all configurations**: videos download paths, temporary download folder, authentication, languages, subtitles, and more.

Depending of the setup, Docker, Docker compose, Portainer, local run, environment variables can be passed to the application in different ways.

**`.env` file from `.env.sample` can be practical for rapid setup:**

```bash
# 1. Clone repository (if not already done)
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# 2. Create your own configuration file from the sample
cp .env.sample .env
```

### 🐳 Docker

With Docker, environment variables can be passed either with `-e VARIABLE=` arguments or `--env-file .env`.

**`-e VARIABLE=`**

```bash
docker run -p 8501:8501 \
  -e TZ=America/New_York \
  -e VIDEOS_FOLDER=/data/videos \
  -e TMP_DOWNLOAD_FOLDER=/data/tmp \
  -e YOUTUBE_COOKIES_FILE_PATH=/config/youtube_cookies.txt \
  -v <VIDEOS_FOLDER_DOCKER_HOST>:/data/videos \
  -v <TMP_DOWNLOAD_FOLDER_DOCKER_HOST>:/data/tmp \
  -v <YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST>:/config \
  ghcr.io/egalitarianmonkey/hometube:latest
```

**`--env-file .env`**

```bash
docker run -p 8501:8501 \
  --env-file .env \
  -v <VIDEOS_FOLDER_DOCKER_HOST>:/data/videos \
  -v <TMP_DOWNLOAD_FOLDER_DOCKER_HOST>:/data/tmp \
  -v <YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST>:/config \
  ghcr.io/egalitarianmonkey/hometube:latest
```

**Access at <http://localhost:8501>**

### 🐳 Docker Compose

With Docker compose, environment variables can be passed either with the `environment:` entry or from the convenient `.env` file with `env_file: .env`.

#### Configuration with `.env` file

**`.env`**

```bash
# --- PORT ---
PORT=8510

# --- Timezone ---
TZ=America/New_York

# --- Languages ---
UI_LANGUAGE=en
SUBTITLES_CHOICES=en

# --- Docker host paths ---
# Docker environment variables to specify depending on your homelab setup.
VIDEOS_FOLDER_DOCKER_HOST=/mnt/data/videos
TMP_DOWNLOAD_FOLDER_DOCKER_HOST=/mnt/data/hometube/tmp
YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST=/opt/cookies/youtube.txt

# --- Paths ---
# Internal Docker container paths (do not change)
VIDEOS_FOLDER=/data/videos
TMP_DOWNLOAD_FOLDER=/data/tmp
YOUTUBE_COOKIES_FILE_PATH=/config/youtube_cookies.txt
#COOKIES_FROM_BROWSER=brave # Not working natively in Docker
```

**docker-compose.yml**

```yaml
services:
  hometube:
    image: ghcr.io/egalitarianmonkey/hometube:latest
    env_file: .env
    volumes:
      - type: bind
        source: ${VIDEOS_FOLDER_DOCKER_HOST:?set VIDEOS_FOLDER_DOCKER_HOST}
        target: /data/videos
      - type: bind
        source: ${TMP_DOWNLOAD_FOLDER_DOCKER_HOST:?set TMP_DOWNLOAD_FOLDER_DOCKER_HOST}
        target: /data/tmp
      - "${YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST}:/config/youtube_cookies.txt"
```

This **long volume structure** with `type:`, `source:`, and `target:` entries forces the environment variables to be set, otherwise the Docker deployment fails. This avoids silent failures and confusions when environment variables are missing.

#### Configuration with `environment:`:

**docker-compose.yml**

```yaml
services:
  hometube:
    image: ghcr.io/egalitarianmonkey/hometube:latest
    environment:
      UI_LANGUAGE: en
      SUBTITLES_CHOICES: en
      VIDEOS_FOLDER: /data/videos
      TMP_DOWNLOAD_FOLDER: /data/tmp
      YOUTUBE_COOKIES_FILE_PATH: /config/youtube_cookies.txt
    volumes:
      - type: bind
        source: ${VIDEOS_FOLDER_DOCKER_HOST:?set VIDEOS_FOLDER_DOCKER_HOST}
        target: /data/videos
      - type: bind
        source: ${TMP_DOWNLOAD_FOLDER_DOCKER_HOST:?set TMP_DOWNLOAD_FOLDER_DOCKER_HOST}
        target: /data/tmp
      - "${YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST}:/config/youtube_cookies.txt"
```

This **long volume structure** with `type:`, `source:`, and `target:` entries forces the environment variables to be set, otherwise the Docker deployment fails. This avoids silent failures and confusions when environment variables are missing.

**Access at <http://localhost:8501>**

### 🐳 Portainer

With Portainer, environment variables must be explicitly written in the `environment:` section of the container setup to get those environment variables in the app.

**Portainer environment variables management is different than Docker Compose as:**

- It does not support `env_file:` entry for passing environment variables **in the container** from a `.env` file involving that the environment variables must be explicitly written in the `environment:` section of the container setup to get those environment variables in the app.
- It does not retrieve any Docker environment variables from a `.env` file as the stack isn't linked to any location. Environment variables for the Portainer docker-compose.yml stack must be **manually** entered from the UI either one by one or with a convenient `.env` upload.

**docker-compose.yml**

```yaml
services:
  hometube:
    image: ghcr.io/egalitarianmonkey/hometube:latest
    environment:
      UI_LANGUAGE: en
      SUBTITLES_CHOICES: en
      VIDEOS_FOLDER: /data/videos
      TMP_DOWNLOAD_FOLDER: /data/tmp
      YOUTUBE_COOKIES_FILE_PATH: /config/youtube_cookies.txt
    volumes:
      - type: bind
        source: ${VIDEOS_FOLDER_DOCKER_HOST:?set VIDEOS_FOLDER_DOCKER_HOST}
        target: /data/videos
      - type: bind
        source: ${TMP_DOWNLOAD_FOLDER_DOCKER_HOST:?set TMP_DOWNLOAD_FOLDER_DOCKER_HOST}
        target: /data/tmp
      - "${YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST}:/config/youtube_cookies.txt"
```

This **long volume structure** with `type:`, `source:`, and `target:` entries forces the environment variables to be set, otherwise the Docker deployment fails. This avoids silent failures and confusions when environment variables are missing.

**Portainer environment variables in the UI**

```bash
VIDEOS_FOLDER_DOCKER_HOST: /mnt/data/videos
TMP_DOWNLOAD_FOLDER_DOCKER_HOST: /mnt/data/hometube/tmp
YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST: /opt/cookies/youtube.txt
```

### 🏠 Local Installation

**Environment variables for local run are setup following a specific order:**

- First, defined and **exported** environment variables from the current shell will be taken (`export VIDEOS_DIR=/data/videos`, `set -a && source .env && set +a`, etc.)
- Then, if a `.env` file exists, not defined environment variables from exported shell will be taken from local `.env` file
- At last, default values will be used for not defined environment variables from **shell** and `.env` file

**Prerequisites** are installed through python environment setup. Below are setups for `venv`, `conda`, or `uv`.

**Option 1: Using pip (Recommended)**

```bash
# Create virtual environment
python -m venv hometube-env
source hometube-env/bin/activate  # On Windows: hometube-env\Scripts\activate

# Install dependencies including yt-dlp
pip install ".[local]"

# Run the application
streamlit run app/main.py
# OR
python run.py
```

**Option 2: Using conda**

```bash
# Create conda environment
conda create -n hometube python=3.10
conda activate hometube

# Install dependencies including yt-dlp
pip install ".[local]"

# Run the application
streamlit run app/main.py
```

**Option 3: Using uv (Fastest)**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies including yt-dlp
uv pip install ".[local]"

# Run with uv
uv run streamlit run app/main.py
```

**Access at**: <http://localhost:8501>

## ⚙️ Configuration Guide

### 🔧 Environment Variables

HomeTube configuration is managed through the `.env` file:

| Variable | Purpose | Defaults | Examples |
|---------|---------|---------|---------|
| `UI_LANGUAGE` | UI language. English (en) and French (fr) supported | `en` | `en,fr` |
| `SUBTITLES_CHOICES` | Subtitles' languages proposals | `en` | `en,fr,es` |
| `VIDEOS_FOLDER` | Where videos will be moved at the end of download | `/data/videos` if in Docker container else `./downloads` | `/data/videos` |
| `TMP_DOWNLOAD_FOLDER` | Temporary download location | `/data/tmp` if in Docker container else `./tmp` | `/data/tmp` |
| `YOUTUBE_COOKIES_FILE_PATH` | Authentication for private videos | **Must be defined** (or `COOKIES_FROM_BROWSER`) | `/config/youtube_cookies.txt` |
| `COOKIES_FROM_BROWSER` | Cookies auth directly from active local browser |  | `chrome,firefox,brave,chromium,edge,opera,safari,vivaldi,whale` |
| `YTDLP_CUSTOM_ARGS` | Custom yt-dlp arguments |  | `--max-filesize 5M --write-info-json` |
| `TZ` | Timezone for Docker | `America/New_York` | `Europe/Paris` |
| `PORT` | Web interface port | `8501` | `8501` |
| `DEBUG` | Debug logging mode | `false` | `true` |
| `VIDEOS_FOLDER_DOCKER_HOST` | Host videos folder in Docker context | **Must be defined** | `/mnt/data/videos` if in Docker container else `/downloads` |
| `TMP_DOWNLOAD_FOLDER_DOCKER_HOST` | Host tmp download videos folder in Docker context | **Must be defined** | `/mnt/data/hometube/tmp` if in Docker container else `./tmp` |
| `YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST` | Youtube cookies file path in Docker context | **Must be defined** | `/opt/cookies/youtube.txt` if in Docker container else `./cookies/youtube_cookies.txt` |

### 🔄 Configuration Validation

Check your setup with this command:

```bash
DEBUG=1 python -c "import app.main" 2>/dev/null
```

**Expected output:**
```
🔧 HomeTube Configuration Summary:
📁 Videos folder: downloads
📁 Temp folder: tmp
✅ Videos folder is ready: downloads
🍪 Cookies file: ./cookies/youtube_cookies.txt
🔤 Subtitle languages: en, fr
✅ Configuration file: .env
```

---

## 📚 Documentation

**📋 Complete Documentation Hub: [docs/README.md](docs/README.md)**

### Core Guides
- **[Installation Guide](docs/installation.md)** - System setup and requirements
- **[Usage Guide](docs/usage.md)** - Complete feature walkthrough
- **[Docker Guide](docs/docker.md)** - Container deployment strategies

### Development & Operations
- **[Development Setup](docs/development-setup.md)** - Multi-environment development guide
- **[UV Workflow Guide](docs/uv-workflow.md)** - Modern dependency management
- **[Testing Documentation](docs/testing.md)** - Test framework and guidelines
- **[Deployment Guide](docs/deployment.md)** - Production deployment strategies

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.10+, yt-dlp, FFmpeg | Core processing |
| **Frontend** | Streamlit | Web interface |
| **Container** | 🐳 jauderho/yt-dlp (Alpine + yt-dlp + FFmpeg) | Optimized deployment |
| **CI/CD** | GitHub Actions | Automation |
| **Testing** | pytest, coverage | Quality assurance |
| **Dependencies** | UV, conda, pip | Package management |

## 📊 System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Python** | 3.10+ | 3.11+ |
| **FFmpeg** | Latest | Latest |
| **Storage** | 2GB free | 10GB+ |
| **Memory** | 512MB | 2GB |
| **Network** | Broadband | High-speed |

## 📈 Project Status

- ✅ **Stable**: Core functionality tested and reliable
- 🔄 **Active Development**: Regular updates and improvements
- 🧪 **Test Coverage**: 84% on testable modules ([details](docs/testing.md))
- 📦 **Production Ready**: Docker images available on GHCR
- 🏠 **HomeLab Optimized**: Designed for self-hosted environments

## 📆 Coming Features

Check out the roadmap for upcoming features and enhancements:

**📋 See the complete roadmap**: [docs/todo.md](docs/todo.md)

---

## 🤝 Contributing & Development

**For developers and contributors**, comprehensive guides are available:

📖 **[Development Setup Guide](docs/development-setup.md)** - Environment setup  
🔄 **[Contributing Guidelines](docs/development.md)** - Workflow and best practices

**Quick Setup Options:**
- **Conda** (recommended for contributors)
- **UV** (fastest for developers) 
- **pip/venv** (universal)

**Includes:** Testing commands, workflows, code standards, and pull request process.

---

## ☕ Support This Project

If you find HomeTube useful, consider supporting the project to help with development costs.

<div align="center">
<a href="https://buymeacoffee.com/egalitarianmonkey" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-orange.png" 
       alt="Buy Me A Coffee" 
       height="35" />
</a>
</div>

<div align="center">

Every contribution is appreciated! 🙏
</div>

## 📄 License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Universal video downloader supporting 1800+ platforms
- **[Streamlit](https://streamlit.io/)** - Excellent web app framework  
- **[SponsorBlock](https://sponsor.ajay.app/)** - Community-driven sponsor detection (YouTube)
- **[FFmpeg](https://ffmpeg.org/)** - Multimedia processing framework

---

<div align="center">

**⭐ If you find this project useful, please consider starring it!**

[⭐ Star on GitHub](https://github.com/EgalitarianMonkey/hometube) • [📖 Documentation](docs/README.md) • [🐳 Docker Hub](https://github.com/EgalitarianMonkey/hometube/pkgs/container/hometube) • [☕ Buy Me a Coffee](https://buymeacoffee.com/egalitarianmonkey)

</div>