# GKI Builder

This repository prepares reusable Android GKI build environments for host workflows and CI-focused Docker images.

Current direction:

- host mode uses a fixed AKB work-tree layout rooted at `{work}/.akb`
- docker mode uses a fixed runtime layout rooted at `/workspace`
- Docker images are one-image-one-target and embed a single active target config

## Repository Layout

- `configs/global.toml`: repository-wide snapshot-image defaults
- `configs/targets/*.toml`: checked-in source target definitions used when building Docker images from the repo
- `docker/`: image definitions
- `docs/`: reference docs
- `manifests/`: checked-in source manifests
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

When run from this repository checkout, `install.sh` seeds `.akb/targets/configs` and `.akb/targets/manifests` from the checked-in `configs/targets` and `manifests` trees, creates `targets -> .akb/targets`, writes `.akb/config.toml`, and creates `.akb/bin`.

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
- `manifests/**` -> `.akb/targets/manifests/**`

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

## Docker Behavior

- Docker runtime paths are fixed in code; they are no longer configured by Docker path env vars.
- The entrypoint loads `/workspace/docker_metadata/gki-builder.env`.
- That env file exports target, build, and manifest metadata for downstream CI scripts.
- Workspace images run `gki-builder sync-source` and `gki-builder warmup-build` during image build.
- Snapshot images additionally prune `.repo` while preserving selected Git projects.
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
