# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path


def docker_build_command(
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
