#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:${PYTHONPATH}}"

TARGET=${1:-android15-6.6}

python3 -m gki_builder.cli sync-source \
  --target "$TARGET" \
  --cache-root .cache

python3 -m gki_builder.cli build \
  --target "$TARGET" \
  --cache-root .cache \
  --output-root out
