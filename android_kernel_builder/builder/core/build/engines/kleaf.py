# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .... import layout
from ....utils import ensure_directory, run_command
from ...config import KleafBuildConfig
from .common import resolve_build_jobs


def build(
    config: KleafBuildConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> None:
    bazel_output_base = ensure_directory(bazel_output_base_path(cache_root))
    bazel_repository_cache = ensure_directory(bazel_repository_cache_path(cache_root))
    bazel_disk_cache = ensure_directory(bazel_disk_cache_path(cache_root))
    kleaf_cache_dir = ensure_directory(kleaf_cache_dir_path(cache_root))
    jobs = resolve_build_jobs(config)
    bazel_binary = source_dir / "tools/bazel"
    if not bazel_binary.exists():
        raise FileNotFoundError(
            f"Missing required bazel launcher: {bazel_binary}. This project expects Kleaf trees to provide tools/bazel."
        )

    command = [
        str(bazel_binary),
        f"--output_base={bazel_output_base}",
        "run",
        f"--repository_cache={bazel_repository_cache}",
        f"--disk_cache={bazel_disk_cache}",
        f"--jobs={jobs}",
        "--config=fast",
        "--config=local",
        f"--cache_dir={kleaf_cache_dir}",
        "--verbose_failures",
    ]
    if config.lto:
        command.append(f"--lto={config.lto}")

    command.append(config.target.format(arch=config.arch))
    command.extend(["--", f"--{config.dist_flag}={output_dir}"])
    run_bazel_command(command, bazel_binary, bazel_output_base, cwd=source_dir, env=env)


def warmup(
    config: KleafBuildConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]] | None:
    if config.warmup_target is None:
        build(config, source_dir, cache_root, output_dir, env)
        return None
    warmup_target(config, source_dir, cache_root, env)
    return export_warmup_outputs(config, source_dir, cache_root, output_dir, env)


def warmup_target(
    config: KleafBuildConfig,
    source_dir: Path,
    cache_root: Path,
    env: dict[str, str],
) -> None:
    target_name = config.warmup_target
    if target_name is None:
        raise ValueError("Kleaf warmup requires build.warmup_target")

    bazel_output_base = ensure_directory(bazel_output_base_path(cache_root))
    bazel_repository_cache = ensure_directory(bazel_repository_cache_path(cache_root))
    bazel_disk_cache = ensure_directory(bazel_disk_cache_path(cache_root))
    kleaf_cache_dir = ensure_directory(kleaf_cache_dir_path(cache_root))
    jobs = resolve_build_jobs(config)
    bazel_binary = source_dir / "tools/bazel"
    if not bazel_binary.exists():
        raise FileNotFoundError(
            f"Missing required bazel launcher: {bazel_binary}. This project expects Kleaf trees to provide tools/bazel."
        )

    command = [
        str(bazel_binary),
        f"--output_base={bazel_output_base}",
        "build",
        f"--repository_cache={bazel_repository_cache}",
        f"--disk_cache={bazel_disk_cache}",
        f"--jobs={jobs}",
        "--config=fast",
        "--config=local",
        f"--cache_dir={kleaf_cache_dir}",
        "--verbose_failures",
    ]
    if config.lto:
        command.append(f"--lto={config.lto}")

    command.append(target_name.format(arch=config.arch))
    run_bazel_command(command, bazel_binary, bazel_output_base, cwd=source_dir, env=env)


def export_warmup_outputs(
    config: KleafBuildConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]]:
    files = query_warmup_outputs(config, source_dir, cache_root, env)
    exported_files: list[dict[str, str]] = []
    for relative_output in files:
        source_path = (source_dir / relative_output).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Warmup output not found: {source_path}")

        export_relative_path = warmup_export_path(relative_output)
        destination_path = (output_dir / export_relative_path).resolve()
        ensure_directory(destination_path.parent)
        shutil.copy2(source_path, destination_path)
        exported_files.append({
            "source": str(source_path),
            "path": str(destination_path),
        })

    print(f"exported {len(exported_files)} warmup artifacts to {output_dir}", flush=True)
    return exported_files


def query_warmup_outputs(
    config: KleafBuildConfig,
    source_dir: Path,
    cache_root: Path,
    env: dict[str, str],
) -> list[str]:
    target_name = config.warmup_target
    if target_name is None:
        raise ValueError("Kleaf warmup requires build.warmup_target")

    bazel_binary = source_dir / "tools/bazel"
    bazel_output_base = bazel_output_base_path(cache_root)
    result = run_bazel_command(
        [
            str(bazel_binary),
            f"--output_base={bazel_output_base}",
            "cquery",
            f"--repository_cache={bazel_repository_cache_path(cache_root)}",
            f"--disk_cache={bazel_disk_cache_path(cache_root)}",
            "--output=files",
            "--config=fast",
            "--config=local",
            f"--cache_dir={kleaf_cache_dir_path(cache_root)}",
            target_name.format(arch=config.arch),
        ],
        bazel_binary,
        bazel_output_base,
        cwd=source_dir,
        env=env,
        capture_output=True,
    )
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


def run_bazel_command(
    command: list[str],
    bazel_binary: Path,
    bazel_output_base: Path,
    *,
    cwd: Path,
    env: dict[str, str],
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return run_command(command, cwd=cwd, env=env, capture_output=capture_output)
    finally:
        run_command(
            [str(bazel_binary), f"--output_base={bazel_output_base}", "shutdown"],
            cwd=cwd,
            env=env,
            check=False,
        )


def warmup_export_path(relative_output: str) -> Path:
    marker = "/bin/"
    if marker in relative_output:
        return Path(relative_output.split(marker, 1)[1])
    return Path(relative_output)


def bazel_output_base_path(cache_root: Path) -> Path:
    return layout.target_bazel_state_dir(cache_root).resolve()


def bazel_repository_cache_path(cache_root: Path) -> Path:
    return layout.target_bazel_repository_cache_dir(cache_root).resolve()


def bazel_disk_cache_path(cache_root: Path) -> Path:
    return layout.target_bazel_disk_cache_dir(cache_root).resolve()


def kleaf_cache_dir_path(cache_root: Path) -> Path:
    return layout.target_kleaf_cache_root(cache_root).resolve()
