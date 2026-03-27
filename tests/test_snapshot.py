#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

environment_module = importlib.import_module("gki_builder.environment")
layout = importlib.import_module("gki_builder.layout")
snapshot = importlib.import_module("gki_builder.snapshot")


class SnapshotTests(unittest.TestCase):
    def test_create_workspace_snapshot_preserves_selected_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "workspace"
            source_dir = workspace_root / "android-kernel"
            metadata_dir = workspace_root / ".akb" / "state" / "targets" / "sample"
            common_dir = source_dir / "common"
            tools_dir = source_dir / "tools"
            common_dir.mkdir(parents=True, exist_ok=True)
            tools_dir.mkdir(parents=True, exist_ok=True)
            (tools_dir / "BUILD.bazel").write_text("exports_files([])\n", encoding="utf-8")
            (source_dir / ".repo" / "manifests").mkdir(parents=True, exist_ok=True)

            self._init_git_repo(common_dir, "README.md", "common")
            self._convert_to_gitfile(common_dir, temp_root / "gitdirs" / "common.git")
            self._init_git_repo(tools_dir, "BUILD.bazel", "tools")
            self._convert_to_gitfile(tools_dir, temp_root / "gitdirs" / "tools.git")

            result = snapshot.create_workspace_snapshot(workspace_root, source_dir, metadata_dir, ["common"])

            self.assertTrue(result["repo_metadata_removed"])
            self.assertFalse((source_dir / ".repo").exists())
            self.assertTrue((common_dir / ".git").is_dir())
            self.assertFalse((tools_dir / ".git").exists())

            head = self._git(common_dir, "rev-parse", "HEAD").strip()
            self.assertTrue(head)
            self.assertIn("common", (common_dir / "README.md").read_text(encoding="utf-8"))
            self.assertTrue((metadata_dir / "snapshot.json").exists())

    def test_parse_snapshot_git_projects_uses_default(self) -> None:
        self.assertEqual(snapshot.parse_snapshot_git_projects(None), ["common"])
        self.assertEqual(snapshot.parse_snapshot_git_projects("common,build/kernel"), ["common", "build/kernel"])

    def test_create_workspace_snapshot_for_current_environment_uses_docker_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "workspace"
            source_dir = workspace_root / "android-kernel"
            metadata_dir = workspace_root / "docker_metadata" / "targets" / "sample"
            common_dir = source_dir / "common"
            tools_dir = source_dir / "tools"
            common_dir.mkdir(parents=True, exist_ok=True)
            tools_dir.mkdir(parents=True, exist_ok=True)
            (tools_dir / "BUILD.bazel").write_text("exports_files([])\n", encoding="utf-8")
            (source_dir / ".repo" / "manifests").mkdir(parents=True, exist_ok=True)
            (temp_root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
            layout.active_target_file(workspace_root).parent.mkdir(parents=True, exist_ok=True)
            layout.active_target_file(workspace_root).write_text(
                """
version = 1
name = "sample"

[manifest]
source = "remote"
url = "https://example.com/manifest"
branch = "common-android15-6.6"

[build]
system = "kleaf"
arch = "aarch64"

[workspace]
source_dir = "android-kernel"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            self._init_git_repo(common_dir, "README.md", "common")
            self._convert_to_gitfile(common_dir, temp_root / "gitdirs" / "common.git")
            self._init_git_repo(tools_dir, "BUILD.bazel", "tools")
            self._convert_to_gitfile(tools_dir, temp_root / "gitdirs" / "tools.git")

            with mock.patch.object(
                snapshot,
                "discover_current_environment",
                return_value=environment_module.AkbEnvironment(mode="docker", work_root=workspace_root),
            ):
                result = snapshot.create_workspace_snapshot_for_current_environment(
                    workspace_root=workspace_root,
                    start_dir=temp_root,
                )

            self.assertEqual(result["preserved_git_projects"], ["common"])
            self.assertTrue((metadata_dir / "snapshot.json").exists())

    def _init_git_repo(self, path: Path, file_name: str, content: str) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / file_name).write_text(content + "\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            }
        )
        self._git(path, "init")
        self._git(path, "add", file_name)
        self._git(path, "commit", "-m", "init", env=env)

    def _convert_to_gitfile(self, worktree: Path, gitdir: Path) -> None:
        original_git_dir = worktree / ".git"
        gitdir.parent.mkdir(parents=True, exist_ok=True)
        original_git_dir.rename(gitdir)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")

    def _git(self, cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
        import subprocess

        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout


if __name__ == "__main__":
    unittest.main()
