# 🚢 Release Process

How HomeTube versions are cut, built, and announced.

## Versioning

HomeTube follows semantic versioning:

- **Patch** (`2.9.1 → 2.9.2`) — bug fixes only. Note: the in-app "New version available!" notification only triggers for major/minor updates, so patch releases are silent for running instances.
- **Minor** (`2.9.x → 2.10.0`) — new features or user-visible behavior changes. Triggers the in-app update notification.
- **Major** (`2.x → 3.0.0`) — breaking changes (configuration, volumes, defaults).

## Step by step

1. **Bump the version** in all files at once:

   ```bash
   make version-update 2.10.0
   ```

   This updates `pyproject.toml` and `app/__init__.py`.

2. **Open a PR** and merge it into `main`. The branch prefix drives the release-notes category (`fix/…` → 🐛 Fixes, `feat/…` → 🚀 Features, see `.github/labeler.yml`).

3. **Tag the merge commit on `main`** (not the branch commit), then push the tag:

   ```bash
   git switch main && git pull
   git tag v2.10.0
   git push origin v2.10.0
   ```

4. **CI takes over** (`.github/workflows/release.yml`): tests + lint, multi-arch Docker build pushed to GHCR, then a **draft release** is created with auto-generated notes (merged PRs grouped by category, per `.github/release.yml`).

5. **Curate and publish.** Open the draft on GitHub, rewrite the notes — a short intro on what the release means for users, keep the generated PR list below — then click **Publish release**.

## Why a draft?

- Watchers subscribed to releases receive the notification email **at publish time, with the curated text**. Editing after publishing does not re-send it — polish first, publish second.
- The draft only exists once tests and the Docker build have succeeded, so a published release always matches a working image.
- Drafts are invisible to the public until published.
