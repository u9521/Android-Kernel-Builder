# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse

from ...extensions.snapshot import create_workspace_snapshot_for_current_environment, parse_snapshot_git_projects
from ..registry import register_command


@register_command("snapshot", "Create a Docker snapshot from a prepared workspace")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("snapshot", help="Create a Docker snapshot from a prepared workspace")
    parser.add_argument(
        "--snapshot-git-projects",
        default=None,
        help="Comma-separated repo projects to preserve; defaults to configs/global.toml [snapshot].git_projects",
    )
    parser.set_defaults(handler=handle_snapshot)


def handle_snapshot(args: argparse.Namespace) -> int:
    create_workspace_snapshot_for_current_environment(
        preserve_git_projects=(
            parse_snapshot_git_projects(args.snapshot_git_projects)
            if args.snapshot_git_projects is not None
            else None
        ),
    )
    return 0
