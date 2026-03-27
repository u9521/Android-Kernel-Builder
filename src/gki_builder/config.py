# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from . import layout

LTO_MODES = {"none", "thin", "full"}


@dataclass(slots=True)
class WorkspaceDefaults:
    source_dir: str = "android-kernel"
    cache_dir: str = layout.CACHE_DIR_NAME
    output_dir: str = layout.OUTPUT_DIR_NAME


@dataclass(slots=True)
class BuildDefaults:
    jobs: int = 0
    lto: str = "thin"


@dataclass(slots=True)
class AkbConfig:
    version: int
    default_target: str | None
    workspace: WorkspaceDefaults
    build: BuildDefaults
    config_path: Path


def load_akb_config(work_root_or_config_path: str | Path) -> AkbConfig:
    config_path = _resolve_config_path(work_root_or_config_path)
    payload = tomllib.loads(config_path.read_text(encoding="utf-8")) or {}

    version = payload.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ValueError(f"Invalid version in {config_path}: expected positive integer")

    default_target = payload.get("default_target")
    if default_target is not None and (not isinstance(default_target, str) or not default_target):
        raise ValueError(f"Invalid default_target in {config_path}: expected non-empty string")

    workspace_payload = payload.get("workspace") or {}
    if not isinstance(workspace_payload, dict):
        raise ValueError(f"Invalid [workspace] section in {config_path}")
    workspace = WorkspaceDefaults(
        source_dir=_validate_relative_path_field(
            workspace_payload.get("source_dir", "android-kernel"),
            config_path,
            "workspace.source_dir",
        ),
        cache_dir=_validate_relative_path_field(
            workspace_payload.get("cache_dir", layout.CACHE_DIR_NAME),
            config_path,
            "workspace.cache_dir",
        ),
        output_dir=_validate_relative_path_field(
            workspace_payload.get("output_dir", layout.OUTPUT_DIR_NAME),
            config_path,
            "workspace.output_dir",
        ),
    )

    build_payload = payload.get("build") or {}
    if not isinstance(build_payload, dict):
        raise ValueError(f"Invalid [build] section in {config_path}")
    jobs = build_payload.get("jobs", 0)
    if not isinstance(jobs, int) or jobs < 0:
        raise ValueError(f"Invalid build.jobs in {config_path}: expected non-negative integer")
    lto = build_payload.get("lto", "thin")
    if not isinstance(lto, str) or lto not in LTO_MODES:
        raise ValueError(f"Invalid build.lto in {config_path}: expected one of {sorted(LTO_MODES)}")
    build = BuildDefaults(jobs=jobs, lto=lto)

    return AkbConfig(
        version=version,
        default_target=default_target,
        workspace=workspace,
        build=build,
        config_path=config_path,
    )


def _resolve_config_path(work_root_or_config_path: str | Path) -> Path:
    path = Path(work_root_or_config_path)
    if path.suffix == ".toml":
        return path.resolve()
    return layout.akb_config_file(path.resolve())


def _validate_relative_path_field(value: object, config_path: Path, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid {field_name} in {config_path}: expected non-empty string")
    candidate = Path(value)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError(f"Invalid {field_name} in {config_path}: path must stay inside the AKB work root")
    return value
