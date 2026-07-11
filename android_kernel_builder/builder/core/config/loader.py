# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib

from ...utils import resolve_path
from .schema import BuildConfig, KleafBuildConfig, LegacyBuildConfig, RepoConfig, SyncConfig, TargetConfig
from .validator import validate_build, validate_sync

_BUILD_BACKENDS = ("kleaf", "legacy")
_KLEAF_BUILD_KEYS = {"target", "warmup_target", "dist_dir", "dist_flag", "arch", "jobs", "lto"}
_LEGACY_BUILD_KEYS = {"legacy_config", "dist_dir", "arch", "jobs", "lto", "use_ccache"}
_REPO_KEYS = {"url", "branch", "file", "path", "minimal", "autodetect_deprecated"}


def _parse_target_definition_file(
    config_path: str | Path,
    *,
    manifest_root: Path | None = None,
) -> TargetConfig:
    path = Path(config_path).resolve()
    payload = _load_target_payload(path)

    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"Missing required 'name' in {path}")

    sync = _parse_sync_config(payload.get("repo"), path, manifest_root=manifest_root)
    validate_sync(sync, path)

    build = _parse_build_config(payload, path)
    validate_build(build, path)

    return TargetConfig(
        name=name,
        sync=sync,
        build=build,
        config_path=path,
    )


def _parse_sync_config(value: object, config_path: Path, *, manifest_root: Path | None) -> SyncConfig:
    if value is None:
        raise ValueError(f"Missing required 'repo' table in {config_path}")
    if not isinstance(value, dict):
        raise ValueError(f"Invalid 'repo' table in {config_path}: expected mapping")
    _reject_unknown_keys(value, _REPO_KEYS, "repo", config_path)
    return RepoConfig(
        url=_optional_string(value.get("url"), field="repo.url", config_path=config_path),
        branch=_optional_string(value.get("branch"), field="repo.branch", config_path=config_path),
        file=_optional_string(value.get("file"), field="repo.file", config_path=config_path),
        path=_resolve_repo_path(
            value.get("path"),
            manifest_root=manifest_root,
            fallback_root=config_path.parent,
            config_path=config_path,
        ),
        minimal=_required_bool(value.get("minimal", False), field="repo.minimal", config_path=config_path),
        autodetect_deprecated=_required_bool(
            value.get("autodetect_deprecated", False),
            field="repo.autodetect_deprecated",
            config_path=config_path,
        ),
    )


def _parse_build_config(payload: dict[str, object], config_path: Path) -> BuildConfig:
    value: dict[str, object] = payload
    if value is None:
        raise ValueError(f"Missing build backend in {config_path}")
    if not isinstance(value, dict):
        raise ValueError(f"Invalid target config in {config_path}: expected mapping")

    configured_backends = [backend for backend in _BUILD_BACKENDS if isinstance(value.get(backend), dict)]
    if len(configured_backends) != 1:
        raise ValueError(f"Expected exactly one build backend in {config_path}: [kleaf] or [legacy]")

    backend = configured_backends[0]
    backend_payload = value[backend]
    if not isinstance(backend_payload, dict):
        raise ValueError(f"Invalid '{backend}' table in {config_path}: expected mapping")
    if backend == "kleaf":
        return _parse_kleaf_build(backend_payload, config_path)
    return _parse_legacy_build(backend_payload, config_path)


def _parse_kleaf_build(payload: dict[str, object], config_path: Path) -> KleafBuildConfig:
    _reject_unknown_keys(payload, _KLEAF_BUILD_KEYS, "kleaf", config_path)
    return KleafBuildConfig(
        target=_required_string(payload.get("target", "//common:kernel_{arch}_dist"), field="kleaf.target", config_path=config_path),
        warmup_target=_optional_string(payload.get("warmup_target"), field="kleaf.warmup_target", config_path=config_path),
        dist_dir=_required_string(payload.get("dist_dir", ""), field="kleaf.dist_dir", config_path=config_path),
        dist_flag=_required_string(payload.get("dist_flag", "dist_dir"), field="kleaf.dist_flag", config_path=config_path),
        arch=_required_string(payload.get("arch", "aarch64"), field="kleaf.arch", config_path=config_path),
        jobs=_required_int(payload.get("jobs", os.cpu_count() or 1), field="kleaf.jobs", config_path=config_path),
        lto=_optional_string(payload.get("lto", "thin"), field="kleaf.lto", config_path=config_path),
    )


