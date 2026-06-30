# Adoption Evidence Pack

This guide defines the handoff package for a real repository adoption. It is the bridge between a
successful local/CI run and an adoption decision. It does not create an adopter claim by itself.

Use this after [Adoption Authorization](adoption-authorization.md) and
[External Adoption Intake](external-adoption-intake.md), and before writing a public case study or
`ADOPTERS.md` entry.

## What The Pack Proves

An adoption evidence pack should prove:

1. A repository outside this project can run SkillOps without maintainer help.
2. The repository can retain machine-readable CI artifacts.
3. Reviewers can explain findings, registry changes, and promotion decisions.
4. Public listing consent is handled separately from technical success.

It does not prove runtime agent execution, tenant isolation, budget enforcement, secret isolation,
or formal compliance certification.

## Directory Shape

Keep the pack in a private issue, release artifact, or shared archive owned by the adoption team:

```text
skillops-adoption/
  README.md
  adoption-record.json
  artifacts/
    check.json
    skills-orchestrator.sarif
    ci-explainability.json
    skillops-review-summary.md
    registry-before.json
    registry-after.json
    registry-graph.json
    registry-diff.json
    registry-diff.md
    conformance.json
    dashboard-snapshot.json
    evidence/
      evidence-manifest.json
      ...
```

Do not include secrets, private tokens, private customer data, or raw model prompts that the
repository is not allowed to disclose. If an artifact cannot be shared, mark it as `missing` or
`not-applicable` in `adoption-record.json` and explain why.

## Local Reproduction Commands

Run these from the reference repository root after adding `config/skills.yaml` and `skills/`:

```bash
python3.12 -m pip install "skills-orchestrator==<adopter-pinned-version>"

mkdir -p skillops-adoption/artifacts/evidence

skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --format json \
  > skillops-adoption/artifacts/check.json

skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --format sarif \
  > skillops-adoption/artifacts/skills-orchestrator.sarif

skills-orchestrator explainability build \
  --check-json skillops-adoption/artifacts/check.json \
  --config config/skills.yaml \
  --output skillops-adoption/artifacts/ci-explainability.json \
  --force

skills-orchestrator build \
  --config config/skills.yaml \
  --lock

skills-orchestrator conformance run \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --profile core \
  --format json \
  > skillops-adoption/artifacts/conformance.json

skills-orchestrator evidence export \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --out skillops-adoption/artifacts/evidence

skills-orchestrator dashboard snapshot \
  --evidence-dir skillops-adoption/artifacts/evidence \
  --repository owner/repo \
  --ref refs/heads/main \
  --commit 0000000000000000000000000000000000000000 \
  --output skillops-adoption/artifacts/dashboard-snapshot.json \
  --force
```

For registry diff, capture a before/after pair around the pull request or local change:

```bash
skills-orchestrator registry build \
  --config-glob config/skills.yaml \
  --output skillops-adoption/artifacts/registry-before.json

# Edit or add a skill, then rebuild.

skills-orchestrator registry build \
  --config-glob config/skills.yaml \
  --output skillops-adoption/artifacts/registry-after.json

skills-orchestrator registry graph \
  --config-glob config/skills.yaml \
  --output skillops-adoption/artifacts/registry-graph.json

skills-orchestrator registry diff \
  skillops-adoption/artifacts/registry-before.json \
  skillops-adoption/artifacts/registry-after.json \
  --format json \
  --output skillops-adoption/artifacts/registry-diff.json \
  --force

skills-orchestrator registry diff \
  skillops-adoption/artifacts/registry-before.json \
  skillops-adoption/artifacts/registry-after.json \
  --format markdown \
  --output skillops-adoption/artifacts/registry-diff.md \
  --force

skills-orchestrator reviewer summary \
  --check-json skillops-adoption/artifacts/check.json \
  --registry-diff-json skillops-adoption/artifacts/registry-diff.json \
  --registry-diff-markdown skillops-adoption/artifacts/registry-diff.md \
  --registry-graph skillops-adoption/artifacts/registry-graph.json \
  --evidence-manifest skillops-adoption/artifacts/evidence/evidence-manifest.json \
  --output skillops-adoption/artifacts/skillops-review-summary.md \
  --force
```

## CI Artifact Requirements

The CI run should preserve at least:

| Artifact | Required | Why |
| --- | --- | --- |
| `check.json` | Yes | Stable diagnostics and policy trace. |
| SARIF | Yes | Code scanning integration. |
| `ci-explainability.json` | Recommended | Reviewer-facing failure explanation. |
| registry diff | Recommended | Reviewable skill change summary. |
| `conformance.json` | Yes | Contract compatibility proof. |
| `evidence/evidence-manifest.json` | Yes | Evidence bundle entry point and hash ledger. |
| dashboard snapshot | Optional | Reporting input; not a conformance requirement. |

Keep the first external adoption advisory unless the repository already has owners, source, version,
lifecycle, license, review-window metadata, and accepted failure ownership.

## Adoption Record

Create `skillops-adoption/adoption-record.json` and validate it:

```bash
skills-orchestrator schema validate \
  --kind external-adoption-record \
  --input skillops-adoption/adoption-record.json
```

Use `status: "present"` only when the artifact exists in the handoff package. Use
`status: "missing"` when it should exist but was not retained. Use `status: "not-applicable"` only
when the artifact is not required for the selected gate.

The record must include `authorization.tier`. Keep the tier at `private-technical-adoption`,
`pending`, `not-requested`, or `declined-no-follow-up` unless the repository owner explicitly
approves public reference. A public adopter listing is valid only when `authorization.tier` is
`public-adopter-reference` or `public-case-study` and `public_listing.status` is `approved`.

Public listing must remain separate:

- `not-requested`: technical adoption evidence exists, but no public listing was requested.
- `denied`: the team ran an adoption but does not allow public citation.
- `approved`: the team explicitly approved public citation; `approved_by` and `approved_at` are
  required by schema.

## Review Meeting Agenda

Use this order for the adoption review:

1. Confirm the repository owner and CI owner.
2. Confirm the SkillOps version, policy pack, and gate mode.
3. Open `check.json` and SARIF; map every finding to an owner.
4. Open the registry diff; decide whether the change is understandable in PR review.
5. Open `conformance.json`; confirm the repo satisfies the core contract.
6. Open `evidence/evidence-manifest.json`; confirm the bundle hash and artifact list.
7. Decide `stay-advisory`, `promote-warning`, `promote-engineering`, or `stop-adoption`.
8. Decide whether public listing will be requested later.

## Promotion Decisions

Use `promote-warning` only when:

- `check --policy-pack builtin/team-standard --fail-on warning` is clean,
- `doctor --profile adopter` is `100/100`,
- reviewers understand registry diff and SARIF findings,
- `skills.lock.json` drift is visible and accepted as a review item.

Use `promote-engineering` only when:

- `builtin/engineering-grade --fail-on warning` is clean,
- external skills have provenance and license metadata,
- review-window metadata is current,
- release owners accept rollback behavior for bad generated artifacts.

Use `stop-adoption` when artifacts cannot be retained, failures have no owner, or the workflow would
require unsafe `pull_request_target` behavior for untrusted forks.

## Case Study Boundary

After an adoption succeeds, use [Adoption Case Study Template](adoption-case-study-template.md) to write a
case. Do not publish repository names, screenshots, metrics, or quotes until `public_listing.status`
is `approved`.
