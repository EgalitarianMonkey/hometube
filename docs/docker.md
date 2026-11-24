# Docker Usage

This guide explains how to use the HomeTube Docker image.

## Available Images

The image is available on GitHub Container Registry, under `ghcr.io/EgalitarianMonkey/hometube`:

| Tag | What it points to | Published by |
|-----|-------------------|--------------|
| `latest` | The most recent release | a release, and every yt-dlp refresh |
| `X.Y.Z`, `X.Y`, `X` | A release's exact version, and its minor and major series | a release |
| `yt-dlp-<version>` | The current release rebuilt on that yt-dlp version | the daily yt-dlp refresh |
| `vX.Y.Z-yt-dlp-<version>` | The same rebuild, pinned to both versions | the daily yt-dlp refresh |

**No tag is built from the `main` branch.** A commit merged into `main` reaches the registry when a release is tagged, or when the daily refresh rebuilds `latest` because yt-dlp published a new version. The tags that exist are listed on the [package page](https://github.com/EgalitarianMonkey/hometube/pkgs/container/hometube).

## Quick Usage

### With docker run

```bash
# Basic usage
docker run -p 8501:8501 ghcr.io/EgalitarianMonkey/hometube:latest

# With volumes for download persistence
docker run -p 8501:8501 \
  -v ./downloads:/data/videos \
  -v ./cookies:/config \
  ghcr.io/EgalitarianMonkey/hometube:latest

# With complete configuration
docker run -p 8501:8501 \
  -v ./downloads:/data/videos \
  -v ./tmp:/data/tmp \
  -v ./cookies:/config \
  -e UI_LANGUAGE=en \
  ghcr.io/EgalitarianMonkey/hometube:latest
```

### With docker-compose

**Step 1: Create your environment file**

The sample compose file reads `.env` — both as the container's environment (`env_file`) and for the host paths it binds — so this step comes first:

```bash
cp .env.sample .env

# Set at least VIDEOS_FOLDER_DOCKER_HOST and TMP_DOWNLOAD_FOLDER_DOCKER_HOST
nano .env  # or use your preferred editor
```

**Step 2: Create your configuration**
```bash
# Copy the sample configuration
cp docker-compose.yml.sample docker-compose.yml

# Edit the file to customize your setup
nano docker-compose.yml  # or use your preferred editor
```

**Step 3: Deploy**
```bash
docker-compose up -d
```

**Sample configuration** (`docker-compose.yml.sample`):
```yaml
services:
  hometube:
    image: ghcr.io/egalitarianmonkey/hometube:latest
    container_name: hometube
    env_file: .env
    environment:
      - TZ=${TZ:-America/New_York}
    ports:
      - "${PORT:-8501}:8501"
    volumes:
      - type: bind
        source: ${VIDEOS_FOLDER_DOCKER_HOST:?set VIDEOS_FOLDER_DOCKER_HOST}
        target: /data/videos
      - type: bind
        source: ${TMP_DOWNLOAD_FOLDER_DOCKER_HOST:?set TMP_DOWNLOAD_FOLDER_DOCKER_HOST}
        target: /data/tmp
      - "${YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST}:/config/youtube_cookies.txt"
    restart: unless-stopped
```

## Volumes

| Volume | Description | Required |
|--------|-------------|----------|
| `/data/videos` | Output folder for downloaded videos | Recommended |
| `/data/tmp` | Temporary processing files | Optional |
| `/config` | Cookie files and configuration | Optional |

## Environment Variables

### Core System Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `PORT` | `8501` | Host port the sample compose file publishes, as `"${PORT:-8501}:8501"` |
| `TZ` | `UTC` | Container timezone (e.g., `America/New_York`, `Europe/Paris`) |
| `DEBUG` | `false` | Enable debug logging mode |

**The container always listens on 8501.** `EXPOSE`, the image's health check and the sample compose file all name that port, so publish it on whatever host port you want — `-p 9000:8501`, or `PORT=9000` with the sample compose file — rather than moving the port inside the container. Setting `STREAMLIT_SERVER_PORT` does move the server, and leaves the health check probing 8501, so the container is reported unhealthy for as long as it runs. `STREAMLIT_SERVER_ADDRESS` has the opposite problem: the image's launch command passes `--server.address` itself, and a command-line flag wins over an environment variable, so setting it changes nothing.

### Docker Host Paths

The sample compose file binds three host paths, and the first two are declared with `:?`, which stops `docker compose up` immediately when they are unset:

| Variable | Required | Description |
|----------|----------|-------------|
| `VIDEOS_FOLDER_DOCKER_HOST` | Yes | Host folder bound to `/data/videos` |
| `TMP_DOWNLOAD_FOLDER_DOCKER_HOST` | Yes | Host folder bound to `/data/tmp` |
| `YOUTUBE_COOKIES_FILE_PATH_DOCKER_HOST` | No | Host cookie file bound to `/config/youtube_cookies.txt` |

### Path Configuration

These are the paths *inside* the container, which the volumes above are bound to. Change them only if you also change the volume targets.

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `VIDEOS_FOLDER` | `/data/videos` | Output folder for downloaded videos |
| `TMP_DOWNLOAD_FOLDER` | `/data/tmp` | Temporary processing folder |
| `YOUTUBE_COOKIES_FILE_PATH` | `/config/youtube_cookies.txt` | Authentication cookie file path |

### Quality & Download Preferences

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `VIDEO_QUALITY_MAX` | `max` | Maximum video resolution (`max`, `2160`, `1440`, `1080`, `720`, `480`, `360`) |
| `QUALITY_DOWNGRADE` | `true` | Allow quality downgrade on profile failure |
| `EMBED_CHAPTERS` | `true` | Embed chapters by default |
| `EMBED_SUBTITLES` | `true` | Embed subtitles by default |
| `CUTTING_MODE` | `keyframes` | Video cutting precision (`keyframes`, `precise`) |

The quality profile itself is not an environment variable: it is chosen in the interface, through the "choose a profile" download strategy. `QUALITY_DOWNGRADE` decides which strategy is preselected.

### Audio Language Preferences

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `LANGUAGE_PRIMARY` | `en` | Primary audio language preference |
| `LANGUAGES_SECONDARIES` | *(empty)* | Secondary audio languages (comma-separated) |
| `LANGUAGE_PRIMARY_INCLUDE_SUBTITLES` | `true` | Include subtitles for primary language |
| `VO_FIRST` | `true` | Prioritize original voice (VO) before primary language |

### Localization

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `UI_LANGUAGE` | `en` | Interface language (`en`, `fr`) |

**Note**: Subtitle languages are automatically determined by `LANGUAGE_PRIMARY_INCLUDE_SUBTITLES` and `LANGUAGES_SECONDARIES` settings (see Audio Language Preferences above).

### Advanced Options

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `YTDLP_CUSTOM_ARGS` | *(empty)* | Custom yt-dlp arguments |
| `BROWSER_SELECT` | `chrome` | Default browser for cookie extraction |
| `REMOVE_TMP_FILES_AFTER_DOWNLOAD` | `false` | Remove temporary files after successful download |
| `NEW_DOWNLOAD_WITHOUT_TMP_FILES` | `false` | Clean tmp folder before each new download |

### Media server integration

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `JELLYFIN_BASE_URL` |  | Address of the Jellyfin server to notify, e.g. `https://jellyfin.local:8096` |
| `JELLYFIN_API_KEY` |  | API key allowed to request a library refresh |

## Access

Once the container is started, access the application via:
- http://localhost:8501

## Configuration

### Personal Configuration

The repository includes a sample Docker Compose configuration that you should copy and customize:

```bash
# Copy the sample configuration
cp docker-compose.yml.sample docker-compose.yml

# Edit to match your setup
nano docker-compose.yml
```

💡 **Note**: `docker-compose.yml` is ignored by Git, so you can safely customize it without affecting the repository.

### Configuration Options

You can customize the following in your `docker-compose.yml`:
- **Ports**: Change the exposed port
- **Volumes**: Modify mount paths for your system
- **Environment variables**: Set timezone, server options, etc.
- **Resource limits**: Add CPU/memory constraints

## Security

### For production usage

```bash
# With basic authentication (to be configured in a reverse proxy)
docker run -p 127.0.0.1:8501:8501 \
  -v ./downloads:/data/videos \
  -v ./cookies:/config \
  ghcr.io/EgalitarianMonkey/hometube:latest
```

### Reverse proxy (nginx)

```nginx
server {
    listen 80;
    server_name videos.example.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Updates

```bash
# Stop the container
docker stop hometube

# Remove the old container
docker rm hometube

# Download the new image
docker pull ghcr.io/EgalitarianMonkey/hometube:latest

# Restart with the new image
docker run -p 8501:8501 \
  -v ./downloads:/data/videos \
  -v ./cookies:/config \
  --name hometube \
  ghcr.io/EgalitarianMonkey/hometube:latest
```

## Troubleshooting

### Container logs
```bash
docker logs hometube
```

### Access the container

The image is Alpine-based and ships no `bash`, so use `sh`:

```bash
docker exec -it hometube /bin/sh
```

### Check volumes
```bash
# Check disk space
docker exec hometube df -h

# List downloaded files
docker exec hometube ls -la /data/videos
```

## Local Build

To build the image locally:

```bash
# Clone the repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Build the image
docker build -t hometube:local .

# Run the local image
docker run -p 8501:8501 hometube:local
```
