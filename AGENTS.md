# AGENTS.md

Guidance for coding agents working in `Android-Kernel-Builder`.

## Scope

- Python 3.11+ project with CLI entry point `gki-builder`.
- Two execution modes:
  - host mode rooted at `{work}/.akb`
  - docker mode rooted at `/workspace`
- Prefer small, behavior-preserving edits unless the task clearly needs a larger refactor.

## Repository Rules Status

- No repo-local Cursor rules were found in `.cursor/rules/`.
- No `.cursorrules` file was found.
- No Copilot instructions file was found at `.github/copilot-instructions.md`.
- Follow existing code, tests, and docs when this file does not answer something directly.

## Project Layout

- Source package: `src/gki_builder/`
- Tests: `tests/`
- Checked-in target inputs: `configs/targets/`
- Checked-in manifests: `manifests/`
- Dockerfiles and entrypoint: `docker/`
- Reference docs: `docs/`

## Setup Commands

- Install editable package: `python3 -m pip install -e .`
- Optional import-path setup: `export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:${PYTHONPATH}}"`
- Initialize a host AKB environment: `bash install.sh`

## Common Commands

- CLI help: `python3 -m gki_builder.cli --help`
- Show target: `python3 -m gki_builder.cli show-target --target android15-6.6`
- Sync source: `python3 -m gki_builder.cli sync-source --target android15-6.6`
- Build target: `python3 -m gki_builder.cli build --target android15-6.6 --output-root out`
- Warm caches: `python3 -m gki_builder.cli warmup-build --target android15-6.6 --output-root out`
- Build Docker base image: `python3 -m gki_builder.cli docker-build-base --tag ghcr.io/<owner>/gki-base:bookworm`
- Build Docker workspace image: `python3 -m gki_builder.cli docker-build-workspace --tag <tag> --base-image <base> --target android15-6.6`
- Build Docker snapshot image: `python3 -m gki_builder.cli docker-build-snapshot --tag <tag> --base-image <base> --target android15-6.6`

## Test Commands

- Full suite: `python3 -m unittest`
- Focused subset: `python3 -m unittest tests.test_config tests.test_environment tests.test_target_store`
- Single module: `python3 -m unittest tests.test_install_script`
- Single class: `python3 -m unittest tests.test_build.BuildUsageTests`
- Single test: `python3 -m unittest tests.test_build.BuildUsageTests.test_warmup_kernel_uses_bazel_build_for_warmup_target`

## Lint / Type Check

- Preferred static check if installed: `pyright`
- `pyrightconfig.json` includes both `src` and `tests`.
- No repo-local Ruff/Black/isort/Flake8 config exists right now.

## Change-Specific Verification

- Start with the smallest relevant `unittest` target.
- If you change CLI argument handling, run `python3 -m unittest tests.test_cli`.
- If you change host/docker environment or layout resolution, run:
  - `python3 -m unittest tests.test_layout tests.test_environment tests.test_config tests.test_active_target tests.test_target_store`
- If you change Docker packaging or runtime layout, run:
  - `python3 -m unittest tests.test_image_env tests.test_image_package tests.test_docker tests.test_snapshot`

## Architecture Notes

- Keep host and docker behavior clearly separated.
- Host discovery walks upward until `.akb/config.toml` is found.
- Docker runtime always uses the fixed root `/workspace`.
- Host targets live under `.akb/targets/configs/<name>.toml`.
- Docker runtime uses `.akb/active-target.toml`.
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
- Use relative imports inside `gki_builder`.
- In tests, follow the existing pattern of inserting `src` into `sys.path` and using `importlib.import_module(...)`.

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

- Prefer `run_command()` from `src/gki_builder/utils.py` for shelling out.
- Pass structured argument lists, not shell strings.
- Use explicit `cwd=Path(...)` and environment dictionaries instead of `os.chdir()`.

## Path and Layout Safety

- Treat host and docker layout paths as fixed, not configurable.
- Reject absolute paths or `..` segments when values must stay inside the AKB root.
- Prefer helpers from `src/gki_builder/layout.py` instead of duplicating path logic.

## Testing Style

- Use `unittest.TestCase`.
- Test file names should be `tests/test_<feature>.py`.
- Test method names should be descriptive, usually `test_<behavior>`.
- Use `tempfile.TemporaryDirectory()` and `Path` for filesystem tests.
- Use `unittest.mock` to isolate subprocesses and heavy operations.

## Docs and CLI Changes

- If you change commands, flags, or workflow shape, update `README.md`, `docs/gki-builder-cli.md`, and any affected docs.
- Keep terminology aligned with the current model:
  - use `sync-source`, not `prepare-workspace`
  - use `source target file` for repo-side Docker build inputs
  - use `active target` for embedded Docker runtime config

## Agent Tips

- Read the nearest tests before changing behavior.
- Prefer extending an existing helper over introducing a parallel abstraction.
- Preserve current user-facing wording unless the task requires a wording change.
- Do not add backward-compatibility shims for removed legacy behavior unless explicitly requested.
