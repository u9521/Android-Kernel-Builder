# GKI Builder

This repository prepares reusable Android GKI build environments for host workflows and CI-focused Docker images.

Current direction:

- host mode uses a fixed AKB work-tree layout rooted at `{work}/.akb`
- docker mode uses a fixed runtime layout rooted at `/workspace`
- Docker images are one-image-one-target and embed a single active target config

## Repository Layout

- `configs/global.toml`: repository-wide snapshot-image defaults
- `configs/targets/*.toml`: checked-in source target definitions used when building Docker images from the repo
- `configs/manifests/**`: checked-in local manifest snapshots (see `configs/manifests/common/README.md`)
- `docker/`: image definitions
- `docs/`: reference docs
- `src/gki_builder/`: CLI and orchestration code
- `examples/consumer-github-actions.yml`: sample downstream CI usage

## Host Layout

Host mode is converging on this fixed layout:

```text
{work}/
├── .akb/
│   ├── config.toml
│   ├── targets/
│   │   ├── configs/
│   │   └── manifests/
│   └── venv/ or bin/
├── targets -> .akb/targets
├── .cache/
└── out/
```

Commands assume the current directory is inside an initialized AKB work tree.

Initialize one from a Linux host directory:

```bash
curl -fsSL https://raw.githubusercontent.com/u9521/Android-Kernel-Builder/refs/heads/master/install.sh | bash
```

When run from this repository checkout, `install.sh` seeds `.akb/targets/configs` and `.akb/targets/manifests` from the checked-in `configs/targets` and `configs/manifests` trees, creates `targets -> .akb/targets`, writes `.akb/config.toml`, and creates `.akb/bin`.

## Host Install

Run the installer from the directory you want to use as the AKB work root:

```bash
mkdir work
cd work
bash /path/to/Android-Kernel-Builder/install.sh
```

The script currently:

- supports Linux hosts only
- requires `python3`
- creates `.akb/config.toml`, `.akb/targets/configs`, `.akb/targets/manifests`, `.akb/bin`, `.cache`, and `out`
- creates `targets -> .akb/targets`
- appends `.akb/bin/` and `.akb/venv/` to `.gitignore`
- does not overwrite an existing `.akb/config.toml` or existing seeded target files

If the installer can see this repository checkout, it also copies the checked-in host seed data:

- `configs/targets/*.toml` -> `.akb/targets/configs/*.toml`
- `configs/manifests/**` -> `.akb/targets/manifests/**`

Supported installer environment variables:

- `AKB_DEFAULT_TARGET`: overrides the generated `.akb/config.toml` `default_target`
- `AKB_SOURCE_DIR`: overrides the generated host source directory name; default `android-kernel`
- `AKB_CACHE_DIR`: overrides the generated host cache directory name; default `.cache`
- `AKB_OUTPUT_DIR`: overrides the generated host output directory name; default `out`

Example:

```bash
AKB_DEFAULT_TARGET=avd-android15-6.6-x64 \
AKB_SOURCE_DIR=src/android-kernel \
bash /path/to/Android-Kernel-Builder/install.sh
```

After install, the normal host flow is:

```bash
gki-builder show-target
gki-builder sync-source
gki-builder build
```

## Docker Layout

Docker runtime uses fixed paths:

```text
/workspace/
├── .akb/
│   ├── active-target.toml
│   └── manifests/
├── docker_metadata/
│   └── gki-builder.env
├── .cache/
├── out/
└── android-kernel/
```

The final image keeps only the minimal runtime payload needed for CI use. It does not keep a full AKB repository checkout.

## Commands

Show the resolved target:

```bash
gki-builder show-target --target android15-6.6
```

Sync source for a host target:

```bash
gki-builder sync-source --target android15-6.6
```

Build a host target:

```bash
gki-builder build --target android15-6.6 --output-root out
```

Build the base image:

