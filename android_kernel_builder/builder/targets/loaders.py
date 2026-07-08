# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib

from ..build_systems import get_build_system_spec
from ..utils import resolve_path
from .models import BuildConfig, ManifestConfig, TargetConfig
from .validation import validate_build, validate_manifest


def _parse_target_definition_file(
    config_path: str | Path,
    *,
    manifest_root: Path | None = None,
) -> TargetConfig:
    path = Path(config_path).resolve()
    payload = _load_target_payload(path)

    if "workspace" in payload:
        raise ValueError(f"workspace paths are fixed and cannot be configured in {path}")

    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"Missing required 'name' in {path}")

    manifest_payload_obj = payload.get("manifest")
    if manifest_payload_obj is None:
        manifest_payload: dict[str, object] = {}
    elif isinstance(manifest_payload_obj, dict):
        manifest_payload = manifest_payload_obj
    else:
        raise ValueError(f"Invalid 'manifest' table in {path}: expected mapping")
    manifest = ManifestConfig(
        source=_required_string(manifest_payload.get("source", "remote"), field="manifest.source", config_path=path),
        url=_optional_string(manifest_payload.get("url"), field="manifest.url", config_path=path),
        branch=_optional_string(manifest_payload.get("branch"), field="manifest.branch", config_path=path),
        file=_optional_string(manifest_payload.get("file"), field="manifest.file", config_path=path),
        path=_resolve_manifest_path(
            manifest_payload.get("path"),
            manifest_root=manifest_root,
            fallback_root=path.parent,
            config_path=path,
        ),
        minimal=_required_bool(manifest_payload.get("minimal", False), field="manifest.minimal", config_path=path),
        autodetect_deprecated=_required_bool(
            manifest_payload.get("autodetect_deprecated", False),
            field="manifest.autodetect_deprecated",
            config_path=path,
        ),
    )
    validate_manifest(manifest, path)

    build_payload_obj = payload.get("build")
    if build_payload_obj is None:
        build_payload: dict[str, object] = {}
    elif isinstance(build_payload_obj, dict):
        build_payload = build_payload_obj
    else:
        raise ValueError(f"Invalid 'build' table in {path}: expected mapping")
    if "system" not in build_payload:
        raise ValueError(f"Missing required 'build.system' in {path}")
    build_system = _required_string(build_payload.get("system", "kleaf"), field="build.system", config_path=path)
    build_spec = get_build_system_spec(build_system)
    use_ccache_default = build_spec.default_use_ccache if build_spec is not None else False
    build = BuildConfig(
        system=build_system,
        target=_required_string(build_payload.get("target", "//common:kernel_{arch}_dist"), field="build.target", config_path=path),
        warmup_target=_optional_string(build_payload.get("warmup_target"), field="build.warmup_target", config_path=path),
        dist_dir=_required_string(build_payload.get("dist_dir", ""), field="build.dist_dir", config_path=path),
        dist_flag=_required_string(build_payload.get("dist_flag", "dist_dir"), field="build.dist_flag", config_path=path),
        arch=_required_string(build_payload.get("arch", "aarch64"), field="build.arch", config_path=path),
        jobs=_required_int(build_payload.get("jobs", os.cpu_count() or 1), field="build.jobs", config_path=path),
        legacy_config=_optional_string(build_payload.get("legacy_config"), field="build.legacy_config", config_path=path),
        lto=_optional_string(build_payload.get("lto", "thin"), field="build.lto", config_path=path),
        use_ccache=_required_bool(build_payload.get("use_ccache", use_ccache_default), field="build.use_ccache", config_path=path),
    )
    validate_build(build, path)

    return TargetConfig(
        name=name,
        manifest=manifest,
        build=build,
        config_path=path,
    )


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
