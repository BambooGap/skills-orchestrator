# Supervisor Governance Model

> Status: v4.8.29 adoption guidance.
>
> Scope: how a lead agent can coordinate specialized agents without turning Skills Orchestrator
> into a runtime scheduler.

## Short Answer

A lead AI agent should not be trusted as the only control plane for other agents.

The reliable pattern is:

```text
Human / CI trigger
  -> deterministic supervisor loop
    -> lead agent plans and delegates
      -> isolated worker agent contexts
        -> structured results
      -> evaluator / reviewer step
    -> policy gate
  -> evidence bundle and audit trail
```

The lead agent can decide, summarize, and revise. The surrounding system must enforce:

- tenant and project boundaries,
- worker permissions,
- tool allowlists and denylists,
- context isolation,
- budget and rate-limit policy,
- timeout and retry behavior,
- structured handoff contracts,
- result validation,
- evidence export.

That distinction is the whole product boundary: Skills Orchestrator governs the instruction assets
and evidence that this loop consumes. It does not need to run the loop itself.

## Correcting The Thread Analogy

The "each conversation window is like a thread" intuition is useful, but incomplete.

| User Mental Model | More Precise Model |
| --- | --- |
| Conversation window | Session context with history, tools, current repo state, and permissions. |
| Subagent | Worker context with its own prompt, tool boundary, model choice, evidence requirements, and output contract. |
| Lead agent | Planner and integrator that can delegate work and merge results. |
| Thread list | Runtime/session registry, not automatically a governance system. |
| Chat handoff | Structured delegation event that should carry task, allowed tools, input facts, expected output, and stop condition. |

The UI can look like threads. The control plane underneath should behave more like CI:

- every worker has a scoped job,
- every job has an owner and timeout,
- every output has a schema or reviewer expectation,
- every privileged tool call has a permission boundary,
- every release has evidence.

## Why One AI Cannot Be The Whole Control Plane

LLMs are good at planning, synthesis, and judgment under uncertainty. They are not good enough to
be the only source of truth for:

- access control,
- cross-tenant isolation,
- key and secret boundaries,
- budget enforcement,
- idempotency,
- audit retention,
- immutable release evidence,
- deterministic failure behavior.

So the supervisor architecture should split authority:

| Responsibility | Best Owner |
| --- | --- |
| Task decomposition | Lead agent |
| Specialist execution | Worker agents |
| Tool permission enforcement | Runtime / platform |
| Tenant isolation | Platform / provider boundary |
| Policy conformance | CI / SkillOps |
| Evidence and release audit | SkillOps evidence bundle |
| Final human-facing synthesis | Lead agent or human reviewer |

This keeps the lead agent powerful without making it a root administrator.

## Minimal Supervisor Contract

Every delegated task should have a machine-readable contract, even if the runtime is simple.

```yaml
supervisor_contract:
  id: release-review-supervisor
  owner: platform-ai
  tenant_scope:
    provider: internal
    project: payments-prod
    environment: production
  workers:
    - id: security-reviewer
      purpose: Review changed code for security-sensitive regressions.
      allowed_tools: [Read, Grep, Glob]
      denied_tools: [Write, Edit, Bash]
      required_outputs:
        - risk_summary
        - blocking_findings
        - evidence_paths
    - id: test-runner
      purpose: Run approved test commands and summarize failures.
      allowed_tools: [Read, Bash]
      denied_tools: [Write, Edit]
      required_outputs:
        - command_log
        - failing_tests
        - retry_recommendation
  handoff:
    required_fields: [task, scope, inputs, expected_output, stop_condition]
    max_retries: 1
    requires_evaluator: true
  evidence:
    required_artifacts:
      - check-json
      - ci-explainability
      - conformance
      - evidence-manifest
```

Skills Orchestrator now treats this structure as a preview artifact contract through
`agent-handoff` schema validation. It is still not a runtime scheduler: the immediate value is that
teams can reason about agent governance with the same nouns across Codex, Claude Code, OpenAI
Agents SDK, A2A-facing services, queues, or their own internal runtime.

Validate the example contract:

```bash
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json
```

The negative fixtures intentionally fail when a supervisor delegates too much authority or too
little evidence:

