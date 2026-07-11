# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from .global_config import GlobalConfig, load_global_config
from .loader import _parse_target_definition_file, load_mapping, load_target_payload_with_inheritance
from .provider import TargetConfigProvider
from .resolver import load_project_target, resolve_target, resolve_target_name, target_config_path
from .schema import ARCHITECTURES, BuildConfig, KleafBuildConfig, LegacyBuildConfig, RepoConfig, SyncConfig, TargetConfig
from .source import ConfigSource, FilesystemConfigSource
from .validator import validate_build, validate_sync

__all__ = [
    "ARCHITECTURES",
    "BuildConfig",
    "ConfigSource",
    "FilesystemConfigSource",
    "GlobalConfig",
    "KleafBuildConfig",
    "LegacyBuildConfig",
    "RepoConfig",
    "SyncConfig",
    "TargetConfig",
    "TargetConfigProvider",
    "_parse_target_definition_file",
    "load_global_config",
    "load_mapping",
    "load_project_target",
    "load_target_payload_with_inheritance",
    "resolve_target",
    "resolve_target_name",
    "target_config_path",
    "validate_build",
    "validate_sync",
]
