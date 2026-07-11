# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import unittest

config = importlib.import_module("android_kernel_builder.builder.core.config")


class BuildConfigSchemaTests(unittest.TestCase):
    def test_kleaf_defaults_are_backend_specific(self) -> None:
        build = config.KleafBuildConfig()

        self.assertEqual(build.target, "//common:kernel_{arch}_dist")
        self.assertEqual(build.dist_flag, "dist_dir")
        self.assertEqual(build.arch, "aarch64")
        self.assertFalse(hasattr(build, "legacy_config"))
        self.assertFalse(hasattr(build, "use_ccache"))

    def test_legacy_defaults_are_backend_specific(self) -> None:
        build = config.LegacyBuildConfig(legacy_config="common/build.config.gki.{arch}")

        self.assertEqual(build.legacy_config, "common/build.config.gki.{arch}")
        self.assertEqual(build.arch, "aarch64")
        self.assertTrue(build.use_ccache)
        self.assertFalse(hasattr(build, "target"))
        self.assertFalse(hasattr(build, "warmup_target"))


if __name__ == "__main__":
    unittest.main()
