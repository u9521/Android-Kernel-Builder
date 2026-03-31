# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

workspace = importlib.import_module("gki_builder.workspace")
targets = importlib.import_module("gki_builder.targets")


class WorkspaceHelpersTests(unittest.TestCase):
    def test_sync_source_creates_bazel_cache_for_kleaf_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            workspace_root.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-kleaf",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android15-6.6"),
                build=targets.BuildConfig(system="kleaf"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", kleaf_dir="kleaf-out", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample-kleaf.toml"),
            )

            with mock.patch.object(workspace, "_repo_init"):
                with mock.patch.object(workspace, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(workspace, "run_command"):
                        workspace.sync_source(target, workspace_root, cache_root, jobs=1)

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
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            workspace_root.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android12-5.10"),
                build=targets.BuildConfig(system="legacy", legacy_config="common/build.config.gki.{arch}"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample-legacy.toml"),
            )

            with mock.patch.object(workspace, "_repo_init"):
                with mock.patch.object(workspace, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(workspace, "run_command"):
                        workspace.sync_source(target, workspace_root, cache_root, jobs=1)

            self.assertTrue((cache_root / "repo").exists())
            self.assertFalse((cache_root / "bazel").exists())
            self.assertTrue((cache_root / "ccache").exists())

    def test_sync_source_skips_ccache_dir_for_legacy_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            workspace_root.mkdir(parents=True, exist_ok=True)
            cache_root.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote", url="https://example.com/manifest", branch="common-android12-5.10"),
                build=targets.BuildConfig(system="legacy", legacy_config="common/build.config.gki.{arch}", use_ccache=False),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample-legacy.toml"),
            )

            with mock.patch.object(workspace, "_repo_init"):
                with mock.patch.object(workspace, "_auto_fix_remote_deprecated_branch", return_value=None):
                    with mock.patch.object(workspace, "run_command"):
                        workspace.sync_source(target, workspace_root, cache_root, jobs=1)

            self.assertTrue((cache_root / "repo").exists())
            self.assertFalse((cache_root / "bazel").exists())
            self.assertFalse((cache_root / "ccache").exists())

    def test_detects_deprecated_branch(self) -> None:
        output = "deadbeef\trefs/heads/deprecated/android14-6.1\n"
        detected = workspace._detect_deprecated_branch(output, "android14-6.1")
        self.assertEqual(detected, "deprecated/android14-6.1")

    def test_extracts_kernel_branch_from_common_branch(self) -> None:
        self.assertEqual(
            workspace._kernel_project_branch_name("common-android15-6.6"),
            "android15-6.6",
        )
        self.assertIsNone(workspace._kernel_project_branch_name("android15-6.6"))

    def test_rewrites_manifest_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "default.xml"
            manifest_path.write_text(
                '<manifest><project revision="android14-6.1" /></manifest>\n',
                encoding="utf-8",
            )

            rewritten = workspace.rewrite_manifest_revisions(
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
        manifest = importlib.import_module("gki_builder.targets").ManifestConfig(
            source="remote",
            url="https://android.googlesource.com/kernel/manifest",
            branch="common-android14-6.1",
            autodetect_deprecated=False,
        )
        target = importlib.import_module("gki_builder.targets").TargetConfig(
            name="sample",
            manifest=manifest,
            build=importlib.import_module("gki_builder.targets").BuildConfig(),
            cache=importlib.import_module("gki_builder.targets").CacheConfig(),
            workspace=importlib.import_module("gki_builder.targets").WorkspaceConfig(),
            config_path=Path("sample.toml"),
        )
        self.assertIsNone(workspace._auto_fix_remote_deprecated_branch(target, Path(".")))


if __name__ == "__main__":
    unittest.main()
