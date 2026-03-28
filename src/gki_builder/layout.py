# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

AKB_DIR_NAME = ".akb"
TARGETS_LINK_NAME = "targets"

TARGETS_DIR_NAME = "targets"
TARGET_CONFIGS_DIR_NAME = "configs"
TARGET_MANIFESTS_DIR_NAME = "manifests"

AKB_CONFIG_FILE_NAME = "config.toml"
ACTIVE_TARGET_FILE_NAME = "active-target.toml"

AKB_VENV_DIR_NAME = "venv"
AKB_BIN_DIR_NAME = "bin"

CACHE_DIR_NAME = ".cache"
OUTPUT_DIR_NAME = "out"
DOCKER_METADATA_DIR_NAME = "docker_metadata"
TARGET_METADATA_DIR_NAME = "targets"

DOCKER_WORK_ROOT = Path("/workspace")

ENV_FILE_NAME = "gki-builder.env"
WORKSPACE_METADATA_FILE_NAME = "workspace.json"
DISK_USAGE_FILE_NAME = "disk-usage.json"
WARMUP_OUTPUTS_FILE_NAME = "warmup-outputs.json"
SNAPSHOT_METADATA_FILE_NAME = "snapshot.json"


def akb_root(work_root: Path) -> Path:
    return work_root / AKB_DIR_NAME


def akb_config_file(work_root: Path) -> Path:
    return akb_root(work_root) / AKB_CONFIG_FILE_NAME


def targets_link(work_root: Path) -> Path:
    return work_root / TARGETS_LINK_NAME


def targets_root(work_root: Path) -> Path:
    return akb_root(work_root) / TARGETS_DIR_NAME


def target_configs_root(work_root: Path) -> Path:
    return targets_root(work_root) / TARGET_CONFIGS_DIR_NAME


def target_manifests_root(work_root: Path) -> Path:
    return targets_root(work_root) / TARGET_MANIFESTS_DIR_NAME


def target_config_file(work_root: Path, target_name: str) -> Path:
    return target_configs_root(work_root) / f"{target_name}.toml"


def akb_venv_root(work_root: Path) -> Path:
    return akb_root(work_root) / AKB_VENV_DIR_NAME


def akb_bin_root(work_root: Path) -> Path:
    return akb_root(work_root) / AKB_BIN_DIR_NAME


def cache_root(work_root: Path) -> Path:
    return work_root / CACHE_DIR_NAME


def output_root(work_root: Path) -> Path:
    return work_root / OUTPUT_DIR_NAME


def docker_metadata_root(work_root: Path) -> Path:
    return work_root / DOCKER_METADATA_DIR_NAME


def docker_env_file(work_root: Path) -> Path:
    return docker_metadata_root(work_root) / ENV_FILE_NAME


def active_target_file(work_root: Path) -> Path:
    return akb_root(work_root) / ACTIVE_TARGET_FILE_NAME


def embedded_manifests_root(work_root: Path) -> Path:
    return akb_root(work_root) / TARGET_MANIFESTS_DIR_NAME


def docker_target_metadata_dir(work_root: Path) -> Path:
    return docker_metadata_root(work_root) / TARGET_METADATA_DIR_NAME


def docker_target_metadata_root(work_root: Path, target_name: str) -> Path:
    return docker_target_metadata_dir(work_root) / target_name


def docker_target_metadata_relative_dir() -> str:
    return f"{DOCKER_METADATA_DIR_NAME}/{TARGET_METADATA_DIR_NAME}"
