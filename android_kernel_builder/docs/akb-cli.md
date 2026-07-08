# Command Line

This document summarizes the current AKB commands. `akb` is a command index; build, Docker, cache, and tool operations use separate console scripts.

## Common Flow

Run AKB commands from the project root. Host and Docker runtime flows use the current project root as the work root:

1. `show-target`
2. `sync-source`
3. `build`

Docker image publishing flow:

1. `build-docker build-base`
2. `build-docker build-workspace` or `build-docker build-snapshot`
3. `build-docker run`

## Fixed Paths

- Target configs: `android_kernel_builder/configs/targets/<name>.toml`
- Local manifests: `android_kernel_builder/configs/manifests/`
- Source checkout: `source-code/<target>/`
- Cache root: `cache/<target>/`
- Output root: `out/<target>/`
- Docker metadata: `docker_datas/`

Path override CLI flags have been removed. Use `--target` or `AKB_TARGET` to select the target.

## Commands

### `show-target`

Prints the resolved target as JSON.

```bash
uv run show-target --target android15-6.6
```

### `sync-source`

Runs `repo init` and `repo sync` for the selected target.

```bash
uv run sync-source --target android15-6.6
```

### `build`

Builds the configured kernel target and writes outputs under `out/<target>/<dist_dir>`.

```bash
uv run build --target android15-6.6
```

### `warmup-build`

Warms caches for the selected target. Kleaf targets use `build.warmup_target` when configured.

```bash
uv run warmup-build --target android15-6.6
```

### `build-docker build-base`

Builds the minimal base image used by workspace and snapshot images.

```bash
uv run build-docker build-base --tag ghcr.io/<owner>/gki-base:bookworm
```

### `build-docker build-workspace`

Builds a pre-warmed one-image-one-target CI image.

```bash
uv run build-docker build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6
```

### `build-docker build-snapshot`

Builds a snapshot-oriented one-image-one-target CI image.

```bash
uv run build-docker build-snapshot \
  --tag ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6 \
  --snapshot-git-projects common
```

### `build-docker run`

Runs an existing image with fixed `source-code`, `cache`, `out`, and `docker_datas/outerimage` mounts.

```bash
uv run build-docker run \
  --image ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  -- bash -lc 'cd "$AKB_SOURCE_ROOT" && tools/bazel help'
```

### `cache init`

Mounts the Docker build cache overlay at `cache/<target>`.

```bash
uv run cache init
```

### `cache export`

Unmounts build cache mounts and exports `next-outer-cache.img/json`.

```bash
uv run cache export
```

### `tools add-git-safe`

Adds the input directory to both global and system `git safe.directory`.

```bash
uv run tools add-git-safe /path/to/workspace -r
```
