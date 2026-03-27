#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import os
import shutil
import tomllib
from pathlib import Path


def prepare_workspace_image_env() -> None:
    repo_root = Path(os.environ["GKI_BUILDER_ROOT"])
    config_path = repo_root / os.environ["TARGET_CONFIG_PATH"]
    workspace_root = Path(os.environ["GKI_WORKSPACE_ROOT"])
    image_metadata_dir = workspace_root / ".gki-builder" / "image"

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    workspace = payload.get("workspace") or {}
    target_name = payload.get("name", "")
    source_dir = workspace.get("source_dir", "android-kernel")

    image_metadata_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, image_metadata_dir / "target-config.toml")
    (image_metadata_dir / "gki-builder.env").write_text(
        f"export GKI_TARGET_NAME={target_name}\n"
        f"export GKI_SOURCE_ROOT={workspace_root / source_dir}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    prepare_workspace_image_env()
