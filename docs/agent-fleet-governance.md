# Agent Fleet Governance

> Status: v4.8.4 adoption guidance.
>
> Scope: governance for AI instruction artifacts used by multi-agent, multi-tenant, and
> multi-project systems. This is not a runtime orchestration specification.

## Why This Exists

Agent systems are moving away from a single general assistant toward fleets of specialized agents:
a lead or manager agent, domain specialists, tool-bound workers, evaluators, background sessions,
and team-channel agents. At the same time, enterprise deployment is moving toward project-scoped
keys, budgets, rate limits, service accounts, admin APIs, audit logs, and usage analytics.

That creates a governance problem before it creates a runtime problem:

- Which instruction assets are allowed to run in a project?
- Which owner, source, license, review window, and lifecycle apply to each skill?
- Which agent surface consumes each instruction asset?
- Which tool boundary, MCP server, handoff path, or model family is expected?
- Which evidence proves that the instruction assets were checked before release?
- Which tenant, project, or cluster is allowed to consume the resulting artifact?

Skills Orchestrator should answer those questions through CI artifacts, schemas, policy packs,
registry output, conformance checks, and evidence bundles. It should not become a queue, runtime
scheduler, hosted control plane, or replacement for OpenAI Agents SDK, Claude Code, A2A, MCP,
LangGraph, CrewAI, AutoGen, or a cloud provider's tenant administration APIs.

## Current Market Signal

The current direction is not one winner-take-all agent runtime. It is a stack split:

| Layer | Direction | SkillOps position |
| --- | --- | --- |
| Agent orchestration | Manager agents, handoffs, agents-as-tools, evaluator loops, parallel workers | Produce governed instruction artifacts that those runtimes can consume. |
| Enterprise administration | Project-scoped access, service accounts, budgets, rate limits, admin APIs, audit logs | Record ownership and evidence metadata; do not manage provider accounts directly. |
| Team collaboration | Agents joining Slack, CI, IDE, issue tracker, and repo workflows | Keep instruction policy and evidence portable across surfaces. |
| Agent interoperability | A2A-style discovery, capability cards, JSON-RPC, streaming, async tasks | Treat protocol metadata as an adapter/export surface, not a core runtime dependency. |
| Context and tool boundaries | Per-agent prompts, tool allowlists, MCP scopes, permissions, worktree isolation | Validate the declared boundary as an instruction governance concern. |

The practical conclusion is:

> The durable surface is not "the one orchestrator." It is the governance contract for agent
> instruction assets across many orchestrators.

## Product Boundary

### Own

- Skill metadata schema, validation, and policy diagnostics.
- Agent-surface adapter evidence for AGENTS.md, Claude Skills, MCP client config, OpenAI Agents SDK
  scaffolds, and future protocol metadata when it is stable enough to fixture.
- Registry, registry diff, registry graph, and multi-repo artifact index.
- Evidence bundles, hash ledgers, SBOM/provenance verification, conformance reports, and CI
  explainability.
- Documentation that maps instruction assets to tenant/project/cluster governance without calling
  provider admin APIs.

### Do Not Own

- Runtime task scheduling.
- Multi-agent queue semantics.
- Provider tenant provisioning.
- Provider audit-log ingestion as a default CLI behavior.
- A2A or MCP protocol implementation beyond compatible adapter evidence.
- Hosted dashboard, GitHub App, or registry backend inside the OSS CLI.

## Agent Fleet Governance Model

Use this model to describe multi-agent adoption without over-claiming runtime control.

```text
Tenant / Organization
  -> Project / Workspace / Cluster
    -> Repository
      -> Agent Surface
        -> Instruction Artifact
          -> Policy Pack
          -> Evidence Bundle
```

### Tenant Or Organization

The administrative boundary that owns budgets, users, service accounts, and audit exports.

SkillOps metadata can reference the owner or tenant id, but the CLI should not create, update, or
delete provider-side tenants, projects, users, service accounts, keys, or budgets.

### Project, Workspace, Or Cluster

The operational boundary where agents run. For example:

- an OpenAI project,
- an Anthropic workspace or Claude Code managed setting scope,
- a Kubernetes namespace,
- a GitHub organization or repository group,
- an internal platform project.

SkillOps should treat this as metadata used for routing evidence and policy scope.

### Repository

The source of governed instruction assets and CI evidence.

Each repository should be able to run:

```bash
skills-orchestrator check --config config/skills.yaml --policy-pack builtin/engineering-grade
skills-orchestrator conformance run --profile enterprise
skills-orchestrator evidence export --config config/skills.yaml --out evidence
```

### Agent Surface

The place where governed instructions are consumed:

- AGENTS.md,
- Claude Skills,
- Claude Code subagent definitions,
- MCP client config,
- OpenAI Agents SDK scaffold,
- future A2A-facing agent card metadata,
- hosted registry or GitHub App consumers.

SkillOps should inspect and export these surfaces as files and evidence. It should not claim that
the runtime used the files unless a downstream integration provides its own runtime evidence.

### Instruction Artifact

The governed asset. In this project, the core instruction artifact remains a skill markdown file
with structured metadata.

Required governance questions:

- Who owns it?
- Where did it come from?
- What license applies?
- Which lifecycle state is it in?
- When was it last reviewed?
- Which policy pack evaluated it?
- Which evidence bundle contains the result?

## Recommended Metadata Direction

