#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from .active_target import load_active_target
from . import layout
from .environment import discover_current_environment
from .global_config import load_global_config
from .utils import discover_project_root, ensure_directory, run_command, write_json

DEFAULT_SNAPSHOT_GIT_PROJECTS = ("common",)


def parse_snapshot_git_projects(value: str | None) -> list[str]:
    if not value:
        return list(DEFAULT_SNAPSHOT_GIT_PROJECTS)
    return [item.strip() for item in value.split(",") if item.strip()]


def create_workspace_snapshot(
    workspace_root: Path,
    source_dir: Path,
    metadata_dir: Path,
    preserve_git_projects: list[str],
) -> dict[str, object]:
    workspace_root = workspace_root.resolve()
    source_dir = source_dir.resolve()
    metadata_dir = ensure_directory(metadata_dir.resolve())
    projects = preserve_git_projects or list(DEFAULT_SNAPSHOT_GIT_PROJECTS)

    with tempfile.TemporaryDirectory(prefix="gki-snapshot-") as temp_dir:
        temp_root = Path(temp_dir)
        clones: dict[str, Path] = {}
        for project in projects:
            project_path = source_dir / project
            if not project_path.is_dir():
                raise FileNotFoundError(f"Snapshot git project not found: {project_path}")
            clones[project] = _clone_standalone_repo(project_path, temp_root / project)

        _remove_repo_metadata(source_dir, projects)

        for project, clone_path in clones.items():
            project_path = source_dir / project
            if project_path.exists():
                shutil.rmtree(project_path)
            ensure_directory(project_path.parent)
            shutil.copytree(clone_path, project_path)

    snapshot = {
        "workspace_root": str(workspace_root),
        "source_dir": str(source_dir),
        "preserved_git_projects": projects,
        "repo_metadata_removed": True,
    }
    write_json(metadata_dir / "snapshot.json", snapshot)
    return snapshot


def create_workspace_snapshot_for_current_environment(
    *,
    workspace_root: str | Path | None = None,
    preserve_git_projects: list[str] | None = None,
    start_dir: Path | None = None,
) -> dict[str, object]:
    environment = discover_current_environment(start_dir)
    if environment.mode != "docker":
        raise ValueError("Snapshot runtime flow is only supported inside Docker images")

    resolved_workspace_root = Path(workspace_root).resolve() if workspace_root is not None else environment.work_root
    return create_workspace_snapshot_from_workspace_root(
        resolved_workspace_root,
        preserve_git_projects=preserve_git_projects,
        project_root=_discover_project_root(start_dir),
    )


def create_workspace_snapshot_from_workspace_root(
    workspace_root: Path,
    *,
    preserve_git_projects: list[str] | None = None,
    project_root: Path | None = None,
) -> dict[str, object]:
    workspace_root = workspace_root.resolve()
    target = load_active_target(workspace_root)
    global_config = load_global_config(project_root or _discover_project_root(workspace_root))
    return create_workspace_snapshot(
        workspace_root,
        workspace_root / target.workspace.source_dir,
        layout.docker_target_metadata_root(workspace_root, target.name),
        preserve_git_projects or list(global_config.snapshot_git_projects),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Docker snapshot from a prepared workspace")
    parser.add_argument(
        "--workspace-root",
        default=str(layout.DOCKER_WORK_ROOT),
        help="Workspace root path; defaults to /workspace",
    )
    parser.add_argument(
        "--snapshot-git-projects",
        default=None,
        help="Comma-separated repo projects to preserve; defaults to configs/global.toml [snapshot].git_projects",
    )
    return parser.parse_args()


def _discover_project_root(project_root: Path | None) -> Path:
    return discover_project_root(project_root or Path.cwd())


def _clone_standalone_repo(project_path: Path, destination: Path) -> Path:
    ensure_directory(destination.parent)
    run_command(["git", "clone", "--no-hardlinks", str(project_path), str(destination)], capture_output=True)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=project_path, capture_output=True).stdout.strip()
    run_command(["git", "checkout", "--detach", head], cwd=destination, capture_output=True)
    return destination


def _remove_repo_metadata(source_dir: Path, preserved_projects: list[str]) -> None:
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


if __name__ == "__main__":
    args = parse_args()
    create_workspace_snapshot_for_current_environment(
        workspace_root=args.workspace_root,
        preserve_git_projects=(
            parse_snapshot_git_projects(args.snapshot_git_projects)
            if args.snapshot_git_projects is not None
            else None
        ),
    )
