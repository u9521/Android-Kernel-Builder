# Manifest Modes

This repository now supports two manifest sources:

- `remote`
- `local`

For `local`, only `init-manifest` behavior is supported.

## Remote Mode

When a target contains:

```toml
[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
file = "default.xml"
minimal = true
autodetect_deprecated = true
```

the tool runs the equivalent of:

```bash
repo init --depth=1 -u <url> -b <branch> -m <file>
repo sync -c --no-clone-bundle --no-tags ...
```

Use this for standard upstream GKI branches.

When `autodetect_deprecated = true` and the remote branch is `common-*`, the tool also
checks whether the corresponding `kernel/common` branch has moved under `deprecated/`.
If it finds `refs/heads/deprecated/<branch-suffix>`, it rewrites matching manifest
revisions before `repo sync`.

## Local Init-Manifest Mode

When a target contains:

```toml
[manifest]
source = "local"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"
path = "../../manifests/avd/local_manifests/avd-android-15-6.6_arm64.xml"
minimal = true
```

the tool does this:

```bash
repo init --depth=1 -u <url> -b <branch> -m <local-manifest-path>
repo sync -c --no-clone-bundle --no-tags ...
```

This matches the old CI style more closely: the checked-in local XML is passed directly to `repo init -m` and acts as the active manifest entry.

## Which One Should I Use?

### Use `remote` when:

- you build stock upstream GKI branches
- the manifest entrypoint is stable and public

### Use `local` when:

- you already maintain a checked-in manifest snapshot
- you want the local XML to be the actual manifest entry for `repo init`
- you want behavior close to your old workflow

## Notes

- `minimal = true` is optional. Enable it when you want shallow init and lighter sync behavior.
- `autodetect_deprecated = true` is optional. Enable it for older remote branches that may have been moved under `deprecated/` upstream.
- There is no repo version pin in the current implementation.
- For local mode, `url` is still required because `repo init` needs a manifest repository context even when `-m` points at a checked-in local XML.
- Deprecated-branch auto-detection currently applies only to `remote` manifests whose branch looks like `common-<kernel-branch>`.
