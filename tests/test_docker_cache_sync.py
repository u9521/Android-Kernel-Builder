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

docker_cache_sync = importlib.import_module("gki_builder.docker_cache_sync")


class DockerCacheSyncTests(unittest.TestCase):
    def test_is_docker_context_accepts_runtime_marker_without_dockerenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            active_target = runtime_cache.parent / ".akb" / "active-target.toml"
            active_target.parent.mkdir(parents=True, exist_ok=True)
            active_target.write_text("name = \"android15-6.6\"\n", encoding="utf-8")

            original_exists = Path.exists

            def fake_exists(path: Path) -> bool:
                if path in (Path("/.dockerenv"), Path("/run/.containerenv")):
                    return False
                return original_exists(path)

            with mock.patch.object(docker_cache_sync.Path, "exists", autospec=True, side_effect=fake_exists):
                self.assertTrue(docker_cache_sync._is_docker_context(runtime_cache))

    def test_prepare_cache_keeps_image_cache_when_host_cache_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            (runtime_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (runtime_cache / "bazel").mkdir(parents=True, exist_ok=True)
            (runtime_cache / "ccache" / "stats").write_text("seed\n", encoding="utf-8")
            (runtime_cache / "bazel" / "artifact").write_text("seed\n", encoding="utf-8")

            with mock.patch.object(docker_cache_sync, "_has_capability", return_value=True):
                with mock.patch.object(docker_cache_sync.os, "chown"):
                    docker_cache_sync.prepare_cache(runtime_cache, host_cache)

            self.assertFalse(runtime_cache.is_symlink())
            self.assertFalse(host_cache.exists())
            self.assertEqual((runtime_cache / "ccache" / "stats").read_text(encoding="utf-8"), "seed\n")
            self.assertEqual((runtime_cache / "bazel" / "artifact").read_text(encoding="utf-8"), "seed\n")

    def test_prepare_cache_prefers_existing_host_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            (runtime_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (runtime_cache / "ccache" / "stats").write_text("image\n", encoding="utf-8")
            (host_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache" / "stats").write_text("repo\n", encoding="utf-8")

            with mock.patch.object(docker_cache_sync, "_has_capability", return_value=True):
                with mock.patch.object(docker_cache_sync.os, "chown"):
                    docker_cache_sync.prepare_cache(runtime_cache, host_cache)

            self.assertTrue(runtime_cache.is_symlink())
            self.assertEqual(runtime_cache.resolve(), host_cache.resolve())
            self.assertEqual((runtime_cache / "ccache" / "stats").read_text(encoding="utf-8"), "repo\n")
            self.assertEqual((host_cache / "ccache" / "stats").read_text(encoding="utf-8"), "repo\n")

    def test_prepare_cache_uses_existing_parent_when_runtime_cache_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            runtime_cache.parent.mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache" / "stats").write_text("repo\n", encoding="utf-8")

            with mock.patch.object(docker_cache_sync, "_has_capability", return_value=True):
                with mock.patch.object(docker_cache_sync.os, "chown") as chown:
                    docker_cache_sync.prepare_cache(runtime_cache, host_cache)

            self.assertTrue(runtime_cache.is_symlink())
            self.assertEqual(runtime_cache.resolve(), host_cache.resolve())
            self.assertTrue(chown.called)

    def test_prepare_cache_requires_chown_permission_when_host_cache_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            runtime_cache.mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache" / "stats").write_text("repo\n", encoding="utf-8")

            with mock.patch.object(docker_cache_sync, "_has_capability", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "requires CAP_CHOWN"):
                    docker_cache_sync.prepare_cache(runtime_cache, host_cache)

    def test_prepare_cache_tolerates_disappearing_entries_during_chown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            runtime_cache.mkdir(parents=True, exist_ok=True)
            transient_file = host_cache / "kleaf" / "entry"
            transient_file.parent.mkdir(parents=True, exist_ok=True)
            transient_file.write_text("repo\n", encoding="utf-8")

            def fake_chown(path: str | Path, uid: int, gid: int) -> None:
                if Path(path) == transient_file:
                    transient_file.unlink()
                    raise FileNotFoundError(path)

            with mock.patch.object(docker_cache_sync, "_has_capability", return_value=True):
                with mock.patch.object(docker_cache_sync.os, "chown", side_effect=fake_chown):
                    docker_cache_sync.prepare_cache(runtime_cache, host_cache)

            self.assertTrue(runtime_cache.is_symlink())
            self.assertEqual(runtime_cache.resolve(), host_cache.resolve())

    def test_save_cache_exports_runtime_cache_when_host_cache_was_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            (runtime_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (runtime_cache / "bazel").mkdir(parents=True, exist_ok=True)
            (runtime_cache / "ccache" / "stats").write_text("seed\n", encoding="utf-8")
            (runtime_cache / "bazel" / "artifact").write_text("seed\n", encoding="utf-8")

            docker_cache_sync.save_cache(runtime_cache, host_cache)

            self.assertTrue(host_cache.exists())
            self.assertEqual((host_cache / "ccache" / "stats").read_text(encoding="utf-8"), "seed\n")
            self.assertEqual((host_cache / "bazel" / "artifact").read_text(encoding="utf-8"), "seed\n")

    def test_save_cache_materializes_runtime_cache_when_runtime_points_to_host_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            runtime_cache = temp_root / "workspace" / ".cache"
            host_cache = temp_root / "host-cache"
            host_cache.mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache").mkdir(parents=True, exist_ok=True)
            (host_cache / "ccache" / "stats").write_text("repo\n", encoding="utf-8")
            runtime_cache.parent.mkdir(parents=True, exist_ok=True)
            runtime_cache.symlink_to(host_cache)

            docker_cache_sync.save_cache(runtime_cache, host_cache)

            self.assertFalse(runtime_cache.is_symlink())
            self.assertEqual((runtime_cache / "ccache" / "stats").read_text(encoding="utf-8"), "repo\n")
            self.assertEqual((host_cache / "ccache" / "stats").read_text(encoding="utf-8"), "repo\n")


if __name__ == "__main__":
    unittest.main()
