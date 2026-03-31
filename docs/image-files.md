# Common Files In Container Images

This document describes the main fixed paths used by Docker images.

## Fixed Roots

### `/workspace`

- Fixed container work root.

### `/workspace/.akb`

- Minimal AKB runtime payload.
- Does not contain the full source repository.

### `/workspace/docker_datas`

- Docker-only metadata root.

### `/workspace/.cache`

- Runtime overlay mountpoint.
- Image builds temporarily mount `container_cache.img` here during warmup.

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

### `/workspace/docker_datas/gki-builder.env`

- Generated shell fragment loaded by `docker/entrypoint.sh`.
- Exports target, build, and manifest metadata for downstream CI scripts.

### `/workspace/docker_datas/image.json`

- Generated runtime image metadata.
- Records target name, cache layout version, and fixed Docker runtime paths.

### `/workspace/docker_datas/container_cache.img`

- Image-baked read-only base cache image.
- Created during image build by mounting a sparse ext4 image on `/workspace/.cache`, warming it, then shrinking it.

### `/workspace/docker_datas/container_cache.json`

- Metadata for `container_cache.img`.
- Stores `container_cache_sha256` used to validate external overlay deltas.

### `/workspace/docker_datas/outerimage/outer-cache.img`

- External writable delta cache image used at runtime as overlay `upperdir` and `workdir`.

### `/workspace/docker_datas/outerimage/outer-cache.json`

- Metadata for `outer-cache.img`.
- Must match the embedded `container_cache_sha256` to be reused.

### `/workspace/docker_datas/outerimage/next-outer-cache.img`

- Exported runtime delta image produced after a container run.
- Shrunk with `resize2fs -M` before export.

### `/workspace/docker_datas/outerimage/next-outer-cache.json`

- Metadata written alongside `next-outer-cache.img`.

### `/workspace/docker_datas/.overlays/`

- Temporary mount roots used by runtime cache setup.
- Holds the loop-mounted lower image, loop-mounted upper image, and merged overlay state.

### `/usr/local/bin/gki-workspace-entrypoint`

- Image entrypoint helper.
- Sources `/workspace/docker_datas/gki-builder.env`, initializes runtime cache mounts, and then runs the requested command.

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

### `/workspace/.cache/bazel/state`

- Bazel local state directory.
- Passed as `--output_base`.

### `/workspace/.cache/bazel/repo`

- Bazel repository cache.
- Passed as `--repository_cache`.

### `/workspace/.cache/bazel/diskcache`

- Bazel disk cache.
- Passed as `--disk_cache`.

### `/workspace/.cache/bazel/kleaf-out`

- Kleaf persistent local output cache.
- Passed as `--config=local --cache_dir`.

### `/workspace/.cache/ccache`

- Compiler cache.

### `/workspace/.cache/.ccache-tools/clang`

- Stable ccache masquerade symlink used by legacy builds.
- Keeps the `CC` compiler path unchanged across runs so `ccache` can reuse cached results.

## Target Metadata

### `/workspace/docker_datas/targets/<target>/workspace.json`

- Metadata written after `gki-builder sync-source`.

### `/workspace/docker_datas/targets/<target>/disk-usage.json`

- Metadata written after `gki-builder build` or `gki-builder warmup-build`.

### `/workspace/docker_datas/targets/<target>/warmup-outputs.json`

- Metadata written after `gki-builder warmup-build` when a warmup target is configured.

### `/workspace/docker_datas/targets/<target>/snapshot.json`

- Metadata written by snapshot image generation.

## CI Packaging Notes

- The CI workflow builds workspace and snapshot images as separate matrix jobs.
- Both images use the same base image and embedded target definition.
- The snapshot image is built directly from its own Dockerfile, so `.repo` cleanup happens within the snapshot image build instead of by repackaging a prepared workspace.
