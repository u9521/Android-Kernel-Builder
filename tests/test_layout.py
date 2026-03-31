#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

layout = importlib.import_module("gki_builder.layout")


class LayoutTests(unittest.TestCase):
    def test_host_layout_paths_use_fixed_structure(self) -> None:
        work_root = Path("/tmp/demo")

        self.assertEqual(layout.akb_root(work_root), Path("/tmp/demo/.akb"))
        self.assertEqual(layout.akb_config_file(work_root), Path("/tmp/demo/.akb/config.toml"))
        self.assertEqual(layout.targets_link(work_root), Path("/tmp/demo/targets"))
        self.assertEqual(layout.target_configs_root(work_root), Path("/tmp/demo/.akb/targets/configs"))
        self.assertEqual(layout.target_manifests_root(work_root), Path("/tmp/demo/.akb/targets/manifests"))
        self.assertEqual(layout.target_config_file(work_root, "sample"), Path("/tmp/demo/.akb/targets/configs/sample.toml"))
        self.assertEqual(layout.akb_venv_root(work_root), Path("/tmp/demo/.akb/venv"))
        self.assertEqual(layout.akb_bin_root(work_root), Path("/tmp/demo/.akb/bin"))
        self.assertEqual(layout.cache_root(work_root), Path("/tmp/demo/.cache"))
        self.assertEqual(layout.output_root(work_root), Path("/tmp/demo/out"))
        self.assertEqual(layout.ccache_tools_root(layout.cache_root(work_root)), Path("/tmp/demo/.cache/.ccache-tools"))
        self.assertEqual(layout.ccache_clang_link(layout.cache_root(work_root)), Path("/tmp/demo/.cache/.ccache-tools/clang"))

    def test_docker_layout_paths_use_fixed_workspace_root(self) -> None:
        work_root = layout.DOCKER_WORK_ROOT

        self.assertEqual(work_root, Path("/workspace"))
        self.assertEqual(layout.active_target_file(work_root), Path("/workspace/.akb/active-target.toml"))
        self.assertEqual(layout.embedded_manifests_root(work_root), Path("/workspace/.akb/manifests"))
        self.assertEqual(layout.docker_datas_root(work_root), Path("/workspace/docker_datas"))
        self.assertEqual(layout.docker_target_metadata_dir(work_root), Path("/workspace/docker_datas/targets"))
        self.assertEqual(layout.docker_target_metadata_root(work_root, "sample"), Path("/workspace/docker_datas/targets/sample"))
        self.assertEqual(layout.docker_env_file(work_root), Path("/workspace/docker_datas/gki-builder.env"))
        self.assertEqual(layout.docker_image_info_file(work_root), Path("/workspace/docker_datas/image.json"))
        self.assertEqual(layout.docker_outerimage_root(work_root), Path("/workspace/docker_datas/outerimage"))
        self.assertEqual(layout.docker_container_cache_image(work_root), Path("/workspace/docker_datas/container_cache.img"))
        self.assertEqual(layout.docker_outer_cache_image(work_root), Path("/workspace/docker_datas/outerimage/outer-cache.img"))
        self.assertEqual(layout.docker_next_outer_cache_image(work_root), Path("/workspace/docker_datas/outerimage/next-outer-cache.img"))
        self.assertEqual(layout.ccache_tools_root(layout.cache_root(work_root)), Path("/workspace/.cache/.ccache-tools"))
        self.assertEqual(layout.ccache_clang_link(layout.cache_root(work_root)), Path("/workspace/.cache/.ccache-tools/clang"))


if __name__ == "__main__":
    unittest.main()
