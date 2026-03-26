# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import os
from pathlib import Path

from .targets import TargetConfig
from .utils import ensure_directory, run_command
from .workspace import build_environment


def resolve_build_jobs(target: TargetConfig) -> int:
    return target.build.jobs or (os.cpu_count() or 1)


def build_kernel(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_root: Path,
) -> Path:
    source_dir = (workspace_root / target.workspace.source_dir).resolve()
    cache_root = cache_root.resolve()
    output_dir = ensure_directory((output_root / target.build.dist_dir).resolve())
    env = build_environment(target, cache_root)

    if target.build.system == "legacy":
        _build_legacy(target, source_dir, output_dir, env)
    else:
        _build_kleaf(target, source_dir, cache_root, output_dir, env)

    return output_dir


def _build_legacy(
    target: TargetConfig,
    source_dir: Path,
    output_dir: Path,
    env: dict[str, str],
) -> None:
    legacy_config = target.build.legacy_config
    if not legacy_config:
        raise ValueError("Legacy build requires build.legacy_config")

    jobs = resolve_build_jobs(target)
    env = env.copy()
    env.update({
        "BUILD_CONFIG": legacy_config,
        "DIST_DIR": str(output_dir),
        "CC": "ccache clang",
        "MAKEFLAGS": f"-j{jobs}",
    })
    if target.build.lto:
        env["LTO"] = target.build.lto

    run_command(["bash", "build/build.sh"], cwd=source_dir, env=env)


def _build_kleaf(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> None:
    bazel_cache = ensure_directory(cache_root / target.cache.bazel_dir)
    jobs = resolve_build_jobs(target)
    bazel_binary = source_dir / "tools/bazel"
    if not bazel_binary.exists():
        raise FileNotFoundError(
            f"Missing required bazel launcher: {bazel_binary}. This project expects Kleaf trees to provide tools/bazel."
        )

    command = [
        str(bazel_binary),
        "run",
        f"--disk_cache={bazel_cache}",
        f"--jobs={jobs}",
        "--config=fast",
        "--config=stamp",
        "--verbose_failures",
    ]
    if target.build.lto:
        command.append(f"--lto={target.build.lto}")

    command.append(target.build.target.format(arch=target.build.arch))
    command.extend(["--", f"--{target.build.dist_flag}={output_dir}"])
    run_command(command, cwd=source_dir, env=env)
