# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .. import layout
from ..utils import ensure_directory, run_command


def run_container(
    image: str,
    work_root: Path,
    command: list[str],
) -> None:
    work_root = work_root.resolve()
    source_root = ensure_directory(work_root / layout.SOURCE_CODE_DIR_NAME)
    cache_root = ensure_directory(layout.cache_root(work_root))
    output_root = ensure_directory(layout.output_root(work_root))
    outerimage_root = ensure_directory(layout.docker_outerimage_root(work_root))
    docker_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{source_root}:{layout.DOCKER_WORK_ROOT / layout.SOURCE_CODE_DIR_NAME}",
        "-v",
        f"{cache_root}:{layout.cache_root(layout.DOCKER_WORK_ROOT)}",
        "-v",
        f"{output_root}:{layout.output_root(layout.DOCKER_WORK_ROOT)}",
        "-v",
        f"{outerimage_root}:{layout.docker_outerimage_root(layout.DOCKER_WORK_ROOT)}",
        image,
        *command,
    ]
    run_command(docker_command)
