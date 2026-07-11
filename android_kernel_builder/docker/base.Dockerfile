# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

FROM debian:bookworm-slim

LABEL org.opencontainers.image.description="Minimal environment for building GKI kernels"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

COPY android_kernel_builder/docker/install-base-deps.sh /usr/local/bin/install-base-deps
RUN chmod +x /usr/local/bin/install-base-deps \
    && /usr/local/bin/install-base-deps

WORKDIR /workspace

ENTRYPOINT ["/bin/bash"]
