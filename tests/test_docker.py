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
    def test_build_base_image_uses_buildx(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "base.Dockerfile"

        with mock.patch.object(docker, "run_command") as run_command:
            docker.build_base_image("example:base", repo_root, dockerfile)

        self.assertEqual(
            run_command.call_args.args[0][:4],
            ["docker", "buildx", "build", "--load"],
        )
        self.assertEqual(run_command.call_args.kwargs["cwd"], repo_root)

    def test_build_workspace_image_uses_packaged_context(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "workspace.Dockerfile"

        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "context"
            (package_root / "docker").mkdir(parents=True, exist_ok=True)
            (package_root / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            with mock.patch.object(docker, "package_image_context") as package_image_context:
                package_image_context.return_value = {}
                with mock.patch("gki_builder.docker.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker, "run_command") as run_command:
                        docker.build_workspace_image(
                            "example:workspace",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                        )

            package_image_context.assert_called_once_with(repo_root, package_root, source_target_file=repo_root / "configs" / "targets" / "sample.toml")
            command = run_command.call_args.args[0]
            self.assertEqual(command[:4], ["docker", "buildx", "build", "--load"])
            self.assertIn("--allow", command)
            self.assertIn("security.insecure", command)
            self.assertIn(str(package_root / "docker" / "workspace.Dockerfile"), command)
            self.assertIn("SOURCE_TARGET_FILE=.docker-target/target.toml", command)
            self.assertNotIn("GKI_WORKSPACE_ROOT=/workspace", command)
            self.assertEqual(run_command.call_args.kwargs["cwd"], package_root)

    def test_build_workspace_image_uses_buildx_when_push_requested(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "workspace.Dockerfile"

        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "context"
            (package_root / "docker").mkdir(parents=True, exist_ok=True)
            (package_root / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            with mock.patch.object(docker, "package_image_context"):
                with mock.patch("gki_builder.docker.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker, "run_command") as run_command:
                        docker.build_workspace_image(
                            "example:workspace",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                            push=True,
                        )

        self.assertEqual(
            run_command.call_args.args[0][:4],
            ["docker", "buildx", "build", "--push"],
        )

    def test_build_snapshot_image_passes_snapshot_projects(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "snapshot.Dockerfile"

        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "context"
            (package_root / "docker").mkdir(parents=True, exist_ok=True)
            (package_root / "docker" / "snapshot.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            with mock.patch.object(docker, "package_image_context") as package_image_context:
                package_image_context.return_value = {}
                with mock.patch("gki_builder.docker.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker, "run_command") as run_command:
                        docker.build_snapshot_image(
                            "example:snapshot",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                            ["common", "build/kernel"],
                        )

            package_image_context.assert_called_once_with(repo_root, package_root, source_target_file=repo_root / "configs" / "targets" / "sample.toml")
            command = run_command.call_args.args[0]
            self.assertEqual(command[:4], ["docker", "buildx", "build", "--load"])
            self.assertIn("--allow", command)
            self.assertIn("security.insecure", command)
            self.assertIn("SNAPSHOT_GIT_PROJECTS=common,build/kernel", command)
            self.assertIn("example:snapshot", command)
            self.assertIn(str(package_root / "docker" / "snapshot.Dockerfile"), command)
            self.assertIn("SOURCE_TARGET_FILE=.docker-target/target.toml", command)
            self.assertEqual(run_command.call_args.kwargs["cwd"], package_root)

    def test_build_snapshot_image_uses_buildx_when_push_requested(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "snapshot.Dockerfile"

        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "context"
            (package_root / "docker").mkdir(parents=True, exist_ok=True)
            (package_root / "docker" / "snapshot.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            with mock.patch.object(docker, "package_image_context"):
                with mock.patch("gki_builder.docker.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker, "run_command") as run_command:
                        docker.build_snapshot_image(
                            "example:snapshot",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                            ["common"],
                            push=True,
                        )

        self.assertEqual(
            run_command.call_args.args[0][:4],
            ["docker", "buildx", "build", "--push"],
        )

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
