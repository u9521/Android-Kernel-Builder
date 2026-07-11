# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from pathlib import Path


def rewrite_manifest_revisions(
    manifest_path: Path,
    original_branch: str,
    replacement_branch: str,
) -> bool:
    original_text = manifest_path.read_text(encoding="utf-8")
    updated_text = original_text.replace(
        f'"{original_branch}"',
        f'"{replacement_branch}"',
    )
    if updated_text == original_text:
        return False
    manifest_path.write_text(updated_text, encoding="utf-8")
    print(
        f"rewrote manifest revisions in {manifest_path} from {original_branch} to {replacement_branch}",
        flush=True,
    )
    return True
