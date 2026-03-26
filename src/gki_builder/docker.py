# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

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
    target_config: Path,
    repo_root: Path,
    dockerfile: Path,
) -> None:
    run_command(
        [
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "--build-arg",
            f"BASE_IMAGE={base_image}",
            "--build-arg",
            f"TARGET_CONFIG={target_config.as_posix()}",
            "-t",
            tag,
            ".",
        ],
        cwd=repo_root,
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
        f"{workspace_root.resolve()}:/workspace",
        "-v",
        f"{cache_root.resolve()}:/cache",
        "-v",
        f"{output_root.resolve()}:/out",
        image,
        *command,
    ]
    run_command(docker_command)
