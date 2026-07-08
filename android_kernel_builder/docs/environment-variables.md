# Container Environment Variables

Docker images run from `/workspace`. Commands must be run from the AKB project root; inside Docker, that root is `/workspace`. The entrypoint loads `/workspace/docker_datas/akb.env` when it exists.

## Runtime Variables

### `AKB_TARGET`

- Active target name embedded into the Docker image.

### `AKB_TARGET_NAME`

- Same target name as `AKB_TARGET`, exported for downstream build scripts.

### `AKB_SOURCE_ROOT`

- Synced kernel source root inside the container.
- Uses `source-code/<target>` under `/workspace`.

### `AKB_DOCKER_DATAS_ROOT`

- Docker metadata and cache image root.
- Default: `/workspace/docker_datas`.

### `AKB_TARGET_METADATA_ROOT`

- Per-target metadata directory.
- Default: `/workspace/docker_datas/targets/${AKB_TARGET}`.

## Build Metadata Variables

- `AKB_BUILD_SYSTEM`
- `AKB_BUILD_ARCH`
- `AKB_BUILD_TARGET`
- `AKB_WARMUP_TARGET`
- `AKB_DIST_DIR`
- `AKB_DIST_FLAG`

## Manifest Metadata Variables

- `AKB_MANIFEST_SOURCE`
- `AKB_MANIFEST_URL`
- `AKB_MANIFEST_BRANCH`
- `AKB_MANIFEST_FILE`
- `AKB_MANIFEST_PATH`

## Common Paths

- Source checkout: `/workspace/source-code/${AKB_TARGET}`
- Cache root: `/workspace/cache/${AKB_TARGET}`
- Output root: `/workspace/out/${AKB_TARGET}`
- Docker metadata: `/workspace/docker_datas`
