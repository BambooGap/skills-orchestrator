# Documentation Index

Use this page as the team entry point for Skills Orchestrator.

## By Role

| Role | Start Here | Goal |
| --- | --- | --- |
| Repository maintainer | [Install](install.md), [GitHub Action](github-action.md) | Add a working skill check to one repo. |
| Platform owner | [Adoption Playbook](adoption-playbook.md), [Team Standardization](team-standardization.md), [CI/CD](CI_CD.md), [Conformance](../CONFORMANCE.md) | Roll the same contract across multiple repos. |
| Security reviewer | [Manifest And Policy Exports](manifest-policy-exports.md), [Policy Packs](policy-packs.md), [Compatibility](../COMPATIBILITY.md) | Review instruction assets with machine-readable evidence. |
| Release owner | [Release Verification](release-verification.md), [Registry And Evidence](registry-evidence.md), [Docker Usage](docker.md) | Produce repeatable release evidence. |
| Agent runtime owner | [MCP Server](MCP_SERVER.md), [Adapters](adapters.md), [Pipelines](PIPELINES.md) | Route runtime context and preserve workflow state. |
| External evaluator | [SkillOps Contract](../SPEC.md), [Conformance](../CONFORMANCE.md), [Demo Repo](../examples/demo-repo/README.md) | Verify the project as a technical contract, not only a CLI. |
| Pilot team | [Adoption Playbook](adoption-playbook.md), [Pilot Repos](../examples/pilot-repos/README.md), [GitHub Action](github-action.md) | Copy a realistic starter pack into one production-like repo. |
| Agent ecosystem integrator | [Adapters](adapters.md), [Adapter Evidence Example](../examples/adapter-evidence/README.md), [Conformance](../CONFORMANCE.md) | Generate Claude Skills, MCP client, and OpenAI Agents SDK evidence from one SkillOps config. |
| Commercial product owner | [Open-core Boundary](open-core-boundary.md), [GitHub App Blueprint](github-app.md), [Hosted Registry](hosted-registry.md), [Enterprise Dashboard](enterprise-dashboard.md) | Build hosted products around OSS artifact contracts. |

## Core Concepts

- [Zones](ZONES.md): map teams, directories, or repo areas to different instruction policies.
- [Pipelines](PIPELINES.md): turn multiple skills into gated runtime workflows.
- [Instruction Supply Chain Roadmap](instruction-supply-chain-roadmap.md): long-term ecosystem direction.
- [Enterprise Narrative](enterprise.md): positioning, buyers, non-goals, and ecosystem routing.
- [Registry And Evidence](registry-evidence.md): doctor, registry graph, evidence ledger, and integration catalog for SkillOps rollout.
- [Adapters](adapters.md): AGENTS.md, Claude Skills, MCP client, and OpenAI Agents SDK bridge surfaces.
- [Adapter Evidence Example](../examples/adapter-evidence/README.md): executable adapter fixture for Claude Skills export, MCP client config, and OpenAI Agents SDK scaffold.
- [Release Trust Example](../examples/release-trust/README.md): external skill trust metadata and container release verification fixture.
- [Policy Packs](policy-packs.md): team-standard, engineering-grade, license allowlists, and import provenance checks.
- [SkillOps Contract](../SPEC.md): executable v1 artifact contract for metadata, registry, diff, evidence, and adapters.
- [Conformance](../CONFORMANCE.md): reproducible checks for local, CI, registry, and adapter conformance.
- [Compatibility Policy](../COMPATIBILITY.md): stable contract surfaces, additive changes, and migration rules.
- [Security Policy](../SECURITY.md): vulnerability reporting, MCP trust model, HMAC audit, and import provenance boundaries.
- [Demo Repo](../examples/demo-repo/README.md): runnable end-to-end demo for PR review and evidence generation.
- [Adoption Playbook](adoption-playbook.md): 15-minute pilot path and promotion criteria from advisory to blocking gates.
- [Pilot Repository Examples](../examples/pilot-repos/README.md): copyable starter packs for Healthchecks, Umami, and Woodpecker-style repositories.
- [Open-core Boundary](open-core-boundary.md): what stays open-source and what belongs in hosted/enterprise layers.
- [Commercial Handoff Examples](../examples/commercial-handoff/README.md): schema-valid example payloads for future hosted consumers.

## First Production Path

1. Install the CLI from PyPI or Docker.
2. Run `skills-orchestrator check --config config/skills.yaml`.
3. Generate and commit or review `skills.lock.json`.
4. Add the GitHub Action.
5. Enable `builtin/team-standard` policy pack.
6. Run `skills-orchestrator conformance run`.
7. For stricter pilots, enable `builtin/engineering-grade`.
8. Run `skills-orchestrator doctor --profile adopter`.
9. Export manifest, registry graph, and evidence bundle for releases.
10. Verify external skill trust metadata and container release evidence.
11. Enable MCP runtime routing when static checks are stable.
