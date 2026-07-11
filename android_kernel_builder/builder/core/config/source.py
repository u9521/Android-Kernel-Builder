# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .loader import _load_target_payload_with_chain, load_mapping


class ConfigSource(ABC):
    """Source for raw target configuration payloads."""

    @abstractmethod
    def list_names(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def load_raw(self, name: str) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def resolve_inherited(self, name: str) -> tuple[dict[str, object], list[Path]]:
        raise NotImplementedError


class FilesystemConfigSource(ConfigSource):
    """Target configuration source backed by a TOML directory."""

    def __init__(self, configs_root: Path):
        self.configs_root = configs_root

    def list_names(self) -> list[str]:
        if not self.configs_root.exists():
            return []
        return [candidate.stem for candidate in sorted(self.configs_root.glob("*.toml"))]

    def load_raw(self, name: str) -> dict[str, object]:
        return load_mapping(self.configs_root / f"{name}.toml")

    def resolve_inherited(self, name: str) -> tuple[dict[str, object], list[Path]]:
        return _load_target_payload_with_chain((self.configs_root / f"{name}.toml").resolve())
