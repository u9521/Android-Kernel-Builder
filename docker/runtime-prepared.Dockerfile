# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/example/gki-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /tmp/akb-build

COPY LICENSE README.md pyproject.toml ./
COPY src ./src
COPY docker/entrypoint.sh docker/entrypoint.sh

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/gki-wheels .
RUN install -Dm755 "docker/entrypoint.sh" /tmp/gki-runtime/bin/gki-workspace-entrypoint

FROM ${BASE_IMAGE}

COPY --from=builder /tmp/gki-wheels /tmp/gki-wheels
RUN pip install --no-cache-dir /tmp/gki-wheels/*.whl \
    && install -Dm755 /opt/venv/bin/gki-builder /usr/local/bin/gki-builder \
    && rm -rf /tmp/gki-wheels
COPY prepared-workspace/ /workspace/
COPY --from=builder /tmp/gki-runtime/bin/gki-workspace-entrypoint /usr/local/bin/gki-workspace-entrypoint

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/gki-workspace-entrypoint"]
