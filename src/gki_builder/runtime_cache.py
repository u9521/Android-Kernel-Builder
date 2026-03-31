# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from . import layout
from .utils import ensure_directory, run_command, sha256_file, write_json

DEFAULT_OUTER_CACHE_SIZE_BYTES = 10 * 1024 * 1024 * 1024
def init_runtime_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    container_metadata = _load_required_metadata(layout.docker_container_cache_metadata_file(work_root))
    outerimage_root = ensure_directory(layout.docker_outerimage_root(work_root))
    ensure_directory(layout.docker_overlays_root(work_root))
    ensure_directory(layout.cache_root(work_root))

    lower_root = ensure_directory(layout.docker_overlay_lower_root(work_root))
    upper_root = ensure_directory(layout.docker_overlay_upper_root(work_root))

    _safe_umount(layout.cache_root(work_root))
    _safe_umount(upper_root)
    _safe_umount(lower_root)

    outer_cache_path = layout.docker_outer_cache_image(work_root)
    outer_metadata_path = layout.docker_outer_cache_metadata_file(work_root)
    outer_metadata = _load_optional_metadata(outer_metadata_path)
    if not _outer_cache_matches(container_metadata, outer_metadata) or not outer_cache_path.exists():
        _create_empty_outer_cache_image(work_root, container_metadata)

    run_command([
        "mount",
        "-v",
        "-o",
        "loop,ro",
        str(layout.docker_container_cache_image(work_root)),
        str(lower_root),
    ])
    run_command([
        "mount",
        "-v",
        "-o",
        "loop",
        str(outer_cache_path),
        str(upper_root),
    ])
    run_command([
        "mount",
        "-v",
        "-t",
        "overlay",
        "overlay",
        "-o",
        "lowerdir="
        + str(lower_root)
        + ",upperdir="
        + str(upper_root / "upper")
        + ",workdir="
        + str(upper_root / "work"),
        str(layout.cache_root(work_root)),
    ])


def cleanup_runtime_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    _safe_umount(layout.cache_root(work_root))
    _safe_umount(layout.docker_overlay_upper_root(work_root))
    _safe_umount(layout.docker_overlay_lower_root(work_root))


def finalize_runtime_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    cleanup_runtime_cache(work_root)
    export_runtime_cache(work_root)


def export_runtime_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    outer_cache_path = layout.docker_outer_cache_image(work_root)
    outer_metadata_path = layout.docker_outer_cache_metadata_file(work_root)
    next_outer_cache_path = layout.docker_next_outer_cache_image(work_root)
    next_outer_metadata_path = layout.docker_next_outer_cache_metadata_file(work_root)

    if not outer_cache_path.exists() or not outer_metadata_path.exists():
        raise FileNotFoundError("outer cache image and metadata must exist before export")

    run_command(["e2fsck", "-fy", str(outer_cache_path)])
    run_command(["resize2fs", "-M", str(outer_cache_path)])
    _remove_path(next_outer_cache_path)
    _remove_path(next_outer_metadata_path)
    _rename_path(outer_cache_path, next_outer_cache_path)
    _rename_path(outer_metadata_path, next_outer_metadata_path)


def prepare_base_container_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    cache_root = ensure_directory(layout.cache_root(work_root))
    lower_root = ensure_directory(layout.docker_overlay_lower_root(work_root))
    container_cache_path = layout.docker_container_cache_image(work_root)

    _safe_umount(cache_root)
    _safe_umount(lower_root)
    _remove_path(container_cache_path)
    run_command(["truncate", "-s", str(DEFAULT_OUTER_CACHE_SIZE_BYTES), str(container_cache_path)])
    run_command(["mkfs.ext4", "-F", str(container_cache_path)])
    run_command(["mount", "-v", "-o", "loop", str(container_cache_path), str(cache_root)])


