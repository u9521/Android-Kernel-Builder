# AGENTS.md

Guidance for coding agents working in `Android-Kernel-Builder`.

## Scope

- Python 3.11+ project with CLI entry point `akb`.
- Two execution modes:
  - commands run from the project root as the work root
  - Docker runtime commands run from `/workspace`, which is the project root inside images
- Prefer small, behavior-preserving edits unless the task clearly needs a larger refactor.

## Repository Rules Status

- No repo-local Cursor rules were found in `.cursor/rules/`.
- No `.cursorrules` file was found.
- No Copilot instructions file was found at `.github/copilot-instructions.md`.
- Follow existing code, tests, and docs when this file does not answer something directly.

## Project Layout

- Source package: `android_kernel_builder/builder/`
- Tests: `android_kernel_builder/tests/`
- Checked-in target inputs: `android_kernel_builder/configs/targets/`
- Checked-in manifests: `android_kernel_builder/configs/manifests/`
- Dockerfiles and entrypoint: `android_kernel_builder/docker/`
- Reference docs: `android_kernel_builder/docs/`

## Setup Commands

- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Install editable package with dev deps: `uv sync --dev`

## Common Commands

- CLI help: `uv run akb --help`
- Show target: `uv run show-target --target android15-6.6`
- Sync source: `uv run sync-source --target android15-6.6`
- Build target: `uv run build --target android15-6.6`
- Warm caches: `uv run warmup-build --target android15-6.6`
- Build Docker base image: `uv run build-docker build-base --tag ghcr.io/<owner>/gki-base:bookworm`
- Build Docker workspace image: `uv run build-docker build-workspace --tag <tag> --base-image <base> --target android15-6.6`
- Build Docker snapshot image: `uv run build-docker build-snapshot --tag <tag> --base-image <base> --target android15-6.6`

## Test Commands

- Full suite: `uv run python -m unittest discover -s android_kernel_builder/tests`
- Focused subset: `uv run python -m unittest discover -s android_kernel_builder/tests -p 'test_target_store.py'`
- Single module: `uv run python -m unittest android_kernel_builder.tests.test_install_script`
- Single class: `uv run python -m unittest android_kernel_builder.tests.test_build.BuildUsageTests`
- Single test: `uv run python -m unittest android_kernel_builder.tests.test_build.BuildUsageTests.test_warmup_kernel_uses_bazel_build_for_warmup_target`

## Lint / Type Check

- Preferred static check: `pyright` (install separately, e.g. `npm install -g pyright`)
- Pyright configuration lives in `pyproject.toml` under `[tool.pyright]`.
- No repo-local Ruff/Black/isort/Flake8 config exists right now.

## Change-Specific Verification

- Start with the smallest relevant `unittest` target.
- If you change CLI argument handling, run `uv run python -m unittest android_kernel_builder.tests.test_cli`.
- If you change host/docker layout resolution, run:
  - `uv run python -m unittest android_kernel_builder.tests.test_layout android_kernel_builder.tests.test_target_store`
- If you change Docker packaging or runtime layout, run:
  - `uv run python -m unittest android_kernel_builder.tests.test_image_env android_kernel_builder.tests.test_image_package android_kernel_builder.tests.test_docker android_kernel_builder.tests.test_snapshot`

## Architecture Notes

- Keep host and docker behavior clearly separated.
- Do not assume the build system enum is fixed to current values; design parser/validation/branching so additional build systems can be introduced without broad rewrites.
- Commands use the current working directory as the work root.
- Docker runtime always runs from `/workspace`.
- Target configs live under `android_kernel_builder/configs/targets/<name>.toml`.
- Docker runtime uses `AKB_TARGET` and the same target config layout under `/workspace`.
- Metadata directories are fixed by layout constants and must not be user-configurable.

## File Creation Rules

- New Python and shell files should start with:
  - `# SPDX-License-Identifier: GPL-3.0-only`
  - `# Copyright (C) 2026 u9521`
- In Python files, put `from __future__ import annotations` immediately after the header.

## Imports

- Order imports as:
  1. future import
  2. standard library imports
  3. local package imports
- Use explicit imports; avoid wildcard imports.
- Use relative imports inside `android_kernel_builder.builder`.

## Formatting

- Use 4-space indentation.
- Keep functions focused and avoid unrelated refactors.
- Preserve existing blank-line spacing between top-level definitions.
- Prefer double quotes in Python unless the surrounding file clearly differs.
- Prefer `Path` operations over manual string path building.
- Write JSON as `json.dumps(..., indent=2, sort_keys=True) + "\n"`.

## Types

- Add type hints to public functions and new helpers.
- Prefer concrete types such as `Path`, `list[str]`, and `dict[str, object]`.
- Use Python 3.11 union syntax like `str | None`.
- Dataclass-based config containers typically use `@dataclass(slots=True)`.

## Naming

- `snake_case` for modules, functions, and variables.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for constants.
- Prefix internal helpers with `_`.
- Use AKB-specific names precisely: `work_root`, `cache_root`, `output_root`, `target_name`, `config_path`.

## Error Handling

- Raise `ValueError` for invalid config content and unsupported option values.
- Raise `FileNotFoundError` for missing required files or directories.
- Keep error messages explicit and include the offending field or path when possible.
- Fail fast during parsing and validation instead of carrying invalid state forward.

## Subprocess and Environment

- Prefer `run_command()` from `android_kernel_builder/builder/utils.py` for shelling out.
- Pass structured argument lists, not shell strings.
- Use explicit `cwd=Path(...)` and environment dictionaries instead of `os.chdir()`.

## Path and Layout Safety

- Treat host and docker layout paths as fixed, not configurable.
- Reject absolute paths or `..` segments when values must stay inside the AKB root.
- Prefer helpers from `android_kernel_builder/builder/layout.py` instead of duplicating path logic.

## Testing Style

- Use `unittest.TestCase`.
- Test file names should be `tests/test_<feature>.py`.
- Test method names should be descriptive, usually `test_<behavior>`.
- Use `tempfile.TemporaryDirectory()` and `Path` for filesystem tests.
- Use `unittest.mock` to isolate subprocesses and heavy operations.

## Docs and CLI Changes

- If you change commands, flags, or workflow shape, update `README.md`, `android_kernel_builder/docs/akb-cli.md`, and any affected docs.
- Keep terminology aligned with the current model:
  - use `sync-source`, not `prepare-workspace`
  - use `source target file` for repo-side Docker build inputs
  - use `AKB_TARGET` for embedded Docker runtime target selection

## Agent Tips

- Read the nearest tests before changing behavior.
- Prefer extending an existing helper over introducing a parallel abstraction.
- Preserve current user-facing wording unless the task requires a wording change.
- Do not add backward-compatibility shims for removed legacy behavior unless explicitly requested.
