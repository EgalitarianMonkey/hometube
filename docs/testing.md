# HomeTube Testing Documentation 🧪

## 📊 Current Testing Status

### ✅ Test Suite Overview
- **20 focused tests** covering core functionality
- **84% coverage** on testable modules (`app.utils`, `app.translations`)
- **Robust Streamlit mocking** prevents import conflicts
- **Multi-environment support** (UV, conda, pip/venv)
- **Quick execution** (< 2 seconds for full suite)

### 🏗️ Current test structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Centralized configuration + fixtures (71 lines)
├── test_core_functions.py   # Core function tests (146 lines, 10 tests)
├── test_translations.py     # Translation system tests (106 lines, 4 tests)  
└── test_utils.py           # Project structure tests (108 lines, 6 tests)
```

**Note**: The project uses a **simplified but robust** testing approach with focused coverage of essential functionality.

## 🚀 Quick Start

### Run Tests
```bash
# Quick tests (< 2 seconds)
make test-fast

# Full test suite
make test

# With coverage report
make test-coverage

# Specific test categories
make test-unit           # Unit tests only
make test-integration    # Integration tests
make test-performance    # Performance tests
```

### Daily Development Commands
```bash
# Basic development workflow
make test                # Quick verification
make test-coverage       # Before commits
make pre-commit         # Full quality checks
```

## 🔧 Testing features

### 1. Robust pytest configuration (`pytest.ini`)
- Custom markers (unit, integration, performance, slow, external, stress)
- Optimized default options 
- Warning filters
- Test discovery configuration

### 2. Centralized fixtures (`conftest.py`)
- `mock_streamlit`: Complete and robust Streamlit mock that handles imports
- `temp_dir`: Temporary directories for tests
- `project_root`: Project root path fixture
- Streamlit session state mocking
- Import-time mocking to prevent conflicts

### 3. Core function tests (`test_core_functions.py`)
- **10 focused tests** covering main utility functions
- Edge case testing (empty inputs, invalid data)
- URL validation and sanitization
- Time parsing and formatting
- Video ID extraction
- Segment inversion algorithms
- Browser validation
- Cookie file validation

### 4. Translation system tests (`test_translations.py`)
- **4 essential tests** for internationalization
- Translation file existence verification
- Module import testing with fallbacks
- Essential key presence validation
- Empty translation detection

### 5. Project structure tests (`test_utils.py`)
- **6 structural tests** ensuring project integrity
- Directory existence validation (app/, tests/, downloads/)
- Required file verification (main.py, pyproject.toml, Makefile, etc.)
- Configuration file testing
- Fixture functionality verification
- Performance regression tests
- Concurrency simulation
- Baseline performance metrics

### 6. Robust translation tests (`test_translations.py`)
- Cross-language consistency verification
- Translation quality tests
- File structure validation
- Translation function tests
- Edge case handling (special characters, etc.)

### 6. Automation and tools

#### Enhanced Makefile
```bash
# Universal testing commands (work with any Python environment)
make test             # Run all tests
make test-all         # Run complete test suite with coverage
make test-unit        # Run unit tests only (core + translations + utils)
make test-fast        # Run fast tests only (exclude slow and external)
make test-coverage    # Run tests with coverage report

# UV-specific commands (faster for UV users)
make uv-test          # Run tests with UV
make uv-test-fast     # Run fast tests with UV
```

#### Verification script (`scripts/check_tests.py`)
- Automatic structure verification
- Execution of all test categories
- Detailed summary report  
- Usage instructions

## 📈 Current metrics

### Test coverage
- **Current**: 20 focused tests covering essential functionality
- **Approach**: Quality over quantity - core functions well tested
- **Coverage**: Main utilities, translations, project structure

### Organization
- **Current**: 3 specialized test modules + fixtures
- **Structure**: Clean separation by functionality
- **Focus**: Essential testing without complexity overhead

### Test performance
- **Speed**: Fast execution (< 2 seconds for full suite)
- **Reliability**: Robust Streamlit mocking prevents import conflicts
- **Maintainability**: Simple, focused tests easy to understand and maintain

## 🎯 Key testing features

### 1. Robust Streamlit mocking
The most challenging aspect of testing a Streamlit app is handled elegantly:

```python
# conftest.py - Import-time mocking
if "streamlit" in sys.modules:
    del sys.modules["streamlit"]

# Create complete mock that handles all Streamlit functionality
mock_st = MagicMock()
mock_session_state = MagicMock()
mock_session_state.__contains__ = MagicMock(return_value=False)
mock_st.session_state = mock_session_state
```

### 2. Comprehensive core function testing
Core utilities are thoroughly tested with edge cases:

```python
def test_sanitize_filename(self):
    # Normal cases
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"
    # Forbidden characters
    assert sanitize_filename('file<>:"/\\|?*.txt') == "file_________.txt"
    # Edge cases
    assert sanitize_filename("   ") == "unnamed"
```

### 3. Translation system validation
Ensures internationalization integrity:

```python
def test_essential_keys_present(self, project_root):
    essential_keys = ["page_title", "page_header"]
    for key in essential_keys:
        assert hasattr(en, key), f"Missing key {key} in English translations"
        assert hasattr(fr, key), f"Missing key {key} in French translations"
```

### 4. Project structure validation
Maintains project integrity:

```python
def test_project_directories_exist(self, project_root):
    required_dirs = ["app", "tests", "downloads"]
    for dir_name in required_dirs:
        assert (project_root / dir_name).exists(), f"Directory {dir_name} missing"
```
## 🔧 Configuration and tools

### Test environment variables
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
```

