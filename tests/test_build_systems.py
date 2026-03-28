# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

build_systems = importlib.import_module("gki_builder.build_systems")


class BuildSystemSpecTests(unittest.TestCase):
    def test_supported_build_systems_include_kleaf_and_legacy(self) -> None:
        supported = build_systems.supported_build_systems()

        self.assertIn("kleaf", supported)
        self.assertIn("legacy", supported)

    def test_kleaf_defaults_use_ccache_to_false(self) -> None:
        spec = build_systems.get_build_system_spec("kleaf")

        if spec is None:
            self.fail("kleaf spec must exist")
        self.assertFalse(spec.default_use_ccache)
        self.assertTrue(spec.supports_warmup)
        self.assertFalse(spec.supports_ccache)

    def test_legacy_defaults_use_ccache_to_true(self) -> None:
        spec = build_systems.get_build_system_spec("legacy")

        if spec is None:
            self.fail("legacy spec must exist")
        self.assertTrue(spec.default_use_ccache)
        self.assertFalse(spec.supports_warmup)
        self.assertTrue(spec.supports_ccache)

    def test_unknown_build_system_returns_none(self) -> None:
        spec = build_systems.get_build_system_spec("unknown")

        self.assertIsNone(spec)


if __name__ == "__main__":
    unittest.main()
