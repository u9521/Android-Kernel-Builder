# Target Configuration Reference

This project uses `TOML` target files under `configs/targets/`.

Each target file describes:

- where kernel source comes from
- how `repo` should initialize and sync the workspace
- how the kernel should be built
- where reusable caches and output directories live

Example:

```toml
name = "avd-android15-6.6-arm64"

[manifest]
source = "local"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
path = "../../manifests/avd/local_manifests/avd-android-15-6.6_arm64.xml"
minimal = true

[build]
system = "kleaf"
target = "//common-modules/virtual-device:virtual_device_{arch}_dist"
dist_dir = "avd/android15-6.6-arm64"
dist_flag = "dist_dir"
arch = "aarch64"
lto = "thin"

[cache]
repo_dir = "repo"
bazel_dir = "bazel"
ccache_dir = "ccache"

[workspace]
source_dir = "android-kernel"
metadata_dir = ".gki-builder"
```

## Top-Level Fields

### `name`

- Unique target name.
- Used in metadata output and image naming.
- Keep it stable and descriptive, for example `android15-6.6` or `avd-android16-6.12-x64`.

## `[manifest]`

Controls how `repo init` and `repo sync` prepare source code.

### `source`

- Allowed values: `remote`, `local`
- `remote`: sync directly from an upstream manifest repo.
- `local`: use checked-in manifest XML from this repository.

### `url`

- Used only when `source = "remote"`.
- Passed to `repo init -u`.
- Example: `https://android.googlesource.com/kernel/manifest`

### `branch`

- Used only when `source = "remote"`.
- Passed to `repo init -b`.
- Example: `common-android15-6.6`

### `autodetect_deprecated`

- Optional boolean for `remote` manifests.
- Default: `false`
- When `true`, and the remote branch looks like `common-<kernel-branch>`, the tool checks
  whether `kernel/common` has moved to `deprecated/<kernel-branch>` and rewrites the
  initialized manifest automatically before sync.
- This is useful for older Android kernel branches that may have been moved under
  `deprecated/` upstream.

### `file`

- Optional for `remote` mode.
- Passed to `repo init -m`.
- Use it when the manifest repo contains multiple XML entrypoints and you need a specific one.

### `path`

- Local path to one manifest XML file.
- Resolved relative to the `.toml` file.
- Used only when `source = "local"`.
- Passed directly to `repo init -m`.

### `minimal`

- Optional boolean.
- When `true`, the tool uses a minimal source sync strategy.
- Current behavior in minimal mode:
  - `repo init --depth=1`
  - `repo sync -c --no-clone-bundle --no-tags`
- Omit it or set it to `false` when you want a fuller source checkout.

### Local mode notes

- Local mode is now init-manifest only.
- The tool runs the equivalent of:
  1. `repo init -u <url> [-b <branch>] -m <path> [--depth=1 when minimal=true]`
  2. `repo sync --trace [with minimal flags when minimal=true]`
- This is intentionally close to your previous CI setup.

### Why local mode still needs `url`

- Even in local mode, `repo init` still expects a manifest repository via `-u`.
- Your local file is used as the manifest entry specified by `-m`.
- So `url` is still required, but there is no separate bootstrap overlay step anymore.

### `branch`

- Optional in local mode.
- Passed to `repo init -b`.
- Recommended when your local manifest belongs to a known branch family such as `common-android15-6.6`.

## `[build]`

Controls how compilation runs after the workspace is ready.

### `system`

- Allowed values: `kleaf`, `legacy`
- This field is required.
- `kleaf`: run the source tree's `tools/bazel`
- `legacy`: run `bash build/build.sh`

### `target`

- Bazel target pattern used for `kleaf` builds.
- Supports `{arch}` substitution.
- Examples:
  - `//common:kernel_{arch}_dist`
  - `//common-modules/virtual-device:virtual_device_{arch}_dist`

### `warmup_target`

