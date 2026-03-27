#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

environment = importlib.import_module("gki_builder.environment")
layout = importlib.import_module("gki_builder.layout")


class EnvironmentTests(unittest.TestCase):
    def test_discover_host_work_root_walks_up_to_akb_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            nested = work_root / "src" / "kernel"
            nested.mkdir(parents=True)
            layout.akb_config_file(work_root).parent.mkdir(parents=True, exist_ok=True)
            layout.akb_config_file(work_root).write_text("version = 1\n", encoding="utf-8")

            resolved = environment.discover_host_work_root(nested)

        self.assertEqual(resolved, work_root)

    def test_discover_host_work_root_rejects_missing_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(FileNotFoundError, "AKB environment not found"):
                environment.discover_host_work_root(Path(temp_dir))

    def test_discover_current_environment_uses_fixed_docker_root(self) -> None:
        with mock.patch.object(environment, "is_docker_runtime", return_value=True):
            resolved = environment.discover_current_environment(Path("/tmp/ignored"))

        self.assertEqual(resolved.mode, "docker")
        self.assertEqual(resolved.work_root, layout.DOCKER_WORK_ROOT)

    def test_discover_current_environment_uses_embedded_docker_layout_without_dockerenv(self) -> None:
        with mock.patch.object(environment, "is_docker_runtime", return_value=False):
            with mock.patch.object(environment, "has_embedded_docker_layout", return_value=True):
                resolved = environment.discover_current_environment(Path("/tmp/ignored"))

        self.assertEqual(resolved.mode, "docker")
        self.assertEqual(resolved.work_root, layout.DOCKER_WORK_ROOT)


if __name__ == "__main__":
    unittest.main()
