# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..utils import run_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AKB maintenance tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    git_safe = subparsers.add_parser("add-git-safe", help="Add directories to global Git safe.directory")
    git_safe.add_argument("path", help="Directory path to add")
    git_safe.add_argument("-r", "--recursive", action="store_true", help="Also add child Git repositories")
    git_safe.set_defaults(handler=handle_add_git_safe)

    return parser


def handle_add_git_safe(args: argparse.Namespace) -> int:
    input_path = Path(args.path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Path does not exist: {input_path}")
    if not input_path.is_dir():
        raise ValueError(f"Path must be a directory: {input_path}")

    global_safe_directories = _load_git_safe_directories(system=False)
    system_safe_directories = _load_git_safe_directories(system=True)
    candidates = _collect_git_safe_candidates(input_path, args.recursive)

    global_added: list[Path] = []
    global_skipped: list[Path] = []
    system_added: list[Path] = []
    system_skipped: list[Path] = []
    for candidate in candidates:
        candidate_text = str(candidate)

        if candidate_text in global_safe_directories:
            global_skipped.append(candidate)
        else:
            run_command(
                ["git", "config", "--global", "--add", "safe.directory", candidate_text],
                capture_output=True,
            )
            global_safe_directories.add(candidate_text)
            global_added.append(candidate)

        if candidate_text in system_safe_directories:
            system_skipped.append(candidate)
        else:
            run_command(
                ["git", "config", "--system", "--add", "safe.directory", candidate_text],
                capture_output=True,
            )
            system_safe_directories.add(candidate_text)
            system_added.append(candidate)

    print(f"Global: added {len(global_added)} safe.directory entries")
    for path in global_added:
        print(f"  + {path}")
    print(f"Global: skipped {len(global_skipped)} existing safe.directory entries")
    for path in global_skipped:
        print(f"  = {path}")

    print(f"System: added {len(system_added)} safe.directory entries")
    for path in system_added:
        print(f"  + {path}")
    print(f"System: skipped {len(system_skipped)} existing safe.directory entries")
    for path in system_skipped:
        print(f"  = {path}")
    return 0


def _load_git_safe_directories(*, system: bool) -> set[str]:
    scope = "--system" if system else "--global"
    result = run_command(
        ["git", "config", scope, "--get-all", "safe.directory"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return set()
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return set(lines)


def _collect_git_safe_candidates(root_path: Path, recursive: bool) -> list[Path]:
    candidates: list[Path] = [root_path]
    if recursive:
        for current_root, dirnames, _ in os.walk(root_path):
            current_path = Path(current_root)
            if current_path == root_path:
                continue
            if ".git" in dirnames:
                candidates.append(current_path.resolve())
                dirnames.remove(".git")
    return _dedupe_paths(candidates)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        text = str(path)
        if text in seen:
            continue
        seen.add(text)
        unique.append(path)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
