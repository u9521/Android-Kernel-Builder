#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

from gki_builder.snapshot import create_workspace_snapshot_from_workspace_root, parse_snapshot_git_projects


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip repo metadata from a prepared workspace tree")
    parser.add_argument("--workspace-root", required=True, help="Prepared workspace root directory")
    parser.add_argument(
        "--snapshot-git-projects",
        default=None,
        help="Comma-separated repo projects to preserve as standalone Git repositories",
    )
    args = parser.parse_args()

    payload = create_workspace_snapshot_from_workspace_root(
        Path(args.workspace_root),
        preserve_git_projects=(
            parse_snapshot_git_projects(args.snapshot_git_projects)
            if args.snapshot_git_projects is not None
            else None
        ),
        project_root=Path(__file__).resolve().parents[1],
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
