# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from ...usage_report import write_usage_report, write_warmup_outputs
from ...utils import ensure_directory
from ..config import KleafBuildConfig, LegacyBuildConfig, TargetConfig
from ..sync import build_environment
from .engines import kleaf, legacy


def build_kernel(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_root: Path,
) -> Path:
    source_dir = source_dir.resolve()
    cache_root = cache_root.resolve()
    output_dir = ensure_directory((output_root / target.build.dist_dir).resolve())
    env = build_environment()

    if isinstance(target.build, KleafBuildConfig):
        kleaf.build(target.build, source_dir, cache_root, output_dir, env)
    elif isinstance(target.build, LegacyBuildConfig):
        legacy.build(target.build, source_dir, cache_root, output_dir, env)
    else:
        raise TypeError(f"Unsupported build config in {target.config_path}: {type(target.build).__name__}")

    write_usage_report(target, source_dir, cache_root, output_dir)
    return output_dir


def warmup_kernel(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_root: Path,
) -> Path:
    source_dir = source_dir.resolve()
    cache_root = cache_root.resolve()
    output_dir = ensure_directory((output_root / target.build.dist_dir).resolve())
    env = build_environment()

    if isinstance(target.build, KleafBuildConfig):
        exported_files = kleaf.warmup(target.build, source_dir, cache_root, output_dir, env)
    elif isinstance(target.build, LegacyBuildConfig):
        exported_files = legacy.warmup(target.build, source_dir, cache_root, output_dir, env)
    else:
        raise TypeError(f"Unsupported build config in {target.config_path}: {type(target.build).__name__}")

    if exported_files is not None:
        write_warmup_outputs(target, source_dir, output_dir, exported_files)

    write_usage_report(target, source_dir, cache_root, output_dir)
    return output_dir
