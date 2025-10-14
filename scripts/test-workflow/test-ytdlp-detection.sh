#!/bin/bash
set -euo pipefail

# Test script to validate the yt-dlp detection logic from the workflow
# This simulates the key steps including the new version comparison logic

echo "🧪 Testing yt-dlp version comparison workflow logic..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
BASE_IMAGE="jauderho/yt-dlp:latest"
REGISTRY="ghcr.io"
IMAGE_NAME="egalitarianmonkey/hometube"
TEST_MODE="${1:-dry-run}"  # dry-run or full-test

echo "📋 Configuration:"
echo "  Base Image: $BASE_IMAGE"
echo "  Target Registry: $REGISTRY"
echo "  Image Name: $IMAGE_NAME"
echo "  Test Mode: $TEST_MODE"
echo ""

# Step 1: Test yt-dlp version detection from base image
echo "🔍 Step 1: Testing yt-dlp version detection from base image..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    exit 1
fi

echo "  Pulling base image..."
if ! docker pull "$BASE_IMAGE" &> /dev/null; then
    echo -e "${RED}❌ Failed to pull base image: $BASE_IMAGE${NC}"
    exit 1
fi

echo "  Extracting yt-dlp version from base image..."
for attempt in {1..3}; do
    if new_version=$(docker run --rm "$BASE_IMAGE" yt-dlp --version 2>/dev/null | tr -d '\r\n'); then
        break
    else
        echo -e "${YELLOW}⚠️  Attempt $attempt failed, retrying...${NC}"
        sleep 2
    fi
done

if [[ -z "${new_version:-}" ]]; then
    echo -e "${RED}❌ Failed to get yt-dlp version after 3 attempts${NC}"
    exit 1
fi

# Validate version format (should be date-based like 2024.01.07)
if [[ ! "$new_version" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$ ]]; then
    echo -e "${YELLOW}⚠️  Warning: Unexpected version format: $new_version${NC}"
else
    echo -e "${GREEN}✅ Valid version format detected${NC}"
fi

echo -e "${GREEN}✅ New yt-dlp version available: $new_version${NC}"
echo ""

# Step 2: Test app version reading
echo "🔍 Step 2: Testing app version reading..."

if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ pyproject.toml not found in current directory${NC}"
    exit 1
fi

