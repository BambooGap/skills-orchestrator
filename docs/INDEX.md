# Documentation Index

Use this page as the team entry point for Skills Orchestrator.

## By Role

| Role | Start Here | Goal |
| --- | --- | --- |
| Repository maintainer | [Install](install.md), [GitHub Action](github-action.md) | Add a working skill check to one repo. |
| Platform owner | [Production Adoption](production-adoption.md), [Adoption Maturity Model](adoption-maturity-model.md), [Adoption Playbook](adoption-playbook.md), [Team Standardization](team-standardization.md), [CI/CD](CI_CD.md), [Conformance](../CONFORMANCE.md) | Roll the same contract across multiple repos. |
| Security reviewer | [Supply Chain Verification](supply-chain-verification.md), [SLSA Readiness](slsa-readiness.md), [Manifest And Policy Exports](manifest-policy-exports.md), [Policy Packs](policy-packs.md), [Compatibility](../COMPATIBILITY.md) | Review instruction assets with machine-readable evidence. |
| Release owner | [Release Verification](release-verification.md), [Supply Chain Verification](supply-chain-verification.md), [SLSA Readiness](slsa-readiness.md), [Release Rollback](release-rollback.md), [Registry And Evidence](registry-evidence.md), [Docker Usage](docker.md) | Produce repeatable release evidence and a rollback path. |
| Agent runtime owner | [MCP Server](MCP_SERVER.md), [Adapters](adapters.md), [Pipelines](PIPELINES.md) | Consume governed context and preserve workflow state. |
| External evaluator | [SkillOps Contract](../SPEC.md), [Conformance](../CONFORMANCE.md), [Third-party Implementation](third-party-implementation.md), [Negative Conformance Fixtures](../examples/negative-conformance/README.md), [Foundation Readiness](foundation-readiness.md), [Reference Repository](../examples/demo-repo/README.md) | Verify the project as a technical contract, not only a CLI. |
| Adoption team | [Adoption Authorization](adoption-authorization.md), [External Adoption Intake](external-adoption-intake.md), [Adoption Evidence Pack](adoption-evidence-pack.md), [Adoption Playbook](adoption-playbook.md), [External Adoption Record](../examples/external-adoption-record/README.md), [Adoption Case Study Template](adoption-case-study-template.md), [Reference Repos](../examples/adoption-repos/README.md), [GitHub Action](github-action.md) | Get explicit adoption permission, copy a realistic starter pack into one production-like repo, retain review evidence, and record adoption decisions. |
| Agent ecosystem integrator | [Agent Fleet Governance](agent-fleet-governance.md), [Supervisor Governance](supervisor-governance.md), [Agent Handoff Contract Example](../examples/agent-handoff/README.md), [Agent Runtime Image Contract Example](../examples/agent-runtime-image/README.md), [Adapters](adapters.md), [Adapter Evidence Example](../examples/adapter-evidence/README.md), [Conformance](../CONFORMANCE.md) | Generate governed agent-surface, handoff, and runtime-image evidence from one SkillOps config. |
| Commercial product owner | [Open-core Boundary](open-core-boundary.md), [GitHub App Blueprint](github-app.md), [Hosted Registry](hosted-registry.md), [Enterprise Dashboard](enterprise-dashboard.md) | Build hosted products around OSS artifact contracts. |

## Core Concepts

- [Zones](ZONES.md): map teams, directories, or repo areas to different instruction policies.
- [Pipelines](PIPELINES.md): turn multiple skills into gated runtime workflows.
- [Instruction Supply Chain Status](instruction-supply-chain-status.md): current ecosystem boundary.
- [Enterprise Narrative](enterprise.md): positioning, buyers, non-goals, and ecosystem routing.
- [Adoption Maturity Model](adoption-maturity-model.md): artifact-driven levels from local adoption to external adoption.
- [Production Adoption](production-adoption.md): minimum production CI configuration with SHA pins, Docker digests, evidence retention, and runtime boundaries.
- [Supply Chain Verification](supply-chain-verification.md): consumer-side verification for PyPI attestations, GHCR provenance/SBOM attestations, digest pins, and hash-lock boundaries.
- [SLSA Readiness](slsa-readiness.md): non-certifying build-track readiness map for release evidence; records what is evidence-ready and what is not claimed.
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
- [Reference Repository](../examples/demo-repo/README.md): runnable end-to-end reference for PR review and evidence generation.
- [Adoption Playbook](adoption-playbook.md): 15-minute adoption path and promotion criteria from advisory to blocking gates.
- [Adoption Authorization](adoption-authorization.md): maintainer request template, consent levels, and public-claim guardrails before a real external adoption.
- [External Adoption Intake](external-adoption-intake.md): go / no-go checklist for repositories outside this project.
- [Adoption Evidence Pack](adoption-evidence-pack.md): artifact handoff package for real external repository adoptions.
- [External Adoption Record Example](../examples/external-adoption-record/README.md): machine-valid adoption handoff record that separates technical success from public adopter consent.
- [Adoption Case Study Template](adoption-case-study-template.md): public case-study structure that requires validated adoption evidence and listing consent.
- [Reference Repository Examples](../examples/adoption-repos/README.md): copyable starter packs for Healthchecks, Umami, and Woodpecker-style repositories.
- [Open-core Boundary](open-core-boundary.md): what stays open-source and what belongs in hosted/enterprise layers.
- [Commercial Handoff Examples](../examples/commercial-handoff/README.md): schema-valid example payloads for hosted consumers.
- [External Consumer Example](../examples/external-consumer/README.md): static hosted registry,
  GitHub App, and multi-repo artifact inputs for downstream products.

## First Production Path

1. Install the CLI from PyPI or Docker.
2. Run `skills-orchestrator check --config config/skills.yaml`.
3. Run `skills-orchestrator build --config config/skills.yaml --lock` and commit or review `AGENTS.md` / `skills.lock.json`.
4. Add the GitHub Action.
5. Enable `builtin/team-standard` policy pack.
6. Run `skills-orchestrator conformance run`.
7. For stricter adoptions, enable `builtin/engineering-grade`.
8. Run `skills-orchestrator doctor --profile adopter`.
9. Export manifest, registry graph, and evidence bundle for releases.
10. Verify external skill trust metadata and container release evidence.
11. Verify PyPI and GHCR release attestations before promoting a production CI pin.
12. Generate and archive a non-certifying SLSA readiness map beside the release smoke report.
13. Document the release rollback path.
14. Enable and review OpenSSF Scorecard results.
15. Build a multi-repo artifact index from repository evidence manifests.
16. Validate external consumer payloads for hosted registry or GitHub App adoptions.
17. Get explicit adoption authorization before treating a real external repository as more than a self-run technical check.
18. Validate an external adoption record before counting the adoption as review evidence.
19. Retain an adoption evidence pack before asking for public adopter listing permission.
20. Use the adoption case-study template only after listing consent and the matching public
    authorization tier are approved.
21. Map governed instruction artifacts to agent surfaces and tenant/project scopes as metadata.
22. Validate lead/worker handoff and evidence expectations before running supervised agents.
23. Validate external agent runtime image contracts when workers are packaged as containers.
24. Enable MCP task-scoped routing when static checks are stable.
