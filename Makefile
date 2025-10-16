# Makefile for HomeTube testing and development
# Supports both UV (fast) and standard Python (universal) workflows

.PHONY: help install test test-unit test-integration test-performance test-coverage clean lint format type-check dev-setup docker-build docker-up docker-down docker-logs docker-test

# Default target
help:
	@echo "🏠 HomeTube Development Commands"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  docker-build     - Build image with auto-detected yt-dlp version"
	@echo "  docker-up        - Start containers (builds if needed)"
	@echo "  docker-down      - Stop and remove containers"
	@echo "  docker-logs      - Follow container logs"
	@echo "  docker-test      - Build and verify labels"
	@echo ""
	@echo "📦 Setup:"
	@echo "  install          - Install dependencies (universal)"
	@echo "  dev-setup        - Setup development environment"
	@echo "  uv-sync          - Sync with UV (fast, for UV users)"
	@echo "  sync-deps        - Sync all dependency files from pyproject.toml"
	@echo "  update-deps      - Update all dependencies and sync files (uses script)"
	@echo "  update-reqs      - Run update-requirements.sh script directly"
	@echo ""
	@echo "🧪 Testing (universal - works with any Python environment):"
	@echo "  test             - Run fast tests (recommended for development)"
	@echo "  test-fast-with-e2e - Run fast tests + E2E functions test (recommended)"
	@echo "  test-all         - Run all tests including slow ones"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-slow        - Run slow tests (includes real download E2E)"
	@echo "  test-with-network - Run tests requiring crane (for local dev)"
	@echo "  test-e2e-functions - Run E2E test with real HomeTube functions (fast, no download)"
	@echo "  test-e2e-real-download    - Run REAL download E2E test (slow, downloads actual video)"
	@echo "  test-performance - Run performance tests"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo ""
	@echo "⚡ UV Commands (faster, requires UV):"
	@echo "  uv-test          - Run fast tests with UV"
	@echo "  uv-test-all      - Run all tests with UV"
	@echo "  uv-lint          - Run linting with UV"
	@echo ""
	@echo "🛠️ Code Quality:"
	@echo "  format           - Format code with black"
	@echo "  fix              - Automatically fix formatting and style issues"
	@echo "  lint             - Check code style (without fixing)"
	@echo "  clean            - Clean test artifacts"
	@echo ""
	@echo "⚙️ Configuration:"
	@echo "  config-check     - Check .env configuration and display summary"

# === UNIVERSAL SETUP COMMANDS ===
# Install dependencies (works with conda, venv, etc.)
install:
	python -m pip install -r requirements/requirements.txt
	python -m pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist

# Setup development environment
dev-setup: install
	python -m pip install black flake8 watchdog
	@echo "✅ Development environment ready!"
	@echo "Run 'make test' to run tests"

# UV-specific sync (fast)
uv-sync:
	uv sync
	@echo "✅ UV environment synced!"

# Sync all dependency files from pyproject.toml (UV as source of truth)
sync-deps:
	@echo "🔄 Syncing dependency files from pyproject.toml..."
	
	# Ensure requirements directory exists
	mkdir -p requirements
	
	# Generate requirements.txt from pyproject.toml (production dependencies)
	uv pip compile pyproject.toml -o requirements/requirements.txt
	@echo "📦 Updated requirements/requirements.txt"
	
	# Generate requirements-dev.txt from pyproject.toml (with dev dependencies)
	uv pip compile pyproject.toml --extra dev -o requirements/requirements-dev.txt
	@echo "🛠️ Updated requirements/requirements-dev.txt"
	
	# Note: environment.yml needs manual sync when adding system deps
	@echo "⚠️  Don't forget to manually update environment.yml if you added system dependencies"
	@echo "✅ Dependency files synced!"

# Update all dependencies and sync files
update-deps:
	@echo "⬆️ Updating all dependencies..."
	./scripts/update-requirements.sh

# Run update-requirements.sh script directly
update-reqs:
	./scripts/update-requirements.sh
# === UNIVERSAL TESTING COMMANDS (work with any Python environment) ===
# Run basic tests (fast, no network)
test:
	python -m pytest tests/ -v --tb=short -m "not slow and not external and not network"

