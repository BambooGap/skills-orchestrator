# External Consumer Example

This example shows how a hosted registry, GitHub App, or dashboard can consume SkillOps artifacts
without reimplementing the OSS CLI.

It is intentionally static:

- no database,
- no server,
- no login flow,
- no dashboard runtime.

The point is to define the artifact boundary that external products should consume.

## Validate the Consumer Inputs

```bash
skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/external-consumer/hosted-registry-ingest.json

skills-orchestrator schema validate \
  --kind github-app-installation \
  --input examples/external-consumer/github-app-installation.json

skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input examples/external-consumer/multi-repo-artifacts.json
```

## Expected Flow

```text
repository CI
  -> evidence/evidence-manifest.json
  -> evidence/skill-registry.json
  -> evidence/registry-diff.json
  -> evidence/multi-repo-artifacts.json
  -> hosted registry / GitHub App / dashboard
```

External consumers may store, render, and correlate these files. They should not parse skill
Markdown directly, re-run policy packs with different semantics, or turn dashboards into a second
policy engine.

## Boundary

The OSS CLI remains the source of truth for:

- schema validation,
- policy evaluation,
- registry generation,
- evidence bundle generation,
- multi-repo artifact indexing.

Hosted products remain responsible for:

- authentication,
- tenant isolation,
- retention policy,
- comment/check rendering,
- billing,
- operator UX.
