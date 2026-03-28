#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

image_env = importlib.import_module("gki_builder.image_env")


class ImageEnvTests(unittest.TestCase):
    def test_prepare_runtime_image_layout_writes_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            akb_root = temp_root / "tooling"
            workspace_root = temp_root / "workspace"
            config_path = akb_root / "configs" / "targets" / "sample.toml"
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

            image_env.prepare_runtime_image_layout(
                "configs/targets/sample.toml",
                workspace_root=workspace_root,
                project_root=akb_root,
            )

            akb_runtime_dir = workspace_root / ".akb"
            image_dir = workspace_root / "docker_metadata"
            config_text = (akb_runtime_dir / "active-target.toml").read_text(encoding="utf-8")
            env_text = (image_dir / "gki-builder.env").read_text(encoding="utf-8")
            self.assertIn('name = "sample"', config_text)
            self.assertIn('version = 1', config_text)
            self.assertNotIn('metadata_dir = ', config_text)
            self.assertIn(f"export GKI_TARGET_NAME=sample\n", env_text)
            self.assertIn(f"export GKI_SOURCE_ROOT={workspace_root / 'android-kernel'}\n", env_text)
            self.assertIn(f"export GKI_DOCKER_METADATA_ROOT={image_dir}\n", env_text)
            self.assertIn(f"export GKI_TARGET_METADATA_ROOT={image_dir / 'targets' / 'sample'}\n", env_text)
            self.assertIn("export GKI_BUILD_SYSTEM=\n", env_text)
            self.assertIn("export GKI_MANIFEST_SOURCE=\n", env_text)

    def test_prepare_runtime_image_layout_copies_local_manifest_into_image_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            akb_root = temp_root / "tooling"
            workspace_root = temp_root / "workspace"
            config_path = akb_root / "configs" / "targets" / "sample.toml"
            manifest_path = akb_root / "configs" / "manifests" / "sample.xml"
            akb_root.mkdir(parents=True, exist_ok=True)
            (akb_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("<manifest />\n", encoding="utf-8")
            config_path.write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://android.googlesource.com/kernel/manifest"
path = "sample.xml"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            image_env.prepare_runtime_image_layout(
                "configs/targets/sample.toml",
                workspace_root=workspace_root,
                project_root=akb_root,
            )

            akb_runtime_dir = workspace_root / ".akb"
            image_dir = workspace_root / "docker_metadata"
            copied_manifest = akb_runtime_dir / "manifests" / "sample.xml"
            config_text = (akb_runtime_dir / "active-target.toml").read_text(encoding="utf-8")
            env_text = (image_dir / "gki-builder.env").read_text(encoding="utf-8")
            self.assertEqual(copied_manifest.read_text(encoding="utf-8"), "<manifest />\n")
            self.assertIn('path = "sample.xml"', config_text)
            self.assertIn("export GKI_MANIFEST_SOURCE=local\n", env_text)
            self.assertIn("export GKI_MANIFEST_PATH=sample.xml\n", env_text)

    def test_prepare_runtime_image_layout_rejects_manifest_path_outside_search_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            akb_root = temp_root / "tooling"
            workspace_root = temp_root / "workspace"
            config_path = akb_root / "configs" / "targets" / "sample.toml"
            akb_root.mkdir(parents=True, exist_ok=True)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://android.googlesource.com/kernel/manifest"
path = "../escape.xml"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must be relative to configs/manifests"):
                image_env.prepare_runtime_image_layout(
                    "configs/targets/sample.toml",
                    workspace_root=workspace_root,
                    project_root=akb_root,
                )


if __name__ == "__main__":
    unittest.main()
