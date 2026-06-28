# Agent Runtime Image Contract Example

This example shows how to describe a containerized agent runtime as a
machine-checkable governance artifact without making Skills Orchestrator run that
agent.

The contract is intentionally evidence-first:

- no model invocation,
- no worker queue,
- no provider admin API,
- no claim that SkillOps enforces tenant isolation at runtime.

It records the review boundary around an external agent image: immutable image
digest, SBOM/provenance references, tenant scope, filesystem/network/secret
permissions, adapter surfaces, handoff requirements, and evaluation gates.

## When To Use This

Use this fixture when a platform team wants to run agent workers from containers,
for example:

- a Codex or Claude Code worker in a devcontainer-like sandbox,
- an OpenAI Agents SDK worker packaged as an internal image,
- an A2A-facing service image,
- a queue worker that consumes governed SkillOps instructions.

SkillOps does not recommend one official agent image. The durable contract is
that whatever image you run should be pinned, reviewable, and connected to
evidence.

## Validate The Happy Path

```bash
skills-orchestrator schema validate \
  --kind agent-runtime-image \
  --input examples/agent-runtime-image/codex-worker-image.json
```

## Validate The Negative Fixture

This fixture is expected to fail because it uses a floating `latest` digest and
requests privileged filesystem, unrestricted network, and service-account secret
access without the required human approval gates.

```bash
skills-orchestrator schema validate \
  --kind agent-runtime-image \
  --input examples/agent-runtime-image/invalid-floating-tag.json \
  --format json
```

## Why This Matters

Multi-agent systems often become hard to trust because the worker image, prompt
surface, permissions, tenant scope, and release evidence live in different
places. This artifact puts those facts into one CI-reviewable envelope.

Use it next to existing SkillOps evidence:

```text
evidence/evidence-manifest.json
evidence/registry-graph.json
evidence/adapter-inspect.json
evidence/container-provenance.json
evidence/container-sbom.cdx.json
examples/agent-handoff/release-review-handoff.json
examples/agent-runtime-image/codex-worker-image.json
```

The runtime remains responsible for actually starting containers, enforcing
network policy, injecting secrets, applying budgets, handling retries, and
isolating tenants.
