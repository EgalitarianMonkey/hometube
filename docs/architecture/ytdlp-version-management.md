# yt-dlp Version Management

**Automated version tracking and updates for HomeTube using crane-based label comparison.**

## Overview

HomeTube automatically stays up-to-date with yt-dlp releases through a crane-based version detection system. This ensures users always have the latest yt-dlp features and fixes without manual intervention.

## How It Works

### 1. Version Source

HomeTube inherits yt-dlp from `jauderho/yt-dlp:latest` base image and tracks its version via OCI labels:

- **Upstream**: `jauderho/yt-dlp` → Label: `org.opencontainers.image.version`
- **HomeTube**: Image → Label: `io.hometube.ytdlp.version`

### 2. Version Detection with Crane

[Crane](https://github.com/google/go-containerregistry/tree/main/cmd/crane) reads image labels **without pulling images**:

```bash
# Detect upstream yt-dlp version
crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"'
# Output: 2025.10.14

# Check HomeTube's current version
crane config ghcr.io/egalitarianmonkey/hometube:latest | jq -r '.config.Labels."io.hometube.ytdlp.version"'
# Output: 2025.10.14
```

**Why crane?**
- ⚡ **Fast**: No image download required
- 📦 **Lightweight**: 10MB binary vs multi-GB Docker pull
- 🔍 **Precise**: Direct label access from registry

### 3. Automatic Update Workflow

The `refresh-ytdlp.yml` workflow runs daily at 2 AM UTC:

```yaml
name: Refresh yt-dlp
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:      # Manual trigger
```

**Process**:

1. **Detect versions** (crane)
   ```bash
   UPSTREAM=$(crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"')
   CURRENT=$(crane config ghcr.io/egalitarianmonkey/hometube:latest | jq -r '.config.Labels."io.hometube.ytdlp.version"')
   ```

2. **Compare versions**
   ```bash
   if [ "$UPSTREAM" != "$CURRENT" ]; then
     echo "🔄 Update needed: $CURRENT → $UPSTREAM"
     trigger_rebuild=true
   fi
   ```

3. **Trigger rebuild** (if needed)
   - Calls `build-image.yml` workflow
   - Injects `YTDLP_VERSION` via build args
   - Publishes updated image

4. **GitHub Summary**
   ```
   ✅ yt-dlp Version Check
   📦 Upstream: 2025.10.15
   🏠 Current:  2025.10.14
   🔄 Action:   Rebuild triggered
   ```

### 4. Build-Time Version Injection

The `build-image.yml` workflow detects and injects the version:

```yaml
- name: Detect yt-dlp version
  run: |
    VERSION=$(crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"')
    echo "YTDLP_VERSION=${VERSION}" >> $GITHUB_ENV

- name: Build image
  run: docker buildx build --build-arg YTDLP_VERSION=${{ env.YTDLP_VERSION }} ...
```

**Dockerfile** receives and stores the version:

```dockerfile
ARG YTDLP_VERSION
LABEL io.hometube.ytdlp.version="${YTDLP_VERSION}"
```

## Quick Reference

### Essential Commands

```bash
# Build with automatic version detection
make docker-build

# Build and verify everything
make docker-test

# Start services
make docker-up

# Check versions
make docker-build  # Shows detected version

# Run tests
pytest tests/test_ytdlp_version_detection.py -v
```

## Local Development

### Build with Automatic Detection

The Makefile simplifies local builds with automatic yt-dlp version detection:

```bash
make docker-build  # Auto-detects version via crane
make docker-up     # Start with auto-detection
make docker-test   # Build + verify labels + runtime version
```

The Makefile automatically detects the yt-dlp version from `jauderho/yt-dlp:latest` using crane (if available) and injects it into the build. If crane is not available, the build continues without the version label

### Manual Version Override

```bash
# Build with specific version
YTDLP_VERSION=2025.10.14 docker-compose build

# Or use Makefile
YTDLP_VERSION=2025.10.14 make docker-build
```

### Verify Version

```bash
# Check label
docker inspect hometube-hometube:latest --format '{{index .Config.Labels "io.hometube.ytdlp.version"}}'

# Check actual runtime version
docker run --rm hometube-hometube:latest yt-dlp --version
```

## Version Comparison Logic

HomeTube uses semantic version comparison for yt-dlp's `YYYY.MM.DD` format:

```python
def compare_versions(v1: str, v2: str) -> int:
    """
    Returns:
        -1 if v1 < v2 (older)
         0 if v1 == v2 (same)
         1 if v1 > v2 (newer)
    """
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    
    # Pad and compare component by component
    max_len = max(len(parts1), len(parts2))
    parts1 += [0] * (max_len - len(parts1))
    parts2 += [0] * (max_len - len(parts2))
    
    for p1, p2 in zip(parts1, parts2):
        if p1 != p2:
            return 1 if p1 > p2 else -1
    return 0
```

**Examples**:
- `2025.10.15` > `2025.10.14` → Rebuild triggered
- `2025.11.1` > `2025.10.31` → Rebuild triggered
- `2025.10.14` == `2025.10.14` → No action

## Testing

### Test Suite

Run version detection tests:

```bash
# All tests
pytest tests/test_ytdlp_version_detection.py -v

# Quick unit tests (no crane needed)
pytest tests/test_ytdlp_version_detection.py -m "unit" -v

# Network tests (requires crane)
pytest tests/test_ytdlp_version_detection.py -m "network" -v
```

### Test Coverage

**Unit Tests** (`@pytest.mark.unit`):
- ✅ Version comparison logic
- ✅ Date format validation
- ✅ Edge cases (multi-digit, padding)

**Integration Tests** (`@pytest.mark.network`):
- ✅ Crane availability
- ✅ Upstream version detection
- ✅ Published image consistency
- ✅ Local build verification

**Example output**:

```
✅ Published HomeTube has yt-dlp version: 2025.10.14
✅ HomeTube is up to date with upstream: 2025.10.14
   Days behind: 0
✅ Local HomeTube matches upstream: 2025.10.14
```

## Monitoring

### Check Current Versions

```bash
# Upstream yt-dlp
crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"'

# Published HomeTube
crane config ghcr.io/egalitarianmonkey/hometube:latest | jq -r '.config.Labels."io.hometube.ytdlp.version"'

# Local build
docker inspect hometube:latest --format '{{index .Config.Labels "io.hometube.ytdlp.version"}}'
```

### GitHub Actions

View workflow runs:
- [Refresh yt-dlp Workflow](../../actions/workflows/refresh-ytdlp.yml)
- [Build Image Workflow](../../actions/workflows/build-image.yml)

Check workflow summaries for version reports.

## Troubleshooting

### Workflow Not Triggering

**Issue**: No rebuild despite upstream update

**Check**:
```bash
# Compare versions manually
UPSTREAM=$(crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"')
CURRENT=$(crane config ghcr.io/egalitarianmonkey/hometube:latest | jq -r '.config.Labels."io.hometube.ytdlp.version"')
echo "Upstream: $UPSTREAM"
echo "Current:  $CURRENT"
```

**Solution**: Trigger manually via GitHub Actions UI

### Local Build Has Wrong Version

**Issue**: `io.hometube.ytdlp.version` label missing or incorrect

**Check**:
```bash
# Verify crane is installed
crane version

# Rebuild with detection
make docker-test
```

**Solution**: Install crane or set version manually:
```bash
YTDLP_VERSION=$(crane config jauderho/yt-dlp:latest | jq -r '.config.Labels."org.opencontainers.image.version"')
docker-compose build --build-arg YTDLP_VERSION=$YTDLP_VERSION
```

### Tests Skip with "crane not found"

**Solution**: Install crane:

```bash
# macOS
brew install crane

# Linux
curl -sL "https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz" | tar xz
sudo mv crane /usr/local/bin/
```

Unit tests still run without crane.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│ Upstream: jauderho/yt-dlp:latest                            │
│ Label: org.opencontainers.image.version = "2025.10.15"     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ crane config (no pull)
                         ▼
                   ┌──────────┐
                   │  Compare │
                   │ Versions │
                   └─────┬────┘
                         │
            ┌────────────┴────────────┐
            │ Different?              │
            └────┬────────────────┬───┘
                 │ Yes            │ No
                 │                │
                 ▼                ▼
          ┌──────────┐      ┌─────────┐
          │ Rebuild  │      │  Skip   │
          │ Trigger  │      └─────────┘
          └────┬─────┘
               │
               │ build-arg YTDLP_VERSION=2025.10.15
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Dockerfile                                                    │
│ ARG YTDLP_VERSION                                            │
│ LABEL io.hometube.ytdlp.version="${YTDLP_VERSION}"          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ Published: ghcr.io/egalitarianmonkey/hometube:latest        │
│ Label: io.hometube.ytdlp.version = "2025.10.15"             │
└──────────────────────────────────────────────────────────────┘
```

## Key Benefits

✅ **Zero manual intervention** - Fully automated updates
✅ **Fast detection** - Crane reads labels without pulling images
✅ **Transparent tracking** - Version visible in image labels
✅ **Testable** - Comprehensive pytest suite validates logic
✅ **Developer-friendly** - Simple Makefile commands for local builds

## Related Files

- `.github/workflows/refresh-ytdlp.yml` - Daily version check
- `.github/workflows/build-image.yml` - Reusable build with detection
- `Dockerfile` - Version label injection
- `Makefile` - Local build commands
- `docker-compose.yml` - Build args configuration
- `tests/test_ytdlp_version_detection.py` - Test suite

## References

- [Crane Documentation](https://github.com/google/go-containerregistry/tree/main/cmd/crane)
- [OCI Image Spec - Labels](https://github.com/opencontainers/image-spec/blob/main/annotations.md)
- [jauderho/yt-dlp Docker Image](https://hub.docker.com/r/jauderho/yt-dlp)
