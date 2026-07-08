# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from .. import layout
from ..build_docker import build_base_image, build_snapshot_image, build_workspace_image, run_container
from ..snapshot import parse_snapshot_git_projects
from ..targets import target_config_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or run AKB Docker images")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_base = subparsers.add_parser("build-base", help="Build the base image")
    build_base.add_argument("--tag", required=True, help="Image tag")
    build_base.add_argument("--push", action="store_true", help="Push directly with docker buildx instead of loading locally")
    build_base.set_defaults(handler=handle_build_base)

    build_workspace = subparsers.add_parser("build-workspace", help="Build the workspace image")
    build_workspace.add_argument("--tag", required=True, help="Image tag")
    build_workspace.add_argument("--base-image", required=True, help="Parent image tag")
    build_workspace.add_argument("--target", required=True, help="Target name")
    build_workspace.add_argument(
        "--push",
        action="store_true",
        help="Push directly with docker buildx instead of loading locally",
    )
    build_workspace.set_defaults(handler=handle_build_workspace)

    build_snapshot = subparsers.add_parser("build-snapshot", help="Build the snapshot image")
    build_snapshot.add_argument("--tag", required=True, help="Image tag")
    build_snapshot.add_argument("--base-image", required=True, help="Parent image tag")
    build_snapshot.add_argument("--target", required=True, help="Target name")
    build_snapshot.add_argument(
        "--snapshot-git-projects",
        default="common",
        help="Comma-separated repo projects to preserve as standalone Git repos in the snapshot image",
    )
    build_snapshot.add_argument(
        "--push",
        action="store_true",
        help="Push directly with docker buildx instead of loading locally",
    )
    build_snapshot.set_defaults(handler=handle_build_snapshot)

    run = subparsers.add_parser("run", help="Run an existing image with mounted workspace")
    run.add_argument("--image", required=True, help="Image tag")
    run.add_argument("container_command", nargs=argparse.REMAINDER, help="Command passed to container")
    run.set_defaults(handler=handle_run)

    return parser


def handle_build_base(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    build_base_image(args.tag, repo_root, layout.base_dockerfile(repo_root), push=args.push)
    return 0


def handle_build_workspace(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    build_workspace_image(
        args.tag,
        args.base_image,
        target_config_path(repo_root, args.target),
        repo_root,
        layout.workspace_dockerfile(repo_root),
        push=args.push,
    )
    return 0


def handle_build_snapshot(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    build_snapshot_image(
        args.tag,
        args.base_image,
        target_config_path(repo_root, args.target),
        repo_root,
        layout.snapshot_dockerfile(repo_root),
        parse_snapshot_git_projects(args.snapshot_git_projects),
        push=args.push,
    )
    return 0


def handle_run(args: argparse.Namespace) -> int:
    command = args.container_command or ["bash"]
    if command and command[0] == "--":
        command = command[1:]
    run_container(
        args.image,
        Path.cwd(),
        command or ["bash"],
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
