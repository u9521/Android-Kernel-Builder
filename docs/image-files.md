# Common Files In Container Images

This document describes the common files and paths that appear in the base and workspace images.

## Base Image

### `${GKI_WORKSPACE_ROOT}`

- Default: `/workspace`
- Default working directory for the base image.
- Parent location for the workspace image contents.

### `/usr/local/bin/repo`

- The downloaded `repo` launcher.
- Installed by the base image so `repo init` and `repo sync` can run later.

### `${VIRTUAL_ENV}`

- Default: `/opt/venv`
- Python virtual environment used by the image.

## Workspace Image

### `${GKI_BUILDER_ROOT}`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/tooling`
- Copy of this repository inside the image.
- Contains the checked-in Python package, Docker scripts, configs, and helper files.

### `${GKI_TARGET_CONFIG}`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/image/target-config.toml`
- Target config copied into the image during `docker-build-workspace`.
- Used by downstream `gki-builder build` invocations inside the container.

### `${GKI_ENV_FILE}`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/image/gki-builder.env`
- Generated shell fragment loaded by `docker/entrypoint.sh`.
- Exports image-derived values such as `GKI_TARGET_NAME` and `GKI_SOURCE_ROOT`.

### `/usr/local/bin/gki-workspace-entrypoint`

- Installed entrypoint script for the workspace image.
- Sources `${GKI_ENV_FILE}` and then executes the requested command.

### `${GKI_SOURCE_ROOT}`

- Usually something like `${GKI_WORKSPACE_ROOT}/android-kernel`
- Synced Android kernel source tree created by `prepare-workspace`.

### `${GKI_CACHE_ROOT}`

- Default: `${GKI_WORKSPACE_ROOT}/.cache`
- Root directory for reusable build caches.

### `${GKI_CACHE_ROOT}/repo`

- Repo reference cache.
- Reused across syncs to reduce network and checkout cost.

### `${GKI_CACHE_ROOT}/bazel`

- Bazel disk cache.
- Reused across Kleaf builds.

### `${GKI_CACHE_ROOT}/ccache`

- C/C++ compiler cache.
- Reused across compatible rebuilds.

### `${GKI_WORKSPACE_ROOT}/.gki-builder/<target>/workspace.json`

- Metadata written after `prepare-workspace`.
- Records manifest details, selected target, cache layout, and related workspace information.

### `${GKI_WORKSPACE_ROOT}/.gki-builder/<target>/disk-usage.json`

- Metadata written after `gki-builder build`.
- Records measured disk usage for source, repo metadata, caches, outputs, and workspace metadata.

### `${GKI_WORKSPACE_ROOT}/.gki-builder/<target>/warmup-outputs.json`

- Metadata written after `gki-builder warmup-build` when a `warmup_target` is used.
- Records the warmup target and the exported file list copied under the chosen output root.

## Downstream Files

The workspace image does not reserve a fixed path for downstream patch repositories, but the recommended pattern is to mount them under a subdirectory of `${GKI_WORKSPACE_ROOT}`.

Example:

- `${GKI_WORKSPACE_ROOT}/downstream/patches/my-change.patch`
