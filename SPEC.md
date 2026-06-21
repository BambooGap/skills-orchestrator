# SkillOps Contract v1

Status: stable contract surface for `skills-orchestrator` v3.x.

This document defines the machine-checkable contract exposed by Skills Orchestrator. It is not a
vision document and does not define a new agent runtime. A project conforms by producing and
validating the artifacts listed here.

Normative terms use RFC 2119 meanings: MUST, MUST NOT, SHOULD, MAY.

## Scope

SkillOps Contract v1 covers five artifact families:

- skill metadata in `skills.yaml` and skill frontmatter,
- organization registry JSON,
- registry diff JSON and Markdown,
- evidence bundle manifests,
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
| `changed` | Entries with changed fields, keyed by `registry_key` and `id`. |
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

An evidence bundle SHOULD include native JSON check output, SARIF, native instruction manifest, OPA
input, Rego test fixture, doctor report, registry JSON, and the evidence manifest.

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

## Supply-chain SBOM Contract

The package SBOM command emits CycloneDX JSON for the Python package distribution surface. The
registered schema kind is `supply-chain-sbom`.

```bash
skills-orchestrator supply-chain sbom --output package-sbom.cdx.json
skills-orchestrator schema validate --kind supply-chain-sbom --input package-sbom.cdx.json
```

CycloneDX is the authoritative external vocabulary for this artifact. Skills Orchestrator only
validates the minimum shape it emits.

## Non-goals

SkillOps Contract v1 does not define:

- an agent runtime or workflow engine,
- a hosted registry API,
- a replacement for SARIF, CycloneDX, OPA, MCP, or AGENTS.md,
- a public adopter list,
- foundation governance or project maturity status.
