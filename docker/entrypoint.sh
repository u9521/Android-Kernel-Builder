#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

if [[ -n "${GKI_ENV_FILE:-}" && -f "${GKI_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${GKI_ENV_FILE}"
fi

if [[ $# -eq 0 ]]; then
  exec /bin/bash
fi

exec "$@"
