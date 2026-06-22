# Enterprise Dashboard Blueprint

The dashboard should render evidence. It should not execute agents or make policy decisions that
contradict CLI outputs.

## First Dashboard Cards

- readiness score from `doctor --format json`,
- policy findings from `check --format json`,
- owner coverage from `skill-registry.json`,
- duplicate skill ids from registry summary,
- lock drift from diagnostics,
- registry diff summary for pull requests,
- adapter surface detection,
- release evidence file completeness.

## Snapshot Contract

Generate a dashboard snapshot from an evidence bundle:

```bash
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --out evidence

skills-orchestrator dashboard snapshot \
  --evidence-dir evidence \
  --repository example-org/example-repo \
  --ref refs/heads/main \
  --commit "$(git rev-parse HEAD)" \
  --output dashboard-snapshot.json
```

Validate a dashboard snapshot:

```bash
skills-orchestrator schema validate \
  --kind enterprise-dashboard-snapshot \
  --input dashboard-snapshot.json
```

Generate and validate an organization rollup from multiple snapshots:

```bash
skills-orchestrator dashboard rollup \
  --snapshot-glob "snapshots/*.json" \
  --organization example-org \
  --output dashboard-rollup.json

skills-orchestrator schema validate \
  --kind enterprise-dashboard-rollup \
  --input dashboard-rollup.json
```

Snapshots and rollups are intentionally derived. They are safe to cache and render because the
authoritative data remains in registry, evidence, and diagnostic artifacts.

## Access Model

Minimum roles:

| Role | Access |
| --- | --- |
| Developer | View PR registry diff and own repo readiness. |
| Platform team | View all repos, owners, policy drift, and adapter surfaces. |
| Security reviewer | View findings, SARIF links, SBOM, provenance, and release evidence. |
| Auditor | Read-only release evidence and historical snapshots. |

## Non-goals

- no live agent orchestration,
- no prompt execution,
- no proprietary registry semantics,
- no hidden mutation of `skills.yaml` or skill files.
