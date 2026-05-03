# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0a5] - 2026-05-03

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
