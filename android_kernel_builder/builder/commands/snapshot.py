# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse

from ..snapshot import create_workspace_snapshot_for_current_environment, parse_snapshot_git_projects


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a Docker snapshot from a prepared workspace")
    parser.add_argument(
        "--snapshot-git-projects",
        default=None,
        help="Comma-separated repo projects to preserve; defaults to configs/global.toml [snapshot].git_projects",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    create_workspace_snapshot_for_current_environment(
        preserve_git_projects=(
            parse_snapshot_git_projects(args.snapshot_git_projects)
            if args.snapshot_git_projects is not None
            else None
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
