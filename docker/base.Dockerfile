# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

FROM debian:bookworm-slim

LABEL org.opencontainers.image.description="Minimal environment for building GKI kernels"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:/root/.local/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    bc \
    bison \
    ccache \
    ca-certificates \
    curl \
    file \
    flex \
    git \
    lz4 \
    make \
    openssh-client \
    python3 \
    python3-pip \
    python3-venv \
    rsync \
    unzip \
    xz-utils \
    zip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

RUN curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo -o /usr/local/bin/repo \
    && chmod +x /usr/local/bin/repo \
    && printf 'repo version: ' \
    && repo --version

RUN git config --system --add safe.directory "/workspace" \
    && git config --system --add safe.directory "/workspace/*"

WORKDIR /workspace

ENTRYPOINT ["/bin/bash"]
