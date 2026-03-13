# 🛠️ Contributing Guide

Complete guide for contributing to HomeTube.

## 📋 Prerequisites

- **Python 3.10+**
- **Git**
- **FFmpeg** (for video processing)
- **Package manager**: UV (recommended), conda, or pip

## 🚀 Quick Setup

Choose your preferred environment:

### Option A: UV (Recommended - Fastest)

```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Configure environment
cp .env.sample .env

# Install UV if needed: curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Verify setup
make test
```

### Option B: Conda (Best for Contributors)

```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Create environment with all dependencies
conda env create -f environment.yml
conda activate hometube

# Verify setup
make test
```

### Option C: pip/venv (Universal)

```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Configure environment
cp .env.sample .env

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements/requirements-dev.txt

# Verify setup
make test
```

## 🏃 Running the Application

```bash
# Standard launch
python run.py

# Debug mode with detailed logging
DEBUG=1 python run.py

# Custom port
PORT=8502 streamlit run app/main.py

# With UV
uv run streamlit run app/main.py
```

Access the application at: <http://localhost:8501>

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Fast tests only
make test-fast

# With coverage report
make test-coverage

# Specific test categories
make test-unit           # Unit tests only
make test-integration    # Integration tests

# Run specific test file
python -m pytest tests/test_core_functions.py -v

# Run specific test function
python -m pytest tests/test_core_functions.py::test_sanitize_filename -v
```

### With UV (Faster)

```bash
make uv-test
make uv-test-fast
```

### Test Categories

Tests use pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Component interaction tests
- `@pytest.mark.performance` - Speed benchmarks
- `@pytest.mark.network` - Real API calls (skipped by default)

## 📊 Code Quality

### Formatting & Linting

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# All quality checks before commit
make pre-commit
```

### Code Standards

- **PEP 8** compliance
- **Type hints** for all new functions
- **Docstrings** for public APIs
- **Tests** for new functionality

## 🔄 Development Workflow

### 1. Fork and Clone

```bash
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube
```

### 2. Create Feature Branch

```bash
git checkout -b feature/awesome-feature
```

### 3. Make Changes

Edit your code and add tests.

### 4. Run Tests and Lint

```bash
make test
make lint
```

### 5. Commit (Conventional Commits)

```bash
git add .
git commit -m "feat: add awesome new feature

- Implements feature X
- Improves performance by Y%
- Fixes issue #123"
```

### 6. Push and Create PR

```bash
git push origin feature/awesome-feature
```

Open a Pull Request on GitHub.

### 7. After Merge

```bash
git checkout main
git pull origin main
git branch -d feature/awesome-feature
```

## 📦 Dependency Management

### Adding Dependencies

```bash
# Core dependency
uv add streamlit>=1.50.0

# Development dependency
uv add --dev pytest>=8.0.0

# Sync all files
make sync-deps
```

### Updating Dependencies

```bash
# Update all dependencies
make update-deps

# Verify everything works
make test
```

### Version Updates

Update version in three places:

```bash
# Using make (recommended)
make version-update 2.0.0
```

Or manually update:

1. `app/__init__.py`: `__version__ = "2.0.0"`
2. `pyproject.toml`: `version = "2.0.0"`
3. Regenerate lock: `uv lock`

## 🐛 Debug Mode

### Environment Variables

```bash
# Keep temporary files for debugging
export REMOVE_TMP_FILES_AFTER_DOWNLOAD=false

# Enable debug logging
export DEBUG=1

# Custom development paths
export VIDEOS_FOLDER=./dev-downloads
export TMP_DOWNLOAD_FOLDER=./dev-tmp

# Test different languages
export UI_LANGUAGE=fr
```

### Debug Session Example

```bash
DEBUG=1 REMOVE_TMP_FILES_AFTER_DOWNLOAD=false python run.py
```

## 🏗️ Project Structure

```text
hometube/
├── app/                     # Main application
│   ├── main.py             # Streamlit entry point
│   ├── core.py             # Core download logic
│   ├── config.py           # Configuration management
│   ├── json_utils.py       # JSON file operations
│   ├── constants.py        # Shared constants
│   └── translations/       # i18n support
├── tests/                   # Test suite
├── docs/                    # Documentation
├── requirements/            # Dependency files
├── .github/                 # CI/CD workflows
├── Dockerfile              # Container definition
├── pyproject.toml          # Project configuration
└── Makefile               # Development commands
```

## 🚀 CI/CD Pipeline

GitHub Actions workflows:

| Workflow | Trigger | Purpose |
| -------- | ------- | ------- |
| `tests.yml` | Push, PR | Run tests on Python 3.10-3.12 |
| `docker-build.yml` | Push to main, tags | Build multi-arch Docker images |
| `release.yml` | Version tags (v*) | Create GitHub releases |
| `refresh-ytdlp.yml` | Daily, manual | Update yt-dlp version |

### Local CI Testing

```bash
# Run full CI pipeline locally
make ci

# Test Docker build
docker build -t hometube:test .
```

## ✅ PR Checklist

Before submitting:

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation updated if needed
- [ ] Conventional commit messages used

## 📊 Performance Comparison

| Environment | Setup Time | Test Speed | Best For |
| ----------- | ---------- | ---------- | -------- |
| UV          | ~10s       | Fastest    | Regular development |
| Conda       | ~60s       | Medium     | Complex dependencies |
| pip/venv    | ~30s       | Medium     | Universal compatibility |

## 📚 Additional Resources

- **[Testing Guide](testing.md)** - Detailed testing documentation
- **[Architecture docs](architecture/)** - Technical implementation details
- **[Streamlit docs](https://docs.streamlit.io/)** - UI framework documentation
- **[yt-dlp docs](https://github.com/yt-dlp/yt-dlp)** - Download engine documentation

## 🤝 Getting Help

1. Check existing [documentation](README.md)
2. Search [GitHub Issues](https://github.com/EgalitarianMonkey/hometube/issues)
3. Create new issue with detailed information
4. Join [GitHub Discussions](https://github.com/EgalitarianMonkey/hometube/discussions)

---

Thank you for contributing to HomeTube! 🎬
