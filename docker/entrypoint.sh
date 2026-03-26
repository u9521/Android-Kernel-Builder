#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

if [[ -n "${GKI_ENV_FILE:-}" && -f "${GKI_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${GKI_ENV_FILE}"
fi

add_safe_directory() {
  local dir="$1"
  if [[ -z "$dir" || ! -d "$dir" ]]; then
    return 0
  fi
  if git config --global --get-all safe.directory 2>/dev/null | grep -Fxq "$dir"; then
    return 0
  fi
  git config --global --add safe.directory "$dir"
}

if command -v git >/dev/null 2>&1; then
  add_safe_directory "$(pwd)"
  add_safe_directory "${GKI_WORKSPACE_ROOT:-}"
  add_safe_directory "${GKI_SOURCE_ROOT:-}"
  add_safe_directory "${GKI_BUILDER_ROOT:-}"
fi

if [[ $# -eq 0 ]]; then
  exec /bin/bash
fi

exec "$@"
