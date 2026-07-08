#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest

image_package = importlib.import_module("android_kernel_builder.builder.docker_image")


class ImagePackageTests(unittest.TestCase):
    def test_package_image_context_copies_minimal_required_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            (repo_root / "android_kernel_builder" / "builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "manifests" / "avd").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "tests").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "configs" / "targets" / "sample.toml").write_text("name='sample'\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "configs" / "manifests" / "avd" / "sample.xml").write_text("<manifest/>\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
            (repo_root / "tests" / "ignore.txt").write_text("ignore\n", encoding="utf-8")

            manifest = image_package.package_image_context(repo_root, output_dir)

            self.assertTrue((output_dir / "android_kernel_builder" / "builder" / "cli.py").exists())
            self.assertTrue((output_dir / "android_kernel_builder" / "configs" / "targets" / "sample.toml").exists())
            self.assertTrue((output_dir / "android_kernel_builder" / "configs" / "manifests" / "avd" / "sample.xml").exists())
            self.assertTrue((output_dir / "android_kernel_builder" / "docker" / "workspace.Dockerfile").exists())
            self.assertTrue((output_dir / "uv.lock").exists())
            self.assertFalse((output_dir / "tests").exists())
            self.assertIn("android_kernel_builder", manifest["included_roots"])

    def test_package_image_context_bundles_selected_local_manifest_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            work_root = Path(temp_dir) / "work"
            (repo_root / "android_kernel_builder" / "builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "manifests").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            source_target_file = repo_root / "android_kernel_builder" / "configs" / "targets" / "sample.toml"
            target_manifest = repo_root / "android_kernel_builder" / "configs" / "manifests" / "avd" / "sample.xml"
            source_target_file.parent.mkdir(parents=True, exist_ok=True)
            target_manifest.parent.mkdir(parents=True, exist_ok=True)
            source_target_file.write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "avd/sample.xml"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            target_manifest.write_text("<manifest/>\n", encoding="utf-8")

            manifest = image_package.package_image_context(repo_root, output_dir, source_target_file=source_target_file)

            bundled_target = output_dir / ".docker-target" / "target.toml"
            self.assertTrue(bundled_target.exists())
            self.assertTrue((output_dir / ".docker-target" / "manifest.xml").exists())
            self.assertEqual(manifest["target_bundle_root"], ".docker-target")
            bundled_target_text = bundled_target.read_text(encoding="utf-8")
            self.assertIn("AUTO-GENERATED by akb image packaging", bundled_target_text)
            self.assertIn("Inheritance chain", bundled_target_text)
            self.assertIn('path = "manifest.xml"', bundled_target_text)

    def test_package_image_context_bundles_merged_inheritance_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            work_root = Path(temp_dir) / "work"
            (repo_root / "android_kernel_builder" / "builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "manifests").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            parent_target = repo_root / "android_kernel_builder" / "configs" / "targets" / "android15-6.6.toml"
            child_target = repo_root / "android_kernel_builder" / "configs" / "targets" / "android15-6.6-2025-10.toml"
            parent_target.parent.mkdir(parents=True, exist_ok=True)
            parent_target.write_text(
                """
name = "android15-6.6"

[manifest]
source = "remote"
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            child_target.write_text(
                """
name = "android15-6.6-2025-10"
extends = "android15-6.6"

[manifest]
branch = "common-android15-6.6-2025-10"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            image_package.package_image_context(repo_root, output_dir, source_target_file=child_target)

            bundled_target = output_dir / ".docker-target" / "target.toml"
            bundled_target_text = bundled_target.read_text(encoding="utf-8")
            self.assertIn("AUTO-GENERATED by akb image packaging", bundled_target_text)
            self.assertIn("android15-6.6.toml", bundled_target_text)
            self.assertIn("android15-6.6-2025-10.toml", bundled_target_text)
            self.assertIn('name = "android15-6.6-2025-10"', bundled_target_text)
            self.assertIn('system = "kleaf"', bundled_target_text)
            self.assertIn('branch = "common-android15-6.6-2025-10"', bundled_target_text)
            self.assertNotIn("extends", bundled_target_text)

    def test_package_image_context_rejects_manifest_path_outside_search_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            work_root = Path(temp_dir) / "work"
            (repo_root / "android_kernel_builder" / "builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "configs" / "manifests").mkdir(parents=True, exist_ok=True)
            (repo_root / "android_kernel_builder" / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "android_kernel_builder" / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            source_target_file = repo_root / "android_kernel_builder" / "configs" / "targets" / "sample.toml"
            source_target_file.parent.mkdir(parents=True, exist_ok=True)
            source_target_file.write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "../escape.xml"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must be relative to configs/manifests"):
                image_package.package_image_context(repo_root, output_dir, source_target_file=source_target_file)


if __name__ == "__main__":
    unittest.main()
