#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

build = importlib.import_module("gki_builder.build")
targets = importlib.import_module("gki_builder.targets")


class BuildUsageTests(unittest.TestCase):
    def test_analyze_workspace_usage_splits_source_repo_cache_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"

            source_dir = workspace_root / "android-kernel"
            repo_dir = source_dir / ".repo"
            metadata_dir = workspace_root / ".akb" / "state" / "targets" / "sample"
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
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
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

    def test_warmup_kernel_uses_bazel_build_for_warmup_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"
            source_dir = workspace_root / "android-kernel"
            source_dir.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(
                    system="kleaf",
                    arch="aarch64",
                    target="//common:kernel_{arch}_dist",
                    warmup_target="//common:kernel_{arch}",
                ),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample.toml"),
            )

            with mock.patch.object(build, "_warmup_kleaf") as warmup_kleaf:
                with mock.patch.object(build, "_export_warmup_kleaf_outputs", return_value=[{"path": "out"}]):
                    output_dir = build.warmup_kernel(target, workspace_root, cache_root, output_root)

            warmup_kleaf.assert_called_once()
            self.assertEqual(output_dir, (output_root / target.build.dist_dir).resolve())
            metadata = json.loads(
                (workspace_root / ".akb" / "state" / "targets" / "sample" / "warmup-outputs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["warmup_target"], "//common:kernel_{arch}")

    def test_warmup_kernel_falls_back_to_full_build_without_warmup_target(self) -> None:
        target = targets.TargetConfig(
            name="sample",
            manifest=targets.ManifestConfig(source="remote"),
            build=targets.BuildConfig(system="kleaf", arch="aarch64"),
            cache=targets.CacheConfig(),
            workspace=targets.WorkspaceConfig(),
            config_path=Path("sample.toml"),
        )

        with mock.patch.object(build, "build_kernel") as build_kernel:
            build.warmup_kernel(target, Path("workspace"), Path("cache"), Path("out"))

        build_kernel.assert_called_once_with(target, Path("workspace"), Path("cache"), Path("out"))

    def test_export_warmup_kleaf_outputs_copies_bazel_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "source"
            output_dir = temp_root / "out"
            bazel_output = source_dir / "bazel-out" / "k8-fastbuild" / "bin" / "common" / "kernel_aarch64" / "vmlinux"
            bazel_output.parent.mkdir(parents=True, exist_ok=True)
            bazel_output.write_bytes(b"kernel")

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(system="kleaf", arch="aarch64", warmup_target="//common:kernel_{arch}"),
                cache=targets.CacheConfig(),
                workspace=targets.WorkspaceConfig(),
                config_path=Path("sample.toml"),
            )

            with mock.patch.object(build, "_query_warmup_kleaf_outputs", return_value=[
                "bazel-out/k8-fastbuild/bin/common/kernel_aarch64/vmlinux"
            ]):
                exported = build._export_warmup_kleaf_outputs(target, source_dir, output_dir, {})

            destination = output_dir / "common" / "kernel_aarch64" / "vmlinux"
            self.assertEqual(destination.read_bytes(), b"kernel")
            self.assertEqual(exported[0]["path"], str(destination.resolve()))


if __name__ == "__main__":
    unittest.main()
