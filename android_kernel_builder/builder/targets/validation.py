# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from ..build_systems import get_build_system_spec, supported_build_systems
from .models import ARCHITECTURES, MANIFEST_SOURCES, BuildConfig, ManifestConfig


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
    if build.system not in supported_build_systems():
        raise ValueError(f"Unsupported build system in {config_path}: {build.system}")
    build_spec = get_build_system_spec(build.system)
    if build_spec is None:
        raise ValueError(f"Unsupported build system in {config_path}: {build.system}")
    if build.arch not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture in {config_path}: {build.arch}")
    if build.jobs <= 0:
        raise ValueError(f"Build jobs must be positive in {config_path}: {build.jobs}")
    if not build_spec.supports_warmup and build.warmup_target:
        raise ValueError(f"build.warmup_target is only supported for kleaf builds in {config_path}")
    if build.dist_flag not in {"dist_dir", "destdir"}:
        raise ValueError(f"Unsupported dist_flag in {config_path}: {build.dist_flag}")
    if not build_spec.supports_ccache and build.use_ccache:
        raise ValueError(f"build.use_ccache=true is only supported for legacy builds in {config_path}")
