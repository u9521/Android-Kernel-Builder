# Common Files In Container Images

This document describes the main fixed paths used by Docker images.

## Fixed Roots

### `/workspace`

- Fixed container work root.

### `/workspace/.akb`

- Minimal AKB runtime payload.
- Does not contain the full source repository.

### `/workspace/docker_metadata`

- Docker-only metadata root.

### `/workspace/.cache`

- Reusable cache root.

### `/workspace/out`

- Common output root used by image warmup and downstream CI.

## Runtime Config Files

### `/usr/local/bin/repo`

- Repo launcher installed in the base image.
- Used by `gki-builder sync-source` for `repo init` and `repo sync`.

### `/workspace/.akb/active-target.toml`

- The single active target embedded into the image.
- Runtime `gki-builder` commands read this by default inside Docker.

### `/workspace/.akb/manifests/`

- Embedded manifest directory.
- Contains only the manifest files needed by the selected image target.

### `/workspace/docker_metadata/gki-builder.env`

- Generated shell fragment loaded by `docker/entrypoint.sh`.
- Exports target, build, and manifest metadata for downstream CI scripts.

### `/usr/local/bin/gki-workspace-entrypoint`

- Image entrypoint helper.
- Sources `/workspace/docker_metadata/gki-builder.env` and then runs the requested command.

### `/usr/local/bin/gki-builder`

- CLI entry point installed in workspace and snapshot images.
- Mirrors the virtualenv binary so login-shell workflows can still call `gki-builder`.

## Source Tree

### `${GKI_SOURCE_ROOT}`

- Usually `/workspace/android-kernel`.
- Created by `gki-builder sync-source` during image build.

## Cache Layout

### `/workspace/.cache/repo`

- Repo reference cache.

### `/workspace/.cache/bazel`

- Bazel disk cache.

### `/workspace/.cache/ccache`

- Compiler cache.

### `/workspace/.cache/.ccache-tools/clang`

- Stable ccache masquerade symlink used by legacy builds.
- Keeps the `CC` compiler path unchanged across runs so `ccache` can reuse cached results.

## Target Metadata

### `/workspace/docker_metadata/targets/<target>/workspace.json`

- Metadata written after `gki-builder sync-source`.

### `/workspace/docker_metadata/targets/<target>/disk-usage.json`

- Metadata written after `gki-builder build` or `gki-builder warmup-build`.

### `/workspace/docker_metadata/targets/<target>/warmup-outputs.json`

- Metadata written after `gki-builder warmup-build` when a warmup target is configured.

### `/workspace/docker_metadata/targets/<target>/snapshot.json`

- Metadata written by snapshot image generation.

## CI Packaging Notes

- The CI workflow builds workspace and snapshot images as separate matrix jobs.
- Both images use the same base image and embedded target definition.
- The snapshot image is built directly from its own Dockerfile, so `.repo` cleanup happens within the snapshot image build instead of by repackaging a prepared workspace.
