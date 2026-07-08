# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from .. import layout
from ..build import build_kernel
from ..targets import resolve_target
from .common import add_target_argument


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the configured kernel target")
    add_target_argument(parser)
    parser.set_defaults(handler=handle_build)
    return parser


def handle_build(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = resolve_target(work_root, args.target)
    build_kernel(
        target,
        layout.target_source_root(work_root, target.name),
        layout.target_cache_root(work_root, target.name),
        layout.target_output_root(work_root, target.name),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
