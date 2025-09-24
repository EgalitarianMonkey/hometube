FROM jauderho/yt-dlp:latest

# Add metadata
LABEL org.opencontainers.image.title="HomeTube"
LABEL org.opencontainers.image.description="🎬 HomeTube is a simple web UI for downloading single videos from the internet with the highest quality available and moving them to specific local locations automatically managed and integrated by media server such as Plex or Jellyfin."
LABEL org.opencontainers.image.url="https://github.com/EgalitarianMonkey/hometube"
LABEL org.opencontainers.image.source="https://github.com/EgalitarianMonkey/hometube"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

# Install additional tools needed for HomeTube (Alpine packages)
RUN apk add --no-cache \
    tini \
    ca-certificates \
    curl

WORKDIR /app

# Copy only pyproject.toml first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies (Alpine style with --break-system-packages)
RUN pip install --no-cache-dir --upgrade pip --break-system-packages

# Copy source code
COPY app/ ./app/

# Install the package with Docker-specific dependencies (excluding yt-dlp since it's already in base image)
RUN pip install --no-cache-dir ".[docker]" --break-system-packages

# Copy Streamlit configuration for consistent UI theme
COPY .streamlit/ /app/.streamlit/

RUN mkdir -p /data/videos /data/tmp /config

# Create non-root user for security (Alpine style)
RUN addgroup -g 1000 streamlit && \
    adduser -D -s /bin/sh -u 1000 -G streamlit streamlit && \
    chown -R streamlit:streamlit /app /data /config

USER streamlit

EXPOSE 8501
ENTRYPOINT ["/sbin/tini","--"]
CMD ["streamlit", "run", "app/main.py", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.address=0.0.0.0"]
