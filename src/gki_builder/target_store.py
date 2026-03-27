# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .active_target import load_active_target, resolve_embedded_manifest_path
from .config import AkbConfig, load_akb_config
from .environment import AkbEnvironment
from . import layout
from .targets import BuildConfig, CacheConfig, ManifestConfig, TargetConfig, WorkspaceConfig, _parse_target_definition_file


def resolve_target(environment: AkbEnvironment, target_name: str | None = None) -> TargetConfig:
    if environment.mode == "docker":
        return _load_docker_target(environment.work_root)
    return load_host_target(environment.work_root, target_name)


def load_host_target(work_root: Path, target_name: str | None = None) -> TargetConfig:
    akb_config = load_akb_config(work_root)
    resolved_name = resolve_host_target_name(akb_config, target_name)
    return _parse_target_definition_file(
        host_target_config_path(work_root, resolved_name),
        manifest_root=layout.target_manifests_root(work_root),
        default_source_dir=akb_config.workspace.source_dir,
    )


def host_target_config_path(work_root: Path, target_name: str) -> Path:
    path = layout.target_config_file(work_root, target_name)
    if not path.exists():
        raise FileNotFoundError(f"Target config not found: {path}")
    return path


def resolve_host_target_name(akb_config: AkbConfig, target_name: str | None) -> str:
    if target_name:
        return target_name
    if akb_config.default_target:
        return akb_config.default_target
    raise ValueError("Missing --target and no default_target configured in .akb/config.toml")


def _load_docker_target(work_root: Path) -> TargetConfig:
    active_target = load_active_target(work_root)
    return TargetConfig(
        name=active_target.name,
        manifest=ManifestConfig(
            source=active_target.manifest.source,
            url=active_target.manifest.url,
            branch=active_target.manifest.branch,
            file=active_target.manifest.file,
            path=resolve_embedded_manifest_path(active_target, work_root),
            minimal=active_target.manifest.minimal,
            autodetect_deprecated=active_target.manifest.autodetect_deprecated,
        ),
        build=BuildConfig(
            system=active_target.build.system,
            target=active_target.build.target,
            warmup_target=active_target.build.warmup_target,
            dist_dir=active_target.build.dist_dir,
            dist_flag=active_target.build.dist_flag,
            arch=active_target.build.arch,
            jobs=active_target.build.jobs,
            legacy_config=active_target.build.legacy_config,
            lto=active_target.build.lto,
        ),
        cache=CacheConfig(),
        workspace=WorkspaceConfig(
            source_dir=active_target.workspace.source_dir,
            metadata_dir=layout.docker_target_metadata_relative_dir(),
        ),
        config_path=active_target.config_path,
    )