Do not add these fields as mandatory schema requirements until real adopters need them. Use them as
future-compatible guidance for teams that already operate multi-agent or multi-tenant systems.

```yaml
agent_surfaces:
  - type: claude-code-subagent
    name: security-reviewer
    permissions: read-only
    tools:
      allowed: [Read, Grep, Glob]
      denied: [Write, Edit, Bash]
  - type: openai-agents-sdk
    role: evaluator
    handoff: bounded-subtask

tenant_scope:
  provider: openai
  project: billing-agent-prod
  environment: production
  budget_owner: platform-ai

cluster_scope:
  provider: internal
  cluster: agent-prod-us-east
  namespace: ai-governance

handoff_contract:
  mode: manager-agent
  allowed_targets: [security-reviewer, release-engineer]
  requires_evidence: true

evaluation_contract:
  required: true
  artifacts:
    - ci-explainability
    - conformance
    - evidence-manifest
```

The v4.x rule is intentionally conservative:

- document these concepts,
- keep current schema stable,
- add fixtures only after a real adapter or adopter needs them,
- do not force all teams to model tenants and clusters before they have them.

## A2A And Protocol Strategy

A2A is important because it formalizes agent-to-agent communication, capability discovery, long
running tasks, and collaboration without exposing internal memory or tools. That maps well to the
future of multi-agent work, but it should not become a hard dependency of the SkillOps CLI.

SkillOps should stay protocol-adjacent:

1. Preserve governed instruction metadata that could be exported into agent cards or adapter files.
2. Validate source, owner, license, lifecycle, review window, and evidence before export.
3. Keep A2A-specific examples as adapter fixtures once downstream usage is real.
4. Avoid implementing A2A task lifecycle, streaming, push notifications, or runtime auth.

This keeps the project useful whether teams use A2A, MCP, OpenAI Agents SDK handoffs, Claude Code
subagents, queues, or an internal orchestration framework.

## Adoption Path

### Level 1: Single Repo Skill Governance

Use the existing team-standard starter kit and GitHub Action.

Exit criteria:

- `check --fail-on warning` passes.
- `doctor --profile adopter --fail-under 100` passes.
- `conformance run --profile core` passes.
- `evidence export` produces schema-valid artifacts.

### Level 2: Agent Surface Evidence

Add adapter inspection and export.

Exit criteria:

- AGENTS.md is generated and current.
- Claude Skills export round-trip fixture passes where relevant.
- MCP client config or OpenAI Agents SDK scaffold compiles where relevant.
- Adapter inspection evidence is included in the evidence bundle.

### Level 3: Multi-repo Artifact Governance

Aggregate multiple repository evidence bundles without a hosted backend.

Exit criteria:

- `evidence index` produces schema-valid `multi-repo-artifacts.json`.
- Missing or tampered repository artifacts are detected.
- Platform owners can compare repositories without reading source code.

### Level 4: Agent Fleet Governance

Map instruction assets to agent surfaces and tenant/project scopes as metadata.

Exit criteria:

- Each production agent surface has an owner and evidence manifest.
- Each externally imported skill has provenance, license, source commit, and review metadata.
- Each project or cluster has a documented policy pack and evidence export path.
- CI explains why an instruction artifact was blocked before runtime.

## v4.x And v5.x Roadmap Boundary

### v4.x

- Keep the CLI focused on check, schema, evidence, registry, conformance, release trust, adapters,
  and post-release smoke.
- Add documentation, fixtures, and adoption guidance for agent fleet governance.
- Keep all multi-tenant and multi-cluster concepts as metadata and artifact contracts.
- Do not add provider admin API write operations.

### v5.x

Consider adding a stable agent fleet manifest only after at least one external adopter or adapter
needs it.

Candidate contract surfaces:

- agent surface inventory,
- tool boundary declarations,
- tenant/project/cluster scope metadata,
- handoff and evaluation evidence requirements,
- protocol export fixtures for A2A-facing agent cards if the ecosystem stabilizes around them.

Do not treat v5 as a rewrite. Treat it as a contract hardening line.

## Recommended Language

Use:

> Skills Orchestrator governs AI instruction artifacts across CI, repositories, and agent
> consumption surfaces.

Use:

> SkillOps helps platform teams verify instruction ownership, provenance, policy conformance,
> adapter evidence, and release trust before multi-agent runtimes consume those instructions.

Avoid:

> Skills Orchestrator is a multi-agent runtime.

Avoid:

> Skills Orchestrator replaces A2A, MCP, OpenAI Agents SDK, Claude Code, or provider audit systems.

Avoid:

> Skills Orchestrator manages tenants, budgets, service accounts, or provider API keys.

## Source References

- OpenAI Agents SDK agent orchestration:
  <https://openai.github.io/openai-agents-python/multi_agent/>
- OpenAI Projects:
  <https://help.openai.com/en/articles/9186755-managing-your-work-in-the-api-platform-with-projects>
- OpenAI Admin and Audit Logs API:
  <https://help.openai.com/en/articles/9687866-admin-and-audit-logs-api-for-the-api-platform>
- Claude Code overview:
  <https://code.claude.com/docs/en/overview>
- Claude Code subagents:
  <https://code.claude.com/docs/en/sub-agents>
- Claude Tag:
  <https://www.anthropic.com/news/introducing-claude-tag>
- Agent2Agent protocol:
  <https://github.com/a2aproject/A2A>
