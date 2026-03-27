#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

image_package = importlib.import_module("gki_builder.image_package")


class ImagePackageTests(unittest.TestCase):
    def test_package_image_context_copies_minimal_required_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            (repo_root / "src" / "gki_builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "manifests" / "avd").mkdir(parents=True, exist_ok=True)
            (repo_root / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "tests").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "src" / "gki_builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "configs" / "targets" / "sample.toml").write_text("name='sample'\n", encoding="utf-8")
            (repo_root / "manifests" / "avd" / "sample.xml").write_text("<manifest/>\n", encoding="utf-8")
            (repo_root / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
            (repo_root / "tests" / "ignore.txt").write_text("ignore\n", encoding="utf-8")

            manifest = image_package.package_image_context(repo_root, output_dir)

            self.assertTrue((output_dir / "src" / "gki_builder" / "cli.py").exists())
            self.assertTrue((output_dir / "configs" / "targets" / "sample.toml").exists())
            self.assertTrue((output_dir / "manifests" / "avd" / "sample.xml").exists())
            self.assertTrue((output_dir / "docker" / "workspace.Dockerfile").exists())
            self.assertFalse((output_dir / "tests").exists())
            self.assertIn("src", manifest["included_roots"])

    def test_package_image_context_bundles_selected_local_manifest_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            work_root = Path(temp_dir) / "work"
            (repo_root / "src" / "gki_builder").mkdir(parents=True, exist_ok=True)
            (repo_root / "configs" / "targets").mkdir(parents=True, exist_ok=True)
            (repo_root / "manifests").mkdir(parents=True, exist_ok=True)
            (repo_root / "docker").mkdir(parents=True, exist_ok=True)
            (repo_root / "LICENSE").write_text("license\n", encoding="utf-8")
            (repo_root / "README.md").write_text("readme\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            (repo_root / "src" / "gki_builder" / "cli.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            source_target_file = work_root / ".akb" / "targets" / "configs" / "sample.toml"
            target_manifest = work_root / ".akb" / "targets" / "manifests" / "avd" / "sample.xml"
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

            self.assertTrue((output_dir / ".docker-target" / "target.toml").exists())
            self.assertTrue((output_dir / ".docker-target" / "manifests" / "avd" / "sample.xml").exists())
            self.assertEqual(manifest["target_bundle_root"], ".docker-target")


if __name__ == "__main__":
    unittest.main()
