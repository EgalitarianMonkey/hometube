# Automatic yt-dlp Updates

HomeTube includes an automated workflow that rebuilds Docker images when new versions of yt-dlp are released, ensuring you always have access to the latest video download capabilities.

## How It Works

The workflow (`refresh-ytdlp.yml`) automatically:

1. **Daily Checks**: Runs every day at 06:00 UTC to check for new yt-dlp versions
2. **Version Detection**: Pulls the latest `jauderho/yt-dlp:latest` image and extracts the yt-dlp version
3. **Smart Building**: Only rebuilds if a new yt-dlp version is detected (unless forced)
4. **Multi-Architecture**: Builds for both `linux/amd64` and `linux/arm64` platforms
5. **Comprehensive Tagging**: Creates multiple tags for easy version management
6. **Verification**: Tests the built image to ensure yt-dlp works correctly

## Docker Tags Generated

For each build, the following tags are created:

- `latest` - Always points to the most recent build
- `v{app-version}` - Tagged with HomeTube app version (e.g., `v1.2.3`)
- `yt-dlp-{ytdlp-version}` - Tagged with yt-dlp version (e.g., `yt-dlp-2024.01.07`)
- `v{app-version}-yt-dlp-{ytdlp-version}` - Combined tag for full traceability

## Manual Triggering

You can manually trigger the workflow from GitHub Actions with options:

- **Force Rebuild**: Rebuild even if the yt-dlp version already exists
- **Custom Platforms**: Specify different target architectures

## Configuration

### Environment Variables

- `REGISTRY`: Container registry (default: `ghcr.io`)
- `IMAGE_NAME`: Image name (default: `egalitarianmonkey/hometube`)
- `BASE_IMAGE`: Base yt-dlp image (default: `jauderho/yt-dlp:latest`)

### Notification Setup

The workflow supports optional Slack notifications. To enable:

1. Add a `SLACK_WEBHOOK_URL` repository variable
2. Uncomment the Slack notification step in the workflow

### Cache Optimization

The workflow uses multiple caching strategies:

- **GitHub Actions Cache**: Caches Docker build layers between runs
- **Registry Cache**: Pushes cache layers to the container registry
- **BuildKit Inline Cache**: Optimizes layer reuse

## Monitoring

### GitHub Actions

- Check the **Actions** tab in your repository for workflow runs
- Each run provides detailed logs and build summaries
- Failed builds include error details and troubleshooting information

### Build Verification

The workflow includes automatic verification:

- Tests that yt-dlp is functional in the built image
- Verifies the correct yt-dlp version is installed
- Validates Python dependencies and Streamlit imports

### Notifications

Build results are available in:

- GitHub Actions summary page
- Optional Slack notifications (if configured)
- Repository commit status checks

## Troubleshooting

### Common Issues

**Build Fails Due to Base Image Issues**:

- The workflow retries failed base image pulls
- Check if `jauderho/yt-dlp:latest` is accessible
- Verify network connectivity in GitHub Actions

**Version Detection Problems**:

- Workflow validates version format (YYYY.MM.DD)
- Logs warnings for unexpected version formats
- Check base image compatibility

**Multi-Architecture Build Issues**:

- Default platforms: `linux/amd64,linux/arm64`
- Can be customized via manual workflow dispatch
- ARM64 builds may take longer due to emulation

### Manual Intervention

If the automatic workflow fails consistently:

1. Check the base image status: `docker pull jauderho/yt-dlp:latest`
2. Manually trigger with force rebuild option
3. Review GitHub Actions logs for specific error details
4. Consider temporarily using single architecture builds

## Security Considerations

- Uses `GITHUB_TOKEN` for registry authentication
- Only pushes to authenticated registries
- Validates image contents before publishing
- Base image digest pinning available for reproducibility

## Performance Notes

- **Build Time**: Typically 15-30 minutes for multi-arch builds
- **Frequency**: Daily checks minimize unnecessary rebuilds
- **Resource Usage**: Optimized caching reduces build times
- **Storage**: Old images should be cleaned up periodically

This automated system ensures HomeTube users always have access to the latest yt-dlp capabilities without manual intervention.
