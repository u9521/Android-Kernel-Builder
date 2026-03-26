#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:${PYTHONPATH}}"

TARGET_CONFIG=${1:-configs/targets/android15-6.6.toml}

python3 -m gki_builder.cli prepare-workspace \
  --target-config "$TARGET_CONFIG" \
  --workspace .workspace \
  --cache-root .cache

python3 -m gki_builder.cli build \
  --target-config "$TARGET_CONFIG" \
  --workspace .workspace \
  --cache-root .cache \
  --output-root out
