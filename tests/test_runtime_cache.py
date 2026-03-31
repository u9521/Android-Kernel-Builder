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

layout = importlib.import_module("gki_builder.layout")
runtime_cache = importlib.import_module("gki_builder.runtime_cache")


class RuntimeCacheTests(unittest.TestCase):
    def test_init_runtime_cache_reuses_matching_outer_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_container_metadata(work_root, "abc123")
            outer_root = layout.docker_outerimage_root(work_root)
            outer_root.mkdir(parents=True, exist_ok=True)
            layout.docker_outer_cache_image(work_root).write_bytes(b"outer")
            layout.docker_outer_cache_metadata_file(work_root).write_text(
                '{"version": 1, "cache_layout_version": 1, "target": "sample", "container_cache_sha256": "abc123"}\n',
                encoding="utf-8",
            )

            with mock.patch.object(runtime_cache, "run_command") as run_command:
                with mock.patch.object(runtime_cache, "_create_empty_outer_cache_image") as create_outer:
                    runtime_cache.init_runtime_cache(work_root)

            create_outer.assert_not_called()
            commands = [call.args[0] for call in run_command.call_args_list]
            self.assertEqual(commands[0][0:2], ["mount", "-v"])
            self.assertIn(str(layout.docker_container_cache_image(work_root)), commands[0])
            self.assertIn(str(layout.docker_outer_cache_image(work_root)), commands[1])
            self.assertEqual(commands[2][0:4], ["mount", "-v", "-t", "overlay"])

    def test_init_runtime_cache_recreates_outer_cache_on_metadata_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_container_metadata(work_root, "new-sha")
            outer_root = layout.docker_outerimage_root(work_root)
            outer_root.mkdir(parents=True, exist_ok=True)
            layout.docker_outer_cache_image(work_root).write_bytes(b"outer")
            layout.docker_outer_cache_metadata_file(work_root).write_text(
                '{"version": 1, "cache_layout_version": 1, "target": "sample", "container_cache_sha256": "old-sha"}\n',
                encoding="utf-8",
            )

            with mock.patch.object(runtime_cache, "run_command"):
                with mock.patch.object(runtime_cache, "_create_empty_outer_cache_image") as create_outer:
                    runtime_cache.init_runtime_cache(work_root)

            create_outer.assert_called_once()

    def test_export_runtime_cache_renames_outer_cache_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            outer_root = layout.docker_outerimage_root(work_root)
            outer_root.mkdir(parents=True, exist_ok=True)
            layout.docker_outer_cache_image(work_root).write_bytes(b"outer")
            layout.docker_outer_cache_metadata_file(work_root).write_text(
                '{"version": 1, "cache_layout_version": 1, "target": "sample", "container_cache_sha256": "sha"}\n',
                encoding="utf-8",
            )

            with mock.patch.object(runtime_cache, "run_command") as run_command:
                runtime_cache.export_runtime_cache(work_root)

            self.assertFalse(layout.docker_outer_cache_image(work_root).exists())
            self.assertFalse(layout.docker_outer_cache_metadata_file(work_root).exists())
            self.assertEqual(layout.docker_next_outer_cache_image(work_root).read_bytes(), b"outer")
            self.assertTrue(layout.docker_next_outer_cache_metadata_file(work_root).exists())
            self.assertEqual(run_command.call_args_list[0].args[0], ["e2fsck", "-fy", str(layout.docker_outer_cache_image(work_root))])
            self.assertEqual(run_command.call_args_list[1].args[0], ["resize2fs", "-M", str(layout.docker_outer_cache_image(work_root))])

    def test_finalize_runtime_cache_cleans_up_then_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)

            with mock.patch.object(runtime_cache, "cleanup_runtime_cache") as cleanup_runtime_cache:
                with mock.patch.object(runtime_cache, "export_runtime_cache") as export_runtime_cache:
                    runtime_cache.finalize_runtime_cache(work_root)

            cleanup_runtime_cache.assert_called_once_with(work_root)
            export_runtime_cache.assert_called_once_with(work_root)

    def test_create_empty_outer_cache_image_uses_sparse_10g_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            self._write_container_metadata(work_root, "sha")

            with mock.patch.object(runtime_cache, "run_command") as run_command:
                runtime_cache._create_empty_outer_cache_image(
                    work_root,
                    runtime_cache._load_required_metadata(layout.docker_container_cache_metadata_file(work_root)),
                )

            truncate_command = run_command.call_args_list[0].args[0]
            self.assertEqual(truncate_command[0:3], ["truncate", "-s", str(10 * 1024 * 1024 * 1024)])

    def test_prepare_base_container_cache_creates_sparse_10g_image_and_mounts_cache_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.docker_datas_root(work_root).mkdir(parents=True, exist_ok=True)

            with mock.patch.object(runtime_cache, "run_command") as run_command:
                runtime_cache.prepare_base_container_cache(work_root)

            self.assertEqual(
                run_command.call_args_list[0].args[0],
                ["truncate", "-s", str(10 * 1024 * 1024 * 1024), str(layout.docker_container_cache_image(work_root))],
            )
            self.assertEqual(
                run_command.call_args_list[2].args[0],
                ["mount", "-v", "-o", "loop", str(layout.docker_container_cache_image(work_root)), str(layout.cache_root(work_root))],
            )

    def test_pack_container_cache_shrinks_existing_image_and_writes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            layout.docker_datas_root(work_root).mkdir(parents=True, exist_ok=True)
            layout.cache_root(work_root).mkdir(parents=True, exist_ok=True)
            layout.docker_container_cache_image(work_root).write_bytes(b"container")
            layout.docker_image_info_file(work_root).write_text('{"target": "sample"}\n', encoding="utf-8")

            with mock.patch.object(runtime_cache, "run_command") as run_command:
                with mock.patch.object(runtime_cache, "sha256_file", return_value="sha256"):
                    runtime_cache.pack_container_cache(work_root)

            self.assertEqual(run_command.call_args_list[0].args[0], ["e2fsck", "-fy", str(layout.docker_container_cache_image(work_root))])
            self.assertEqual(run_command.call_args_list[1].args[0], ["resize2fs", "-M", str(layout.docker_container_cache_image(work_root))])
            self.assertIn('"container_cache_sha256": "sha256"', layout.docker_container_cache_metadata_file(work_root).read_text(encoding="utf-8"))

    def _write_container_metadata(self, work_root: Path, container_sha: str) -> None:
        datas_root = layout.docker_datas_root(work_root)
        datas_root.mkdir(parents=True, exist_ok=True)
        layout.docker_container_cache_image(work_root).write_bytes(b"container")
        layout.docker_container_cache_metadata_file(work_root).write_text(
            (
                "{"
                '"version": 1, '
                '"cache_layout_version": 1, '
                '"target": "sample", '
                f'"container_cache_sha256": "{container_sha}"'
                "}\n"
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
