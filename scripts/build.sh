#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 -m gki_builder.cli build "$@"
