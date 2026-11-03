#!/bin/bash
# Script to update all requirements files

echo "🔄 Updating dependencies with UV..."

# Update the lockfile
echo "📦 Updating lockfile..."
uv lock --upgrade

# Regenerate production requirements.txt
# --upgrade is required: without it, uv reads the existing output file and keeps
# every version already pinned there, so this script reports success while
# changing nothing. That is how blinker (no longer a streamlit dependency) and a
# stale uvicorn survived in these files for months.
#
# --universal resolves for every platform and writes the differences as
# environment markers. Without it uv resolves for the machine running this
# script: compiled on macOS, the files dropped watchdog, which streamlit
# requires everywhere but Darwin.
#
# --python-version is required for the same reason, one axis over: --universal
# resolves for every Python version at or above the *interpreter running uv*,
# not every version pyproject.toml allows. Run on a 3.12 machine it pins
# numpy==2.5.4 unconditionally — a release that does not exist for 3.11 — so
# the file becomes uninstallable on the floor requires-python declares and CI
# pins. With the floor passed explicitly the fork reappears as a marker pair.
# It must stay equal to requires-python's lower bound in pyproject.toml;
# tests/test_requirements_contract.py fails if the two drift apart.
echo "📝 Generating requirements.txt..."
uv pip compile pyproject.toml --universal --python-version 3.11 --upgrade -o requirements/requirements.txt

# Regenerate requirements-dev.txt
#
# --extra test alongside --extra dev: the test tooling (pytest and its plugins)
# lives in its own extra, so with --extra dev alone this file carried black,
# ruff and watchdog and no pytest at all. docs/contributing.md hands a
# contributor `pip install -r requirements/requirements-dev.txt` and then
# `make test` under the heading "Verify setup", which failed on a clean venv
# with ModuleNotFoundError. CI never caught it: it installs -e ".[test,dev]"
# and never reads these files.
echo "🛠️ Generating requirements-dev.txt..."
uv pip compile pyproject.toml --extra dev --extra test --universal --python-version 3.11 --upgrade -o requirements/requirements-dev.txt

echo "✅ Requirements files updated!"
echo ""
echo "📋 Generated files:"
echo "  - requirements/requirements.txt (production)"
echo "  - requirements/requirements-dev.txt (development)"
echo "  - uv.lock (lockfile)"