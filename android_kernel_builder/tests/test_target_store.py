#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest import mock

layout = importlib.import_module("android_kernel_builder.builder.layout")
target_store = importlib.import_module("android_kernel_builder.builder.targets.store")


class TargetStoreTests(unittest.TestCase):
    def test_load_project_target_uses_manifest_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_project(project_root)
            (layout.target_manifests_root(project_root) / "default.xml").write_text("<manifest />\n", encoding="utf-8")
            self._write_target(project_root, "sample", self._local_target("sample"))

            target = target_store.load_project_target(project_root, "sample")

        self.assertEqual(target.name, "sample")
        self.assertEqual(target.manifest.path, layout.target_manifests_root(project_root) / "default.xml")

    def test_resolve_target_uses_akb_target_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_project(project_root)
            self._write_target(project_root, "sample", self._remote_target("sample"))

            with mock.patch.dict(os.environ, {"AKB_TARGET": "sample"}):
                target = target_store.resolve_target(project_root)

        self.assertEqual(target.name, "sample")

    def test_target_config_path_falls_back_to_declared_name_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_project(project_root)
            self._write_target(project_root, "android14", self._remote_target("sample"))

            output = io.StringIO()
            with redirect_stdout(output):
                target = target_store.load_project_target(project_root, "sample")

        self.assertEqual(target.name, "sample")
        self.assertIn("target config mismatch", output.getvalue())

    def test_target_config_path_rejects_base_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_project(project_root)
            self._write_target(
                project_root,
                "sample-base",
                """
name = "sample-base"
base = true

[manifest]
url = "https://example.com/manifest"
""",
            )

            with self.assertRaisesRegex(ValueError, "base config"):
                target_store.target_config_path(project_root, "sample-base")

    def _write_project(self, project_root: Path) -> None:
        (project_root / "pyproject.toml").write_text("[project]\nname = \"sample\"\n", encoding="utf-8")
        layout.target_configs_root(project_root).mkdir(parents=True, exist_ok=True)
        layout.target_manifests_root(project_root).mkdir(parents=True, exist_ok=True)

    def _write_target(self, project_root: Path, target_name: str, content: str) -> None:
        layout.target_config_file(project_root, target_name).write_text(content.strip() + "\n", encoding="utf-8")

    def _local_target(self, name: str) -> str:
        return f"""
name = "{name}"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "default.xml"

[build]
system = "kleaf"
arch = "aarch64"
"""

    def _remote_target(self, name: str) -> str:
        return f"""
name = "{name}"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
"""


if __name__ == "__main__":
    unittest.main()
