# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import tempfile

from . import layout
from .global_config import load_global_config
from .image_package import package_image_context
from .utils import run_command


def build_base_image(tag: str, repo_root: Path, dockerfile: Path) -> None:
    run_command(
        [
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "-t",
            tag,
            ".",
        ],
        cwd=repo_root,
    )


def build_workspace_image(
    tag: str,
    base_image: str,
    source_target_file: Path,
    repo_root: Path,
    dockerfile: Path,
) -> None:
    with tempfile.TemporaryDirectory(prefix="gki-image-package-") as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        run_command(
            [
                "docker",
                "build",
                "-f",
                str(packaged_dockerfile),
                "--build-arg",
                f"BASE_IMAGE={base_image}",
                "--build-arg",
                "SOURCE_TARGET_FILE=.docker-target/target.toml",
                "-t",
                tag,
                ".",
            ],
            cwd=package_root,
        )


def build_snapshot_image(
    tag: str,
    base_image: str,
    source_target_file: Path,
    repo_root: Path,
    dockerfile: Path,
    snapshot_git_projects: list[str] | None = None,
) -> None:
    global_config = load_global_config(repo_root)
    projects = snapshot_git_projects or list(global_config.snapshot_git_projects)
    with tempfile.TemporaryDirectory(prefix="gki-image-package-") as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        run_command(
            [
                "docker",
                "build",
                "-f",
                str(packaged_dockerfile),
                "--build-arg",
                f"BASE_IMAGE={base_image}",
                "--build-arg",
                "SOURCE_TARGET_FILE=.docker-target/target.toml",
                "--build-arg",
                f"SNAPSHOT_GIT_PROJECTS={','.join(projects)}",
                "-t",
                tag,
                ".",
            ],
                cwd=package_root,
            )


def run_container(
    image: str,
    workspace_root: Path,
    cache_root: Path,
    output_root: Path,
    command: list[str],
) -> None:
    docker_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{workspace_root.resolve()}:{layout.DOCKER_WORK_ROOT}",
        "-v",
        f"{cache_root.resolve()}:{layout.cache_root(layout.DOCKER_WORK_ROOT)}",
        "-v",
        f"{output_root.resolve()}:{layout.output_root(layout.DOCKER_WORK_ROOT)}",
        image,
        *command,
    ]
    run_command(docker_command)
