# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ... import layout
from ...core.config import KleafBuildConfig, LegacyBuildConfig, TargetConfigProvider
from ..common import add_target_argument
from ..registry import register_command


@register_command("show-target", "Print the selected target config as JSON")
def build_parser(subparsers: object) -> None:
    parser = subparsers.add_parser("show-target", help="Print the selected target config as JSON")
    add_target_argument(parser)
    parser.set_defaults(handler=handle_show_target)


def handle_show_target(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = TargetConfigProvider(work_root).load(args.target)
    payload = {
        "name": target.name,
        "repo": {
            "url": target.sync.url,
            "branch": target.sync.branch,
            "file": target.sync.file,
            "path": str(target.sync.path) if target.sync.path else None,
            "minimal": target.sync.minimal,
            "autodetect_deprecated": target.sync.autodetect_deprecated,
        },
        "build": _build_payload(target.build),
        "paths": _target_paths(work_root, target.name),
        "config_path": str(target.config_path),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _target_paths(work_root: Path, target_name: str) -> dict[str, str]:
    return {
        "source_root": str(layout.target_source_root(work_root, target_name)),
        "cache_root": str(layout.target_cache_root(work_root, target_name)),
        "output_root": str(layout.target_output_root(work_root, target_name)),
        "metadata_root": str(layout.docker_target_metadata_root(work_root, target_name)),
    }


def _build_payload(build_config: KleafBuildConfig | LegacyBuildConfig) -> dict[str, object]:
    if isinstance(build_config, KleafBuildConfig):
        return {
            "kleaf": {
                "target": build_config.target,
                "warmup_target": build_config.warmup_target,
                "dist_dir": build_config.dist_dir,
                "dist_flag": build_config.dist_flag,
                "arch": build_config.arch,
                "jobs": build_config.jobs,
                "lto": build_config.lto,
            }
        }
    return {
        "legacy": {
            "legacy_config": build_config.legacy_config,
            "dist_dir": build_config.dist_dir,
            "arch": build_config.arch,
            "jobs": build_config.jobs,
            "lto": build_config.lto,
            "use_ccache": build_config.use_ccache,
        }
    }
