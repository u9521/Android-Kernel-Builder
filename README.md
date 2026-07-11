# Android Kernel Builder

This repository prepares reusable Android GKI build environments for host workflows and CI-focused Docker images.

Current direction:

- host and Docker commands use the current project root as the work root
- source, cache, and output paths are derived from target name
- Docker images are one-image-one-target and set `AKB_TARGET` for default builds

## Repository Layout

- `android_kernel_builder/builder/`: CLI and orchestration code
- `android_kernel_builder/configs/targets/*.toml`: checked-in target definitions
- `android_kernel_builder/configs/manifests/**`: checked-in local manifest snapshots
- `android_kernel_builder/docker/`: image definitions
- `android_kernel_builder/docs/`: reference docs
- `android_kernel_builder/docs/examples/consumer-github-actions.yml`: sample downstream CI usage

## Setup / Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install editable package with dev dependencies
uv sync --dev

# Run CLI
uv run akb --help

# Run tests
uv run python -m unittest discover -s android_kernel_builder/tests
```

## Host Layout

Run AKB commands from the project root. Host and Docker commands use the current project root as the work root with this layout:

```text
{work}/
├── android_kernel_builder/
├── source-code/<target>/
├── cache/<target>/
└── out/
```

Commands derive paths from the selected target and the current directory. Use `--target` or set `AKB_TARGET`.

## Commands

Show the resolved target:

```bash
uv run akb show-target --target android15-6.6
```

Sync source for a host target:

```bash
uv run akb sync-source --target android15-6.6
```

After `repo sync` completes, the command prints the selected source root and the size of each direct file or directory under it.

Build a host target:

```bash
uv run akb build --target android15-6.6
```

Build the base image:

```bash
docker buildx build \
  -f android_kernel_builder/docker/base.Dockerfile \
  -t ghcr.io/<owner>/gki-base:bookworm \
  .
```

Build a one-image-one-target workspace image:

```bash
docker buildx build \
  --allow security.insecure \
  -f android_kernel_builder/docker/workspace.Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/<owner>/gki-base:bookworm \
  --build-arg TARGET=android15-6.6 \
  -t ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  .
```

During final image cleanup, this removes everything under `/workspace/source-code/<target>/common` except `.git`, removes warmup outputs and cache contents, then prints the final workspace disk usage report.

Build and push the workspace image directly without loading it into the local Docker image store:

```bash
docker buildx build \
  --allow security.insecure \
  -f android_kernel_builder/docker/workspace.Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/<owner>/gki-base:bookworm \
  --build-arg TARGET=android15-6.6 \
  -t ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --push \
  .
```

Build a one-image-one-target snapshot image:

```bash
docker buildx build \
  --allow security.insecure \
  -f android_kernel_builder/docker/snapshot.Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/<owner>/gki-base:bookworm \
  --build-arg TARGET=android15-6.6 \
  --build-arg SNAPSHOT_GIT_PROJECTS=common \
  -t ghcr.io/<owner>/gki-snapshot:android15-6.6-latest \
  .
```

Snapshot images apply the same final cleanup and disk usage report after preserving the requested Git projects.

Print the current workspace disk usage report:

```bash
uv run akb usage
```

Run a built image:

```bash
docker run --rm -it \
  --privileged \
  ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  -- bash -lc 'cd "$AKB_SOURCE_ROOT" && tools/bazel help'
```

Recommended downstream CI build cache flow inside the container:

```bash
bash -lc '
  set -euo pipefail
  trap "uv run akb cache export || true" EXIT
  uv run akb cache init
  uv run akb build
'
```

Add directories to global Git safe.directory:

```bash
uv run akb tools add-git-safe /path/to/workspace -r
```

This command updates both global and system `safe.directory` scopes.

## Docker Behavior

- Docker runtime commands run from `/workspace`, matching the same project-root layout used on host.
- Docker image builds use the checked-in target configs directly and select the target with the Docker build arg `TARGET`.
- The base Dockerfile delegates package installation to `android_kernel_builder/docker/install-base-deps.sh`.
- The entrypoint loads `/workspace/docker_datas/akb.env`.
- That env file exports target, build, and manifest metadata for downstream CI scripts.
- Workspace images run `uv run akb sync-source`, create a sparse `container_cache.img`, mount it on `/workspace/cache/<target>`, then run `uv run akb warmup-build` during image build and remove warmup outputs before the final image layer completes.
- Workspace and snapshot images remove every direct entry under `/workspace/source-code/<target>/common` except `.git` before the final image layer completes, reducing retained source checkout size while keeping the project Git history available.
- Workspace and snapshot images run `uv run akb usage` after final cleanup so build logs include the final retained workspace disk usage.
- `warmup-build` exports warmup outputs to `<output-root>/<dist_dir>` when `build.kleaf.warmup_target` is configured.
- Snapshot images run snapshot pruning before `uv run akb warmup-build`, preserving selected Git projects while removing `.repo` metadata.
- After snapshot pruning removes `.repo`, downstream flows should use Git commands inside preserved project directories instead of `repo` commands.
- Docker image publishing uses `docker buildx build --push`, which avoids loading large images into the local Docker image store.
- The image build no longer consumes external build caches. It always creates the base `container_cache.img` inside the image build, then shrinks it with `resize2fs -M`.
- Build cache uses overlay mounts: image-baked `container_cache.img` is the lower read-only cache, and external `outer-cache.img` is the writable delta image.
- The entrypoint does not manage cache mounts or exports; downstream CI should explicitly run `uv run cache init` and guarantee `uv run cache export` runs with a shell `trap` or equivalent cleanup step.
- In CI, prefer running the container as `root` with enough mount capability, typically `--privileged`, because build cache setup requires loop mounts and overlayfs.
- The GitHub Actions publishing flow builds workspace and snapshot images in a matrix, with each image built on its own runner from the same base image and target definition, and optionally pushed to GHCR.

## Notes

- Kleaf builds rely on the kernel tree's `tools/bazel`.
- Docker images are intended for CI/runtime use, not as full AKB development checkouts.
- Local manifest support remains first-class through checked-in configs under `android_kernel_builder/configs/manifests/`.

## Documentation

- `android_kernel_builder/docs/configuration.md`
- `android_kernel_builder/docs/environment-variables.md`
- `android_kernel_builder/docs/faq.md`
- `android_kernel_builder/docs/akb-cli.md`
- `android_kernel_builder/docs/image-files.md`
- `android_kernel_builder/docs/manifest-modes.md`

## License

This project is licensed under `GPL-3.0-only`. See `LICENSE`.
