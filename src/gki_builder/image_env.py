#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import shutil
import tomllib
from pathlib import Path
from typing import cast

from . import layout
from .utils import discover_project_root


def prepare_runtime_image_layout(
    source_target_file: str | Path,
    *,
    workspace_root: str | Path | None = None,
    output_root: str | Path | None = None,
    project_root: Path | None = None,
) -> None:
    repo_root = discover_project_root(project_root or Path.cwd())
    config_path = _resolve_source_target_file(repo_root, source_target_file)
    resolved_workspace_root = Path(workspace_root or layout.DOCKER_WORK_ROOT).resolve()
    runtime_root = Path(output_root).resolve() if output_root is not None else resolved_workspace_root
    akb_root = layout.akb_root(runtime_root)
    manifests_root = layout.embedded_manifests_root(runtime_root)
    docker_metadata_dir = layout.docker_metadata_root(runtime_root)
    final_docker_metadata_dir = layout.docker_metadata_root(resolved_workspace_root)
    target_metadata_dir = final_docker_metadata_dir / "targets"

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    workspace = payload.get("workspace") or {}
    target_name = payload.get("name", "")
    source_dir = workspace.get("source_dir", "android-kernel")

    akb_root.mkdir(parents=True, exist_ok=True)
    docker_metadata_dir.mkdir(parents=True, exist_ok=True)
    active_target_payload = _prepare_active_target_payload(payload, config_path, manifests_root)

    layout.active_target_file(runtime_root).write_text(
        _dump_toml_document(active_target_payload),
        encoding="utf-8",
    )
    build_payload = cast(dict[str, object], active_target_payload.get("build") or {})
    manifest_payload = cast(dict[str, object], active_target_payload.get("manifest") or {})
    layout.docker_env_file(runtime_root).write_text(
        f"export GKI_TARGET_NAME={target_name}\n"
        f"export GKI_SOURCE_ROOT={resolved_workspace_root / source_dir}\n"
        f"export GKI_BUILD_SYSTEM={build_payload.get('system', '')}\n"
        f"export GKI_BUILD_ARCH={build_payload.get('arch', '')}\n"
        f"export GKI_BUILD_TARGET={build_payload.get('target', '')}\n"
        f"export GKI_WARMUP_TARGET={build_payload.get('warmup_target', '') or ''}\n"
        f"export GKI_DIST_DIR={build_payload.get('dist_dir', '')}\n"
        f"export GKI_DIST_FLAG={build_payload.get('dist_flag', '')}\n"
        f"export GKI_MANIFEST_SOURCE={manifest_payload.get('source', '')}\n"
        f"export GKI_MANIFEST_URL={manifest_payload.get('url', '')}\n"
        f"export GKI_MANIFEST_BRANCH={manifest_payload.get('branch', '')}\n"
        f"export GKI_MANIFEST_FILE={manifest_payload.get('file', '') or ''}\n"
        f"export GKI_MANIFEST_PATH={manifest_payload.get('path', '') or ''}\n"
        f"export GKI_DOCKER_METADATA_ROOT={final_docker_metadata_dir}\n"
        f"export GKI_TARGET_METADATA_ROOT={target_metadata_dir / target_name}\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Docker image target config and env files")
    parser.add_argument(
        "--source-target-file",
        required=True,
        help="Path to the source target definition, relative to the project root or absolute",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(layout.DOCKER_WORK_ROOT),
        help="Workspace root path; defaults to /workspace",
    )
    parser.add_argument(
        "--output-root",
        help="Directory where the stripped runtime workspace layout is written",
    )
    return parser.parse_args()


def _resolve_source_target_file(project_root: Path, source_target_file: str | Path) -> Path:
    path = Path(source_target_file)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _prepare_active_target_payload(
    payload: dict[str, object],
    config_path: Path,
    manifests_root: Path,
) -> dict[str, object]:
    cloned_payload = cast(dict[str, object], _clone_mapping(payload))
    cloned_payload["version"] = 1
    workspace = cloned_payload.get("workspace")
    if isinstance(workspace, dict):
        workspace.pop("metadata_dir", None)
    manifest = cloned_payload.get("manifest")
    if not isinstance(manifest, dict):
        return cloned_payload

    if manifest.get("source") != "local":
        return cloned_payload

    manifest_path_value = manifest.get("path")
    if not isinstance(manifest_path_value, str) or not manifest_path_value:
        return cloned_payload

    source_manifest_path = _resolve_source_manifest_path(config_path, manifest_path_value)
    embedded_manifest_path = _embedded_manifest_relative_path(manifest_path_value)
    manifest_copy_path = manifests_root / embedded_manifest_path
    manifest_copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_manifest_path, manifest_copy_path)
    manifest["path"] = embedded_manifest_path.as_posix()
    return cloned_payload


def _clone_mapping(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clone_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_mapping(item) for item in value]
    return value


def _embedded_manifest_relative_path(value: str) -> Path:
    path = Path(value)
    if path.parts and path.parts[0] == "manifests":
        path = Path(*path.parts[1:])
    return path


def _resolve_source_manifest_path(config_path: Path, manifest_path_value: str) -> Path:
    path = Path(manifest_path_value)
    if path.is_absolute():
        return path.resolve()

    embedded_manifest_path = _embedded_manifest_relative_path(manifest_path_value)
    candidates = [
        (discover_project_root(config_path.parent) / manifest_path_value).resolve(),
        (config_path.parent / "manifests" / embedded_manifest_path).resolve(),
        (config_path.parent.parent / "manifests" / embedded_manifest_path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Local manifest file not found for Docker runtime packaging: {manifest_path_value}")


def _dump_toml_document(payload: dict[str, object]) -> str:
    lines: list[str] = []
    root_scalars = {key: value for key, value in payload.items() if not isinstance(value, dict)}
    sections = {key: value for key, value in payload.items() if isinstance(value, dict)}

    for key, value in root_scalars.items():
        lines.append(f"{key} = {_dump_toml_value(value)}")

    if root_scalars and sections:
        lines.append("")

    section_names = list(sections.keys())
    for index, section_name in enumerate(section_names):
        lines.append(f"[{section_name}]")
        section = sections[section_name]
        assert isinstance(section, dict)
        for key, value in section.items():
            lines.append(f"{key} = {_dump_toml_value(value)}")
        if index != len(section_names) - 1:
            lines.append("")

    return "\n".join(lines) + "\n"


def _dump_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return '""'
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_dump_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value type: {type(value)!r}")


if __name__ == "__main__":
    args = parse_args()
    prepare_runtime_image_layout(args.source_target_file, workspace_root=args.workspace_root, output_root=args.output_root)
