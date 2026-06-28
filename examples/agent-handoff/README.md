# Agent Handoff Contract Example

This example shows how a supervisor/worker handoff can be represented as a
machine-checkable artifact without making Skills Orchestrator an agent runtime.

The contract is intentionally artifact-first:

- no worker queue,
- no provider admin API,
- no model invocation,
- no runtime scheduling.

It records the governance boundary that a runtime, queue, or agent framework can
consume: tenant scope, supervisor authority, worker tool permissions, task inputs,
expected outputs, evidence requirements, and evaluation gates.

## Validate The Happy Path

```bash
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json
```

## Validate The Negative Fixture

This fixture is expected to fail because a `privileged` worker must explicitly
set `requires_human_approval: true`.

```bash
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/invalid-privileged-worker.json \
  --format json
```

## Why This Matters

In a multi-agent system, the risky part is not only which model is smarter. The
risky part is whether a worker receives too much context, too many tools, or the
wrong tenant boundary. This contract makes that boundary reviewable in CI before
any runtime starts workers.

Use this artifact next to existing SkillOps evidence:

```text
evidence/check.json
evidence/ci-explainability.json
evidence/evidence-manifest.json
examples/agent-handoff/release-review-handoff.json
```

The runtime remains responsible for actual execution, rate limits, secrets,
budget enforcement, retries, and task queues.
