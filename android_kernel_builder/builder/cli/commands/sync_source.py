# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from ... import layout
from ...core.config import TargetConfigProvider
from ...core.sync import sync_source
from ..common import DEFAULT_JOBS, add_target_argument
from ..registry import register_command


@register_command("sync-source", "Initialize and sync kernel source")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("sync-source", help="Initialize and sync kernel source")
    add_target_argument(parser)
    parser.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"repo sync parallelism (default: max available threads, {DEFAULT_JOBS})",
    )
    parser.set_defaults(handler=handle_sync_source)


def handle_sync_source(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    sync_source(
        target,
        layout.target_source_root(work_root, target.name),
        layout.target_cache_root(work_root, target.name),
        args.jobs,
    )
    return 0
