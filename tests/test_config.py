#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

config = importlib.import_module("gki_builder.config")
layout = importlib.import_module("gki_builder.layout")


class AkbConfigTests(unittest.TestCase):
    def test_load_akb_config_reads_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.akb_config_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.akb_config_file(work_root).write_text(
                """
version = 1
default_target = "android15-6.6"

[workspace]
source_dir = "android-kernel"
cache_dir = ".cache"
output_dir = "out"

[build]
jobs = 0
lto = "thin"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            loaded = config.load_akb_config(work_root)

        self.assertEqual(loaded.version, 1)
        self.assertEqual(loaded.default_target, "android15-6.6")
        self.assertEqual(loaded.workspace.source_dir, "android-kernel")
        self.assertEqual(loaded.workspace.cache_dir, ".cache")
        self.assertEqual(loaded.workspace.output_dir, "out")
        self.assertEqual(loaded.build.jobs, 0)
        self.assertEqual(loaded.build.lto, "thin")

    def test_load_akb_config_rejects_absolute_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                """
version = 1

[workspace]
cache_dir = "/var/cache"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "workspace.cache_dir"):
                config.load_akb_config(config_path)


if __name__ == "__main__":
    unittest.main()
