# SkillOps Contract v1

Status: stable contract surface for `skills-orchestrator` v4.x and compatible later lines.

This document defines the machine-checkable contract exposed by Skills Orchestrator. It is not a
vision document and does not define a new agent runtime. A project conforms by producing and
validating the artifacts listed here.

Normative terms use RFC 2119 meanings: MUST, MUST NOT, SHOULD, MAY.

## Scope

SkillOps Contract v1 covers eleven artifact families:

- skill metadata in `skills.yaml` and skill frontmatter,
- schema catalog metadata for public contract discovery,
- check reports with CI policy trace,
- organization registry JSON,
- registry graph JSON,
- registry diff JSON and Markdown,
- evidence bundle manifests,
- multi-repository artifact indexes,
- preview external adoption records,
- preview agent handoff contracts,
- preview agent runtime image contracts,
- adapter inspection reports.

SARIF, CycloneDX, OPA/Rego, MCP, and AGENTS.md remain upstream or adjacent standards. This contract
only specifies how Skills Orchestrator emits or references them.

## Versioning

- Contract identifiers MUST use the `skills-orchestrator.<name>.v1` form.
- Breaking changes MUST create a new contract identifier, for example
  `skills-orchestrator.registry.v2`.
- Additive fields MAY be added to v1 artifacts. Consumers MUST ignore unknown fields unless they
  intentionally opt into strict validation.
- JSON Schema files under `skills_orchestrator/schemas/` are the executable contract source.

## Schema Catalog Contract

The schema catalog is the machine-readable entry point for public contract discovery. The
registered schema kind is `schema-catalog`, backed by `schema-catalog.schema.json`.

```bash
skills-orchestrator schema list --format json > schema-catalog.json
skills-orchestrator schema validate --kind schema-catalog --input schema-catalog.json
```

Every catalog entry MUST include:

| Field | Constraint |
| --- | --- |
| `kind` | CLI schema kind used by `schema validate --kind`. |
| `file` | Packaged JSON Schema filename. |
| `contract_id` | Public contract identifier or upstream standard id. |
| `stability` | One of `stable` or `preview`. |
| `since` | First release exposing the contract surface. |
| `consumers` | Intended integration surfaces such as `ci`, `audit`, or `hosted-service`. |

`stable` catalog entries follow the compatibility policy for v4.x and later compatible lines.
`preview` entries are executable and tested, but downstream hosted-product workflows may still
evolve additively before a future major version.

## Schema Audit Contract

The schema audit contract verifies that packaged schemas and schema catalog metadata are internally
consistent. The registered schema kind is `schema-audit`, backed by `schema-audit.schema.json`.

```bash
skills-orchestrator schema audit --format json > schema-audit.json
skills-orchestrator schema validate --kind schema-audit --input schema-audit.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.schema-audit.v1`. |
| `tool` | Tool metadata, including the emitting package version. |
| `status` | `pass` or `fail`. |
| `summary` | Counts for schemas, stable entries, preview entries, checks, passed, and failed. |
| `checks` | Per-schema load and metadata checks. |

The audit command MUST NOT read project skill files, execute agents, or re-evaluate policy. It is a
package self-audit gate for contract distribution quality.

## Skill Metadata Contract

Skill metadata is loaded from `config/skills.yaml` and Markdown frontmatter. The registered schema
kind is `config`, backed by `skills-config.schema.json`.

Validation command:

```bash
skills-orchestrator schema validate --kind config --input config/skills.yaml
```

### Required Skill Fields

Every effective skill entry MUST expose:

| Field | Type | Constraint |
| --- | --- | --- |
| `id` | string | Non-empty, stable within the project or organization. |
| `name` | string | Human-readable display name. |
| `path` | string | Path to the Markdown skill file. |
| `summary` | string | Short description used in reports and search. |

### Governance Fields

When the `builtin/team-standard` policy pack is enabled, shared skills SHOULD include:

| Field | Type | Constraint |
| --- | --- | --- |
| `owner` | string | Team or maintainer responsible for review. |
| `source` | string | Repository, URL, or internal source reference. |
| `version` | string | Semver, date, or locally stable version value. |
| `lifecycle` | enum | One of `active`, `beta`, `deprecated`, `retired`. |
| `approvers` | string array | Required when `load_policy` is `require`. |

Policy check:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

When the `builtin/engineering-grade` policy pack is enabled, it includes `builtin/team-standard`
and shared skills SHOULD also include:

