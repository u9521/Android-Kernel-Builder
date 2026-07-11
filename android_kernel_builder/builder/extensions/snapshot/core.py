# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from ... import layout
from ...core.config import TargetConfigProvider, load_global_config
from ...utils import ensure_directory, write_json
from .git import clone_standalone_repo, remove_repo_metadata

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

    temp_root_dir = ensure_directory(layout.temp_root(workspace_root))
    with tempfile.TemporaryDirectory(prefix="gki-snapshot-", dir=temp_root_dir) as temp_dir:
        temp_root = Path(temp_dir)
        clones: dict[str, Path] = {}
        for project in projects:
            project_path = source_dir / project
            if not project_path.is_dir():
                raise FileNotFoundError(f"Snapshot git project not found: {project_path}")
            clones[project] = clone_standalone_repo(project_path, temp_root / project)

        remove_repo_metadata(source_dir, projects)

        for project, clone_path in clones.items():
            project_path = source_dir / project
            if project_path.exists():
                shutil.rmtree(project_path)
            ensure_directory(project_path.parent)
            shutil.move(str(clone_path), str(project_path))

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
    del start_dir
    resolved_workspace_root = Path(workspace_root).resolve() if workspace_root is not None else Path.cwd()
    return create_workspace_snapshot_from_workspace_root(
        resolved_workspace_root,
        preserve_git_projects=preserve_git_projects,
        project_root=resolved_workspace_root,
    )


def create_workspace_snapshot_from_workspace_root(
    workspace_root: Path,
    *,
    preserve_git_projects: list[str] | None = None,
    project_root: Path | None = None,
) -> dict[str, object]:
    workspace_root = workspace_root.resolve()
    root = project_root or workspace_root
    target = TargetConfigProvider(root).load()
    global_config = load_global_config(root)
    return create_workspace_snapshot(
        workspace_root,
        layout.target_source_root(workspace_root, target.name),
        layout.docker_target_metadata_root(workspace_root, target.name),
        preserve_git_projects or list(global_config.snapshot_git_projects),
    )
