# Configuration

AKB uses checked-in target configuration files and the current project root as the work root. There is no host environment config file and no configurable source/cache/output path section.

## Target Files

- Target configs live under `android_kernel_builder/configs/targets/<name>.toml`.
- Local manifests live under `android_kernel_builder/configs/manifests/`.
- Target inheritance uses `extends = "<target-name>"` and resolves within the target config directory.

## Target Selection

Commands select a target using this order:

1. `--target <name>`
2. `AKB_TARGET`
3. The only selectable target in `android_kernel_builder/configs/targets/`

If multiple selectable targets exist and neither `--target` nor `AKB_TARGET` is set, AKB fails fast.

## Fixed Work Layout

For target `<name>`, AKB derives paths as follows:

- Source checkout: `source-code/<name>/`
- Cache root: `cache/<name>/`
- Output root: `out/<name>/`
- Metadata root: `docker_datas/targets/<name>/`

These paths are not configurable through target files or CLI flags.

## Target Schema

Required target fields:

```toml
name = "android15-6.6"

[repo]
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"
```

Sync configuration currently uses the `[repo]` table. Its fields include `url`, `branch`, `file`, `path`, `minimal`, and `autodetect_deprecated`.

Build configuration must use exactly one backend table: `[kleaf]` or `[legacy]`.

Kleaf build fields include `target`, `warmup_target`, `dist_dir`, `dist_flag`, `arch`, `jobs`, and `lto`.

Legacy build fields include `legacy_config`, `dist_dir`, `arch`, `jobs`, `lto`, and `use_ccache`.

The `[cache]` section is ignored; cache subdirectory names are fixed by the AKB layout.

The `[workspace]` section is ignored.
