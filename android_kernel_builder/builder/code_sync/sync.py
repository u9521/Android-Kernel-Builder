# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .. import layout
from ..build_systems import get_build_system_spec
from ..targets import TargetConfig
from ..utils import ensure_directory, run_command, sha256_file, write_json
from . import repo


def sync_source(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    jobs: int,
) -> dict[str, str]:
    source_dir = ensure_directory(source_dir.resolve())
    cache_root = cache_root.resolve()
    metadata_dir = layout.docker_target_metadata_root(source_dir.parents[1], target.name)
    repo_reference_dir = ensure_directory(layout.target_repo_cache_root(cache_root))
    build_spec = get_build_system_spec(target.build.system)
    if build_spec is None:
        raise ValueError(f"Unsupported build system in {target.config_path}: {target.build.system}")
    if build_spec.allows_cache_bazel_dir:
        ensure_directory(layout.target_bazel_cache_root(cache_root))
        ensure_directory(layout.target_bazel_state_dir(cache_root))
        ensure_directory(layout.target_bazel_repository_cache_dir(cache_root))
        ensure_directory(layout.target_bazel_disk_cache_dir(cache_root))
        ensure_directory(layout.target_kleaf_cache_root(cache_root))
    if build_spec.allows_cache_ccache_dir and target.build.use_ccache:
        ensure_directory(layout.target_ccache_cache_root(cache_root))

    repo._repo_init(target, source_dir, repo_reference_dir)
    deprecated_branch = repo._auto_fix_remote_deprecated_branch(target, source_dir)

    run_command(
        repo._repo_sync_command(target, jobs),
        cwd=source_dir,
    )

    metadata = {
        "target": target.name,
        "config_path": str(target.config_path),
        "source_dir": str(source_dir),
        "cache_root": str(cache_root),
        "manifest_source": target.manifest.source,
        "manifest_url": target.manifest.url,
        "manifest_branch": target.manifest.branch,
        "manifest_file": target.manifest.file,
        "manifest_path": str(target.manifest.path) if target.manifest.path else None,
        "manifest_sha256": sha256_file(target.manifest.path) if target.manifest.path else None,
        "manifest_minimal": target.manifest.minimal,
        "manifest_autodetect_deprecated": target.manifest.autodetect_deprecated,
        "deprecated_branch": deprecated_branch,
    }
    if metadata_dir is not None:
        metadata_root = ensure_directory(metadata_dir)
        write_json(metadata_root / "workspace.json", metadata)
    return metadata
