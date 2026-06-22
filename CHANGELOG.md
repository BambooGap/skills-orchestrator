# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.0.1] - 2026-06-23

### Fixed
- Fixed the registry/evidence documentation to validate the SBOM artifact at
  `evidence/package-sbom.cdx.json`, matching the output written by `evidence export`.

### Changed
- Updated current install, Action, container, and PyPI examples to `v4.0.1` so release artifacts,
  package metadata, and documentation snapshots stay aligned after the v4.0 documentation fix.

## [4.0.0] - 2026-06-22

### Added
- Added `schema audit` to self-audit packaged schema contracts and schema catalog metadata.
- Added `schema-audit.schema.json` so the schema audit report is itself machine-validatable.

### Changed
- Marked the package as `Production/Stable` for the v4 line while keeping existing v1 SkillOps
  contract identifiers compatible.
- Updated current install, Action, container, and pilot workflow examples to `v4.0.0`.

## [3.9.0] - 2026-06-22

### Added
- Added `schema-catalog.schema.json` so `schema list --format json` is itself a
  machine-validated SkillOps contract.
- Added contract catalog metadata for every registered schema: `contract_id`, `stability`,
  `since`, and intended `consumers`.

### Changed
- Expanded schema catalog text/JSON output to distinguish stable contracts from preview
  commercial handoff contracts before the 4.0 line.
- Updated current install, Action, container, and pilot workflow examples to `v3.9.0`.

## [3.8.0] - 2026-06-22

### Added
- Added `dashboard rollup` to aggregate multiple enterprise dashboard snapshots into a
  schema-validated organization-level dashboard payload.
- Added `enterprise-dashboard-rollup.schema.json` and a commercial handoff example for hosted
  dashboard consumers.

### Changed
- Expanded CI smoke and docs to validate dashboard snapshot and dashboard rollup contracts.
- Updated current install, Action, container, and pilot workflow examples to `v3.8.0`.

## [3.7.0] - 2026-06-22

### Changed
- Upgraded pinned GitHub Actions workflow dependencies to Node 24-compatible releases:
  `actions/checkout@v7.0.0` and `actions/setup-python@v6.2.0`.
- Updated current install, Action, container, and pilot workflow examples to `v3.7.0`.

## [3.6.0] - 2026-06-22

### Added
- Added `dashboard snapshot` to derive a schema-validated enterprise dashboard payload from an
  existing evidence bundle without re-running policy decisions.
- Added GitHub Action `dashboard-snapshot` inputs and output path so CI can publish dashboard-ready
  JSON alongside check, reviewer summary, and evidence artifacts.

### Changed
- Expanded CI smoke coverage and docs to validate dashboard snapshots generated from demo evidence.

## [3.5.0] - 2026-06-22

### Added
- Added `reviewer summary` to generate a PR reviewer-facing Markdown or JSON summary from
  check JSON, policy trace, registry diff, registry graph, and evidence ledger artifacts.
- Expanded the composite GitHub Action outputs with stable paths for check JSON, policy trace,
  registry diff JSON, registry graph, evidence manifest, evidence bundle hash, and reviewer
  summary artifacts.

### Changed
- The GitHub Action now delays failing on `check` diagnostics until reviewer artifacts have been
  generated, so failing pull requests still retain inspectable SkillOps evidence.

## [3.4.0] - 2026-06-22

### Added
- Added CI policy trace to JSON check reports via `policy_trace`, covering diagnostic failures and
  passed built-in rule groups without representing agent reasoning as runtime trace.
- Added `registry graph` and `registry-graph.schema.json` for derived ownership, source, combo, and
  conflict relationships across organization registry facts.
- Added an evidence ledger to `evidence export` manifests with per-artifact SHA-256 hashes,
  `bundle_hash`, and optional `previous_bundle_hash` for simple audit continuity.

### Changed
- Expanded the SkillOps Contract, conformance, registry/evidence, release verification, and demo
  docs to include policy trace, registry graph, and evidence ledger validation paths.

## [3.3.1] - 2026-06-22

### Fixed
- `evidence export` now writes `adapter-inspect.json` and `package-sbom.cdx.json` so
  `doctor --profile enterprise` can reach 100 after a complete evidence export.
- Documented upgrade remediation for stale generated `AGENTS.md` artifacts.
- Clarified that registry diff JSON is the schema-validation output, while Markdown is for PR
  review comments.

## [3.3.0] - 2026-06-22

### Added
- Added an Adoption Playbook for advisory, warning, and engineering-grade rollout modes.
- Added copyable pilot repository starter packs for Healthchecks, Umami, and Woodpecker-style
  repositories.
- Added a release hygiene regression test that fails when generated `AGENTS.md` is stale relative
  to the package version.

