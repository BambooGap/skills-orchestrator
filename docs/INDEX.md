# Documentation Index

Use this page as the team entry point for Skills Orchestrator.

## By Role

| Role | Start Here | Goal |
| --- | --- | --- |
| Repository maintainer | [Install](install.md), [GitHub Action](github-action.md) | Add a working skill check to one repo. |
| Platform owner | [Production Adoption](production-adoption.md), [Adoption Maturity Model](adoption-maturity-model.md), [Adoption Playbook](adoption-playbook.md), [Team Standardization](team-standardization.md), [CI/CD](CI_CD.md), [Conformance](../CONFORMANCE.md) | Roll the same contract across multiple repos. |
| Security reviewer | [Manifest And Policy Exports](manifest-policy-exports.md), [Policy Packs](policy-packs.md), [Compatibility](../COMPATIBILITY.md) | Review instruction assets with machine-readable evidence. |
| Release owner | [Release Verification](release-verification.md), [Release Rollback](release-rollback.md), [Registry And Evidence](registry-evidence.md), [Docker Usage](docker.md) | Produce repeatable release evidence and a rollback path. |
| Agent runtime owner | [MCP Server](MCP_SERVER.md), [Adapters](adapters.md), [Pipelines](PIPELINES.md) | Consume governed context and preserve workflow state. |
| External evaluator | [SkillOps Contract](../SPEC.md), [Conformance](../CONFORMANCE.md), [Third-party Implementation](third-party-implementation.md), [Negative Conformance Fixtures](../examples/negative-conformance/README.md), [Foundation Readiness](foundation-readiness.md), [Demo Repo](../examples/demo-repo/README.md) | Verify the project as a technical contract, not only a CLI. |
| Pilot team | [External Pilot Intake](external-pilot-intake.md), [Adoption Playbook](adoption-playbook.md), [Pilot Repos](../examples/pilot-repos/README.md), [GitHub Action](github-action.md) | Copy a realistic starter pack into one production-like repo. |
| Agent ecosystem integrator | [Agent Fleet Governance](agent-fleet-governance.md), [Supervisor Governance](supervisor-governance.md), [Agent Handoff Contract Example](../examples/agent-handoff/README.md), [Agent Runtime Image Contract Example](../examples/agent-runtime-image/README.md), [Adapters](adapters.md), [Adapter Evidence Example](../examples/adapter-evidence/README.md), [Conformance](../CONFORMANCE.md) | Generate governed agent-surface, handoff, and runtime-image evidence from one SkillOps config. |
| Commercial product owner | [Open-core Boundary](open-core-boundary.md), [GitHub App Blueprint](github-app.md), [Hosted Registry](hosted-registry.md), [Enterprise Dashboard](enterprise-dashboard.md) | Build hosted products around OSS artifact contracts. |

## Core Concepts

