# Scripts Utilities

This directory contains utility scripts for the HomeTube project.

## Available Scripts

### `update-requirements.sh`

Automates dependency updates using uv.

### `demo_url_reuse_cache.py`

Demonstrates the intelligent URL analysis caching feature.

**Usage:**
```bash
# Run from project root
python scripts/demo_url_reuse_cache.py
```

**What it does:**
- Creates mock URL info files with different format qualities
- Tests the intelligent caching logic (reuse vs re-download decisions)
- Shows visual output of all scenarios with pass/fail indicators

**Scenarios tested:**
- ❌ Video with h264 only → Should NOT reuse (limited quality)
- ✅ Video with AV1 → Should reuse (premium quality)
- ✅ Video with VP9 → Should reuse (premium quality)
- ✅ Playlist → Should always reuse (no quality check needed)
- ✅ Mixed formats with premium → Should reuse

**When to use:**
- Understanding how the URL caching feature works
- Debugging caching behavior
- Validating changes to `app/url_utils.py`

### `update-requirements.sh`

Automates dependency updates using uv.

**Usage:**
```bash
# Run from project root
./scripts/update-requirements.sh
```

**What it does:**
1. Updates `uv.lock` lockfile
2. Regenerates `requirements/requirements.txt` (production)
3. Regenerates `requirements/requirements-dev.txt` (development)

**When to use:**
- After updating dependencies in `pyproject.toml`
- Before committing dependency changes
- During dependency maintenance

## Testing

For running tests, use the Makefile commands instead:

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-all          # All tests with coverage

# Quick development testing
make dev-test          # Fast unit tests for development
```

See the [Testing Documentation](../docs/testing.md) for more details.