# 🛠️ Development Guide

Guide for developers contributing to the Universal Video Downloader project.

## 🏗️ Development Setup

### Prerequisites

- **Python 3.10+**
- **Package manager**: pip, conda, uv, or poetry
- **Docker** (for container testing)
- **Git**
- **FFmpeg**

### Quick Setup

```bash
# Clone repository
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube

# Setup development environment (using make)
make dev-setup

# Verify installation
make test
```

### Manual Setup

Choose your preferred environment manager:

#### Using pip/venv
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
pip install -e ".[dev]"
```

#### Using conda
```bash
# Create conda environment
conda create -n hometube python=3.11
conda activate hometube

# Install dependencies
pip install -e .
pip install -e ".[dev]"
```

#### Using uv
```bash
# Install dependencies
uv sync

# Install development dependencies
uv add --dev pytest pytest-asyncio pytest-mock pytest-cov pytest-xdist
```

## 🧪 Testing Framework

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration  
├── test_core_functions.py   # Core utility functions tests
├── test_translations.py     # Translation system tests
└── test_utils.py            # Project structure and configuration tests
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit           # Unit tests only
make test-integration    # Integration tests
make test-performance    # Performance tests

# Run with coverage
make test-coverage

# Run specific test file
python -m pytest tests/test_utils.py -v

# Run specific test function
python -m pytest tests/test_utils.py::TestUtilityFunctions::test_sanitize_filename -v

# Alternative: using make
make test-file           # Interactive file selection
make test-pattern        # Interactive pattern matching
```

### Test Categories

**Unit Tests** (`@pytest.mark.unit`):
- Fast, isolated function tests
- No external dependencies
- Comprehensive utility function coverage

**Integration Tests** (`@pytest.mark.integration`):
- Component interaction testing
- File system operations
- Configuration validation

**Performance Tests** (`@pytest.mark.performance`):
- Speed benchmarks
- Memory usage validation
- Stress testing with large inputs

**Network Tests** (`@pytest.mark.network`):
- Real API calls (skipped by default)
- External service integration
- Authentication flows

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from app.main import sanitize_filename

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test basic sanitization
        result = sanitize_filename("test<>file.mp4")
        assert result == "testfile.mp4"
        
        # Test edge cases
        assert sanitize_filename("") == ""
        assert sanitize_filename("normal.mp4") == "normal.mp4"
    
    @pytest.mark.performance
    def test_sanitize_filename_performance(self):
        """Test performance with large inputs."""
        large_filename = "A" * 10000 + "?" * 1000
        
        import time
        start = time.time()
        result = sanitize_filename(large_filename)
        duration = time.time() - start
        
        assert duration < 1.0  # Should complete in under 1 second
        assert isinstance(result, str)
```

### Mocking Guidelines

**Streamlit Components**:
```python
# Tests automatically mock Streamlit via conftest.py
def test_function_using_streamlit():
    from app.main import some_function_using_st
    result = some_function_using_st()
    assert result is not None
