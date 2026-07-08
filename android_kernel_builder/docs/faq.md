# FAQ

## Where are caches stored?

Caches are stored under `cache/<target>/` on host and `/workspace/cache/<target>/` in Docker images.

Common Kleaf cache paths are:

- `cache/<target>/bazel/state`: Bazel local state passed as `--output_base`
- `cache/<target>/bazel/repo`: Bazel repository cache passed as `--repository_cache`
- `cache/<target>/bazel/diskcache`: Bazel disk cache passed as `--disk_cache`
- `cache/<target>/bazel/kleaf-out`: Kleaf persistent local output cache passed as `--config=local --cache_dir`

## Can I override source, cache, or output directories?

No. The layout is fixed: `source-code/<target>`, `cache/<target>`, and `out/<target>`.

## How do I select a default target?

Set `AKB_TARGET=<target>` or pass `--target <target>` on the command line.
