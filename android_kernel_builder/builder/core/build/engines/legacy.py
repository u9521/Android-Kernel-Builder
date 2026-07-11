# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .... import layout
from ....utils import ensure_directory, run_command
from ...config import LegacyBuildConfig
from .common import resolve_build_jobs


def build(
    config: LegacyBuildConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> None:
    legacy_config = config.legacy_config
    if not legacy_config:
        raise ValueError("Legacy build requires build.legacy_config")
    jobs = resolve_build_jobs(config)
    base_cmdline = ["bash", "build/build.sh", f"-j{jobs}"]
    env = env.copy()
    env.update({
        "BUILD_CONFIG": legacy_config.format(arch=config.arch),
        "DIST_DIR": str(output_dir),
    })
    if config.lto:
        env["LTO"] = config.lto

    if not config.use_ccache:
        run_command(base_cmdline, cwd=source_dir, env=env)
        return

    env["CCACHE_DIR"] = str(layout.target_ccache_cache_root(cache_root).resolve())
    env["CCACHE_COMPILERCHECK"] = "none"
    ccache_clang = create_ccache_clang_symlink(cache_root, env)
    base_cmdline.append(f"CC={ccache_clang}")
    run_command(base_cmdline, cwd=source_dir, env=env)
    print_ccache_stats(env)


def warmup(
    config: LegacyBuildConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]] | None:
    build(config, source_dir, cache_root, output_dir, env)
    return None


def create_ccache_clang_symlink(cache_root: Path, env: dict[str, str]) -> Path:
    ccache_binary = shutil.which("ccache", path=env.get("PATH"))
    if ccache_binary is None:
        raise FileNotFoundError("Legacy build requires ccache, but no ccache executable was found in PATH")

    ensure_directory(layout.ccache_tools_root(cache_root))
    link_path = layout.ccache_clang_link(cache_root)
    resolved_ccache_binary = Path(ccache_binary).resolve()

    if link_path.is_symlink():
        if link_path.resolve() == resolved_ccache_binary:
            return link_path.absolute()
        link_path.unlink()
    elif link_path.exists():
        raise FileExistsError(f"Cannot create ccache clang symlink because {link_path} already exists and is not a symlink")

    os.symlink(resolved_ccache_binary, link_path)
    return link_path.absolute()


def print_ccache_stats(env: dict[str, str]) -> None:
    print("ccache stats:", flush=True)
    try:
        result = run_command(["ccache", "-s"], env=env, check=False, capture_output=True)
    except FileNotFoundError:
        print("(ccache not found)", flush=True)
        return
    output = result.stdout.strip() if isinstance(result.stdout, str) else ""
    if output:
        print(output, flush=True)
        return
    print("(no ccache output)", flush=True)
