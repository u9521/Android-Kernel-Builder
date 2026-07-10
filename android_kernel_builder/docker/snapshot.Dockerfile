# syntax=docker/dockerfile:1.7-labs
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/u9521/gki-base:latest
FROM ${BASE_IMAGE}

ARG SOURCE_TARGET_FILE=android_kernel_builder/configs/targets/android15-6.6.toml
ARG SNAPSHOT_GIT_PROJECTS=common

ENV UV_PROJECT_ENVIRONMENT=/workspace/.venv

WORKDIR /workspace

COPY . .

RUN uv sync --frozen --no-dev

RUN uv run image-env \
        --source-target-file ${SOURCE_TARGET_FILE}
RUN install -Dm755 "android_kernel_builder/docker/entrypoint.sh" /usr/local/bin/akb-entrypoint

RUN --security=insecure . /workspace/docker_datas/akb.env \
    && uv run sync-source \
    && uv run cache prepare-base \
    && uv run python -m android_kernel_builder.builder.commands.snapshot \
        --snapshot-git-projects ${SNAPSHOT_GIT_PROJECTS} \
    && uv run warmup-build \
    && uv run cache pack-base \
    && find "/workspace/source-code/${AKB_TARGET}/common" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} + \
    && rm -rf "/workspace/out/${AKB_TARGET}" \
        "/workspace/source-code/${AKB_TARGET}/out" \
    && rm -rvf "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv /workspace/docker_datas/outerimage \
    && uv run print-usage-report

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/akb-entrypoint"]
