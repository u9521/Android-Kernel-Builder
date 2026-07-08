# Common Files In Container Images

This document describes the main fixed paths used by Docker images.

## Fixed Roots

### `/workspace`

- Fixed container work root.
- Contains the installed project checkout, source tree, cache root, output root, and Docker metadata.

### `/workspace/android_kernel_builder`

- AKB package, configs, docs, Dockerfiles, and scripts copied into the image.

### `/workspace/source-code/<target>`

- Synced kernel source tree.
- Created by `uv run sync-source` during image build.

### `/workspace/cache/<target>`

- Target cache root.
- Image builds temporarily mount `container_cache.img` here during warmup.

### `/workspace/out/<target>`

- Target output root used by image warmup and downstream CI.

### `/workspace/docker_datas`

- Docker-only metadata root.

## Runtime Config Files

### `/workspace/docker_datas/akb.env`

- Generated shell fragment loaded by `android_kernel_builder/docker/entrypoint.sh`.
- Exports target, build, and manifest metadata for downstream CI scripts.

### `/workspace/docker_datas/image.json`

- Generated runtime image metadata.
- Records target name, cache layout version, and fixed Docker runtime paths.

### `/workspace/docker_datas/container_cache.img`

- Image-baked read-only base cache image.
- Created during image build by mounting a sparse ext4 image on `/workspace/cache/<target>`, warming it, then shrinking it.

### `/workspace/docker_datas/container_cache.json`

- Metadata for `container_cache.img`.
- Stores `container_cache_sha256` used to validate external overlay deltas.

### `/workspace/docker_datas/outerimage/outer-cache.img`

- External writable delta cache image used at runtime as overlay `upperdir` and `workdir`.

### `/workspace/docker_datas/outerimage/next-outer-cache.img`

- Exported runtime delta image produced after a container run.

### `/usr/local/bin/akb-entrypoint`

- Image entrypoint helper.
- Sources `/workspace/docker_datas/akb.env` and runs the requested command.

## Cache Layout

Under `/workspace/cache/<target>`:

- `repo`: repo reference cache
- `bazel/state`: Bazel local state passed as `--output_base`
- `bazel/repo`: Bazel repository cache passed as `--repository_cache`
- `bazel/diskcache`: Bazel disk cache passed as `--disk_cache`
- `bazel/kleaf-out`: Kleaf persistent local output cache passed as `--config=local --cache_dir`
- `ccache`: compiler cache for legacy builds

## Target Metadata

Under `/workspace/docker_datas/targets/<target>`:

- `workspace.json`: written after `uv run sync-source`
- `disk-usage.json`: written after `uv run build` or `uv run warmup-build`
- `warmup-outputs.json`: written after `uv run warmup-build` when a warmup target is configured
- `snapshot.json`: written by snapshot image generation

During workspace and snapshot image builds, final cleanup removes every direct entry under `/workspace/source-code/<target>/common` except `.git`, then runs `uv run print-usage-report` so the build log shows the final retained workspace disk usage.
