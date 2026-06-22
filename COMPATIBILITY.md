# Compatibility Policy

Skills Orchestrator treats SkillOps artifacts as contracts. This policy describes what can change
inside the v3.x line.

## Stable Contract Surfaces

The following are stable for compatible v3.x releases:

- JSON Schema kinds returned by `skills-orchestrator schema list`.
- Schema catalog entries returned by `skills-orchestrator schema list --format json`.
- Existing `schema_version` identifiers that end in `.v1`.
- Existing diagnostic rule ids such as `SO008`.
- CLI commands documented in `README.md`, `SPEC.md`, and `CONFORMANCE.md`.
- Built-in policy pack ids under `builtin/`.

## Allowed Additive Changes

Minor and patch releases MAY add:

- new optional JSON fields,
- new schema kinds,
- new diagnostic rule ids,
- new policy pack ids,
- new CLI options with backwards-compatible defaults.

Consumers SHOULD ignore unknown JSON fields unless they intentionally run strict validation.

## Breaking Changes

Breaking changes require one of:

- a new major package version,
- a new contract identifier, such as `skills-orchestrator.registry.v2`,
- or a new explicit opt-in CLI flag.

Examples of breaking changes:

- removing or renaming a schema kind,
- changing a v1 `schema_version` payload incompatibly,
- changing the meaning of an existing `SOxxx` rule id,
- changing default policy behavior in a way that turns a previously passing default check into a
  failure.

## Migration Rule

When a future contract version is introduced, the project should provide:

1. a compatibility note in this file,
2. a changelog entry,
3. a schema validation example,
4. and, where practical, a migration command or documented manual migration.

## Contract Stability

`schema list --format json` exposes a machine-readable catalog for current contracts. Each entry
declares:

- `contract_id`: the public identifier or upstream standard id.
- `stability`: `stable` or `preview`.
- `since`: the release that introduced the public surface.
- `consumers`: the intended integration surfaces.

`stable` means consumers can build CI and audit automation against the contract using this
compatibility policy. `preview` means the schema is executable and tested, but its downstream
hosted-product workflow may still evolve additively before a future major version.

## Current Line

`v3.9.x` keeps SkillOps Contract v1 stable and adds a machine-readable contract catalog:

- `skills-orchestrator.conformance.v1`
- `skills-orchestrator.policy-pack.v1`
- optional `policy_trace` in check reports, required for v3.4 conformance
- optional `ledger` in evidence manifests, required for v3.4 conformance
- `skills-orchestrator.registry-graph.v1`
- `skills-orchestrator.schema-catalog.v1`

Commercial handoff contracts for GitHub App installation, hosted registry ingest, and enterprise
dashboard snapshots/rollups remain `preview` catalog entries in v3.9.x.
