#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

build = importlib.import_module("gki_builder.build")
targets = importlib.import_module("gki_builder.targets")


class BuildUsageTests(unittest.TestCase):
    def test_analyze_workspace_usage_splits_source_repo_cache_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / ".workspace"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"

            source_dir = workspace_root / "android-kernel"
            repo_dir = source_dir / ".repo"
            metadata_dir = workspace_root / ".gki-builder" / "sample"
            repo_reference_dir = cache_root / "repo"
            bazel_dir = cache_root / "bazel"
            ccache_dir = cache_root / "ccache"
            output_dir = output_root / "dist"

            for directory in [
                source_dir,
                repo_dir,
                metadata_dir,
                repo_reference_dir,
                bazel_dir,
                ccache_dir,
                output_dir,
            ]:
                directory.mkdir(parents=True, exist_ok=True)

            (source_dir / "kernel.bin").write_bytes(b"a" * 100)
            (repo_dir / "manifest.xml").write_bytes(b"b" * 30)
            (metadata_dir / "workspace.json").write_bytes(b"c" * 7)
            (repo_reference_dir / "ref.pack").write_bytes(b"d" * 11)
            (bazel_dir / "cache.bin").write_bytes(b"e" * 13)
            (ccache_dir / "entry.bin").write_bytes(b"f" * 17)
            (output_dir / "Image").write_bytes(b"g" * 19)

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(system="kleaf", arch="aarch64", dist_dir="dist"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel", metadata_dir=".gki-builder"),
                config_path=Path("sample.toml"),
            )

            report = build.analyze_workspace_usage(target, workspace_root, cache_root, output_dir)
            sections = report["sections"]

            self.assertEqual(sections["source"]["bytes"], 100)
            self.assertEqual(sections["repo_metadata"]["bytes"], 30)
            self.assertEqual(sections["cache"]["bytes"], 41)
            self.assertEqual(sections["cache_repo_reference"]["bytes"], 11)
            self.assertEqual(sections["cache_bazel"]["bytes"], 13)
            self.assertEqual(sections["cache_ccache"]["bytes"], 17)
            self.assertEqual(sections["output"]["bytes"], 19)
            self.assertEqual(sections["workspace_metadata"]["bytes"], 7)


if __name__ == "__main__":
    unittest.main()
