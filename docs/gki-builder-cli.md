# gki-builder CLI

This document summarizes the main `gki-builder` commands and when to use them.

## Common Flow

Typical local usage:

1. `bootstrap`
2. `prepare-workspace`
3. `build`

Typical workspace-image flow:

1. `docker-build-base`
2. `docker-build-workspace`
3. `docker-run`

Typical snapshot-image flow:

1. `docker-build-base`
2. `docker-build-snapshot`
3. `docker-run`

## Commands

### `show-target`

- Loads a target config and prints the resolved config as JSON.
- Useful for checking manifest paths, cache directories, and build settings after path resolution.

Example:

```bash
gki-builder show-target --target-config configs/targets/android15-6.6.toml
```

### `bootstrap`

- Creates local workspace, cache, and output directories.
- Does not sync source or build anything.

Example:

```bash
gki-builder bootstrap \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
```

### `prepare-workspace`

- Runs `repo init` and `repo sync` for the selected target.
- Writes workspace metadata under `<workspace>/.gki-builder/<target>/workspace.json`.

Example:

```bash
gki-builder prepare-workspace \
  --target-config configs/targets/android15-6.6.toml \
  --workspace .workspace \
  --cache-root .cache
```

### `build`

- Performs the normal kernel build for the configured target.
- For `kleaf`, this runs the configured `build.target`.
- Writes build outputs under `<output-root>/<dist_dir>`.
- Prints disk usage analysis and writes `<workspace>/.gki-builder/<target>/disk-usage.json`.

Example:

```bash
gki-builder build \
  --target-config configs/targets/android15-6.6.toml \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
```

### `warmup-build`

- Warms build caches for image creation or local reuse.
- If `build.warmup_target` is set for a `kleaf` target, this runs `bazel build <warmup_target>`.
- Exports the warmup target's default output files to `<output-root>/<dist_dir>` so downstream users can reuse kernel-only artifacts without building ramdisk or dist packaging.
- Writes `<workspace>/.gki-builder/<target>/warmup-outputs.json` with the exported file list.
- Otherwise, it falls back to the normal `build` behavior.
- Useful when the normal build target also creates ramdisk, boot, or partition images and you want a lighter warmup step.

Example:

```bash
gki-builder warmup-build \
  --target-config configs/targets/avd-android16-6.12-x64.toml \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
```

### `docker-build-base`

- Builds the minimal base image used by workspace images.

Example:

```bash
gki-builder docker-build-base --tag ghcr.io/<owner>/gki-base:bookworm
```

### `docker-build-workspace`

- Builds a pre-warmed workspace image on top of the base image.
- During image creation, it prepares the source tree and runs `warmup-build`.
- Installs `gki-builder` into `/usr/local/bin` as well as the virtualenv so login-shell workflows can still find it in `PATH`.

Example:

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target-config configs/targets/android15-6.6.toml
```

### `docker-build-snapshot`

- Builds a snapshot-oriented image on top of the base image.
- During image creation, it prepares the source tree, runs `warmup-build`, exports warmup artifacts, then removes `.repo` metadata.
- Preserves selected repo projects as standalone Git repositories so downstream patch workflows can still commit changes.
- Defaults to preserving `common`.
- Snapshot images are intended for Git operations inside the preserved project directories, not for `repo` commands.
- Installs `gki-builder` into `/usr/local/bin` as well as the virtualenv so login-shell workflows can still find it in `PATH`.

Example:

```bash
gki-builder docker-build-snapshot \
  --tag ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target-config configs/targets/android15-6.6.toml \
  --snapshot-git-projects common
```

### `docker-run`

- Runs a built workspace image with local workspace, cache, and output directories mounted in.
- If no command is provided, it opens an interactive shell.

Example:

```bash
gki-builder docker-run \
  --image ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out \
  -- bash -lc 'cd "$GKI_SOURCE_ROOT" && tools/bazel help'
```

## Important Inputs

### `--target-config`

- Used by `show-target`, `prepare-workspace`, `build`, `warmup-build`, and `docker-build-workspace`.
- Points to a target file under `configs/targets/` or a custom config file.

### `--snapshot-git-projects`

- Used by `docker-build-snapshot`.
- Comma-separated list of repo projects to preserve as standalone Git repositories inside the snapshot image.
- Default: `common`

### `--workspace`

- Root directory for synced source and workspace metadata.

### `--cache-root`

- Root directory for reusable repo, Bazel, and ccache data.

### `--output-root`

- Root directory for build results.
- Final outputs are written under `<output-root>/<dist_dir>` for normal builds.

## Related Docs

- `docs/configuration.md`
- `docs/environment-variables.md`
- `docs/image-files.md`
- `docs/manifest-modes.md`