| Field | Type | Constraint |
| --- | --- | --- |
| `reviewed_at` | string | ISO date in `YYYY-MM-DD` form. |
| `expires_at` | string | ISO date in `YYYY-MM-DD` form; MUST be on or after `reviewed_at` and SHOULD be in the future. |
| `license` | string | SPDX license id. Built-in allowlist is `MIT` and `Apache-2.0`. |
| `provenance` | object | Required for externally sourced skills. SHOULD include `source_url`, `source_ref`, `source_commit`, `content_hash`, and `fetched_at`. |

Engineering-grade policy check:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

Local declarative policy packs MUST use `skills-orchestrator.policy-pack.v1` and MUST be data-only
YAML/JSON. Implementations MUST NOT execute repository code while loading a policy pack.

Validation command:

```bash
skills-orchestrator schema validate \
  --kind policy-pack \
  --input policy-pack.yaml
```

### Routing Fields

| Field | Type | Constraint |
| --- | --- | --- |
| `tags` | string array | Used for search, filtering, and catalog grouping. |
| `load_policy` | enum | `require` or `free` for skills. |
| `priority` | integer | Higher values win during routing and ordering. |
| `zones` | string array | Zone ids where the skill applies. |
| `conflict_with` | string array | Skill ids that cannot be active with this skill. |
| `base` | string | Optional inherited skill id. |

Resolvers MAY allow asymmetric `conflict_with` declarations. A one-way conflict remains valid, but
conformance checks SHOULD treat it as weaker audit evidence than symmetric declarations.

## Check Report And Policy Trace Contract

The check report contract records machine-readable diagnostics and CI policy trace. The registered
schema kind is `check`, backed by `check-report.schema.json`.

```bash
skills-orchestrator check --config config/skills.yaml --format json > check.json
skills-orchestrator schema validate --kind check --input check.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `1.0`. |
| `tool` | Tool metadata, including the emitting package version when available. |
| `summary` | Diagnostic and project counts. |
| `diagnostics` | Diagnostic findings keyed by rule id. |
| `policy_trace` | Rule evaluation trace items. |

Each `policy_trace` item MUST include:

| Field | Constraint |
| --- | --- |
| `rule_id` | SkillOps diagnostic rule id or compatible rule identifier. |
| `outcome` | One of `pass`, `fail`, or `skip`. |
| `scope` | Evaluation scope such as `metadata`, `resolver`, `lock`, or `policy_pack`. |
| `reason` | Human-readable reason for the outcome. |
| `input_facts` | Machine-readable facts used by the check. |

Failed trace items SHOULD embed the corresponding diagnostic in `diagnostic`. Policy-pack trace
items SHOULD include `policy_pack`. This trace is a CI rule-evaluation trace; it MUST NOT be
represented as an agent reasoning trace or runtime execution graph.

`policy_trace` is additive in the v1 JSON Schema for backwards compatibility with older check
reports. v4.x conformant emitters MUST include it, and `conformance run` MUST fail when it is
absent.

## CI Explainability Contract

The CI explainability contract is the reviewer- and platform-facing explanation layer derived from
`check --format json`. The registered schema kind is `ci-explainability`, backed by
`ci-explainability.schema.json`.

Build and validate:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --format json > check.json

skills-orchestrator explainability build \
  --check-json check.json \
  --config config/skills.yaml \
  --output ci-explainability.json \
  --force

skills-orchestrator schema validate \
  --kind ci-explainability \
  --input ci-explainability.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.ci-explainability.v1`. |
| `tool` | Tool metadata, including the emitting package version when available. |
| `source` | Source artifact metadata, including the config path and check schema version when known. |
| `status` | One of `pass`, `warn`, or `fail`, derived from check diagnostics. |
| `summary` | Counts for decisions, diagnostics, severities, and project shape. |
| `ci_decision` | CI outcome, blocking flag, fail-on threshold, and human-readable reason. |
| `decisions` | Normalized policy decision trace items. |
| `failure_explainability` | Reviewer-focused failure explanations for non-passing decisions. |

Each `decisions` item MUST include `rule_id`, `outcome`, `scope`, `reason`, `location`,
`input_facts`, and `ci_effect`. Failed decision items SHOULD include `severity`, `diagnostic`, and
`suggested_fix` when the underlying check report provides them.

