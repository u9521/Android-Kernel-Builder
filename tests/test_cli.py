#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

cli = importlib.import_module("gki_builder.cli")
config = importlib.import_module("gki_builder.config")
environment_module = importlib.import_module("gki_builder.environment")


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
