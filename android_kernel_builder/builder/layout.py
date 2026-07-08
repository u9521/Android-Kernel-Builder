# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

PROJECT_PACKAGE_DIR_NAME = "android_kernel_builder"
CONFIGS_DIR_NAME = "configs"
DOCKER_DIR_NAME = "docker"
DOCS_DIR_NAME = "docs"
TARGETS_DIR_NAME = "targets"
TARGET_CONFIGS_DIR_NAME = "configs"
TARGET_MANIFESTS_DIR_NAME = "manifests"

SOURCE_CODE_DIR_NAME = "source-code"
CACHE_DIR_NAME = "cache"
REPO_CACHE_DIR_NAME = "repo"
BAZEL_CACHE_DIR_NAME = "bazel"
BAZEL_STATE_DIR_NAME = "state"
BAZEL_REPOSITORY_CACHE_DIR_NAME = "repo"
BAZEL_DISK_CACHE_DIR_NAME = "diskcache"
KLEAF_CACHE_DIR_NAME = "kleaf-out"
CCACHE_CACHE_DIR_NAME = "ccache"
TEMP_DIR_NAME = ".temp"
OUTPUT_DIR_NAME = "out"
CCACHE_TOOLS_DIR_NAME = ".ccache-tools"
CCACHE_CLANG_LINK_NAME = "clang"
DOCKER_DATAS_DIR_NAME = "docker_datas"
TARGET_METADATA_DIR_NAME = "targets"
DOCKER_OUTERIMAGE_DIR_NAME = "outerimage"
DOCKER_OVERLAYS_DIR_NAME = ".overlays"
DOCKER_IMAGE_INFO_FILE_NAME = "image.json"
CONTAINER_CACHE_IMAGE_FILE_NAME = "container_cache.img"
CONTAINER_CACHE_METADATA_FILE_NAME = "container_cache.json"
OUTER_CACHE_IMAGE_FILE_NAME = "outer-cache.img"
OUTER_CACHE_METADATA_FILE_NAME = "outer-cache.json"
NEXT_OUTER_CACHE_IMAGE_FILE_NAME = "next-outer-cache.img"
NEXT_OUTER_CACHE_METADATA_FILE_NAME = "next-outer-cache.json"
OVERLAY_LOWER_DIR_NAME = "lower.mnt"
OVERLAY_UPPER_DIR_NAME = "upper.mnt"
OVERLAY_MERGED_DIR_NAME = "merged"

DOCKER_WORK_ROOT = Path("/workspace")

ENV_FILE_NAME = "akb.env"
WORKSPACE_METADATA_FILE_NAME = "workspace.json"
DISK_USAGE_FILE_NAME = "disk-usage.json"
WARMUP_OUTPUTS_FILE_NAME = "warmup-outputs.json"
SNAPSHOT_METADATA_FILE_NAME = "snapshot.json"


def project_package_root(project_root: Path) -> Path:
    return project_root / PROJECT_PACKAGE_DIR_NAME


def project_configs_root(project_root: Path) -> Path:
    return project_package_root(project_root) / CONFIGS_DIR_NAME


def global_config_file(project_root: Path) -> Path:
    return project_configs_root(project_root) / "global.toml"


def target_configs_root(project_root: Path) -> Path:
    return project_configs_root(project_root) / TARGETS_DIR_NAME


def target_manifests_root(project_root: Path) -> Path:
    return project_configs_root(project_root) / TARGET_MANIFESTS_DIR_NAME


def target_config_file(project_root: Path, target_name: str) -> Path:
    return target_configs_root(project_root) / f"{target_name}.toml"


def docker_root(project_root: Path) -> Path:
    return project_package_root(project_root) / DOCKER_DIR_NAME


def base_dockerfile(project_root: Path) -> Path:
    return docker_root(project_root) / "base.Dockerfile"


def workspace_dockerfile(project_root: Path) -> Path:
    return docker_root(project_root) / "workspace.Dockerfile"


def snapshot_dockerfile(project_root: Path) -> Path:
    return docker_root(project_root) / "snapshot.Dockerfile"


def target_source_root(work_root: Path, target_name: str) -> Path:
    return work_root / SOURCE_CODE_DIR_NAME / target_name


def cache_root(work_root: Path) -> Path:
    return work_root / CACHE_DIR_NAME


def target_cache_root(work_root: Path, target_name: str) -> Path:
    return cache_root(work_root) / target_name


