# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.9] - 2026-05-07

### Added
- CI now runs package build, `twine check`, and CLI smoke checks after the Python test matrix.
- Added `test_version_consistency` to prevent `pyproject.toml` and `skills_orchestrator.__version__` from drifting again.

### Changed
- Updated README runtime model documentation: `AGENTS.md` is bootstrap guidance, MCP is runtime skill loading, and Pipeline is runtime workflow orchestration.
- Reworked README roadmap from stale v1.x milestones to the current v2.x stabilization and runtime roadmap.
- Filled the missing v2.0.1-v2.0.8 release notes in this changelog.

### Fixed
- Closed the remaining release-engineering gap where reports and package versions were current but CHANGELOG/README/CI protection lagged behind.

## [2.0.8] - 2026-05-07

### Fixed
- Aligned release bookkeeping after v2.0.7 and backfilled the v2.0.7 test report commit.
- Kept package metadata, CLI version output, GitHub release, and PyPI publication aligned.

## [2.0.7] - 2026-05-07

### Security
- Added regression tests for malicious skill IDs in Parser and sync targets.
- Restored safe Unicode/Chinese skill IDs while continuing to reject path separators, dot segments, and unsafe punctuation.
- Added regression coverage for arbitrary `skill_dirs` environment-variable rejection and `SKILLS_ROOT` allow-list behavior.

### Fixed
- Aligned `pyproject.toml` and `skills_orchestrator.__version__`.
- Added Pipeline validation for unreachable steps so disconnected multi-step pipelines are reported instead of silently completing after the first step.
- Normalized YAML scalar `next: step_id` to `next: [step_id]`.

## [2.0.6] - 2026-05-07

### Security
- Patched path traversal via malicious `skill_id` in Hermes, OpenClaw, and Cursor sync targets.
- Restricted `skill_dirs` environment variable expansion to `SKILLS_ROOT`.
- Tightened explicit `skills[].path` environment variable checks.

### Known Follow-Up
- Shipped with package metadata at 2.0.6 while CLI `--version` still reported 2.0.5; fixed in v2.0.7.
- Security tests for this patch were added in v2.0.7.

## [2.0.5] - 2026-05-07

### Security
- Hardened MCP and Pipeline path handling for `skill_id`, `pipeline_id`, `run_id`, and `.latest` references.
- Added MCP tool argument shape validation and numeric bounds for `top_k` / `max_combos`.
- Tightened parser path resolution for explicit `skill.path` and `SKILLS_ROOT`.

### Changed
- Replaced recursive Pipeline auto-skip with an iterative loop for deep pipelines.
- Added keyword search token caching for faster repeated/high-volume searches.
- Added Windows console compatibility for GBK terminals and explicit UTF-8 subprocess decoding.

## [2.0.4] - 2026-05-05

### Security
- Hardened GitHub import downloads with size, UTF-8, empty-content, and malformed-frontmatter checks.
- Preserved compatibility for Markdown without frontmatter when metadata can be inferred.

### Fixed
- Improved base inheritance cycle diagnostics with the full cycle chain.
- Added regression coverage for sync generated-overwrite behavior.

## [2.0.3] - 2026-05-04

### Added
- Added high-frequency CLI smoke coverage for main user-facing commands.

### Changed
- Strengthened release validation with build, twine check, and CLI version checks.

## [2.0.2] - 2026-05-04

### Added
- Added mocked GitHub import command tests for blob/raw URL conversion, allow-listing, network errors, invalid markdown, and traversal cases.
- Added independent release test report indexing.

### Fixed
- Split migrated init/import command implementations out of `main.py` registration paths.
- Ensured packaged `tag_categories.yaml` is read through `importlib.resources`.
- Made `mcp-test get_skill` return a non-zero exit for missing skills through the executor exception path.

## [2.0.1] - 2026-05-04

### Fixed
- Fixed the first post-2.0.0 bugfix batch found through cross-model review and CLI validation.
- Kept Python 3.12/3.13 CI and PyPI Trusted Publishing green.

## [2.0.0] - 2026-05-03

### Summary

**首个正式版本发布！** 这是一个里程碑式的版本，标志着 Skills Orchestrator 从 alpha 阶段正式进入生产可用状态。

本版本包含了完整的 Skill 治理、多平台同步、Pipeline 编排、MCP 服务等核心功能，并修复了所有已知的安全漏洞。

### Security
- **Fixed**: Path traversal vulnerability in `_parse_context` - context files must now be within current working directory
- **Fixed**: SSRF vulnerability in GitHub URL validation - added hostname whitelist for github.com, raw.githubusercontent.com, and api.github.com
- **Improved**: All YAML parsing uses `safe_load` to prevent code injection

### Added
- **Pipeline conditional branching** - support `if` conditions in pipeline steps
- **Multi-platform sync** - sync skills to Claude Desktop, Cursor, OpenClaw, Hermes, and Copilot
- **`--version` command** - show version information
- **GitHub Issue templates** - bug report and feature request templates
- **`--force` flag for import command** - explicitly allow overwriting existing files
- **`--pipelines-dir` parameter** - specify custom pipeline directory for all pipeline commands