# Run fast tests including E2E functions test
test-fast-with-e2e:
	@echo "🧪 Running fast tests + E2E functions test..."
	python -m pytest tests/ -v --tb=short -m "not slow and not external"
	@echo ""
	@echo "🔧 Running E2E functions test (fast)..."
	python -m pytest tests/test_end_to_end.py::TestEndToEndDownload::test_real_hometube_functions -v --tb=short

# Run all tests including slow ones
test-all:
	python -m pytest tests/ -v --tb=short

# Run tests with network access (requires crane for version detection tests)
test-with-network:
	@echo "🌐 Running tests with network access (requires crane)..."
	@if ! command -v crane >/dev/null 2>&1; then \
		echo "⚠️  crane not found - network tests will be skipped"; \
		echo "💡 Install crane: brew install crane (macOS)"; \
	fi
	python -m pytest tests/ -v --tb=short -m "not slow and not external"

# Run unit tests only (specific test files)
test-unit:
	python -m pytest tests/test_core_functions.py tests/test_translations.py tests/test_utils.py -v -m "not slow and not external and not network"

# Run integration tests only 
test-integration:
	python -m pytest tests/test_integration.py -v --tb=short

# Run E2E test with real HomeTube functions (fast - no actual download)
test-e2e-functions:
	@echo "🔧 Running E2E test with real HomeTube functions (fast)..."
	@echo "📋 Tests command building with real HomeTube code"
	python -m pytest tests/test_end_to_end.py::TestEndToEndDownload::test_real_hometube_functions -v -s --tb=short

# Run the REAL YouTube download E2E test (slow - actual download)
test-e2e-real-download:
	@echo "🎬 Running REAL YouTube download E2E test..."
	@echo "⚠️  This will ACTUALLY download a real video and may take several minutes"
	@echo "🌐 Requires internet connection to YouTube"
	@echo "🔧 Uses real HomeTube functions + real download for complete E2E testing"
	python -m pytest tests/test_end_to_end.py::TestEndToEndDownload::test_real_youtube_download_with_actual_download -v -s --tb=short

# Run only slow tests (like the real E2E download test)
test-slow:
	python -m pytest tests/ -v --tb=short -m "slow"

# Run performance tests
test-performance:
	python -m pytest tests/test_performance.py -v -m "performance"

# Run tests with coverage report
test-coverage:
	python -m pytest tests/ --cov=app.utils --cov=app.translations --cov-report=html --cov-report=term-missing --cov-fail-under=70

# === UV-SPECIFIC COMMANDS (faster, for UV users) ===
# Run tests with UV (faster)
uv-test:
	uv run pytest tests/ -v --tb=short -m "not slow and not external"

# Run all tests with UV
uv-test-all:
	uv run pytest tests/ -v --tb=short

# Run linting with UV
uv-lint:
	uv run black app/ tests/
	uv run flake8 app/ tests/

# === UNIVERSAL CODE QUALITY COMMANDS ===
# Format code (fixes most issues automatically)
format:
	python -m black app/ tests/
	@echo "✅ Code formatting completed"

# Lint code (check without fixing)
# Code quality checks (without fixing)
lint:
	python -m black --check app/ tests/
	python -m ruff check app/ tests/
	@echo "✅ Linting completed"

# Fix code formatting and style issues automatically
fix:
	python -m black app/ tests/
	@echo "✅ Code automatically formatted with black"
	@echo "💡 Run 'make lint' to check for remaining issues"

# === UTILITY COMMANDS ===

# === UTILITY COMMANDS ===
# Clean test artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "🧹 Cleaned test artifacts"

# Run tests in watch mode (requires pytest-watch)
test-watch:
	python -m pip install pytest-watch
	ptw tests/ -- -v

# Run specific test file
test-file:
	@read -p "Enter test file (e.g., test_core_functions): " file; \
	python -m pytest tests/$$file.py -v

# Run tests matching a pattern
test-pattern:
	@read -p "Enter test pattern (e.g., test_sanitize): " pattern; \
	python -m pytest tests/ -k "$$pattern" -v

# Run only failed tests from last run
test-failed:
	python -m pytest tests/ --lf -v

