# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
from pathlib import Path

from ... import layout
from ...core.config import KleafBuildConfig, LegacyBuildConfig, TargetConfigProvider


def prepare_runtime_image_layout(
    target_name: str,
    *,
    workspace_root: str | Path | None = None,
    project_root: Path | None = None,
) -> None:
    repo_root = (project_root or Path.cwd()).resolve()
    resolved_workspace_root = Path(workspace_root or layout.DOCKER_WORK_ROOT).resolve()
    target = TargetConfigProvider(repo_root).load(target_name)

    docker_datas_dir = layout.docker_datas_root(resolved_workspace_root)
    target_metadata_dir = layout.docker_target_metadata_dir(resolved_workspace_root)
    docker_datas_dir.mkdir(parents=True, exist_ok=True)
    layout.docker_outerimage_root(resolved_workspace_root).mkdir(parents=True, exist_ok=True)
    layout.docker_overlays_root(resolved_workspace_root).mkdir(parents=True, exist_ok=True)

    output_root_path = layout.target_output_root(resolved_workspace_root, target.name)
    dist_dir_path = output_root_path / target.build.dist_dir if target.build.dist_dir else output_root_path
    build_system = _build_system_name(target.build)
    build_target = target.build.target if isinstance(target.build, KleafBuildConfig) else ""
    warmup_target = target.build.warmup_target if isinstance(target.build, KleafBuildConfig) else ""
    dist_flag = target.build.dist_flag if isinstance(target.build, KleafBuildConfig) else ""
    layout.docker_env_file(resolved_workspace_root).write_text(
        f"export AKB_TARGET={target.name}\n"
        f"export AKB_SOURCE_ROOT={layout.target_source_root(resolved_workspace_root, target.name)}\n"
        f"export AKB_BUILD_SYSTEM={build_system}\n"
        f"export AKB_BUILD_ARCH={target.build.arch}\n"
        f"export AKB_BUILD_TARGET={build_target}\n"
        f"export AKB_WARMUP_TARGET={warmup_target or ''}\n"
        f"export AKB_DIST_DIR={dist_dir_path.resolve()}\n"
        f"export AKB_DIST_FLAG={dist_flag}\n"
        f"export AKB_DOCKER_DATAS_ROOT={docker_datas_dir}\n"
        f"export AKB_TARGET_METADATA_ROOT={target_metadata_dir / target.name}\n",
        encoding="utf-8",
    )
    layout.docker_image_info_file(resolved_workspace_root).write_text(
        json.dumps(
            {
                "target": target.name,
                "source_mode": "config",
                "cache_mode": "overlay-image",
                "cache_layout_version": 1,
                "docker_datas_root": str(docker_datas_dir),
                "container_cache_image": str(layout.docker_container_cache_image(resolved_workspace_root)),
                "outerimage_root": str(layout.docker_outerimage_root(resolved_workspace_root)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _build_system_name(build_config: KleafBuildConfig | LegacyBuildConfig) -> str:
    if isinstance(build_config, KleafBuildConfig):
        return "kleaf"
    return "legacy"
