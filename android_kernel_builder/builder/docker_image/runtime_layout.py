# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

from .. import layout
from ..targets import load_target_payload_with_inheritance
from .manifests import embedded_manifest_relative_path, resolve_source_manifest_path
from .payloads import clone_mapping, dump_toml_document


def prepare_runtime_image_layout(
    source_target_file: str | Path,
    *,
    workspace_root: str | Path | None = None,
    project_root: Path | None = None,
) -> None:
    repo_root = (project_root or Path.cwd()).resolve()
    config_path = _resolve_source_target_file(repo_root, source_target_file)
    resolved_workspace_root = Path(workspace_root or layout.DOCKER_WORK_ROOT).resolve()
    manifests_root = layout.target_manifests_root(resolved_workspace_root)
    target_configs_root = layout.target_configs_root(resolved_workspace_root)
    docker_datas_dir = layout.docker_datas_root(resolved_workspace_root)
    final_docker_datas_dir = layout.docker_datas_root(resolved_workspace_root)
    target_metadata_dir = layout.docker_target_metadata_dir(resolved_workspace_root)

    payload, _ = load_target_payload_with_inheritance(config_path)
    target_name_value = payload.get("name", "")
    target_name = target_name_value if isinstance(target_name_value, str) else ""
    if not target_name:
        raise ValueError(f"Missing required target name in {config_path}")

    target_configs_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)
    docker_datas_dir.mkdir(parents=True, exist_ok=True)
    layout.docker_outerimage_root(resolved_workspace_root).mkdir(parents=True, exist_ok=True)
    layout.docker_overlays_root(resolved_workspace_root).mkdir(parents=True, exist_ok=True)
    packaged_target_payload = _prepare_runtime_target_payload(payload, config_path, manifests_root)

    layout.target_config_file(resolved_workspace_root, target_name).write_text(
        dump_toml_document(packaged_target_payload),
        encoding="utf-8",
    )
    build_payload = cast(dict[str, object], packaged_target_payload.get("build") or {})
    manifest_payload = cast(dict[str, object], packaged_target_payload.get("manifest") or {})
    output_root_path = layout.target_output_root(resolved_workspace_root, target_name)
    dist_dir_value = str(build_payload.get("dist_dir", "") or "")
    dist_dir_path = _absolute_path(output_root_path, dist_dir_value) if dist_dir_value else str(output_root_path)
    manifest_path_value = str(manifest_payload.get("path", "") or "")
    manifest_path = _absolute_path(layout.target_manifests_root(resolved_workspace_root), manifest_path_value)
    layout.docker_env_file(resolved_workspace_root).write_text(
        f"export AKB_TARGET={target_name}\n"
        f"export AKB_TARGET_NAME={target_name}\n"
        f"export AKB_SOURCE_ROOT={layout.target_source_root(resolved_workspace_root, target_name)}\n"
        f"export AKB_SOURCE_MODE=embedded\n"
        f"export AKB_BUILD_SYSTEM={build_payload.get('system', '')}\n"
        f"export AKB_BUILD_ARCH={build_payload.get('arch', '')}\n"
        f"export AKB_BUILD_TARGET={build_payload.get('target', '')}\n"
        f"export AKB_WARMUP_TARGET={build_payload.get('warmup_target', '') or ''}\n"
        f"export AKB_DIST_DIR={dist_dir_path}\n"
        f"export AKB_DIST_FLAG={build_payload.get('dist_flag', '')}\n"
        f"export AKB_MANIFEST_SOURCE={manifest_payload.get('source', '')}\n"
        f"export AKB_MANIFEST_URL={manifest_payload.get('url', '')}\n"
        f"export AKB_MANIFEST_BRANCH={manifest_payload.get('branch', '')}\n"
        f"export AKB_MANIFEST_FILE={manifest_payload.get('file', '') or ''}\n"
        f"export AKB_MANIFEST_PATH={manifest_path}\n"
        f"export AKB_DOCKER_DATAS_ROOT={final_docker_datas_dir}\n"
        f"export AKB_TARGET_METADATA_ROOT={target_metadata_dir / target_name}\n",
        encoding="utf-8",
    )
    layout.docker_image_info_file(resolved_workspace_root).write_text(
        json.dumps(
            {
                "target": target_name,
                "source_mode": "embedded",
                "cache_mode": "overlay-image",
                "cache_layout_version": 1,
                "docker_datas_root": str(final_docker_datas_dir),
                "container_cache_image": str(layout.docker_container_cache_image(resolved_workspace_root)),
                "outerimage_root": str(layout.docker_outerimage_root(resolved_workspace_root)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _resolve_source_target_file(project_root: Path, source_target_file: str | Path) -> Path:
    path = Path(source_target_file)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _prepare_runtime_target_payload(
    payload: dict[str, object],
    config_path: Path,
    manifests_root: Path,
) -> dict[str, object]:
    cloned_payload = cast(dict[str, object], clone_mapping(payload))
    cloned_payload.pop("workspace", None)
    cloned_payload.pop("cache", None)
    manifest = cloned_payload.get("manifest")
    if not isinstance(manifest, dict):
        return cloned_payload

    if manifest.get("source") != "local":
        return cloned_payload

    manifest_path_value = manifest.get("path")
    if not isinstance(manifest_path_value, str) or not manifest_path_value:
        return cloned_payload

    source_manifest_path = resolve_source_manifest_path(config_path, manifest_path_value, _manifest_search_root(config_path))
    embedded_manifest_path = embedded_manifest_relative_path(manifest_path_value)
    manifest_copy_path = manifests_root / embedded_manifest_path
    manifest_copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_manifest_path, manifest_copy_path)
    manifest["path"] = embedded_manifest_path.as_posix()
    return cloned_payload


def _manifest_search_root(config_path: Path) -> Path:
    if config_path.parent.name == ".docker-target":
        return config_path.parent.resolve()
    return (config_path.parent.parent / "manifests").resolve()


def _absolute_path(root: Path, value: str) -> str:
    if not value:
        return ""
    candidate = Path(value)
    if candidate.is_absolute():
        return str(candidate)
    return str((root / candidate).resolve())


def main() -> int:
    from ..commands.image_env import main as image_env_main

    return image_env_main()


if __name__ == "__main__":
    raise SystemExit(main())
