#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'install.sh supports Linux hosts only.\n' >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf 'install.sh requires python3.\n' >&2
    exit 1
fi

repo_root="${AKB_INSTALLER_REPO_ROOT:-}"
if [[ -z "${repo_root}" && -n "${BASH_SOURCE[0]:-}" && -e "${BASH_SOURCE[0]}" ]]; then
    script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    if [[ -d "${script_dir}/configs/targets" && -d "${script_dir}/manifests" ]]; then
        repo_root="${script_dir}"
    fi
fi

export AKB_INSTALL_WORK_ROOT="$(pwd -P)"
export AKB_INSTALL_REPO_ROOT="${repo_root}"

python3 - <<'PY'
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import sys


DEFAULT_SOURCE_DIR = "android-kernel"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_OUTPUT_DIR = "out"
PREFERRED_DEFAULT_TARGET = "android15-6.6"
GITIGNORE_ENTRIES = (".akb/bin/", ".akb/venv/")


def validate_relative_path(value: str, field_name: str) -> str:
    candidate = Path(value)
    if not value or candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise SystemExit(f"Invalid {field_name}: path must stay inside the current work root")
    return value


def normalize_manifest_path_references(text: str) -> str:
    return re.sub(r'(?m)^(\s*path\s*=\s*")manifests/', r'\1', text)


def seed_directory(source_root: Path, destination_root: Path) -> int:
    copied = 0
    for source_path in sorted(source_root.rglob("*")):
        relative_path = source_path.relative_to(source_root)
        destination_path = destination_root / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        if destination_path.exists():
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied += 1
    return copied


def seed_target_configs(source_root: Path, destination_root: Path) -> tuple[int, list[str]]:
    copied = 0
    available_targets: list[str] = []
    for source_path in sorted(source_root.glob("*.toml")):
        destination_path = destination_root / source_path.name
        if not destination_path.exists():
            destination_path.write_text(
                normalize_manifest_path_references(source_path.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            copied += 1
        available_targets.append(destination_path.stem)
    return copied, available_targets


def choose_default_target(available_targets: list[str]) -> str | None:
    configured = os.environ.get("AKB_DEFAULT_TARGET", "").strip()
    if configured:
        return configured
    if PREFERRED_DEFAULT_TARGET in available_targets:
        return PREFERRED_DEFAULT_TARGET
    if len(available_targets) == 1:
        return available_targets[0]
    return None


def render_config(*, default_target: str | None, source_dir: str, cache_dir: str, output_dir: str) -> str:
    lines = ["version = 1"]
    if default_target:
        lines.append(f'default_target = "{default_target}"')
    lines.extend(
        [
            "",
            "[workspace]",
            f'source_dir = "{source_dir}"',
            f'cache_dir = "{cache_dir}"',
            f'output_dir = "{output_dir}"',
            "",
            "[build]",
            'jobs = 0',
            'lto = "thin"',
            "",
        ]
    )
    return "\n".join(lines)


def ensure_targets_symlink(work_root: Path, targets_root: Path) -> None:
    targets_link = work_root / "targets"
    if not targets_link.exists() and not targets_link.is_symlink():
        targets_link.symlink_to(Path(".akb") / "targets", target_is_directory=True)
        return
    if not targets_link.is_symlink():
        raise SystemExit(f"Refusing to replace non-symlink path: {targets_link}")
    if targets_link.resolve() != targets_root.resolve():
        raise SystemExit(f"Refusing to replace unexpected targets symlink: {targets_link}")


def update_gitignore(work_root: Path) -> None:
    gitignore_path = work_root / ".gitignore"
    existing_lines = []
    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    missing_entries = [entry for entry in GITIGNORE_ENTRIES if entry not in existing_lines]
    if not missing_entries:
        return
    lines = list(existing_lines)
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(missing_entries)
    gitignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    work_root = Path(os.environ["AKB_INSTALL_WORK_ROOT"]).resolve()
    repo_root_value = os.environ.get("AKB_INSTALL_REPO_ROOT", "").strip()
    repo_root = Path(repo_root_value).resolve() if repo_root_value else None

    source_dir = validate_relative_path(os.environ.get("AKB_SOURCE_DIR", DEFAULT_SOURCE_DIR).strip(), "AKB_SOURCE_DIR")
    cache_dir = validate_relative_path(os.environ.get("AKB_CACHE_DIR", DEFAULT_CACHE_DIR).strip(), "AKB_CACHE_DIR")
    output_dir = validate_relative_path(os.environ.get("AKB_OUTPUT_DIR", DEFAULT_OUTPUT_DIR).strip(), "AKB_OUTPUT_DIR")

    akb_root = work_root / ".akb"
    targets_root = akb_root / "targets"
    target_configs_root = targets_root / "configs"
    target_manifests_root = targets_root / "manifests"
    akb_bin_root = akb_root / "bin"
    config_path = akb_root / "config.toml"

    target_configs_root.mkdir(parents=True, exist_ok=True)
    target_manifests_root.mkdir(parents=True, exist_ok=True)
    akb_bin_root.mkdir(parents=True, exist_ok=True)
    (work_root / cache_dir).mkdir(parents=True, exist_ok=True)
    (work_root / output_dir).mkdir(parents=True, exist_ok=True)

    ensure_targets_symlink(work_root, targets_root)

    copied_targets = 0
    copied_manifests = 0
    available_targets = sorted(path.stem for path in target_configs_root.glob("*.toml"))
    if repo_root is not None:
        source_targets_root = repo_root / "configs" / "targets"
        source_manifests_root = repo_root / "manifests"
        if source_targets_root.is_dir():
            copied_targets, available_targets = seed_target_configs(source_targets_root, target_configs_root)
            available_targets = sorted(set(available_targets) | {path.stem for path in target_configs_root.glob("*.toml")})
        if source_manifests_root.is_dir():
            copied_manifests = seed_directory(source_manifests_root, target_manifests_root)

    if not config_path.exists():
        config_path.write_text(
            render_config(
                default_target=choose_default_target(available_targets),
                source_dir=source_dir,
                cache_dir=cache_dir,
                output_dir=output_dir,
            ),
            encoding="utf-8",
        )

    update_gitignore(work_root)

    print(f"Initialized AKB host environment at {work_root}")
    print(f"- config: {config_path}")
    print(f"- targets link: {work_root / 'targets'} -> .akb/targets")
    print(f"- seeded target configs: {copied_targets}")
    print(f"- seeded manifests: {copied_manifests}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY
