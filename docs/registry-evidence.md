# Registry And Evidence

`v2.5.0` adds the commercial evidence layer for SkillOps teams:

- `doctor`: local readiness score and actionable findings.
- `registry build`: organization-level skill inventory from one or more configs.
- `registry diff`: PR/release review between two registry snapshots.
- `evidence export`: release evidence bundle for CI artifacts, audits, or customer handoff.
- `integrations list`: adjacent ecosystem catalog for agent runtimes, memory layers, and visualization tools.

## Team Doctor

```bash
skills-orchestrator doctor \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard
```

JSON mode is intended for CI:

```bash
skills-orchestrator doctor \
  --config config/skills.yaml \
  --format json \
  --fail-under 85
```

The doctor checks the normal diagnostics plus commercial artifacts such as CI workflow, GitHub
Action, Dockerfile, `skills.lock.json`, generated `AGENTS.md`, and the versioned test report.

## Organization Registry

Build a local registry:

```bash
skills-orchestrator registry build \
  --config-glob "config/skills.yaml" \
  --output skill-registry.json
```

For multiple repos from an aggregator checkout:

```bash
skills-orchestrator registry build \
  --config-glob "repos/*/config/skills.yaml" \
  --output org-skill-registry.json
```

Diff two registry snapshots:

```bash
skills-orchestrator registry diff \
  registry-before.json \
  registry-after.json \
  --format json
```

The registry is file-based by design. It does not run agents, index code, or require a database.

## Evidence Bundle

```bash
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --out evidence
```

The bundle writes:

- `check.json`
- `check.sarif`
- `instruction-manifest.json`
- `policy-opa-input.json`
- `policy-proof.rego`
- `doctor.json`
- `skill-registry.json`
- `evidence-manifest.json`

Use the folder as a CI artifact or release attachment. It contains metadata and hashes, not raw
runtime task text.

## Integration Catalog

```bash
skills-orchestrator integrations list
skills-orchestrator integrations list --format json
```

The catalog defines ecosystem position, not hard dependencies. `skills-orchestrator` should remain
the SkillOps control plane: skills, routing decisions, policy reports, registry manifests, and audit
evidence. Code graph, business memory, visualization, execution, and multi-agent orchestration tools
should consume those artifacts instead of being embedded into this package.
