# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_JOBS = os.cpu_count() or 1


def add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target name; defaults to AKB_TARGET when set")


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]
