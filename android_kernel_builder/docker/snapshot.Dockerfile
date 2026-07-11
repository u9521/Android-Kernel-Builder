# syntax=docker/dockerfile:1.7-labs
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

FROM debian:bookworm-slim

LABEL org.opencontainers.image.description="Snapshot environment for building GKI kernels"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

COPY android_kernel_builder/docker/install-base-deps.sh /usr/local/bin/install-base-deps
RUN chmod +x /usr/local/bin/install-base-deps \
    && /usr/local/bin/install-base-deps

ARG TARGET=android15-6.6
ARG SNAPSHOT_GIT_PROJECTS=common

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
    && uv run akb snapshot \
        --snapshot-git-projects ${SNAPSHOT_GIT_PROJECTS} \
    && uv run akb warmup-build \
    && uv run akb cache pack-base \
    && find "/workspace/source-code/${AKB_TARGET}/common" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} + \
    && rm -rf "/workspace/out/${AKB_TARGET}" \
        "/workspace/source-code/${AKB_TARGET}/out" \
    && rm -rvf "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv "/workspace/cache/${AKB_TARGET}" \
    && mkdir -pv /workspace/docker_datas/outerimage \
    && uv run akb usage

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/akb-entrypoint"]
