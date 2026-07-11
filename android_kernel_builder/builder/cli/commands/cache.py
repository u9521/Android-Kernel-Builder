# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
from pathlib import Path

from ... import layout
from ...core.config import TargetConfigProvider
from ...extensions.cache import cleanup_build_cache
from ...extensions.cache import finalize_build_cache
from ...extensions.cache import init_build_cache
from ...extensions.cache import pack_base_build_cache
from ...extensions.cache import prepare_base_build_cache
from ..common import add_target_argument
from ..registry import register_command


@register_command("cache", "Manage Docker build cache mounts")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("cache", help="Manage Docker build cache mounts")
    cache_subparsers = parser.add_subparsers(dest="cache_command", required=True)

    init = cache_subparsers.add_parser("init", help="Initialize Docker build cache mounts")
    add_target_argument(init)
    init.set_defaults(handler=handle_init)

    cleanup = cache_subparsers.add_parser("cleanup", help="Cleanup Docker build cache mounts")
    add_target_argument(cleanup)
    cleanup.set_defaults(handler=handle_cleanup)

    finalize = cache_subparsers.add_parser("finalize", help="Cleanup and export Docker build cache")
    add_target_argument(finalize)
    finalize.set_defaults(handler=handle_finalize)

    prepare_base = cache_subparsers.add_parser("prepare-base", help="Prepare base Docker build cache image")
    add_target_argument(prepare_base)
    prepare_base.add_argument("--work-root", default=str(layout.DOCKER_WORK_ROOT))
    prepare_base.set_defaults(handler=handle_prepare_base)

    pack_base = cache_subparsers.add_parser("pack-base", help="Pack base Docker build cache image")
    add_target_argument(pack_base)
    pack_base.add_argument("--work-root", default=str(layout.DOCKER_WORK_ROOT))
    pack_base.set_defaults(handler=handle_pack_base)

    export = cache_subparsers.add_parser("export", help="Cleanup and export Docker build cache")
    add_target_argument(export)
    export.set_defaults(handler=handle_export)


def handle_init(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    init_build_cache(work_root, target.name)
    return 0


def handle_cleanup(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    cleanup_build_cache(work_root, target.name)
    return 0


def handle_finalize(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    finalize_build_cache(work_root, target.name)
    return 0


def handle_prepare_base(args: argparse.Namespace) -> int:
    prepare_base_build_cache(Path(args.work_root).resolve(), args.target)
    return 0


def handle_pack_base(args: argparse.Namespace) -> int:
    pack_base_build_cache(Path(args.work_root).resolve(), args.target)
    return 0


def handle_export(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    finalize_build_cache(work_root, target.name)
    return 0
