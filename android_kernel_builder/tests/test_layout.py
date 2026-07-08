#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import unittest

layout = importlib.import_module("android_kernel_builder.builder.layout")


class LayoutTests(unittest.TestCase):
    def test_host_layout_paths_use_fixed_structure(self) -> None:
        work_root = Path("/tmp/demo")

        self.assertEqual(layout.project_package_root(work_root), Path("/tmp/demo/android_kernel_builder"))
        self.assertEqual(layout.target_configs_root(work_root), Path("/tmp/demo/android_kernel_builder/configs/targets"))
        self.assertEqual(layout.target_manifests_root(work_root), Path("/tmp/demo/android_kernel_builder/configs/manifests"))
        self.assertEqual(layout.target_config_file(work_root, "sample"), Path("/tmp/demo/android_kernel_builder/configs/targets/sample.toml"))
        self.assertEqual(layout.target_source_root(work_root, "sample"), Path("/tmp/demo/source-code/sample"))
        self.assertEqual(layout.cache_root(work_root), Path("/tmp/demo/cache"))
        self.assertEqual(layout.target_cache_root(work_root, "sample"), Path("/tmp/demo/cache/sample"))
        self.assertEqual(layout.output_root(work_root), Path("/tmp/demo/out"))
        self.assertEqual(layout.target_output_root(work_root, "sample"), Path("/tmp/demo/out/sample"))
        self.assertEqual(layout.ccache_tools_root(layout.target_cache_root(work_root, "sample")), Path("/tmp/demo/cache/sample/.ccache-tools"))
        self.assertEqual(layout.ccache_clang_link(layout.target_cache_root(work_root, "sample")), Path("/tmp/demo/cache/sample/.ccache-tools/clang"))

    def test_docker_layout_paths_use_fixed_workspace_root(self) -> None:
        work_root = layout.DOCKER_WORK_ROOT

        self.assertEqual(work_root, Path("/workspace"))
        self.assertEqual(layout.target_source_root(work_root, "sample"), Path("/workspace/source-code/sample"))
        self.assertEqual(layout.target_cache_root(work_root, "sample"), Path("/workspace/cache/sample"))
        self.assertEqual(layout.target_output_root(work_root, "sample"), Path("/workspace/out/sample"))
        self.assertEqual(layout.docker_datas_root(work_root), Path("/workspace/docker_datas"))
        self.assertEqual(layout.docker_target_metadata_dir(work_root), Path("/workspace/docker_datas/targets"))
        self.assertEqual(layout.docker_target_metadata_root(work_root, "sample"), Path("/workspace/docker_datas/targets/sample"))
        self.assertEqual(layout.docker_env_file(work_root), Path("/workspace/docker_datas/akb.env"))
        self.assertEqual(layout.docker_image_info_file(work_root), Path("/workspace/docker_datas/image.json"))
        self.assertEqual(layout.docker_outerimage_root(work_root), Path("/workspace/docker_datas/outerimage"))
        self.assertEqual(layout.docker_container_cache_image(work_root), Path("/workspace/docker_datas/container_cache.img"))
        self.assertEqual(layout.docker_outer_cache_image(work_root), Path("/workspace/docker_datas/outerimage/outer-cache.img"))
        self.assertEqual(layout.docker_next_outer_cache_image(work_root), Path("/workspace/docker_datas/outerimage/next-outer-cache.img"))


if __name__ == "__main__":
    unittest.main()
