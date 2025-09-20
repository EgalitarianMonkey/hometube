# Docker Usage

This guide explains how to use the HomeTube Docker image.

## Available Images

The image is available on GitHub Container Registry:
- `ghcr.io/EgalitarianMonkey/hometube:latest` - Stable version (main branch)
- `ghcr.io/EgalitarianMonkey/hometube:v1.0.0` - Specific tagged version
- `ghcr.io/EgalitarianMonkey/hometube:main` - Development version

## Quick Usage

### With docker run

```bash
# Basic usage
docker run -p 8501:8501 ghcr.io/EgalitarianMonkey/hometube:latest

# With volumes for download persistence
docker run -p 8501:8501 \
  -v ./downloads:/data/Videos \
  -v ./cookies:/config \
  ghcr.io/EgalitarianMonkey/hometube:latest

# With complete configuration
docker run -p 8501:8501 \
  -v ./downloads:/data/Videos \
  -v ./tmp:/data/tmp \
  -v ./cookies:/config \
  -e STREAMLIT_SERVER_PORT=8501 \
  ghcr.io/EgalitarianMonkey/hometube:latest
```

### With docker-compose

**Step 1: Create your configuration**
```bash
# Copy the sample configuration
cp docker-compose.yml.sample docker-compose.yml

# Edit the file to customize your setup
nano docker-compose.yml  # or use your preferred editor
```

**Step 2: Deploy**
```bash
docker-compose up -d
```

**Sample configuration** (`docker-compose.yml.sample`):
```yaml
services:
  hometube:
    image: ghcr.io/EgalitarianMonkey/hometube:latest
    ports:
      - "8501:8501"
    volumes:
      - ./downloads:/data/Videos
      - ./tmp:/data/tmp
      - ./cookies:/config
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
    restart: unless-stopped
```

## Volumes

| Volume | Description | Required |
|--------|-------------|----------|
| `/data/Videos` | Output folder for downloaded videos | Recommended |
| `/data/tmp` | Temporary processing files | Optional |
| `/config` | Cookie files and configuration | Optional |

## Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `STREAMLIT_SERVER_PORT` | `8501` | Application listening port |
| `STREAMLIT_SERVER_ADDRESS` | `0.0.0.0` | Listening address |

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
  -v ./downloads:/data/Videos \
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
  -v ./downloads:/data/Videos \
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
```bash
docker exec -it hometube /bin/bash
```

### Check volumes
```bash
# Check disk space
docker exec hometube df -h

# List downloaded files
docker exec hometube ls -la /data/Videos
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