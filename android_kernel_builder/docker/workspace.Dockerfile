# syntax=docker/dockerfile:1.7-labs
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/u9521/gki-base:latest
FROM ${BASE_IMAGE}

ARG TARGET=android15-6.6

ENV UV_PROJECT_ENVIRONMENT=/workspace/.venv \
    AKB_TARGET=${TARGET}

WORKDIR /workspace

COPY . .

RUN uv sync --frozen --no-dev

RUN uv run akb image-env --target "${TARGET}"
RUN install -Dm755 "android_kernel_builder/docker/entrypoint.sh" /usr/local/bin/akb-entrypoint

RUN --security=insecure . /workspace/docker_datas/akb.env \
    && uv run akb sync-source \
    && uv run akb cache prepare-base \
    && uv run akb warmup-build \
    && uv run akb cache pack-base \
    && rm -rvf "/workspace/out/${AKB_TARGET}" \
        "/workspace/source-code/${AKB_TARGET}/out" \
    && rm -rf "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv /workspace/docker_datas/outerimage \
    && uv run akb usage

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/akb-entrypoint"]
