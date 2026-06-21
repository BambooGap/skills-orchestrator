# Documentation Index

Use this page as the team entry point for Skills Orchestrator.

## By Role

| Role | Start Here | Goal |
| --- | --- | --- |
| Repository maintainer | [Install](install.md), [GitHub Action](github-action.md) | Add a working skill check to one repo. |
| Platform owner | [Team Standardization](team-standardization.md), [CI/CD](CI_CD.md) | Roll the same contract across multiple repos. |
| Security reviewer | [Manifest And Policy Exports](manifest-policy-exports.md), [Policy Packs](policy-packs.md) | Review instruction assets with machine-readable evidence. |
| Release owner | [Release Verification](release-verification.md), [Registry And Evidence](registry-evidence.md), [Docker Usage](docker.md) | Produce repeatable release evidence. |
| Agent runtime owner | [MCP Server](MCP_SERVER.md), [Adapters](adapters.md), [Pipelines](PIPELINES.md) | Route runtime context and preserve workflow state. |
| External evaluator | [SkillOps Contract](../SPEC.md), [Conformance](../CONFORMANCE.md), [Demo Repo](../examples/demo-repo/README.md) | Verify the project as a technical contract, not only a CLI. |
| Commercial product owner | [Open-core Boundary](open-core-boundary.md), [GitHub App Blueprint](github-app.md), [Hosted Registry](hosted-registry.md), [Enterprise Dashboard](enterprise-dashboard.md) | Build hosted products around OSS artifact contracts. |

## Core Concepts

- [Zones](ZONES.md): map teams, directories, or repo areas to different instruction policies.
- [Pipelines](PIPELINES.md): turn multiple skills into gated runtime workflows.
- [Instruction Supply Chain Roadmap](instruction-supply-chain-roadmap.md): long-term ecosystem direction.
- [Enterprise Narrative](enterprise.md): positioning, buyers, non-goals, and ecosystem routing.
- [Registry And Evidence](registry-evidence.md): doctor, registry, evidence bundle, and integration catalog for commercial rollout.
- [Adapters](adapters.md): AGENTS.md, Claude Skills, MCP client, and OpenAI Agents SDK bridge surfaces.
- [SkillOps Contract](../SPEC.md): executable v1 artifact contract for metadata, registry, diff, evidence, and adapters.
- [Conformance](../CONFORMANCE.md): reproducible checks for local, CI, registry, and adapter conformance.
- [Security Policy](../SECURITY.md): vulnerability reporting, MCP trust model, HMAC audit, and import provenance boundaries.
- [Demo Repo](../examples/demo-repo/README.md): runnable end-to-end demo for PR review and evidence generation.
- [Open-core Boundary](open-core-boundary.md): what stays open-source and what belongs in hosted/enterprise layers.
- [Commercial Handoff Examples](../examples/commercial-handoff/README.md): schema-valid example payloads for future hosted consumers.

## First Production Path

1. Install the CLI from PyPI or Docker.
2. Run `skills-orchestrator check --config config/skills.yaml`.
3. Generate and commit or review `skills.lock.json`.
4. Add the GitHub Action.
5. Enable `builtin/team-standard` policy pack.
6. Run `skills-orchestrator doctor`.
7. Export manifest, registry, and evidence bundle for releases.
8. Enable MCP runtime routing when static checks are stable.
