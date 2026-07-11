# Command Line

This document summarizes the current AKB commands. `akb` is the only Python CLI entry point; all operations are subcommands.

## Common Flow

Run AKB commands from the project root. Host and Docker runtime flows use the current project root as the work root:

1. `akb show-target`
2. `akb sync-source`
3. `akb build`

Docker image publishing is no longer handled by a Python `build-docker` command. Use `docker buildx build` directly with the Dockerfiles under `android_kernel_builder/docker/` and pass the selected target with `--build-arg TARGET=<target>`.

## Fixed Paths

- Target configs: `android_kernel_builder/configs/targets/<name>.toml`
- Local manifests: `android_kernel_builder/configs/manifests/`
- Source checkout: `source-code/<target>/`
- Cache root: `cache/<target>/`
- Output root: `out/<target>/`
- Docker metadata: `docker_datas/`

Path override CLI flags have been removed. Use `--target` or `AKB_TARGET` to select the target.

## Commands

### `akb show-target`

Prints the resolved target as JSON.

```bash
uv run akb show-target --target android15-6.6
```

### `akb sync-source`

Runs `repo init` and `repo sync` for the selected target.

```bash
uv run akb sync-source --target android15-6.6
```

After sync completes, the command prints the selected source root and direct source-root entry sizes, including both directories and files.

### `akb build`

Builds the configured kernel target and writes outputs under `out/<target>/<dist_dir>`.

```bash
uv run akb build --target android15-6.6
```

### `akb warmup-build`

Warms caches for the selected target. Kleaf targets use `build.kleaf.warmup_target` when configured.

```bash
uv run akb warmup-build --target android15-6.6
```

### `akb image-env`

Writes Docker runtime metadata files under `docker_datas/` for the selected target.

```bash
uv run akb image-env --target android15-6.6
```

### `akb usage`

Prints the current workspace disk usage report for the selected target. The target is resolved from `AKB_TARGET` or the only selectable target config in the current workspace.

```bash
uv run akb usage
```

### `akb cache init`

Mounts the Docker build cache overlay at `cache/<target>`.

```bash
uv run akb cache init
```

### `akb cache export`

Unmounts build cache mounts and exports `next-outer-cache.img/json`.

```bash
uv run akb cache export
```

### `akb snapshot`

Prunes a prepared workspace for snapshot-oriented image builds while preserving selected Git projects.

```bash
uv run akb snapshot --snapshot-git-projects common
```

### `akb tools add-git-safe`

Adds the input directory to both global and system `git safe.directory`.

```bash
uv run akb tools add-git-safe /path/to/workspace -r
```

## Docker Image Builds

Build a snapshot image:

```bash
docker buildx build \
  --allow security.insecure \
  -f android_kernel_builder/docker/snapshot.Dockerfile \
  --build-arg TARGET=android15-6.6 \
  --build-arg SNAPSHOT_GIT_PROJECTS=common \
  -t ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  .
```
