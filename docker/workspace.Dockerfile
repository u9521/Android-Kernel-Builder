# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/example/gki-base:latest
FROM ${BASE_IMAGE}

ARG TARGET_CONFIG=configs/targets/android15-6.6.toml

ENV GKI_BUILDER_ROOT=${GKI_WORKSPACE_ROOT}/.gki-builder/tooling \
    GKI_CACHE_ROOT=${GKI_WORKSPACE_ROOT}/.cache \
    GKI_TARGET_CONFIG=${GKI_WORKSPACE_ROOT}/.gki-builder/image/target-config.toml \
    GKI_ENV_FILE=${GKI_WORKSPACE_ROOT}/.gki-builder/image/gki-builder.env

WORKDIR ${GKI_BUILDER_ROOT}

COPY . ${GKI_BUILDER_ROOT}

RUN pip install --no-cache-dir .
RUN TARGET_CONFIG_PATH="${TARGET_CONFIG}" python3 -m gki_builder.image_env
RUN install -Dm755 "${GKI_BUILDER_ROOT}/docker/entrypoint.sh" /usr/local/bin/gki-workspace-entrypoint
RUN mkdir -p "${GKI_CACHE_ROOT}" "${GKI_WORKSPACE_ROOT}/.warmup-out" \
    && gki-builder prepare-workspace \
        --target-config ${TARGET_CONFIG} \
        --workspace ${GKI_WORKSPACE_ROOT} \
        --cache-root ${GKI_CACHE_ROOT} \
    && gki-builder warmup-build \
        --target-config ${TARGET_CONFIG} \
        --workspace ${GKI_WORKSPACE_ROOT} \
        --cache-root ${GKI_CACHE_ROOT} \
        --output-root ${GKI_WORKSPACE_ROOT}/.warmup-out \
    && rm -rf "${GKI_WORKSPACE_ROOT}/.warmup-out"

WORKDIR ${GKI_WORKSPACE_ROOT}
ENTRYPOINT ["/bin/bash", "/usr/local/bin/gki-workspace-entrypoint"]
