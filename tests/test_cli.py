#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

cli = importlib.import_module("gki_builder.cli")
config = importlib.import_module("gki_builder.config")
environment_module = importlib.import_module("gki_builder.environment")


class CliTests(unittest.TestCase):
    def test_docker_build_workspace_passes_push_flag(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "docker-build-workspace",
                "--tag",
                "example:workspace",
                "--base-image",
                "example:base",
                "--target",
                "android15-6.6",
                "--push",
            ]
        )
        env = environment_module.AkbEnvironment(mode="host", work_root=Path("/tmp/workspace"))

        with mock.patch.object(cli, "discover_current_environment", return_value=env):
            with mock.patch.object(cli, "host_target_config_path", return_value=Path("/tmp/workspace/.akb/targets/configs/android15-6.6.toml")):
                with mock.patch.object(cli, "build_workspace_image") as build_workspace_image:
                    result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertTrue(build_workspace_image.call_args.kwargs["push"])

    def test_docker_build_snapshot_passes_push_flag(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "docker-build-snapshot",
                "--tag",
                "example:snapshot",
                "--base-image",
                "example:base",
                "--target",
                "android15-6.6",
                "--push",
            ]
        )
        env = environment_module.AkbEnvironment(mode="host", work_root=Path("/tmp/workspace"))

        with mock.patch.object(cli, "discover_current_environment", return_value=env):
            with mock.patch.object(cli, "host_target_config_path", return_value=Path("/tmp/workspace/.akb/targets/configs/android15-6.6.toml")):
                with mock.patch.object(cli, "parse_snapshot_git_projects", return_value=["common"]):
                    with mock.patch.object(cli, "build_snapshot_image") as build_snapshot_image:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertTrue(build_snapshot_image.call_args.kwargs["push"])

    def test_sync_source_uses_host_default_target_and_config_cache_root(self) -> None:
        args = cli.build_parser().parse_args(["sync-source"])
        env = environment_module.AkbEnvironment(mode="host", work_root=Path("/tmp/workspace"))
        akb_config = config.AkbConfig(
            version=1,
            default_target="android15-6.6",
            workspace=config.WorkspaceDefaults(cache_dir=".cache-data", output_dir="out-data"),
            build=config.BuildDefaults(),
            config_path=Path("/tmp/workspace/.akb/config.toml"),
        )

        with mock.patch.object(cli, "discover_current_environment", return_value=env):
            with mock.patch.object(cli, "load_akb_config", return_value=akb_config):
                with mock.patch.object(cli, "resolve_target", return_value=object()) as resolve_target:
                    with mock.patch.object(cli, "sync_source") as sync_source:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(resolve_target.call_args.args[1], None)
        self.assertEqual(sync_source.call_args.args[1], Path("/tmp/workspace"))
        self.assertEqual(sync_source.call_args.args[2], Path("/tmp/workspace/.cache-data"))

    def test_build_uses_host_config_output_root_when_omitted(self) -> None:
        args = cli.build_parser().parse_args(["build", "--target", "android15-6.6"])
        env = environment_module.AkbEnvironment(mode="host", work_root=Path("/tmp/workspace"))
        akb_config = config.AkbConfig(
            version=1,
            default_target=None,
            workspace=config.WorkspaceDefaults(cache_dir=".cache-data", output_dir="out-data"),
            build=config.BuildDefaults(),
            config_path=Path("/tmp/workspace/.akb/config.toml"),
        )

        with mock.patch.object(cli, "discover_current_environment", return_value=env):
            with mock.patch.object(cli, "load_akb_config", return_value=akb_config):
                with mock.patch.object(cli, "resolve_target", return_value=object()):
                    with mock.patch.object(cli, "build_kernel") as build_kernel:
                        result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(build_kernel.call_args.args[2], Path("/tmp/workspace/.cache-data"))
        self.assertEqual(build_kernel.call_args.args[3], Path("/tmp/workspace/out-data"))

    def test_docker_run_uses_workspace_cache_root_when_omitted(self) -> None:
        args = cli.build_parser().parse_args(
            [
                "docker-run",
                "--image",
                "example:image",
                "--workspace",
                "/tmp/workspace",
                "--output-root",
                "/tmp/out",
            ]
        )

        with mock.patch.object(cli, "run_container") as run_container:
            result = args.handler(args)

        self.assertEqual(result, 0)
        self.assertEqual(run_container.call_args.args[2], Path("/tmp/workspace/.cache"))

    def test_runtime_cache_init_calls_runtime_cache_helper(self) -> None:
        args = cli.build_parser().parse_args(["runtime-cache-init"])

        with mock.patch.object(cli, "init_runtime_cache") as init_runtime_cache:
            result = args.handler(args)

        self.assertEqual(result, 0)
        init_runtime_cache.assert_called_once_with(Path("/workspace"))

    def test_runtime_cache_export_calls_runtime_cache_helper(self) -> None:
        args = cli.build_parser().parse_args(["runtime-cache-export"])

        with mock.patch.object(cli, "finalize_runtime_cache") as finalize_runtime_cache:
            result = args.handler(args)

        self.assertEqual(result, 0)
        finalize_runtime_cache.assert_called_once_with(Path("/workspace"))

    def test_add_git_safe_adds_input_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = cli.build_parser().parse_args(["add-git-safe", str(root)])

            completed_empty = subprocess.CompletedProcess(
                ["git", "config", "--global", "--get-all", "safe.directory"],
                0,
                stdout="",
            )
            completed_empty_system = subprocess.CompletedProcess(
                ["git", "config", "--system", "--get-all", "safe.directory"],
                0,
                stdout="",
            )
            completed_ok_global = subprocess.CompletedProcess(
                ["git", "config", "--global", "--add", "safe.directory", str(root)],
                0,
                stdout="",
            )
            completed_ok_system = subprocess.CompletedProcess(
                ["git", "config", "--system", "--add", "safe.directory", str(root)],
                0,
                stdout="",
            )

            with mock.patch.object(
                cli,
                "run_command",
                side_effect=[completed_empty, completed_empty_system, completed_ok_global, completed_ok_system],
            ) as run_command:
                with mock.patch("builtins.print"):
                    result = args.handler(args)

        self.assertEqual(result, 0)
        add_calls = [
            call.args[0]
            for call in run_command.call_args_list
            if call.args[0][3] == "--add" and call.args[0][4] == "safe.directory"
        ]
        self.assertCountEqual(
            add_calls,
            [
                ["git", "config", "--global", "--add", "safe.directory", str(root.resolve())],
                ["git", "config", "--system", "--add", "safe.directory", str(root.resolve())],
            ],
        )

    def test_add_git_safe_recursive_adds_only_child_git_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_a = root / "repo-a"
            repo_b = root / "nested" / "repo-b"
            repo_a.mkdir(parents=True)
            repo_b.mkdir(parents=True)
            (repo_a / ".git").mkdir()
            (repo_b / ".git").write_text("gitdir: ../.git/modules/repo-b\n", encoding="utf-8")

            args = cli.build_parser().parse_args(["add-git-safe", str(root), "-r"])
            existing_stdout = f"{root.resolve()}\n"
            completed_existing = subprocess.CompletedProcess(
                ["git", "config", "--global", "--get-all", "safe.directory"],
                0,
                stdout=existing_stdout,
            )
            completed_existing_system = subprocess.CompletedProcess(
                ["git", "config", "--system", "--get-all", "safe.directory"],
                0,
                stdout=existing_stdout,
            )
            completed_ok = subprocess.CompletedProcess(
                ["git", "config", "--global", "--add", "safe.directory", ""],
                0,
                stdout="",
            )

            with mock.patch.object(
                cli,
                "run_command",
                side_effect=[
                    completed_existing,
                    completed_existing_system,
                    completed_ok,
                    completed_ok,
                ],
            ) as run_command:
                with mock.patch("builtins.print"):
                    result = args.handler(args)

        self.assertEqual(result, 0)
        add_calls = [
            call.args[0]
            for call in run_command.call_args_list
            if call.args[0][4] == "safe.directory" and call.args[0][3] == "--add"
        ]
        self.assertCountEqual(
            add_calls,
            [
                ["git", "config", "--global", "--add", "safe.directory", str(repo_a.resolve())],
                ["git", "config", "--system", "--add", "safe.directory", str(repo_a.resolve())],
            ],
        )


if __name__ == "__main__":
    unittest.main()
