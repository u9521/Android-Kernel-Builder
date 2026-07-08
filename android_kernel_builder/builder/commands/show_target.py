# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .. import layout
from ..targets import resolve_target
from .common import add_target_argument


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print the selected target config as JSON")
    add_target_argument(parser)
    parser.set_defaults(handler=handle_show_target)
    return parser


def handle_show_target(args: argparse.Namespace) -> int:
    work_root = Path.cwd()
    target = resolve_target(work_root, args.target)
    payload = {
        "name": target.name,
        "manifest": {
            "source": target.manifest.source,
            "url": target.manifest.url,
            "branch": target.manifest.branch,
            "file": target.manifest.file,
            "path": str(target.manifest.path) if target.manifest.path else None,
            "minimal": target.manifest.minimal,
            "autodetect_deprecated": target.manifest.autodetect_deprecated,
        },
        "build": {
            "system": target.build.system,
            "target": target.build.target,
            "warmup_target": target.build.warmup_target,
            "dist_dir": target.build.dist_dir,
            "dist_flag": target.build.dist_flag,
            "arch": target.build.arch,
            "jobs": target.build.jobs,
            "legacy_config": target.build.legacy_config,
            "lto": target.build.lto,
            "use_ccache": target.build.use_ccache,
        },
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
