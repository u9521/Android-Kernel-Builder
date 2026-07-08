# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import shutil

from ..utils import ensure_directory, run_command


def clone_standalone_repo(project_path: Path, destination: Path) -> Path:
    ensure_directory(destination.parent)
    run_command(["git", "clone", "--no-hardlinks", str(project_path), str(destination)], capture_output=True)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=project_path, capture_output=True).stdout.strip()
    run_command(["git", "checkout", "--detach", head], cwd=destination, capture_output=True)
    return destination


def remove_repo_metadata(source_dir: Path, preserved_projects: list[str]) -> None:
    preserved_paths = {(source_dir / project).resolve() for project in preserved_projects}
    repo_dir = source_dir / ".repo"
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    for git_entry in source_dir.rglob(".git"):
        parent = git_entry.parent.resolve()
        if parent in preserved_paths:
            continue
        if git_entry.is_dir():
            shutil.rmtree(git_entry)
        else:
            git_entry.unlink()
