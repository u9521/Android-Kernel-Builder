# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

workspace = importlib.import_module("gki_builder.workspace")


class WorkspaceHelpersTests(unittest.TestCase):
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
