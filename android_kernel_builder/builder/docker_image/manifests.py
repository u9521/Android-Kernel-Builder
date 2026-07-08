# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path


def embedded_manifest_relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"Invalid local manifest path '{value}': must be relative to configs/manifests")
    return path


def resolve_source_manifest_path(config_path: Path, manifest_path: str, search_root: Path) -> Path:
    relative_manifest = embedded_manifest_relative_path(manifest_path)
    candidate = (search_root / relative_manifest).resolve()
    try:
        candidate.relative_to(search_root)
    except ValueError as error:
        raise ValueError(
            f"Invalid manifest.path in {config_path}: path must stay inside search root {search_root}"
        ) from error
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Local manifest file not found for Docker image packaging: {manifest_path} (search root: {search_root})"
    )