```bash
gki-builder docker-build-base --tag ghcr.io/<owner>/gki-base:bookworm
```

Build a one-image-one-target workspace image:

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6
```

Build and push the workspace image directly without loading it into the local Docker image store:

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6 \
  --push
```

Seed the packaged image context with a restored runtime cache:

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6 \
  --runtime-cache-root .image-build-cache/workspace-android15-6.6 \
  --push
```

Build a one-image-one-target snapshot image:

```bash
gki-builder docker-build-snapshot \
  --tag ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target android15-6.6 \
  --snapshot-git-projects common
```

Run a built image:

```bash
gki-builder docker-run \
  --image ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --workspace work \
  --output-root out \
  -- bash -lc 'cd "$GKI_SOURCE_ROOT" && tools/bazel help'
```

Add directories to global Git safe.directory:

```bash
gki-builder add-git-safe /path/to/workspace -r
```

This command updates both global and system `safe.directory` scopes.

## Docker Behavior

- Docker runtime paths are fixed in code; they are no longer configured by Docker path env vars.
- Docker image packaging generates `.docker-target/target.toml` as a flattened single-target config for the selected image build; when that target uses a local manifest, the referenced file is bundled as `.docker-target/manifest.xml` and `manifest.path` is rewritten to match.
- The entrypoint loads `/workspace/docker_metadata/gki-builder.env`.
- That env file exports target, build, and manifest metadata for downstream CI scripts.
- Workspace images run `gki-builder sync-source` and `gki-builder warmup-build` during image build.
- `warmup-build` exports warmup outputs to `<output-root>/<dist_dir>` when `build.warmup_target` is configured.
- Snapshot images run snapshot pruning before `gki-builder warmup-build`, preserving selected Git projects while removing `.repo` metadata.
- After snapshot pruning removes `.repo`, downstream flows should use Git commands inside preserved project directories instead of `repo` commands.
- `docker-build-base`, `docker-build-workspace`, and `docker-build-snapshot` accept `--push` to use `docker buildx build --push`, which avoids loading large images into the local Docker image store.
- `gki-builder-cache-sync` is installed into Docker images. It replaces `/workspace/.cache` with a symlink to a mounted host cache only when that host cache already has content, otherwise it keeps using the image cache. During `prepare`, it changes the mounted cache ownership to match the image's existing `/workspace/.cache` owner before the build; if the container lacks `CAP_CHOWN`, it fails fast.
- During image builds, `gki-builder-cache-sync save` materializes `/workspace/.cache` back into the image filesystem, so downstream CI gets a prewarmed image cache on the first run even when the build consumed a mounted `cache-host` context.
- In CI, prefer running the container as `root`. Running as another user can make host-mounted cache ownership harder to reconcile during restore, especially for `ccache` and Bazel caches, and `gki-builder-cache-sync prepare` will fail if the container lacks `CAP_CHOWN`.
- The GitHub Actions publishing flow builds workspace and snapshot images in a matrix, with each image built and pushed on its own runner from the same base image and target definition.
- The workspace and snapshot image publishing workflow restores a repository-side runtime cache with `actions/cache`, then calls `gki-builder docker-build-workspace --push` or `gki-builder docker-build-snapshot --push` with `--runtime-cache-root` so the restored cache is passed as a named BuildKit context and consumed by `gki-builder-cache-sync prepare` / `gki-builder-cache-sync save` during the image build without creating an extra host-side cache copy.

## Notes

- Kleaf builds rely on the kernel tree's `tools/bazel`.
- Docker images are intended for CI/runtime use, not as full AKB development checkouts.
- Local manifest support remains first-class, but embedded Docker manifests must stay inside the image manifest root.

## Documentation

- `docs/configuration.md`
- `docs/environment-variables.md`
- `docs/gki-builder-cli.md`
- `docs/image-files.md`
- `docs/manifest-modes.md`

## License

This project is licensed under `GPL-3.0-only`. See `LICENSE`.
