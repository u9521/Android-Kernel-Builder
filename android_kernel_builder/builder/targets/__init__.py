# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from .loaders import _parse_target_definition_file, load_mapping, load_target_payload_with_inheritance
from .models import ARCHITECTURES, MANIFEST_SOURCES, BuildConfig, ManifestConfig, TargetConfig
from .store import load_project_target, resolve_target, resolve_target_name, target_config_path
from .validation import validate_build, validate_manifest

__all__ = [
    "ARCHITECTURES",
    "MANIFEST_SOURCES",
    "BuildConfig",
    "ManifestConfig",
    "TargetConfig",
    "_parse_target_definition_file",
    "load_mapping",
    "load_project_target",
    "load_target_payload_with_inheritance",
    "resolve_target",
    "resolve_target_name",
    "target_config_path",
    "validate_build",
    "validate_manifest",
]
