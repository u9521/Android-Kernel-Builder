# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
from pathlib import Path

from . import layout
from .core.build.engines import kleaf
from .core.config import KleafBuildConfig, TargetConfig
from .utils import directory_size_bytes, ensure_directory, format_bytes, write_json


def write_usage_report(target: TargetConfig, source_dir: Path, cache_root: Path, output_dir: Path) -> None:
    usage_report = analyze_workspace_usage(target, source_dir, cache_root, output_dir)
    metadata_root = ensure_directory(target_metadata_root(source_dir, target))
    write_json(metadata_root / layout.DISK_USAGE_FILE_NAME, usage_report)
    print_usage_report(usage_report)


def write_warmup_outputs(
    target: TargetConfig,
    source_dir: Path,
    output_dir: Path,
    exported_files: list[dict[str, str]],
) -> None:
    metadata_root = ensure_directory(target_metadata_root(source_dir, target))
    write_json(
        metadata_root / layout.WARMUP_OUTPUTS_FILE_NAME,
        {
            "target": target.name,
            "warmup_target": target.build.warmup_target if isinstance(target.build, KleafBuildConfig) else None,
            "output_dir": str(output_dir),
            "files": exported_files,
        },
    )


def analyze_workspace_usage(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    source_dir = source_dir.resolve()
    metadata_dir = target_metadata_root(source_dir, target)
    repo_metadata_dir = source_dir / ".repo"
    repo_reference_dir = layout.target_repo_cache_root(cache_root).resolve()
    bazel_root = layout.target_bazel_cache_root(cache_root).resolve()
    bazel_state_dir = kleaf.bazel_output_base_path(cache_root)
    bazel_repo_dir = kleaf.bazel_repository_cache_path(cache_root)
    bazel_disk_cache_dir = kleaf.bazel_disk_cache_path(cache_root)
    kleaf_cache_dir = kleaf.kleaf_cache_dir_path(cache_root)
    ccache_dir = layout.target_ccache_cache_root(cache_root).resolve()

    source_total = directory_size_bytes(source_dir)
    repo_metadata = directory_size_bytes(repo_metadata_dir)
    source_checkout = max(source_total - repo_metadata, 0)
    cache_total = directory_size_bytes(cache_root)

    sections = {
        "source": usage_entry(source_dir, source_checkout),
        "repo_metadata": usage_entry(repo_metadata_dir, repo_metadata),
        "cache": usage_entry(cache_root, cache_total),
        "cache_repo_reference": usage_entry(repo_reference_dir, directory_size_bytes(repo_reference_dir)),
        "cache_bazel": usage_entry(bazel_root, directory_size_bytes(bazel_root)),
        "cache_bazel_state": usage_entry(bazel_state_dir, directory_size_bytes(bazel_state_dir)),
        "cache_bazel_repo": usage_entry(bazel_repo_dir, directory_size_bytes(bazel_repo_dir)),
        "cache_bazel_diskcache": usage_entry(bazel_disk_cache_dir, directory_size_bytes(bazel_disk_cache_dir)),
        "cache_kleaf": usage_entry(kleaf_cache_dir, directory_size_bytes(kleaf_cache_dir)),
        "cache_ccache": usage_entry(ccache_dir, directory_size_bytes(ccache_dir)),
        "output": usage_entry(output_dir, directory_size_bytes(output_dir)),
    }
    sections["workspace_metadata"] = usage_entry(metadata_dir, directory_size_bytes(metadata_dir))
    return {
        "target": target.name,
        "sections": sections,
    }


def usage_entry(path: Path, size_bytes: int) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": size_bytes,
        "human": format_bytes(size_bytes),
    }


def target_metadata_root(source_dir: Path, target: TargetConfig) -> Path:
    work_root = source_dir.parents[1]
    return layout.docker_target_metadata_root(work_root, target.name)


def print_usage_report(report: dict[str, object]) -> None:
    print("workspace disk usage:", flush=True)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
