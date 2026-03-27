# Configuration Reference

This project now uses three main TOML inputs:

- `configs/global.toml`: repository-wide defaults still needed during image creation
- `{work}/.akb/config.toml`: host environment defaults
- one target file per target
  - host: `{work}/.akb/targets/configs/<name>.toml`
  - docker: `/workspace/.akb/active-target.toml`

## `configs/global.toml`

Only snapshot-image preserved Git projects remain configurable here.

```toml
[snapshot]
git_projects = ["common"]
```

## `{work}/.akb/config.toml`

Host environment defaults.

```toml
version = 1
default_target = "android15-6.6"

[workspace]
source_dir = "android-kernel"
cache_dir = ".cache"
output_dir = "out"

[build]
jobs = 0
lto = "thin"
```

Rules:

- `default_target` is optional
- workspace paths must stay inside the AKB work root
- `build.jobs = 0` means auto-detect CPU count at runtime

## Target Files

Target files describe:

- manifest source
- build system and build target
- cache subdirectory names
- source subdirectory name

Example host target:

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
warmup_target = "//common:kernel_{arch}"
dist_dir = "gki/android15-6.6"
dist_flag = "dist_dir"
arch = "aarch64"

[cache]
repo_dir = "repo"
bazel_dir = "bazel"
ccache_dir = "ccache"

[workspace]
source_dir = "android-kernel"
```

## Docker Active Target

Docker runtime uses exactly one active target:

`/workspace/.akb/active-target.toml`

Example:

```toml
version = 1
name = "android15-6.6"

[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
file = "default.xml"

[build]
system = "kleaf"
target = "//common:kernel_{arch}_dist"
warmup_target = "//common:kernel_{arch}"
dist_dir = "gki/android15-6.6"
dist_flag = "dist_dir"
arch = "aarch64"
jobs = 0

[workspace]
source_dir = "android-kernel"
```

## Manifest Rules

- `manifest.source` supports `remote` and `local`
- local manifests must stay inside the manifests root
- host target manifests resolve relative to `{work}/.akb/targets/manifests`
- docker active-target manifests resolve relative to `/workspace/.akb/manifests`
- absolute paths and `..` escape paths are rejected for embedded/docker manifest paths

## Metadata Rules

- host target metadata is always written under `{work}/.akb/state/targets/<target>`
- docker target metadata is always written under `/workspace/docker_metadata/targets/<target>`
- `workspace.metadata_dir` is fixed by layout constants and cannot be configured
