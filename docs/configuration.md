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

### Target Field Reference

#### Top-Level Fields

- `name`: unique target name used by `--target`, metadata directories, and image metadata.
- `extends`: optional parent target name in the same config directory.
- `base`: optional boolean; `true` means inheritance-only (cannot be selected as build target).

#### `[manifest]`

Controls how `repo init` and `repo sync` prepare source code.

- `source`: allowed values are `remote` and `local`.
- `url`: manifest repository URL; required for both `remote` and `local` modes.
- `branch`: required for `remote`; optional for `local`.
- `file`: optional remote manifest entry file passed to `repo init -m`.
- `path`: required for `local`; must be a relative path inside the manifest search root.
- `minimal`: optional boolean; when `true`, uses shallow/minimal sync flags.
- `autodetect_deprecated`: optional boolean for remote `common-*` branches.

Minimal sync behavior currently maps to:

- `repo init --depth=1`
- `repo sync --trace -c --no-clone-bundle --no-tags`

Local mode uses init-manifest behavior directly (`repo init ... -m <path>`), not overlay patching.

#### `[build]`

Controls how compilation runs after source sync.

- `system`: required; allowed values `kleaf` and `legacy`.
- `target`: build target pattern; supports `{arch}` formatting.
- `warmup_target`: optional warmup target pattern for kleaf only; supports `{arch}` formatting.
- `dist_dir`: output directory relative to `--output-root`; defaults to target `name` when omitted.
- `dist_flag`: allowed values `dist_dir` and `destdir`.
- `arch`: allowed values `aarch64` and `x86_64`.
- `jobs`: positive integer; when `0` or omitted in defaults, resolves to CPU count.
- `legacy_config`: required when `system = "legacy"`; supports `{arch}` formatting.
- `lto`: optional, typically `thin` or `none`.
- `use_ccache`: optional boolean; defaults to `true` for legacy builds and `false` for non-legacy builds.

Build constraints:

- `warmup_target` is rejected for non-kleaf targets.
- legacy builds export `BUILD_CONFIG`, `DIST_DIR`, and `MAKEFLAGS` for `build/build.sh`.
- when `build.use_ccache = true`, legacy builds also set `CCACHE_DIR` and pass `CC=<absolute ccache-masqueraded clang path>`.
- the ccache masquerade path is fixed at `<cache_root>/.ccache-tools/clang` so the compiler path stays stable across runs and ccache can keep hitting the same cache entries.
- kleaf builds use the source tree `tools/bazel` launcher and pass `--<dist_flag>=<output>`.

#### `[cache]`

Reusable subdirectories under the selected cache root.

- `repo_dir`: repo reference cache directory.
- `bazel_dir`: bazel cache root directory.
- `kleaf_dir`: kleaf cache directory name under `bazel_dir`.
- `ccache_dir`: compiler cache directory.

For Kleaf targets, AKB uses the following fixed subpaths under `cache.<bazel_dir>`:

- `state`: Bazel `--output_base`
- `repo`: Bazel `--repository_cache`
- `diskcache`: Bazel `--disk_cache`
- `<kleaf_dir>`: Kleaf `--config=local --cache_dir`

Mode-specific constraints:

- `build.system = "kleaf"`: do not define `cache.ccache_dir`.
- `build.system = "legacy"`: do not define `cache.bazel_dir` or `cache.kleaf_dir`.
- `build.system != "legacy"`: `build.use_ccache = true` is rejected.
- `build.system = "legacy"` and `build.use_ccache = true`: `cache.ccache_dir` must be explicitly defined (no implicit default).
- `build.system = "legacy"` and `build.use_ccache = false`: `cache.ccache_dir` is optional and ignored when present (with warning).
- `cache.kleaf_dir` must be a single directory name, not a path.

#### `[workspace]`

- `source_dir`: kernel source directory under the work root.
- `metadata_dir`: not configurable in target files; only Docker runtime uses fixed metadata paths.

### Target Name And File Name

Target selection is requested by target name (for example `--target android14-6.1`).

Recommended convention:

- file path: `.akb/targets/configs/<target-name>.toml`
- top-level `name`: `<target-name>`

Examples:

- `sample.toml` should contain `name = "sample"`
- `android14-6.1.toml` should contain `name = "android14-6.1"`

Resolution behavior:

- the loader first checks `<target-name>.toml`
- if the file exists but `name` mismatches, it prints a warning
- if `name` does not match the requested target, it falls back to scanning target configs
- fallback matching supports exact and case-insensitive filename matches
- `name` matching is always case-sensitive and must be exact
- mismatch warnings are deduplicated per resolution

To avoid ambiguity and noisy warnings, keep filename and `name` consistent.

### Target Inheritance

Target files can inherit from another target file in the same directory by using
top-level `extends`.

Example child target for monthly patch branch overrides:

```toml
name = "android14-6.1-2025-03"
extends = "android14-6.1"

[manifest]
branch = "common-android14-6.1-2025-03"
```

Rules:

- `extends` must be a target name (`android14-6.1`), not a file name or path
- child values override parent values
- table values are merged recursively (`manifest`, `build`, `cache`, `workspace`)
- `extends` is resolved to `<target-name>.toml` in the same target config directory
- circular inheritance is rejected

### Base Target Configs

You can mark a target config as inheritance-only:

```toml
name = "android15-6.6-base"
base = true
```

Rules:

- `base` must be a boolean
- `base = true` targets are not selectable build targets
- base configs are allowed to omit fields that would normally be required for buildable targets
- base configs are intended to be inherited via `extends`

### Legacy Build Notes

- For `build.system = "legacy"`, `build.legacy_config` is required.
- `build.legacy_config` supports `{arch}` formatting (for example `common/build.config.gki.{arch}`).

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
- local manifests must stay inside the manifest search root
- for checked-in targets under `configs/targets`, `manifest.path` is resolved relative to `configs/manifests`
- host target manifests resolve relative to `{work}/.akb/targets/manifests`
- docker active-target manifests resolve relative to `/workspace/.akb/manifests`
- absolute paths and `..` escape paths are rejected for embedded/docker manifest paths

## Metadata Rules

- host mode does not write target metadata files.
- docker target metadata is always written under `/workspace/docker_datas/targets/<target>`.
- `workspace.metadata_dir` is fixed by layout constants and cannot be configured.
