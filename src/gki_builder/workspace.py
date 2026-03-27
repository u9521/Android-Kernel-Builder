# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from . import layout
from .targets import TargetConfig
from .utils import current_environment, ensure_directory, run_command, sha256_file, write_json


def sync_source(
    target: TargetConfig,
    workspace_root: Path,
    cache_root: Path,
    jobs: int,
) -> dict[str, str]:
    workspace_root = workspace_root.resolve()
    cache_root = cache_root.resolve()
    source_dir = ensure_directory(workspace_root / target.workspace.source_dir)
    metadata_dir = ensure_directory(_target_metadata_root(workspace_root, target))
    repo_reference_dir = ensure_directory(cache_root / target.cache.repo_dir)
    ensure_directory(cache_root / target.cache.bazel_dir)
    ensure_directory(cache_root / target.cache.ccache_dir)

    _repo_init(target, source_dir, repo_reference_dir)
    deprecated_branch = _auto_fix_remote_deprecated_branch(target, source_dir)

    run_command(
        _repo_sync_command(target, jobs),
        cwd=source_dir,
    )

    metadata = {
        "target": target.name,
        "config_path": str(target.config_path),
        "source_dir": str(source_dir),
        "cache_root": str(cache_root),
        "manifest_source": target.manifest.source,
        "manifest_url": target.manifest.url,
        "manifest_branch": target.manifest.branch,
        "manifest_file": target.manifest.file,
        "manifest_path": str(target.manifest.path) if target.manifest.path else None,
        "manifest_sha256": sha256_file(target.manifest.path) if target.manifest.path else None,
        "manifest_minimal": target.manifest.minimal,
        "manifest_autodetect_deprecated": target.manifest.autodetect_deprecated,
        "deprecated_branch": deprecated_branch,
    }
    write_json(metadata_dir / "workspace.json", metadata)
    return metadata


def build_environment(target: TargetConfig, cache_root: Path) -> dict[str, str]:
    return current_environment({
        "USE_CCACHE": "1",
        "CCACHE_DIR": str((cache_root / target.cache.ccache_dir).resolve()),
    })


def _target_metadata_root(workspace_root: Path, target: TargetConfig) -> Path:
    metadata_dir = target.workspace.metadata_dir
    if metadata_dir == layout.docker_target_metadata_relative_dir():
        return layout.docker_target_metadata_root(workspace_root, target.name)
    return layout.host_target_metadata_root(workspace_root, target.name)


def _repo_init(target: TargetConfig, source_dir: Path, repo_reference_dir: Path) -> None:
    command = ["repo", "init"]
    if target.manifest.minimal:
        command.append("--depth=1")

    if target.manifest.source == "remote":
        command.extend(["-u", target.manifest.url or "", "-b", target.manifest.branch or ""])
        if target.manifest.file:
            command.extend(["-m", target.manifest.file])
    else:
        command.extend(["-u", target.manifest.url or "", "-m", str(target.manifest.path or "")])
        if target.manifest.branch:
            command.extend(["-b", target.manifest.branch])

    if any(repo_reference_dir.iterdir()):
        command.extend(["--reference", str(repo_reference_dir)])

    run_command(command, cwd=source_dir)


def _repo_sync_command(target: TargetConfig, jobs: int) -> list[str]:
    command = ["repo", "--trace", "sync", f"-j{jobs}"]
    if target.manifest.minimal:
        command.extend(["-c", "--no-clone-bundle", "--no-tags"])
    return command


def _auto_fix_remote_deprecated_branch(target: TargetConfig, source_dir: Path) -> str | None:
    if (target.manifest.source != "remote" or not target.manifest.branch or not target.manifest.autodetect_deprecated):
        return None

    kernel_branch = _kernel_project_branch_name(target.manifest.branch)
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

    manifest_path = source_dir / ".repo/manifests" / (target.manifest.file or "default.xml")
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


def rewrite_manifest_revisions(
    manifest_path: Path,
    original_branch: str,
    replacement_branch: str,
) -> bool:
    original_text = manifest_path.read_text(encoding="utf-8")
    updated_text = original_text.replace(
        f'"{original_branch}"',
        f'"{replacement_branch}"',
    )
    if updated_text == original_text:
        return False
    manifest_path.write_text(updated_text, encoding="utf-8")
    print(
        f"rewrote manifest revisions in {manifest_path} from {original_branch} to {replacement_branch}",
        flush=True,
    )
    return True
