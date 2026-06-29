# Commercial And Foundation Readiness

This document defines the adoption evidence standard for Skills Orchestrator. It is not an
`ADOPTERS.md` substitute, and it keeps foundation eligibility separate from release quality.

## Current Position

Skills Orchestrator is currently best described as:

> A CI-native governance system for AI instruction artifacts, focused on conformance validation,
> policy evaluation, registry integrity, CI-level explainability, and evidence-based traceability
> across multi-repository environments.

The project is suitable for advisory or limited blocking CI adoptions when a repository can generate
the standard evidence artifacts. It is not an agent runtime control plane, an OPA replacement, or a
hosted compliance platform.

## Readiness Levels

| Level | Claim | Evidence required |
| --- | --- | --- |
| 1. Local adoption | One repo can run SkillOps checks locally. | `check`, `schema audit --stability stable`, `build --lock`, `doctor --profile adopter`, and `conformance run --profile core` pass. |
| 2. CI adoption | One repo can run SkillOps in pull requests. | GitHub Action produces JSON/SARIF, reviewer summary, registry diff, and evidence bundle artifacts. |
| 3. Production advisory | A production-like repo can run advisory gates without blocking delivery. | `builtin/team-standard` is enabled, lock drift is visible, and PR reviewers understand failures. |
| 4. Production blocking | A platform-owned repo can block merges on instruction governance. | `builtin/engineering-grade --fail-on warning`, negative conformance, release trust verification, and rollback path are accepted by owners. |
| 5. Multi-repo governance | Multiple repos publish comparable SkillOps evidence. | `evidence index`, registry graph, dashboard snapshot, and multi-repo artifact schema validation pass from CI artifacts. |
| 6. External adoption | A repo not owned by the maintainer relies on SkillOps. | Public issue/PR/release evidence from that repo, a validated external adoption record, and permission to list it. |
| 7. Foundation candidate | The project has community and governance depth beyond one maintainer. | Multiple maintainers, real external adopters, documented governance, security response history, and regular releases. |

## Commercial Value Standard

The open-source CLI can meet commercial value when it helps a platform team reduce review and audit
work without requiring a SaaS backend. The minimum commercial-standard OSS package is:

- stable CLI surfaces for `check`, `schema`, `evidence`, `registry`, `conformance`, and release
  trust verification,
- machine-readable contracts with JSON Schema and conformance reports,
- negative fixtures proving bad instruction artifacts fail deterministically,
- GitHub Action integration that works in a single workflow step,
- PyPI, GHCR, SBOM, provenance, and release attestation hygiene,
- public OpenSSF Scorecard results or a documented reason why the check is temporarily disabled,
- repeatable adoption examples for production repositories,
- clear open-core boundary so hosted registry, GitHub App, and dashboard products consume OSS
  artifacts instead of changing CLI semantics.

This standard is met for CI governance adoption. Broader commercial references depend on retained
evidence from repositories that operate the tool without maintainer help.

## Foundation Readiness Standard

Foundation readiness is a community and governance milestone, not a version number. Public
foundation-readiness claims require all of these conditions:

- at least two independent external adopters have public evidence of use,
- at least two maintainers from different organizations can review and release,
- security policy and vulnerability response have been exercised,
- conformance fixtures are stable enough for third-party implementations,
- governance documents describe reality rather than intent,
- direction-setting decisions are tracked in issues or ADRs,
- release cadence and compatibility policy are predictable for downstream users.

Before those conditions are met, the correct claim is:

> Foundation-aligned, not foundation-ready.

## What Not To Do

- Do not create `ADOPTERS.md` from internal examples or reference fixtures.
- Do not describe the CLI as an agent runtime, multi-agent OS, or policy engine replacement.
- Do not add hosted-service state to the OSS CLI.
- Do not make screenshots or dashboards a conformance requirement.
- Do not make governance documents imply a multi-maintainer project before that is true.

## Operating Controls

- Conformance and negative fixtures are part of the release gate.
- GitHub Action and release trust workflows stay reproducible and pinned.
- Public security-health signals stay visible through CodeQL, pinned Actions, Dependabot, and
  OpenSSF Scorecard.
- Adoption guidance stays tied to copyable commands and retained artifacts.
- [External Adoption Intake](external-adoption-intake.md), [Adoption Evidence Pack](adoption-evidence-pack.md),
  and a validated adoption record are required before public listing permission is requested.
- Ecosystem examples preserve the same artifact contracts as the CLI.
- Governance claims are limited to evidence-backed maintainership and adoption facts.

## OpenSSF Scorecard Hygiene

The repository runs OpenSSF Scorecard on `main`, on a weekly schedule, and on manual dispatch. The
workflow publishes SARIF-backed results and keeps the action pinned to a full commit SHA, matching
the repository's existing GitHub Actions pinning policy.

Scorecard is not treated as a marketing badge or a release gate by itself. It is a public health
signal that complements:

- CodeQL analysis,
- pinned third-party GitHub Actions,
- constrained automation `pip install` paths checked by `scripts/check_pip_constraints.py`,
- Docker base image digest pinning checked by `scripts/check_docker_base_digest.py`,
- Dependabot update checks,
- PyPI trusted publishing,
- package artifact attestations,
- GHCR multi-architecture image publishing,
- container SBOM/provenance attestations.
