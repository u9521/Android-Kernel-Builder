# Manifest Modes

AKB supports remote and local manifests.

## Remote Manifests

Remote manifests use `repo init -u <url> -b <branch>` and optionally `-m <file>`.

```toml
[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
file = "default.xml"
```

## Local Manifests

Local manifest paths are relative to `android_kernel_builder/configs/manifests/`.

```toml
[manifest]
source = "local"
url = "https://android.googlesource.com/kernel/manifest"
path = "avd/default.xml"
```

Docker image packaging copies only the selected local manifest into the packaged target bundle and rewrites `manifest.path` accordingly.
