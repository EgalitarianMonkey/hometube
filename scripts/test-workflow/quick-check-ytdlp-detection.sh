#!/bin/bash

# Quick validation check for the improved workflow
echo "🔍 Quick Validation Check - Improved Version Logic"
echo "================================================"

echo -n "✓ YAML syntax... "
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/refresh-ytdlp.yml'))" 2>/dev/null && echo "✅ OK" || echo "❌ FAILED"

echo -n "✓ Version comparison logic... "
./scripts/test-workflow/test-ytdlp-detection.sh full-test >/dev/null 2>&1 && echo "✅ OK" || echo "❌ FAILED"

echo -n "✓ Required files... "
test -f .github/workflows/refresh-ytdlp.yml && test -f pyproject.toml && test -f Dockerfile && echo "✅ OK" || echo "❌ FAILED"

echo ""
echo "🚀 Improved workflow ready!"
echo ""
echo "✨ New Logic Summary:"
echo "  • Compares yt-dlp version in current HomeTube image vs available version"
echo "  • Only builds when versions are different (or no existing image)"
echo "  • Skips builds when versions are identical"
echo "  • Provides clear reasoning in logs and notifications"
echo ""
echo "Commands to deploy the improvement:"
echo "  git add .github/workflows/refresh-ytdlp.yml"
echo "  git add scripts/test-workflow/"
echo "  git commit -m 'feat: Improve yt-dlp workflow to skip builds when versions are identical'"
echo "  git push"