def pack_container_cache(work_root: Path = layout.DOCKER_WORK_ROOT) -> None:
    cache_root = layout.cache_root(work_root)
    container_cache_path = layout.docker_container_cache_image(work_root)
    metadata_path = layout.docker_container_cache_metadata_file(work_root)
    image_info = _load_optional_metadata(layout.docker_image_info_file(work_root)) or {}

    _safe_umount(cache_root)
    _remove_path(metadata_path)
    run_command(["e2fsck", "-fy", str(container_cache_path)])
    run_command(["resize2fs", "-M", str(container_cache_path)])
    write_json(
        metadata_path,
        {
            "version": 1,
            "cache_layout_version": 1,
            "target": image_info.get("target", ""),
            "container_cache_sha256": sha256_file(container_cache_path),
        },
    )


def _load_required_metadata(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Required runtime cache metadata not found: {path}")
    return _load_optional_metadata(path) or {}


def _load_optional_metadata(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Runtime cache metadata must be a mapping: {path}")
    return payload


def _outer_cache_matches(container_metadata: dict[str, object], outer_metadata: dict[str, object] | None) -> bool:
    if outer_metadata is None:
        return False
    return (
        outer_metadata.get("cache_layout_version") == container_metadata.get("cache_layout_version")
        and outer_metadata.get("container_cache_sha256") == container_metadata.get("container_cache_sha256")
        and outer_metadata.get("target") == container_metadata.get("target")
    )


def _create_empty_outer_cache_image(
    work_root: Path,
    container_metadata: dict[str, object],
    *,
    size_bytes: int = DEFAULT_OUTER_CACHE_SIZE_BYTES,
) -> None:
    outer_cache_path = layout.docker_outer_cache_image(work_root)
    outer_metadata_path = layout.docker_outer_cache_metadata_file(work_root)
    upper_root = ensure_directory(layout.docker_overlay_upper_root(work_root))

    _safe_umount(upper_root)
    _remove_path(outer_cache_path)
    _remove_path(outer_metadata_path)
    ensure_directory(outer_cache_path.parent)

    run_command(["truncate", "-s", str(size_bytes), str(outer_cache_path)])
    run_command(["mkfs.ext4", "-F", str(outer_cache_path)])
    run_command(["mount", "-v", "-o", "loop", str(outer_cache_path), str(upper_root)])
    try:
        ensure_directory(upper_root / "upper")
        ensure_directory(upper_root / "work")
    finally:
        run_command(["umount", "-v", str(upper_root)], check=False)

    write_json(
        outer_metadata_path,
        {
            "version": 1,
            "cache_layout_version": container_metadata.get("cache_layout_version", 1),
            "target": container_metadata.get("target", ""),
            "container_cache_sha256": container_metadata.get("container_cache_sha256", ""),
        },
    )


def _safe_umount(path: Path) -> None:
    if not _is_mountpoint(path):
        return
    run_command(["umount", "-v", str(path)], check=False)


def _is_mountpoint(path: Path) -> bool:
    mounts_path = Path("/proc/self/mounts")
    if not mounts_path.exists():
        return False
    mount_target = str(path)
    for line in mounts_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] == mount_target:
            return True
    return False


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        print(f"+ rm -vf {path}", flush=True)
        path.unlink()
        return
    if path.is_dir():
        print(f"+ rm -rvf {path}", flush=True)
        shutil.rmtree(path)


def _rename_path(source: Path, destination: Path) -> None:
    ensure_directory(destination.parent)
    print(f"+ mv -v {source} {destination}", flush=True)
    source.rename(destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Docker runtime cache mounts and exports")
    parser.add_argument("command", choices=["init", "cleanup", "export", "finalize", "prepare-base", "pack-base"])
    parser.add_argument("--work-root", default=str(layout.DOCKER_WORK_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    work_root = Path(args.work_root).resolve()
    if args.command == "init":
        init_runtime_cache(work_root)
    elif args.command == "cleanup":
        cleanup_runtime_cache(work_root)
    elif args.command == "finalize":
        finalize_runtime_cache(work_root)
    elif args.command == "prepare-base":
        prepare_base_container_cache(work_root)
    elif args.command == "pack-base":
        pack_container_cache(work_root)
    else:
        export_runtime_cache(work_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
