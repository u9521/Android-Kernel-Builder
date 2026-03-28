#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import cast

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src").resolve()))

from gki_builder.targets import load_target_payload_with_inheritance


def _run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _safe_run(command: list[str]) -> str:
    try:
        return _run(command)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _safe_int(value: str | int | object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "N/A"
    minutes, remain = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {remain}s"
    if minutes > 0:
        return f"{minutes}m {remain}s"
    return f"{remain}s"


def _image_repository(image_ref: str) -> str:
    if not image_ref:
        return ""
    if "@" in image_ref:
        return image_ref.split("@", 1)[0]
    if ":" in image_ref and image_ref.rfind(":") > image_ref.rfind("/"):
        return image_ref.rsplit(":", 1)[0]
    return image_ref


def _image_tag(image_ref: str) -> str:
    if not image_ref or "@" in image_ref:
        return "N/A"
    if ":" in image_ref and image_ref.rfind(":") > image_ref.rfind("/"):
        return image_ref.rsplit(":", 1)[1]
    return "N/A"


def _extract_digest(value: str) -> str:
    if not value:
        return ""
    if "@sha256:" in value:
        return value.split("@", 1)[1].strip()
    if value.startswith("sha256:"):
        return value.strip()
    return ""


def _resolve_image_digest(image_ref: str) -> str:
    if not image_ref:
        return ""

    digest = _extract_digest(_safe_run(["docker", "buildx", "imagetools", "inspect", image_ref, "--format", "{{.Digest}}"]))
    if digest:
        return digest

    repo_digest = _safe_run(["docker", "image", "inspect", image_ref, "--format", "{{index .RepoDigests 0}}"])
    digest = _extract_digest(repo_digest)
    if digest:
        return digest

    inspect_text = _safe_run(["docker", "buildx", "imagetools", "inspect", image_ref])
    for line in inspect_text.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("Digest:"):
            continue
        candidate = trimmed.split(":", 1)[1].strip()
        digest = _extract_digest(candidate)
        if digest:
            return digest

    return ""


def _load_target_payload(source_target_file: str) -> dict[str, object]:
    if not source_target_file:
        return {}
    target_path = Path(source_target_file)
    if not target_path.exists():
        return {}
    payload, _ = load_target_payload_with_inheritance(target_path)
    return payload


def _resolve_summary_path(summary_file: str | None) -> Path:
    if summary_file:
        return Path(summary_file)
    env_path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if env_path:
        return Path(env_path)
    raise ValueError("Missing summary file path; pass --summary-file or set GITHUB_STEP_SUMMARY")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write CI image/kernel summary into GitHub step summary")
    parser.add_argument("--image-ref", default="")
    parser.add_argument("--source-target-file", default="")
    parser.add_argument("--target-input", default="")
    parser.add_argument("--build-duration-seconds", default="0")
    parser.add_argument("--build-step-outcome", default="")
    parser.add_argument("--summary-file", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary_path = _resolve_summary_path(args.summary_file)

    image_ref = args.image_ref
    source_target_file = args.source_target_file
    target_input = args.target_input
    build_step_outcome = args.build_step_outcome
    build_duration_seconds = _safe_int(args.build_duration_seconds)

    image_digest = ""
    if image_ref:
        image_digest = _resolve_image_digest(image_ref)

    target_payload = _load_target_payload(source_target_file)
    target_name = str(target_payload.get("name") or target_input)
    manifest_payload_obj = target_payload.get("manifest")
    if isinstance(manifest_payload_obj, dict):
        manifest_payload: dict[str, object] = cast(dict[str, object], manifest_payload_obj)
    else:
        manifest_payload = {}
    build_payload_obj = target_payload.get("build")
    if isinstance(build_payload_obj, dict):
        build_payload: dict[str, object] = cast(dict[str, object], build_payload_obj)
    else:
        build_payload = {}

    kernel_branch = str(manifest_payload.get("branch") or "")

    build_system = str(build_payload.get("system") or "N/A")
    dist_dir = str(build_payload.get("dist_dir") or target_name or "N/A")

    push_status = "success" if build_step_outcome == "success" else "failed"
    image_repository = _image_repository(image_ref) or "N/A"
    image_tag = _image_tag(image_ref)

    lines = [
        "## Image Metadata",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Image | `{image_repository}` |",
        f"| Tags | `{image_tag}` |",
        f"| Digest | `{image_digest or 'N/A'}` |",
        f"| Build Duration | `{_format_duration(build_duration_seconds)}` |",
        f"| Push | `{push_status}` |",
        f"| Branch | `{os.environ.get('GITHUB_REF_NAME', 'N/A')}` |",
        f"| Commit | `{os.environ.get('GITHUB_SHA', 'N/A')}` |",
        "",
        "## Build Configuration",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Source Target File | `{source_target_file or 'N/A'}` |",
        f"| Requested Target Input | `{target_input or 'N/A'}` |",
        f"| Target Name | `{target_name or 'N/A'}` |",
        f"| Kernel Branch/Tag | `{kernel_branch or 'N/A'}` |",
        f"| Build System | `{build_system or 'N/A'}` |",
        f"| Default Dist Dir | `{dist_dir or 'N/A'}` |",
        "",
    ]

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
