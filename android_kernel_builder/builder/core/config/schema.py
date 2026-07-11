# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import TypeAlias


ARCHITECTURES = ("aarch64", "x86_64")


@dataclass(slots=True)
class RepoConfig:
    url: str | None = None
    branch: str | None = None
    file: str | None = None
    path: Path | None = None
    minimal: bool = False
    autodetect_deprecated: bool = False


SyncConfig: TypeAlias = RepoConfig


@dataclass(slots=True)
class KleafBuildConfig:
    target: str = "//common:kernel_{arch}_dist"
    warmup_target: str | None = None
    dist_dir: str = ""
    dist_flag: str = "dist_dir"
    arch: str = "aarch64"
    jobs: int = os.cpu_count() or 1
    lto: str | None = "thin"


@dataclass(slots=True)
class LegacyBuildConfig:
    legacy_config: str
    dist_dir: str = ""
    arch: str = "aarch64"
    jobs: int = os.cpu_count() or 1
    lto: str | None = "thin"
    use_ccache: bool = True


BuildConfig: TypeAlias = KleafBuildConfig | LegacyBuildConfig


@dataclass(slots=True)
class TargetConfig:
    name: str
    sync: SyncConfig
    build: BuildConfig
    config_path: Path
