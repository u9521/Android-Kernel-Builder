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
├── docker_datas/
│   ├── gki-builder.env
│   ├── image.json
│   ├── container_cache.img
│   ├── container_cache.json
│   ├── outerimage/
│   └── .overlays/
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

Recommended downstream CI runtime cache flow inside the container:

```bash
bash -lc '
  set -euo pipefail
  trap "gki-builder runtime-cache-export || true" EXIT
  gki-builder runtime-cache-init
  cd "$GKI_SOURCE_ROOT"
  gki-builder build --output-root /workspace/out
'
```

Add directories to global Git safe.directory:

```bash
gki-builder add-git-safe /path/to/workspace -r
```

This command updates both global and system `safe.directory` scopes.

## Docker Behavior

- Docker runtime paths are fixed in code; they are no longer configured by Docker path env vars.
- Docker image packaging generates `.docker-target/target.toml` as a flattened single-target config for the selected image build; when that target uses a local manifest, the referenced file is bundled as `.docker-target/manifest.xml` and `manifest.path` is rewritten to match.
- The entrypoint loads `/workspace/docker_datas/gki-builder.env`.
- That env file exports target, build, and manifest metadata for downstream CI scripts.
- Workspace images run `gki-builder sync-source`, create a sparse `container_cache.img`, mount it on `/workspace/.cache`, then run `gki-builder warmup-build` during image build.
- `warmup-build` exports warmup outputs to `<output-root>/<dist_dir>` when `build.warmup_target` is configured.
- Snapshot images run snapshot pruning before `gki-builder warmup-build`, preserving selected Git projects while removing `.repo` metadata.
- After snapshot pruning removes `.repo`, downstream flows should use Git commands inside preserved project directories instead of `repo` commands.
- `docker-build-base`, `docker-build-workspace`, and `docker-build-snapshot` accept `--push` to use `docker buildx build --push`, which avoids loading large images into the local Docker image store.
- The image build no longer consumes external build caches. It always creates the base `container_cache.img` inside the image build, then shrinks it with `resize2fs -M`.
- Runtime cache uses overlay mounts: image-baked `container_cache.img` is the lower read-only cache, and external `outer-cache.img` is the writable delta image.
- The entrypoint does not manage cache mounts or exports; downstream CI should explicitly run `gki-builder runtime-cache-init` and guarantee `gki-builder runtime-cache-export` runs with a shell `trap` or equivalent cleanup step.
- In CI, prefer running the container as `root` with enough mount capability, typically `--privileged`, because runtime cache setup requires loop mounts and overlayfs.
- The GitHub Actions publishing flow builds workspace and snapshot images in a matrix, with each image built and pushed on its own runner from the same base image and target definition.

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
