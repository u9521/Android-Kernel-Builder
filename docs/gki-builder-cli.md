# gki-builder CLI

This document summarizes the current `gki-builder` commands.

## Common Flow

Host environment flow:

0. `install.sh`
1. `show-target`
2. `sync-source`
3. `build`

Docker image flow:

1. `docker-build-base`
2. `docker-build-workspace` or `docker-build-snapshot`
3. `docker-run`

## Commands

### `show-target`

- Prints the resolved target as JSON.
- Host mode: uses `--target` or `.akb/config.toml` `default_target`.
- Docker mode: uses `/workspace/.akb/active-target.toml`.

Example:

```bash
gki-builder show-target --target android15-6.6
```

### `sync-source`

- Runs `repo init` and `repo sync` for the selected target.
- Writes workspace metadata under `<work-root>/<metadata-dir>/<target>/workspace.json`.

Example:

```bash
gki-builder sync-source --target android15-6.6
```

### `build`

- Builds the configured kernel target.
- Writes outputs under `<output-root>/<dist_dir>`.
- Writes disk usage metadata under `<metadata-dir>/<target>/disk-usage.json`.

Example:

```bash
gki-builder build --target android15-6.6 --output-root out
```

### `warmup-build`

- Warms caches for the selected target.
- Uses `build.warmup_target` when configured for Kleaf targets.
- Exports warmup target output files to `<output-root>/<dist_dir>`.
- Falls back to normal `build` behavior when warmup is not configured.
- Writes warmup metadata under `<metadata-dir>/<target>/warmup-outputs.json`.

Example:

```bash
gki-builder warmup-build --target android15-6.6 --output-root out
```

### `docker-build-base`

- Builds the minimal base image used by workspace and snapshot images.

```bash
gki-builder docker-build-base --tag ghcr.io/<owner>/gki-base:bookworm
```

### `docker-build-workspace`

- Builds a pre-warmed one-image-one-target CI image.
- Embeds one `active-target.toml` and only the manifest files needed by that target.
- The final image contains a stripped runtime payload, not the full AKB repository checkout.
- During packaging, the selected target is flattened (inheritance resolved) and written as an auto-generated `.docker-target/target.toml` with inheritance-chain comments.

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6
```

### `docker-build-snapshot`

- Builds a snapshot-oriented one-image-one-target CI image.
- Runs warmup, then removes `.repo` metadata while preserving selected Git projects.
- Uses the same flattened auto-generated `.docker-target/target.toml` flow as `docker-build-workspace`.

```bash
gki-builder docker-build-snapshot \
  --tag ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6 \
  --snapshot-git-projects common
```

### `docker-run`

- Runs an existing image with host workspace, cache, and output directories mounted into `/workspace`, `/workspace/.cache`, and `/workspace/out`.
- If no command is provided, starts `bash` in the container.

```bash
gki-builder docker-run \
  --image ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --workspace work \
  --output-root out \
  -- bash -lc 'cd "$GKI_SOURCE_ROOT" && tools/bazel help'
```

### `add-git-safe`

- Adds the input directory to both global and system `git safe.directory`.
- With `-r`/`--recursive`, scans child directories and adds each detected Git repository directory.
- Prints added entries and skipped already-configured entries for both scopes.

```bash
gki-builder add-git-safe /path/to/workspace -r
```

## Important Inputs

### `--target`

- Used by `show-target`, `sync-source`, `build`, `warmup-build`, `docker-build-workspace`, and `docker-build-snapshot`.
- Host mode resolves it from `.akb/targets/configs/<name>.toml`.
- Host mode rejects targets with `base = true` (inheritance-only configs).
- Docker runtime commands ignore it and use the embedded active target by default.

### `--snapshot-git-projects`

- Used by `docker-build-snapshot`.
- Comma-separated repo projects to preserve as standalone Git repositories.
- Default: `common`.

### `--workspace`

- Used by `docker-run`.
- Host directory mounted to `/workspace` in the container.
- Default: `work`.

### `--cache-root`

- Optional cache-root override.
- Host mode defaults to `.akb/config.toml` `workspace.cache_dir`.
- `docker-run` defaults to `<workspace>/.cache`.

### `--output-root`

- Optional output-root override.
- Host mode defaults to `.akb/config.toml` `workspace.output_dir`.
- `docker-run` defaults to `<workspace>/out`.

### `--jobs`

- Used by `sync-source`.
- Controls `repo sync` parallelism.
- Default: maximum available CPU threads.

### `-r` / `--recursive`

- Used by `add-git-safe`.
- Recursively scans subdirectories and adds only directories that are Git repositories.