# === WORKFLOW COMMANDS ===
# Run pre-commit checks (universal)
pre-commit: clean format lint test
	@echo "✅ Pre-commit checks completed successfully!"

# Quick development workflow
dev-test: clean test-unit
	@echo "✅ Quick development tests completed"

# Full CI workflow (matches GitHub Actions)
ci: clean lint test-coverage
	@echo "✅ Full CI workflow completed"

# Debug failing test
debug-test:
	@read -p "Enter test function (e.g., test_sanitize_filename): " test; \
	python -m pytest tests/ -k "$$test" -v -s --pdb

# Show environment info
env-info:
	@echo "🐍 Python version: $$(python --version)"
	@echo "📦 Pip version: $$(python -m pip --version)"

# Check .env configuration and display summary
config-check:
	@echo "🔧 Checking HomeTube configuration..."
	@if [ ! -f .env ]; then \
		echo "⚠️  No .env file found. Creating from .env.sample..."; \
		cp .env.sample .env 2>/dev/null || echo "❌ .env.sample not found!"; \
	fi
	@echo ""
	DEBUG=1 python -c "import app.main" 2>/dev/null | grep -E "🔧|📁|🍪|🔤|✅|⚠️|❌" || echo "✅ Configuration loaded successfully"
	@echo ""
	@echo "💡 Tips:"
	@echo "   • Edit .env to customize paths and authentication"
	@echo "   • Set YOUTUBE_COOKIES_FILE_PATH for private videos"
	@echo "   • Use COOKIES_FROM_BROWSER for browser authentication"
	@echo "🧪 Pytest version: $$(python -m pytest --version 2>/dev/null || echo 'Not installed')"
	@echo "⚡ UV version: $$(uv --version 2>/dev/null || echo 'Not installed')"
	@echo "🏠 Current directory: $$(pwd)"

# === DOCKER COMMANDS ===
# Helper: Detect yt-dlp version (exported for docker-compose)
define detect_ytdlp_version
	$(eval YTDLP_VERSION := $(shell \
		if command -v crane >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then \
			crane config jauderho/yt-dlp:latest 2>/dev/null | jq -r '.config.Labels["org.opencontainers.image.version"] // empty' 2>/dev/null || echo ""; \
		fi \
	))
	$(if $(YTDLP_VERSION), \
		$(info ✅ Detected yt-dlp version: $(YTDLP_VERSION)), \
		$(info ⚠️  Could not detect yt-dlp version (crane/jq not found or failed)) \
		$(if $(shell command -v crane 2>/dev/null),, $(info 💡 Install crane: brew install crane)) \
	)
endef

# Build with auto-detected yt-dlp version
docker-build:
	@echo "🔍 Detecting yt-dlp version..."
	@$(call detect_ytdlp_version)
	@YTDLP_VERSION="$(YTDLP_VERSION)" docker-compose build

# Start services with build
docker-up:
	@echo "🚀 Starting HomeTube..."
	@$(call detect_ytdlp_version)
	@YTDLP_VERSION="$(YTDLP_VERSION)" docker-compose up --build -d
	@echo "✅ HomeTube started at http://localhost:8501"

# Stop services
docker-down:
	@echo "🛑 Stopping HomeTube..."
	@docker-compose down

# View logs
docker-logs:
	@docker-compose logs -f

# Build and verify labels
docker-test: docker-build
	@echo ""
	@echo "🔍 Verifying image labels..."
	@IMAGE_NAME=$$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "hometube.*:latest" | head -1); \
	if [ -n "$$IMAGE_NAME" ]; then \
		echo "� Image: $$IMAGE_NAME"; \
		echo ""; \
		echo "📋 Labels:"; \
		docker inspect $$IMAGE_NAME --format '{{ json .Config.Labels }}' | jq '{ \
			"app.version": .["org.opencontainers.image.version"], \
			"ytdlp.version": .["io.hometube.ytdlp.version"], \
			"build.trigger": .["io.hometube.build.trigger"], \
			"created": .["org.opencontainers.image.created"] \
		}'; \
		echo ""; \
		echo "🔍 yt-dlp version in container:"; \
		docker run --rm $$IMAGE_NAME yt-dlp --version || echo "⚠️  Could not verify"; \
	else \
		echo "❌ No hometube image found"; \
	fi