def _parse_legacy_build(payload: dict[str, object], config_path: Path) -> LegacyBuildConfig:
    _reject_unknown_keys(payload, _LEGACY_BUILD_KEYS, "legacy", config_path)
    legacy_config = _required_string(payload.get("legacy_config"), field="legacy.legacy_config", config_path=config_path)
    return LegacyBuildConfig(
        legacy_config=legacy_config,
        dist_dir=_required_string(payload.get("dist_dir", ""), field="legacy.dist_dir", config_path=config_path),
        arch=_required_string(payload.get("arch", "aarch64"), field="legacy.arch", config_path=config_path),
        jobs=_required_int(payload.get("jobs", os.cpu_count() or 1), field="legacy.jobs", config_path=config_path),
        lto=_optional_string(payload.get("lto", "thin"), field="legacy.lto", config_path=config_path),
        use_ccache=_required_bool(payload.get("use_ccache", True), field="legacy.use_ccache", config_path=config_path),
    )


def _reject_unknown_keys(payload: dict[str, object], allowed_keys: set[str], section: str, config_path: Path) -> None:
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        joined = ", ".join(unknown_keys)
        raise ValueError(f"Unsupported {section} field in {config_path}: {joined}")


def load_mapping(path: Path) -> dict[str, object]:
    raw_payload: object
    if path.suffix == ".toml":
        raw_payload = tomllib.loads(path.read_text(encoding="utf-8")) or {}
    elif path.suffix == ".json":
        raw_payload = json.loads(path.read_text(encoding="utf-8")) or {}
    elif path.suffix in {".yaml", ".yml"}:
        raise ModuleNotFoundError("YAML config requires PyYAML. Prefer TOML configs in this repository.")
    else:
        raise ValueError(f"Unsupported config format: {path}")

    if not isinstance(raw_payload, dict):
        raise ValueError(f"Target config must be a mapping: {path}")
    return raw_payload


def _load_target_payload(path: Path, *, stack: tuple[Path, ...] = ()) -> dict[str, object]:
    payload, _ = _load_target_payload_with_chain(path, stack=stack)
    return payload


def load_target_payload_with_inheritance(config_path: str | Path) -> tuple[dict[str, object], list[Path]]:
    return _load_target_payload_with_chain(Path(config_path).resolve())


def _load_target_payload_with_chain(
    path: Path,
    *,
    stack: tuple[Path, ...] = (),
) -> tuple[dict[str, object], list[Path]]:
    resolved_path = path.resolve()
    if resolved_path in stack:
        cycle_paths = [*stack, resolved_path]
        cycle_text = " -> ".join(str(candidate) for candidate in cycle_paths)
        raise ValueError(f"Circular target inheritance detected: {cycle_text}")

    payload = load_mapping(resolved_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Target config must be a mapping: {resolved_path}")

    extends_value = payload.get("extends")
    if extends_value is None:
        return payload, [resolved_path]

    parent_path = _resolve_extends_path(resolved_path, extends_value)
    if not parent_path.exists():
        raise FileNotFoundError(f"Parent target config not found: {parent_path}")

    parent_payload, parent_chain = _load_target_payload_with_chain(parent_path, stack=(*stack, resolved_path))
    child_payload = dict(payload)
    child_payload.pop("extends", None)
    return _merge_payload(parent_payload, child_payload), [*parent_chain, resolved_path]


def _resolve_extends_path(config_path: Path, extends_value: object) -> Path:
    if not isinstance(extends_value, str) or not extends_value.strip():
        raise ValueError(f"Invalid extends in {config_path}: expected non-empty string")

    extends_text = extends_value.strip()
    relative_path = Path(extends_text)
    if (
        relative_path.is_absolute()
        or any(part == ".." for part in relative_path.parts)
        or len(relative_path.parts) != 1
        or extends_text.endswith(".toml")
    ):
        raise ValueError(
            f"Invalid extends in {config_path}: expected target name like 'android14-6.1'"
        )

    return (config_path.parent / f"{extends_text}.toml").resolve()


def _merge_payload(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _merge_payload(base_value, value)
            continue
        merged[key] = value
    return merged


def _required_string(value: object, *, field: str, config_path: Path) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f"Invalid {field} in {config_path}: expected string")


def _optional_string(value: object, *, field: str, config_path: Path) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"Invalid {field} in {config_path}: expected string or null")


def _required_bool(value: object, *, field: str, config_path: Path) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Invalid {field} in {config_path}: expected boolean")


def _required_int(value: object, *, field: str, config_path: Path) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"Invalid {field} in {config_path}: expected integer")


def _resolve_repo_path(
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
        raise ValueError(f"Invalid repo.path in {config_path}: expected non-empty string")
    relative_path = Path(value)
    if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
        raise ValueError(f"Invalid repo.path in {config_path}: path must stay inside the manifests root")
    return (manifest_root.resolve() / relative_path).resolve()
