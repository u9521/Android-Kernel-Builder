#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import argparse
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

cli = importlib.import_module("android_kernel_builder.builder.cli")
build_command = importlib.import_module("android_kernel_builder.builder.cli.commands.build")
cache_command = importlib.import_module("android_kernel_builder.builder.cli.commands.cache")
usage_command = importlib.import_module("android_kernel_builder.builder.cli.commands.usage")
sync_source_command = importlib.import_module("android_kernel_builder.builder.cli.commands.sync_source")
targets = importlib.import_module("android_kernel_builder.builder.core.config")
tools_command = importlib.import_module("android_kernel_builder.builder.cli.commands.tools")


def _target(name: str) -> object:
    return targets.TargetConfig(
        name=name,
        sync=targets.RepoConfig(),
        build=targets.KleafBuildConfig(),
        config_path=Path(f"{name}.toml"),
    )


def _parse_command(module: object, name: str, argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    module.build_parser(subparsers)
    return parser.parse_args([name, *argv])


class CliTests(unittest.TestCase):
    def test_akb_help_lists_commands(self) -> None:
        stdout = io.StringIO()

        with mock.patch("sys.stdout", stdout), self.assertRaises(SystemExit) as context:
            cli.main(["--help"])

        self.assertEqual(context.exception.code, 0)
        self.assertIn("show-target", stdout.getvalue())
        self.assertNotIn("build-docker", stdout.getvalue())

    def test_akb_accepts_core_subcommands(self) -> None:
        args = cli.build_app().parse_args(["build", "--target", "android15-6.6"])
        self.assertEqual(args.command, "build")

    def test_akb_rejects_removed_build_docker_command(self) -> None:
        with self.assertRaises(SystemExit):
            cli.build_app().parse_args(["build-docker"])

    def test_build_rejects_removed_output_root_option(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_command(build_command, "build", ["--target", "android15-6.6", "--output-root", "out"])

    def test_sync_source_uses_current_directory_target_paths(self) -> None:
        args = _parse_command(sync_source_command, "sync-source", ["--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(sync_source_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(sync_source_command.TargetConfigProvider, "load", return_value=target):
                    with mock.patch.object(sync_source_command, "sync_source") as sync_source:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(sync_source.call_args.args[1], work_root / "source-code/android15-6.6")
        self.assertEqual(sync_source.call_args.args[2], work_root / "cache/android15-6.6")

    def test_build_uses_current_directory_target_paths(self) -> None:
        args = _parse_command(build_command, "build", ["--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(build_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(build_command.TargetConfigProvider, "load", return_value=target):
                    with mock.patch.object(build_command, "build_kernel") as build_kernel:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(build_kernel.call_args.args[1], work_root / "source-code/android15-6.6")
        self.assertEqual(build_kernel.call_args.args[2], work_root / "cache/android15-6.6")
        self.assertEqual(build_kernel.call_args.args[3], work_root / "out/android15-6.6")

    def test_print_usage_report_uses_current_directory_target_paths(self) -> None:
        args = _parse_command(usage_command, "usage", [])
        target = _target("android15-6.6")
        report = {"target": "android15-6.6", "sections": {}}

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(usage_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(usage_command.TargetConfigProvider, "load", return_value=target):
                    with mock.patch.object(usage_command, "analyze_workspace_usage", return_value=report) as analyze_workspace_usage:
                        with mock.patch.object(usage_command, "print_usage_report") as print_usage_report:
                            result = args.handler(args)

        self.assertEqual(result, 0)
        analyze_workspace_usage.assert_called_once_with(
            target,
            work_root / "source-code/android15-6.6",
            work_root / "cache/android15-6.6",
            work_root / "out/android15-6.6",
        )
        print_usage_report.assert_called_once_with(report)

    def test_build_cache_init_resolves_target_and_work_root(self) -> None:
        args = _parse_command(cache_command, "cache", ["init", "--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(cache_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(cache_command.TargetConfigProvider, "load", return_value=target):
                    with mock.patch.object(cache_command, "init_build_cache") as init_build_cache:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        init_build_cache.assert_called_once_with(work_root, "android15-6.6")

    def test_build_cache_export_finalizes_target_cache(self) -> None:
        args = _parse_command(cache_command, "cache", ["export", "--target", "android15-6.6"])
        target = _target("android15-6.6")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_root = Path(temp_dir)
            with mock.patch.object(cache_command.Path, "cwd", return_value=work_root):
                with mock.patch.object(cache_command.TargetConfigProvider, "load", return_value=target):
                    with mock.patch.object(cache_command, "finalize_build_cache") as finalize_build_cache:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        finalize_build_cache.assert_called_once_with(work_root, "android15-6.6")

    def test_add_git_safe_adds_input_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = _parse_command(tools_command, "tools", ["add-git-safe", str(root)])
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
