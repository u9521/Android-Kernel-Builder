#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

image_env = importlib.import_module("gki_builder.image_env")


class ImageEnvTests(unittest.TestCase):
    def test_prepare_workspace_image_env_writes_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            builder_root = temp_root / "tooling"
            workspace_root = temp_root / "workspace"
            config_path = builder_root / "configs" / "targets" / "sample.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                """
name = "sample"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "GKI_BUILDER_ROOT": str(builder_root),
                    "GKI_WORKSPACE_ROOT": str(workspace_root),
                    "TARGET_CONFIG_PATH": "configs/targets/sample.toml",
                },
                clear=False,
            ):
                image_env.prepare_workspace_image_env()

            image_dir = workspace_root / ".gki-builder" / "image"
            self.assertEqual(
                (image_dir / "target-config.toml").read_text(encoding="utf-8"),
                config_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (image_dir / "gki-builder.env").read_text(encoding="utf-8"),
                f"export GKI_TARGET_NAME=sample\n"
                f"export GKI_SOURCE_ROOT={workspace_root / 'android-kernel'}\n",
            )


if __name__ == "__main__":
    unittest.main()
