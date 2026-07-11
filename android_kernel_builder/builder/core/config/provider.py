# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path

from .resolver import resolve_target, resolve_target_name
from .schema import TargetConfig


class TargetConfigProvider:
    """Facade for resolving and loading target configurations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def load(self, target_name: str | None = None) -> TargetConfig:
        return resolve_target(self.project_root, target_name)

    def resolve_name(self, target_name: str | None = None) -> str:
        return resolve_target_name(self.project_root, target_name)
