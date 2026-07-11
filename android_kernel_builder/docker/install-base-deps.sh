#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"

apt-get update
apt-get install -y --no-install-recommends \
  bash \
  bc \
  bison \
  ccache \
  ca-certificates \
  curl \
  e2fsprogs \
  file \
  flex \
  git \
  lz4 \
  make \
  openssh-client \
  python3 \
  rsync \
  unzip \
  util-linux \
  xz-utils \
  zip
rm -rf /var/lib/apt/lists/*

curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo -o /usr/local/bin/repo
chmod +x /usr/local/bin/repo
printf 'repo version: '
repo --version

curl -LsSf https://astral.sh/uv/install.sh | sh
ln -sf /root/.local/bin/uv /usr/local/bin/uv
ln -sf /root/.local/bin/uvx /usr/local/bin/uvx
uv --version
uvx --version
