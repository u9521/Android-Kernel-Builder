# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
import shutil
import tempfile
from pathlib import Path

from . import layout
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
    workspace_root = workspace_root.resolve()
    context = _create_build_context(target, workspace_root, cache_root, output_root)
    executor = _resolve_build_system_executor(target)
    executor.build(target, context.source_dir, context.cache_root, context.output_dir, context.env)
    _write_usage_report(target, workspace_root, context.cache_root, context.output_dir)
    return context.output_dir


def warmup_kernel(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_root: Path,
) -> Path:
    workspace_root = workspace_root.resolve()
    context = _create_build_context(target, workspace_root, cache_root, output_root)
    executor = _resolve_build_system_executor(target)
    exported_files = executor.warmup(target, context.source_dir, context.cache_root, context.output_dir, context.env)

    if exported_files is not None:
        _write_warmup_outputs(target, workspace_root, context.output_dir, exported_files)

    _write_usage_report(target, workspace_root, context.cache_root, context.output_dir)
    return context.output_dir


BuildAction = Callable[[TargetConfig, Path, Path, Path, dict[str, str]], None]
WarmupAction = Callable[[TargetConfig, Path, Path, Path, dict[str, str]], list[dict[str, str]] | None]


@dataclass(slots=True)
class _BuildContext:
    source_dir: Path
    cache_root: Path
    output_dir: Path
    env: dict[str, str]


@dataclass(frozen=True, slots=True)
class _BuildSystemExecutor:
    build: BuildAction
    warmup: WarmupAction

def _create_build_context(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_root: Path,
) -> _BuildContext:
    return _BuildContext(
        source_dir=(workspace_root / target.workspace.source_dir).resolve(),
        cache_root=cache_root.resolve(),
        output_dir=ensure_directory((output_root / target.build.dist_dir).resolve()),
        env=build_environment(),
    )


def _write_usage_report(target: TargetConfig, workspace_root: Path, cache_root: Path, output_dir: Path) -> None:
    usage_report = analyze_workspace_usage(target, workspace_root, cache_root, output_dir)
    metadata_dir = ensure_directory(_target_metadata_root(workspace_root, target))
    write_json(metadata_dir / "disk-usage.json", usage_report)
    _print_usage_report(usage_report)


def _write_warmup_outputs(
    target: TargetConfig,
    workspace_root: Path,
    output_dir: Path,
    exported_files: list[dict[str, str]],
) -> None:
    metadata_dir = ensure_directory(_target_metadata_root(workspace_root, target))
    write_json(
        metadata_dir / "warmup-outputs.json",
        {
            "target": target.name,
            "warmup_target": target.build.warmup_target,
            "output_dir": str(output_dir),
            "files": exported_files,
        },
    )


def analyze_workspace_usage(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    source_dir = (workspace_root / target.workspace.source_dir).resolve()
    metadata_dir = _target_metadata_root(workspace_root.resolve(), target)
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


def _target_metadata_root(workspace_root: Path, target: TargetConfig) -> Path:
    metadata_dir = target.workspace.metadata_dir
    if metadata_dir == layout.docker_target_metadata_relative_dir():
        return layout.docker_target_metadata_root(workspace_root, target.name)
    return layout.host_target_metadata_root(workspace_root, target.name)


def _print_usage_report(report: dict[str, object]) -> None:
    print("workspace disk usage:", flush=True)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


def _print_ccache_stats(env: dict[str, str]) -> None:
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


def _build_legacy(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> None:
    legacy_config = target.build.legacy_config
    if not legacy_config:
        raise ValueError("Legacy build requires build.legacy_config")

    jobs = resolve_build_jobs(target)
    env = env.copy()
    env.update({
        "BUILD_CONFIG": legacy_config.format(arch=target.build.arch),
        "DIST_DIR": str(output_dir),
        "MAKEFLAGS": f"-j{jobs}",
    })
    if target.build.lto:
        env["LTO"] = target.build.lto

    if not target.build.use_ccache:
        run_command(["bash", "build/build.sh"], cwd=source_dir, env=env)
        return

    env["CCACHE_DIR"] = str((cache_root / target.cache.ccache_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="akb-ccache-link-") as temp_dir:
        ccache_clang = _create_ccache_clang_symlink(Path(temp_dir), env)
        run_command(["bash", "build/build.sh", f"CC={ccache_clang}"], cwd=source_dir, env=env)
    _print_ccache_stats(env)


def _create_ccache_clang_symlink(directory: Path, env: dict[str, str]) -> Path:
    ccache_binary = shutil.which("ccache", path=env.get("PATH"))
    if ccache_binary is None:
        raise FileNotFoundError("Legacy build requires ccache, but no ccache executable was found in PATH")

    link_path = directory / "clang"
    os.symlink(Path(ccache_binary).resolve(), link_path)
    return link_path.absolute()


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


def _warmup_legacy(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]] | None:
    _build_legacy(target, source_dir, cache_root, output_dir, env)
    return None


def _warmup_kleaf_mode(
    target: TargetConfig,
    source_dir: Path,
    cache_root: Path,
    output_dir: Path,
    env: dict[str, str],
) -> list[dict[str, str]] | None:
    if target.build.warmup_target is None:
        _build_kleaf(target, source_dir, cache_root, output_dir, env)
        return None
    _warmup_kleaf(target, source_dir, cache_root, env)
    return _export_warmup_kleaf_outputs(target, source_dir, output_dir, env)


_BUILD_SYSTEM_EXECUTORS = {
    "kleaf": _BuildSystemExecutor(build=_build_kleaf, warmup=_warmup_kleaf_mode),
    "legacy": _BuildSystemExecutor(build=_build_legacy, warmup=_warmup_legacy),
}


def _resolve_build_system_executor(target: TargetConfig) -> _BuildSystemExecutor:
    executor = _BUILD_SYSTEM_EXECUTORS.get(target.build.system)
    if executor is None:
        raise ValueError(f"Unsupported build system in {target.config_path}: {target.build.system}")
    return executor


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
        exported_files.append({
            "source": str(source_path),
            "path": str(destination_path),
        })

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
