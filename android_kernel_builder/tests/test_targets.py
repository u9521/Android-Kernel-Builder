# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest

layout = importlib.import_module("android_kernel_builder.builder.layout")
target_store = importlib.import_module("android_kernel_builder.builder.targets.store")


class TargetConfigTests(unittest.TestCase):
    def test_base_parent_allows_missing_fields_when_inherited(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "android15-6.6-base",
                """
name = "android15-6.6-base"
base = true

[manifest]
url = "https://example.com/manifest"

[build]
arch = "aarch64"
""",
            )
            self._write_target(
                work_root,
                "android15-6.6",
                """
name = "android15-6.6"
extends = "android15-6.6-base"

[manifest]
source = "remote"
branch = "common-android15-6.6"

[build]
system = "kleaf"
""",
            )

            target = target_store.load_project_target(work_root, "android15-6.6")

        self.assertEqual(target.name, "android15-6.6")
        self.assertEqual(target.manifest.url, "https://example.com/manifest")
        self.assertEqual(target.manifest.branch, "common-android15-6.6")
        self.assertEqual(target.build.system, "kleaf")
        self.assertEqual(target.build.dist_dir, "")

    def test_rejects_base_target_as_direct_build_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "android15-6.6-base",
                """
name = "android15-6.6-base"
base = true

[manifest]
url = "https://example.com/manifest"
""",
            )

            with self.assertRaisesRegex(ValueError, "base config"):
                target_store.load_project_target(work_root, "android15-6.6-base")

    def test_load_target_with_extends_overrides_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "android14-6.1-base",
                """
name = "android14-6.1-base"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android14-6.1"
file = "default.xml"
minimal = true
autodetect_deprecated = true

[build]
system = "kleaf"
arch = "aarch64"
target = "//common:kernel_{arch}_dist"
warmup_target = "//common:kernel_{arch}"
dist_dir = "gki/android14-6.1"

""",
            )
            self._write_target(
                work_root,
                "android14-6.1-2025-03",
                """
name = "android14-6.1-2025-03"
extends = "android14-6.1-base"

[manifest]
branch = "common-android14-6.1-2025-03"
""",
            )

            target = target_store.load_project_target(work_root, "android14-6.1-2025-03")

        self.assertEqual(target.name, "android14-6.1-2025-03")
        self.assertEqual(target.manifest.url, "https://example.com/manifest")
        self.assertEqual(target.manifest.branch, "common-android14-6.1-2025-03")
        self.assertEqual(target.build.system, "kleaf")
        self.assertEqual(target.build.dist_dir, "gki/android14-6.1")

    def test_rejects_circular_extends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "base",
                """
name = "base"
extends = "child"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
""",
            )
            self._write_target(
                work_root,
                "child",
                """
name = "child"
extends = "base"

[manifest]
branch = "common-android15-6.6"
""",
            )

            with self.assertRaisesRegex(ValueError, "Circular target inheritance"):
                target_store.load_project_target(work_root, "child")

    def test_rejects_extends_escape_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"
extends = "../outside"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
""",
            )

            with self.assertRaisesRegex(ValueError, "Invalid extends"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_extends_with_file_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"
extends = "android14-6.1.toml"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
""",
            )

            with self.assertRaisesRegex(ValueError, "expected target name"):
                target_store.load_project_target(work_root, "sample")

    def test_load_remote_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"
autodetect_deprecated = true

[build]
system = "kleaf"
arch = "aarch64"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertEqual(target.name, "sample")
        self.assertEqual(target.manifest.source, "remote")
        self.assertTrue(target.manifest.autodetect_deprecated)
        self.assertGreater(target.build.jobs, 0)
        self.assertEqual(target.build.system, "kleaf")
        self.assertEqual(target.build.dist_dir, "")
        self.assertFalse(target.build.use_ccache)

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

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "default.xml"
minimal = true

[build]
system = "kleaf"
arch = "aarch64"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertEqual(target.manifest.path, manifest_root / "default.xml")
        self.assertEqual(target.manifest.url, "https://example.com/manifest")
        self.assertTrue(target.manifest.minimal)
        self.assertFalse(target.manifest.autodetect_deprecated)

    def test_loads_optional_warmup_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
target = "//common:kernel_{arch}_dist"
warmup_target = "//common:kernel_{arch}"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertEqual(target.build.warmup_target, "//common:kernel_{arch}")

    def test_requires_explicit_build_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
arch = "aarch64"
""",
            )

            with self.assertRaisesRegex(ValueError, "build.system"):
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

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
jobs = 0
""",
            )

            with self.assertRaisesRegex(ValueError, "Build jobs must be positive"):
                target_store.load_project_target(work_root, "sample")

    def test_rejects_warmup_target_for_legacy_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "legacy"
arch = "aarch64"
legacy_config = "build.config.gki"
warmup_target = "//common:kernel_{arch}"
""",
            )

            with self.assertRaisesRegex(ValueError, "build.warmup_target"):
                target_store.load_project_target(work_root, "sample")

    def test_ignores_cache_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"

[cache]
repo_dir = "custom-repo"
bazel_dir = "custom-bazel"
kleaf_dir = "custom-kleaf"
ccache_dir = "custom-ccache"
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertEqual(target.name, "sample")
        self.assertFalse(hasattr(target, "cache"))

    def test_rejects_use_ccache_for_non_legacy_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
use_ccache = true
""",
            )

            with self.assertRaisesRegex(ValueError, "build.use_ccache=true"):
                target_store.load_project_target(work_root, "sample")

    def test_allows_legacy_ccache_disabled_without_ccache_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "legacy"
arch = "aarch64"
legacy_config = "common/build.config.gki.{arch}"
use_ccache = false
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertFalse(target.build.use_ccache)

    def test_allows_legacy_ccache_enabled_without_cache_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "legacy"
arch = "aarch64"
legacy_config = "common/build.config.gki.{arch}"
use_ccache = true
""",
            )

            target = target_store.load_project_target(work_root, "sample")

        self.assertTrue(target.build.use_ccache)

    def test_rejects_configurable_workspace_metadata_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_akb_config(work_root)
            self._write_target(
                work_root,
                "sample",
                """
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
