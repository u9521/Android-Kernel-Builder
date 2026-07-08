# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from .. import layout
from ..targets import resolve_target
from ..code_sync import sync_source
from .common import DEFAULT_JOBS, add_target_argument


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize and sync kernel source")
    add_target_argument(parser)
    parser.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"repo sync parallelism (default: max available threads, {DEFAULT_JOBS})",
    )
    parser.set_defaults(handler=handle_sync_source)
    return parser


def handle_sync_source(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = resolve_target(work_root, args.target)
    sync_source(
        target,
        layout.target_source_root(work_root, target.name),
        layout.target_cache_root(work_root, target.name),
        args.jobs,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