### Available pytest markers
- `@pytest.mark.unit`: Fast unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow tests (excluded by default)
- `@pytest.mark.external`: Tests requiring external services
- `@pytest.mark.stress`: Stress tests

### Smart filtering
```bash
# Only fast tests (development)
pytest -m "not slow and not external"

# Performance tests only
pytest -m "performance"

# All tests except stress tests
pytest -m "not stress"
```
pytest -m "performance"

# Tous sauf stress tests
pytest -m "not stress"
```

## 📚 Documentation

### Test documentation (`docs/testing.md`)
- Complete usage guide
- Command examples
- Current testing status
- Test architecture overview
- Available commands and tools

### Code comments
- Each test class documented
- Clear fixture explanations
- Comprehensive test descriptions

## 🚀 Daily usage

### Quick development testing
```bash
make test-fast    # Fast tests only (< 2 seconds)
make test         # All tests (< 5 seconds)
```

### Before committing
```bash
make test-all     # Complete test suite with coverage
```

### UV users (faster)
```bash
make uv-test      # Run tests with UV
make uv-test-fast # Fast tests with UV
```

### Debugging specific tests
```bash
pytest tests/test_core_functions.py::TestCoreFunctions::test_sanitize_filename -v -s
```

### Coverage reporting
```bash
make test-coverage  # Generate HTML coverage report in htmlcov/
```

## 🎉 Current test suite status

The HomeTube test suite provides:

- ✅ **Simplicity**: Focused on essential functionality without over-engineering
- ✅ **Reliability**: Robust Streamlit mocking prevents import conflicts
- ✅ **Speed**: Full test suite completes in under 5 seconds
- ✅ **Coverage**: Core functions, translations, and project structure tested
- ✅ **Maintainability**: Clear, simple tests easy to understand and extend
- ✅ **Automation**: Makefile commands for all testing scenarios
- ✅ **Integration**: Works with any Python environment (UV, conda, venv)
- ✅ **Documentation**: This comprehensive guide and inline comments

**Philosophy**: Quality over quantity - focus on testing what matters most with robust, maintainable tests. 🎯

---

## 🎬 End-to-End Testing with Real Downloads

### Overview
HomeTube includes comprehensive E2E tests that validate the complete download pipeline using real HomeTube functions.

### Available E2E Tests

#### 1. Fast E2E Test (Functions Only)
```bash
make test-e2e-functions
```
- Tests real HomeTube function integration
- Builds complete yt-dlp commands
- Validates configurations (cookies, SponsorBlock)
- **Fast execution** (~0.01s) - perfect for development

#### 2. Real Download E2E Test
```bash
make test-e2e-real-download
```
- **Actually downloads** a real YouTube video
- Uses real HomeTube functions end-to-end
- Tests complete pipeline with file operations
- **Takes time** (~17s) - comprehensive validation

#### 3. All Slow Tests
```bash
make test-slow
```
- Runs all tests marked with `@pytest.mark.slow`
- Includes both E2E tests above
- Perfect for comprehensive regression testing

### E2E Test Features

#### Real HomeTube Function Integration
The E2E tests use actual functions from `app.core`:
- `build_base_ytdlp_command()` - Command building with 28+ arguments
- `build_cookies_params()` - Cookie authentication
- `build_sponsorblock_params()` - Sponsor segment removal
- `sanitize_filename()` - Filename sanitization
- `video_id_from_url()` - URL parsing

#### Test Configuration
```python
# Real video used for testing
test_url = "https://www.youtube.com/watch?v=pXRviuL6vMY"
expected_title = "Stressed Out - Twenty One Pilots"

# Cookie priority order
cookies_priority = [
    "cookies/youtube_cookies.txt",
    "cookies/youtube_cookies-2025-09-29.txt", 
    "cookies/youtube_cookies-2025-09-27.txt"
]
```

#### Download Validation
The real download test validates:
- ✅ **Network connectivity** - Pings YouTube before attempting
- ✅ **Command building** - 40+ arguments from real HomeTube functions  
- ✅ **File download** - Actual video file downloaded
- ✅ **File size accuracy** - Tests the original file size bug fix
- ✅ **File operations** - Move, rename, cleanup operations
- ✅ **Error handling** - Timeout, network failures, cleanup on error

#### Output Locations
```bash
# Downloaded files for inspection
./tmp/tests/videos/     # Final video files
./tmp/tests/tmp/        # Temporary download location
```

#### Expected Results
```
🔧 Testing real HomeTube functions...
📝 Sanitized 'Stressed Out - Twenty One Pilots' -> 'Stressed Out - Twenty One Pilots'
🔗 Video ID extracted: pXRviuL6vMY
✅ Base command built with 28 arguments
🍪 Using cookies from: cookies/youtube_cookies.txt
📺 SponsorBlock config: 5 parameters
🎯 Final command built with 40 total arguments using real HomeTube functions!
📋 This is a vrai E2E test using real HomeTube code!
```

### Troubleshooting E2E Tests

#### No Network Connectivity
```bash
ping -c 1 youtube.com
```

#### Cookie Issues
```bash
ls -la cookies/
# Ensure valid cookie files exist
```

#### Test Exclusion from Fast Tests
E2E download tests are marked `@pytest.mark.slow`:
- ✅ `make test` - **Excludes** real download tests (fast development)
- ✅ `make test-all` - **Includes** all tests
- ✅ `make test-slow` - **Only** slow tests (E2E downloads)

This ensures fast development cycles while maintaining comprehensive testing capabilities.

### Integration with CI/CD
- **Fast tests** run on every commit (development workflow)
- **Slow E2E tests** run on releases/PRs (validation workflow)
- **Real download tests** validate against YouTube API changes