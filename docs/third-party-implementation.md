# Third-party Implementation Guide

This guide is for teams that want to implement SkillOps-compatible tooling without depending on
the Python CLI internals. Treat the CLI as the reference implementation and the artifacts below as
the contract.

## Compatibility Boundary

A compatible implementation SHOULD support these stable surfaces:

| Surface | Required behavior |
| --- | --- |
| Schema catalog | Emit or consume schema kinds compatible with `skills-orchestrator schema list --format json`. |
| Config validation | Accept `skills-orchestrator.config.v1` projects and reject invalid config shapes. |
| Diagnostics | Emit stable `SOxxx` rule ids with file, line, severity, and suggested fix when possible. |
| Policy packs | Preserve the meaning of built-in policy pack ids such as `builtin/team-standard` and `builtin/engineering-grade` when claiming parity. |
| Evidence | Produce evidence manifests that validate against `skills-orchestrator.evidence.v1`. |
| Registry | Produce registry, registry diff, and registry graph artifacts that validate against their v1 schemas. |
| Conformance | Pass positive conformance checks and fail the public negative fixtures deterministically. |
| Agent handoff | Treat `agent-handoff` as a preview artifact contract for supervisor/worker delegation metadata, not as proof that a runtime executed workers. |

Compatible tools MAY add local fields or custom rules. They SHOULD keep custom data additive so
existing consumers can ignore unknown fields.

## Minimum Test Matrix

Use this matrix before claiming compatibility:

```bash
skills-orchestrator schema audit --format text

skills-orchestrator conformance run \
  --profile core \
  --config config/skills.yaml

python -m pytest tests/test_negative_conformance_examples.py
```

For an implementation outside this repository, replace the last command with equivalent checks
against `examples/negative-conformance/cases.json`. Each listed case must fail with at least the
expected rule ids.

## Negative Fixture Contract

The negative fixture index is:

```text
examples/negative-conformance/cases.json
```

Each case defines:

| Field | Meaning |
| --- | --- |
| `id` | Stable fixture identifier. |
| `config` | Relative path to the intentionally invalid SkillOps config. |
| `policy_packs` | Built-in policy packs required to trigger the expected diagnostics. |
| `expected_rules` | Rule ids that must appear in the diagnostic output. |

The fixture may produce additional diagnostics when a stricter policy pack is enabled. A compatible
negative test should require `expected_rules` to be a subset of actual rule ids, not an exact match.

## Artifact Validation Loop

When building a compatible producer, validate every emitted artifact:

```bash
skills-orchestrator schema validate --kind check --input check.json
skills-orchestrator schema validate --kind evidence --input evidence/evidence-manifest.json
skills-orchestrator schema validate --kind registry --input evidence/skill-registry.json
skills-orchestrator schema validate --kind registry-diff --input evidence/registry-diff.json
skills-orchestrator schema validate --kind registry-graph --input evidence/registry-graph.json
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json
```

When building a compatible consumer, reject artifacts that fail schema validation and ignore
unknown additive fields unless your consumer explicitly runs in strict mode.

## Rule Id Stability

Rule ids are part of the compatibility surface. A compatible implementation MUST NOT reuse an
existing `SOxxx` id for a different meaning. If a downstream implementation adds local rules, use a
separate namespace such as `ACME001` or `ORG001`.

## Non-goals

Third-party compatibility does not require:

- reusing the Python parser implementation,
- matching terminal text output byte-for-byte,
- implementing hosted dashboards or GitHub App behavior,
- controlling agent runtime execution,
- producing identical artifact ordering when the JSON Schema does not require ordering.

## Release Checklist For Implementers

Before publishing a compatible implementation:

1. run schema validation for every supported output kind,
2. run positive conformance against at least one valid project,
3. run the negative fixture suite,
4. document custom rules and policy packs,
5. publish a compatibility note naming the SkillOps Contract version tested,
6. include migration notes when changing emitted schema versions or rule meanings.
