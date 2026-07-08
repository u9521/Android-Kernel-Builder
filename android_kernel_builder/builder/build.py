# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .build_systems import kleaf, legacy
from .targets import TargetConfig
from .utils import ensure_directory
from .code_sync import build_environment
from .usage_report import write_usage_report, write_warmup_outputs


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

    if target.build.system == "kleaf":
        kleaf.build(target, source_dir, cache_root, output_dir, env)
    elif target.build.system == "legacy":
        legacy.build(target, source_dir, cache_root, output_dir, env)
    else:
        raise ValueError(f"Unsupported build system in {target.config_path}: {target.build.system}")

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

    if target.build.system == "kleaf":
        exported_files = kleaf.warmup(target, source_dir, cache_root, output_dir, env)
    elif target.build.system == "legacy":
        exported_files = legacy.warmup(target, source_dir, cache_root, output_dir, env)
    else:
        raise ValueError(f"Unsupported build system in {target.config_path}: {target.build.system}")

    if exported_files is not None:
        write_warmup_outputs(target, source_dir, output_dir, exported_files)

    write_usage_report(target, source_dir, cache_root, output_dir)
    return output_dir