```bash
skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/invalid-privileged-worker.json \
  --format json

skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/invalid-privileged-without-human-review.json \
  --format json

skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/invalid-production-evidence.json \
  --format json
```

The current preview contract enforces three CI-reviewable safety properties:

- authorized, running, or completed handoffs must enable evaluation;
- production handoffs must require `evidence-manifest` and `ci-explainability`;
- privileged workers must have explicit approval and a `human-review` gate.

If the worker is packaged as a container image, validate the runtime image boundary separately:

```bash
skills-orchestrator schema validate \
  --kind agent-runtime-image \
  --input examples/agent-runtime-image/codex-worker-image.json
```

This keeps the control split clear: the supervisor can delegate work, the runtime can start worker
containers, and SkillOps can verify that the declared image digest, SBOM/provenance, adapter
surfaces, tenant scope, permissions, handoff requirements, and evaluation gates are reviewable
before execution.

## Handoff Lifecycle

Use this lifecycle when designing multi-agent workflows:

1. `plan`: the supervisor identifies work units and selects worker types.
2. `authorize`: the runtime resolves tenant, repo, model, tools, budget, and permission limits.
3. `prepare`: SkillOps supplies governed instructions and evidence for the selected worker.
4. `execute`: the worker runs inside its scoped context.
5. `return`: the worker returns structured output and artifact references.
6. `evaluate`: an evaluator, policy gate, or human reviewer checks the output.
7. `merge`: the supervisor integrates accepted outputs.
8. `record`: evidence, trace, and release artifacts are written.

The lead agent can participate in steps 1, 5, 6, and 7. Steps 2, 3, and 8 should be deterministic
platform behavior.

## Multi-Tenant Rules

For enterprise adoption, multi-agent only becomes valuable if tenant separation is boring and
predictable.

Minimum rules:

- No worker should inherit secrets from a different tenant or project.
- No worker should receive cross-tenant memory unless the runtime explicitly grants it.
- Project-scoped keys and service accounts should be owned by the platform, not by prompts.
- Budget and rate-limit metadata should be recorded, but provider enforcement should stay in the
  provider/platform layer.
- Evidence bundles should be partitionable by tenant, project, repository, and release.
- A worker's instructions should be reproducible from committed artifacts, not only chat history.

SkillOps can help with the last two immediately. The first four belong to the runtime or provider
control plane.

## What This Project Should Build

### Now

- Keep `check`, `schema`, `evidence`, `registry`, `conformance`, `release trust`, adapters, and
  post-release smoke as the core.
- Document supervisor and worker governance boundaries.
- Keep `agent-handoff` as a preview schema-backed fixture for concrete supervisor/worker handoff
  review.
- Keep `agent-runtime-image` as a preview schema-backed fixture for reviewing containerized worker
  images without making the CLI start those images.
- Keep all supervisor, tenant, and cluster fields optional guidance until real adopters need schema
  enforcement.

### Next

- Add adapter examples for supervisor/worker instruction packs when a real runtime can consume
  them.
- Keep expanding negative fixtures for unsafe worker permissions, stale evidence, or missing
  handoff evidence only when the field model can be enforced by schema.
- Consider a preview `agent-fleet-manifest` schema only when the same metadata appears in at least
  two downstream surfaces.

### Not Yet

- Do not add queues.
- Do not add provider admin write APIs.
- Do not claim to enforce budget or rate limits.
- Do not run arbitrary worker agents from the CLI.
- Do not make A2A, MCP, OpenAI Agents SDK, Claude Code, or any one framework a hard dependency.

## Practical Future Shape

The likely near-term shape is not one universal pattern. It is a family of compatible patterns:

- manager agent calls specialists as tools,
- triage agent hands off to specialists,
- evaluator loop critiques and retries work,
- parallel workers run independent slices,
- Slack/CI/IDE agents join existing team surfaces,
- A2A-like protocols connect opaque agents across servers,
- queues and workflows remain common for production reliability.

That means the durable value is not "own the whole runtime." The durable value is:

> make every agent instruction, worker boundary, handoff contract, and evidence bundle inspectable
> before runtime.

That is the path where an open-source SkillOps project can stay relevant even if the winning
multi-agent runtime changes.
