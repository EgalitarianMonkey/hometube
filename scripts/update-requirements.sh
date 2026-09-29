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
echo "📝 Generating requirements.txt..."
uv pip compile pyproject.toml --upgrade -o requirements/requirements.txt

# Regenerate requirements-dev.txt
echo "🛠️ Generating requirements-dev.txt..."
uv pip compile pyproject.toml --extra dev --upgrade -o requirements/requirements-dev.txt

echo "✅ Requirements files updated!"
echo ""
echo "📋 Generated files:"
echo "  - requirements/requirements.txt (production)"
echo "  - requirements/requirements-dev.txt (development)"
echo "  - uv.lock (lockfile)"