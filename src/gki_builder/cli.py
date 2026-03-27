# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .build import build_kernel, warmup_kernel
from .docker import build_base_image, build_snapshot_image, build_workspace_image, run_container
from . import layout
from .config import load_akb_config
from .environment import discover_current_environment
from .snapshot import parse_snapshot_git_projects
from .target_store import host_target_config_path, resolve_target
from .workspace import sync_source


DEFAULT_JOBS = os.cpu_count() or 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare reusable GKI workspaces and builds")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_target = subparsers.add_parser("show-target", help="Print the selected target config as JSON")
    show_target.add_argument("--target", help="Target name; defaults to .akb/config.toml on host")
    show_target.set_defaults(handler=handle_show_target)

    sync = subparsers.add_parser("sync-source", help="Initialize and sync kernel source")
    _add_shared_target_arguments(sync)
    sync.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"repo sync parallelism (default: max available threads, {DEFAULT_JOBS})",
    )
    sync.set_defaults(handler=handle_sync_source)

    build = subparsers.add_parser("build", help="Build the configured kernel target")
    _add_shared_target_arguments(build)
    build.add_argument("--output-root", help="Artifacts root directory; defaults to .akb/config.toml on host")
    build.set_defaults(handler=handle_build)

    warmup = subparsers.add_parser("warmup-build", help="Warm build caches for the configured target")
    _add_shared_target_arguments(warmup)
    warmup.add_argument("--output-root", help="Artifacts root directory; defaults to .akb/config.toml on host")
    warmup.set_defaults(handler=handle_warmup_build)

    docker_base = subparsers.add_parser("docker-build-base", help="Build the base image")
    docker_base.add_argument("--tag", required=True, help="Image tag")
    docker_base.add_argument("--dockerfile", default="docker/base.Dockerfile", help="Path to base Dockerfile")
    docker_base.set_defaults(handler=handle_docker_build_base)

    docker_workspace = subparsers.add_parser("docker-build-workspace", help="Build the workspace image")
    docker_workspace.add_argument("--tag", required=True, help="Image tag")
    docker_workspace.add_argument("--base-image", required=True, help="Parent image tag")
    docker_workspace.add_argument("--target", required=True, help="Target name")
    docker_workspace.add_argument(
        "--dockerfile",
        default="docker/workspace.Dockerfile",
        help="Path to workspace Dockerfile",
    )
    docker_workspace.set_defaults(handler=handle_docker_build_workspace)

    docker_snapshot = subparsers.add_parser("docker-build-snapshot", help="Build the snapshot image")
    docker_snapshot.add_argument("--tag", required=True, help="Image tag")
    docker_snapshot.add_argument("--base-image", required=True, help="Parent image tag")
    docker_snapshot.add_argument("--target", required=True, help="Target name")
    docker_snapshot.add_argument(
        "--dockerfile",
        default="docker/snapshot.Dockerfile",
        help="Path to snapshot Dockerfile",
    )
    docker_snapshot.add_argument(
        "--snapshot-git-projects",
        default="common",
        help="Comma-separated repo projects to preserve as standalone Git repos in the snapshot image",
    )
    docker_snapshot.set_defaults(handler=handle_docker_build_snapshot)

    docker_run = subparsers.add_parser("docker-run", help="Run an existing image with mounted workspace")
    docker_run.add_argument("--image", required=True, help="Image tag")
    docker_run.add_argument("--workspace", default="work", help="Workspace root directory")
    docker_run.add_argument("--cache-root", help="Cache root directory; defaults to <workspace>/.cache")
    docker_run.add_argument("--output-root", default="out", help="Artifacts root directory")
    docker_run.add_argument("container_command", nargs=argparse.REMAINDER, help="Command passed to container")
    docker_run.set_defaults(handler=handle_docker_run)

    return parser


def _add_shared_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target name; defaults to .akb/config.toml on host")
    parser.add_argument("--cache-root", help="Cache root directory; defaults to .akb/config.toml on host")


