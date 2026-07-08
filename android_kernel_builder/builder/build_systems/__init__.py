# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildSystemSpec:
    name: str
    supports_warmup: bool
    supports_ccache: bool
    allows_cache_bazel_dir: bool
    allows_cache_ccache_dir: bool
    default_use_ccache: bool


_BUILD_SYSTEM_SPECS: dict[str, BuildSystemSpec] = {
    "kleaf": BuildSystemSpec(
        name="kleaf",
        supports_warmup=True,
        supports_ccache=False,
        allows_cache_bazel_dir=True,
        allows_cache_ccache_dir=False,
        default_use_ccache=False,
    ),
    "legacy": BuildSystemSpec(
        name="legacy",
        supports_warmup=False,
        supports_ccache=True,
        allows_cache_bazel_dir=False,
        allows_cache_ccache_dir=True,
        default_use_ccache=True,
    ),
}


def supported_build_systems() -> tuple[str, ...]:
    return tuple(_BUILD_SYSTEM_SPECS.keys())


def get_build_system_spec(name: str) -> BuildSystemSpec | None:
    return _BUILD_SYSTEM_SPECS.get(name)
