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

docker = importlib.import_module("gki_builder.docker")


class DockerTests(unittest.TestCase):
    def test_build_snapshot_image_passes_snapshot_projects(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "snapshot.Dockerfile"

        with mock.patch.object(docker, "run_command") as run_command:
            docker.build_snapshot_image(
                "example:snapshot",
                "example:base",
                Path("configs/targets/sample.toml"),
                repo_root,
                dockerfile,
                ["common", "build/kernel"],
            )

        command = run_command.call_args.args[0]
        self.assertIn("SNAPSHOT_GIT_PROJECTS=common,build/kernel", command)
        self.assertIn("example:snapshot", command)

    def test_run_container_mounts_cache_and_output_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "workspace"
            cache = root / "cache"
            output = root / "out"
            for path in [workspace, cache, output]:
                path.mkdir(parents=True, exist_ok=True)

            with mock.patch.object(docker, "run_command") as run_command:
                docker.run_container("example:image", workspace, cache, output, ["bash"])

            run_command.assert_called_once()
            command = run_command.call_args.args[0]
            self.assertIn(f"{workspace.resolve()}:/workspace", command)
            self.assertIn(f"{cache.resolve()}:/workspace/.cache", command)
            self.assertIn(f"{output.resolve()}:/workspace/out", command)


if __name__ == "__main__":
    unittest.main()
