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
build_systems = importlib.import_module("gki_builder.build_systems")
targets = importlib.import_module("gki_builder.targets")
layout = importlib.import_module("gki_builder.layout")


class BuildUsageTests(unittest.TestCase):
    def test_build_system_executor_registry_matches_supported_build_systems(self) -> None:
        supported_systems = set(build_systems.supported_build_systems())
        registered_systems = set(build._BUILD_SYSTEM_EXECUTORS.keys())

        self.assertEqual(registered_systems, supported_systems)
        for system_name, executor in build._BUILD_SYSTEM_EXECUTORS.items():
            self.assertIn(system_name, supported_systems)
            self.assertTrue(callable(executor.build))
            self.assertTrue(callable(executor.warmup))

    def test_build_kernel_formats_legacy_config_with_arch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"
            source_dir = workspace_root / "android-kernel"
            source_dir.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(
                    system="legacy",
                    arch="aarch64",
                    dist_dir="dist",
                    legacy_config="common/build.config.gki.{arch}",
                ),
                cache=targets.CacheConfig(),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample-legacy.toml"),
            )

            def _capture_command(*args: object, **kwargs: object) -> object:
                command_obj = args[0]
                if not isinstance(command_obj, list):
                    raise TypeError("expected command list")
                if command_obj[0:2] == ["bash", "build/build.sh"]:
                    cc_arg = next(arg for arg in command_obj if arg.startswith("CC="))
                    self.assertTrue(cc_arg.startswith("CC="))
                    cc_path = Path(cc_arg.split("=", 1)[1])
                    self.assertTrue(cc_path.is_absolute())
                    self.assertTrue(cc_path.is_symlink())
                    self.assertEqual(cc_path.name, "clang")
                    self.assertEqual(cc_path.parent, layout.ccache_tools_root(cache_root).resolve())
                    self.assertEqual(cc_path.resolve(), Path("/usr/bin/ccache"))
                return mock.Mock(stdout="")

            with mock.patch.object(build, "run_command", side_effect=_capture_command) as run_command:
                with mock.patch.object(build, "analyze_workspace_usage", return_value={"target": "sample-legacy", "sections": {}}):
                    with mock.patch.object(build.shutil, "which", return_value="/usr/bin/ccache"):
                        build.build_kernel(target, workspace_root, cache_root, output_root)

            legacy_call = run_command.call_args_list[0]
            self.assertEqual(legacy_call.args[0][0:2], ["bash", "build/build.sh"])
            self.assertEqual(legacy_call.kwargs["env"]["BUILD_CONFIG"], "common/build.config.gki.aarch64")
            self.assertNotIn("USE_CCACHE", legacy_call.kwargs["env"])
            self.assertEqual(legacy_call.kwargs["env"]["CCACHE_DIR"], str((cache_root / "ccache").resolve()))
            self.assertNotIn("CC_WRAPPER", legacy_call.kwargs["env"])
            self.assertNotIn("CC", legacy_call.kwargs["env"])
            self.assertEqual(run_command.call_args_list[1].args[0], ["ccache", "-s"])

    def test_create_ccache_clang_symlink_reuses_stable_cache_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_root = Path(temp_dir) / ".cache"
            cache_root.mkdir(parents=True, exist_ok=True)

            with mock.patch.object(build.shutil, "which", return_value="/usr/bin/ccache"):
                first_link = build._create_ccache_clang_symlink(cache_root, {"PATH": "/usr/bin"})
                second_link = build._create_ccache_clang_symlink(cache_root, {"PATH": "/usr/bin"})

            self.assertEqual(first_link, second_link)
            self.assertEqual(first_link, layout.ccache_clang_link(cache_root).absolute())
            self.assertTrue(first_link.is_symlink())
            self.assertEqual(first_link.resolve(), Path("/usr/bin/ccache"))

    def test_build_kernel_legacy_skips_ccache_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"
            source_dir = workspace_root / "android-kernel"
            source_dir.mkdir(parents=True, exist_ok=True)

            target = targets.TargetConfig(
                name="sample-legacy",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(
                    system="legacy",
                    arch="aarch64",
                    dist_dir="dist",
                    legacy_config="common/build.config.gki.{arch}",
                    use_ccache=False,
                ),
                cache=targets.CacheConfig(),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample-legacy.toml"),
            )

            with mock.patch.object(build, "run_command", return_value=mock.Mock(stdout="")) as run_command:
                with mock.patch.object(build, "analyze_workspace_usage", return_value={"target": "sample-legacy", "sections": {}}):
                    build.build_kernel(target, workspace_root, cache_root, output_root)

            self.assertEqual(run_command.call_count, 1)
            legacy_call = run_command.call_args_list[0]
            self.assertEqual(legacy_call.args[0][0:2], ["bash", "build/build.sh"])
            self.assertNotIn("CCACHE_DIR", legacy_call.kwargs["env"])

    def test_analyze_workspace_usage_splits_source_repo_cache_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "work"
            cache_root = temp_root / ".cache"
            output_root = temp_root / "out"

            source_dir = workspace_root / "android-kernel"
            repo_dir = source_dir / ".repo"
            repo_reference_dir = cache_root / "repo"
            bazel_dir = cache_root / "bazel"
            bazel_state_dir = bazel_dir / "state"
            bazel_repo_dir = bazel_dir / "repo"
            bazel_diskcache_dir = bazel_dir / "diskcache"
            kleaf_dir = bazel_dir / "kleaf-out"
            ccache_dir = cache_root / "ccache"
            output_dir = output_root / "dist"

            for directory in [
                source_dir,
                repo_dir,
                repo_reference_dir,
                bazel_state_dir,
                bazel_repo_dir,
                bazel_diskcache_dir,
                kleaf_dir,
                ccache_dir,
                output_dir,
            ]:
                directory.mkdir(parents=True, exist_ok=True)

            (source_dir / "kernel.bin").write_bytes(b"a" * 100)
            (repo_dir / "manifest.xml").write_bytes(b"b" * 30)
            (repo_reference_dir / "ref.pack").write_bytes(b"d" * 11)
            (bazel_state_dir / "state.bin").write_bytes(b"e" * 13)
            (bazel_repo_dir / "repo.bin").write_bytes(b"h" * 23)
            (bazel_diskcache_dir / "disk.bin").write_bytes(b"i" * 29)
            (kleaf_dir / "out.bin").write_bytes(b"j" * 31)
            (ccache_dir / "entry.bin").write_bytes(b"f" * 17)
            (output_dir / "Image").write_bytes(b"g" * 19)

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(system="kleaf", arch="aarch64", dist_dir="dist"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", kleaf_dir="kleaf-out", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample.toml"),
            )

            report = build.analyze_workspace_usage(target, workspace_root, cache_root, output_dir)
            sections = report["sections"]

            self.assertEqual(sections["source"]["bytes"], 100)
            self.assertEqual(sections["repo_metadata"]["bytes"], 30)
            self.assertEqual(sections["cache"]["bytes"], 124)
            self.assertEqual(sections["cache_repo_reference"]["bytes"], 11)
            self.assertEqual(sections["cache_bazel"]["bytes"], 96)
            self.assertEqual(sections["cache_bazel_state"]["bytes"], 13)
            self.assertEqual(sections["cache_bazel_repo"]["bytes"], 23)
            self.assertEqual(sections["cache_bazel_diskcache"]["bytes"], 29)
            self.assertEqual(sections["cache_kleaf"]["bytes"], 31)
            self.assertEqual(sections["cache_ccache"]["bytes"], 17)
            self.assertEqual(sections["output"]["bytes"], 19)
            self.assertNotIn("workspace_metadata", sections)

    def test_build_kleaf_uses_split_bazel_cache_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "android-kernel"
            cache_root = temp_root / ".cache"
            output_dir = temp_root / "out"
            bazel_binary = source_dir / "tools" / "bazel"
            bazel_binary.parent.mkdir(parents=True, exist_ok=True)
            bazel_binary.write_text("#!/bin/sh\n", encoding="utf-8")

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(system="kleaf", arch="aarch64", target="//common:kernel_{arch}_dist"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", kleaf_dir="kleaf-out", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample.toml"),
            )

            with mock.patch.object(build, "run_command", return_value=mock.Mock(stdout="")) as run_command:
                build._build_kleaf(target, source_dir, cache_root, output_dir, {})

            command = run_command.call_args_list[0].args[0]
            self.assertIn(f"--output_base={(cache_root / 'bazel' / 'state').resolve()}", command)
            self.assertIn(f"--repository_cache={(cache_root / 'bazel' / 'repo').resolve()}", command)
            self.assertIn(f"--disk_cache={(cache_root / 'bazel' / 'diskcache').resolve()}", command)
            self.assertIn(f"--cache_dir={(cache_root / 'bazel' / 'kleaf-out').resolve()}", command)
            self.assertEqual(
                run_command.call_args_list[1].args[0],
                [
                    str(bazel_binary),
                    f"--output_base={(cache_root / 'bazel' / 'state').resolve()}",
                    "shutdown",
                ],
            )
            self.assertFalse(run_command.call_args_list[1].kwargs["check"])

    def test_query_warmup_kleaf_outputs_uses_split_bazel_cache_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "android-kernel"
            cache_root = temp_root / ".cache"
            bazel_binary = source_dir / "tools" / "bazel"
            bazel_binary.parent.mkdir(parents=True, exist_ok=True)
            bazel_binary.write_text("#!/bin/sh\n", encoding="utf-8")

            target = targets.TargetConfig(
                name="sample",
                manifest=targets.ManifestConfig(source="remote"),
                build=targets.BuildConfig(system="kleaf", arch="aarch64", warmup_target="//common:kernel_{arch}"),
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", kleaf_dir="kleaf-out", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(source_dir="android-kernel"),
                config_path=Path("sample.toml"),
            )

            with mock.patch.object(build, "run_command", return_value=mock.Mock(stdout="one\ntwo\n")) as run_command:
                outputs = build._query_warmup_kleaf_outputs(target, source_dir, cache_root, {})

            command = run_command.call_args_list[0].args[0]
            self.assertEqual(outputs, ["one", "two"])
            self.assertIn(f"--output_base={(cache_root / 'bazel' / 'state').resolve()}", command)
            self.assertIn(f"--repository_cache={(cache_root / 'bazel' / 'repo').resolve()}", command)
            self.assertIn(f"--disk_cache={(cache_root / 'bazel' / 'diskcache').resolve()}", command)
            self.assertIn(f"--cache_dir={(cache_root / 'bazel' / 'kleaf-out').resolve()}", command)
            self.assertEqual(
                run_command.call_args_list[1].args[0],
                [
                    str(bazel_binary),
                    f"--output_base={(cache_root / 'bazel' / 'state').resolve()}",
                    "shutdown",
                ],
            )
            self.assertFalse(run_command.call_args_list[1].kwargs["check"])

    def test_run_bazel_command_shuts_down_even_after_failure(self) -> None:
        bazel_binary = Path("/tmp/tools/bazel")
        bazel_output_base = Path("/tmp/.cache/bazel/state")
        command = [str(bazel_binary), f"--output_base={bazel_output_base}", "build", "//common:kernel_aarch64"]
        failure = RuntimeError("build failed")

        with mock.patch.object(build, "run_command", side_effect=[failure, mock.Mock(stdout="")]) as run_command:
            with self.assertRaisesRegex(RuntimeError, "build failed"):
                build._run_bazel_command(command, bazel_binary, bazel_output_base, cwd=Path("/tmp"), env={})

        self.assertEqual(run_command.call_args_list[1].args[0], [str(bazel_binary), f"--output_base={bazel_output_base}", "shutdown"])
        self.assertFalse(run_command.call_args_list[1].kwargs["check"])

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
                cache=targets.CacheConfig(repo_dir="repo", bazel_dir="bazel", kleaf_dir="kleaf-out", ccache_dir="ccache"),
                workspace=targets.WorkspaceConfig(
                    source_dir="android-kernel",
                    metadata_dir="docker_datas/targets",
                ),
                config_path=Path("sample.toml"),
            )

            with mock.patch.object(build, "_warmup_kleaf") as warmup_kleaf:
                with mock.patch.object(build, "_export_warmup_kleaf_outputs", return_value=[{"path": "out"}]):
                    output_dir = build.warmup_kernel(target, workspace_root, cache_root, output_root)

            warmup_kleaf.assert_called_once()
            self.assertEqual(output_dir, (output_root / target.build.dist_dir).resolve())
            metadata = json.loads(
                (workspace_root / "docker_datas" / "targets" / "sample" / "warmup-outputs.json").read_text(encoding="utf-8")
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

        with mock.patch.object(build, "_build_kleaf") as build_kleaf:
            with mock.patch.object(build, "analyze_workspace_usage", return_value={"target": "sample", "sections": {}}):
                build.warmup_kernel(target, Path("workspace"), Path("cache"), Path("out"))

        build_kleaf.assert_called_once()

    def test_warmup_kernel_routes_legacy_to_build_implementation(self) -> None:
        target = targets.TargetConfig(
            name="sample-legacy",
            manifest=targets.ManifestConfig(source="remote"),
            build=targets.BuildConfig(system="legacy", arch="aarch64", legacy_config="common/build.config.gki.{arch}"),
            cache=targets.CacheConfig(),
            workspace=targets.WorkspaceConfig(),
            config_path=Path("sample-legacy.toml"),
        )

        with mock.patch.object(build, "_build_legacy") as build_legacy:
            with mock.patch.object(build, "analyze_workspace_usage", return_value={"target": "sample-legacy", "sections": {}}):
                build.warmup_kernel(target, Path("workspace"), Path("cache"), Path("out"))

        build_legacy.assert_called_once()

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
                exported = build._export_warmup_kleaf_outputs(target, source_dir, temp_root / ".cache", output_dir, {})

            destination = output_dir / "common" / "kernel_aarch64" / "vmlinux"
            self.assertEqual(destination.read_bytes(), b"kernel")
            self.assertEqual(exported[0]["path"], str(destination.resolve()))


if __name__ == "__main__":
    unittest.main()
