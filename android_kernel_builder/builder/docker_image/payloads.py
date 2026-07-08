# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 u9521

from __future__ import annotations

from typing import cast


def clone_mapping(value: object) -> object:
    if isinstance(value, dict):
        return {key: clone_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clone_mapping(item) for item in value]
    return value


def dump_toml_document(payload: dict[str, object]) -> str:
    lines: list[str] = []
    root_scalars = {key: value for key, value in payload.items() if not isinstance(value, dict)}
    sections = {key: value for key, value in payload.items() if isinstance(value, dict)}

    for key, value in root_scalars.items():
        lines.append(f"{key} = {dump_toml_value(value)}")

    if root_scalars and sections:
        lines.append("")

    section_names = list(sections.keys())
    for index, section_name in enumerate(section_names):
        lines.append(f"[{section_name}]")
        section = cast(dict[str, object], sections[section_name])
        for key, value in section.items():
            lines.append(f"{key} = {dump_toml_value(value)}")
        if index != len(section_names) - 1:
            lines.append("")

    return "\n".join(lines) + "\n"


def dump_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return '""'
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(dump_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value type: {type(value)!r}")
