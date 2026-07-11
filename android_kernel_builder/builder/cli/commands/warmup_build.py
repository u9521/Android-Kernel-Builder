# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from ... import layout
from ...core.build import warmup_kernel
from ...core.config import TargetConfigProvider
from ..common import add_target_argument
from ..registry import register_command


@register_command("warmup-build", "Warm build caches for the configured target")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("warmup-build", help="Warm build caches for the configured target")
    add_target_argument(parser)
    parser.set_defaults(handler=handle_warmup_build)


def handle_warmup_build(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    warmup_kernel(
        target,
        layout.target_source_root(work_root, target.name),
        layout.target_cache_root(work_root, target.name),
        layout.target_output_root(work_root, target.name),
    )
    return 0
