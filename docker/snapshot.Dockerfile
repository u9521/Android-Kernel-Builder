# syntax=docker/dockerfile:1.7-labs
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/example/gki-base:latest
FROM ${BASE_IMAGE} AS builder

ARG SOURCE_TARGET_FILE=configs/targets/android15-6.6.toml
ARG SNAPSHOT_GIT_PROJECTS=common

WORKDIR /tmp/akb-build

COPY . .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/gki-wheels .
RUN PYTHONPATH=/tmp/akb-build/src python3 -m gki_builder.image_env \
        --source-target-file ${SOURCE_TARGET_FILE} \
        --workspace-root /workspace \
        --output-root /tmp/gki-runtime/workspace
RUN install -Dm755 "docker/entrypoint.sh" /tmp/gki-runtime/bin/gki-workspace-entrypoint

FROM ${BASE_IMAGE}

ARG SNAPSHOT_GIT_PROJECTS=common

COPY --from=builder /tmp/gki-wheels /tmp/gki-wheels
RUN pip install --no-cache-dir /tmp/gki-wheels/*.whl \
    && install -Dm755 /opt/venv/bin/gki-builder /usr/local/bin/gki-builder \
    && rm -rf /tmp/gki-wheels
COPY --from=builder /tmp/gki-runtime/workspace/.akb /workspace/.akb
COPY --from=builder /tmp/gki-runtime/workspace/docker_datas /workspace/docker_datas
COPY --from=builder /tmp/gki-runtime/bin/gki-workspace-entrypoint /usr/local/bin/gki-workspace-entrypoint

RUN --security=insecure gki-builder sync-source \
    && python3 -m gki_builder.runtime_cache prepare-base \
    && python3 -m gki_builder.snapshot \
        --workspace-root /workspace \
        --snapshot-git-projects ${SNAPSHOT_GIT_PROJECTS} \
    && gki-builder warmup-build --output-root /workspace/out \
    && python3 -m gki_builder.runtime_cache pack-base \
    && rm -rvf /workspace/.cache \
    && mkdir -pv /workspace/.cache \
    && mkdir -pv /workspace/docker_datas/outerimage \
    && rm -rf /workspace/.warmup-out

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/gki-workspace-entrypoint"]
