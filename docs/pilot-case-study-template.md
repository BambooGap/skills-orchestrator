# Pilot Case Study Template

Use this template after a real repository has produced a validated
`external-pilot-record`. It is designed to keep public adoption claims honest while still giving
platform teams a useful story to evaluate.

Do not publish this as an adopter case until the repository owner explicitly approves public
listing. Synthetic examples, internal demos, and maintainer-owned fixtures do not qualify.

## Case Metadata

| Field | Value |
| --- | --- |
| Repository | `owner/repo` |
| Organization/team | `team-name` |
| Pilot owner | `name-or-team` |
| SkillOps version | `vX.Y.Z` |
| Gate mode | `advisory`, `warning`, `engineering`, or `release-gate` |
| Policy pack | `builtin/team-standard` or `builtin/engineering-grade` |
| CI system | `github-actions`, `gitlab-ci`, `buildkite`, or other |
| Public listing consent | `not-requested`, `denied`, or `approved` |

## Starting Point

Describe the repository shape:

- application type,
- number of initial skills,
- whether external/copied skills were present,
- existing CI and release process,
- why instruction governance was needed.

Avoid naming private customers, secrets, incident details, or unpublished internal architecture.

## Pilot Patch

List the smallest patch used for the pilot:

```text
config/skills.yaml
skills/
.github/workflows/skillops.yml
evidence/.gitkeep
```

If the pilot required additional files, explain why:

- `AGENTS.md`
- `skills.lock.json`
- adapter exports
- release trust fixtures
- external skill provenance

## Evidence Produced

Summarize the artifacts retained from the first successful CI run:

| Artifact | Status | Notes |
| --- | --- | --- |
| `check.json` | `present` |  |
| SARIF | `present` |  |
| `ci-explainability.json` | `present` / `not-applicable` |  |
| registry diff | `present` / `not-applicable` |  |
| `conformance.json` | `present` |  |
| `evidence/evidence-manifest.json` | `present` |  |
| dashboard snapshot | `present` / `not-applicable` |  |

Reference the validated `pilot-record.json` path or CI artifact URL if it is public.

## What Changed For Reviewers

Answer these questions in concrete terms:

1. Could reviewers identify which skill changed?
2. Could reviewers map findings to an owner?
3. Did SARIF or PR summaries reduce manual review time?
4. Did lock drift catch unexpected instruction changes?
5. Did the team understand the difference between advisory and blocking gates?

Use neutral language. Do not claim productivity gains unless the pilot measured them.

## Promotion Decision

Record the decision:

- `stay-advisory`
- `promote-warning`
- `promote-engineering`
- `promote-release-gate`
- `stop-pilot`

Then explain:

- what evidence supported the decision,
- which risks remain,
- who owns the next review,
- when the next review happens.

## Measured Outcomes

Only include metrics that were actually measured:

| Metric | Before | After | Measurement window |
| --- | --- | --- | --- |
| Skill metadata coverage |  |  |  |
| CI findings resolved |  |  |  |
| Registry diff review time |  |  |  |
| Evidence bundle availability |  |  |  |
| External skill provenance coverage |  |  |  |

If no metrics were measured, write:

> No quantitative outcome was measured during this pilot.

## Public Quote

Leave this blank until public listing is approved.

```text
Quote:
Approved by:
Approved at:
Scope:
```

## Non-Goals And Boundaries

State these boundaries explicitly:

- This pilot validates CI governance of AI instruction artifacts.
- It does not validate agent runtime enforcement.
- It does not prove tenant isolation, secret isolation, or budget enforcement.
- It is not a formal SLSA or compliance certification.
- It is not an adopter claim unless public listing consent is approved.

## Publication Checklist

Before publishing:

- `pilot-record.json` validates against `external-pilot-record`.
- `public_listing.status` is `approved`.
- `approved_by` and `approved_at` are present.
- Private repository details are redacted or approved.
- The case links to public CI/release evidence when possible.
- The case does not imply runtime control-plane capabilities.
