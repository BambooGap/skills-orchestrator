# Registry And Evidence

`v3.0.x` hardens the open-source evidence layer for SkillOps teams:

- `doctor`: local readiness score and actionable findings.
- `registry build`: organization-level skill inventory from one or more configs.
- `registry diff`: PR/release review between two registry snapshots, including Markdown output.
- `evidence export`: release evidence bundle for CI artifacts, audits, or customer handoff.
- `schema validate`: machine-checkable JSON Schema contracts for generated files.
- `integrations list`: adjacent ecosystem catalog for agent runtimes, memory layers, and visualization tools.
- `adapters inspect`: detected AGENTS.md, Claude Skills, MCP, and Agents SDK surfaces.
- `supply-chain sbom`: Python package SBOM for the software distribution surface.

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

For PR review, generate Markdown instead of wiring the CLI to GitHub APIs:

```bash
skills-orchestrator registry diff \
  registry-before.json \
  registry-after.json \
  --format markdown \
  --output registry-diff.md

skills-orchestrator registry comment-body registry-diff.md \
  --output registry-diff-comment.md
```

The registry is file-based by design. It does not run agents, index code, or require a database.

## Schema Validation

Validate config and generated JSON artifacts independently in CI:

```bash
skills-orchestrator schema validate --kind config --input config/skills.yaml
skills-orchestrator schema validate --kind check --input evidence/check.json
skills-orchestrator schema validate --kind manifest --input evidence/instruction-manifest.json
skills-orchestrator schema validate --kind policy-opa-input --input evidence/policy-opa-input.json
skills-orchestrator schema validate --kind doctor --input evidence/doctor.json
skills-orchestrator schema validate --kind registry --input evidence/skill-registry.json
skills-orchestrator schema validate --kind registry-diff --input evidence/registry-diff.json
skills-orchestrator schema validate --kind adapter-inspect --input evidence/adapter-inspect.json
skills-orchestrator schema validate --kind supply-chain-sbom --input package-sbom.cdx.json
skills-orchestrator schema validate --kind evidence --input evidence/evidence-manifest.json
```

SARIF and CycloneDX keep using their upstream schemas; Skills Orchestrator only owns its native
config and artifact contracts. The commercial handoff schemas are additive contracts for future
GitHub App, hosted registry, and enterprise dashboard consumers:

```bash
skills-orchestrator schema validate \
  --kind github-app-installation \
  --input examples/commercial-handoff/installation.json

skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/commercial-handoff/registry-ingest.json

skills-orchestrator schema validate \
  --kind enterprise-dashboard-snapshot \
  --input examples/commercial-handoff/dashboard-snapshot.json
```

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

## Adapter Inspection

```bash
skills-orchestrator adapters inspect --path . --format json > adapter-inspect.json
skills-orchestrator adapters export mcp-client-config --config config/skills.yaml
skills-orchestrator adapters export openai-agents-sdk --config config/skills.yaml
```

Adapters are bridge contracts. They do not replace `build`, `sync agents-md`, MCP `serve`, or the
native manifest.