### Changed
- Refined the GitHub Action and Marketplace-facing positioning around SkillOps policy packs,
  SARIF, registry diff, and evidence checks.
- Linked the README, documentation index, and examples index to the new adoption path.

## [3.2.1] - 2026-06-22

### Fixed
- Fixed MCP `list_skills` filtering for clients that pass `tags: ["..."]` instead of the
  legacy single-string `tag` argument.
- Documented `list_skills` support for both `tag` and `tags`, with `tags` requiring all specified
  tags to be present.

## [3.2.0] - 2026-06-21

### Added
- Added trust metadata fields for skill `license` and external import `provenance` across parser,
  registry, instruction manifest, OPA input, CycloneDX export, and public JSON Schemas.
- Added engineering-grade policy diagnostics `SO018`, `SO019`, and `SO020` for missing license,
  disallowed license, and missing external import provenance.
- Added safer GitHub skill import provenance capture, including observed commit, content hash, fetch
  timestamp, HTTPS-only source validation, no-redirect raw downloads, and path-safe filenames.
- Added default review-window and license metadata to the team-standard starter kit.

### Changed
- Expanded SkillOps Contract, conformance, security, and policy-pack docs to treat trust metadata as
  part of the engineering-grade governance layer.
- Updated the built-in example skills with review-window and license metadata.

### Fixed
- Pinned GitHub import downloads to the resolved commit so provenance cannot record one commit while
  hashing bytes fetched from a later branch head.
- Resolved bare repository imports through the repository default branch instead of assuming `main`.
- Rejected mutable `raw.githubusercontent.com` refs for direct raw imports.
- Made HTTP(S) external-source detection case-insensitive for `SO020`.

## [3.1.0] - 2026-06-21

### Added
- Added `conformance run` to execute the local SkillOps Contract suite across config schema,
  check diagnostics, evidence artifacts, registry output, and adapter inspection.
- Added `builtin/engineering-grade`, a policy pack that extends `builtin/team-standard` with
  `reviewed_at` / `expires_at` review-window governance.
- Added declarative local policy packs validated by `policy-pack.schema.json`; packs are data-only
  YAML/JSON and do not execute repository Python code.
- Added `doctor --profile enterprise` to verify schema-backed evidence bundles for enterprise
  SkillOps pilots.
- Added `conformance-report.schema.json` and `policy-pack.schema.json` to the public schema catalog.

### Changed
- Registry diff Markdown now expands `reviewed_at` and `expires_at` governance changes for PR
  reviewers.

## [3.0.6] - 2026-06-21

### Changed
- Upgraded pinned `github/codeql-action` references from v3 to the v4 commit SHA for CodeQL
  analysis and SARIF upload.
- Expanded the demo repository README with a local changed-registry-diff walkthrough.
- Updated current install, GitHub Action, and container examples to `v3.0.6`.

### Fixed
- Made subprocess-based CLI tests hermetic by invoking `skills_orchestrator.main` with the active
  Python interpreter instead of relying on `python` or `skills-orchestrator` being on `PATH`.

## [3.0.5] - 2026-06-21

### Added
- Added `SO013` for skill-level `load_policy` validation so CI JSON/SARIF output points to the
  offending skill file instead of a generic fatal config error.

### Changed
- Clarified the SkillOps Contract `missing_file` boundary: explicit `skills[].path` references keep
  registry entries with `missing_file=true`; `skill_dirs` auto-discovery deletions are represented
  as removed entries or combo-reference errors.
- Updated current install, GitHub Action, and container examples to `v3.0.5`.

### Fixed
- Normalized null and blank governance metadata so `owner:`, `source:`, `version:`, and
  `lifecycle:` no longer become the literal string `"None"` and bypass policy checks.
- Fixed explicit `skills[].path` resolution for the standard `config/skills.yaml` layout so existing
  files such as `skills/real.md` are not misreported as `missing_file=true`.

## [3.0.4] - 2026-06-21

### Added
- Packaged built-in pipeline templates under `skills_orchestrator/config/pipelines/` so
  `pipeline list` works from installed wheels and source checkouts.

### Changed
- Registry diff JSON changed entries now include an optional `skill` summary, and Markdown changed
  rows use it to populate Status, Owner, and Path columns for PR review.

### Fixed
- Fixed `registry-diff` schema validation for changed entries that include the compact `skill`
  summary.
- Fixed installed-package `pipeline list` fallback so it no longer depends on the repository root
  `config/pipelines` directory being present.

## [3.0.3] - 2026-06-21

### Added
- Added `doctor --profile adopter|maintainer` so consuming repositories and this package's release
  workflow can use separate readiness scoring profiles.
- Added implementer-facing SkillOps Contract notes with registry diff examples, diagnostic code
  conventions, and boundary cases for third-party compatible tools.

