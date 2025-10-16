# Scripts Utilities

This directory contains utility scripts for the HomeTube project.

## Available Scripts

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