This contract explains CI rule evaluation and PR failure causes. It MUST NOT be represented as an
agent chain-of-thought trace, runtime execution graph, or general-purpose policy runtime.

## Registry Contract

The registry contract is the organization inventory format. The registered schema kind is
`registry`, backed by `skill-registry.schema.json`.

Build and validate:

```bash
skills-orchestrator registry build \
  --config-glob "config/skills.yaml" \
  --output skill-registry.json

skills-orchestrator schema validate \
  --kind registry \
  --input skill-registry.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.registry.v1`. |
| `tool` | Tool metadata, including the emitting package version when available. |
| `summary` | Counts for configs, skill refs, unique skills, and duplicate ids. |
| `duplicates` | Object keyed by duplicate skill id. |
| `owners` | Object keyed by owner value. |
| `configs` | Per-config registry entries. |

Every registry skill entry MUST include:

| Field | Constraint |
| --- | --- |
| `registry_key` | Stable key for comparing skills across configs. |
| `id` | Skill id. |
| `name` | Skill display name. |
| `status` | One of `forced`, `passive`, `blocked`. |
| `path` | Source path used by the config. |
| `governance` | Owner/source/version/lifecycle/approver metadata. |
| `content_hash` | Hash information for drift review. |
| `missing_file` | Boolean indicating whether the skill file was missing. |

## Registry Graph Contract

The registry graph contract is a derived structural view over the organization registry. The
registered schema kind is `registry-graph`, backed by `registry-graph.schema.json`.

```bash
skills-orchestrator registry graph \
  --config-glob "config/skills.yaml" \
  --output registry-graph.json

skills-orchestrator schema validate \
  --kind registry-graph \
  --input registry-graph.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.registry-graph.v1`. |
| `tool` | Tool metadata. |
| `summary` | Counts for nodes, edges, configs, and skill refs. |
| `nodes` | Graph nodes. |
| `edges` | Graph edges. |

Node types currently include `config`, `zone`, `skill`, `owner`, `source`, and `combo`. Edge types
currently include `config_uses_zone`, `config_contains_skill`, `skill_owned_by`,
`skill_sourced_from`, `config_defines_combo`, `skill_member_of_combo`, and
`skill_conflicts_with`.

The registry graph is an artifact contract, not a database API. It SHOULD be regenerated from
registry input and MAY be consumed by hosted registries, graph viewers, or platform review tools.

## Registry Diff Contract

The JSON diff contract compares two registry snapshots. The registered schema kind is
`registry-diff`, backed by `registry-diff.schema.json`.

```bash
skills-orchestrator registry diff before.json after.json \
  --format json \
  --output registry-diff.json

skills-orchestrator schema validate \
  --kind registry-diff \
  --input registry-diff.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.registry-diff.v1`. |
| `summary` | Counts for `added`, `removed`, `changed`, and `duplicate_id_changes`. |
| `added` | Registry skill entries that appeared in the after snapshot. |
| `removed` | Registry skill entries absent from the after snapshot. |
| `changed` | Entries with changed fields, keyed by `registry_key` and `id`; entries MAY include an optional `skill` snapshot for PR-review display. |
| `duplicate_id_changes` | Duplicate count changes by skill id. |

Markdown registry diffs are presentation artifacts for PR review. Consumers that need stable parsing
MUST use JSON diff output. PR comments MUST include the marker generated by:

```bash
skills-orchestrator registry comment-body registry-diff.md \
  --output registry-diff-comment.md
```

## Evidence Bundle Contract

The evidence bundle manifest records generated evidence files. The registered schema kind is
`evidence`, backed by `evidence-bundle.schema.json`.

```bash
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --out evidence

skills-orchestrator schema validate \
  --kind evidence \
  --input evidence/evidence-manifest.json
```

