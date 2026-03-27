# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .targets import TargetConfig
from .utils import directory_size_bytes, ensure_directory, format_bytes, run_command, write_json
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

    usage_report = analyze_workspace_usage(target, workspace_root.resolve(), cache_root, output_dir)
    metadata_dir = ensure_directory((workspace_root / target.workspace.metadata_dir / target.name).resolve())
    write_json(metadata_dir / "disk-usage.json", usage_report)
    _print_usage_report(usage_report)

    return output_dir


def warmup_kernel(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_root: Path,
) -> Path:
    if target.build.system != "kleaf" or not target.build.warmup_target:
        return build_kernel(target, workspace_root, cache_root, output_root)

    source_dir = (workspace_root / target.workspace.source_dir).resolve()
    cache_root = cache_root.resolve()
    output_dir = ensure_directory((output_root / target.build.dist_dir).resolve())
    env = build_environment(target, cache_root)
    _warmup_kleaf(target, source_dir, cache_root, env)
    exported_files = _export_warmup_kleaf_outputs(target, source_dir, output_dir, env)

    metadata_dir = ensure_directory((workspace_root / target.workspace.metadata_dir / target.name).resolve())
    write_json(
        metadata_dir / "warmup-outputs.json",
        {
            "target": target.name,
            "warmup_target": target.build.warmup_target,
            "output_dir": str(output_dir),
            "files": exported_files,
        },
    )
    usage_report = analyze_workspace_usage(target, workspace_root.resolve(), cache_root, output_dir)
    write_json(metadata_dir / "disk-usage.json", usage_report)
    _print_usage_report(usage_report)
    return output_dir


def analyze_workspace_usage(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    source_dir = (workspace_root / target.workspace.source_dir).resolve()
    metadata_dir = (workspace_root / target.workspace.metadata_dir / target.name).resolve()
    repo_metadata_dir = source_dir / ".repo"
    repo_reference_dir = (cache_root / target.cache.repo_dir).resolve()
    bazel_cache_dir = (cache_root / target.cache.bazel_dir).resolve()
    ccache_dir = (cache_root / target.cache.ccache_dir).resolve()

    source_total = directory_size_bytes(source_dir)
    repo_metadata = directory_size_bytes(repo_metadata_dir)
    source_checkout = max(source_total - repo_metadata, 0)
    cache_total = directory_size_bytes(cache_root)

    sections = {
        "source": _usage_entry(source_dir, source_checkout),
        "repo_metadata": _usage_entry(repo_metadata_dir, repo_metadata),
        "cache": _usage_entry(cache_root, cache_total),
        "cache_repo_reference": _usage_entry(repo_reference_dir, directory_size_bytes(repo_reference_dir)),
        "cache_bazel": _usage_entry(bazel_cache_dir, directory_size_bytes(bazel_cache_dir)),
        "cache_ccache": _usage_entry(ccache_dir, directory_size_bytes(ccache_dir)),
        "output": _usage_entry(output_dir, directory_size_bytes(output_dir)),
        "workspace_metadata": _usage_entry(metadata_dir, directory_size_bytes(metadata_dir)),
    }
    return {
        "target": target.name,
        "sections": sections,
    }


def _usage_entry(path: Path, size_bytes: int) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": size_bytes,
        "human": format_bytes(size_bytes),
    }


def _print_usage_report(report: dict[str, object]) -> None:
    print("workspace disk usage:", flush=True)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


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


def _warmup_kleaf(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    env: dict[str, str],
) -> None:
    warmup_target = target.build.warmup_target
    if warmup_target is None:
        raise ValueError("Kleaf warmup requires build.warmup_target")

    bazel_cache = ensure_directory(cache_root / target.cache.bazel_dir)
    jobs = resolve_build_jobs(target)
    bazel_binary = source_dir / "tools/bazel"
    if not bazel_binary.exists():
        raise FileNotFoundError(
            f"Missing required bazel launcher: {bazel_binary}. This project expects Kleaf trees to provide tools/bazel."
        )

    command = [
        str(bazel_binary),
        "build",
        f"--disk_cache={bazel_cache}",
        f"--jobs={jobs}",
        "--config=fast",
        "--config=stamp",
        "--verbose_failures",
    ]
    if target.build.lto:
        command.append(f"--lto={target.build.lto}")

    command.append(warmup_target.format(arch=target.build.arch))
    run_command(command, cwd=source_dir, env=env)


def _export_warmup_kleaf_outputs(
    target: TargetConfig,
    source_dir: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]]:
    files = _query_warmup_kleaf_outputs(target, source_dir, env)
    exported_files: list[dict[str, str]] = []
    for relative_output in files:
        source_path = (source_dir / relative_output).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Warmup output not found: {source_path}")

        export_relative_path = _warmup_export_path(relative_output)
        destination_path = (output_dir / export_relative_path).resolve()
        ensure_directory(destination_path.parent)
        shutil.copy2(source_path, destination_path)
        exported_files.append(
            {
                "source": str(source_path),
                "path": str(destination_path),
            }
        )

    print(f"exported {len(exported_files)} warmup artifacts to {output_dir}", flush=True)
    return exported_files


def _query_warmup_kleaf_outputs(
    target: TargetConfig,
    source_dir: Path,
    env: dict[str, str],
) -> list[str]:
    warmup_target = target.build.warmup_target
    if warmup_target is None:
        raise ValueError("Kleaf warmup requires build.warmup_target")

    bazel_binary = source_dir / "tools/bazel"
    result = run_command(
        [
            str(bazel_binary),
            "cquery",
            "--output=files",
            "--config=fast",
            "--config=stamp",
            warmup_target.format(arch=target.build.arch),
        ],
        cwd=source_dir,
        env=env,
        capture_output=True,
    )
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


def _warmup_export_path(relative_output: str) -> Path:
    marker = "/bin/"
    if marker in relative_output:
        return Path(relative_output.split(marker, 1)[1])
    return Path(relative_output)
