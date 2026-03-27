#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

active_target = importlib.import_module("gki_builder.active_target")
layout = importlib.import_module("gki_builder.layout")


class ActiveTargetTests(unittest.TestCase):
    def test_load_active_target_with_remote_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.active_target_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.active_target_file(work_root).write_text(
                """
version = 1
name = "android15-6.6"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
target = "//common:kernel_aarch64_dist"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            loaded = active_target.load_active_target(work_root)

        self.assertEqual(loaded.version, 1)
        self.assertEqual(loaded.name, "android15-6.6")
        self.assertEqual(loaded.manifest.source, "remote")
        self.assertEqual(loaded.build.system, "kleaf")

    def test_load_active_target_with_local_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "active-target.toml"
            config_path.write_text(
                """
version = 1
name = "avd-android15-6.6-x64"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "avd/default.xml"

[build]
system = "kleaf"
arch = "x86_64"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            loaded = active_target.load_active_target(config_path)

        self.assertEqual(loaded.manifest.path, "avd/default.xml")
        self.assertEqual(
            active_target.resolve_embedded_manifest_path(loaded, Path("/workspace")),
            Path("/workspace/.akb/manifests/avd/default.xml"),
        )

    def test_load_active_target_rejects_manifest_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "active-target.toml"
            config_path.write_text(
                """
version = 1
name = "sample"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "../default.xml"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "manifest.path"):
                active_target.load_active_target(config_path)

    def test_load_active_target_rejects_configurable_workspace_metadata_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "active-target.toml"
            config_path.write_text(
                """
version = 1
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"

[workspace]
source_dir = "android-kernel"
metadata_dir = "docker_metadata/targets"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "workspace.metadata_dir"):
                active_target.load_active_target(config_path)


if __name__ == "__main__":
    unittest.main()
