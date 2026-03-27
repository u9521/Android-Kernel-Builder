# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .build import build_kernel, warmup_kernel
from .docker import build_base_image, build_snapshot_image, build_workspace_image, run_container
from .snapshot import parse_snapshot_git_projects
from .targets import load_target_config
from .utils import ensure_directory
from .workspace import prepare_workspace


DEFAULT_JOBS = os.cpu_count() or 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare reusable GKI workspaces and builds")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_target = subparsers.add_parser("show-target", help="Print a target config as JSON")
    show_target.add_argument("--target-config", required=True, help="Path to target config")
    show_target.set_defaults(handler=handle_show_target)

    bootstrap = subparsers.add_parser("bootstrap", help="Create local workspace, cache, and output directories")
    bootstrap.add_argument("--workspace", default=".workspace", help="Workspace root directory")
    bootstrap.add_argument("--cache-root", default=".cache", help="Cache root directory")
    bootstrap.add_argument("--output-root", default="out", help="Artifacts root directory")
    bootstrap.set_defaults(handler=handle_bootstrap)

    prepare = subparsers.add_parser("prepare-workspace", help="Initialize and sync kernel source")
    _add_shared_target_arguments(prepare)
    prepare.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"repo sync parallelism (default: max available threads, {DEFAULT_JOBS})",
    )
    prepare.set_defaults(handler=handle_prepare_workspace)

    build = subparsers.add_parser("build", help="Build the configured kernel target")
    _add_shared_target_arguments(build)
    build.add_argument("--output-root", default="out", help="Artifacts root directory")
    build.set_defaults(handler=handle_build)

    warmup = subparsers.add_parser("warmup-build", help="Warm build caches for the configured target")
    _add_shared_target_arguments(warmup)
    warmup.add_argument("--output-root", default="out", help="Artifacts root directory")
    warmup.set_defaults(handler=handle_warmup_build)

    docker_base = subparsers.add_parser("docker-build-base", help="Build the base image")
    docker_base.add_argument("--tag", required=True, help="Image tag")
    docker_base.add_argument("--dockerfile", default="docker/base.Dockerfile", help="Path to base Dockerfile")
    docker_base.set_defaults(handler=handle_docker_build_base)

    docker_workspace = subparsers.add_parser("docker-build-workspace", help="Build the workspace image")
    docker_workspace.add_argument("--tag", required=True, help="Image tag")
    docker_workspace.add_argument("--base-image", required=True, help="Parent image tag")
    docker_workspace.add_argument("--target-config", required=True, help="Path to target config")
    docker_workspace.add_argument(
        "--dockerfile",
        default="docker/workspace.Dockerfile",
        help="Path to workspace Dockerfile",
    )
    docker_workspace.set_defaults(handler=handle_docker_build_workspace)

    docker_snapshot = subparsers.add_parser("docker-build-snapshot", help="Build the snapshot image")
    docker_snapshot.add_argument("--tag", required=True, help="Image tag")
    docker_snapshot.add_argument("--base-image", required=True, help="Parent image tag")
    docker_snapshot.add_argument("--target-config", required=True, help="Path to target config")
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
    docker_run.add_argument("--workspace", default=".workspace", help="Workspace root directory")
    docker_run.add_argument("--cache-root", default=".cache", help="Cache root directory")
    docker_run.add_argument("--output-root", default="out", help="Artifacts root directory")
    docker_run.add_argument("container_command", nargs=argparse.REMAINDER, help="Command passed to container")
    docker_run.set_defaults(handler=handle_docker_run)

    return parser


def _add_shared_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target-config", required=True, help="Path to target config")
    parser.add_argument("--workspace", default=".workspace", help="Workspace root directory")
    parser.add_argument("--cache-root", default=".cache", help="Cache root directory")


def handle_show_target(args: argparse.Namespace) -> int:
    target = load_target_config(args.target_config)
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
        },
        "config_path": str(target.config_path),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def handle_bootstrap(args: argparse.Namespace) -> int:
    workspace_root = ensure_directory(Path(args.workspace))
    cache_root = ensure_directory(Path(args.cache_root))
    ensure_directory(cache_root / "repo")
    ensure_directory(cache_root / "bazel")
    ensure_directory(cache_root / "ccache")
    output_root = ensure_directory(Path(args.output_root))
    print(
        json.dumps(
            {
                "workspace": str(workspace_root.resolve()),
                "cache_root": str(cache_root.resolve()),
                "output_root": str(output_root.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def handle_prepare_workspace(args: argparse.Namespace) -> int:
    target = load_target_config(args.target_config)
    prepare_workspace(target, Path(args.workspace), Path(args.cache_root), args.jobs)
    return 0


def handle_build(args: argparse.Namespace) -> int:
    target = load_target_config(args.target_config)
    build_kernel(target, Path(args.workspace), Path(args.cache_root), Path(args.output_root))
    return 0


def handle_warmup_build(args: argparse.Namespace) -> int:
    target = load_target_config(args.target_config)
    warmup_kernel(target, Path(args.workspace), Path(args.cache_root), Path(args.output_root))
    return 0


def handle_docker_build_base(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    build_base_image(args.tag, repo_root, repo_root / args.dockerfile)
    return 0


def handle_docker_build_workspace(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    build_workspace_image(
        args.tag,
        args.base_image,
        Path(args.target_config),
        repo_root,
        repo_root / args.dockerfile,
    )
    return 0


def handle_docker_build_snapshot(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    build_snapshot_image(
        args.tag,
        args.base_image,
        Path(args.target_config),
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
        Path(args.cache_root),
        Path(args.output_root),
        command or ["bash"],
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