def target_repo_cache_root(cache_root: Path) -> Path:
    return cache_root / REPO_CACHE_DIR_NAME


def target_bazel_cache_root(cache_root: Path) -> Path:
    return cache_root / BAZEL_CACHE_DIR_NAME


def target_bazel_state_dir(cache_root: Path) -> Path:
    return target_bazel_cache_root(cache_root) / BAZEL_STATE_DIR_NAME


def target_bazel_repository_cache_dir(cache_root: Path) -> Path:
    return target_bazel_cache_root(cache_root) / BAZEL_REPOSITORY_CACHE_DIR_NAME


def target_bazel_disk_cache_dir(cache_root: Path) -> Path:
    return target_bazel_cache_root(cache_root) / BAZEL_DISK_CACHE_DIR_NAME


def target_kleaf_cache_root(cache_root: Path) -> Path:
    return target_bazel_cache_root(cache_root) / KLEAF_CACHE_DIR_NAME


def target_ccache_cache_root(cache_root: Path) -> Path:
    return cache_root / CCACHE_CACHE_DIR_NAME


def temp_root(work_root: Path) -> Path:
    return work_root / TEMP_DIR_NAME


def output_root(work_root: Path) -> Path:
    return work_root / OUTPUT_DIR_NAME


def target_output_root(work_root: Path, target_name: str) -> Path:
    return output_root(work_root) / target_name


def ccache_tools_root(cache_root: Path) -> Path:
    return cache_root / CCACHE_TOOLS_DIR_NAME


def ccache_clang_link(cache_root: Path) -> Path:
    return ccache_tools_root(cache_root) / CCACHE_CLANG_LINK_NAME


def docker_datas_root(work_root: Path) -> Path:
    return work_root / DOCKER_DATAS_DIR_NAME


def docker_env_file(work_root: Path) -> Path:
    return docker_datas_root(work_root) / ENV_FILE_NAME


def docker_image_info_file(work_root: Path) -> Path:
    return docker_datas_root(work_root) / DOCKER_IMAGE_INFO_FILE_NAME


def docker_target_metadata_dir(work_root: Path) -> Path:
    return docker_datas_root(work_root) / TARGET_METADATA_DIR_NAME


def docker_target_metadata_root(work_root: Path, target_name: str) -> Path:
    return docker_target_metadata_dir(work_root) / target_name


def docker_target_metadata_relative_dir() -> str:
    return f"{DOCKER_DATAS_DIR_NAME}/{TARGET_METADATA_DIR_NAME}"


def docker_outerimage_root(work_root: Path) -> Path:
    return docker_datas_root(work_root) / DOCKER_OUTERIMAGE_DIR_NAME


def docker_overlays_root(work_root: Path) -> Path:
    return docker_datas_root(work_root) / DOCKER_OVERLAYS_DIR_NAME


def docker_container_cache_image(work_root: Path) -> Path:
    return docker_datas_root(work_root) / CONTAINER_CACHE_IMAGE_FILE_NAME


def docker_container_cache_metadata_file(work_root: Path) -> Path:
    return docker_datas_root(work_root) / CONTAINER_CACHE_METADATA_FILE_NAME


def docker_outer_cache_image(work_root: Path) -> Path:
    return docker_outerimage_root(work_root) / OUTER_CACHE_IMAGE_FILE_NAME


def docker_outer_cache_metadata_file(work_root: Path) -> Path:
    return docker_outerimage_root(work_root) / OUTER_CACHE_METADATA_FILE_NAME


def docker_next_outer_cache_image(work_root: Path) -> Path:
    return docker_outerimage_root(work_root) / NEXT_OUTER_CACHE_IMAGE_FILE_NAME


def docker_next_outer_cache_metadata_file(work_root: Path) -> Path:
    return docker_outerimage_root(work_root) / NEXT_OUTER_CACHE_METADATA_FILE_NAME


def docker_overlay_lower_root(work_root: Path) -> Path:
    return docker_overlays_root(work_root) / OVERLAY_LOWER_DIR_NAME


def docker_overlay_upper_root(work_root: Path) -> Path:
    return docker_overlays_root(work_root) / OVERLAY_UPPER_DIR_NAME


def docker_overlay_merged_root(work_root: Path) -> Path:
    return docker_overlays_root(work_root) / OVERLAY_MERGED_DIR_NAME
