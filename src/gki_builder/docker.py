# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import tempfile

from . import layout
from .global_config import load_global_config
from .image_package import package_image_context
from .utils import ensure_directory
from .utils import run_command


def _docker_build_command(
    dockerfile: Path,
    tag: str,
    *,
    push: bool,
    build_args: list[str] | None = None,
    build_contexts: dict[str, Path] | None = None,
    allow_security_insecure: bool = False,
) -> list[str]:
    command = ["docker", "buildx", "build", "--push" if push else "--load"]
    if allow_security_insecure:
        command.extend(["--allow", "security.insecure"])
    command.extend(["-f", str(dockerfile)])
    if build_args:
        command.extend(build_args)
    if build_contexts:
        for name, path in build_contexts.items():
            command.extend(["--build-context", f"{name}={path}"])
    command.extend(["-t", tag, "."])
    return command


def build_base_image(tag: str, repo_root: Path, dockerfile: Path, *, push: bool = False) -> None:
    run_command(
        _docker_build_command(dockerfile, tag, push=push),
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
            _docker_build_command(
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
            _docker_build_command(
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