- [Zones](ZONES.md): map teams, directories, or repo areas to different instruction policies.
- [Pipelines](PIPELINES.md): turn multiple skills into gated runtime workflows.
- [Instruction Supply Chain Roadmap](instruction-supply-chain-roadmap.md): long-term ecosystem direction.
- [Enterprise Narrative](enterprise.md): positioning, buyers, non-goals, and ecosystem routing.
- [Adoption Maturity Model](adoption-maturity-model.md): artifact-driven levels from local pilot to external adoption.
- [Production Adoption](production-adoption.md): minimum production CI configuration with SHA pins, Docker digests, evidence retention, and runtime boundaries.
- [Agent Fleet Governance](agent-fleet-governance.md): multi-agent, multi-tenant, and multi-project governance boundary for instruction assets.
- [Supervisor Governance](supervisor-governance.md): lead agent, worker agent, handoff, permission, and evidence governance model.
- [Agent Handoff Contract Example](../examples/agent-handoff/README.md): preview schema fixture for supervisor/worker delegation, tenant scope, tool boundaries, evaluation gates, and negative handoff safety cases.
- [Agent Runtime Image Contract Example](../examples/agent-runtime-image/README.md): preview schema fixture for external agent runtime images, permission boundaries, SBOM/provenance, and evaluation gates.
- [Commercial And Foundation Readiness](foundation-readiness.md): honest adoption levels, commercial standard, and foundation-readiness gates.
- [OpenSSF Scorecard Hygiene](foundation-readiness.md#openssf-scorecard-hygiene): public security-health signal alongside CodeQL, pinned Actions, and release attestations.
- [Registry And Evidence](registry-evidence.md): doctor, registry graph, evidence ledger, and integration catalog for SkillOps rollout.
- [Adapters](adapters.md): AGENTS.md, Claude Skills, MCP client, and OpenAI Agents SDK bridge surfaces.
- [Adapter Evidence Example](../examples/adapter-evidence/README.md): executable adapter fixture for Claude Skills export, MCP client config, and OpenAI Agents SDK scaffold.
- [Adapter Negative Fixtures](../examples/adapter-negative/README.md): malformed Claude Skills, MCP config, and OpenAI-looking files that must not be detected as valid adapter surfaces.
- [Release Trust Example](../examples/release-trust/README.md): external skill trust metadata and container release verification fixture.
- [Release Rollback Playbook](release-rollback.md): incident response for bad PyPI, GHCR, GitHub Release, or evidence artifacts.
- [Multi-repo Artifacts Example](../examples/multi-repo-artifacts/README.md): organization-level evidence index over multiple repositories.
- [Policy Packs](policy-packs.md): team-standard, engineering-grade, license allowlists, and import provenance checks.
- [SkillOps Contract](../SPEC.md): executable v1 artifact contract for metadata, registry, diff, evidence, and adapters.
- [Conformance](../CONFORMANCE.md): reproducible checks for local, CI, registry, and adapter conformance.
- [Third-party Implementation Guide](third-party-implementation.md): how to implement compatible producers or consumers without depending on Python internals.
- [Negative Conformance Fixtures](../examples/negative-conformance/README.md): intentionally invalid projects that prove bad instruction artifacts fail with stable rule ids.
- [Compatibility Policy](../COMPATIBILITY.md): stable contract surfaces, additive changes, and migration rules.
- [Security Policy](../SECURITY.md): vulnerability reporting, MCP trust model, HMAC audit, and import provenance boundaries.
- [Demo Repo](../examples/demo-repo/README.md): runnable end-to-end demo for PR review and evidence generation.
- [Adoption Playbook](adoption-playbook.md): 15-minute pilot path and promotion criteria from advisory to blocking gates.
- [External Pilot Intake](external-pilot-intake.md): go / no-go checklist for repositories outside this project.
- [Pilot Repository Examples](../examples/pilot-repos/README.md): copyable starter packs for Healthchecks, Umami, and Woodpecker-style repositories.
- [Open-core Boundary](open-core-boundary.md): what stays open-source and what belongs in hosted/enterprise layers.
- [Commercial Handoff Examples](../examples/commercial-handoff/README.md): schema-valid example payloads for future hosted consumers.
- [External Consumer Example](../examples/external-consumer/README.md): static hosted registry,
  GitHub App, and multi-repo artifact inputs for downstream products.

## First Production Path

1. Install the CLI from PyPI or Docker.
2. Run `skills-orchestrator check --config config/skills.yaml`.
3. Run `skills-orchestrator build --config config/skills.yaml --lock` and commit or review `AGENTS.md` / `skills.lock.json`.
4. Add the GitHub Action.
5. Enable `builtin/team-standard` policy pack.
6. Run `skills-orchestrator conformance run`.
7. For stricter pilots, enable `builtin/engineering-grade`.
8. Run `skills-orchestrator doctor --profile adopter`.
9. Export manifest, registry graph, and evidence bundle for releases.
10. Verify external skill trust metadata and container release evidence.
11. Document the release rollback path.
12. Enable and review OpenSSF Scorecard results.
13. Build a multi-repo artifact index from repository evidence manifests.
14. Validate external consumer payloads for hosted registry or GitHub App pilots.
15. Map governed instruction artifacts to agent surfaces and tenant/project scopes as metadata.
16. Validate lead/worker handoff and evidence expectations before running supervised agents.
17. Validate external agent runtime image contracts when workers are packaged as containers.
18. Enable MCP task-scoped routing when static checks are stable.
