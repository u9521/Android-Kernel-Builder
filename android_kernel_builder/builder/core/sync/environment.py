# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from ...utils import current_environment


def build_environment() -> dict[str, str]:
    return current_environment()
