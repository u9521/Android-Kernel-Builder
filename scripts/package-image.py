#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

from gki_builder.image_package import package_image_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the minimal Docker image build context")
    parser.add_argument("--output-dir", required=True, help="Directory to write the packaged image context")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    payload = package_image_context(repo_root, Path(args.output_dir))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
