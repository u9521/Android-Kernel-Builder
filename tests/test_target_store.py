#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

environment_module = importlib.import_module("gki_builder.environment")
layout = importlib.import_module("gki_builder.layout")
target_store = importlib.import_module("gki_builder.target_store")


class TargetStoreTests(unittest.TestCase):
    def test_load_host_target_uses_default_target_and_manifest_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.akb_config_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.target_configs_root(work_root).mkdir(parents=True, exist_ok=True)
            layout.target_manifests_root(work_root).mkdir(parents=True, exist_ok=True)
            layout.akb_config_file(work_root).write_text(
                """
version = 1
default_target = "sample"

[workspace]
source_dir = "src-tree"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (layout.target_manifests_root(work_root) / "default.xml").write_text("<manifest />\n", encoding="utf-8")
            (layout.target_configs_root(work_root) / "sample.toml").write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "default.xml"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            target = target_store.load_host_target(work_root)

        self.assertEqual(target.name, "sample")
        self.assertEqual(target.workspace.source_dir, "src-tree")
        self.assertEqual(target.workspace.metadata_dir, ".akb/state/targets")
        self.assertEqual(target.manifest.path, layout.target_manifests_root(work_root) / "default.xml")

    def test_resolve_target_uses_embedded_docker_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.active_target_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.active_target_file(work_root).write_text(
                """
version = 1
name = "sample"

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
            environment = environment_module.AkbEnvironment(mode="docker", work_root=work_root)

            target = target_store.resolve_target(environment)

        self.assertEqual(target.workspace.metadata_dir, "docker_metadata/targets")
        self.assertEqual(target.manifest.path, work_root / ".akb" / "manifests" / "avd" / "default.xml")


if __name__ == "__main__":
    unittest.main()
