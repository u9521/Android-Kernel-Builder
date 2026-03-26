# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/example/gki-base:latest
FROM ${BASE_IMAGE}

ARG TARGET_CONFIG=configs/targets/android15-6.6.toml

ENV GKI_BUILDER_ROOT=/opt/gki-builder \
    GKI_WORKSPACE_ROOT=/workspace \
    GKI_CACHE_ROOT=/workspace/.cache \
    GKI_OUTPUT_ROOT=/workspace/out \
    GKI_TARGET_CONFIG=/opt/gki-builder/${TARGET_CONFIG} \
    GKI_ENV_FILE=/etc/gki-builder.env

WORKDIR /opt/gki-builder

COPY . /opt/gki-builder

RUN pip install --no-cache-dir .
RUN TARGET_CONFIG_PATH="${TARGET_CONFIG}" python3 - <<'PY'
from pathlib import Path
import os
import tomllib

repo_root = Path("/opt/gki-builder")
config_path = repo_root / os.environ["TARGET_CONFIG_PATH"]
payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
workspace = payload.get("workspace") or {}
target_name = payload.get("name", "")
source_dir = workspace.get("source_dir", "android-kernel")
env_file = Path("/etc/gki-builder.env")
env_file.write_text(
    f"export GKI_TARGET_NAME={target_name}\n"
    f"export GKI_SOURCE_ROOT=/workspace/{source_dir}\n",
    encoding="utf-8",
)
PY
RUN mkdir -p /workspace/.cache /workspace/.warmup-out \
    && gki-builder prepare-workspace \
        --target-config ${TARGET_CONFIG} \
        --workspace /workspace \
        --cache-root /workspace/.cache \
    && gki-builder build \
        --target-config ${TARGET_CONFIG} \
        --workspace /workspace \
        --cache-root /workspace/.cache \
        --output-root /workspace/.warmup-out \
    && rm -rf /workspace/.warmup-out

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/opt/gki-builder/docker/entrypoint.sh"]