if ! python3 -c "import tomllib" 2>/dev/null; then
    echo -e "${RED}❌ Python tomllib module not available (Python 3.11+ required)${NC}"
    # Fallback test
    if python3 -c "import toml" 2>/dev/null; then
        app_version=$(python3 -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
        echo -e "${YELLOW}⚠️  Using toml module instead of tomllib${NC}"
    else
        echo -e "${RED}❌ No TOML parsing library available${NC}"
        exit 1
    fi
else
    app_version=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
print(data['project']['version'])
")
fi

if [[ -z "$app_version" ]]; then
    echo -e "${RED}❌ Failed to read app version${NC}"
    exit 1
fi

echo -e "${GREEN}✅ App version detected: $app_version${NC}"
echo ""

# Step 3: Test current yt-dlp version detection from HomeTube image
echo "🔍 Step 3: Testing current yt-dlp version detection from HomeTube image..."

LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
current_version=""

if [[ "$TEST_MODE" == "full-test" ]]; then
    echo "  Checking for existing HomeTube image..."
    
    if docker pull "$LATEST_TAG" >/dev/null 2>&1; then
        echo "  Found existing HomeTube image"
        
        echo "  Extracting current yt-dlp version from HomeTube image..."
        for attempt in {1..3}; do
            if current_version=$(docker run --rm "$LATEST_TAG" yt-dlp --version 2>/dev/null | tr -d '\r\n'); then
                break
            else
                echo -e "${YELLOW}⚠️  Attempt $attempt failed to get current version, retrying...${NC}"
                sleep 2
            fi
        done
        
        if [[ -n "$current_version" ]]; then
            echo -e "${GREEN}✅ Current yt-dlp version in HomeTube: $current_version${NC}"
        else
            echo -e "${YELLOW}⚠️  Failed to get current yt-dlp version${NC}"
        fi
    else
        echo -e "${YELLOW}📦 No existing HomeTube image found${NC}"
    fi
else
    echo "  (Simulated in dry-run mode - assuming existing version for demo)"
    # For demo purposes, let's simulate having the same version to show the skip logic
    current_version="$new_version"
    echo -e "${GREEN}✅ Simulated current version: $current_version${NC}"
fi

echo ""

# Step 4: Test build decision logic
echo "🔍 Step 4: Testing build decision logic..."

echo "  📈 New yt-dlp version available: $new_version"
echo "  📦 Current yt-dlp version in HomeTube: ${current_version:-none}"

should_build="false"
build_reason=""

if [[ -z "$current_version" ]]; then
    should_build="true"
    build_reason="No existing HomeTube image or version detection failed"
    echo -e "${GREEN}✅ Decision: BUILD NEEDED${NC}"
    echo "  Reason: $build_reason"
elif [[ "$new_version" != "$current_version" ]]; then
    should_build="true"
    build_reason="yt-dlp version update: $current_version → $new_version"
    echo -e "${GREEN}✅ Decision: BUILD NEEDED${NC}"
    echo "  Reason: $build_reason"
else
    should_build="false"
    build_reason="yt-dlp versions are identical ($current_version)"
    echo -e "${YELLOW}⏭️  Decision: SKIP BUILD${NC}"
    echo "  Reason: $build_reason"
fi

echo ""

# Step 5: Test tag generation (only if build is needed)
echo "🔍 Step 5: Testing tag generation..."

if [[ "$should_build" == "true" ]]; then
    BASE_NAME="${REGISTRY}/${IMAGE_NAME}"
    TAG_LATEST="${BASE_NAME}:latest"
    TAG_APP_VERSION="${BASE_NAME}:v${app_version}"
    TAG_YTDLP_VERSION="${BASE_NAME}:yt-dlp-${new_version}"
    TAG_COMBINED="${BASE_NAME}:v${app_version}-yt-dlp-${new_version}"

    echo "  Generated tags for build:"
    echo "    - $TAG_LATEST"
    echo "    - $TAG_APP_VERSION"
    echo "    - $TAG_YTDLP_VERSION"
    echo "    - $TAG_COMBINED"

    # Validate tag formats
    for tag in "$TAG_LATEST" "$TAG_APP_VERSION" "$TAG_YTDLP_VERSION" "$TAG_COMBINED"; do
        if [[ ! "$tag" =~ ^[a-z0-9._/-]+:[a-zA-Z0-9._-]+$ ]]; then
            echo -e "${RED}❌ Invalid tag format: $tag${NC}"
            exit 1
        fi
    done

    echo -e "${GREEN}✅ All tags have valid formats${NC}"
else
    echo -e "${YELLOW}⏭️  No tags generated (build skipped)${NC}"
fi

echo ""

# Summary
echo "🎉 Test Summary:"
echo -e "  ${GREEN}✅ New yt-dlp version detection: $new_version${NC}"
echo -e "  ${GREEN}✅ App version reading: $app_version${NC}"
echo -e "  ${GREEN}✅ Current version detection: ${current_version:-none}${NC}"

if [[ "$should_build" == "true" ]]; then
    echo -e "  ${GREEN}✅ Build decision: WILL BUILD${NC}"
    echo -e "  ${GREEN}✅ Reason: $build_reason${NC}"
    echo -e "  ${GREEN}✅ Tag generation: 4 tags ready${NC}"
else
    echo -e "  ${YELLOW}⏭️  Build decision: WILL SKIP${NC}"
    echo -e "  ${YELLOW}⏭️  Reason: $build_reason${NC}"
fi

echo ""
if [[ "$should_build" == "true" ]]; then
    echo -e "${GREEN}🎯 Workflow validation: PASSED - Build would be triggered${NC}"
else
    echo -e "${YELLOW}🎯 Workflow validation: PASSED - Build would be skipped (as expected)${NC}"
fi
echo "The improved workflow logic is working correctly!"