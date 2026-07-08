# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

code_sync = importlib.import_module("android_kernel_builder.builder.code_sync")
code_sync_repo = importlib.import_module("android_kernel_builder.builder.code_sync.repo")
code_sync_sync = importlib.import_module("android_kernel_builder.builder.code_sync.sync")
targets = importlib.import_module("android_kernel_builder.builder.targets")


class CodeSyncHelpersTests(unittest.TestCase):
    def test_sync_source_creates_bazel_cache_for_kleaf_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "source-code" / "sample-kleaf"
            cache_root = temp_root / "cache" / "sample-kleaf"
            source_dir.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-kleaf",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android15-6.6"),
                build=targets.BuildConfig(system="kleaf"),
                config_path=Path("sample-kleaf.toml"),
            )

            with mock.patch.object(code_sync_repo, "_repo_init"):
                with mock.patch.object(code_sync_repo, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(code_sync_sync, "run_command"):
                        code_sync.sync_source(target, source_dir, cache_root, jobs=1)

            self.assertTrue((cache_root / "repo").exists())
            self.assertTrue((cache_root / "bazel").exists())
            self.assertTrue((cache_root / "bazel" / "state").exists())
            self.assertTrue((cache_root / "bazel" / "repo").exists())
            self.assertTrue((cache_root / "bazel" / "diskcache").exists())
            self.assertTrue((cache_root / "bazel" / "kleaf-out").exists())
            self.assertFalse((cache_root / "ccache").exists())

    def test_sync_source_creates_ccache_for_legacy_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "source-code" / "sample-legacy"
            cache_root = temp_root / "cache" / "sample-legacy"
            source_dir.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android12-5.10"),
                build=targets.BuildConfig(system="legacy", legacy_config="common/build.config.gki.{arch}"),
                config_path=Path("sample-legacy.toml"),
            )

            with mock.patch.object(code_sync_repo, "_repo_init"):
                with mock.patch.object(code_sync_repo, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(code_sync_sync, "run_command"):
                        code_sync.sync_source(target, source_dir, cache_root, jobs=1)

            self.assertTrue((cache_root / "repo").exists())
            self.assertFalse((cache_root / "bazel").exists())
            self.assertTrue((cache_root / "ccache").exists())

    def test_sync_source_skips_ccache_dir_for_legacy_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "source-code" / "sample-legacy"
            cache_root = temp_root / "cache" / "sample-legacy"
            source_dir.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android12-5.10"),
                build=targets.BuildConfig(system="legacy", legacy_config="common/build.config.gki.{arch}", use_ccache=False),
                config_path=Path("sample-legacy.toml"),
            )

            with mock.patch.object(code_sync_repo, "_repo_init"):
                with mock.patch.object(code_sync_repo, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(code_sync_sync, "run_command"):
                        code_sync.sync_source(target, source_dir, cache_root, jobs=1)

            self.assertTrue((cache_root / "repo").exists())
            self.assertFalse((cache_root / "bazel").exists())
            self.assertFalse((cache_root / "ccache").exists())

    def test_detects_deprecated_branch(self) -> None:
        output = "deadbeef\trefs/heads/deprecated/android14-6.1\n"
        detected = code_sync_repo._detect_deprecated_branch(output, "android14-6.1")
        self.assertEqual(detected, "deprecated/android14-6.1")

    def test_extracts_kernel_branch_from_common_branch(self) -> None:
        self.assertEqual(
            code_sync_repo._kernel_project_branch_name("common-android15-6.6"),
            "android15-6.6",
        )
        self.assertIsNone(code_sync_repo._kernel_project_branch_name("android15-6.6"))

    def test_rewrites_manifest_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "default.xml"
            manifest_path.write_text(
                '<manifest><project revision="android14-6.1" /></manifest>\n',
                encoding="utf-8",
            )

            rewritten = code_sync.rewrite_manifest_revisions(
                manifest_path,
                "android14-6.1",
                "deprecated/android14-6.1",
            )

            self.assertTrue(rewritten)
            self.assertIn(
                'revision="deprecated/android14-6.1"',
                manifest_path.read_text(encoding="utf-8"),
            )

    def test_skips_autodetect_when_disabled(self) -> None:
        manifest = importlib.import_module("android_kernel_builder.builder.targets").ManifestConfig(
            source="remote",
            url="https://android.googlesource.com/kernel/manifest",
            branch="common-android14-6.1",
            autodetect_deprecated=False,
        )
        target = importlib.import_module("android_kernel_builder.builder.targets").TargetConfig(
            name="sample",
            manifest=manifest,
            build=importlib.import_module("android_kernel_builder.builder.targets").BuildConfig(),
            config_path=Path("sample.toml"),
        )
        self.assertIsNone(code_sync_repo._auto_fix_remote_deprecated_branch(target, Path(".")))


if __name__ == "__main__":
    unittest.main()
