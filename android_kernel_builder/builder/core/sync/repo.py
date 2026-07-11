# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from ...utils import run_command
from ..config import TargetConfig
from .manifest import rewrite_manifest_revisions


def _repo_init(target: TargetConfig, source_dir: Path, repo_reference_dir: Path) -> None:
    command = ["repo", "init"]
    if target.sync.minimal:
        command.append("--depth=1")

    if target.sync.path is None:
        command.extend(["-u", target.sync.url or "", "-b", target.sync.branch or ""])
        if target.sync.file:
            command.extend(["-m", target.sync.file])
    else:
        command.extend(["-u", target.sync.url or "", "-m", str(target.sync.path or "")])
        if target.sync.branch:
            command.extend(["-b", target.sync.branch])

    if any(repo_reference_dir.iterdir()):
        command.extend(["--reference", str(repo_reference_dir)])

    run_command(command, cwd=source_dir)


def _repo_sync_command(target: TargetConfig, jobs: int) -> list[str]:
    command = ["repo", "--trace", "sync", f"-j{jobs}"]
    if target.sync.minimal:
        command.extend(["-c", "--no-clone-bundle", "--no-tags"])
    return command


def _auto_fix_remote_deprecated_branch(target: TargetConfig, source_dir: Path) -> str | None:
    if (target.sync.path is not None or not target.sync.branch or not target.sync.autodetect_deprecated):
        return None

    kernel_branch = _kernel_project_branch_name(target.sync.branch)
    if kernel_branch is None:
        return None

    result = run_command(
        [
            "git",
            "ls-remote",
            "https://android.googlesource.com/kernel/common",
            kernel_branch,
            f"deprecated/{kernel_branch}",
        ],
        cwd=source_dir,
        check=False,
        capture_output=True,
    )
    deprecated_branch = _detect_deprecated_branch(result.stdout or "", kernel_branch)
    if deprecated_branch is None:
        return None

    manifest_path = source_dir / ".repo/manifests" / (target.sync.file or "default.xml")
    if not manifest_path.exists():
        print(f"warning: manifest file not found for deprecated rewrite: {manifest_path}")
        return deprecated_branch

    rewrite_manifest_revisions(manifest_path, kernel_branch, deprecated_branch)
    return deprecated_branch


def _kernel_project_branch_name(manifest_branch: str) -> str | None:
    prefix = "common-"
    if not manifest_branch.startswith(prefix):
        return None
    return manifest_branch[len(prefix):]


def _detect_deprecated_branch(ls_remote_output: str, kernel_branch: str) -> str | None:
    deprecated_ref = f"refs/heads/deprecated/{kernel_branch}"
    if deprecated_ref in ls_remote_output:
        return f"deprecated/{kernel_branch}"
    return None
