# Deliberately unpinned: refresh-ytdlp.yml rebuilds daily off this tag so a new
# yt-dlp release reaches users without a manual bump. The trade-off is that the
# base can change under us (it dropped a preinstalled pip and moved to Python
# 3.14), so the install step below must not assume anything beyond python3.
FROM jauderho/yt-dlp:latest

# Static labels (common to all builds)
LABEL org.opencontainers.image.title="HomeTube" \
    org.opencontainers.image.description="🎬 HomeTube is a simple web UI for videos downloading" \
    org.opencontainers.image.url="https://github.com/EgalitarianMonkey/hometube" \
    org.opencontainers.image.source="https://github.com/EgalitarianMonkey/hometube" \
    org.opencontainers.image.licenses="AGPL-3.0-or-later"

# Dynamic yt-dlp version label - will be set by build args
ARG YTDLP_VERSION
LABEL io.hometube.ytdlp.version="${YTDLP_VERSION}"

# Minimal runtime deps
RUN apk add --no-cache tini ca-certificates curl deno

# Pip/Streamlit/runtime ergonomics
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_HEADLESS=true

WORKDIR /app

# Copy project metadata early for layer caching
COPY pyproject.toml ./

# One single RUN via Dockerfile heredoc (requires BuildKit)
RUN <<'BASH'
set -eux
# Temporary build deps (watchdog may need a build on musllinux/aarch64).
# py3-pip is one of them: no interpreter in the base image carries a pip.
apk add --no-cache --virtual .build-deps build-base python3-dev py3-pip

# The base image currently puts a uv-built virtualenv first on PATH, and that
# venv holds no pip of its own. So drive every install from the system pip and
# aim it at whichever interpreter PATH resolves to: HomeTube then lands in the
# very environment CMD runs in, venv or not. "pip --python" needs no pip on the
# target, and PIP_BREAK_SYSTEM_PACKAGES covers the case where that target turns
# out to be the system interpreter.
TARGET_PY="$(command -v python3)"
SITE_DIR="$("$TARGET_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"

/usr/bin/python3 -m pip --python "$TARGET_PY" install --no-cache-dir \
    --only-binary=:all: --no-binary=watchdog --no-compile ".[docker]"

# Remove heavy optional deps not needed by HomeTube.
# (Add pydeck to the list to also drop Streamlit's deck.gl maps support.)
for pkg in pyarrow; do
    if "$TARGET_PY" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$pkg') else 1)"; then
        /usr/bin/python3 -m pip --python "$TARGET_PY" uninstall -y "$pkg"
    fi
done

# Prune Python bloat
find "$SITE_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$SITE_DIR" -type d -regex '.*\(tests\|testing\|test\)$' -exec rm -rf {} +
find "$SITE_DIR" -type f -name '*.pyi' -delete

# Drop build deps before committing the layer
apk del .build-deps

# A base that shifts under us must break the build here, not at runtime
"$TARGET_PY" -c 'import streamlit'
yt-dlp --version
BASH

# App code
COPY app/ ./app/
COPY .streamlit/ /app/.streamlit/
# Copy favicon for page icon
COPY docs/icons/favicon.svg /app/docs/icons/favicon.svg

# Folders + non-root user
RUN <<'BASH'
set -eux
mkdir -p /data/videos /data/tmp /config
addgroup -g 1000 streamlit
adduser -D -s /bin/sh -u 1000 -G streamlit streamlit
chown -R streamlit:streamlit /app /data /config
BASH

USER streamlit

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
    CMD wget -qO- http://127.0.0.1:8501/_stcore/health || exit 1

ENTRYPOINT ["/sbin/tini","--"]
CMD ["python","-m","streamlit","run","app/main.py","--server.headless=true","--server.address=0.0.0.0","--server.enableCORS=false","--server.enableXsrfProtection=false"]