- Optional Bazel target pattern used only for workspace-image warmup builds.
- Supports `{arch}` substitution.
- If set, `docker-build-workspace` warms caches with `bazel build <warmup_target>` instead of running the full distribution target.
- `warmup-build` exports the warmup target's default output files to `<output-root>/<dist_dir>`.
- Use this when the normal `target` also creates ramdisk, boot, or partition images and you want faster image creation.
- Example:
  - `//common:kernel_{arch}`
- For the AVD `virtual_device_{arch}_dist` targets, prefer `//common-modules/virtual-device:virtual_device_{arch}` as the warmup target so image warmup compiles the kernel and modules without also building initramfs or dist packaging.

### `dist_dir`

- Output directory relative to `--output-root`.
- Example: `gki`, `avd/android15-6.6-arm64`
- Final output path becomes `<output-root>/<dist_dir>`.

### `dist_flag`

- Allowed values: `dist_dir`, `destdir`
- Used for Kleaf target differences across kernel generations.
- Most 5.x and 6.1/6.6 trees use `dist_dir`.
- Some newer trees such as 6.12-based setups may need `destdir`.

### `arch`

- Allowed values: `aarch64`, `x86_64`
- Used in target substitution and target metadata.

### `jobs`

- Optional positive integer.
- Controls compile parallelism.
- For `kleaf`, it is passed as `--jobs=<n>` to `tools/bazel`.
- For `legacy`, it is exported as `MAKEFLAGS=-j<n>` before running `build/build.sh`.
- Defaults to the maximum available CPU threads when omitted.

### `legacy_config`

- Only needed for `legacy` builds.
- Sets `BUILD_CONFIG` before running `build/build.sh`.

### `lto`

- Optional.
- Passed through to build invocation.
- Common values:
  - `thin`
  - `none`

LTO defaults are branch-specific. According to the Kleaf LTO guide, GKI `gki_defconfig`
on `android14-6.1` and newer disables LTO by default, and this should only be changed
when the trade-offs are understood.

For development and patch iteration, `lto = "none"` often reduces build time.
The same guide also notes there may be incremental build issues with LTO caching, so
if incremental rebuild behavior looks suspicious, verify whether the branch expects LTO
to stay disabled.

Reference: `https://android.googlesource.com/kernel/build/+/refs/heads/master/kleaf/docs/lto.md`

## `[cache]`

Controls reusable cache directories under the chosen `--cache-root`.

### `repo_dir`

- Directory for `repo` reference data.
- Intended to help repeated syncs reuse fetched objects.

### `bazel_dir`

- Bazel disk cache directory.
- Important for incremental Kleaf rebuild speed in CI and local Docker runs.

### `ccache_dir`

- `ccache` directory used by the build environment.

## `[workspace]`

Controls the layout under the chosen `--workspace` root.

### `source_dir`

- Where the Android kernel source tree lives.
- Example final path: `.workspace/android-kernel`

### `metadata_dir`

- Where this tool writes metadata such as `workspace.json` and `disk-usage.json`.
- Example final path: `.workspace/.gki-builder/<target>/workspace.json`

## Notes And Pitfalls

### Local manifests are active init manifests

When `source = "local"`, the file in `path` is passed directly to `repo init -m`.

This is not overlay behavior.

### Be careful with branch mismatches

If the local XML is for `common-android16-6.12`, do not set `branch = "common-android15-6.6"`.

### Keep target names and output directories stable

Consumer CI, image tags, and artifact paths become much easier to manage when `name` and `dist_dir` do not drift.

### Use `minimal = true` for pre-warmed CI workspaces

This is a good fit when the goal is to create a reusable workspace image quickly and keep download volume small.

If you later need fuller history or tags for debugging, turn it off for that target.

### Prefer one target file per exact source baseline

Good:

- `avd-android15-6.6-arm64.toml`
- `avd-android15-6.6-x64.toml`

Avoid:

- one target file that is reused for multiple manifests by hand edits
