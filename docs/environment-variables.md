# Container Environment Variables

This document describes the runtime environment variables exported by Docker images.

Docker layout paths are fixed in code:

- work root: `/workspace`
- AKB runtime root: `/workspace/.akb`
- Docker runtime data root: `/workspace/docker_datas`
- cache root: `/workspace/.cache`
- default output root: `/workspace/out`

The entrypoint loads `/workspace/docker_datas/gki-builder.env` before executing the requested command.

## Runtime Variables

### `GKI_TARGET_NAME`

- Active target name from `/workspace/.akb/active-target.toml`.

### `GKI_SOURCE_ROOT`

- Synced kernel source root inside the container.
- Usually `/workspace/android-kernel`.

### `GKI_DOCKER_DATAS_ROOT`

- Fixed runtime data root for generated Docker metadata and cache images.
- Default: `/workspace/docker_datas`.

### `GKI_TARGET_METADATA_ROOT`

- Per-target metadata directory.
- Default: `/workspace/docker_datas/targets/${GKI_TARGET_NAME}`.

### `GKI_SOURCE_MODE`

- Runtime source mode.
- Current Docker images export `embedded`.

## Build Metadata Variables

These are exported so downstream CI scripts can inspect the active image target without parsing TOML.

### `GKI_BUILD_SYSTEM`

- Build system, for example `kleaf`.

### `GKI_BUILD_ARCH`

- Target architecture, for example `aarch64` or `x86_64`.

### `GKI_BUILD_TARGET`

- Main build target label or identifier.

### `GKI_WARMUP_TARGET`

- Warmup build target when configured.

### `GKI_DIST_DIR`

- Absolute distribution output directory under `/workspace/out` by default.

### `GKI_DIST_FLAG`

- Output flag used by the configured build flow.

## Manifest Metadata Variables

### `GKI_MANIFEST_SOURCE`

- `remote` or `local`.

### `GKI_MANIFEST_URL`

- Manifest repository URL.

### `GKI_MANIFEST_BRANCH`

- Manifest branch used by `repo init`.

### `GKI_MANIFEST_FILE`

- Remote manifest file name when configured.

### `GKI_MANIFEST_PATH`

- Absolute embedded local manifest path when configured.

## Other Common Image Variables

### `VIRTUAL_ENV`

- Default: `/opt/venv`

### `PATH`

- Includes `/opt/venv/bin` and `/usr/local/bin` so `gki-builder` and `repo` are available in login shells.
