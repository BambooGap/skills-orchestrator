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
          "approvers": ["security", "staff-engineering"]
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
            "approvers": ["security"]
          },
          "after": {
            "owner": "agent-platform",
            "source": "internal://skills/team-review-v2",
            "version": "1.0.1",
            "lifecycle": "active",
            "approvers": ["security", "staff-engineering"]
          }
        }
      }
    }
  ],
  "duplicate_id_changes": []
}
```

Markdown registry diffs SHOULD render owner, source, version, lifecycle, approver, status, and hash
changes directly for human review. Markdown remains a presentation format; consumers MUST NOT parse
it as the stable contract.

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
- a replacement for SARIF, CycloneDX, OPA, MCP, or AGENTS.md,
- a public adopter list,
- foundation governance or project maturity status.
