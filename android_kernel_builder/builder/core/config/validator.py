# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .schema import ARCHITECTURES, BuildConfig, KleafBuildConfig, LegacyBuildConfig, RepoConfig, SyncConfig


def validate_sync(sync: SyncConfig, config_path: Path) -> None:
    if isinstance(sync, RepoConfig):
        _validate_repo(sync, config_path)
        return
    raise TypeError(f"Unsupported sync config in {config_path}: {type(sync).__name__}")


def _validate_repo(repo: RepoConfig, config_path: Path) -> None:
    if repo.path is None:
        if not repo.url or not repo.branch:
            raise ValueError(f"Remote repo requires url and branch in {config_path}")
        return

    if not repo.path.exists():
        raise FileNotFoundError(f"Local repo manifest file not found: {repo.path}")

    if not repo.url:
        raise ValueError(f"Local repo requires url in {config_path}")


def validate_build(build: BuildConfig, config_path: Path) -> None:
    if isinstance(build, KleafBuildConfig):
        _validate_kleaf_build(build, config_path)
        return
    if isinstance(build, LegacyBuildConfig):
        _validate_legacy_build(build, config_path)
        return
    raise TypeError(f"Unsupported build config in {config_path}: {type(build).__name__}")


def _validate_common_build(build: BuildConfig, config_path: Path) -> None:
    if build.arch not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture in {config_path}: {build.arch}")
    if build.jobs <= 0:
        raise ValueError(f"Build jobs must be positive in {config_path}: {build.jobs}")


def _validate_kleaf_build(build: KleafBuildConfig, config_path: Path) -> None:
    _validate_common_build(build, config_path)
    if build.dist_flag not in {"dist_dir", "destdir"}:
        raise ValueError(f"Unsupported dist_flag in {config_path}: {build.dist_flag}")


def _validate_legacy_build(build: LegacyBuildConfig, config_path: Path) -> None:
    _validate_common_build(build, config_path)
    if not build.legacy_config:
        raise ValueError(f"Legacy build requires build.legacy.legacy_config in {config_path}")
