# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import os

from ...config import BuildConfig


def resolve_build_jobs(config: BuildConfig) -> int:
    return config.jobs or (os.cpu_count() or 1)
