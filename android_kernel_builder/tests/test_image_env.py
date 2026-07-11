#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import json
from pathlib import Path
import tempfile
import unittest

image_env = importlib.import_module("android_kernel_builder.builder.extensions.image_env")


def _target_configs_root(project_root: Path) -> Path:
    return project_root / "android_kernel_builder" / "configs" / "targets"


def _target_manifests_root(project_root: Path) -> Path:
    return project_root / "android_kernel_builder" / "configs" / "manifests"


class ImageEnvTests(unittest.TestCase):
    def test_prepare_runtime_image_layout_writes_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            workspace_root = temp_root / "workspace"
            config_path = _target_configs_root(project_root) / "sample.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                """
name = "sample"

[repo]
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android15-6.6"

[kleaf]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            image_env.prepare_runtime_image_layout(
                "sample",
                workspace_root=workspace_root,
                project_root=project_root,
            )

            image_dir = workspace_root / "docker_datas"
            env_text = (image_dir / "akb.env").read_text(encoding="utf-8")
            image_info = json.loads((image_dir / "image.json").read_text(encoding="utf-8"))
            self.assertIn("export AKB_TARGET=sample\n", env_text)
            self.assertIn("export AKB_TARGET_NAME=sample\n", env_text)
            self.assertIn(f"export AKB_SOURCE_ROOT={workspace_root / 'source-code' / 'sample'}\n", env_text)
            self.assertIn("export AKB_SOURCE_MODE=config\n", env_text)
            self.assertIn(f"export AKB_DOCKER_DATAS_ROOT={image_dir}\n", env_text)
            self.assertIn(f"export AKB_TARGET_METADATA_ROOT={image_dir / 'targets' / 'sample'}\n", env_text)
            self.assertIn(f"export AKB_DIST_DIR={(workspace_root / 'out' / 'sample').resolve()}\n", env_text)
            self.assertIn("export AKB_BUILD_SYSTEM=kleaf\n", env_text)
            self.assertNotIn("AKB_MANIFEST_", env_text)
            self.assertNotIn("AKB_REPO_", env_text)
            self.assertNotIn("export GKI_", env_text)
            self.assertEqual(image_info["target"], "sample")
            self.assertEqual(image_info["source_mode"], "config")
            self.assertEqual(image_info["cache_layout_version"], 1)

    def test_prepare_runtime_image_layout_accepts_local_repo_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            workspace_root = temp_root / "workspace"
            config_path = _target_configs_root(project_root) / "sample.toml"
            manifest_path = _target_manifests_root(project_root) / "sample.xml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("<manifest />\n", encoding="utf-8")
            config_path.write_text(
                """
name = "sample"

[repo]
url = "https://android.googlesource.com/kernel/manifest"
path = "sample.xml"

[kleaf]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            image_env.prepare_runtime_image_layout(
                "sample",
                workspace_root=workspace_root,
                project_root=project_root,
            )

            env_text = (workspace_root / "docker_datas" / "akb.env").read_text(encoding="utf-8")
            self.assertNotIn("AKB_MANIFEST_", env_text)
            self.assertNotIn("AKB_REPO_", env_text)

    def test_prepare_runtime_image_layout_rejects_repo_path_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            workspace_root = temp_root / "workspace"
            config_path = _target_configs_root(project_root) / "sample.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                """
name = "sample"

[repo]
url = "https://android.googlesource.com/kernel/manifest"
path = "../escape.xml"

[kleaf]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "path must stay inside the manifests root"):
                image_env.prepare_runtime_image_layout(
                    "sample",
                    workspace_root=workspace_root,
                    project_root=project_root,
                )

    def test_prepare_runtime_image_layout_resolves_inherited_repo_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            workspace_root = temp_root / "workspace"
            base_config_path = _target_configs_root(project_root) / "base.toml"
            child_config_path = _target_configs_root(project_root) / "child.toml"
            base_config_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_root.mkdir(parents=True, exist_ok=True)
            base_config_path.write_text(
                """
name = "base"
base = true

[repo]
url = "https://android.googlesource.com/kernel/manifest"
branch = "common-android12-5.10"

[kleaf]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            child_config_path.write_text(
                """
name = "child"
extends = "base"

[repo]
branch = "common-android12-5.10-2025-09"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            image_env.prepare_runtime_image_layout(
                "child",
                workspace_root=workspace_root,
                project_root=project_root,
            )

            env_text = (workspace_root / "docker_datas" / "akb.env").read_text(encoding="utf-8")
            self.assertIn(f"export AKB_SOURCE_ROOT={workspace_root / 'source-code' / 'child'}\n", env_text)
            self.assertNotIn("AKB_MANIFEST_", env_text)
            self.assertNotIn("AKB_REPO_", env_text)


if __name__ == "__main__":
    unittest.main()
