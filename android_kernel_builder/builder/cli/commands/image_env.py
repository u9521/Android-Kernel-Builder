# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse

from ...extensions.image_env import prepare_runtime_image_layout
from ..common import add_target_argument
from ..registry import register_command


@register_command("image-env", "Prepare Docker image target env files")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("image-env", help="Prepare Docker image target env files")
    add_target_argument(parser)
    parser.set_defaults(handler=handle_image_env)


def handle_image_env(args: argparse.Namespace) -> int:
    prepare_runtime_image_layout(args.target)
    return 0