The manifest MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.evidence-bundle.v1`. |
| `config` | Source config path. |
| `zone` | Effective zone id. |
| `policy_packs` | Policy packs used when generating evidence. |
| `files` | Object mapping evidence labels to generated paths. |
| `ledger` | Hash ledger for evidence artifacts and bundle chaining. |

An evidence bundle SHOULD include native JSON check output, SARIF, native instruction manifest, OPA
input, Rego test fixture, doctor report, registry JSON, adapter inspection, package SBOM, and the
evidence manifest.

The `ledger` object MUST include:

| Field | Constraint |
| --- | --- |
| `artifact_hashes` | Object keyed by evidence label; each value records `alg`, `value`, and `path`. |
| `bundle_hash` | SHA-256 hash over the evidence manifest payload with `bundle_hash` set to empty string. |
| `previous_bundle_hash` | Previous bundle hash for simple hash-chain continuity, or empty string. |

Ledger hashes are integrity evidence for generated artifacts. They do not imply cryptographic
signing, attestation, or SLSA compliance by themselves.

`ledger` is additive in the v1 JSON Schema for backwards compatibility with older evidence
manifests. v4.x conformant emitters MUST include it, and `conformance run` MUST fail when it is
absent or incomplete.

## Multi-repo Artifacts Contract

The multi-repo artifacts contract is an organization-level index over repository evidence bundles.
The registered schema kind is `multi-repo-artifacts`, backed by
`multi-repo-artifacts.schema.json`.

```bash
skills-orchestrator evidence index \
  --manifest "api=../api/evidence/evidence-manifest.json" \
  --manifest "web=../web/evidence/evidence-manifest.json" \
  --scope-name example-org \
  --output multi-repo-artifacts.json

skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input multi-repo-artifacts.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.multi-repo-artifacts.v1`. |
| `tool` | Tool metadata, including the emitting package version. |
| `generated_at` | UTC timestamp for the index generation. |
| `scope` | Multi-repository scope metadata, including `kind` and `name`. |
| `summary` | Counts for repositories, artifacts, missing artifacts, invalid artifacts, bundle hashes, policy findings, and registry skills. |
| `repositories` | Per-repository evidence summaries keyed by stable repository id. |
| `artifacts` | Flattened artifact records from all indexed evidence bundles. |
| `ledger` | Index-level hash ledger with artifact hashes, previous index hash, and index hash. |

Each artifact record MUST include `repository_id`, `label`, `kind`, `path`, `hash`, `required`,
and `status`. `status` MUST be one of `ok`, `missing`, or `invalid`.

The multi-repo index is derived from evidence manifests and referenced artifacts. It MUST NOT be the
source of truth for skill definitions, CI decisions, hosted registry state, dashboard state, agent
runs, or runtime orchestration. Consumers that need per-repository detail SHOULD dereference the
underlying `evidence-manifest.json` path and validate the referenced artifact contracts directly.

## External Adoption Record Contract

The external adoption record contract is a preview artifact for recording external repository
adoption state outside this project. The registered schema kind is `external-adoption-record`,
backed by `external-adoption-record.schema.json`.

```bash
skills-orchestrator schema validate \
  --kind external-adoption-record \
  --input examples/external-adoption-record/advisory-adoption-record.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.external-adoption-record.v1`. |
| `adoption` | Repository, adoption owner, start time, SkillOps version, and CI system. |
| `gate` | Current gate mode and policy pack used by the adoption. |
| `artifacts` | Presence map for check JSON, SARIF, registry diff, evidence manifest, conformance report, and optional review artifacts. |
| `promotion` | Promotion decision, decision time, optional next review, reviewer, and rationale. |
| `public_listing` | Explicit consent status for public adopter listing. |

Artifact paths MUST be bundle-relative safe paths, not absolute paths, URLs, `..` traversal paths,
or platform-specific backslash paths. A valid external adoption record is review evidence; it MUST
NOT be represented as an adopter claim, endorsement, production success proof, or hosted service
state. `ADOPTERS.md` MUST only be created or updated after the repository owner explicitly approves
public listing.

## Agent Handoff Contract

The agent handoff contract is a preview artifact for supervisor-to-worker delegation metadata. The
registered schema kind is `agent-handoff`, backed by `agent-handoff.schema.json`.

```bash
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.agent-handoff.v1`. |
| `handoff` | Handoff id, mode, owner, creation time, source, and status. |
| `tenant_scope` | Provider, project, environment, and optional tenant / cluster metadata. |
| `supervisor` | Lead agent identity, role, allowed actions, and denied actions. |
| `workers` | One or more worker contracts with purpose, permission mode, allowed tools, denied tools, context, and required outputs. |
| `task` | Delegated work id, summary, scope, inputs, expected outputs, stop condition, and retry limit. |
| `evidence` | Required and produced SkillOps artifacts for the handoff. |
| `evaluation` | Gates and reviewers required before accepting worker output. |

Authorized, running, or completed handoffs MUST set `evaluation.required: true`. Production
handoffs MUST require both `evidence-manifest` and `ci-explainability` artifacts. Privileged
workers MUST explicitly set `requires_human_approval: true` and the handoff evaluation gates MUST
include `human-review`. Implementations MUST NOT treat a valid `agent-handoff` artifact as proof
that a runtime executed workers, enforced tenant boundaries, or applied provider budgets. It is a
reviewable contract that runtimes and CI can consume before execution.

## Agent Runtime Image Contract

The agent runtime image contract is a preview artifact for containerized agent runtime review. The
registered schema kind is `agent-runtime-image`, backed by
`agent-runtime-image.schema.json`.

```bash
skills-orchestrator schema validate \
  --kind agent-runtime-image \
  --input examples/agent-runtime-image/codex-worker-image.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.agent-runtime-image.v1`. |
| `runtime` | Runtime id, name, kind, owner, purpose, and optional entrypoint metadata. |
| `image` | Immutable image reference, `sha256:` digest, supported platforms, and provenance reference. |
| `tenant_scope` | Provider, project, environment, and optional tenant / cluster metadata. |
| `permission_boundary` | Network, filesystem, secret, and human-approval boundary declarations. |
| `agent_surfaces` | AGENTS.md, Claude Skills, MCP, OpenAI Agents SDK, A2A, or internal runtime config surfaces consumed by the image. |
| `evidence` | Required and produced SkillOps artifacts that reviewers should validate before running the image. |
| `evaluation` | CI, schema, container-release, adapter, and human-review gates for the runtime image. |

Runtime image references MUST be pinned to immutable `sha256:` digests. Floating tags such as
`latest` are not sufficient evidence. Privileged filesystem access, unrestricted networking, and
runtime secret access MUST be paired with explicit human-approval requirements.

Implementations MUST NOT treat a valid `agent-runtime-image` artifact as proof that the image was
executed, that tenants were isolated, that provider keys were managed correctly, or that budgets
were enforced. This contract only makes the declared runtime-image boundary reviewable in CI.

## Adapter Inspection Contract

Adapter inspection records adjacent ecosystem surfaces. The registered schema kind is
`adapter-inspect`, backed by `adapter-inspect.schema.json`.

```bash
skills-orchestrator adapters inspect --path . --format json \
  > adapter-inspect.json

