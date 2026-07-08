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

[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
```

Optional target-specific build fields include `target`, `warmup_target`, `dist_dir`, `dist_flag`, `jobs`, `lto`, and `legacy_config`. The `[cache]` section is ignored; cache subdirectory names are fixed by the AKB layout.

The `[workspace]` section has been removed. Any workspace path configuration now raises an error.
