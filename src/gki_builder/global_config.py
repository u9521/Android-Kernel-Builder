# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib

from .utils import discover_project_root


DEFAULT_GLOBAL_CONFIG_PATH = Path("configs/global.toml")


@dataclass(slots=True)
class GlobalConfig:
    snapshot_git_projects: list[str] = field(default_factory=lambda: ["common"])


def load_global_config(project_root: Path | None = None) -> GlobalConfig:
    root = discover_project_root(project_root or Path.cwd())
    config_path = root / DEFAULT_GLOBAL_CONFIG_PATH
    if not config_path.exists():
        return GlobalConfig()

    payload = tomllib.loads(config_path.read_text(encoding="utf-8")) or {}
    snapshot = _mapping(payload.get("snapshot"))
    return GlobalConfig(
        snapshot_git_projects=_string_list(snapshot.get("git_projects"), ["common"], config_path, "snapshot.git_projects")
    )


def _mapping(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Global config section must be a table: {value!r}")
    return value


def _string_list(value: object, default: list[str], config_path: Path, field_name: str) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"Invalid {field_name} in {config_path}: expected list of non-empty strings")
    return list(value)
