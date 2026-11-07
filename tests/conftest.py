"""
Simplified and robust pytest configuration.
"""

import pytest
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

# === MOCK STREAMLIT AT IMPORT TIME ===
# Ensure streamlit is not already loaded
if "streamlit" in sys.modules:
    del sys.modules["streamlit"]

# Create a complete mock
mock_st = MagicMock()

# Simple session_state mock that accepts everything
mock_session_state = MagicMock()
mock_session_state.__contains__ = MagicMock(return_value=False)
mock_st.session_state = mock_session_state

# Mock main functions
mock_st.title = MagicMock(return_value=None)
mock_st.write = MagicMock(return_value=None)
mock_st.text_input = MagicMock(return_value="")
mock_st.button = MagicMock(return_value=False)
mock_st.selectbox = MagicMock(return_value="")
mock_st.checkbox = MagicMock(return_value=False)
mock_st.error = MagicMock(return_value=None)
mock_st.success = MagicMock(return_value=None)
mock_st.warning = MagicMock(return_value=None)
mock_st.info = MagicMock(return_value=None)
mock_st.empty = MagicMock()
mock_st.container = MagicMock()
# FIX: st.columns must return exactly 2 columns
mock_col1, mock_col2 = MagicMock(), MagicMock()
mock_st.columns = MagicMock(return_value=[mock_col1, mock_col2])
mock_st.set_page_config = MagicMock(return_value=None)
mock_st.markdown = MagicMock(return_value=None)

# Install the mock IMMEDIATELY
sys.modules["streamlit"] = mock_st


# === EXTERNAL TOOL AVAILABILITY ===
# `external` means "this test drives a real external tool"; pyproject declares it
# as "Tests requiring external tools (yt-dlp, ffmpeg, etc.)". The tools are not
# Python dependencies of a dev install: yt-dlp sits in the `local` extra, so
# `uv sync`, requirements.txt and requirements-dev.txt all omit the binary on
# purpose, and no documented setup path installs it.
#
# A marker only deselects, it does not skip. CI and `make test-ci` pass
# `-m "not external"`, but `make test` does not -- and that is the command
# docs/contributing.md names both for "Verify setup" and in the PR checklist. So
# a contributor on a clean checkout saw these tests *fail*, and the failure read
# as a code regression (`assert 0 >= 1`) rather than as a missing tool, because
# the code under test catches the OSError and returns an empty list.
#
# A tool the project never asked you to install is not a regression: skip.
EXTERNAL_TOOLS = ("yt-dlp",)


def pytest_runtest_setup(item):
    """Skip `external` tests when the tools they drive are not on PATH."""
    if item.get_closest_marker("external") is None:
        return
    missing = [tool for tool in EXTERNAL_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"requires external tool(s) not on PATH: {', '.join(missing)}")


def pytest_configure(config):
    """Global test configuration."""
    print("\n🧪 Starting HomeTube tests (simplified version)")


def pytest_unconfigure(config):
    """Cleanup after tests."""
    print("\n✅ Tests completed")


@pytest.fixture(scope="session")
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def temp_dir(tmp_path_factory):
    """Temporary directory for tests."""
    return tmp_path_factory.mktemp("hometube_tests")


@pytest.fixture
def mock_streamlit():
    """Simple and robust Streamlit mock."""
    return sys.modules.get("streamlit", MagicMock())
