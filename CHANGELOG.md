# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