### Fixed
- **Fixed**: Pipeline `duration_s` now correctly records step execution time
- **Fixed**: `import_skill` command prevents silent file overwrites by default
- **Fixed**: Version comparison uses proper semantic versioning instead of string comparison
- **Fixed**: `_auto_skip` handles empty `next` list to prevent IndexError
- **Fixed**: `_load_pipeline` provides meaningful error messages instead of silently swallowing exceptions
- **Fixed**: `_parse_zones` uses default values for better error handling
- **Fixed**: Renamed `_expand_combos` to `_validate_combos` for clarity
- **Fixed**: `sync --dry-run` removed unused `SyncEngine` instantiation
- **Fixed**: `pipeline_start` uses unified `_load_pipeline()` to avoid duplicate loading

### Changed
- **Improved**: Pipeline CLI parameter consistency - `status` and `resume` use positional argument `PIPELINE_ID`
- **Improved**: `validate --check-lock` exits with proper error code when lock file doesn't exist
- **Improved**: `sync --full` help text accurately describes behavior
- **Improved**: Zone load_policy semantics - zone `require` overrides skill `free`

### Technical Details
- Package name refactored from `src` to `skills_orchestrator`
- Skill content reading unified via `SkillContentResolver`
- Skills lock file support for reproducibility
- 185 tests passing with full coverage
- All ruff checks passing
- Security vulnerabilities fixed

### Breaking Changes
- Package name changed from `src` to `skills_orchestrator` - update your imports
- Zone `require` now properly overrides skill `free` - check your zone configurations

### Migration Guide

If you're upgrading from alpha versions:

1. Update imports from `src.*` to `skills_orchestrator.*`
2. Check zone configurations with `require` load_policy
3. Review any custom pipelines for compatibility
4. Run `skills-orchestrator validate` to check configuration

## [2.0.0a5] - 2026-05-03 [YANKED]

Alpha release, merged into v2.0.0.

### Security
- **Fixed**: Path traversal vulnerability in `_parse_context` - context files must now be within current working directory
- **Fixed**: SSRF vulnerability in GitHub URL validation - added hostname whitelist for github.com, raw.githubusercontent.com, and api.github.com

### Fixed
- **Fixed**: Pipeline `duration_s` now correctly records step execution time instead of always being 0
- **Fixed**: `import_skill` command now prevents silent file overwrites with new `--force` flag
- **Fixed**: Version comparison now uses proper semantic versioning instead of string comparison
- **Fixed**: `_auto_skip` now handles empty `next` list to prevent IndexError
- **Fixed**: `_load_pipeline` now provides meaningful error messages instead of silently swallowing exceptions
- **Fixed**: `sync --dry-run` removed unused `SyncEngine` instantiation
- **Fixed**: `pipeline_start` now uses unified `_load_pipeline()` to avoid duplicate loading
- **Fixed**: `_parse_zones` now uses `.get()` with default values for better error handling
- **Fixed**: Renamed `_expand_combos` to `_validate_combos` for clarity

### Changed
- **Improved**: Pipeline CLI parameter consistency - `status` and `resume` now use positional argument `PIPELINE_ID`
- **Improved**: Added `--pipelines-dir` parameter to all pipeline subcommands
- **Improved**: `validate --check-lock` now exits with proper error code when lock file doesn't exist
- **Improved**: `sync --full` help text now accurately describes behavior

### Security Improvements
- Added path validation to prevent directory traversal attacks
- Added URL hostname whitelist to prevent SSRF attacks
- All YAML parsing uses `safe_load` to prevent code injection

## [2.0.0a4] - 2026-05-02

### Added
- Pipeline conditional branching feature
- `--version` command
- Multi-platform sync support (Claude Desktop, Cursor, OpenClaw, Hermes, Copilot)
- GitHub Issue templates

### Fixed
- Semantic consistency fixes for `effective_load_policy`, MCP `--zone`, cross-Zone base inheritance
- Documentation corrections

## [2.0.0a3] - 2026-05-02

### Fixed
- `effective_load_policy` calculation
- MCP `--zone` parameter
- Cross-Zone base inheritance

## [2.0.0a2] - 2026-05-02

### Fixed
- Documentation fixes

## [2.0.0a1] - 2026-05-02

### Added
- Initial alpha release
- Core skill orchestration functionality
- MCP server support
- Pipeline execution engine
- Multi-platform synchronization

## [1.4.0] - 2026-05-02

### Added
- Pipeline conditional branching
- `--version` command
- PyPI publishing with Trusted Publishing

## [1.3.1] - 2026-05-02

### Fixed
- `SkillContentResolver` unified content reading
- MCP dependency hints
- Base inheritance validation

## [1.3.0] - 2026-05-02

### Changed
- Package name refactored from `src` to `skills_orchestrator`
- Zone require semantics
- Added `skills.lock` support
- Compressor and registry improvements

## [1.2.0] - 2026-05-01

### Added
- Initial release with core functionality
