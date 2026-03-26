# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

load_target_config = importlib.import_module("gki_builder.targets").load_target_config


class TargetConfigTests(unittest.TestCase):
    def test_load_remote_target(self) -> None:
        target = load_target_config("configs/targets/android15-6.6.toml")
        self.assertEqual(target.name, "android15-6.6")
        self.assertEqual(target.manifest.source, "remote")
        self.assertTrue(target.manifest.autodetect_deprecated)
        self.assertGreater(target.build.jobs, 0)
        self.assertEqual(target.build.system, "kleaf")

    def test_load_local_target_with_relative_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifests = temp_root / "manifests"
            manifests.mkdir(parents=True)
            (manifests / "default.xml").write_text("<manifest />\n", encoding="utf-8")

            config = temp_root / "target.toml"
            config.write_text(
                """
name = "sample"

[manifest]
source = "local"
url = "https://example.com/manifest"
path = "manifests/default.xml"
minimal = true

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            target = load_target_config(config)
            self.assertEqual(target.manifest.path, manifests.resolve() / "default.xml")
            self.assertEqual(target.manifest.url, "https://example.com/manifest")
            self.assertTrue(target.manifest.minimal)
            self.assertFalse(target.manifest.autodetect_deprecated)

    def test_requires_explicit_build_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            config = temp_root / "target.toml"
            config.write_text(
                """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
arch = "aarch64"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "build.system"):
                load_target_config(config)

    def test_rejects_non_positive_build_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            config = temp_root / "target.toml"
            config.write_text(
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
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Build jobs must be positive"):
                load_target_config(config)


if __name__ == "__main__":
    unittest.main()
