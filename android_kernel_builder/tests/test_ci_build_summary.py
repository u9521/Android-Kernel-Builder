#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def _load_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "write-ci-build-summary.py"
    spec = importlib.util.spec_from_file_location("write_ci_build_summary", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


summary_script = _load_module()


class WriteCiBuildSummaryTests(unittest.TestCase):
    def test_main_reports_skipped_push_when_push_not_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.md"
            args = [
                "write-ci-build-summary.py",
                "--image-ref",
                "ghcr.io/example/gki-snapshot:test",
                "--target-input",
                "android15-6.6",
                "--build-duration-seconds",
                "15",
                "--build-step-outcome",
                "success",
                "--push-requested",
                "false",
                "--summary-file",
                str(summary_path),
            ]

            with mock.patch("sys.argv", args):
                with mock.patch.object(summary_script, "_resolve_image_digest", return_value=""):
                    result = summary_script.main()

            self.assertEqual(result, 0)
            summary_text = summary_path.read_text(encoding="utf-8")
            self.assertIn("| Push | `skipped` |", summary_text)


if __name__ == "__main__":
    unittest.main()
