#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from .targets import load_target_payload_with_inheritance
from .utils import ensure_directory, write_json

PACKAGE_ROOT_FILES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
)

PACKAGE_DIRS = (
    "configs",
    "docker",
    "src",
)

DOCKER_TARGET_BUNDLE_DIR = Path(".docker-target")
DOCKER_TARGET_MANIFEST_FILE = Path("manifest.xml")


def package_image_context(repo_root: Path, output_dir: Path, source_target_file: Path | None = None) -> dict[str, object]:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()

    if output_dir.exists():
        shutil.rmtree(output_dir)
    ensure_directory(output_dir)

    packaged_files: list[str] = []
    for relative_path in PACKAGE_ROOT_FILES:
        source_path = repo_root / relative_path
        destination_path = output_dir / relative_path
        shutil.copy2(source_path, destination_path)
        packaged_files.append(relative_path)

    for relative_path in PACKAGE_DIRS:
        source_path = repo_root / relative_path
        destination_path = output_dir / relative_path
        shutil.copytree(source_path, destination_path)
        packaged_files.extend(_list_relative_files(destination_path, output_dir))

    target_bundle_root = None
    if source_target_file is not None:
        target_bundle_root = _package_selected_target_bundle(source_target_file.resolve(), output_dir)
        packaged_files.extend(_list_relative_files(target_bundle_root, output_dir))

    manifest = {
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "included_roots": list(PACKAGE_ROOT_FILES + PACKAGE_DIRS),
        "files": sorted(packaged_files),
    }
    if target_bundle_root is not None:
        manifest["target_bundle_root"] = str(target_bundle_root.relative_to(output_dir))
    write_json(output_dir / ".gki-image-package.json", manifest)
    return manifest


def _list_relative_files(path: Path, root: Path) -> list[str]:
    return [str(child.relative_to(root)) for child in path.rglob("*") if child.is_file()]


def _package_selected_target_bundle(source_target_file: Path, output_dir: Path) -> Path:
    bundle_root = ensure_directory(output_dir / DOCKER_TARGET_BUNDLE_DIR)
    payload, inheritance_chain = load_target_payload_with_inheritance(source_target_file)
    compact_payload = _compact_target_payload(payload)
    manifest = compact_payload.get("manifest") or {}
    if isinstance(manifest, dict) and manifest.get("source") == "local":
        manifest_path = manifest.get("path")
        if isinstance(manifest_path, str) and manifest_path:
            source_manifest = _resolve_source_manifest_path(source_target_file, manifest_path)
            destination_manifest = bundle_root / DOCKER_TARGET_MANIFEST_FILE
            shutil.copy2(source_manifest, destination_manifest)
            manifest["path"] = DOCKER_TARGET_MANIFEST_FILE.as_posix()

    target_file = bundle_root / "target.toml"
    target_file.write_text(
        _render_generated_target_toml(source_target_file, inheritance_chain, compact_payload),
        encoding="utf-8",
    )
    return bundle_root


def _resolve_source_manifest_path(source_target_file: Path, manifest_path: str) -> Path:
    search_root = _manifest_search_root(source_target_file)
    relative_manifest = _embedded_manifest_relative_path(manifest_path)
    candidate = (search_root / relative_manifest).resolve()
    try:
        candidate.relative_to(search_root)
    except ValueError as error:
        raise ValueError(
            f"Invalid manifest.path in {source_target_file}: path must stay inside search root {search_root}"
        ) from error
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Local manifest file not found for Docker target bundle: {manifest_path} (search root: {search_root})"
    )


def _embedded_manifest_relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"Invalid local manifest path '{value}': must be relative to configs/manifests")
    return path


def _manifest_search_root(source_target_file: Path) -> Path:
    return (source_target_file.parent.parent / "manifests").resolve()


def _compact_target_payload(payload: dict[str, object]) -> dict[str, object]:
    compact: dict[str, object] = {}
    for key in ("name", "manifest", "build", "workspace"):
        if key not in payload:
            continue
        compact[key] = _clone_mapping(payload[key])
    return compact


def _clone_mapping(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clone_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_mapping(item) for item in value]
    return value


def _render_generated_target_toml(
    source_target_file: Path,
    inheritance_chain: list[Path],
    payload: dict[str, object],
) -> str:
    lines = [
        "# AUTO-GENERATED by gki-builder image packaging. Do not edit.",
        f"# Source target file: {source_target_file.name}",
        "# Inheritance chain (base -> leaf):",
    ]
    for chain_path in inheritance_chain:
        lines.append(f"# - {chain_path.name}")
    lines.append("")
    lines.append(_dump_toml_document(payload).rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


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
        section_mapping = cast(dict[str, object], section)
        for key, value in section_mapping.items():
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
