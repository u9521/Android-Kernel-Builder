# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import layout


@dataclass(slots=True, frozen=True)
class AkbEnvironment:
    mode: str
    work_root: Path


def is_docker_runtime() -> bool:
    return Path("/.dockerenv").exists()


def has_embedded_docker_layout() -> bool:
    return layout.active_target_file(layout.DOCKER_WORK_ROOT).exists()


def discover_host_work_root(start_dir: Path | None = None) -> Path:
    current = (start_dir or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if layout.akb_config_file(candidate).exists():
            return candidate
    raise FileNotFoundError(
        f"AKB environment not found from {current}. Run the host install script in your work directory first."
    )


def discover_current_environment(start_dir: Path | None = None) -> AkbEnvironment:
    if is_docker_runtime() or has_embedded_docker_layout():
        return AkbEnvironment(mode="docker", work_root=layout.DOCKER_WORK_ROOT)
    return AkbEnvironment(mode="host", work_root=discover_host_work_root(start_dir))
