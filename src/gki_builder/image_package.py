#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import shutil
from pathlib import Path
import tomllib

from .utils import ensure_directory, write_json

PACKAGE_ROOT_FILES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
)

PACKAGE_DIRS = (
    "configs",
    "docker",
    "manifests",
    "src",
)

DOCKER_TARGET_BUNDLE_DIR = Path(".docker-target")


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
    shutil.copy2(source_target_file, bundle_root / "target.toml")

    payload = tomllib.loads(source_target_file.read_text(encoding="utf-8")) or {}
    manifest = payload.get("manifest") or {}
    if not isinstance(manifest, dict) or manifest.get("source") != "local":
        return bundle_root

    manifest_path = manifest.get("path")
    if not isinstance(manifest_path, str) or not manifest_path:
        return bundle_root

    source_manifest = _resolve_source_manifest_path(source_target_file, manifest_path)
    destination_manifest = bundle_root / "manifests" / _embedded_manifest_relative_path(manifest_path)
    ensure_directory(destination_manifest.parent)
    shutil.copy2(source_manifest, destination_manifest)
    return bundle_root


def _resolve_source_manifest_path(source_target_file: Path, manifest_path: str) -> Path:
    relative_manifest = _embedded_manifest_relative_path(manifest_path)
    candidates = [
        (source_target_file.parent / "manifests" / relative_manifest).resolve(),
        (source_target_file.parent.parent / "manifests" / relative_manifest).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    project_candidate = (source_target_file.parent / manifest_path).resolve()
    if project_candidate.exists():
        return project_candidate
    project_root_candidate = (source_target_file.parents[2] / manifest_path).resolve() if len(source_target_file.parents) >= 3 else project_candidate
    if project_root_candidate.exists():
        return project_root_candidate
    raise FileNotFoundError(f"Local manifest file not found for Docker target bundle: {manifest_path}")


def _embedded_manifest_relative_path(value: str) -> Path:
    path = Path(value)
    if path.parts and path.parts[0] == "manifests":
        path = Path(*path.parts[1:])
    return path
