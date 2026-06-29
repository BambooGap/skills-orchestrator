# Manifest And Policy Exports

Skills Orchestrator exposes machine-readable evidence for instruction supply-chain review.

## Native Manifest

The native JSON manifest is the authoritative inventory. It preserves Skills Orchestrator semantics
such as zones, load policies, effective resolver status, content hashes, and diagnostics.

```bash
skills-orchestrator manifest --config config/skills.yaml --format json \
  --include-diagnostics \
  --output instruction-manifest.json
```

Use this artifact for team review, release evidence, and custom organization checks.

## CycloneDX

CycloneDX output is an interoperability adapter for supply-chain tools that already understand BOM
formats.

```bash
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --package my-repo-agent-instructions \
  --output instruction-manifest.cdx.json
```

Use it to put instruction assets into existing BOM vocabulary. Do not treat it as more complete
than the native manifest.

## OPA Input

OPA input exports resolver facts without adding a second runtime policy engine.

```bash
skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
```

Use this when an external policy pipeline needs facts about skill status, conflicts, and effective
load policies.

## Rego Test Fixture

The Rego fixture proves the exported resolver facts can be represented as policy-as-code tests.

```bash
skills-orchestrator policy export --config config/skills.yaml --format rego-test \
  --output skills_orchestrator_policy_test.rego
opa test skills_orchestrator_policy_test.rego
```

## Authority Model

| Artifact | Authority |
| --- | --- |
| `skills.yaml` and skill files | Source of truth. |
| `skills.lock.json` | Reproducibility and drift detection. |
| Native manifest | Full inventory and audit evidence. |
| CycloneDX | Supply-chain vocabulary adapter. |
| OPA input / Rego test | Policy proof and external integration surface. |

If artifacts disagree, regenerate them from source and review the diff.
