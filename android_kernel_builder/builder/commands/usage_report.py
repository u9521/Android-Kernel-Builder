# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from .. import layout
from ..targets import resolve_target
from ..usage_report import analyze_workspace_usage, print_usage_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print AKB workspace disk usage")
    parser.set_defaults(handler=handle_usage_report)
    return parser


def handle_usage_report(args: argparse.Namespace) -> int:
    del args
    work_root = Path.cwd()
    target = resolve_target(work_root)
    print_usage_report(
        analyze_workspace_usage(
            target,
            layout.target_source_root(work_root, target.name),
            layout.target_cache_root(work_root, target.name),
            layout.target_output_root(work_root, target.name),
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
