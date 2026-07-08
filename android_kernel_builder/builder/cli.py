# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse


_COMMAND_HELP = """available commands:
  show-target       print the selected target config as JSON
  sync-source       initialize and sync kernel source
  build             build the configured kernel target
  warmup-build      warm build caches for the configured target
  build-docker            build or run Docker images
  cache             manage Docker build cache mounts
  tools             run tools

examples:
  uv run show-target --target android15-6.6
  uv run sync-source --target android15-6.6
  uv run build --target android15-6.6
  uv run build-docker build-workspace --tag <tag> --base-image <base> --target android15-6.6
  uv run cache init --target android15-6.6
  uv run tools add-git-safe /path/to/workspace -r
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Android Kernel Builder command index",
        epilog=_COMMAND_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