### Changed
- Changed the default `doctor` profile to adopter readiness, focused on SkillOps CI, lock, and
  `AGENTS.md` evidence instead of package release artifacts.
- Improved `doctor` CI workflow detection so the generated `skills-orchestrator.yml` starter
  workflow passes the readiness threshold immediately after `init --template team-standard`.
- Expanded registry diff Markdown details to show reviewer-facing governance field changes such as
  owner, source, version, lifecycle, approvers, status, and content hash.
- Clarified Python 3.12 installation requirements in README and installation docs, including the
  common macOS Python 3.9 failure mode.

## [3.0.2] - 2026-06-21

### Changed
- Replaced the README Marketplace badge link with the repository GitHub Action documentation until the action is explicitly published through GitHub's Marketplace release UI.
- Documented the Marketplace publishing handoff and Developer Agreement prerequisite in the GitHub Action guide.
- Updated README, docs, examples, package metadata, and reports to point at `v3.0.2` release entry points.

## [3.0.1] - 2026-06-21

### Added
- Added `SPEC.md` for the executable SkillOps Contract v1 across skill metadata, registry, registry diff, evidence bundle, adapter inspection, and package SBOM surfaces.
- Added `CONFORMANCE.md` with reproducible local, CI, registry, and adapter conformance checks.
- Added `SECURITY.md` with the MCP trust model, HMAC audit boundary, import provenance boundary, and vulnerability reporting flow.
- Added a runnable `examples/demo-repo/` fixture covering SARIF, registry diff, PR comment body, evidence bundle export, and adapter inspection.
- Added GitHub Action Marketplace branding metadata.
- Added minimal honest governance files for the current early-stage single-maintainer project state.

### Changed
- Updated README, docs, and examples to point at `v3.0.1` release entry points.
- Added the demo repo conformance smoke to CI.

## [3.0.0] - 2026-06-21

### Added
- Added registry diff PR comment automation for the composite GitHub Action, including registry diff artifacts, idempotent PR comment bodies, and optional PR comment upsert.
- Added `registry comment-body` to generate stable PR comment Markdown without coupling the core CLI to GitHub APIs.
- Added `supply-chain sbom` to generate a Python package CycloneDX SBOM distinct from the instruction manifest CycloneDX export.
- Added CodeQL and GHCR publishing workflows for the open-source distribution path.
- Added `adapters inspect` plus `adapters export mcp-client-config` and `adapters export openai-agents-sdk` for AGENTS.md, Claude Skills, MCP, and OpenAI Agents SDK integration surfaces.
- Added adapter, supply-chain SBOM, GitHub App installation, hosted registry ingest, and enterprise dashboard snapshot JSON Schema contracts.
- Added commercial handoff examples for future GitHub App, hosted registry, and enterprise dashboard consumers.

### Changed
- Reframed the roadmap around open-source SkillOps contracts first, with hosted services as downstream consumers of CLI-generated artifacts.
- Expanded CI supply-chain checks with package SBOM generation and pinned `pip-audit`.

### Security
- GitHub PR comment automation uses a hidden marker for idempotent updates and keeps token/API access in an integration boundary, not the registry diff core.
- GHCR publishing uses release/workflow-dispatch events and does not push containers from pull requests.

## [2.6.0] - 2026-06-21

### Added
- Added `skills-orchestrator schema list` and `schema validate` for native config, check, manifest, policy OPA input, doctor, registry, registry diff, and evidence bundle contracts.
- Added packaged JSON Schema files under `skills_orchestrator/schemas/` and declared `jsonschema` as a direct runtime dependency.
- Added `init --template team-standard` to generate a portable team starter kit with governed skills, a review pipeline, CI workflow, and evidence directory.
- Added `registry diff --format markdown` plus `--output` for PR/release review files.

### Changed
- Updated README, Quick Start, team standardization, registry/evidence, install, CI, policy pack, and GitHub Action docs for the v2.6.0 commercial workflow.
- Regenerated the repository `AGENTS.md` with v2.6.0 metadata.

### Security
- The generated team-standard workflow defaults to read-only permissions and does not enable SARIF upload unless teams opt into the documented GitHub Action settings.
- Template initialization now rejects output path traversal and symlink targets, and registry diff output no longer overwrites existing files unless `--force` is passed.
- Schema validation now caps input size and reported validation errors.

## [2.5.1] - 2026-06-21

### Changed
- Updated project-page positioning for GitHub, PyPI, and the GitHub Action marketplace around the current SkillOps / instruction-supply-chain control-plane scope.
- Refreshed install and CI examples to point at `v2.5.1`.

## [2.5.0] - 2026-06-21

