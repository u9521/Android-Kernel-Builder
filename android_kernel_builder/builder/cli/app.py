# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse

from .registry import get_commands

# Import command modules for registration side effects.
from .commands import build  # noqa: F401
from .commands import cache  # noqa: F401
from .commands import image_env  # noqa: F401
from .commands import show_target  # noqa: F401
from .commands import snapshot  # noqa: F401
from .commands import sync_source  # noqa: F401
from .commands import tools  # noqa: F401
from .commands import usage  # noqa: F401
from .commands import warmup_build  # noqa: F401


def build_app() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Android Kernel Builder")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for _, _, build_command in get_commands():
        build_command(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_app()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
