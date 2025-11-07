# Development Setup Guide

HomeTube supports multiple development environments. Choose the approach that best fits your workflow:

## 🚀 Quick Start (Contributors)

### Option A: Using Conda (Recommended for new contributors)
```bash
# Clone and setup
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Create environment and install dependencies
conda env create -f environment.yml
conda activate hometube

# Run tests to verify setup
make test
```

### Option B: Using UV (Fastest, for regular developers)
```bash
# Clone and setup
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# ⚠️ ESSENTIAL: Configure environment first
cp .env.sample .env

# Install UV if not already installed
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync environment
uv sync

# Run tests
make test
# or faster with UV:
make uv-test
```

### Option C: Using pip/venv (Universal)
```bash
# Clone and setup
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# ⚠️ ESSENTIAL: Configure environment first
cp .env.sample .env

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements/requirements-dev.txt

# Run tests
make test
```

## 🛠️ Development Commands

### Universal Commands (work with any Python environment)
```bash
# Testing
make test              # Run all tests
make test-fast         # Run fast tests only
make test-coverage     # Run tests with coverage
make test-unit         # Run unit tests only

# Code Quality
make lint              # Lint and format code
make format            # Format code only
make type-check        # Run type checking

# Utilities
make clean             # Clean test artifacts
make help              # Show all available commands
```

### UV-Specific Commands (faster, requires UV)
```bash
make uv-sync           # Sync dependencies with UV
make uv-test           # Run tests with UV
make uv-test-fast      # Run fast tests with UV
make uv-lint           # Run linting with UV
```

## 🏗️ Project Structure

```
├── app/                    # Main application code
├── tests/                  # Test suite
├── docs/                   # Documentation
├── pyproject.toml         # UV + modern Python configuration
├── environment.yml        # Conda environment
├── requirements/          # Dependencies directory
│   ├── requirements.txt       # Core dependencies
│   └── requirements-dev.txt   # Development dependencies
├── Makefile              # Universal build commands
└── uv.lock               # UV lock file (for reproducibility)
```

## 🎯 Recommended Workflows

### For Contributors (First Time)
1. Use **Conda** setup (Option A above)
2. Run `make test` to verify everything works
3. Make your changes
4. Run `make pre-commit` before committing

### For Regular Developers
1. Use **UV** setup (Option B above)
2. Use `make uv-test-fast` for quick feedback
3. Use `make pre-commit` before pushing

### For CI/CD
1. Install UV for fast dependency resolution
2. Use universal `python -m pytest` commands
3. Both approaches are supported

## 🔧 Troubleshooting

### Environment Issues
```bash
# Check your environment
make env-info

# Clean and restart
make clean
# Then re-setup your environment
```

### Missing Dependencies
```bash
# Conda users
conda activate hometube
make dev-setup

# UV users  
uv sync

# pip users
pip install -r requirements/requirements-dev.txt
```

### Test Failures
```bash
# Run specific test
make test-file

# Debug specific test
make debug-test

# Run only failed tests
make test-failed
```

## 🔧 Development Environment Variables

### Debug & Testing Options

```bash
# Keep temporary files for debugging (useful for troubleshooting subtitle issues)
export REMOVE_TMP_FILES_AFTER_DOWNLOAD=false

# Don't clean tmp before downloads (preserve cache)
export NEW_DOWNLOAD_WITHOUT_TMP_FILES=false

# Enable debug mode for detailed logging
export DEBUG=1

# Custom development paths
export VIDEOS_FOLDER=./dev-downloads
export TMP_DOWNLOAD_FOLDER=./dev-tmp

# Test with different languages
export UI_LANGUAGE=fr
export LANGUAGE_PRIMARY=fr
export LANGUAGE_PRIMARY_INCLUDE_SUBTITLES=true
export LANGUAGES_SECONDARIES=en,es
```

### Useful Debug Combinations

```bash
# Full debug mode with file preservation
export DEBUG=1
export REMOVE_TMP_FILES_AFTER_DOWNLOAD=false
python run.py

# Test subtitle processing (keeps all .srt/.vtt files)
export REMOVE_TMP_FILES_AFTER_DOWNLOAD=false
make test

# Development with custom paths
export VIDEOS_FOLDER=./test-videos
export TMP_DOWNLOAD_FOLDER=./test-tmp
export REMOVE_TMP_FILES_AFTER_DOWNLOAD=false
streamlit run app/main.py

# Force fresh download (useful after errors)
export NEW_DOWNLOAD_WITHOUT_TMP_FILES=true
python run.py
```

**🔍 Debug Mode Benefits:**

- **REMOVE_TMP_FILES_AFTER_DOWNLOAD=false**: Keeps all temporary files (.srt, .vtt, .part, intermediate outputs) in `tmp/` folder
- **NEW_DOWNLOAD_WITHOUT_TMP_FILES=false**: Reuses cached files for intelligent caching (set to `true` for fresh start)
- **DEBUG=1**: Enables detailed logging and configuration summary
- **Custom paths**: Separate development files from production

## 🚀 Quick Development Commands

### Launch Application
```bash
# Test the app quickly
python run.py

# Debug mode with configuration summary  
DEBUG=1 python run.py

# Custom port
PORT=8502 streamlit run app/main.py

# Direct Streamlit launch
streamlit run app/main.py

# UV-managed launch (if using UV)
uv run streamlit run app/main.py
```

### Testing & Validation
```bash
# Run all tests
make test

# Check configuration status
make config-check

# Run tests with UV (faster)
make uv-test

# Check test coverage
make test-coverage
```

### Development Workflow
```bash
# Setup environment (do once)
# Using UV:    uv sync
# Using Conda: conda env create -f environment.yml && conda activate hometube
# Using pip:   python -m venv .venv && source .venv/bin/activate && pip install -r requirements/requirements-dev.txt

# Daily development (repeat as needed)
python run.py              # Launch app
make test                  # Run tests
make config-check          # Verify configuration
```

## �📊 Performance Comparison

| Environment | Setup Time | Test Speed | Best For |
|-------------|------------|------------|----------|
| UV          | ~10s       | Fastest    | Regular development |
| Conda       | ~60s       | Medium     | Contributors, complex deps |
| pip/venv    | ~30s       | Medium     | Universal compatibility |

Choose the setup that matches your needs! 🎉