### Added
- Added `builtin/team-standard` policy pack for owner/source/version/lifecycle/approver governance checks.
- Added governance metadata parsing for skills and exported it in native manifests, CycloneDX properties, and OPA input.
- Added `skills-orchestrator doctor` for local commercial-readiness scoring.
- Added `skills-orchestrator registry build` and `registry diff` for organization-level skill inventory and PR review.
- Added `skills-orchestrator evidence export` to write check, SARIF, manifest, OPA, Rego, doctor, and registry evidence bundles.
- Added `skills-orchestrator integrations list` for adjacent agent-tooling ecosystem positioning.
- Added GitHub Action `policy-pack` input for one-line team-standard CI enforcement.

### Changed
- Hardened MCP runtime injection with a configurable per-skill content byte limit.
- Hardened MCP audit task hashing with optional HMAC via `SKILLS_ORCHESTRATOR_AUDIT_SALT`.
- Hardened MCP audit and pipeline state files with private file permissions.
- Pipeline run-state persistence now redacts sensitive context keys and truncates oversized context strings.

## [2.4.0] - 2026-06-20

### Added
- Added Dockerfile and Docker usage documentation for portable CLI execution.
- Added a team standardization guide and missing Zone, Pipeline, and CI/CD docs.
- Added a CI Docker build and smoke-test job.
- Added structured `prepare_context` decision records with routing IDs, task hashes, registry generation, active/inactive skills, and content hashes.
- Added opt-in MCP audit JSONL events plus `skills-orchestrator usage report`.
- Added MCP `pipeline_list_runs` for runtime workflow recovery and audit.
- Added documentation for install paths, policy packs, manifest/policy exports, release verification, and enterprise positioning.

### Changed
- Updated the team collaboration example to use the current v2 configuration schema.
- Pipeline gates now support `must_produce` as either a single artifact key or a list of required artifact keys.
- Hardened the Dockerfile by removing the unpinned pip upgrade and running as a non-root user.

## [2.3.0] - 2026-06-20

### Added
- Added a composite GitHub Action for running `skills-orchestrator check` in CI and optionally uploading SARIF to GitHub Code Scanning.
- Added GitHub Action usage documentation.
- Added Dependabot coverage for GitHub Actions and Python dependencies.
- Added `skills-orchestrator manifest --format json|cyclonedx` for native instruction inventory and experimental CycloneDX export.
- Added `skills-orchestrator policy export --format opa-input|rego-test` for OPA/Rego proof exports without adding an OPA runtime backend.
- Added runtime dependency constraints for the composite action, CI, and publish workflow.
- Added a release artifact attestation step for wheel and sdist provenance.
- Added a CI guard that checks third-party GitHub Actions are pinned to full commit SHAs.

### Changed
- Hardened CI with a local action smoke test.
- Hardened PyPI publishing with explicit `contents: read` permission and release tag/package version verification.
- Hardened MCP debug logging so tool argument values are not logged.
- Pinned third-party GitHub Actions in CI, publish, and the composite action to full commit SHAs.
- Bumped the next release version to `2.3.0` because the GitHub Action and export surfaces are new release content after the `v2.2.0` tag.

## [2.2.0] - 2026-06-19

### Added
- Added `skills-orchestrator check` for structured skill diagnostics.
- Added diagnostic rules for missing descriptions, duplicate skill ids, unresolved conflicts, asymmetric conflict declarations, oversized skills, and lock drift.
- Added JSON and SARIF output for `check` and structured `validate --format json|sarif` usage.
- Added rule documentation under `docs/rules/` for GitHub Code Scanning help links.
- Added the Agent Instruction Supply Chain roadmap under `docs/instruction-supply-chain-roadmap.md`.

### Changed
- Repositioned README around SkillOps, static diagnostics, and machine-readable CI output.
- Kept existing `validate` text output and resolver behavior compatible by default.

## [2.1.1] - 2026-05-07

### Fixed
- `prepare_context`: required/forced skills now unconditionally enter `active_skills`; `max_skills` now only limits task-relevant passive skills. Previously, forced skills could be displaced from `active_skills` by higher-scoring passive skills, creating a governance hole where enterprise-mandatory rules were silently skipped.
- Renamed `inactive_previous_skills` → `inactive_skills` in `prepare_context` output and corrected the accompanying note: the field lists skills not selected for the current task, not skills that were "previously loaded".

## [2.1.0] - 2026-05-07

### Added
- Added MCP `prepare_context` for per-task runtime skill routing with active/inactive skill decisions.
- Added generated `AGENTS.md` runtime loading guidance so agents know to call `prepare_context` at each new task boundary.
- Added regression coverage for `prepare_context` argument validation, content injection, summary-only mode, and generated `AGENTS.md` routing instructions.

### Changed
- Updated README MCP documentation and examples to describe `prepare_context` as the recommended runtime entrypoint.

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
