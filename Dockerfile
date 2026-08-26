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
# py3-pip is one of them: the base image ships python3 without pip.
apk add --no-cache --virtual .build-deps build-base python3-dev py3-pip

# Upgrade pip and install runtime deps. Always go through "python3 -m pip":
# the base provides no "pip" executable on PATH.
python3 -m pip install --no-cache-dir --upgrade pip --break-system-packages
python3 -m pip install --no-cache-dir --only-binary=:all: --no-binary=watchdog --no-compile ".[docker]" --break-system-packages

# Remove heavy optional deps not needed by HomeTube
python - <<'PY'
import importlib.util, subprocess, sys, os
env = dict(os.environ)
def rm(pkg: str):
    if importlib.util.find_spec(pkg):
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", pkg, "--break-system-packages"], env=env)
rm("pyarrow")
# If you never use deck.gl maps in Streamlit, uncomment:
# rm("pydeck")
PY

# Prune Python bloat
find /usr/lib/python3*/site-packages -type d -name "__pycache__" -prune -exec rm -rf {} +
find /usr/lib/python3*/site-packages -type d -regex '.*\(tests\|testing\|test\)$' -exec rm -rf {} +
find /usr/lib/python3*/site-packages -type f -name '*.pyi' -delete

# Drop build deps before committing the layer
apk del .build-deps
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