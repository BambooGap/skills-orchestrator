# Multi-repo Artifacts Example

This example demonstrates the v4.5 organization-level evidence index.

It turns multiple repository `evidence-manifest.json` files into one machine-readable
`multi-repo-artifacts.json` contract. The output is an audit index, not a dashboard and not an
agent runtime.

## Generate Repository Evidence

From each repository, generate evidence with the normal single-repo command:

```bash
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --out evidence
```

For this repository's pilot fixtures, generate three local evidence bundles:

```bash
for repo in healthchecks umami woodpecker; do
  (
    cd "../pilot-repos/${repo}"
    skills-orchestrator evidence export \
      --config config/skills.yaml \
      --policy-pack builtin/team-standard \
      --out evidence
  )
done
```

## Build The Multi-repo Index

```bash
skills-orchestrator evidence index \
  --manifest "healthchecks=../pilot-repos/healthchecks/evidence/evidence-manifest.json" \
  --manifest "umami=../pilot-repos/umami/evidence/evidence-manifest.json" \
  --manifest "woodpecker=../pilot-repos/woodpecker/evidence/evidence-manifest.json" \
  --scope-name pilot-org \
  --output evidence/multi-repo-artifacts.json \
  --force
```

Or use a glob:

```bash
skills-orchestrator evidence index \
  --manifest-glob "../pilot-repos/*/evidence/evidence-manifest.json" \
  --scope-name pilot-org \
  --output evidence/multi-repo-artifacts.json \
  --force
```

## Validate The Contract

```bash
skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input evidence/multi-repo-artifacts.json
```

Expected result: the schema is valid, `summary.repositories` is `3`, and every indexed repository
has a bundle hash plus artifact references.

## Boundary

`multi-repo-artifacts.json` only references existing evidence artifacts and records their hashes.
It does not execute agents, run workflows, render dashboards, or replace the per-repository
`evidence export` contract.
