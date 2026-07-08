# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from ..commands.snapshot import build_parser


def main(argv: list[str] | None = None) -> int:
    from ..commands.snapshot import main as snapshot_main

    return snapshot_main(argv)


def parse_args(argv: list[str] | None = None):
    return build_parser().parse_args(argv)
