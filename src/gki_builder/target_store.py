# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .active_target import load_active_target, resolve_embedded_manifest_path
from .config import AkbConfig, load_akb_config
from .environment import AkbEnvironment
from . import layout
from .targets import BuildConfig, CacheConfig, ManifestConfig, TargetConfig, WorkspaceConfig, _parse_target_definition_file, load_mapping


def resolve_target(environment: AkbEnvironment, target_name: str | None = None) -> TargetConfig:
    if environment.mode == "docker":
        return _load_docker_target(environment.work_root)
    return load_host_target(environment.work_root, target_name)


def load_host_target(work_root: Path, target_name: str | None = None) -> TargetConfig:
    akb_config = load_akb_config(work_root)
    resolved_name = resolve_host_target_name(akb_config, target_name)
    config_path = host_target_config_path(work_root, resolved_name)
    return _parse_target_definition_file(
        config_path,
        manifest_root=layout.target_manifests_root(work_root),
        default_source_dir=akb_config.workspace.source_dir,
    )


def host_target_config_path(work_root: Path, target_name: str) -> Path:
    configs_root = layout.target_configs_root(work_root)
    path = layout.target_config_file(work_root, target_name)
    warned_messages: set[str] = set()

    if path.exists():
        declared_name = _declared_target_name(path)
        filename_stem = path.stem

        if declared_name is not None and declared_name != filename_stem:
            _warn_target_mismatch(
                target_name,
                path,
                f"filename '{filename_stem}' != declared name '{declared_name}'",
                warned_messages,
            )

        if declared_name == target_name:
            _ensure_selectable_target_config(path, target_name)
            return path
        if declared_name is not None:
            _warn_target_mismatch(
                target_name,
                path,
                f"requested target '{target_name}' != declared name '{declared_name}'",
                warned_messages,
            )

        fallback_path, fallback_reason = _find_target_config_fallback(configs_root, target_name, skip_path=path)
        if fallback_path is not None and fallback_reason is not None:
            _warn_target_mismatch(
                target_name,
                fallback_path,
                f"using fallback {fallback_reason} match",
                warned_messages,
            )
            _ensure_selectable_target_config(fallback_path, target_name)
            return fallback_path

        if declared_name is not None:
            raise FileNotFoundError(
                f"Target '{target_name}' not found; {path} declares '{declared_name}' and no fallback match exists"
            )
        _ensure_selectable_target_config(path, target_name)
        return path

    fallback_path, fallback_reason = _find_target_config_fallback(configs_root, target_name)
    if fallback_path is not None and fallback_reason is not None:
        _warn_target_mismatch(
            target_name,
            fallback_path,
            f"using fallback {fallback_reason} match",
            warned_messages,
        )
        _ensure_selectable_target_config(fallback_path, target_name)
        return fallback_path

    raise FileNotFoundError(f"Target config not found: {path}")


def _declared_target_name(path: Path) -> str | None:
    payload = load_mapping(path)
    name = payload.get("name")
    if isinstance(name, str) and name:
        return name
    return None


def _ensure_selectable_target_config(path: Path, requested_target_name: str) -> None:
    payload = load_mapping(path)
    base_value = payload.get("base", False)
    if not isinstance(base_value, bool):
        raise ValueError(f"Invalid 'base' in {path}: expected boolean")
    if not base_value:
        return
    raise ValueError(
        f"Target '{requested_target_name}' resolves to base config '{path.name}' and cannot be used as a build target"
    )


def _find_target_config_fallback(
    configs_root: Path,
    target_name: str,
    *,
    skip_path: Path | None = None,
) -> tuple[Path | None, str | None]:
    if not configs_root.exists():
        return None, None

    filename_exact_matches: list[Path] = []
    filename_casefold_matches: list[Path] = []
    declared_exact_matches: list[Path] = []

    for candidate in sorted(configs_root.glob("*.toml")):
        resolved_candidate = candidate.resolve()
        if skip_path is not None and resolved_candidate == skip_path.resolve():
            continue

        candidate_stem = candidate.stem
        if candidate_stem == target_name:
            filename_exact_matches.append(candidate)
        elif _equals_ignore_case(candidate_stem, target_name):
            filename_casefold_matches.append(candidate)

        declared_name = _declared_target_name(candidate)
        if declared_name == target_name:
            declared_exact_matches.append(candidate)

    if filename_exact_matches:
        return _resolve_single_target_match(filename_exact_matches, target_name, "filename"), "filename"

    if filename_casefold_matches:
        return (
            _resolve_single_target_match(filename_casefold_matches, target_name, "filename (case-insensitive)"),
            "filename (case-insensitive)",
        )

    if declared_exact_matches:
        return _resolve_single_target_match(declared_exact_matches, target_name, "declared name"), "declared name"

    return None, None


def _resolve_single_target_match(matches: list[Path], target_name: str, match_kind: str) -> Path:
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(f"Multiple target configs matched target '{target_name}' by {match_kind}: {joined}")
    return matches[0]


def _equals_ignore_case(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def _warn_target_mismatch(target_name: str, config_path: Path, detail: str, warned_messages: set[str]) -> None:
    message = (
        f"warning: target config mismatch for '{target_name}' in '{config_path.name}': {detail}. "
        "Recommend normalizing filename and name field."
    )
    _warn_once(message, warned_messages)


def _warn_once(message: str, warned_messages: set[str]) -> None:
    if message in warned_messages:
        return
    warned_messages.add(message)
    print(message)


def resolve_host_target_name(akb_config: AkbConfig, target_name: str | None) -> str:
    if target_name:
        return target_name
    if akb_config.default_target:
        return akb_config.default_target
    raise ValueError("Missing --target and no default_target configured in .akb/config.toml")


def _load_docker_target(work_root: Path) -> TargetConfig:
    active_target = load_active_target(work_root)
    return TargetConfig(
        name=active_target.name,
        manifest=ManifestConfig(
            source=active_target.manifest.source,
            url=active_target.manifest.url,
            branch=active_target.manifest.branch,
            file=active_target.manifest.file,
            path=resolve_embedded_manifest_path(active_target, work_root),
            minimal=active_target.manifest.minimal,
            autodetect_deprecated=active_target.manifest.autodetect_deprecated,
        ),
        build=BuildConfig(
            system=active_target.build.system,
            target=active_target.build.target,
            warmup_target=active_target.build.warmup_target,
            dist_dir=active_target.build.dist_dir,
            dist_flag=active_target.build.dist_flag,
            arch=active_target.build.arch,
            jobs=active_target.build.jobs,
            legacy_config=active_target.build.legacy_config,
            lto=active_target.build.lto,
            use_ccache=active_target.build.use_ccache,
        ),
        cache=CacheConfig(),
        workspace=WorkspaceConfig(
            source_dir=active_target.workspace.source_dir,
            metadata_dir=layout.docker_target_metadata_relative_dir(),
        ),
        config_path=active_target.config_path,
    )
