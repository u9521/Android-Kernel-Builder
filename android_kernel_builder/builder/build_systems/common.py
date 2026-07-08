# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import os

from ..targets import TargetConfig


def resolve_build_jobs(target: TargetConfig) -> int:
    return target.build.jobs or (os.cpu_count() or 1)