```

**External Services**:
```python
@patch('requests.get')
def test_api_call(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_get.return_value = mock_response
    
    # Test your function
    result = your_api_function()
    assert result["status"] == "success"
```

## 📊 Code Quality

### Code Coverage

Current coverage: **29%** (target: 80%+)

```bash
# Generate coverage report
make test-coverage

# View HTML report
open htmlcov/index.html
```

**Coverage Goals**:
- **Utilities**: 90%+ (core functions)
- **Main Application**: 70%+ (UI components)
- **Integration**: 60%+ (external dependencies)

### Code Style

**Formatting**:
```bash
# Format code
make format

# Check formatting
make lint
```

**Standards**:
- **PEP 8** compliance
- **Type hints** for new functions
- **Docstrings** for public APIs
- **Consistent naming** conventions

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🚀 CI/CD Pipeline

### GitHub Actions Workflows

**1. Tests Workflow** (`.github/workflows/tests.yml`):
- Triggered on: Push, Pull Request
- Runs on: Ubuntu, Python 3.10-3.12
- Steps: Install dependencies → Run tests → Upload coverage

**2. Docker Build** (`.github/workflows/docker-build.yml`):
- Triggered on: Push to main, Tags
- Builds: Multi-architecture images
- Pushes to: GitHub Container Registry

**3. Release** (`.github/workflows/release.yml`):
- Triggered on: Version tags (v*)
- Creates: GitHub releases with changelog
- Includes: Documentation artifacts

### Local CI Testing

```bash
# Run full CI pipeline locally
make ci

# Test Docker build
docker build -t hometube:test .

# Test different Python versions (with pyenv)
pyenv install 3.10.12 3.11.9 3.12.1
pyenv local 3.10.12
make test-all
```

## 🏗️ Architecture

### Project Structure

```
hometube/
├── app/                     # Main application
│   ├── main.py             # Streamlit app entry point
│   ├── utils.py            # Utility functions
│   └── translations/       # i18n support
├── requirements/            # Dependencies
│   ├── requirements.txt    # Runtime dependencies (auto-generated)
│   └── requirements-dev.txt # Dev dependencies (auto-generated)
├── tests/                   # Test suite
├── docs/                    # Documentation
├── .github/                 # CI/CD workflows
├── nginx/                   # Production nginx config
├── Dockerfile              # Container definition
├── pyproject.toml          # Project configuration
└── Makefile               # Development commands
```

### Key Components

**Core Modules**:
- `main.py`: Streamlit UI and main application logic
- `translations/`: Multi-language support
- Utility functions: Video processing, file management, API integration

**External Dependencies**:
- **yt-dlp**: Video downloading engine
- **Streamlit**: Web interface framework
- **FFmpeg**: Video/audio processing
- **Requests**: HTTP client for APIs

### Design Patterns

**Configuration Management**:
- Environment variables for deployment settings
- Session state for UI persistence
- Cookie-based authentication flow

**Error Handling**:
- Graceful degradation for missing dependencies
- User-friendly error messages
- Comprehensive logging

**Performance Optimization**:
- Lazy loading of heavy dependencies
- Caching of expensive operations
- Streaming for large file operations

## 🔄 Contributing Workflow

### 1. Issue Creation

**Bug Reports**:
- Use bug report template
- Include reproduction steps
- Provide system information
- Add relevant logs

**Feature Requests**:
- Use feature request template
- Explain use case and benefits
- Consider backward compatibility
- Suggest implementation approach

### 2. Development Process

#### 1. Fork and Clone
```bash
git clone https://github.com/EgalitarianMonkey/hometube.git
cd hometube
```

#### 2. Create a Feature Branch
```bash
git checkout -b feature/awesome-feature
```

#### 3. Make Changes
_Edit your code here_

#### 4. Run Tests and Lint
```bash
make test-all
make lint
```

#### 5. Update Version (if needed)

**In `__init__.py`:**
```python
__version__ = "1.2.0"
```

**In `pyproject.toml`:**
```toml
version = "1.2.0"
```

**Update lock file:**
```bash
uv lock
```

**Update requirements files for python:**
```bash
uv pip compile pyproject.toml -o requirements/requirements.txt
```

#### 6. Stage Changes
```bash
git add .
```

#### 7. Commit (Conventional Commit Format)
```bash
git commit -m "feat: add awesome new feature

- Implements feature X
- Improves performance by Y%
- Fixes issue #123"
```

#### 8. Push feature branch
```bash
git push origin feature/awesome-feature
```

#### 9. Open a Pull Request
_Open a PR from your feature branch to `main` on GitHub._


#### 10. Squash and merge
_Once the  GitHub Actions workflow is passed, squash and merge all the feature branch commits in one._

#### 11. Pull main commit and push tag on it
```bash
git pull origin main
git checkout main
git tag v1.2.0
git push origin v1.2.0
```

#### 13. Verify GitHub Actions
_Check CI results for validation before merging._


### 3. Pull Request Guidelines

**PR Checklist**:
- [ ] Tests pass locally
- [ ] Code is formatted (make format)
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Breaking changes documented

**PR Description**:
- Clear title and description
- Link to related issues
- Screenshots for UI changes
- Testing instructions

### 4. Code Review Process

**Review Criteria**:
- **Functionality**: Does it work as intended?
- **Testing**: Adequate test coverage?
- **Performance**: No significant regressions?
- **Documentation**: Clear and complete?
- **Style**: Follows project conventions?

## 🚢 Release Process

### Version Strategy

**Semantic Versioning** (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Steps

```bash
# 1. Update version
git checkout main
git pull origin main

# 2. Update CHANGELOG.md
# Add new version section with changes

# 3. Create and push tag
git tag v1.2.0
git push origin v1.2.0

# 4. GitHub Actions automatically:
# - Builds Docker images
# - Creates GitHub release
# - Updates documentation
```

### Deployment

**Development**:
- Every push to `main` → `latest` Docker image
- Available at `ghcr.io/EgalitarianMonkey/hometube:latest`

**Production**:
- Version tags → versioned Docker images
- Available at `ghcr.io/EgalitarianMonkey/hometube:v1.2.0`
- GitHub releases with changelogs and artifacts

## 🛠️ Development Tools

### Useful Commands

```bash
# Development environment
make dev-setup              # Setup development environment
make test-watch             # Run tests in watch mode
make format                 # Format code with black
make lint                   # Run linting checks
make type-check             # Run type checking
make clean                  # Clean build artifacts

# Docker development
make docker-build           # Build local Docker image
make docker-test            # Test Docker image
make docker-run             # Run Docker container locally

# Documentation
make docs-serve             # Serve documentation locally
make docs-build             # Build documentation
```

### IDE Configuration

**VS Code Settings** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.formatting.provider": "black",
    "editor.formatOnSave": true
}
```

**PyCharm Configuration**:
- Interpreter: Project virtual environment
- Test runner: pytest
- Code style: Black
- Inspections: Enable all Python inspections

## 📚 Additional Resources

### Learning Resources

- **Streamlit**: [Official Documentation](https://docs.streamlit.io/)
- **yt-dlp**: [GitHub Repository](https://github.com/yt-dlp/yt-dlp)
- **pytest**: [Testing Guide](https://docs.pytest.org/)
- **Docker**: [Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Community

- **GitHub Discussions**: Project discussions and Q&A
- **Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions

### Getting Help

1. Check existing [documentation](../README.md)
2. Search [GitHub Issues](https://github.com/EgalitarianMonkey/hometube/issues)
3. Create new issue with detailed information
4. Join community discussions

---

**Next: [Deployment Guide](deployment.md)** - Production deployment strategies