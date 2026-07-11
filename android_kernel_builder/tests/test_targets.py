# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest

layout = importlib.import_module("android_kernel_builder.builder.layout")
config = importlib.import_module("android_kernel_builder.builder.core.config")
target_store = importlib.import_module("android_kernel_builder.builder.core.config.resolver")


class TargetConfigTests(unittest.TestCase):
    def test_loads_kleaf_build_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"
target = "//common:kernel_{arch}_dist"
warmup_target = "//common:kernel_{arch}"
dist_dir = "dist"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertIsInstance(target.sync, config.RepoConfig)
        self.assertEqual(target.sync.url, "https://example.com/manifest")
        self.assertEqual(target.sync.branch, "common-android15-6.6")
        self.assertIsInstance(target.build, config.KleafBuildConfig)
        self.assertEqual(target.build.target, "//common:kernel_{arch}_dist")
        self.assertEqual(target.build.warmup_target, "//common:kernel_{arch}")
        self.assertEqual(target.build.dist_dir, "dist")
        self.assertFalse(hasattr(target.build, "legacy_config"))

    def test_loads_legacy_build_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android12-5.10"

[legacy]
arch = "aarch64"
legacy_config = "common/build.config.gki.{arch}"
use_ccache = false
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertIsInstance(target.build, config.LegacyBuildConfig)
        self.assertEqual(target.build.legacy_config, "common/build.config.gki.{arch}")
        self.assertFalse(target.build.use_ccache)
        self.assertFalse(hasattr(target.build, "target"))

    def test_base_parent_allows_missing_fields_when_inherited(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "base",
                """
name = "base"
base = true

[repo]
url = "https://example.com/manifest"

[kleaf]
arch = "aarch64"
""",
            )
            self._write_target(
                work_root,
                "child",
                """
name = "child"
extends = "base"

[repo]
branch = "common-android15-6.6"
""",
            )

            target = target_store.load_project_target(work_root, "child")

        self.assertEqual(target.sync.url, "https://example.com/manifest")
        self.assertEqual(target.sync.branch, "common-android15-6.6")
        self.assertIsInstance(target.build, config.KleafBuildConfig)

    def test_load_target_with_extends_overrides_branch_and_build_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "base",
                """
name = "base"

[repo]
url = "https://example.com/manifest"
branch = "common-android14-6.1"

[kleaf]
arch = "aarch64"
target = "//common:kernel_{arch}_dist"
dist_dir = "gki/android14-6.1"
""",
            )
            self._write_target(
                work_root,
                "child",
                """
name = "child"
extends = "base"

[repo]
branch = "common-android14-6.1-2025-03"

[kleaf]
dist_dir = "child-dist"
""",
            )

            target = target_store.load_project_target(work_root, "child")

        self.assertEqual(target.sync.branch, "common-android14-6.1-2025-03")
        self.assertEqual(target.build.dist_dir, "child-dist")
        self.assertEqual(target.build.target, "//common:kernel_{arch}_dist")

    def test_rejects_base_target_as_direct_build_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "base",
                """
name = "base"
base = true

[repo]
url = "https://example.com/manifest"
""",
            )

            with self.assertRaisesRegex(ValueError, "base config"):
                target_store.target_config_path(work_root, "base")

    def test_rejects_circular_extends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(work_root, "base", 'name = "base"\nextends = "child"\n')
            self._write_target(work_root, "child", 'name = "child"\nextends = "base"\n')

            with self.assertRaisesRegex(ValueError, "Circular target inheritance"):
                target_store.load_project_target(work_root, "child")

    def test_rejects_extends_escape_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(work_root, "sample", 'name = "sample"\nextends = "../outside"\n')

            with self.assertRaisesRegex(ValueError, "Invalid extends"):
                target_store.load_project_target(work_root, "sample")

    def test_load_local_target_with_manifest_root_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            manifest_root = layout.target_manifests_root(work_root)
            manifest_root.mkdir(parents=True, exist_ok=True)
            (manifest_root / "default.xml").write_text("<manifest />\n", encoding="utf-8")
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
path = "default.xml"
minimal = true

[kleaf]
arch = "aarch64"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertEqual(target.sync.path, manifest_root / "default.xml")
        self.assertTrue(target.sync.minimal)

    def test_rejects_legacy_field_in_kleaf_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"
legacy_config = "build.config.gki"
""",
            )

            with self.assertRaisesRegex(ValueError, "Unsupported kleaf field"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_kleaf_field_in_legacy_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android12-5.10"

[legacy]
arch = "aarch64"
legacy_config = "build.config.gki"
warmup_target = "//common:kernel_{arch}"
""",
            )

            with self.assertRaisesRegex(ValueError, "Unsupported legacy field"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_multiple_build_backends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"

[legacy]
arch = "aarch64"
legacy_config = "build.config.gki"
""",
            )

            with self.assertRaisesRegex(ValueError, "Expected exactly one build backend"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_legacy_build_without_legacy_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android12-5.10"

[legacy]
arch = "aarch64"
""",
            )

            with self.assertRaisesRegex(ValueError, "legacy.legacy_config"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_non_positive_build_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"
jobs = 0
""",
            )

            with self.assertRaisesRegex(ValueError, "Build jobs must be positive"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_configurable_workspace_metadata_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[repo]
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[kleaf]
arch = "aarch64"

[workspace]
source_dir = "android-kernel"
metadata_dir = ".gki-builder"
""",
            )

            with self.assertRaisesRegex(ValueError, "workspace paths are fixed"):
                target_store.load_project_target(work_root, "sample")

    def _write_akb_config(self, work_root: Path) -> None:
        (work_root / "pyproject.toml").write_text("[project]\nname = \"sample\"\n", encoding="utf-8")
        layout.target_configs_root(work_root).mkdir(parents=True, exist_ok=True)

    def _write_target(self, work_root: Path, target_name: str, content: str) -> None:
        target_path = layout.target_config_file(work_root, target_name)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
