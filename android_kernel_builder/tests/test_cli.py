#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

cli = importlib.import_module("android_kernel_builder.builder.cli")
build_command = importlib.import_module("android_kernel_builder.builder.commands.build")
cache_command = importlib.import_module("android_kernel_builder.builder.commands.cache")
docker_command = importlib.import_module("android_kernel_builder.builder.commands.docker")
sync_source_command = importlib.import_module("android_kernel_builder.builder.commands.sync_source")
targets = importlib.import_module("android_kernel_builder.builder.targets")
tools_command = importlib.import_module("android_kernel_builder.builder.commands.tools")


def _target(name: str) -> object:
    return targets.TargetConfig(
        name=name,
        manifest=targets.ManifestConfig(source="remote"),
        build=targets.BuildConfig(),
        config_path=Path(f"{name}.toml"),
    )


class CliTests(unittest.TestCase):
    def test_akb_prints_command_index(self) -> None:
        stdout = io.StringIO()

        with mock.patch("sys.stdout", stdout):
            result = cli.main([])

        self.assertEqual(result, 0)
        self.assertIn("show-target", stdout.getvalue())
        self.assertIn("docker", stdout.getvalue())

    def test_akb_rejects_removed_business_subcommands(self) -> None:
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["build"])

    def test_build_rejects_removed_output_root_option(self) -> None:
        with self.assertRaises(SystemExit):
            build_command.build_parser().parse_args(["--target", "android15-6.6", "--output-root", "out"])

    def test_sync_source_uses_current_directory_target_paths(self) -> None:
        args = sync_source_command.build_parser().parse_args(["--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(sync_source_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(sync_source_command, "resolve_target", return_value=target):
                    with mock.patch.object(sync_source_command, "sync_source") as sync_source:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(sync_source.call_args.args[1], work_root / "source-code/android15-6.6")
        self.assertEqual(sync_source.call_args.args[2], work_root / "cache/android15-6.6")

    def test_build_uses_current_directory_target_paths(self) -> None:
        args = build_command.build_parser().parse_args(["--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(build_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(build_command, "resolve_target", return_value=target):
                    with mock.patch.object(build_command, "build_kernel") as build_kernel:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(build_kernel.call_args.args[1], work_root / "source-code/android15-6.6")
        self.assertEqual(build_kernel.call_args.args[2], work_root / "cache/android15-6.6")
        self.assertEqual(build_kernel.call_args.args[3], work_root / "out/android15-6.6")

    def test_docker_build_workspace_passes_fixed_dockerfile_and_push(self) -> None:
        args = docker_command.build_parser().parse_args([
            "build-workspace",
            "--tag",
            "example:workspace",
            "--base-image",
            "example:base",
            "--target",
            "android15-6.6",
            "--push",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with mock.patch.object(docker_command.Path, "cwd", return_value=repo_root):
                with mock.patch.object(
                    docker_command,
                    "target_config_path",
                    return_value=repo_root / "android_kernel_builder/configs/targets/android15-6.6.toml",
                ):
                    with mock.patch.object(docker_command, "build_workspace_image") as build_workspace_image:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertTrue(build_workspace_image.call_args.kwargs["push"])
        self.assertEqual(build_workspace_image.call_args.args[4].name, "workspace.Dockerfile")

    def test_build_cache_init_resolves_target_and_work_root(self) -> None:
        args = cache_command.build_parser().parse_args(["init", "--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(cache_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(cache_command, "resolve_target", return_value=target):
                    with mock.patch.object(cache_command, "init_build_cache") as init_build_cache:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        init_build_cache.assert_called_once_with(work_root, "android15-6.6")

    def test_build_cache_export_finalizes_target_cache(self) -> None:
        args = cache_command.build_parser().parse_args(["export", "--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(cache_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(cache_command, "resolve_target", return_value=target):
                    with mock.patch.object(cache_command, "finalize_build_cache") as finalize_build_cache:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        finalize_build_cache.assert_called_once_with(work_root, "android15-6.6")

    def test_docker_run_passes_current_work_root(self) -> None:
        args = docker_command.build_parser().parse_args(["run", "--image", "example:image"])

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(docker_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(docker_command, "run_container") as run_container:
                    result = args.handler(args)

        self.assertEqual(result, 0)
        run_container.assert_called_once_with("example:image", work_root, ["bash"])

    def test_add_git_safe_adds_input_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = tools_command.build_parser().parse_args(["add-git-safe", str(root)])
            completed_empty = subprocess.CompletedProcess([], 0, stdout="")
            completed_ok = subprocess.CompletedProcess([], 0, stdout="")

            with mock.patch.object(
                tools_command,
                "run_command",
                side_effect=[completed_empty, completed_empty, completed_ok, completed_ok],
            ) as run_command:
                with mock.patch("builtins.print"):
                    result = args.handler(args)

        self.assertEqual(result, 0)
        add_calls = [call.args[0] for call in run_command.call_args_list if len(call.args[0]) > 4 and call.args[0][3] == "--add"]
        self.assertCountEqual(
            add_calls,
            [
                ["git", "config", "--global", "--add", "safe.directory", str(root.resolve())],
                ["git", "config", "--system", "--add", "safe.directory", str(root.resolve())],
            ],
        )


if __name__ == "__main__":
    unittest.main()
