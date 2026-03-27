#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

config = importlib.import_module("gki_builder.config")
layout = importlib.import_module("gki_builder.layout")
target_store = importlib.import_module("gki_builder.target_store")


class InstallScriptTests(unittest.TestCase):
    def test_install_script_initializes_host_layout_and_seeds_repo_targets(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script_path = repo_root / "install.sh"

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=work_root,
                env={**os.environ, "AKB_INSTALLER_REPO_ROOT": str(repo_root)},
                capture_output=True,
                text=True,
                check=True,
            )

            loaded = config.load_akb_config(work_root)
            local_target = target_store.load_host_target(work_root, "avd-android15-6.6-x64")

            self.assertIn("Initialized AKB host environment", result.stdout)
            self.assertEqual(loaded.default_target, "android15-6.6")
            self.assertEqual(loaded.workspace.source_dir, "android-kernel")
            self.assertTrue(layout.targets_link(work_root).is_symlink())
            self.assertEqual(layout.targets_link(work_root).resolve(), layout.targets_root(work_root).resolve())
            self.assertTrue((layout.akb_bin_root(work_root)).is_dir())
            self.assertTrue((work_root / ".cache").is_dir())
            self.assertTrue((work_root / "out").is_dir())
            self.assertEqual(
                local_target.manifest.path,
                layout.target_manifests_root(work_root) / "avd" / "avd-android-15-6.6_x64.xml",
            )
            self.assertTrue(local_target.manifest.path.exists())
            self.assertIn('.akb/bin/', (work_root / '.gitignore').read_text(encoding='utf-8'))
            self.assertIn('.akb/venv/', (work_root / '.gitignore').read_text(encoding='utf-8'))

    def test_install_script_preserves_existing_config_and_target_files(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script_path = repo_root / "install.sh"

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.target_configs_root(work_root).mkdir(parents=True, exist_ok=True)
            layout.akb_config_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.akb_config_file(work_root).write_text(
                """
version = 1
default_target = "custom"

[workspace]
source_dir = "kernel-src"
cache_dir = ".cache"
output_dir = "out"

[build]
jobs = 0
lto = "thin"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            custom_target_path = layout.target_configs_root(work_root) / "android15-6.6.toml"
            custom_target_path.write_text("name = \"custom\"\n\n[manifest]\nsource = \"remote\"\nurl = \"https://example.com\"\nbranch = \"main\"\n\n[build]\nsystem = \"kleaf\"\narch = \"aarch64\"\n", encoding="utf-8")

            subprocess.run(
                ["bash", str(script_path)],
                cwd=work_root,
                env={**os.environ, "AKB_INSTALLER_REPO_ROOT": str(repo_root)},
                capture_output=True,
                text=True,
                check=True,
            )

            loaded = config.load_akb_config(work_root)

            self.assertEqual(loaded.default_target, "custom")
            self.assertEqual(loaded.workspace.source_dir, "kernel-src")
            self.assertIn('name = "custom"', custom_target_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
