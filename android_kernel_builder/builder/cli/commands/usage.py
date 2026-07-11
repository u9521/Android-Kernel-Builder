# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from ... import layout
from ...core.config import TargetConfigProvider
from ...usage_report import analyze_workspace_usage, print_usage_report
from ..registry import register_command


@register_command("usage", "Print AKB workspace disk usage")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("usage", help="Print AKB workspace disk usage")
    parser.set_defaults(handler=handle_usage_report)


def handle_usage_report(args: argparse.Namespace) -> int:
    del args
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load()
    print_usage_report(
        analyze_workspace_usage(
            target,
            layout.target_source_root(work_root, target.name),
            layout.target_cache_root(work_root, target.name),
            layout.target_output_root(work_root, target.name),
        )
    )
    return 0
