# Conformance

This document defines how to verify compatibility with SkillOps Contract v1. Conformance is based
on executable checks, not project branding.

## Levels

The executable shortcut for the core suite is:

```bash
skills-orchestrator conformance run \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard

skills-orchestrator conformance run \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --profile enterprise \
  --format json > evidence/conformance.json

skills-orchestrator schema validate \
  --kind conformance \
  --input evidence/conformance.json

skills-orchestrator schema list --format json > evidence/schema-catalog.json
skills-orchestrator schema validate \
  --kind schema-catalog \
  --input evidence/schema-catalog.json

skills-orchestrator schema audit --format json > evidence/schema-audit.json
skills-orchestrator schema validate \
  --kind schema-audit \
  --input evidence/schema-audit.json
```

The core suite includes positive contract checks and a negative conformance suite. The negative
suite verifies that intentionally invalid skill projects trigger expected findings for missing
governance metadata, invalid parser-level metadata, duplicate ids, review-window failures, and
external skill trust metadata. It currently covers these representative rule families:

| Area | Expected rules |
| --- | --- |
| Duplicate skill identity | `SO002` |
| Team governance metadata | `SO008`, `SO009`, `SO010`, `SO011`, `SO012` |
| Parser-level skill metadata | `SO013` |
| Review-window integrity | `SO015`, `SO016` |
| External import trust | `SO019`, `SO020` |

The negative suite is not a complete fuzzing harness. Its purpose is to prove that the public
contract rejects the highest-value malformed inputs a platform team would use as CI gate fixtures.
The same rule families are also published as copyable projects under
`examples/negative-conformance/` for downstream CI and third-party implementation tests.

### Level 1: Local SkillOps

A project is Level 1 conformant when it has a valid Skills Orchestrator config and skill metadata:

```bash
skills-orchestrator schema validate --kind config --input config/skills.yaml
skills-orchestrator check --config config/skills.yaml
```

When the project claims team governance, it MUST also pass:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

When the project claims engineering-grade governance, it SHOULD pass:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

Engineering-grade conformance includes trust metadata. Each skill SHOULD declare an SPDX-style
`license`, reviewed skills SHOULD include `reviewed_at` and `expires_at`, and externally sourced
skills SHOULD carry observed import `provenance` with `source_url`, `source_ref`, `source_commit`,
`content_hash`, and `fetched_at`.

### Level 2: CI Evidence

A project is Level 2 conformant when it produces machine-readable diagnostics and release evidence:

```bash
mkdir -p evidence

skills-orchestrator check --config config/skills.yaml --format json \
  > evidence/check.json
skills-orchestrator check --config config/skills.yaml --format sarif \
  > evidence/check.sarif
skills-orchestrator explainability build \
  --check-json evidence/check.json \
  --config config/skills.yaml \
  --output evidence/ci-explainability.json \
  --force
skills-orchestrator evidence export --config config/skills.yaml --out evidence

skills-orchestrator schema validate --kind check --input evidence/check.json
skills-orchestrator schema validate \
  --kind ci-explainability \
  --input evidence/ci-explainability.json
skills-orchestrator schema validate --kind evidence --input evidence/evidence-manifest.json
```

`evidence/check.json` MUST include `policy_trace` entries for CI rule evaluation. This is
conformance evidence for deterministic policy checks, not proof of agent runtime behavior.
`evidence/ci-explainability.json` MUST explain the CI decision, blocking status, failed rules,
locations, and suggested fixes in a machine-readable form.
`evidence/evidence-manifest.json` MUST include a ledger with artifact hashes and a bundle hash.

SARIF should be uploaded to GitHub Code Scanning or an equivalent SARIF consumer when the CI system
supports it.

### Level 3: Registry Review

A project is Level 3 conformant when it can build and compare registry snapshots:

```bash
skills-orchestrator registry build \
  --config-glob "config/skills.yaml" \
  --output evidence/skill-registry.json

skills-orchestrator schema validate \
  --kind registry \
  --input evidence/skill-registry.json

skills-orchestrator registry graph \
  --config-glob "config/skills.yaml" \
  --output evidence/registry-graph.json

skills-orchestrator schema validate \
  --kind registry-graph \
  --input evidence/registry-graph.json
```

Pull request review SHOULD compare a base registry and head registry:

```bash
skills-orchestrator registry diff \
  evidence/registry-before.json \
  evidence/registry-after.json \
  --format json \
  --output evidence/registry-diff.json

skills-orchestrator registry diff \
  evidence/registry-before.json \
  evidence/registry-after.json \
  --format markdown \
  --output evidence/registry-diff.md

skills-orchestrator registry comment-body \
  evidence/registry-diff.md \
  --output evidence/registry-diff-comment.md

skills-orchestrator schema validate \
  --kind registry-diff \
  --input evidence/registry-diff.json
```

### Level 4: Ecosystem Adapter Evidence

A project is Level 4 conformant when adjacent agent ecosystem surfaces are inspected and validated:

```bash
skills-orchestrator adapters inspect --path . --format json \
  > evidence/adapter-inspect.json

skills-orchestrator schema validate \
  --kind adapter-inspect \
  --input evidence/adapter-inspect.json
```

Projects using MCP clients SHOULD also generate an explicit MCP client config scaffold:

```bash
skills-orchestrator adapters export mcp-client-config \
  --config config/skills.yaml \
  --output evidence/mcp-client.json
```

Projects using Claude Skills SHOULD prove export compatibility with a generated bundle manifest:

```bash
skills-orchestrator adapters export claude-skills \
  --config config/skills.yaml \
  --output-dir .claude/skills \
  --manifest-output evidence/claude-skills-export.json \
  --force
```

Projects using OpenAI Agents SDK MAY generate a scaffold and compile it:

```bash
skills-orchestrator adapters export openai-agents-sdk \
  --config config/skills.yaml \
  --output evidence/openai_skillops_agent.py

python -m py_compile evidence/openai_skillops_agent.py
```

### Level 5: Multi-repo Artifact Index

An organization-level rollout is Level 5 conformant when each repository produces a Level 2 evidence
bundle and the platform team can build a single machine-readable index over those bundles:

```bash
skills-orchestrator evidence index \
  --manifest "api=../api/evidence/evidence-manifest.json" \
  --manifest "web=../web/evidence/evidence-manifest.json" \
  --scope-name example-org \
  --output evidence/multi-repo-artifacts.json

skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input evidence/multi-repo-artifacts.json
```

The index SHOULD be generated from CI evidence artifacts, not manually curated. A Level 5 claim MUST
NOT depend on screenshots, hosted dashboards, or runtime agent traces. Those systems may consume the
index, but the conformance evidence remains the generated `multi-repo-artifacts.json` file and the
repository evidence manifests it references.

## GitHub Action Conformance

The shortest CI path is:

```yaml
permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  skillops:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v4.7.9
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
          comment-registry-diff: true
```

The action is conformant when the check passes, SARIF uploads successfully, and PR registry comments
are generated on pull request events.

## Demo Repository

`examples/demo-repo/` is the executable conformance fixture in this repository. The main CI runs it
as a smoke test. A downstream project can copy that directory into a standalone repository and run
the same commands in `examples/demo-repo/README.md`.

`examples/adapter-evidence/` is the Level 4 adapter evidence fixture. It generates Claude Skills
bundles, an MCP client config, and an OpenAI Agents SDK scaffold from one SkillOps config, then
validates adapter inspection evidence.

## Claims

Do not claim Level 2 or higher conformance unless the corresponding artifacts are generated by CI or
a reproducible local command. Screenshots and README examples are not conformance evidence.
