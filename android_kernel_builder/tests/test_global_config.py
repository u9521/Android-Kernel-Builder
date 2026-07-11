#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest

global_config = importlib.import_module("android_kernel_builder.builder.core.config.global_config")


class GlobalConfigTests(unittest.TestCase):
    def test_load_global_config_uses_checked_in_snapshot_defaults(self) -> None:
        config = global_config.load_global_config(Path(__file__).resolve().parents[1])

        self.assertEqual(config.snapshot_git_projects, ["common"])

    def test_load_global_config_supports_custom_snapshot_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (temp_root / "android_kernel_builder" / "configs").mkdir(parents=True, exist_ok=True)
            (temp_root / "android_kernel_builder" / "configs" / "global.toml").write_text(
                """
[snapshot]
git_projects = ["common", "build/kernel"]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            config = global_config.load_global_config(temp_root)

            self.assertEqual(config.snapshot_git_projects, ["common", "build/kernel"])


if __name__ == "__main__":
    unittest.main()
