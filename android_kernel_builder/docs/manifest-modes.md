# Repo Sync Modes

AKB currently supports Android `repo` manifest based source synchronization.

## Remote Repo Manifests

Remote repo manifests use `repo init -u <url> -b <branch>` and optionally `-m <file>`.

```toml
[repo]
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
file = "default.xml"
minimal = true
```

## Local Repo Manifests

Local repo manifest paths are relative to `android_kernel_builder/configs/manifests/`.

```toml
[repo]
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
path = "avd/default.xml"
minimal = true
```
