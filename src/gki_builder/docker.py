# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import tempfile

from . import layout
from .global_config import load_global_config
from .image_package import package_image_context
from .utils import run_command


def _docker_build_command(
    dockerfile: Path,
    tag: str,
    *,
    push: bool,
    build_args: list[str] | None = None,
    build_contexts: dict[str, Path] | None = None,
) -> list[str]:
    use_buildx = push or bool(build_contexts)
    command = ["docker"]
    if use_buildx:
        command.extend(["buildx", "build"])
        command.append("--push" if push else "--load")
    else:
        command.append("build")
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
    runtime_cache_root: Path | None = None,
) -> None:
    with tempfile.TemporaryDirectory(prefix="gki-image-package-") as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        cache_context_root = _resolve_runtime_cache_context(runtime_cache_root, temp_dir)
        run_command(
            _docker_build_command(
                packaged_dockerfile,
                tag,
                push=push,
                build_args=[
                    "--build-arg",
                    f"BASE_IMAGE={base_image}",
                    "--build-arg",
                    "SOURCE_TARGET_FILE=.docker-target/target.toml",
                ],
                build_contexts={"cache-host": cache_context_root},
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
    runtime_cache_root: Path | None = None,
) -> None:
    global_config = load_global_config(repo_root)
    projects = snapshot_git_projects or list(global_config.snapshot_git_projects)
    with tempfile.TemporaryDirectory(prefix="gki-image-package-") as temp_dir:
        package_root = Path(temp_dir) / "context"
        package_image_context(repo_root, package_root, source_target_file=source_target_file)
        packaged_dockerfile = package_root / dockerfile.relative_to(repo_root)
        cache_context_root = _resolve_runtime_cache_context(runtime_cache_root, temp_dir)
        run_command(
            _docker_build_command(
                packaged_dockerfile,
                tag,
                push=push,
                build_args=[
                    "--build-arg",
                    f"BASE_IMAGE={base_image}",
                    "--build-arg",
                    "SOURCE_TARGET_FILE=.docker-target/target.toml",
                    "--build-arg",
                    f"SNAPSHOT_GIT_PROJECTS={','.join(projects)}",
                ],
                build_contexts={"cache-host": cache_context_root},
            ),
            cwd=package_root,
        )


def _resolve_runtime_cache_context(runtime_cache_root: Path | None, temp_dir: str) -> Path:
    if runtime_cache_root is None:
        empty_root = Path(temp_dir) / "empty-cache-host"
        empty_root.mkdir(parents=True, exist_ok=True)
        return empty_root

    source_root = runtime_cache_root.resolve()
    if not source_root.exists():
        empty_root = Path(temp_dir) / "empty-cache-host"
        empty_root.mkdir(parents=True, exist_ok=True)
        return empty_root
    if not source_root.is_dir():
        raise ValueError(f"Runtime cache root must be a directory: {source_root}")
    return source_root


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
