# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import tempfile

from .. import layout
from ..docker_image import package_image_context
from ..global_config import load_global_config
from ..utils import ensure_directory, run_command
from .buildx import docker_build_command


def build_base_image(tag: str, repo_root: Path, dockerfile: Path, *, push: bool = False) -> None:
    run_command(
        docker_build_command(dockerfile, tag, push=push),
        cwd=repo_root,
    )


def build_workspace_image(
    tag: str,
    base_image: str,
    source_target_file: Path,
    repo_root: Path,
    dockerfile: Path,
    *,
    push: bool = False,
) -> None:
    temp_root = ensure_directory(layout.temp_root(repo_root))
    with tempfile.TemporaryDirectory(prefix="gki-image-package-", dir=temp_root) as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        run_command(
            docker_build_command(
                packaged_dockerfile,
                tag,
                push=push,
                allow_security_insecure=True,
                build_args=[
                    "--build-arg",
                    f"BASE_IMAGE={base_image}",
                    "--build-arg",
                    "SOURCE_TARGET_FILE=.docker-target/target.toml",
                ],
            ),
            cwd=package_root,
        )


def build_snapshot_image(
    tag: str,
    base_image: str,
    source_target_file: Path,
    repo_root: Path,
    dockerfile: Path,
    snapshot_git_projects: list[str] | None = None,
    *,
    push: bool = False,
) -> None:
    global_config = load_global_config(repo_root)
    projects = snapshot_git_projects or list(global_config.snapshot_git_projects)
    temp_root = ensure_directory(layout.temp_root(repo_root))
    with tempfile.TemporaryDirectory(prefix="gki-image-package-", dir=temp_root) as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        run_command(
            docker_build_command(
                packaged_dockerfile,
                tag,
                push=push,
                allow_security_insecure=True,
                build_args=[
                    "--build-arg",
                    f"BASE_IMAGE={base_image}",
                    "--build-arg",
                    "SOURCE_TARGET_FILE=.docker-target/target.toml",
                    "--build-arg",
                    f"SNAPSHOT_GIT_PROJECTS={','.join(projects)}",
                ],
            ),
            cwd=package_root,
        )
