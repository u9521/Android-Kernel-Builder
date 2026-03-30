# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

ARG BASE_IMAGE=ghcr.io/example/gki-base:latest
FROM ${BASE_IMAGE} AS builder

ARG SOURCE_TARGET_FILE=configs/targets/android15-6.6.toml

WORKDIR /tmp/akb-build

COPY . .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/gki-wheels .
RUN PYTHONPATH=/tmp/akb-build/src python3 -m gki_builder.image_env \
        --source-target-file ${SOURCE_TARGET_FILE} \
        --workspace-root /workspace \
        --output-root /tmp/gki-runtime/workspace
RUN install -Dm755 "docker/entrypoint.sh" /tmp/gki-runtime/bin/gki-workspace-entrypoint

FROM ${BASE_IMAGE}

COPY --from=builder /tmp/gki-wheels /tmp/gki-wheels
RUN pip install --no-cache-dir /tmp/gki-wheels/*.whl \
    && install -Dm755 /opt/venv/bin/gki-builder /usr/local/bin/gki-builder \
    && install -Dm755 /opt/venv/bin/gki-builder-cache-sync /usr/local/bin/gki-builder-cache-sync \
    && rm -rf /tmp/gki-wheels
COPY --from=builder /tmp/gki-runtime/workspace/.akb /workspace/.akb
COPY --from=builder /tmp/gki-runtime/workspace/docker_metadata /workspace/docker_metadata
COPY --from=builder /tmp/gki-runtime/bin/gki-workspace-entrypoint /usr/local/bin/gki-workspace-entrypoint
COPY --from=cache-host . /cache-host

RUN gki-builder sync-source \
    && gki-builder-cache-sync prepare \
    && gki-builder warmup-build --output-root /workspace/.warmup-out \
    && gki-builder-cache-sync save \
    && rm -rf /cache-host \
    && rm -rf /workspace/.warmup-out

WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/usr/local/bin/gki-workspace-entrypoint"]
