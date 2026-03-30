# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from .environment import has_embedded_docker_layout, is_docker_runtime

DEFAULT_RUNTIME_CACHE_ROOT = Path("/workspace/.cache")
DEFAULT_HOST_CACHE_ROOT = Path("/cache-host")
CAP_CHOWN = 1 << 0


def _is_docker_context(runtime_cache_root: Path = DEFAULT_RUNTIME_CACHE_ROOT) -> bool:
    if runtime_cache_root != DEFAULT_RUNTIME_CACHE_ROOT:
        return (runtime_cache_root.parent / ".akb" / "active-target.toml").exists()
    if is_docker_runtime() or Path("/run/.containerenv").exists():
        return True
    return has_embedded_docker_layout()


def _has_entries(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def _replace_runtime_with_symlink(runtime_cache_root: Path, host_cache_root: Path) -> None:
    runtime_parent = runtime_cache_root.parent
    runtime_parent.mkdir(parents=True, exist_ok=True)

    if runtime_cache_root.is_symlink():
        target = runtime_cache_root.resolve(strict=False)
        if target == host_cache_root.resolve():
            return
        runtime_cache_root.unlink()
    elif runtime_cache_root.exists():
        shutil.rmtree(runtime_cache_root)

    runtime_cache_root.symlink_to(host_cache_root)


def _read_effective_capabilities() -> int:
    status_path = Path("/proc/self/status")
    if not status_path.exists():
        return 0
    for line in status_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CapEff:"):
            _, value = line.split(":", 1)
            return int(value.strip(), 16)
    return 0


def _has_capability(capability_mask: int) -> bool:
    return (_read_effective_capabilities() & capability_mask) == capability_mask


def _resolve_existing_reference_path(reference_path: Path) -> Path:
    current_path = reference_path
    while not current_path.exists():
        if current_path.parent == current_path:
            raise FileNotFoundError(f"Unable to resolve ownership reference for {reference_path}")
        current_path = current_path.parent
    return current_path


def _apply_cache_ownership(cache_root: Path, reference_path: Path) -> None:
    if not _has_capability(CAP_CHOWN):
        raise RuntimeError("gki-builder-cache-sync requires CAP_CHOWN; in CI run the container with chown capability")

    reference_stat = _resolve_existing_reference_path(reference_path).stat()
    resolved_uid = reference_stat.st_uid
    resolved_gid = reference_stat.st_gid
    for root, dir_names, file_names in os.walk(cache_root):
        os.chown(root, resolved_uid, resolved_gid)
        for name in dir_names:
            os.chown(Path(root) / name, resolved_uid, resolved_gid)
        for name in file_names:
            os.chown(Path(root) / name, resolved_uid, resolved_gid)


def _format_bytes(total_bytes: int) -> str:
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(total_bytes)
    for suffix in suffixes:
        if value < 1024 or suffix == suffixes[-1]:
            if suffix == "B":
                return f"{int(value)} {suffix}"
            return f"{value:.1f} {suffix}"
        value /= 1024
    return f"{total_bytes} B"


def _count_files_and_bytes(root: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    if not root.exists():
        return file_count, total_bytes

    for current_root, _, file_names in os.walk(root):
        current_path = Path(current_root)
        for file_name in file_names:
            file_path = current_path / file_name
            file_count += 1
            total_bytes += file_path.stat().st_size
    return file_count, total_bytes


def _print_stats(label: str, root: Path) -> None:
    file_count, total_bytes = _count_files_and_bytes(root)
    print(f"[docker-cache-sync] {label}: {root}")
    print(f"[docker-cache-sync] {label} files: {file_count}")
    print(f"[docker-cache-sync] {label} size: {_format_bytes(total_bytes)}")


def prepare_cache(
    runtime_cache_root: Path = DEFAULT_RUNTIME_CACHE_ROOT,
    host_cache_root: Path = DEFAULT_HOST_CACHE_ROOT,
) -> None:
    if _has_entries(host_cache_root):
        print("[docker-cache-sync] repo cache present, replacing runtime cache with mounted cache")
        host_cache_root.mkdir(parents=True, exist_ok=True)
        _apply_cache_ownership(host_cache_root, runtime_cache_root)
        _replace_runtime_with_symlink(runtime_cache_root, host_cache_root)
    else:
        print("[docker-cache-sync] repo cache missing or empty, keeping image cache")
    _print_stats("runtime cache", runtime_cache_root)
    _print_stats("host cache", host_cache_root)


def save_cache(
    runtime_cache_root: Path = DEFAULT_RUNTIME_CACHE_ROOT,
    host_cache_root: Path = DEFAULT_HOST_CACHE_ROOT,
) -> None:
    host_cache_root.mkdir(parents=True, exist_ok=True)

    if runtime_cache_root.is_symlink():
        if runtime_cache_root.resolve(strict=False) != host_cache_root.resolve():
            raise ValueError(f"Expected {runtime_cache_root} to point to {host_cache_root}")
    else:
        shutil.rmtree(host_cache_root)
        shutil.copytree(runtime_cache_root, host_cache_root, symlinks=True, copy_function=shutil.copy2)

    _print_stats("runtime cache", runtime_cache_root)
    _print_stats("host cache", host_cache_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Docker runtime cache with a mounted host cache")
    parser.add_argument("command", choices=["prepare", "save"])
    args = parser.parse_args()

    if DEFAULT_RUNTIME_CACHE_ROOT != Path("/workspace/.cache") or DEFAULT_HOST_CACHE_ROOT != Path("/cache-host"):
        raise AssertionError("Unexpected default cache paths")
    if not _is_docker_context():
        raise RuntimeError("docker cache sync is only supported inside Docker containers")

    if args.command == "prepare":
        prepare_cache()
    else:
        save_cache()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
