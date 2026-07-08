# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


ARCHITECTURES = ("aarch64", "x86_64")
MANIFEST_SOURCES = ("remote", "local")


@dataclass(slots=True)
class ManifestConfig:
    source: str
    url: str | None = None
    branch: str | None = None
    file: str | None = None
    path: Path | None = None
    minimal: bool = False
    autodetect_deprecated: bool = False


@dataclass(slots=True)
class BuildConfig:
    system: str = "kleaf"
    target: str = "//common:kernel_{arch}_dist"
    warmup_target: str | None = None
    dist_dir: str = ""
    dist_flag: str = "dist_dir"
    arch: str = "aarch64"
    jobs: int = os.cpu_count() or 1
    legacy_config: str | None = None
    lto: str | None = "thin"
    use_ccache: bool = True


@dataclass(slots=True)
class TargetConfig:
    name: str
    manifest: ManifestConfig
    build: BuildConfig
    config_path: Path
