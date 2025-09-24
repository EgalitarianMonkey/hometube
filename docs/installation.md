# 📦 Installation Guide

This guide covers all installation methods for HomeTube.

## 🐳 Docker Installation (Recommended)

Docker provides the easiest and most reliable installation method.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) (optional)
- 2GB free disk space
- Internet connection

### Quick Start with Docker

```bash
# Basic run with ephemeral storage
docker run -p 8501:8501 ghcr.io/EgalitarianMonkey/hometube:latest

# Persistent storage (recommended)
docker run -p 8501:8501 \
  -v ./downloads:/data/videos \
  -v ./cookies:/config \
  --name hometube \
  ghcr.io/EgalitarianMonkey/hometube:latest
```

### Docker Compose Setup

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/EgalitarianMonkey/hometube.git
   cd hometube
   ```

2. **Set up configuration**:
   ```bash
   # Copy sample files
   cp docker-compose.yml.sample docker-compose.yml
   cp .env.sample .env
   
   # Edit configurations as needed
   nano docker-compose.yml  # Optional: customize ports, volumes
   nano .env               # Optional: customize paths, settings
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the interface**:
   Open http://localhost:8501 in your browser

### Environment Configuration

Create a `.env` file for custom settings:

```bash
# Network configuration
PORT=8501
TZ=Europe/Paris

# Storage paths
VIDEOS_FOLDER_DOCKER_HOST=./downloads
TMP_DOWNLOAD_FOLDER_DOCKER_HOST=./tmp
YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST=./cookies/youtube_cookies.txt
```

## 💻 Local Installation

For development or systems without Docker.

### Prerequisites

- **Python 3.10+**: [Download from python.org](https://www.python.org/downloads/)
- **FFmpeg**: Required for video processing
- **Package manager**: pip, conda, uv, or poetry

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip ffmpeg
```

#### macOS (with Homebrew)
```bash
brew install python ffmpeg
```

#### Windows
1. Install [Python 3.10+](https://www.python.org/downloads/)
2. Download [FFmpeg](https://ffmpeg.org/download.html) and add to PATH

### Python Environment Setup

Choose your preferred method:

#### Using pip/venv (Standard)
```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -e ".[test]"

# Run tests
make test

# Start application
streamlit run app/main.py
```

#### Using conda
```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# ⚠️ ESSENTIAL: Configure environment
cp .env.sample .env
# Edit .env file to customize settings (see Configuration section below)

# Create conda environment
conda create -n hometube python=3.11
conda activate hometube

# Install dependencies
pip install -e .
pip install -e ".[test]"

# Run tests
make test

# Start application
streamlit run app/main.py
```

#### Using uv
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# ⚠️ ESSENTIAL: Configure environment
cp .env.sample .env
# Edit .env file to customize settings (see Configuration section below)

# Setup environment
uv sync

# Run tests
uv run pytest tests/

# Start application
uv run streamlit run app/main.py
```

#### Using pip/venv (Legacy)
```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# ⚠️ ESSENTIAL: Configure environment
cp .env.sample .env
# Edit .env file to customize settings (see Configuration section below)

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements/requirements-dev.txt

# Start application
streamlit run app/main.py
```

## 🔧 Advanced Installation

### Custom Build from Source

```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Build custom Docker image
docker build -t my-hometube .

# Run custom image
docker run -p 8501:8501 my-hometube
```

### Production Deployment

For production environments, see the [Deployment Guide](deployment.md).

### Development Setup

For contributing to the project, see the [Development Guide](development.md).

## ⚙️ Environment Configuration

### Essential: .env File Setup

The `.env` file is **required** for the application to work properly:

```bash
# Copy the sample configuration
cp .env.sample .env

# Edit with your preferred settings
nano .env  # or code .env, vim .env, etc.
```

### Configuration Options

```bash
# Network & Port
PORT=8501                    # Application port (default: 8501)
TZ=Europe/Paris             # Your timezone

# Storage Paths (Local Installation)
VIDEOS_FOLDER=./downloads    # Where videos are saved
TMP_DOWNLOAD_FOLDER=./tmp    # Temporary processing folder
SUBTITLES_CHOICES=en,fr     # Default subtitle languages
UI_LANGUAGE=en              # Interface language (en/fr)

# Authentication
YOUTUBE_COOKIES_FILE_PATH=./cookies/youtube_cookies.txt
# COOKIES_FROM_BROWSER=brave  # Auto-extract from browser (optional)

# Docker Paths (Docker Installation)
VIDEOS_FOLDER_DOCKER_HOST=./downloads
TMP_DOWNLOAD_FOLDER_DOCKER_HOST=./tmp
YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST=./cookies/youtube_cookies.txt
```

### Common Customizations

**Change download location**:
```bash
# Edit .env file
VIDEOS_FOLDER=/path/to/your/media/library
```

**Add multiple subtitle languages**:
```bash
# Edit .env file
SUBTITLES_CHOICES=en,fr,es,de,it
```

**Change interface language**:
```bash
# Edit .env file
UI_LANGUAGE=fr  # French interface
```

## 🚨 Troubleshooting

### Common Issues

**Application won't start - Missing .env file**:
```bash
# Solution: Copy and configure environment
cp .env.sample .env
```

**FFmpeg not found**:
```bash
# Verify FFmpeg installation
ffmpeg -version

# Ubuntu/Debian: Install via apt
sudo apt install ffmpeg

# macOS: Install via Homebrew
brew install ffmpeg
```

**Permission denied (Docker)**:
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

**Port already in use**:
```bash
# Check what's using port 8501
lsof -i :8501

# Use different port
docker run -p 8502:8501 ghcr.io/EgalitarianMonkey/hometube:latest
```

**Downloads not persistent**:
- Ensure you're using volume mounts: `-v ./downloads:/data/videos`
- Check directory permissions: `chmod 755 ./downloads`

### Performance Optimization

**For faster downloads**:
```bash
# Increase concurrent fragments
export YTDL_CONCURRENT_FRAGMENTS=4

# Use temporary directory on SSD
docker run -v /tmp/downloads:/data/tmp ...
```

**For lower resource usage**:
```bash
# Limit Docker resources
docker run --memory=1g --cpus=1.0 ...
```

## 📋 Verification

After installation, verify everything works:

1. **Access web interface**: http://localhost:8501
2. **Test download**: Try downloading a public YouTube video
3. **Check logs**: `docker logs hometube` (Docker) or console output (local)
4. **Test features**: Try different quality settings, subtitle options

## 🔄 Updates

### Docker Updates
```bash
# Pull latest image
docker pull ghcr.io/EgalitarianMonkey/hometube:latest

# Recreate container
docker-compose up -d --force-recreate
```

### Local Updates
```bash
# Update repository
git pull origin main

# Update dependencies
make dev-setup  # or pip install -r requirements/requirements-dev.txt

# Restart application
```

## 🆘 Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review the [Usage Guide](usage.md) for feature-specific help
3. Check [GitHub Issues](https://github.com/EgalitarianMonkey/hometube/issues)
4. Create a new issue with:
   - Installation method used
   - Error messages
   - System information (OS, Python version, etc.)

---

**Next: [Usage Guide](usage.md)** - Learn how to use all the features