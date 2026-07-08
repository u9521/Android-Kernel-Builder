# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse

from ..docker_image.runtime_layout import prepare_runtime_image_layout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Docker image target config and env files")
    parser.add_argument(
        "--source-target-file",
        required=True,
        help="Path to the source target definition, relative to the project root or absolute",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    prepare_runtime_image_layout(args.source_target_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