def handle_show_target(args: argparse.Namespace) -> int:
    target = resolve_target(discover_current_environment(), args.target)
    metadata_root = _target_metadata_root_preview(target)
    payload = {
        "name": target.name,
        "manifest": {
            "source": target.manifest.source,
            "url": target.manifest.url,
            "branch": target.manifest.branch,
            "file": target.manifest.file,
            "path": str(target.manifest.path) if target.manifest.path else None,
            "minimal": target.manifest.minimal,
            "autodetect_deprecated": target.manifest.autodetect_deprecated,
        },
        "build": {
            "system": target.build.system,
            "target": target.build.target,
            "warmup_target": target.build.warmup_target,
            "dist_dir": target.build.dist_dir,
            "dist_flag": target.build.dist_flag,
            "arch": target.build.arch,
            "jobs": target.build.jobs,
            "legacy_config": target.build.legacy_config,
            "lto": target.build.lto,
        },
        "cache": {
            "repo_dir": target.cache.repo_dir,
            "bazel_dir": target.cache.bazel_dir,
            "ccache_dir": target.cache.ccache_dir,
        },
        "workspace": {
            "source_dir": target.workspace.source_dir,
            "metadata_dir": target.workspace.metadata_dir,
            "metadata_root": str(metadata_root),
        },
        "config_path": str(target.config_path),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def handle_sync_source(args: argparse.Namespace) -> int:
    environment = discover_current_environment()
    akb_config = load_akb_config(environment.work_root) if environment.mode == "host" else None
    target = resolve_target(environment, args.target)
    sync_source(
        target,
        environment.work_root,
        _resolve_cache_root(args.cache_root, environment.work_root, akb_config),
        args.jobs,
    )
    return 0


def handle_build(args: argparse.Namespace) -> int:
    environment = discover_current_environment()
    akb_config = load_akb_config(environment.work_root) if environment.mode == "host" else None
    target = resolve_target(environment, args.target)
    build_kernel(
        target,
        environment.work_root,
        _resolve_cache_root(args.cache_root, environment.work_root, akb_config),
        _resolve_output_root(args.output_root, environment.work_root, akb_config),
    )
    return 0


def handle_warmup_build(args: argparse.Namespace) -> int:
    environment = discover_current_environment()
    akb_config = load_akb_config(environment.work_root) if environment.mode == "host" else None
    target = resolve_target(environment, args.target)
    warmup_kernel(
        target,
        environment.work_root,
        _resolve_cache_root(args.cache_root, environment.work_root, akb_config),
        _resolve_output_root(args.output_root, environment.work_root, akb_config),
    )
    return 0


def handle_docker_build_base(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    build_base_image(args.tag, repo_root, repo_root / args.dockerfile)
    return 0


def handle_docker_build_workspace(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    environment = discover_current_environment()
    if environment.mode != "host":
        raise ValueError("docker-build-workspace must be run from a host AKB environment")
    build_workspace_image(
        args.tag,
        args.base_image,
        host_target_config_path(environment.work_root, args.target),
        repo_root,
        repo_root / args.dockerfile,
    )
    return 0


def handle_docker_build_snapshot(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    environment = discover_current_environment()
    if environment.mode != "host":
        raise ValueError("docker-build-snapshot must be run from a host AKB environment")
    build_snapshot_image(
        args.tag,
        args.base_image,
        host_target_config_path(environment.work_root, args.target),
        repo_root,
        repo_root / args.dockerfile,
        parse_snapshot_git_projects(args.snapshot_git_projects),
    )
    return 0


def handle_docker_run(args: argparse.Namespace) -> int:
    command = args.container_command or ["bash"]
    if command and command[0] == "--":
        command = command[1:]
    run_container(
        args.image,
        Path(args.workspace),
        _resolve_cache_root(args.cache_root, args.workspace),
        Path(args.output_root),
        command or ["bash"],
    )
    return 0


def _resolve_cache_root(cache_root: str | None, work_root: str | Path, akb_config: object | None = None) -> Path:
    if cache_root:
        return Path(cache_root)
    if akb_config is not None:
        from .config import AkbConfig

        assert isinstance(akb_config, AkbConfig)
        return _resolve_under_work_root(work_root, akb_config.workspace.cache_dir)
    return layout.cache_root(Path(work_root))


def _resolve_output_root(output_root: str | None, work_root: str | Path, akb_config: object | None = None) -> Path:
    if output_root:
        return Path(output_root)
    if akb_config is not None:
        from .config import AkbConfig

        assert isinstance(akb_config, AkbConfig)
        return _resolve_under_work_root(work_root, akb_config.workspace.output_dir)
    return layout.output_root(Path(work_root))


def _resolve_under_work_root(work_root: str | Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(work_root) / path


def _target_metadata_root_preview(target: object) -> Path:
    from .targets import TargetConfig

    assert isinstance(target, TargetConfig)
    metadata_dir = target.workspace.metadata_dir
    if metadata_dir == layout.docker_target_metadata_relative_dir():
        return layout.docker_target_metadata_root(layout.DOCKER_WORK_ROOT, target.name)
    return layout.host_target_metadata_root(Path("<work>"), target.name)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
