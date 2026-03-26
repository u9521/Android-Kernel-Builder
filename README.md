# GKI Builder

This repository prepares reusable Android GKI workspaces for local builds and CI.

The main idea is:

1. Build a stable `gki-base` image with toolchains and build dependencies.
2. Build a `gki-workspace` image with synced kernel source plus warmed `repo`, `bazel`, and `ccache` state.
3. Let consumer repositories pull the workspace image, patch the source tree, and run an incremental Kleaf build.

## Layout

- `configs/targets/*.toml`: target definitions for GKI and AVD variants.
- `docker/`: base and workspace image definitions.
- `docs/`: configuration reference and manifest mode notes.
- `manifests/`: checked-in manifest snapshots.
- `src/gki_builder/`: CLI and orchestration code.
- `scripts/`: thin wrappers for common local workflows.
- `examples/consumer-github-actions.yml`: sample consumer CI job.

## Target Model

Each target config describes three things:

- where the manifest comes from
- how the kernel is built
- where source and caches live inside the reusable workspace

Example remote manifest target:

```toml
name = "android15-6.6"

[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
file = "default.xml"

[build]
system = "kleaf"
target = "//common:kernel_{arch}_dist"
arch = "aarch64"
```

Example local manifest target:

```toml
name = "avd-android15"

[manifest]
source = "local"
path = "../../manifests/avd/avd-android-15-6.6_arm64.xml"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
minimal = true
```

`source = "local"` means the checked-in XML is passed directly to `repo init -m`, which matches the old CI style more closely.

For remote targets that use `common-*` branches, workspace preparation also auto-detects
deprecated `kernel/common` branch names and rewrites the initialized manifest before sync when needed, but only when `autodetect_deprecated = true` is set for that target.

Kleaf builds in this repository rely on the kernel source tree's `tools/bazel`; the Docker images do not install a separate system `bazel` or `bazelisk` fallback.

Build targets must declare `build.system` explicitly as either `kleaf` or `legacy`

You can set `build.jobs` in a target file to control compile parallelism. If omitted, builds use the maximum available CPU threads.

When tuning `build.lto`, remember that LTO defaults are branch-specific. The Kleaf LTO guide notes that GKI `gki_defconfig` on `android14-6.1` and newer disables LTO by default. For development and iterative patching, `lto = "none"` is often the safer and faster choice, and it may also avoid incremental cache issues described in the upstream guide: `https://android.googlesource.com/kernel/build/+/refs/heads/master/kleaf/docs/lto.md`

## Local Usage

Install the package:

```bash
python3 -m pip install -e .
```

Create local directories:

```bash
gki-builder bootstrap \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
```

Prepare the source workspace:

```bash
gki-builder prepare-workspace \
  --target-config configs/targets/android15-6.6.toml \
  --workspace .workspace \
  --cache-root .cache
```

`prepare-workspace` defaults to the maximum available CPU threads. Use `--jobs` only when you want to cap sync parallelism manually.

Warm the cache with one build:

```bash
gki-builder build \
  --target-config configs/targets/android15-6.6.toml \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
```

## Docker Usage

Build the base image:

```bash
gki-builder docker-build-base --tag ghcr.io/<owner>/gki-base:bookworm
```

Build the workspace image:

```bash
gki-builder docker-build-workspace \
  --tag ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --base-image ghcr.io/<owner>/gki-base:bookworm \
  --target-config configs/targets/android15-6.6.toml
```

During workspace image build, the Dockerfile now runs `prepare-workspace` and one `gki-builder build` warmup pass so the published image already contains prepared source plus warmed compile caches.

The warmup build mainly helps Bazel and ccache reuse previous work. If a consumer repository only changes a small patch set, especially in a limited part of the kernel tree, more cached actions can be reused and rebuilds are usually much faster. Large patch sets, broad config changes, toolchain changes, or target changes will reduce cache hit rates and the speedup will be smaller.

The `build-workspace-image` GitHub Actions workflow expects only the target name, for example `android15-6.6`, and resolves it from `configs/targets/<name>.toml` automatically.

Workspace images export these key path variables:

- `GKI_BUILDER_ROOT`: repository tooling root, default `/opt/gki-builder`
- `GKI_TARGET_CONFIG`: resolved target config inside the image
- `GKI_WORKSPACE_ROOT`: synced workspace root, default `/workspace`
- `GKI_SOURCE_ROOT`: kernel source directory resolved from the target config
- `GKI_CACHE_ROOT`: reusable cache root, default `/cache`
- `GKI_OUTPUT_ROOT`: recommended output root, default `/out`

The workspace entrypoint also adds the current working directory, `GKI_WORKSPACE_ROOT`, `GKI_SOURCE_ROOT`, and `GKI_BUILDER_ROOT` to Git `safe.directory` so mounted workspaces do not fail with `dubious ownership` errors.

Run a command inside the workspace image:

```bash
gki-builder docker-run \
  --image ghcr.io/<owner>/gki-workspace:android15-6.6-latest \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out \
  -- bash -lc 'cd "$GKI_SOURCE_ROOT" && tools/bazel help'
```

## Publishing Strategy

Recommended image split:

- `ghcr.io/<owner>/gki-base:<toolchain-tag>`
- `ghcr.io/<owner>/gki-workspace:<target>-<manifest-or-date-tag>`

Keep tags stable enough that consumers can intentionally pin to a source baseline.

When a workspace image is produced, the CLI also writes target metadata under `.gki-builder/<target>/workspace.json` inside the workspace root. That makes it easier to inspect which manifest and cache layout the image was built from.

Because workspace images now perform one warmup build during image creation, expect workspace image builds to take longer than base image builds.

## Consumer CI Flow

1. pull the pre-warmed workspace image
2. apply project-specific patches inside `$GKI_SOURCE_ROOT`
3. run `gki-builder build` against the mounted workspace
4. collect artifacts from the mounted `$GKI_OUTPUT_ROOT`

See `examples/consumer-github-actions.yml` for a minimal pattern.

## Notes

- This project intentionally focuses on stock kernel source preparation and build reuse.
- Project-specific patching belongs in consumer repositories, not in the workspace image.
- Local manifests are first-class inputs so AVD or custom branch setups can be checked into the repo instead of discovered dynamically.

## Documentation

- `docs/configuration.md`: field-by-field target config reference
- `docs/manifest-modes.md`: remote and local init-manifest behavior

## License

This project is licensed under `GPL-3.0-only`. See `LICENSE`.
