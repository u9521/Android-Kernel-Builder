# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .build_systems import get_build_system_spec, supported_build_systems
from . import layout

ARCHITECTURES = ("aarch64", "x86_64")
MANIFEST_SOURCES = ("remote", "local")
@dataclass(slots=True)
class ActiveManifestConfig:
    source: str
    url: str | None = None
    branch: str | None = None
    file: str | None = None
    path: str | None = None
    minimal: bool = False
    autodetect_deprecated: bool = False


@dataclass(slots=True)
class ActiveBuildConfig:
    system: str
    target: str = "//common:kernel_{arch}_dist"
    warmup_target: str | None = None
    dist_dir: str = "out/gki"
    dist_flag: str = "dist_dir"
    arch: str = "aarch64"
    jobs: int = 0
    legacy_config: str | None = None
    lto: str | None = "thin"
    use_ccache: bool = True


@dataclass(slots=True)
class ActiveWorkspaceConfig:
    source_dir: str = "android-kernel"


@dataclass(slots=True)
class ActiveTargetConfig:
    version: int
    name: str
    manifest: ActiveManifestConfig
    build: ActiveBuildConfig
    workspace: ActiveWorkspaceConfig
    config_path: Path


def load_active_target(work_root_or_config_path: str | Path) -> ActiveTargetConfig:
    config_path = _resolve_config_path(work_root_or_config_path)
    payload = tomllib.loads(config_path.read_text(encoding="utf-8")) or {}

    version = payload.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ValueError(f"Invalid version in {config_path}: expected positive integer")

    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"Missing required 'name' in {config_path}")

    manifest_payload = payload.get("manifest") or {}
    if not isinstance(manifest_payload, dict):
        raise ValueError(f"Invalid [manifest] section in {config_path}")
    manifest = ActiveManifestConfig(
        source=manifest_payload.get("source", "remote"),
        url=manifest_payload.get("url"),
        branch=manifest_payload.get("branch"),
        file=manifest_payload.get("file"),
        path=_validate_manifest_relative_path(manifest_payload.get("path"), config_path),
        minimal=bool(manifest_payload.get("minimal", False)),
        autodetect_deprecated=bool(manifest_payload.get("autodetect_deprecated", False)),
    )
    _validate_manifest(manifest, config_path)

    build_payload = payload.get("build") or {}
    if not isinstance(build_payload, dict):
        raise ValueError(f"Invalid [build] section in {config_path}")
    if "system" not in build_payload:
        raise ValueError(f"Missing required 'build.system' in {config_path}")
    build_system = build_payload.get("system", "kleaf")
    build_spec = get_build_system_spec(build_system) if isinstance(build_system, str) else None
    use_ccache_default = build_spec.default_use_ccache if build_spec is not None else False
    build = ActiveBuildConfig(
        system=build_system,
        target=build_payload.get("target", "//common:kernel_{arch}_dist"),
        warmup_target=build_payload.get("warmup_target"),
        dist_dir=build_payload.get("dist_dir", name),
        dist_flag=build_payload.get("dist_flag", "dist_dir"),
        arch=build_payload.get("arch", "aarch64"),
        jobs=build_payload.get("jobs", 0),
        legacy_config=build_payload.get("legacy_config"),
        lto=build_payload.get("lto", "thin"),
        use_ccache=_required_bool(build_payload.get("use_ccache", use_ccache_default), config_path, "build.use_ccache"),
    )
    _validate_build(build, config_path)

    workspace_payload = payload.get("workspace") or {}
    if not isinstance(workspace_payload, dict):
        raise ValueError(f"Invalid [workspace] section in {config_path}")
    if "metadata_dir" in workspace_payload:
        raise ValueError(f"workspace.metadata_dir is fixed by layout constants and cannot be configured in {config_path}")
    workspace = ActiveWorkspaceConfig(
        source_dir=_validate_relative_path_field(
            workspace_payload.get("source_dir", "android-kernel"),
            config_path,
            "workspace.source_dir",
        )
    )

    return ActiveTargetConfig(
        version=version,
        name=name,
        manifest=manifest,
        build=build,
        workspace=workspace,
        config_path=config_path,
    )


def resolve_embedded_manifest_path(target: ActiveTargetConfig, work_root: Path | None = None) -> Path | None:
    if target.manifest.path is None:
        return None
    root = layout.embedded_manifests_root(work_root or layout.DOCKER_WORK_ROOT)
    return root / target.manifest.path


def _resolve_config_path(work_root_or_config_path: str | Path) -> Path:
    path = Path(work_root_or_config_path)
    if path.suffix == ".toml":
        return path.resolve()
    return layout.active_target_file(path.resolve())


def _validate_manifest(manifest: ActiveManifestConfig, config_path: Path) -> None:
    if manifest.source not in MANIFEST_SOURCES:
        raise ValueError(f"Unsupported manifest source in {config_path}: {manifest.source}")
    if manifest.source == "remote":
        if not manifest.url or not manifest.branch:
            raise ValueError(f"Remote manifest requires url and branch in {config_path}")
        return
    if not manifest.url:
        raise ValueError(f"Local manifest requires url in {config_path}")
    if not manifest.path:
        raise ValueError(f"Local manifest requires 'path' in {config_path}")


def _validate_build(build: ActiveBuildConfig, config_path: Path) -> None:
    if build.system not in supported_build_systems():
        raise ValueError(f"Unsupported build system in {config_path}: {build.system}")
    build_spec = get_build_system_spec(build.system)
    if build_spec is None:
        raise ValueError(f"Unsupported build system in {config_path}: {build.system}")
    if build.arch not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture in {config_path}: {build.arch}")
    if not isinstance(build.jobs, int) or build.jobs < 0:
        raise ValueError(f"Invalid build.jobs in {config_path}: expected non-negative integer")
    if not build_spec.supports_warmup and build.warmup_target:
        raise ValueError(f"build.warmup_target is only supported for kleaf builds in {config_path}")
    if build.dist_flag not in {"dist_dir", "destdir"}:
        raise ValueError(f"Unsupported dist_flag in {config_path}: {build.dist_flag}")
    if not build_spec.supports_ccache and build.use_ccache:
        raise ValueError(f"build.use_ccache=true is only supported for legacy builds in {config_path}")


def _validate_manifest_relative_path(value: object, config_path: Path) -> str | None:
    if value is None:
        return None
    return _validate_relative_path_field(value, config_path, "manifest.path")


def _validate_relative_path_field(value: object, config_path: Path, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid {field_name} in {config_path}: expected non-empty string")
    candidate = Path(value)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError(f"Invalid {field_name} in {config_path}: path must stay inside the embedded manifests root")
    return value


def _required_bool(value: object, config_path: Path, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Invalid {field_name} in {config_path}: expected boolean")