skills-orchestrator schema validate \
  --kind adapter-inspect \
  --input adapter-inspect.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.adapters.v1`. |
| `root` | Inspected repository root. |
| `summary` | Surface count and detected count. |
| `surfaces` | Detected and non-detected adapter surface records. |

Each surface MUST include `id`, `name`, `direction`, `authority`, `detected`, `paths`,
`verification`, and `notes`.

Supported surface ids in v1:

| Surface id | Meaning |
| --- | --- |
| `agents-md` | Existing `AGENTS.md` bootstrap instructions. |
| `claude-skills` | Valid Claude-style `*/SKILL.md` bundle entrypoints. |
| `mcp-client-config` | Valid MCP client JSON config with an `mcpServers` object. |
| `openai-agents-sdk` | Declared OpenAI Agents SDK dependency surface. |

## Claude Skills Export Manifest Contract

Claude Skills export writes generated `*/SKILL.md` bundles and may emit a manifest. The registered
schema kind is `claude-skills-export`, backed by `claude-skills-export.schema.json`.

```bash
skills-orchestrator adapters export claude-skills \
  --config config/skills.yaml \
  --output-dir .claude/skills \
  --manifest-output claude-skills-export.json \
  --force

skills-orchestrator schema validate \
  --kind claude-skills-export \
  --input claude-skills-export.json
