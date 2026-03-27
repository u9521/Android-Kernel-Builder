# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tomllib

from . import layout
from .utils import discover_project_root, resolve_path

ARCHITECTURES = ("aarch64", "x86_64")
MANIFEST_SOURCES = ("remote", "local")
BUILD_SYSTEMS = ("kleaf", "legacy")


@dataclass(slots=True)
class ManifestConfig:
    source: str
    url: str | None = None
    branch: str | None = None
    file: str | None = None
    path: Path | None = None
    minimal: bool = False
    autodetect_deprecated: bool = False


@dataclass(slots=True)
class BuildConfig:
    system: str = "kleaf"
    target: str = "//common:kernel_{arch}_dist"
    warmup_target: str | None = None
    dist_dir: str = "out/gki"
    dist_flag: str = "dist_dir"
    arch: str = "aarch64"
    jobs: int = os.cpu_count() or 1
    legacy_config: str | None = None
    lto: str | None = "thin"


@dataclass(slots=True)
class CacheConfig:
    repo_dir: str = "repo"
    bazel_dir: str = "bazel"
    ccache_dir: str = "ccache"


@dataclass(slots=True)
class WorkspaceConfig:
    source_dir: str = "android-kernel"
    metadata_dir: str = layout.host_target_metadata_relative_dir()


@dataclass(slots=True)
class TargetConfig:
    name: str
    manifest: ManifestConfig
    build: BuildConfig
    cache: CacheConfig
    workspace: WorkspaceConfig
    config_path: Path


def _parse_target_definition_file(
    config_path: str | Path,
    *,
    manifest_root: Path | None = None,
    default_source_dir: str = "android-kernel",
) -> TargetConfig:
    path = Path(config_path).resolve()
    payload = load_mapping(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Target config must be a mapping: {path}")

    project_root = discover_project_root(path.parent)
    name = payload.get("name")
    if not name:
        raise ValueError(f"Missing required 'name' in {path}")

    manifest_payload = payload.get("manifest") or {}
    manifest = ManifestConfig(
        source=manifest_payload.get("source", "remote"),
        url=manifest_payload.get("url"),
        branch=manifest_payload.get("branch"),
        file=manifest_payload.get("file"),
        path=_resolve_manifest_path(
            manifest_payload.get("path"),
            manifest_root=manifest_root,
            fallback_root=project_root,
            config_path=path,
        ),
        minimal=bool(manifest_payload.get("minimal", False)),
        autodetect_deprecated=bool(manifest_payload.get("autodetect_deprecated", False)),
    )
    validate_manifest(manifest, path)

    build_payload = payload.get("build") or {}
    if "system" not in build_payload:
        raise ValueError(f"Missing required 'build.system' in {path}")
    build = BuildConfig(
        system=build_payload.get("system", "kleaf"),
        target=build_payload.get("target", "//common:kernel_{arch}_dist"),
        warmup_target=build_payload.get("warmup_target"),
        dist_dir=build_payload.get("dist_dir", "out/gki"),
        dist_flag=build_payload.get("dist_flag", "dist_dir"),
        arch=build_payload.get("arch", "aarch64"),
        jobs=build_payload.get("jobs", os.cpu_count() or 1),
        legacy_config=build_payload.get("legacy_config"),
        lto=build_payload.get("lto", "thin"),
    )
    validate_build(build, path)

    cache_payload = payload.get("cache") or {}
    cache = CacheConfig(
        repo_dir=cache_payload.get("repo_dir", "repo"),
        bazel_dir=cache_payload.get("bazel_dir", "bazel"),
        ccache_dir=cache_payload.get("ccache_dir", "ccache"),
    )

    workspace_payload = payload.get("workspace") or {}
    if "metadata_dir" in workspace_payload:
        raise ValueError(f"workspace.metadata_dir is fixed by layout constants and cannot be configured in {path}")
    workspace = WorkspaceConfig(
        source_dir=workspace_payload.get("source_dir", default_source_dir),
    )

    return TargetConfig(
        name=name,
        manifest=manifest,
        build=build,
        cache=cache,
        workspace=workspace,
        config_path=path,
    )


def load_mapping(path: Path) -> dict:
    if path.suffix == ".toml":
        return tomllib.loads(path.read_text(encoding="utf-8")) or {}
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8")) or {}
    if path.suffix in {".yaml", ".yml"}:
        raise ModuleNotFoundError("YAML config requires PyYAML. Prefer TOML configs in this repository.")
    raise ValueError(f"Unsupported config format: {path}")


def validate_manifest(manifest: ManifestConfig, config_path: Path) -> None:
    if manifest.source not in MANIFEST_SOURCES:
        raise ValueError(f"Unsupported manifest source in {config_path}: {manifest.source}")

    if manifest.source == "remote":
        if not manifest.url or not manifest.branch:
            raise ValueError(f"Remote manifest requires url and branch in {config_path}")
        return

    if not manifest.path:
        raise ValueError(f"Local manifest requires 'path' in {config_path}")

    if not manifest.path.exists():
        raise FileNotFoundError(f"Local manifest file not found: {manifest.path}")

    if not manifest.url:
        raise ValueError(f"Local manifest requires url in {config_path}")


def validate_build(build: BuildConfig, config_path: Path) -> None:
    if build.system not in BUILD_SYSTEMS:
        raise ValueError(f"Unsupported build system in {config_path}: {build.system}")
    if build.arch not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture in {config_path}: {build.arch}")
    if build.jobs <= 0:
        raise ValueError(f"Build jobs must be positive in {config_path}: {build.jobs}")
    if build.system != "kleaf" and build.warmup_target:
        raise ValueError(f"build.warmup_target is only supported for kleaf builds in {config_path}")
    if build.dist_flag not in {"dist_dir", "destdir"}:
        raise ValueError(f"Unsupported dist_flag in {config_path}: {build.dist_flag}")


def _resolve_manifest_path(
    value: object,
    *,
    manifest_root: Path | None,
    fallback_root: Path,
    config_path: Path,
) -> Path | None:
    if value is None:
        return None
    if manifest_root is None:
        return resolve_path(fallback_root, str(value) if isinstance(value, str) else None)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid manifest.path in {config_path}: expected non-empty string")
    relative_path = Path(value)
    if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
        raise ValueError(f"Invalid manifest.path in {config_path}: path must stay inside the manifests root")
    return (manifest_root.resolve() / relative_path).resolve()
