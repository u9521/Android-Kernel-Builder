# Container Environment Variables

This document describes the environment variables used or exported by the base and workspace images.

## Base Image

### `GKI_WORKSPACE_ROOT`

- Default: `/workspace`
- Used as the default working directory for the base image.
- Also used when the base image preconfigures Git `safe.directory` entries.

### `VIRTUAL_ENV`

- Default: `/opt/venv`
- Python virtual environment used by the image.

### `PATH`

- Includes `${VIRTUAL_ENV}/bin` and `/root/.local/bin`
- Makes the installed Python tooling and helper commands available by default.

## Workspace Image

The workspace image inherits `GKI_WORKSPACE_ROOT` from the base image and adds workspace-specific paths under that root.

### `GKI_BUILDER_ROOT`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/tooling`
- Location of the checked-in builder repository copied into the image.

### `GKI_CACHE_ROOT`

- Default: `${GKI_WORKSPACE_ROOT}/.cache`
- Reusable cache root used for repo reference data, Bazel cache, and ccache.

### `GKI_TARGET_CONFIG`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/image/target-config.toml`
- Resolved target config copied into the workspace image during build.

### `GKI_ENV_FILE`

- Default: `${GKI_WORKSPACE_ROOT}/.gki-builder/image/gki-builder.env`
- Shell fragment generated during workspace image build.
- Loaded by `docker/entrypoint.sh` when the container starts.

### `GKI_SOURCE_ROOT`

- Generated into `GKI_ENV_FILE`
- Points to the synced kernel source directory under `GKI_WORKSPACE_ROOT`.
- Example: `${GKI_WORKSPACE_ROOT}/android-kernel`

### `GKI_TARGET_NAME`

- Generated into `GKI_ENV_FILE`
- Mirrors the `name` field from the selected target config.

### `GKI_SNAPSHOT_GIT_PROJECTS`

- Used by snapshot images.
- Comma-separated list of repo projects preserved as standalone Git repositories after snapshot pruning.
- Default: `common`

## Output Paths

There is no default exported output-root environment variable.

- Downstream callers should choose the build output path explicitly with `gki-builder build --output-root ...`
- Snapshot images keep exported warmup artifacts under the output root used during image creation, usually `${GKI_WORKSPACE_ROOT}/out`
