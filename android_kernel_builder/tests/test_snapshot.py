#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

layout = importlib.import_module("android_kernel_builder.builder.layout")
snapshot = importlib.import_module("android_kernel_builder.builder.snapshot")


class SnapshotTests(unittest.TestCase):
    def test_create_workspace_snapshot_preserves_selected_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "workspace"
            source_dir = layout.target_source_root(workspace_root, "sample")
            metadata_dir = layout.docker_target_metadata_root(workspace_root, "sample")
            common_dir = source_dir / "common"
            tools_dir = source_dir / "tools"
            common_dir.mkdir(parents=True, exist_ok=True)
            tools_dir.mkdir(parents=True, exist_ok=True)
            (tools_dir / "BUILD.bazel").write_text("exports_files([])\n", encoding="utf-8")
            (source_dir / ".repo" / "manifests").mkdir(parents=True, exist_ok=True)

            self._init_git_repo(common_dir, "README.md", "common")
            self._add_git_symlink(common_dir, "README.link", Path("README.md"))
            self._convert_to_gitfile(common_dir, temp_root / "gitdirs" / "common.git")
            self._init_git_repo(tools_dir, "BUILD.bazel", "tools")
            self._convert_to_gitfile(tools_dir, temp_root / "gitdirs" / "tools.git")

            result = snapshot.create_workspace_snapshot(workspace_root, source_dir, metadata_dir, ["common"])

            self.assertTrue(result["repo_metadata_removed"])
            self.assertFalse((source_dir / ".repo").exists())
            self.assertTrue((common_dir / ".git").is_dir())
            self.assertFalse((tools_dir / ".git").exists())
            self.assertTrue(layout.temp_root(workspace_root).is_dir())
            self.assertTrue((common_dir / "README.link").is_symlink())
            self.assertEqual(Path(os.readlink(common_dir / "README.link")), Path("README.md"))
            self.assertTrue((metadata_dir / "snapshot.json").exists())

    def test_create_workspace_snapshot_for_current_environment_uses_target_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            self._write_workspace_project(workspace_root)
            source_dir = layout.target_source_root(workspace_root, "sample")
            common_dir = source_dir / "common"
            common_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / ".repo" / "manifests").mkdir(parents=True, exist_ok=True)
            self._init_git_repo(common_dir, "README.md", "common")
            self._convert_to_gitfile(common_dir, Path(temp_dir) / "gitdirs" / "common.git")

            with mock.patch.dict(os.environ, {"AKB_TARGET": "sample"}):
                result = snapshot.create_workspace_snapshot_for_current_environment(workspace_root=workspace_root)

            self.assertEqual(result["preserved_git_projects"], ["common"])
            self.assertTrue((layout.docker_target_metadata_root(workspace_root, "sample") / "snapshot.json").exists())

    def _write_workspace_project(self, workspace_root: Path) -> None:
        workspace_root.mkdir(parents=True, exist_ok=True)
        (workspace_root / "pyproject.toml").write_text("[project]\nname = \"sample\"\n", encoding="utf-8")
        layout.target_configs_root(workspace_root).mkdir(parents=True, exist_ok=True)
        layout.target_config_file(workspace_root, "sample").write_text(
            """
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"
""".strip()
            + "\n",
            encoding="utf-8",
        )

    def _init_git_repo(self, path: Path, file_name: str, content: str) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / file_name).write_text(content + "\n", encoding="utf-8")
        env = os.environ.copy()
        env.update({"GIT_AUTHOR_NAME": "Test User", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "Test User", "GIT_COMMITTER_EMAIL": "test@example.com"})
        self._git(path, "init")
        self._git(path, "add", file_name)
        self._git(path, "commit", "-m", "init", env=env)

    def _convert_to_gitfile(self, worktree: Path, gitdir: Path) -> None:
        original_git_dir = worktree / ".git"
        gitdir.parent.mkdir(parents=True, exist_ok=True)
        original_git_dir.rename(gitdir)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")

    def _add_git_symlink(self, repo_dir: Path, link_name: str, target: Path) -> None:
        link_path = repo_dir / link_name
        link_path.symlink_to(target)
        env = os.environ.copy()
        env.update({"GIT_AUTHOR_NAME": "Test User", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "Test User", "GIT_COMMITTER_EMAIL": "test@example.com"})
        self._git(repo_dir, "add", link_name)
        self._git(repo_dir, "commit", "-m", "symlink", env=env)

    def _git(self, cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
        import subprocess

        result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env)
        return result.stdout


if __name__ == "__main__":
    unittest.main()