```

The root object MUST include:

| Field | Constraint |
| --- | --- |
| `schema_version` | MUST be `skills-orchestrator.claude-skills-export.v1`. |
| `config` | Source SkillOps config path used for export. |
| `output_dir` | Directory containing generated Claude-style skill bundles. |
| `summary.exported` | Number of exported skills. |
| `skills[]` | Exported skill entries with `id`, source path, and generated bundle path. |

This manifest proves file-format export coverage. It MUST NOT be treated as proof that Claude Code
or another runtime loaded the generated bundles.

## Supply-chain SBOM Contract

The package SBOM command emits CycloneDX JSON for the Python package distribution surface. The
registered schema kind is `supply-chain-sbom`.

```bash
skills-orchestrator supply-chain sbom --output package-sbom.cdx.json
skills-orchestrator schema validate --kind supply-chain-sbom --input package-sbom.cdx.json
```

CycloneDX is the authoritative external vocabulary for this artifact. Skills Orchestrator only
validates the minimum shape it emits.

## Implementer Notes And Examples

Third-party implementations SHOULD treat the JSON Schema files as executable tests and this section
as the semantic guide for edge cases that schemas cannot fully express.

### Minimal Registry Diff Example

A changed skill with content and governance drift SHOULD expose both the machine-readable change
keys and reviewer-facing field values:

```json
{
  "schema_version": "skills-orchestrator.registry-diff.v1",
  "summary": {
    "added": 0,
    "removed": 0,
    "changed": 1,
    "duplicate_id_changes": 0
  },
  "added": [],
  "removed": [],
  "changed": [
    {
      "registry_key": "config/skills.yaml::skills/review.md::team-review",
      "id": "team-review",
      "skill": {
        "name": "Team Review",
        "status": "passive",
        "path": "skills/review.md",
        "governance": {
          "owner": "agent-platform",
          "source": "internal://skills/team-review-v2",
          "version": "1.0.1",
          "lifecycle": "active",
          "approvers": ["security", "staff-engineering"],
          "reviewed_at": "2026-06-21",
          "expires_at": "2026-12-21",
          "license": "Apache-2.0",
          "provenance": {
            "source_url": "https://raw.githubusercontent.com/example/skills/0123456789abcdef0123456789abcdef01234567/review.md",
            "source_ref": "main",
            "source_commit": "0123456789abcdef0123456789abcdef01234567",
            "content_hash": "sha256:222222222222",
            "fetched_at": "2026-06-21T00:00:00Z"
          }
        }
      },
      "changes": {
        "content_hash": {
          "before": {"algorithm": "sha256", "value": "111111111111"},
          "after": {"algorithm": "sha256", "value": "222222222222"}
        },
        "governance": {
          "before": {
            "owner": "platform-team",
            "source": "internal://skills/team-review",
            "version": "1.0.0",
            "lifecycle": "active",
            "approvers": ["security"],
            "license": "MIT"
          },
          "after": {
            "owner": "agent-platform",
            "source": "internal://skills/team-review-v2",
            "version": "1.0.1",
            "lifecycle": "active",
            "approvers": ["security", "staff-engineering"],
            "license": "Apache-2.0"
          }
        }
      }
    }
  ],
  "duplicate_id_changes": []
}
```

Markdown registry diffs SHOULD render owner, source, version, lifecycle, approver, review window,
license, provenance, status, and hash changes directly for human review. Markdown remains a
presentation format; consumers MUST NOT parse it as the stable contract.

### Diagnostic And Error Code Conventions

- `SO###` codes are `check` diagnostics and MAY be emitted as SARIF rules.
- `DOCTOR_*` codes are advisory readiness findings. They are not skill metadata errors.
- JSON Schema validation errors are reported by schema path and instance path; v1 does not assign
  stable numeric codes to every schema violation.
- Implementations MAY add warning or info codes, but MUST NOT reuse an existing code with different
  semantics.

### Boundary Cases

- `conflict_with` MAY be one-way. A resolver MAY enforce the one-way conflict, while conformance
  tooling SHOULD warn that asymmetric conflicts are weaker audit evidence than symmetric conflicts.
- Missing skill files referenced by explicit `skills[].path` entries MUST keep their registry
  entries and MUST set `missing_file` to `true`.
- Missing files from `skill_dirs` auto-discovery are not retained as registry entries because the
  deleted file is no longer discoverable. Registry diffs SHOULD represent these as removed entries
  when comparing two snapshots. A combo or zone reference to a no-longer-discovered skill MAY fail
  validation before registry generation.
- Unknown additive fields in v1 artifacts MUST be ignored by default by non-strict consumers.
- Absolute local paths SHOULD be redacted in Markdown or comments intended for pull requests.
- Hosted registries, dashboards, and GitHub Apps SHOULD consume generated artifacts. They SHOULD
  NOT reimplement resolver semantics unless they also run the same conformance checks.

## Non-goals

SkillOps Contract v1 does not define:

- an agent runtime or workflow engine,
- a hosted registry API,
- cryptographic signing or provenance attestation,
- a replacement for SARIF, CycloneDX, OPA, MCP, or AGENTS.md,
- a public adopter list,
- foundation governance or project maturity status.
