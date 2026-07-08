#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

docker = importlib.import_module("android_kernel_builder.builder.build_docker")
docker_images = importlib.import_module("android_kernel_builder.builder.build_docker.images")
docker_runtime = importlib.import_module("android_kernel_builder.builder.build_docker.runtime")
layout = importlib.import_module("android_kernel_builder.builder.layout")


COMMON_CLEANUP_COMMAND = 'find "/workspace/source-code/${AKB_TARGET}/common" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +'


class DockerTests(unittest.TestCase):
    def test_build_base_image_uses_buildx(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "base.Dockerfile"

        with mock.patch.object(docker_images, "run_command") as run_command:
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

            with mock.patch.object(docker_images, "package_image_context") as package_image_context:
                package_image_context.return_value = {}
                with mock.patch("android_kernel_builder.builder.build_docker.images.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker_images, "run_command") as run_command:
                        docker.build_workspace_image(
                            "example:workspace",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                        )

            temporary_directory.assert_called_once_with(
                prefix="gki-image-package-",
                dir=layout.temp_root(repo_root),
            )
            package_image_context.assert_called_once_with(repo_root, package_root, source_target_file=repo_root / "configs" / "targets" / "sample.toml")
            command = run_command.call_args.args[0]
            self.assertEqual(command[:4], ["docker", "buildx", "build", "--load"])
            self.assertIn("--allow", command)
            self.assertIn("security.insecure", command)
            self.assertIn(str(package_root / "docker" / "workspace.Dockerfile"), command)
            self.assertIn("SOURCE_TARGET_FILE=.docker-target/target.toml", command)
            self.assertNotIn("GKI_", command)
            self.assertEqual(run_command.call_args.kwargs["cwd"], package_root)

    def test_build_workspace_image_uses_buildx_when_push_requested(self) -> None:
        repo_root = Path("/tmp/repo")
        dockerfile = repo_root / "docker" / "workspace.Dockerfile"

        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "context"
            (package_root / "docker").mkdir(parents=True, exist_ok=True)
            (package_root / "docker" / "workspace.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

            with mock.patch.object(docker_images, "package_image_context"):
                with mock.patch("android_kernel_builder.builder.build_docker.images.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker_images, "run_command") as run_command:
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

            with mock.patch.object(docker_images, "package_image_context") as package_image_context:
                package_image_context.return_value = {}
                with mock.patch("android_kernel_builder.builder.build_docker.images.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker_images, "run_command") as run_command:
                        docker.build_snapshot_image(
                            "example:snapshot",
                            "example:base",
                            repo_root / "configs" / "targets" / "sample.toml",
                            repo_root,
                            dockerfile,
                            ["common", "build/kernel"],
                        )

            temporary_directory.assert_called_once_with(
                prefix="gki-image-package-",
                dir=layout.temp_root(repo_root),
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

            with mock.patch.object(docker_images, "package_image_context"):
                with mock.patch("android_kernel_builder.builder.build_docker.images.tempfile.TemporaryDirectory") as temporary_directory:
                    temporary_directory.return_value.__enter__.return_value = temp_dir
                    temporary_directory.return_value.__exit__.return_value = False
                    with mock.patch.object(docker_images, "run_command") as run_command:
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

    def test_workspace_and_snapshot_images_cleanup_common_before_final_usage_report(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        dockerfiles = [
            repo_root / "docker" / "workspace.Dockerfile",
            repo_root / "docker" / "snapshot.Dockerfile",
        ]

        for dockerfile in dockerfiles:
            content = dockerfile.read_text(encoding="utf-8")
            self.assertIn(COMMON_CLEANUP_COMMAND, content)
            self.assertLess(content.index(COMMON_CLEANUP_COMMAND), content.index("uv run print-usage-report"))
            self.assertLess(content.index("mkdir -pv /workspace/docker_datas/outerimage"), content.index("uv run print-usage-report"))

    def test_run_container_mounts_cache_and_output_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.object(docker_runtime, "run_command") as run_command:
                docker.run_container("example:image", root, ["bash"])

            run_command.assert_called_once()
            command = run_command.call_args.args[0]
            self.assertIn(f"{root / 'source-code'}:/workspace/source-code", command)
            self.assertIn(f"{root / 'cache'}:/workspace/cache", command)
            self.assertIn(f"{root / 'out'}:/workspace/out", command)
            self.assertIn(f"{root / 'docker_datas' / 'outerimage'}:/workspace/docker_datas/outerimage", command)


if __name__ == "__main__":
    unittest.main()
